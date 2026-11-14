"""
OANDA v20 (forex + gold). Official REST API, practice (demo) account free.
Credentials: api_key = OANDA personal access token, account_id = 101-001-xxxxxxx-001
Symbol format: EUR_USD, GBP_USD, USD_JPY, XAU_USD ...

Shimabaddhota (ekhon):
  * Account currency USD hote hobe.
  * Shudhu USD er sathe pair (EUR_USD, USD_JPY, XAU_USD ...). Cross pair (EUR_GBP) e margin->units hishab ekhono nai.
  * OANDA te leverage account-level (API diye set kora jay na). 'leverage' ekhane shudhu units calculate korte lage.
  * TP/SL gap = price unit (EUR_USD te 0.0020 = 20 pip).
"""
import time
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

import pandas as pd
import requests

from .base import BaseEngine


def _dec(x):
    return Decimal(str(x))


def _fmt(d):
    return format(d, "f")


FOREX_DATABASE = {
    "💶 EUR/USD":  {"symbol": "EUR_USD", "max_leverage": 30, "default_tp": 0.0020, "default_sl": 0.0030, "step": 0.0001},
    "💷 GBP/USD":  {"symbol": "GBP_USD", "max_leverage": 30, "default_tp": 0.0025, "default_sl": 0.0035, "step": 0.0001},
    "🦘 AUD/USD":  {"symbol": "AUD_USD", "max_leverage": 30, "default_tp": 0.0015, "default_sl": 0.0025, "step": 0.0001},
    "🥝 NZD/USD":  {"symbol": "NZD_USD", "max_leverage": 30, "default_tp": 0.0015, "default_sl": 0.0025, "step": 0.0001},
    "💴 USD/JPY":  {"symbol": "USD_JPY", "max_leverage": 30, "default_tp": 0.20, "default_sl": 0.30, "step": 0.01},
    "🍁 USD/CAD":  {"symbol": "USD_CAD", "max_leverage": 30, "default_tp": 0.0020, "default_sl": 0.0030, "step": 0.0001},
    "🇨🇭 USD/CHF": {"symbol": "USD_CHF", "max_leverage": 30, "default_tp": 0.0020, "default_sl": 0.0030, "step": 0.0001},
    "🥇 XAU/USD (Gold)": {"symbol": "XAU_USD", "max_leverage": 20, "default_tp": 3.0, "default_sl": 5.0, "step": 0.01},
}


