"""
exchanges.py  -  Multi-exchange layer (Bybit / Binance Futures / OANDA Forex)

Duto alada jinish:
  * XxxData   : price + candle (key lage na, shudhu OANDA te token lage)
  * XxxEngine : asol account e kaj (wallet, order, position, close, PnL)

Sob Engine e ek-i method: wallet(), get_position(sym), open_position(...),
close_position(sym), last_closed_pnl(sym, since_ms), after_close(sym)
"""
import hashlib
import hmac
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode

import requests

from bybit_engine import BybitEngine, _dec, _fmt, _round_step
from pybit.unified_trading import HTTP

EXCHANGES = ["Bybit (Crypto)", "Binance (Crypto)", "OANDA (Forex)"]
EXCHANGE_IDS = {"Bybit (Crypto)": "bybit", "Binance (Crypto)": "binance", "OANDA (Forex)": "oanda"}
EXCHANGE_NAMES = {"bybit": "Bybit", "binance": "Binance", "oanda": "OANDA"}

BINANCE_MAIN = "https://fapi.binance.com"
BINANCE_TEST = "https://testnet.binancefuture.com"
OANDA_PRACTICE = "https://api-fxpractice.oanda.com"
OANDA_LIVE = "https://api-fxtrade.oanda.com"

# OANDA: shudhu USD pair (P&L USD te hishab kora shohoj). TP/SL = price unit e.
OANDA_MAJORS = {
    "💶 EUR/USD (OANDA Forex)": {"symbol": "EUR_USD", "max_leverage": 30, "default_tp": 0.0010, "default_sl": 0.0007, "step": 0.00001},
    "💷 GBP/USD (OANDA Forex)": {"symbol": "GBP_USD", "max_leverage": 30, "default_tp": 0.0012, "default_sl": 0.0008, "step": 0.00001},
    "🦘 AUD/USD (OANDA Forex)": {"symbol": "AUD_USD", "max_leverage": 30, "default_tp": 0.0008, "default_sl": 0.0006, "step": 0.00001},
    "🥝 NZD/USD (OANDA Forex)": {"symbol": "NZD_USD", "max_leverage": 30, "default_tp": 0.0008, "default_sl": 0.0006, "step": 0.00001},
    "💴 USD/JPY (OANDA Forex)": {"symbol": "USD_JPY", "max_leverage": 30, "default_tp": 0.10, "default_sl": 0.07, "step": 0.001},
    "🍁 USD/CAD (OANDA Forex)": {"symbol": "USD_CAD", "max_leverage": 30, "default_tp": 0.0010, "default_sl": 0.0007, "step": 0.00001},
    "🇨🇭 USD/CHF (OANDA Forex)": {"symbol": "USD_CHF", "max_leverage": 30, "default_tp": 0.0008, "default_sl": 0.0006, "step": 0.00001},
    "🥇 XAU/USD Gold (OANDA)": {"symbol": "XAU_USD", "max_leverage": 20, "default_tp": 3.0, "default_sl": 2.0, "step": 0.01},
}


def _first_num(*vals):
    for v in vals:
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return 0.0


def _guards(price, tp_gap, sl_gap, lev):
    """Sob exchange e ek-i safety: SL liquidation er age, TP onek boro na."""
    sl_frac, tp_frac, liq_frac = _dec(sl_gap) / price, _dec(tp_gap) / price, _dec("0.8") / lev
    if sl_frac >= liq_frac:
        raise ValueError(f"SL gap {float(sl_frac)*100:.2f}% > liquidation distance ~{float(liq_frac)*100:.2f}% ({lev}x). SL trigger hobar age-i liquidate hobe. Leverage komao ba SL chhoto koro.")
    if tp_frac >= _dec("0.5"):
        raise ValueError(f"TP gap price er {float(tp_frac)*100:.0f}% - onek boro, TP thik koro (price {float(price):g}).")


def _iso_ms(s):
    """OANDA RFC3339 ('2026-11-11T20:49:00.123456789Z') ba unix string -> ms"""
    s = str(s)
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return int(float(s) * 1000)
    m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(?:\.(\d+))?", s)
    if not m:
        return 0
    dt = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000) + int((m.group(3) or "0")[:3].ljust(3, "0"))


