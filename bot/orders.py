"""
High-level order placement logic.

Wraps the raw client calls with:
  - Parameter construction for each order type
  - Validation (via validators module)
  - Consistent structured logging
  - Clean response extraction
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient
from .validators import validate_all

log = logging.getLogger("trading_bot.orders")

# ── Response helpers ────────────────────────────────────────────────────────────

def _extract_summary(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pull the most useful fields out of a raw Binance order response.
    Extra fields are preserved under 'raw'.
    """
    return {
        "orderId":     response.get("orderId"),
        "symbol":      response.get("symbol"),
        "side":        response.get("side"),
        "type":        response.get("type"),
        "status":      response.get("status"),
        "price":       response.get("price"),
        "stopPrice":   response.get("stopPrice"),
        "origQty":     response.get("origQty"),
        "executedQty": response.get("executedQty"),
        "avgPrice":    response.get("avgPrice"),
        "timeInForce": response.get("timeInForce"),
        "clientOrderId": response.get("clientOrderId"),
        "raw":         response,
    }


# ── Order functions ─────────────────────────────────────────────────────────────

def place_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float | str,
) -> Dict[str, Any]:
    """
    Place a MARKET order.

    Parameters
    ----------
    client   : BinanceFuturesClient
    symbol   : e.g. "BTCUSDT"
    side     : "BUY" or "SELL"
    quantity : number of contracts / coins
    """
    params = validate_all(symbol=symbol, side=side, order_type="MARKET", quantity=quantity)
    log.info(
        "MARKET order | %s %s qty=%s",
        params["side"], params["symbol"], params["quantity"],
    )

    response = client.place_order(
        symbol=params["symbol"],
        side=params["side"],
        type="MARKET",
        quantity=str(params["quantity"]),
    )
    summary = _extract_summary(response)
    log.info(
        "MARKET order accepted | orderId=%s status=%s executedQty=%s avgPrice=%s",
        summary["orderId"], summary["status"],
        summary["executedQty"], summary["avgPrice"],
    )
    return summary


def place_limit_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float | str,
    price: float | str,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Place a LIMIT order.

    Parameters
    ----------
    time_in_force : GTC | IOC | FOK  (default: GTC — Good Till Cancel)
    """
    params = validate_all(
        symbol=symbol, side=side, order_type="LIMIT",
        quantity=quantity, price=price,
    )
    log.info(
        "LIMIT order | %s %s qty=%s price=%s tif=%s",
        params["side"], params["symbol"],
        params["quantity"], params["price"], time_in_force,
    )

    response = client.place_order(
        symbol=params["symbol"],
        side=params["side"],
        type="LIMIT",
        quantity=str(params["quantity"]),
        price=str(params["price"]),
        timeInForce=time_in_force,
    )
    summary = _extract_summary(response)
    log.info(
        "LIMIT order accepted | orderId=%s status=%s price=%s origQty=%s",
        summary["orderId"], summary["status"],
        summary["price"], summary["origQty"],
    )
    return summary


def place_stop_market_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    quantity: float | str,
    stop_price: float | str,
) -> Dict[str, Any]:
    """
    Place a STOP_MARKET order (bonus order type).

    Triggers a market order when the market reaches ``stop_price``.
    """
    params = validate_all(
        symbol=symbol, side=side, order_type="STOP_MARKET",
        quantity=quantity, stop_price=stop_price,
    )
    log.info(
        "STOP_MARKET order | %s %s qty=%s stopPrice=%s",
        params["side"], params["symbol"],
        params["quantity"], params["stop_price"],
    )

    response = client.place_order(
        symbol=params["symbol"],
        side=params["side"],
        type="STOP_MARKET",
        quantity=str(params["quantity"]),
        stopPrice=str(params["stop_price"]),
    )
    summary = _extract_summary(response)
    log.info(
        "STOP_MARKET order accepted | orderId=%s status=%s stopPrice=%s",
        summary["orderId"], summary["status"], summary["stopPrice"],
    )
    return summary


# ── Convenience dispatcher ──────────────────────────────────────────────────────

def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: Optional[float | str] = None,
    stop_price: Optional[float | str] = None,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Single entry-point that dispatches to the correct order function.

    Raises
    ------
    ValueError  – on invalid parameters (before hitting the API)
    BinanceAPIError  – when the API rejects the order
    BinanceNetworkError – on connectivity issues
    """
    order_type = order_type.strip().upper()

    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)

    if order_type == "LIMIT":
        return place_limit_order(client, symbol, side, quantity, price, time_in_force)

    if order_type == "STOP_MARKET":
        return place_stop_market_order(client, symbol, side, quantity, stop_price)

    raise ValueError(
        f"Unsupported order type: '{order_type}'. "
        "Supported: MARKET, LIMIT, STOP_MARKET."
    )
