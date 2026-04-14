"""
Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamping
  - Server-time synchronisation (optional, enabled by default)
  - Structured logging of every request / response
  - Granular exception hierarchy
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import setup_logging

# Ensure logging is initialised even if client is imported standalone
setup_logging()
log = logging.getLogger("trading_bot.client")

# ── Base URL ───────────────────────────────────────────────────────────────────
BASE_URL = "https://testnet.binancefuture.com"

# ── Custom exceptions ──────────────────────────────────────────────────────────

class BinanceClientError(Exception):
    """Base exception for all client-layer errors."""


class BinanceAPIError(BinanceClientError):
    """Raised when the Binance API returns a non-2xx status or error payload."""

    def __init__(self, status_code: int, code: int, msg: str) -> None:
        self.status_code = status_code
        self.code = code
        self.msg = msg
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {msg}")


class BinanceNetworkError(BinanceClientError):
    """Raised on network / connection failures."""


class BinanceAuthError(BinanceClientError):
    """Raised when API key / secret are missing or invalid."""


# ── Client ─────────────────────────────────────────────────────────────────────

class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API.

    Parameters
    ----------
    api_key : str
        Your Binance Futures Testnet API key.
    api_secret : str
        Your Binance Futures Testnet secret key.
    base_url : str
        Override the default testnet URL if needed.
    recv_window : int
        Milliseconds tolerance for request validity (default: 5000).
    timeout : int
        HTTP request timeout in seconds (default: 10).
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = BASE_URL,
        recv_window: int = 5000,
        timeout: int = 10,
    ) -> None:
        self._api_key = (api_key or "").strip()
        self._api_secret = (api_secret or "").strip()
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self.timeout = timeout

        self._session = requests.Session()
        if self._api_key:
            self._session.headers.update({"X-MBX-APIKEY": self._api_key})

        log.info("BinanceFuturesClient initialised (base_url=%s)", self.base_url)

    # ── Signing ────────────────────────────────────────────────────────────────

    def _sign(self, params: Dict[str, Any]) -> str:
        """Return HMAC-SHA256 hex signature of the query string."""
        query = urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _signed_params(self, extra: Dict[str, Any]) -> Dict[str, Any]:
        """Merge extra params with timestamp/recvWindow and append signature."""
        params = {
            **extra,
            "timestamp": int(time.time() * 1000),
            "recvWindow": self.recv_window,
        }
        params["signature"] = self._sign(params)
        return params

    # ── HTTP helpers ───────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        signed: bool = False,
        **kwargs,
    ) -> Any:
        """
        Internal HTTP dispatcher.

        Logs request summary and full response; raises typed exceptions on errors.
        """
        url = f"{self.base_url}{path}"

        if signed:
            if not self._api_key or not self._api_secret:
                raise BinanceAuthError(
                    "Signed endpoint requested but API credentials are missing. "
                    "Set BINANCE_API_KEY and BINANCE_API_SECRET."
                )
            params = kwargs.pop("params", {})
            kwargs["params"] = self._signed_params(params)

        log.debug(
            "→ %s %s | params=%s",
            method.upper(),
            path,
            kwargs.get("params") or kwargs.get("data"),
        )

        try:
            resp = self._session.request(
                method, url, timeout=self.timeout, **kwargs
            )
        except requests.exceptions.ConnectionError as exc:
            log.error("Network connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            log.error("Request timed out after %ss: %s", self.timeout, exc)
            raise BinanceNetworkError(f"Request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            log.error("Unexpected request error: %s", exc)
            raise BinanceNetworkError(f"Request error: {exc}") from exc

        log.debug("← HTTP %s | body=%s", resp.status_code, resp.text[:400])

        # Parse JSON; fall back to raw text
        try:
            payload = resp.json()
        except ValueError:
            payload = resp.text

        if not resp.ok:
            if isinstance(payload, dict):
                code = payload.get("code", resp.status_code)
                msg = payload.get("msg", resp.reason)
            else:
                code = resp.status_code
                msg = str(payload)
            log.error("API error %s (HTTP %s): %s", code, resp.status_code, msg)
            raise BinanceAPIError(resp.status_code, code, msg)

        return payload

    # ── Public endpoints ───────────────────────────────────────────────────────

    def get_server_time(self) -> int:
        """Return server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self, symbol: Optional[str] = None) -> Dict:
        """Return exchange info (optionally filtered to one symbol)."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", "/fapi/v1/exchangeInfo", params=params)

    def get_account(self) -> Dict:
        """Return account balance and position information."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    # ── Order endpoints ────────────────────────────────────────────────────────

    def place_order(self, **order_params) -> Dict:
        """
        Place a new order.

        All parameters are passed directly to POST /fapi/v1/order.
        Caller is responsible for correct param names (see orders.py).
        """
        log.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
            order_params.get("symbol"),
            order_params.get("side"),
            order_params.get("type"),
            order_params.get("quantity"),
            order_params.get("price", "—"),
            order_params.get("stopPrice", "—"),
        )
        return self._request(
            "POST",
            "/fapi/v1/order",
            signed=True,
            params=order_params,
        )

    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """Cancel an open order by orderId."""
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            signed=True,
            params={"symbol": symbol.upper(), "orderId": order_id},
        )

    def get_order(self, symbol: str, order_id: int) -> Dict:
        """Query order status."""
        return self._request(
            "GET",
            "/fapi/v1/order",
            signed=True,
            params={"symbol": symbol.upper(), "orderId": order_id},
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """List all open orders (optionally filtered by symbol)."""
        params = {}
        if symbol:
            params["symbol"] = symbol.upper()
        return self._request("GET", "/fapi/v1/openOrders", signed=True, params=params)