# =====================================================================
#  BYBIT (public data; trading = bybit_engine.BybitEngine)
# =====================================================================
class BybitData:
    def __init__(self, testnet=False):
        self.session = HTTP(testnet=bool(testnet))
        self.tradeable = True

    def last_price(self, symbol):
        lst = self.session.get_tickers(category="linear", symbol=symbol).get("result", {}).get("list", [])
        if not lst:
            raise RuntimeError(f"{symbol} ticker paoa jay nai")
        return float(lst[0]["lastPrice"])

    def klines(self, symbol, limit=30):
        rows = self.session.get_kline(category="linear", symbol=symbol, interval="1", limit=limit).get("result", {}).get("list", [])
        return [[int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in reversed(rows)]   # oldest -> newest

    def cost_frac(self, symbol, price):
        return 0.0011   # taker 0.055% x 2


# =====================================================================
#  BINANCE USDT-M FUTURES
# =====================================================================
class BinanceData:
    def __init__(self, testnet=False):
        self.testnet = bool(testnet)
        self.base = BINANCE_TEST if self.testnet else BINANCE_MAIN
        self.tradeable = True

    def _get(self, path, params=None):
        r = requests.get(self.base + path, params=params, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"Binance {path} HTTP {r.status_code}: {r.text[:200]}")
        return r.json()

    def last_price(self, symbol):
        return float(self._get("/fapi/v1/ticker/price", {"symbol": symbol})["price"])

    def klines(self, symbol, limit=30):
        rows = self._get("/fapi/v1/klines", {"symbol": symbol, "interval": "1m", "limit": limit})
        return [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])] for r in rows]

    def cost_frac(self, symbol, price):
        return 0.0010   # taker 0.05% x 2

    def coins(self, top=60):
        """Volume onujayi top USDT perpetual. TP/SL default = price er 0.5% / 0.3%."""
        ticks = {}
        for s in self._get("/fapi/v1/exchangeInfo").get("symbols", []):
            if s.get("status") == "TRADING" and s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT":
                tick = next((f["tickSize"] for f in s.get("filters", []) if f.get("filterType") == "PRICE_FILTER"), None)
                if tick:
                    ticks[s["symbol"]] = (s.get("baseAsset", s["symbol"]), float(tick))
        rows = []
        for x in self._get("/fapi/v1/ticker/24hr"):
            if x.get("symbol") in ticks:
                rows.append((x["symbol"], _first_num(x.get("quoteVolume")), _first_num(x.get("lastPrice"))))
        rows.sort(key=lambda r: -r[1])
        out = {}
        for sym, _vol, price in rows[:top]:
            base, tick = ticks[sym]
            t = _dec(tick)
            tp = max(float((_dec(price * 0.005) / t).to_integral_value(ROUND_HALF_UP) * t), tick * 2)
            sl = max(float((_dec(price * 0.003) / t).to_integral_value(ROUND_HALF_UP) * t), tick * 2)
            out[f"🪙 {base} (Binance Futures)"] = {"symbol": sym, "max_leverage": 50, "default_tp": tp, "default_sl": sl, "step": tick}
        if not out:
            raise RuntimeError("Binance e kono USDT perpetual paoa jay nai")
        return out


