"""
Generic crypto futures engine (ccxt diye): Binance USDM, OKX, Bitget.
Internal symbol format sob jaygay 'BTCUSDT'; ekhane ccxt format 'BTC/USDT:USDT' e convert hoy.
"""
import time
from decimal import Decimal

import pandas as pd

from .base import BaseEngine

try:
    import ccxt
except Exception:      # ccxt install na thakle shudhu ei engine gulo kaj korbe na, baki app cholbe
    ccxt = None

_EX_CACHE = {}         # (ccxt_id, testnet, apiKey) -> exchange (markets ekbar load hoy, protibar na)
_PNL_KEYS = ("realizedPnl", "fillPnl", "profit", "pnl", "closedPnl")


def _dec(x):
    return Decimal(str(x))


def _to_ccxt(symbol):
    if symbol.endswith("USDT"):
        return f"{symbol[:-4]}/USDT:USDT"
    return symbol


class CcxtEngine(BaseEngine):
    market = "crypto"
    ccxt_id = ""
    tpsl_mode = "attached"       # "attached": order er sathe TP/SL (OKX, Bitget) | "separate": alada reduce-only trigger order (Binance)
    margin_params = {}           # set_leverage er extra params

    def __init__(self, creds, testnet=True):
        super().__init__(creds, testnet)
        if ccxt is None:
            raise RuntimeError("ccxt install kora nai. requirements.txt e 'ccxt' add koro.")
        ck = (self.ccxt_id, self.testnet, self.creds.get("api_key", ""))
        ex = _EX_CACHE.get(ck)
        if ex is None:
            cfg = {"enableRateLimit": True, "timeout": 15000, "options": {"defaultType": "swap"}}
            if self.creds.get("api_key"):
                cfg["apiKey"], cfg["secret"] = self.creds["api_key"], self.creds.get("api_secret", "")
            if self.creds.get("passphrase"):
                cfg["password"] = self.creds["passphrase"]
            ex = getattr(ccxt, self.ccxt_id)(cfg)
            if self.testnet:
                ex.set_sandbox_mode(True)
            ex.load_markets()
            _EX_CACHE[ck] = ex
        self.ex = ex

    # ----------------------------------------------------------- helpers
    def _sym(self, symbol):
        s = _to_ccxt(symbol)
        if s not in self.ex.markets:
            raise ValueError(f"{symbol} {self.label} e paoa jay nai ({'testnet' if self.testnet else 'mainnet'}). Onno coin nao.")
        return s

    @classmethod
    def live_symbols(cls, testnet):
        e = cls({}, testnet)
        return {m["base"] + "USDT" for m in e.ex.markets.values()
                if m.get("swap") and m.get("linear") and m.get("quote") == "USDT" and m.get("active") is not False}

    # ------------------------------------------------------- market data
    def price(self, symbol):
        return float(self.ex.fetch_ticker(self._sym(symbol))["last"])

    def klines(self, symbol, limit=30):
        rows = self.ex.fetch_ohlcv(self._sym(symbol), "1m", limit=limit)
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows, columns=["time", "open", "high", "low", "close", "volume"]).astype(float)

    # ------------------------------------------------------------ wallet
    def wallet(self):
        bal = self.ex.fetch_balance()
        u = bal.get("USDT") or {}
        total = float(u.get("total") or 0)
        free = float(u.get("free") or 0)
        return {"equity": total, "available": free, "usdt_wallet": total,
                "account_type": f"{self.key} futures",
                "raw": {"coins_returned": [c for c, v in bal.items() if isinstance(v, dict) and (v.get("total") or 0) > 0]}}

    # ---------------------------------------------------------- position
    def get_position(self, symbol):
        sym = self._sym(symbol)
        for p in self.ex.fetch_positions([sym]):
            size = float(p.get("contracts") or 0)
            if size > 0:
                return {
                    "side": "LONG" if p.get("side") == "long" else "SHORT",
                    "size": size, "size_raw": size,
                    "entry_price": float(p.get("entryPrice") or 0),
                    "unrealised_pnl": float(p.get("unrealizedPnl") or 0),
                    "take_profit": None, "stop_loss": None,
                }
        self._cleanup_orders(sym)
        return None

    def _cleanup_orders(self, sym):
        """Position nai, kintu TP/SL er onno ta (separate mode e) theke gele seta cancel kore."""
        if self.tpsl_mode != "separate":
            return
        try:
            for o in self.ex.fetch_open_orders(sym):
                if o.get("reduceOnly"):
                    try:
                        self.ex.cancel_order(o["id"], sym)
                    except Exception:
                        pass
        except Exception:
            pass

    def _set_account(self, sym, lev):
        try:
            self.ex.set_position_mode(False, sym)     # one-way mode
        except Exception:
            pass
        try:
            self.ex.set_leverage(lev, sym, dict(self.margin_params))
        except Exception as e:
            m = str(e).lower()
            if "not modified" in m or "no need" in m or "same" in m:
                return
            raise

    def open_position(self, symbol, side, margin_usd, leverage, tp_gap, sl_gap):
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise ValueError("side LONG ba SHORT hote hobe")
        sym = self._sym(symbol)
        if self.get_position(symbol):
            raise RuntimeError(f"{symbol} e {self.label} e agei position khola ache")

        mk = self.ex.market(sym)
        max_lev = (((mk.get("limits") or {}).get("leverage") or {}).get("max")) or 125
        lev = max(1, min(int(leverage), int(max_lev)))

        price = _dec(self.price(symbol))
        sl_frac, tp_frac, liq_frac = _dec(sl_gap) / price, _dec(tp_gap) / price, _dec("0.8") / lev
        if sl_frac >= liq_frac:
            raise ValueError(f"SL gap {float(sl_frac)*100:.2f}% > liquidation distance ~{float(liq_frac)*100:.2f}% ({lev}x). Leverage komao ba SL chhoto koro.")
        if tp_frac >= _dec("0.5"):
            raise ValueError(f"TP gap price er {float(tp_frac)*100:.0f}% - onek boro, TP thik koro.")

        self._set_account(sym, lev)

        csize = _dec(mk.get("contractSize") or 1)
        coins = _dec(margin_usd) * lev / price
        qty = _dec(self.ex.amount_to_precision(sym, float(coins / csize)))
        lim = mk.get("limits") or {}
        min_amt = ((lim.get("amount") or {}).get("min")) or 0
        min_cost = ((lim.get("cost") or {}).get("min")) or 0
        if qty <= 0 or qty < _dec(min_amt):
            raise ValueError(f"Qty {qty} < minimum {min_amt}. Margin ba leverage barao.")
        if min_cost and qty * csize * price < _dec(min_cost):
            raise ValueError(f"Order value ${qty * csize * price:.2f} < minimum ${min_cost}. Margin barao.")

        sgn = 1 if side == "LONG" else -1
        tp = _dec(self.ex.price_to_precision(sym, float(price + sgn * _dec(tp_gap))))
        sl = _dec(self.ex.price_to_precision(sym, float(price - sgn * _dec(sl_gap))))
        if tp <= 0 or sl <= 0:
            raise ValueError("TP/SL gap onek boro, price negative hoye jacche.")

        o_side, c_side = ("buy", "sell") if side == "LONG" else ("sell", "buy")
        amt = float(qty)
        if self.tpsl_mode == "attached":
            self.ex.create_order(sym, "market", o_side, amt, None, {
                "takeProfit": {"triggerPrice": float(tp)}, "stopLoss": {"triggerPrice": float(sl)}})
        else:
            self.ex.create_order(sym, "market", o_side, amt)
            try:     # SL age: SL na bosle position khola rakha jabe na
                self.ex.create_order(sym, "market", c_side, amt, None, {"stopLossPrice": float(sl), "reduceOnly": True})
                self.ex.create_order(sym, "market", c_side, amt, None, {"takeProfitPrice": float(tp), "reduceOnly": True})
            except Exception as e:
                try:
                    self.ex.create_order(sym, "market", c_side, amt, None, {"reduceOnly": True})
                    self._cleanup_orders(sym)
                    closed = "tai position bondho kore dewa holo"
                except Exception as ce:
                    closed = f"ABAR position bondho korte parlam na ({ce}) - EKHUNI exchange e giye nijer haate bondho koro"
                raise RuntimeError(f"TP/SL boshano gelo na ({e}); {closed}")

        entry, confirmed = float(price), False
        for _ in range(6):
            time.sleep(0.5)
            p = self.get_position(symbol)
            if p:
                entry, confirmed = p["entry_price"], True
                break
        return {"symbol": symbol, "side": side, "qty": float(qty * csize), "leverage": lev,
                "entry_price": entry, "tp_price": float(tp), "sl_price": float(sl), "confirmed": confirmed}

    def close_position(self, symbol):
        sym = self._sym(symbol)
        pos = self.get_position(symbol)
        if not pos:
            return None
        self.ex.create_order(sym, "market", "sell" if pos["side"] == "LONG" else "buy",
                             pos["size_raw"], None, {"reduceOnly": True})
        self._cleanup_orders(sym)
        return pos

    def last_closed_pnl(self, symbol, since_ms=0):
        """since_ms er por fill gulo theke net PnL (exchange er realized pnl - fee). Closing fill na paole None."""
        sym = self._sym(symbol)
        trades = self.ex.fetch_my_trades(sym, since=max(int(since_ms) - 5000, 0), limit=100)
        pnl = fees = 0.0
        opens, closes = [], []
        for t in trades:
            info = t.get("info") or {}
            rp = 0.0
            for k in _PNL_KEYS:
                if info.get(k) not in (None, ""):
                    try:
                        rp = float(info[k]); break
                    except (TypeError, ValueError):
                        pass
            fee = t.get("fee") or {}
            fees += abs(float(fee.get("cost") or 0))
            pnl += rp
            (closes if rp != 0 else opens).append((float(t["price"]), float(t["amount"])))
        if not closes:
            return None
        vw = lambda xs: sum(p * a for p, a in xs) / sum(a for _, a in xs) if xs else 0.0
        return {"pnl": pnl - fees, "entry": vw(opens), "exit": vw(closes), "time": int(trades[-1].get("timestamp") or 0)}


