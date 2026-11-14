"""Multi-platform trading engines. App e: from engines import PLATFORMS, get_engine, FOREX_DATABASE"""
from .base import BaseEngine
from .bybit import BybitEngine
from .ccxt_engine import BinanceEngine, OkxEngine, BitgetEngine
from .oanda import OandaEngine, FOREX_DATABASE

PLATFORMS = {c.key: c for c in (BybitEngine, BinanceEngine, OkxEngine, BitgetEngine, OandaEngine)}


def get_engine(platform, creds=None, testnet=True):
    if platform not in PLATFORMS:
        raise ValueError(f"Unknown platform: {platform}")
    return PLATFORMS[platform](creds or {}, testnet)