class BinanceEngine:
    def __init__(self, api_key, api_secret, testnet=True):
        self.testnet = bool(testnet)
        self.base = BINANCE_TEST if self.testnet else BINANCE_MAIN
        self.key, self.secret = api_key.strip(), api_secret.strip()
        self._inst = {}
        self._offset = 0

    # ---------------------------------------------------------------- http
    def _sync_time(self):
        r = requests.get(self.base + "/fapi/v1/time", timeout=10)
        self._offset = int(r.json()["serverTime"]) - int(time.time() * 1000)

    def _call(self, method, path, params=None, signed=True):
        for attempt in (0, 1):
            p = dict(params or {})
            if signed:
                p["timestamp"] = int(time.time() * 1000) + self._offset
                p["recvWindow"] = 10000
            qs = urlencode(p)
            if signed:
                qs += "&signature=" + hmac.new(self.secret.encode(), qs.encode(), hashlib.sha256).hexdigest()
            r = requests.request(method, f"{self.base}{path}?{qs}", headers={"X-MBX-APIKEY": self.key}, timeout=10)
            if r.status_code == 200:
                return r.json()
            if attempt == 0 and '"code":-1021' in r.text:   # clock mismatch
                self._sync_time()
                continue
            raise RuntimeError(f"Binance {path} HTTP {r.status_code}: {r.text[:220]}")

    def _try_paths(self, method, paths, params=None):
        last = None
        for pth in paths:
            try:
                return self._call(method, pth, params)
            except Exception as e:
                last = e
        raise RuntimeError(f"{last}")

    # -------------------------------------------------------------- wallet
    def wallet(self):
        a = self._try_paths("GET", ("/fapi/v3/account", "/fapi/v2/account"))
        usdt = next((x for x in a.get("assets", []) if x.get("asset") == "USDT"), {})
        raw = {k: a.get(k) for k in ("totalWalletBalance", "totalUnrealizedProfit", "totalMarginBalance", "availableBalance", "canTrade") if k in a}
        raw["USDT"] = usdt
        raw["coins_returned"] = [x.get("asset") for x in a.get("assets", []) if _first_num(x.get("walletBalance")) != 0]
        raw["accountTypeQueried"] = "BINANCE_USDM_FUTURES" + (" (testnet)" if self.testnet else "")
        return {
            "equity": _first_num(a.get("totalMarginBalance"), a.get("totalWalletBalance"), usdt.get("marginBalance"), usdt.get("walletBalance")),
            "available": _first_num(a.get("availableBalance"), usdt.get("availableBalance")),
            "usdt_wallet": _first_num(usdt.get("walletBalance")),
            "account_type": "BINANCE_USDM", "raw": raw,
        }

    # ---------------------------------------------------------- market info
    def _instrument(self, symbol):
        if not self._inst:
            for s in self._call("GET", "/fapi/v1/exchangeInfo", signed=False).get("symbols", []):
                f = {x["filterType"]: x for x in s.get("filters", [])}
                lot = f.get("MARKET_LOT_SIZE") or f.get("LOT_SIZE") or {}
                mn = f.get("MIN_NOTIONAL", {})
                self._inst[s["symbol"]] = {
                    "status": s.get("status"), "qty_step": lot.get("stepSize", "0.001"), "min_qty": lot.get("minQty", "0.001"),
                    "tick": f.get("PRICE_FILTER", {}).get("tickSize", "0.01"), "min_notional": mn.get("notional") or mn.get("minNotional") or "5",
                }
        it = self._inst.get(symbol)
        if not it:
            raise ValueError(f"{symbol} Binance e paoa jay nai ({'testnet' if self.testnet else 'mainnet'})")
        if it["status"] != "TRADING":
            raise ValueError(f"{symbol} ekhon live na (status: {it['status']}). Onno coin nao.")
        return it

    def last_price(self, symbol):
        return float(self._call("GET", "/fapi/v1/ticker/price", {"symbol": symbol}, signed=False)["price"])

    # ------------------------------------------------------------- position
    def get_position(self, symbol):
        rows = self._try_paths("GET", ("/fapi/v3/positionRisk", "/fapi/v2/positionRisk"), {"symbol": symbol})
        for p in rows:
            amt = _first_num(p.get("positionAmt"))
            if amt != 0:
                return {
                    "side": "LONG" if amt > 0 else "SHORT", "size": abs(amt), "size_raw": str(p["positionAmt"]).lstrip("-"),
                    "entry_price": _first_num(p.get("entryPrice")),
                    "unrealised_pnl": _first_num(p.get("unRealizedProfit"), p.get("unrealizedProfit")),
                    "take_profit": None, "stop_loss": None,
                }
        return None

    def _set_leverage(self, symbol, lev):
        self._call("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": int(lev)})

    def _conditional(self, symbol, side, otype, trigger):
        """TP/SL (exit-only, poorata close). Binance conditional order API bodle geche, tai duto-i try kori."""
        errs = []
        attempts = (
            ("/fapi/v1/order", {"symbol": symbol, "side": side, "type": otype, "stopPrice": _fmt(trigger), "closePosition": "true", "workingType": "MARK_PRICE"}),
            ("/fapi/v1/algoOrder", {"algoType": "CONDITIONAL", "symbol": symbol, "side": side, "type": otype, "triggerPrice": _fmt(trigger), "closePosition": "true", "workingType": "MARK_PRICE"}),
        )
        for path, params in attempts:
            try:
                return self._call("POST", path, params)
            except Exception as e:
                errs.append(str(e)[:160])
        raise RuntimeError(" | ".join(errs))

    def after_close(self, symbol):
        """Position bondho hole baki TP/SL order gulo batil (best effort)."""
        for path in ("/fapi/v1/allOpenOrders", "/fapi/v1/algoOpenOrders"):
            try:
                self._call("DELETE", path, {"symbol": symbol})
            except Exception:
                pass

    def open_position(self, symbol, side, margin_usd, leverage, tp_gap, sl_gap):
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise ValueError("side LONG ba SHORT hote hobe")
        if self.get_position(symbol):
            raise RuntimeError(f"{symbol} e Binance e agei position khola ache")
        inst = self._instrument(symbol)
        lev = max(1, min(int(leverage), 125))
        price = _dec(self.last_price(symbol))
        _guards(price, tp_gap, sl_gap, lev)
        qty = _round_step(_dec(margin_usd) * lev / price, inst["qty_step"])
        if qty < _dec(inst["min_qty"]):
            raise ValueError(f"Qty {qty} < minimum {inst['min_qty']}. Margin ba leverage barao.")
        if qty * price < _dec(inst["min_notional"]):
            raise ValueError(f"Order value ${qty * price:.2f} < minimum ${inst['min_notional']}. Margin barao.")
        long_ = side == "LONG"
        tp = _round_step(price + _dec(tp_gap) if long_ else price - _dec(tp_gap), inst["tick"], ROUND_HALF_UP)
        sl = _round_step(price - _dec(sl_gap) if long_ else price + _dec(sl_gap), inst["tick"], ROUND_HALF_UP)
        if tp <= 0 or sl <= 0:
            raise ValueError("TP/SL gap onek boro, price negative hoye jacche.")
        entry_side, exit_side = ("BUY", "SELL") if long_ else ("SELL", "BUY")

        opened_ms = int(time.time() * 1000)
        try:   # isolated margin: liquidation shudhu ei position er margin e shimito thake
            self._call("POST", "/fapi/v1/marginType", {"symbol": symbol, "marginType": "ISOLATED"})
        except Exception:
            pass
        self._set_leverage(symbol, lev)
        self._call("POST", "/fapi/v1/order", {"symbol": symbol, "side": entry_side, "type": "MARKET", "quantity": _fmt(qty), "newOrderRespType": "RESULT"})

        entry, confirmed = float(price), False
        for _ in range(6):
            time.sleep(0.4)
            p = self.get_position(symbol)
            if p:
                entry, confirmed = p["entry_price"], True
                break
        try:
            self._conditional(symbol, exit_side, "STOP_MARKET", sl)
            self._conditional(symbol, exit_side, "TAKE_PROFIT_MARKET", tp)
        except Exception as e:   # SL chhara position khola rakha jabe na
            try:
                self.close_position(symbol)
                self.after_close(symbol)
            except Exception as e2:
                raise RuntimeError(f"🚨 TP/SL boshano gelo na ({e}) ar position close o hoy nai ({e2}). Binance app e GIYE MANUAL CLOSE koro!")
            raise RuntimeError(f"TP/SL boshano gelo na, tai position niraponottar jonno close kora holo: {e}")
        return {"symbol": symbol, "side": side, "qty": float(qty), "leverage": lev, "entry_price": entry,
                "tp_price": float(tp), "sl_price": float(sl), "confirmed": confirmed, "opened_ms": opened_ms}

    def close_position(self, symbol):
        pos = self.get_position(symbol)
        if not pos:
            return None
        self._call("POST", "/fapi/v1/order", {"symbol": symbol, "side": "SELL" if pos["side"] == "LONG" else "BUY",
                                              "type": "MARKET", "quantity": pos["size_raw"], "reduceOnly": "true"})
        self.after_close(symbol)
        return pos

    def last_closed_pnl(self, symbol, since_ms=0):
        """since_ms er por: REALIZED_PNL + COMMISSION + FUNDING_FEE (net)."""
        rows = self._call("GET", "/fapi/v1/income", {"symbol": symbol, "startTime": max(int(since_ms) - 1000, 0), "limit": 100})
        net, found, tmax = 0.0, False, 0
        for r in rows:
            t = int(r.get("time", 0))
            if t < int(since_ms) - 1000:
                continue
            typ, val = r.get("incomeType"), _first_num(r.get("income"))
            if typ == "REALIZED_PNL":
                net, found = net + val, True
            elif typ in ("COMMISSION", "FUNDING_FEE"):
                net += val
            tmax = max(tmax, t)
        return {"pnl": net, "entry": 0.0, "exit": 0.0, "time": tmax} if found else None


