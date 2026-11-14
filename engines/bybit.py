"""Bybit: tomar ager bybit_engine.py ke-i use kore (oita bodlai nai), shudhu common interface e mura holo."""
import pandas as pd
import requests

from bybit_engine import BybitEngine as _Core
from .base import BaseEngine


class BybitEngine(_Core, BaseEngine):
    key = "bybit"
    label = "Bybit (USDT Perpetual)"
    market = "crypto"
    has_testnet = True
    testnet_label = "Bybit TESTNET"
    fields = (("api_key", "Bybit API Key", True, True), ("api_secret", "Bybit Secret Key", True, True))
    fee_roundtrip = 0.0011   # taker 0.055% x 2

    def __init__(self, creds, testnet=True):
        BaseEngine.__init__(self, creds, testnet)
        _Core.__init__(self, (creds or {}).get("api_key") or None, (creds or {}).get("api_secret") or None, testnet=testnet)

    @classmethod
    def live_symbols(cls, testnet):
        if not testnet:
            return None    # mainnet e ager moto puro list
        r = requests.get("https://api-testnet.bybit.com/v5/market/instruments-info?category=linear&limit=1000", timeout=10).json()
        return {i["symbol"] for i in r.get("result", {}).get("list", [])
                if i.get("status") == "Trading" and i.get("quoteCoin") == "USDT"}

    def price(self, symbol):
        return self.last_price(symbol)

    def klines(self, symbol, limit=30):
        r = self.session.get_kline(category="linear", symbol=symbol, interval="1", limit=limit)
        rows = r.get("result", {}).get("list", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume", "turnover"]).iloc[::-1].reset_index(drop=True)
        for c in ("open", "high", "low", "close", "volume"):
            df[c] = pd.to_numeric(df[c])
        return df[["time", "open", "high", "low", "close", "volume"]]