class BinanceEngine(CcxtEngine):
    key, label, ccxt_id = "binance", "Binance (USDT-M Futures)", "binanceusdm"
    testnet_label = "Binance Futures TESTNET"
    tpsl_mode = "separate"
    fee_roundtrip = 0.0009        # taker 0.04% x 2 + slippage


class OkxEngine(CcxtEngine):
    key, label, ccxt_id = "okx", "OKX (USDT Swap)", "okx"
    testnet_label = "OKX DEMO trading"
    tpsl_mode = "attached"
    margin_params = {"marginMode": "cross"}
    fields = (("api_key", "OKX API Key", True, True), ("api_secret", "OKX Secret Key", True, True),
              ("passphrase", "OKX API Passphrase", True, True))
    fee_roundtrip = 0.0010


class BitgetEngine(CcxtEngine):
    key, label, ccxt_id = "bitget", "Bitget (USDT Futures)", "bitget"
    has_testnet = False           # Bitget e ccxt sandbox symbol alada (SBTCSUSDT), tai ekhane mainnet only
    tpsl_mode = "attached"
    fields = (("api_key", "Bitget API Key", True, True), ("api_secret", "Bitget Secret Key", True, True),
              ("passphrase", "Bitget API Passphrase", True, True))
    fee_roundtrip = 0.0012