# =====================================================================
#  OANDA (Forex)  -  v20 REST
# =====================================================================
class _OandaBase:
    def __init__(self, token, account_id, practice=True):
        self.practice = bool(practice)
        self.testnet = self.practice
        self.base = OANDA_PRACTICE if self.practice else OANDA_LIVE
        self.token, self.acct = token.strip(), account_id.strip()
        self.tradeable = True
        self.spread = 0.0

    def _req(self, method, path, body=None, params=None):
        r = requests.request(method, self.base + path, headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                             json=body, params=params, timeout=10)
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code >= 300:
            raise RuntimeError(f"OANDA {path} HTTP {r.status_code}: {data.get('errorMessage') or r.text[:200]}")
        return data

    def _quote(self, symbol):
        p = self._req("GET", f"/v3/accounts/{self.acct}/pricing", params={"instruments": symbol})["prices"][0]
        bid, ask = float(p["bids"][0]["price"]), float(p["asks"][0]["price"])
        self.tradeable, self.spread = bool(p.get("tradeable", True)), ask - bid
        return bid, ask, self.tradeable

    def last_price(self, symbol):
        bid, ask, _ = self._quote(symbol)
        return (bid + ask) / 2


class OandaData(_OandaBase):
    def klines(self, symbol, limit=30):
        cs = self._req("GET", f"/v3/instruments/{symbol}/candles", params={"count": limit, "granularity": "M1", "price": "M"}).get("candles", [])
        return [[_iso_ms(c["time"]), float(c["mid"]["o"]), float(c["mid"]["h"]), float(c["mid"]["l"]), float(c["mid"]["c"]), float(c.get("volume", 0))] for c in cs]

    def cost_frac(self, symbol, price):
        return (self.spread / price) if (price and self.spread > 0) else 0.0001   # forex e kharoch = spread (commission nei)


