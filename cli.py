#!/usr/bin/env python3
"""
cli.py — Trading Bot CLI entry point.

Usage examples
--------------
Place a MARKET buy:
    python cli.py place-order --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

Place a LIMIT sell:
    python cli.py place-order --symbol BTCUSDT --side SELL --type LIMIT \
        --quantity 0.001 --price 95000

Place a STOP_MARKET:
    python cli.py place-order --symbol BTCUSDT --side SELL --type STOP_MARKET \
        --quantity 0.001 --stop-price 90000

Account balance:
    python cli.py account

Open orders:
    python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import click

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceAuthError
from bot.orders import place_order as _place_order
from bot.logging_config import setup_logging

# ── Colour helpers (click.style wrappers) ─────────────────────────────────────

def ok(msg: str)   -> str: return click.style(msg, fg="green", bold=True)
def err(msg: str)  -> str: return click.style(msg, fg="red",   bold=True)
def warn(msg: str) -> str: return click.style(msg, fg="yellow")
def info(msg: str) -> str: return click.style(msg, fg="cyan")
def bold(msg: str) -> str: return click.style(msg, bold=True)


def _section(title: str) -> None:
    click.echo(f"\n{bold('─' * 50)}")
    click.echo(f"  {bold(title)}")
    click.echo(f"{bold('─' * 50)}")


def _kv(label: str, value, color: str = "white") -> None:
    click.echo(f"  {click.style(label + ':', fg='bright_black'):<22} "
               f"{click.style(str(value), fg=color)}")


# ── Client factory ─────────────────────────────────────────────────────────────

def _build_client(log_level: str) -> BinanceFuturesClient:
    """Read credentials from environment and return a configured client."""
    setup_logging(level=log_level)

    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        click.echo(
            err("✗ API credentials not found.\n")
            + warn(
                "  Set the following environment variables before running:\n"
                "    export BINANCE_API_KEY='your_key_here'\n"
                "    export BINANCE_API_SECRET='your_secret_here'\n"
                "  Or create a .env file and load it with:\n"
                "    source .env"
            )
        )
        sys.exit(1)

    try:
        return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    except BinanceAuthError as exc:
        click.echo(err(f"✗ Auth error: {exc}"))
        sys.exit(1)


# ── Root group ─────────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    show_default=True,
    help="Console log verbosity. File always captures DEBUG.",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """
    \b
    ╔══════════════════════════════════════╗
    ║   Binance Futures Testnet Trade Bot  ║
    ╚══════════════════════════════════════╝

    API credentials are read from environment variables:
      BINANCE_API_KEY and BINANCE_API_SECRET
    """
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level


# ── place-order command ────────────────────────────────────────────────────────

@cli.command("place-order")
@click.option("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT")
@click.option("--side",       required=True,  type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="Order direction")
@click.option("--type",       "order_type",   required=True, type=click.Choice(["MARKET", "LIMIT", "STOP_MARKET"], case_sensitive=False), help="Order type")
@click.option("--quantity",   required=True,  type=float,    help="Number of contracts / coins")
@click.option("--price",      default=None,   type=float,    help="Limit price (required for LIMIT orders)")
@click.option("--stop-price", "stop_price",   default=None, type=float, help="Stop trigger price (required for STOP_MARKET)")
@click.option("--tif",        default="GTC",  type=click.Choice(["GTC", "IOC", "FOK"], case_sensitive=False), show_default=True, help="Time-in-force for LIMIT orders")
@click.pass_context
def place_order_cmd(
    ctx: click.Context,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    tif: str,
) -> None:
    """Place a new order on Binance Futures Testnet."""
    client = _build_client(ctx.obj["log_level"])

    # ── Request summary ──────────────────────────────────────────────────────
    _section("ORDER REQUEST")
    _kv("Symbol",      symbol.upper())
    _kv("Side",        side.upper(),       color="green" if side.upper() == "BUY" else "red")
    _kv("Type",        order_type.upper(), color="cyan")
    _kv("Quantity",    quantity)
    if price is not None:
        _kv("Price",       price)
    if stop_price is not None:
        _kv("Stop Price",  stop_price)
    if order_type.upper() == "LIMIT":
        _kv("TimeInForce", tif)

    click.echo()

    # ── Place the order ──────────────────────────────────────────────────────
    try:
        result = _place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=tif,
        )
    except ValueError as exc:
        click.echo(err(f"✗ Validation error: {exc}"))
        sys.exit(1)
    except BinanceAPIError as exc:
        click.echo(err(f"✗ API error [{exc.code}]: {exc.msg}"))
        sys.exit(1)
    except BinanceNetworkError as exc:
        click.echo(err(f"✗ Network error: {exc}"))
        sys.exit(1)

    # ── Response details ─────────────────────────────────────────────────────
    _section("ORDER RESPONSE")
    status = result.get("status", "UNKNOWN")
    _kv("Order ID",     result.get("orderId"),     color="bright_white")
    _kv("Status",       status,                    color="green" if status == "FILLED" else "yellow")
    _kv("Type",         result.get("type"))
    _kv("Side",         result.get("side"),        color="green" if result.get("side") == "BUY" else "red")
    _kv("Orig Qty",     result.get("origQty"))
    _kv("Executed Qty", result.get("executedQty"), color="bright_white")
    _kv("Avg Price",    result.get("avgPrice")     or "—")
    _kv("Limit Price",  result.get("price")        or "—")
    _kv("Stop Price",   result.get("stopPrice")    or "—")
    _kv("Time-in-Force",result.get("timeInForce")  or "—")
    _kv("Client OID",   result.get("clientOrderId"))
    click.echo()
    click.echo(ok("✓ Order placed successfully!"))


# ── account command ────────────────────────────────────────────────────────────

@cli.command("account")
@click.option("--full", is_flag=True, help="Print the full JSON response.")
@click.pass_context
def account_cmd(ctx: click.Context, full: bool) -> None:
    """Display account balance and margin information."""
    client = _build_client(ctx.obj["log_level"])

    try:
        data = client.get_account()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        click.echo(err(f"✗ {exc}"))
        sys.exit(1)

    if full:
        click.echo(json.dumps(data, indent=2))
        return

    _section("ACCOUNT SUMMARY")
    _kv("Total Wallet Balance",    data.get("totalWalletBalance"))
    _kv("Total Unrealized PnL",    data.get("totalUnrealizedProfit"))
    _kv("Total Margin Balance",    data.get("totalMarginBalance"))
    _kv("Available Balance",       data.get("availableBalance"))
    _kv("Max Withdraw Amount",     data.get("maxWithdrawAmount"))

    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]
    if assets:
        click.echo(f"\n  {bold('Assets with balance:')}")
        for asset in assets:
            _kv(f"  {asset['asset']}", asset.get("walletBalance"))


# ── open-orders command ────────────────────────────────────────────────────────

@cli.command("open-orders")
@click.option("--symbol", default=None, help="Filter by symbol (e.g. BTCUSDT).")
@click.pass_context
def open_orders_cmd(ctx: click.Context, symbol: Optional[str]) -> None:
    """List open orders on the account."""
    client = _build_client(ctx.obj["log_level"])

    try:
        orders = client.get_open_orders(symbol=symbol)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        click.echo(err(f"✗ {exc}"))
        sys.exit(1)

    if not orders:
        click.echo(info("ℹ No open orders found."))
        return

    _section(f"OPEN ORDERS ({len(orders)})")
    for i, o in enumerate(orders, 1):
        click.echo(
            f"  [{i}] {bold(o.get('symbol','?'))} "
            f"{click.style(o.get('side','?'), fg='green' if o.get('side')=='BUY' else 'red')} "
            f"{o.get('type','?')} | "
            f"qty={o.get('origQty')} price={o.get('price')} | "
            f"orderId={o.get('orderId')}"
        )


# ── cancel-order command ───────────────────────────────────────────────────────

@cli.command("cancel-order")
@click.option("--symbol",   required=True, help="Trading pair, e.g. BTCUSDT")
@click.option("--order-id", required=True, type=int, help="Order ID to cancel")
@click.pass_context
def cancel_order_cmd(ctx: click.Context, symbol: str, order_id: int) -> None:
    """Cancel an open order by its ID."""
    client = _build_client(ctx.obj["log_level"])

    try:
        result = client.cancel_order(symbol=symbol, order_id=order_id)
    except BinanceAPIError as exc:
        click.echo(err(f"✗ API error [{exc.code}]: {exc.msg}"))
        sys.exit(1)
    except BinanceNetworkError as exc:
        click.echo(err(f"✗ Network error: {exc}"))
        sys.exit(1)

    _section("CANCEL RESPONSE")
    _kv("Order ID", result.get("orderId"))
    _kv("Symbol",   result.get("symbol"))
    _kv("Status",   result.get("status"), color="yellow")
    click.echo()
    click.echo(ok("✓ Order cancelled successfully!"))


# ── server-time command ────────────────────────────────────────────────────────

@cli.command("server-time")
@click.pass_context
def server_time_cmd(ctx: click.Context) -> None:
    """Fetch and display Binance Testnet server time (connectivity check)."""
    client = _build_client(ctx.obj["log_level"])

    try:
        ts = client.get_server_time()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        click.echo(err(f"✗ {exc}"))
        sys.exit(1)

    import datetime
    dt = datetime.datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
    click.echo(info(f"✓ Binance Testnet server time: {dt} (epoch ms: {ts})"))


# ── entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli(obj={})
