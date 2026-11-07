"""
bybit_engine.py  -  Bybit V5 (USDT Perpetual / linear) trading helper

Ki kore:
  * wallet()          -> Bybit er asol balance
  * open_position()   -> leverage set + Market order + TP/SL (Bybit er server e boshe)
  * get_position()    -> ekhon position khola ache kina, unrealised PnL
  * close_position()  -> reduce-only market close
  * last_closed_pnl() -> position bondho hole asol realised PnL

TP/SL Bybit er server e thake (tpslMode=Full), tai tomar app ghumiye gelew
position TP/SL e nije theke close hobe.
"""
import time
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from pybit.unified_trading import HTTP


def _dec(x):
    return Decimal(str(x))


def _round_step(value, step, rounding=ROUND_DOWN):
    step = _dec(step)
    return (_dec(value) / step).to_integral_value(rounding=rounding) * step


def _fmt(d):
    """Decimal -> plain string (kono scientific notation na)."""
    return format(d.normalize(), "f")


class BybitEngine:
    def __init__(self, api_key, api_secret, testnet=True):
        self.testnet = bool(testnet)
        self.session = HTTP(testnet=self.testnet, api_key=api_key, api_secret=api_secret)
        self._inst_cache = {}

    # ---------------------------------------------------------------- wallet
    def wallet(self):
        """UNIFIED, na hole CONTRACT account er balance. 'raw' = debug er jonno Bybit er uttor (secret chhara)."""
        def num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def first(*vals):
            for v in vals:
                n = num(v)
                if n is not None:      # "" ba None skip, kintu "0" ke valid dhori
                    return n
            return 0.0

        last_err = None
        for acct_type in ("UNIFIED", "CONTRACT"):
            try:
                r = self.session.get_wallet_balance(accountType=acct_type)
                lst = r["result"]["list"]
            except Exception as ex:
                last_err = ex
                continue
            if not lst:
                last_err = f"{acct_type}: empty list"
                continue
            acct = lst[0]
            usdt = next((c for c in acct.get("coin", []) if c.get("coin") == "USDT"), {})
            equity = first(acct.get("totalEquity"), acct.get("totalWalletBalance"), usdt.get("equity"), usdt.get("walletBalance"))
            available = first(acct.get("totalAvailableBalance"), usdt.get("availableToWithdraw"), usdt.get("walletBalance"))
            raw = {k: v for k, v in acct.items() if k != "coin"}
            raw["accountTypeQueried"] = acct_type
            raw["USDT"] = usdt
            raw["coins_returned"] = [c.get("coin") for c in acct.get("coin", [])]
            try:   # ei API key ta kon Bybit account (UID) er, ar ki permission ache
                ki = self.session.get_api_key_information()["result"]
                raw["API_KEY_INFO"] = {k: ki.get(k) for k in ("userID", "parentUid", "readOnly", "permissions", "uta", "ips", "expiredAt") if k in ki}
            except Exception as ex:
                raw["API_KEY_INFO_error"] = str(ex)[:200]
            return {"equity": equity, "available": available,
                    "usdt_wallet": first(usdt.get("walletBalance")), "account_type": acct_type, "raw": raw}
        raise RuntimeError(f"Wallet fetch failed: {last_err}")

    # ------------------------------------------------------------ market info
    def _instrument(self, symbol):
        if symbol in self._inst_cache:
            return self._inst_cache[symbol]
        r = self.session.get_instruments_info(category="linear", symbol=symbol)
        lst = r["result"]["list"]
        if not lst:
            raise ValueError(f"{symbol} Bybit e paoa jay nai ({'testnet' if self.testnet else 'mainnet'})")
        it = lst[0]
        if it.get("status") not in (None, "Trading"):
            raise ValueError(f"{symbol} ekhon {'testnet' if self.testnet else 'mainnet'} e live na (status: {it.get('status')}). Onno coin nao.")
        info = {
            "qty_step": it["lotSizeFilter"]["qtyStep"],
            "min_qty": it["lotSizeFilter"]["minOrderQty"],
            "min_notional": it["lotSizeFilter"].get("minNotionalValue", "5"),
            "tick": it["priceFilter"]["tickSize"],
            "max_lev": float(it["leverageFilter"]["maxLeverage"]),
        }
        self._inst_cache[symbol] = info
        return info

    def last_price(self, symbol):
        r = self.session.get_tickers(category="linear", symbol=symbol)
        return float(r["result"]["list"][0]["lastPrice"])

    def _set_leverage(self, symbol, lev):
        try:
            self.session.set_leverage(
                category="linear", symbol=symbol,
                buyLeverage=str(lev), sellLeverage=str(lev),
            )
        except Exception as e:
            # 110043 = leverage already same, eta error na
            if "110043" in str(e) or "not modified" in str(e).lower():
                return
            raise

    # --------------------------------------------------------------- position
    def get_position(self, symbol):
        r = self.session.get_positions(category="linear", symbol=symbol)
        for p in r["result"]["list"]:
            size = float(p.get("size") or 0)
            if size > 0:
                return {
                    "side": "LONG" if p.get("side") == "Buy" else "SHORT",
                    "size": size,
                    "size_raw": p.get("size"),
                    "entry_price": float(p.get("avgPrice") or 0),
                    "unrealised_pnl": float(p.get("unrealisedPnl") or 0),
                    "take_profit": p.get("takeProfit"),
                    "stop_loss": p.get("stopLoss"),
                }
        return None

    def open_position(self, symbol, side, margin_usd, leverage, tp_gap, sl_gap):
        """
        side      : 'LONG' / 'SHORT'
        margin_usd: tomar margin ($)    -> notional = margin * leverage
        tp_gap    : entry theke koto $ dure Take Profit
        sl_gap    : entry theke koto $ dure Stop Loss
        """
        side = side.upper()
        if side not in ("LONG", "SHORT"):
            raise ValueError("side LONG ba SHORT hote hobe")
        if self.get_position(symbol):
            raise RuntimeError(f"{symbol} e Bybit e agei position khola ache")

        inst = self._instrument(symbol)
        lev = max(1, min(int(leverage), int(inst["max_lev"])))

        price = _dec(self.last_price(symbol))
        sl_frac, tp_frac, liq_frac = _dec(sl_gap) / price, _dec(tp_gap) / price, _dec("0.8") / lev
        if sl_frac >= liq_frac:
            raise ValueError(f"SL gap {float(sl_frac)*100:.2f}% > liquidation distance ~{float(liq_frac)*100:.2f}% ({lev}x). SL trigger hobar age-i liquidate hobe. Leverage komao ba SL chhoto koro.")
        if tp_frac >= _dec("0.5"):
            raise ValueError(f"TP gap price er {float(tp_frac)*100:.0f}% - onek boro, TP thik koro (coin er price ${float(price):g}).")
        self._set_leverage(symbol, lev)
        qty = _round_step(_dec(margin_usd) * lev / price, inst["qty_step"])
        if qty < _dec(inst["min_qty"]):
            raise ValueError(f"Qty {qty} < minimum {inst['min_qty']}. Margin ba leverage barao.")
        if qty * price < _dec(inst["min_notional"]):
            raise ValueError(f"Order value ${qty * price:.2f} < minimum ${inst['min_notional']}. Margin barao.")

        tick = inst["tick"]
        if side == "LONG":
            order_side = "Buy"
            tp = price + _dec(tp_gap)
            sl = price - _dec(sl_gap)
        else:
            order_side = "Sell"
            tp = price - _dec(tp_gap)
            sl = price + _dec(sl_gap)
        tp = _round_step(tp, tick, ROUND_HALF_UP)
        sl = _round_step(sl, tick, ROUND_HALF_UP)
        if tp <= 0 or sl <= 0:
            raise ValueError("TP/SL gap onek boro, price negative hoye jacche.")

        self.session.place_order(
            category="linear", symbol=symbol, side=order_side, orderType="Market",
            qty=_fmt(qty),
            takeProfit=_fmt(tp), stopLoss=_fmt(sl),
            tpTriggerBy="LastPrice", slTriggerBy="LastPrice",
            tpslMode="Full", positionIdx=0,
        )

        entry, confirmed = float(price), False
        for _ in range(6):
            time.sleep(0.5)
            p = self.get_position(symbol)
            if p:
                entry, confirmed = p["entry_price"], True
                break
        return {
            "symbol": symbol, "side": side, "qty": float(qty), "leverage": lev,
            "entry_price": entry, "tp_price": float(tp), "sl_price": float(sl),
            "confirmed": confirmed,
        }

    def close_position(self, symbol):
        pos = self.get_position(symbol)
        if not pos:
            return None
        self.session.place_order(
            category="linear", symbol=symbol,
            side="Sell" if pos["side"] == "LONG" else "Buy",
            orderType="Market", qty=pos["size_raw"],
            reduceOnly=True, positionIdx=0,
        )
        return pos

    def last_closed_pnl(self, symbol, since_ms=0):
        """since_ms er por bondho howa sesh trade er realised PnL (fee soho Bybit er hishab)."""
        r = self.session.get_closed_pnl(category="linear", symbol=symbol, limit=5)
        for x in r["result"]["list"]:
            t = int(x.get("updatedTime") or x.get("createdTime") or 0)
            if t >= int(since_ms) - 5000:
                return {
                    "pnl": float(x.get("closedPnl") or 0),
                    "entry": float(x.get("avgEntryPrice") or 0),
                    "exit": float(x.get("avgExitPrice") or 0),
                    "time": t,
                }
        return None