class OandaEngine(_OandaBase):
    def __init__(self, token, account_id, practice=True):
        super().__init__(token, account_id, practice)
        self._inst = {}

    def _summary(self):
        return self._req("GET", f"/v3/accounts/{self.acct}/summary")["account"]

    def wallet(self):
        a = self._summary()
        bal = _first_num(a.get("balance"))
        raw = {k: a.get(k) for k in ("alias", "currency", "balance", "NAV", "unrealizedPL", "marginAvailable", "marginRate", "openTradeCount") if k in a}
        raw["coins_returned"] = [a.get("currency")] if bal != 0 else []
        raw["API_KEY_INFO"] = {"userID": a.get("id", self.acct)}
        raw["accountTypeQueried"] = "OANDA " + ("PRACTICE" if self.practice else "LIVE")
        return {"equity": _first_num(a.get("NAV"), a.get("balance")), "available": _first_num(a.get("marginAvailable")),
                "usdt_wallet": bal, "account_type": f"OANDA {a.get('currency', '?')}", "raw": raw}

    def _instrument(self, symbol):
        if symbol not in self._inst:
            lst = self._req("GET", f"/v3/accounts/{self.acct}/instruments", params={"instruments": symbol}).get("instruments", [])
            if not lst:
                raise ValueError(f"{symbol} OANDA te paoa jay nai")
            self._inst[symbol] = lst[0]
        return self._inst[symbol]

    def get_position(self, symbol):
        try:
            pos = self._req("GET", f"/v3/accounts/{self.acct}/positions/{symbol}")["position"]
        except RuntimeError as e:
            if "HTTP 404" in str(e):
                return None
            raise
        lo, sh = pos.get("long", {}), pos.get("short", {})
        if _first_num(lo.get("units")) > 0:
            return {"side": "LONG", "size": float(lo["units"]), "size_raw": lo["units"], "entry_price": _first_num(lo.get("averagePrice")),
                    "unrealised_pnl": _first_num(lo.get("unrealizedPL")), "take_profit": None, "stop_loss": None}
        if _first_num(sh.get("units")) < 0:
            return {"side": "SHORT", "size": abs(float(sh["units"])), "size_raw": sh["units"], "entry_price": _first_num(sh.get("averagePrice")),
                    "unrealised_pnl": _first_num(sh.get("unrealizedPL")), "take_profit": None, "stop_loss": None}
        return None

    def after_close(self, symbol):
        return None   # OANDA te TP/SL trade er sathe-i bandha, alada order nei

    def open_position(self, symbol, side, margin_usd, leverage, tp_gap, sl_gap):
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise ValueError("side LONG ba SHORT hote hobe")
        base, quote = symbol.split("_")
        acct = self._summary()
        if acct.get("currency") != "USD":
            raise ValueError(f"OANDA account currency {acct.get('currency')} - ekhon shudhu USD account support kore.")
        if quote != "USD" and base != "USD":
            raise ValueError(f"{symbol}: ekhon shudhu USD pair (EUR_USD, USD_JPY ityadi) support kore.")
        if self.get_position(symbol):
            raise RuntimeError(f"{symbol} e OANDA te agei position khola ache")
        inst = self._instrument(symbol)
        bid, ask, tradeable = self._quote(symbol)
        if not tradeable:
            raise ValueError("OANDA market ekhon bondho (weekend/holiday). Market khulle abar chesta koro.")
        mid = _dec((bid + ask) / 2)
        max_lev = max(1, int(1 / float(inst.get("marginRate", "0.02"))))
        lev = max(1, min(int(leverage), max_lev))
        _guards(mid, tp_gap, sl_gap, lev)
        spread = _dec(ask - bid)
        if spread * 2 >= _dec(tp_gap):
            raise ValueError(f"Spread {float(spread):g} TP ({float(tp_gap):g}) er prai ordhek. TP barao.")

        units = _dec(margin_usd) * lev / (mid if quote == "USD" else Decimal(1))
        units = _round_step(units, Decimal(1).scaleb(-int(inst.get("tradeUnitsPrecision", 0))))
        if units < _dec(inst.get("minimumTradeSize", "1")):
            raise ValueError(f"Units {units} < minimum {inst.get('minimumTradeSize')}. Margin ba leverage barao.")
        if units > _dec(inst.get("maximumOrderUnits", "100000000")):
            raise ValueError("Units maximum order size er beshi.")
        long_ = side == "LONG"
        ref = _dec(ask if long_ else bid)
        q = Decimal(1).scaleb(-int(inst.get("displayPrecision", 5)))
        tp = (ref + _dec(tp_gap) if long_ else ref - _dec(tp_gap)).quantize(q, ROUND_HALF_UP)
        sl = (ref - _dec(sl_gap) if long_ else ref + _dec(sl_gap)).quantize(q, ROUND_HALF_UP)

        opened_ms = int(time.time() * 1000)
        res = self._req("POST", f"/v3/accounts/{self.acct}/orders", body={"order": {
            "type": "MARKET", "instrument": symbol, "units": ("" if long_ else "-") + _fmt(units),
            "timeInForce": "FOK", "positionFill": "DEFAULT",
            "takeProfitOnFill": {"price": format(tp, "f"), "timeInForce": "GTC"},
            "stopLossOnFill": {"price": format(sl, "f"), "timeInForce": "GTC"},
        }})
        fill = res.get("orderFillTransaction")
        if not fill:
            raise RuntimeError(f"OANDA order batil: {res.get('orderCancelTransaction', {}).get('reason', 'unknown')}")
        return {"symbol": symbol, "side": side, "qty": float(units), "leverage": lev, "entry_price": float(fill.get("price", ref)),
                "tp_price": float(tp), "sl_price": float(sl), "confirmed": True, "opened_ms": opened_ms}

    def close_position(self, symbol):
        pos = self.get_position(symbol)
        if not pos:
            return None
        body = {"longUnits": "ALL"} if pos["side"] == "LONG" else {"shortUnits": "ALL"}
        self._req("PUT", f"/v3/accounts/{self.acct}/positions/{symbol}/close", body=body)
        return pos

    def last_closed_pnl(self, symbol, since_ms=0):
        trades = self._req("GET", f"/v3/accounts/{self.acct}/trades", params={"state": "CLOSED", "instrument": symbol, "count": 20}).get("trades", [])
        net, found, tmax = 0.0, False, 0
        for t in trades:
            ct = _iso_ms(t.get("closeTime", "0"))
            if ct >= int(since_ms) - 2000:
                net += _first_num(t.get("realizedPL")) + _first_num(t.get("financing")) + _first_num(t.get("commission"))
                found, tmax = True, max(tmax, ct)
        return {"pnl": net, "entry": 0.0, "exit": 0.0, "time": tmax} if found else None


# =====================================================================
#  Factory
# =====================================================================
def make_data(exch, testnet=False, token="", account=""):
    if exch == "binance":
        return BinanceData(testnet)
    if exch == "oanda":
        return OandaData(token, account, practice=testnet)
    return BybitData(testnet)


def make_engine(exch, key, secret, testnet=True):
    """key/secret: Bybit & Binance = API key/secret. OANDA = token / account ID."""
    if exch == "binance":
        return BinanceEngine(key, secret, testnet)
    if exch == "oanda":
        return OandaEngine(key, secret, practice=testnet)
    return BybitEngine(key, secret, testnet=testnet)
