"""
Common interface. App shudhu eta-i jane; kon exchange/broker seta app er dekhar dorkar nai.

Sob engine ek-i format-e return kore:
  wallet()          -> {"equity", "available", "usdt_wallet", "account_type", "raw"}
  get_position()    -> {"side": "LONG"/"SHORT", "size", "size_raw", "entry_price", "unrealised_pnl", ...} ba None
  open_position()   -> {"symbol","side","qty","leverage","entry_price","tp_price","sl_price","confirmed"}
  close_position()  -> agey khola position dict ba None
  last_closed_pnl() -> {"pnl","entry","exit","time"} ba None
  price(symbol)     -> float (live price)
  klines(symbol, n) -> pandas DataFrame [time, open, high, low, close, volume] (purono -> notun)
"""


class BaseEngine:
    key = "base"
    label = "Base"
    market = "crypto"            # "crypto" | "forex"
    has_testnet = True
    testnet_label = "TESTNET"
    # (field_name, label, is_secret, required)
    fields = (("api_key", "API Key", True, True), ("api_secret", "API Secret", True, True))
    fee_roundtrip = 0.0011       # demo/estimate: taker fee x 2 (forex e spread, tai 0)

    def __init__(self, creds, testnet=True):
        self.creds = creds or {}
        self.testnet = bool(testnet)

    @classmethod
    def live_symbols(cls, testnet):
        """Exchange e ekhon asol e trade-able symbol er set (internal format, jemon BTCUSDT). None = filter korbo na."""
        return None

    def wallet(self): raise NotImplementedError
    def price(self, symbol): raise NotImplementedError
    def klines(self, symbol, limit=30): raise NotImplementedError
    def get_position(self, symbol): raise NotImplementedError
    def open_position(self, symbol, side, margin_usd, leverage, tp_gap, sl_gap): raise NotImplementedError
    def close_position(self, symbol): raise NotImplementedError
    def last_closed_pnl(self, symbol, since_ms=0): raise NotImplementedError
