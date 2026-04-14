"""
trading_bot.bot — Binance Futures Testnet trading bot core package.
"""

from .client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceAuthError
from .orders import place_order
from .logging_config import setup_logging

__all__ = [
    "BinanceFuturesClient",
    "BinanceAPIError",
    "BinanceNetworkError",
    "BinanceAuthError",
    "place_order",
    "setup_logging",
]
