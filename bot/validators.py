"""
Input validation for order parameters.
Raises ValueError with a human-readable message on any violation.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP", "TAKE_PROFIT", "TAKE_PROFIT_MARKET"}


# ── public helpers ──────────────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """Uppercase and basic format check (letters only, min 3 chars)."""
    symbol = symbol.strip().upper()
    if not symbol.isalpha() or len(symbol) < 3:
        raise ValueError(
            f"Invalid symbol '{symbol}'. Must be alphabetic, e.g. BTCUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    """Ensure side is BUY or SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """Ensure order type is supported."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Parse and validate quantity — must be positive."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Invalid quantity '{quantity}'. Must be a positive number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than 0. Got: {qty}")
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """
    Price is required for LIMIT and STOP orders; must be positive.
    Returns None for MARKET/STOP_MARKET (price not needed).
    """
    no_price_types = {"MARKET", "STOP_MARKET", "TAKE_PROFIT_MARKET"}
    order_type = order_type.strip().upper()

    if order_type in no_price_types:
        return None   # price is irrelevant for these types

    if price is None:
        raise ValueError(
            f"Price is required for {order_type} orders."
        )
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Invalid price '{price}'. Must be a positive number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than 0. Got: {p}")
    return p


def validate_stop_price(stop_price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """Stop price required for STOP / TAKE_PROFIT order types."""
    needs_stop = {"STOP", "TAKE_PROFIT", "STOP_MARKET", "TAKE_PROFIT_MARKET"}
    order_type = order_type.strip().upper()

    if order_type not in needs_stop:
        return None

    if stop_price is None:
        raise ValueError(
            f"stopPrice is required for {order_type} orders."
        )
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Invalid stopPrice '{stop_price}'. Must be a positive number.")
    if sp <= 0:
        raise ValueError(f"stopPrice must be greater than 0. Got: {sp}")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validations and return a clean, normalised parameter dict.
    Raises ValueError on the first violation found.
    """
    clean_type = validate_order_type(order_type)
    clean_price = validate_price(price, clean_type)
    clean_stop = validate_stop_price(stop_price, clean_type)

    return {
        "symbol":     validate_symbol(symbol),
        "side":       validate_side(side),
        "order_type": clean_type,
        "quantity":   validate_quantity(quantity),
        "price":      clean_price,
        "stop_price": clean_stop,
    }