class OandaEngine(BaseEngine):
    key = "oanda"
    label = "OANDA (Forex / Gold)"
    market = "forex"
    has_testnet = True
    testnet_label = "OANDA PRACTICE (demo account)"
    fields = (("api_key", "OANDA API Token", True, True), ("account_id", "OANDA Account ID (101-001-...)", False, True))
    fee_roundtrip = 0.0      # commission nai, spread ache (price e-i dhora)

    def __init__(self, creds, testnet=True):
        super().__init__(creds, testnet)
        self.base = "https://api-fxpractice.oanda.com" if self.testnet else "https://api-fxtrade.oanda.com"
        self.token = self.creds.get("api_key", "")
        self.acct = (self.creds.get("account_id") or "").strip()
        self._inst = {}

    # ------------------------------------------------------------- http
    def _req(self, method, path, **kw):
        if not self.token or not self.acct:
            raise RuntimeError("OANDA token + account id lagbe")
        h = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
             "Accept-Datetime-Format": "UNIX"}
        r = requests.request(method, self.base + path, headers=h, timeout=12, **kw)
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code >= 400:
            raise RuntimeError(f"OANDA {r.status_code}: {data.get('errorMessage') or r.text[:200]}")
        return data

    def _a(self, tail=""):
        return f"/v3/accounts/{self.acct}{tail}"

    # ----------------------------------------------------------- wallet
    def wallet(self):
        a = self._req("GET", self._a("/summary"))["account"]
        self.ccy = a.get("currency", "USD")
        return {"equity": float(a.get("NAV") or 0), "available": float(a.get("marginAvailable") or 0),
                "usdt_wallet": float(a.get("balance") or 0), "account_type": f"OANDA {self.ccy}",
                "raw": {"coins_returned": [self.ccy], "currency": self.ccy,
                        "unrealizedPL": a.get("unrealizedPL"), "marginUsed": a.get("marginUsed"),
                        "openTradeCount": a.get("openTradeCount")}}

    # ------------------------------------------------------ market data
    def _instrument(self, symbol):
        if symbol in self._inst:
            return self._inst[symbol]
        d = self._req("GET", self._a("/instruments"), params={"instruments": symbol})
        lst = d.get("instruments") or []
        if not lst:
            raise ValueError(f"{symbol} OANDA te paoa jay nai")
        i = lst[0]
        info = {"price_prec": int(i.get("displayPrecision", 5)), "units_prec": int(i.get("tradeUnitsPrecision", 0)),
                "min_units": _dec(i.get("minimumTradeSize", "1")), "margin_rate": _dec(i.get("marginRate", "0.02"))}
        self._inst[symbol] = info
        return info

    def _quote(self, symbol):
        d = self._req("GET", self._a("/pricing"), params={"instruments": symbol})
        p = d["prices"][0]
        bid, ask = _dec(p["bids"][0]["price"]), _dec(p["asks"][0]["price"])
        return bid, ask

    def price(self, symbol):
        bid, ask = self._quote(symbol)
        return float((bid + ask) / 2)

    def klines(self, symbol, limit=30):
        d = requests.get(self.base + f"/v3/instruments/{symbol}/candles",
                         headers={"Authorization": f"Bearer {self.token}", "Accept-Datetime-Format": "UNIX"},
                         params={"granularity": "M1", "count": limit, "price": "M"}, timeout=12).json()
        rows = [{"time": float(c["time"]) * 1000, "open": float(c["mid"]["o"]), "high": float(c["mid"]["h"]),
                 "low": float(c["mid"]["l"]), "close": float(c["mid"]["c"]), "volume": float(c.get("volume", 0))}
                for c in d.get("candles", []) if c.get("mid")]
        return pd.DataFrame(rows)

    # --------------------------------------------------------- position
    def get_position(self, symbol):
        try:
            p = self._req("GET", self._a(f"/positions/{symbol}"))["position"]
        except RuntimeError as e:
            if " 404" in str(e):
                return None
            raise
        lg, sh = p.get("long", {}), p.get("short", {})
        lu, su = float(lg.get("units") or 0), float(sh.get("units") or 0)
        if lu > 0:
            return {"side": "LONG", "size": lu, "size_raw": lg["units"], "entry_price": float(lg.get("averagePrice") or 0),
                    "unrealised_pnl": float(lg.get("unrealizedPL") or 0), "take_profit": None, "stop_loss": None}
        if su < 0:
            return {"side": "SHORT", "size": abs(su), "size_raw": sh["units"], "entry_price": float(sh.get("averagePrice") or 0),
                    "unrealised_pnl": float(sh.get("unrealizedPL") or 0), "take_profit": None, "stop_loss": None}
        return None

    def open_position(self, symbol, side, margin_usd, leverage, tp_gap, sl_gap):
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise ValueError("side LONG ba SHORT hote hobe")
        if self.get_position(symbol):
            raise RuntimeError(f"{symbol} e OANDA te agei position khola ache")
        w = self.wallet()
        if self.ccy != "USD":
            raise ValueError(f"OANDA account currency {self.ccy}. Ekhon shudhu USD account support kore.")
        base, quote = symbol.split("_")
        if quote != "USD" and base != "USD":
            raise ValueError(f"{symbol}: ekhon shudhu USD er sathe pair support kore (EUR_USD, USD_JPY, XAU_USD ...).")

        inst = self._instrument(symbol)
        max_lev = int(1 / inst["margin_rate"])
        lev = max(1, min(int(leverage), max_lev))
        bid, ask = self._quote(symbol)
        ref = ask if side == "LONG" else bid
        mid = (bid + ask) / 2

        sl_frac, tp_frac, liq_frac = _dec(sl_gap) / mid, _dec(tp_gap) / mid, _dec("0.5") / lev
        if sl_frac >= liq_frac:
            raise ValueError(f"SL gap {float(sl_frac)*100:.2f}% > margin-closeout distance ~{float(liq_frac)*100:.2f}% ({lev}x). Leverage komao ba SL chhoto koro.")
        if tp_frac >= _dec("0.2"):
            raise ValueError(f"TP gap price er {float(tp_frac)*100:.0f}% - forex e onek boro, TP thik koro.")

        notional = _dec(margin_usd) * lev                      # USD
        units = notional if base == "USD" else notional / mid  # base currency units
        q = Decimal(1).scaleb(-inst["units_prec"])
        units = units.quantize(q, rounding=ROUND_DOWN)
        if units < inst["min_units"]:
            raise ValueError(f"Units {units} < minimum {inst['min_units']}. Margin ba leverage barao.")
        need = units * mid * inst["margin_rate"]
        if need > _dec(w["available"]):
            raise ValueError(f"Margin lagbe ~${need:.2f}, available ${w['available']:.2f}.")

        sgn = 1 if side == "LONG" else -1
        pq = Decimal(1).scaleb(-inst["price_prec"])
        tp = (ref + sgn * _dec(tp_gap)).quantize(pq, rounding=ROUND_HALF_UP)
        sl = (ref - sgn * _dec(sl_gap)).quantize(pq, rounding=ROUND_HALF_UP)
        if tp <= 0 or sl <= 0:
            raise ValueError("TP/SL gap onek boro, price negative hoye jacche.")

        body = {"order": {
            "type": "MARKET", "instrument": symbol, "units": _fmt(units * sgn), "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "takeProfitOnFill": {"price": _fmt(tp), "timeInForce": "GTC"},
            "stopLossOnFill": {"price": _fmt(sl), "timeInForce": "GTC"},
        }}
        d = self._req("POST", self._a("/orders"), json=body)
        if "orderCancelTransaction" in d or "orderFillTransaction" not in d:
            why = (d.get("orderCancelTransaction") or d.get("orderRejectTransaction") or {}).get("reason", "unknown")
            raise RuntimeError(f"OANDA order cancel hoyeche: {why}")
        fill = d["orderFillTransaction"]
        entry = float(fill.get("price") or ref)
        return {"symbol": symbol, "side": side, "qty": float(units), "leverage": lev,
                "entry_price": entry, "tp_price": float(tp), "sl_price": float(sl), "confirmed": True}

    def close_position(self, symbol):
        pos = self.get_position(symbol)
        if not pos:
            return None
        body = {"longUnits": "ALL"} if pos["side"] == "LONG" else {"shortUnits": "ALL"}
        self._req("PUT", self._a(f"/positions/{symbol}/close"), json=body)   # attached TP/SL auto cancel hoy
        return pos

    def last_closed_pnl(self, symbol, since_ms=0):
        d = self._req("GET", self._a("/trades"), params={"state": "CLOSED", "instrument": symbol, "count": 20})
        pnl, entry, exit_, t_last, n = 0.0, 0.0, 0.0, 0, 0
        for t in d.get("trades", []):
            ct = int(float(t.get("closeTime") or 0) * 1000)
            if ct < int(since_ms) - 5000:
                continue
            pnl += float(t.get("realizedPL") or 0) + float(t.get("financing") or 0) + float(t.get("commission") or 0)
            if ct >= t_last:
                t_last, entry, exit_ = ct, float(t.get("price") or 0), float(t.get("averageClosePrice") or 0)
            n += 1
        return {"pnl": pnl, "entry": entry, "exit": exit_, "time": t_last} if n else None
