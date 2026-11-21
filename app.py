import firebase_admin
import json
import os
import random
import string
import time
from datetime import datetime
from firebase_admin import credentials, firestore
import plotly.graph_objects as go
import pandas as pd
from pybit.unified_trading import HTTP
import requests
import streamlit as st
import copy
import threading
import re
import base64
import hashlib
import exchanges as _exch_mod
import pro_ui
from bybit_engine import BybitEngine
from exchanges import EXCHANGES, EXCHANGE_IDS, EXCHANGE_NAMES, OANDA_MAJORS, BinanceData, BitgetData, mt5_majors, make_data, make_engine, _check_ban, BINANCE_MAIN
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None
# Secure Cloud Firebase Gateway Authentication Layer
# cache_resource = ekbar-i chole (thread-safe), tai duto session ekshathe shuru holeo "already exists" error ashe na
@st.cache_resource(show_spinner=False)
def _init_firebase():
    if firebase_admin._apps:
        return True
    fb_json = os.environ.get("firebase_json", None)
    if fb_json:
        fb_dict = json.loads(fb_json) if isinstance(fb_json, str) else fb_json
        cred = credentials.Certificate(fb_dict)
    elif os.path.exists("firebase_key.json"):
        cred = credentials.Certificate("firebase_key.json")
    else:
        raise RuntimeError("Missing Config Database Keys Node Property!")
    try:
        firebase_admin.initialize_app(cred)
    except ValueError as e:
        if "already exists" not in str(e):   # onno session age-i init kore felle thik ache
            raise
    return True

try:
    _init_firebase()
except Exception as e:
    st.error(f"Sync Error: {str(e)}")
    st.stop()

db = firestore.client()
@st.cache_resource(show_spinner=False)
def _db_cache():
    return {}
DB_CACHE_TTL = 15   # sec: Firestore read free-quota bachanor jonno

def db_load(key, default_val):
    cache = _db_cache()
    hit = cache.get(key)
    if hit is not None and time.time() - hit[0] < DB_CACHE_TTL:
        return copy.deepcopy(hit[1]) if hit[2] else default_val
    try:
        ref = db.collection("scalper_system").document(key).get()
        if ref.exists:
            val = ref.to_dict().get("data", default_val)
            cache[key] = (time.time(), val, True)
            return copy.deepcopy(val)
        cache[key] = (time.time(), None, False)
        return default_val
    except: return default_val

def db_save(key, val):
    cache = _db_cache()
    hit = cache.get(key)
    if hit is not None and hit[2] and time.time() - hit[0] < 600 and hit[1] == val:
        cache[key] = (time.time(), hit[1], True)   # ager-i same value: write dorkar nai
        return
    try:
        db.collection("scalper_system").document(key).set({"data": val})
        _db_cache()[key] = (time.time(), copy.deepcopy(val), True)
    except: pass
# ---------- 🔐 Sticky inputs: License/API key ekbar dile mone thake (Firebase e encrypted), mode/exchange bodlaleo jay na ----------
_TN_DEFAULT = {"bybit": False, "binance": False, "bitget": False, "oanda": True, "mt5": True}   # crypto = mainnet default, forex = practice default
_STICKY_KEYS = ["lic_field_sidebar", "pass_field_bitget", "acct_field_oanda", "api_field_mt5", "acct_field_mt5", "region_field_mt5", "mt5_suffix_field"] + \
               [f"{p}_field_{e}" for e in ("bybit", "binance", "bitget", "oanda") for p in ("api", "sec")]

def _vault():
    from cryptography.fernet import Fernet
    seed = os.environ.get("VAULT_SECRET") or os.environ.get("firebase_json") or ""
    if not seed and os.path.exists("firebase_key.json"):
        seed = open("firebase_key.json").read()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest()))

def vault_get(uid, name):
    tok = db_load(f"vault_{uid}_{name}", "")
    if not tok: return ""
    try: return _vault().decrypt(tok.encode()).decode()
    except Exception: return ""

def vault_set(uid, name, val):
    try: db_save(f"vault_{uid}_{name}", _vault().encrypt(val.encode()).decode())
    except Exception: pass

def vault_clear(uid):
    for k in _STICKY_KEYS:
        try: db.collection("scalper_system").document(f"vault_{uid}_{k}").delete()
        except Exception: pass
        _db_cache().pop(f"vault_{uid}_{k}", None)
        st.session_state.pop(k, None); st.session_state.pop(f"_sv_{k}", None)

def sticky_seed(uid, key, default=""):
    if key not in st.session_state:
        st.session_state[key] = vault_get(uid, key) or default

def sticky_text(uid, label, key, secret=True, default="", **kw):
    sticky_seed(uid, key, default)
    val = (st.text_input(label, type="password" if secret else "default", key=key, **kw) or "").strip()
    if val and val != st.session_state.get(f"_sv_{key}"):   # kokhono faka value diye saved key mochha hoy na
        if val != vault_get(uid, key): vault_set(uid, key, val)
        st.session_state[f"_sv_{key}"] = val
    return val

def sticky_init(uid, key, default=False):
    if key not in st.session_state:
        st.session_state[key] = bool(db_load(f"sticky_{uid}_{key}", default))

def sticky_check(uid, label, key, default=False, **kw):
    sticky_init(uid, key, default)
    val = st.checkbox(label, key=key, **kw)
    db_save(f"sticky_{uid}_{key}", bool(val))
    return val

def _ban_restore():
    try:
        for k, v in (db_load("ban_until_state", {}) or {}).items():
            if float(v) > time.time(): _exch_mod._BAN_UNTIL[k] = max(_exch_mod._BAN_UNTIL.get(k, 0), float(v))
    except Exception: pass

def _ban_persist():
    db_save("ban_until_state", {k: v for k, v in _exch_mod._BAN_UNTIL.items() if v > time.time()})

def conn_check():
    """Server er public IP/country + exchange gulo ei server theke reach hocche kina."""
    rows, us = [], False
    try:
        j = requests.get("https://ipinfo.io/json", timeout=6).json()
        rows.append(("Server IP", f"{j.get('ip')} | {j.get('city')}, {j.get('country')}"))
        us = j.get("country") == "US"
    except Exception as e:
        rows.append(("Server IP", f"check kora gelo na ({str(e)[:60]})"))
    tests = [("Bybit mainnet", "https://api.bybit.com/v5/market/time", None),
             ("Bybit testnet", "https://api-testnet.bybit.com/v5/market/time", None),
             ("Binance Futures mainnet", "https://fapi.binance.com/fapi/v1/ping", BINANCE_MAIN),
             ("Bitget mainnet", "https://api.bitget.com/api/v2/public/time", None)]
    for name, url, bankey in tests:
        try:
            if bankey: _check_ban(bankey)
            c = requests.get(url, timeout=8).status_code
            v = "✅ OK" if c == 200 else ("❌ Region/IP block" if c in (403, 451) else ("❌ Rate-limit ban" if c in (418, 429) else f"⚠️ HTTP {c}"))
        except RuntimeError as e:
            _u = _exch_mod._BAN_UNTIL.get(bankey or "", 0)
            v = f"❌ IP ban cholche, {datetime.utcfromtimestamp(_u + 6 * 3600).strftime('%d %b %I:%M %p')} (Dhaka somoy) porjonto. Ei somoy request pathai nai, karon ban-e request pathale ban aro lomba hoy."
        except Exception as e:
            v = f"❌ {str(e)[:50]}"
        rows.append((name, v))
    return rows, us

_ban_restore()   # restart/deploy er por-o Binance ban er somoy mone rakhe
# Initialize Sync Control Registries Persistent Global Cache System
if "init_sync" not in st.session_state:
    st._central_user_creds = db_load("user_creds", {})
    st._central_key_registry = db_load("key_registry", {})
    st._central_blacklist = db_load("blacklist", [])
    st._license_csv_database = db_load("license_csv", [])
    st._global_referral_tree = db_load("referral_tree", {})
    st._global_user_pnl_history = db_load("pnl_history", [])
    st._uid_to_username = db_load("uid_to_user", {})
    st._mlm_bonus_enabled = db_load("mlm_enabled", True)
    st._ref_system_active = db_load("ref_sys_active", True)
    st._mlm_deposit_bonus_rate = db_load("dep_rate", 5.18)
    st._mlm_gen_rates = db_load("gen_rates", {1: 5.0, 2: 4.0, 3: 3.0, 4: 2.0, 5: 1.0, 6: 0.5, 7: 0.5})
    st._mlm_id_thresholds = db_load("id_thresh", {1: 10, 2: 20, 3: 40, 4: 80, 5: 160, 6: 320, 7: 640})
    st.session_state.init_sync = True
else:
    st._central_user_creds = db_load("user_creds", {})
    st._central_key_registry = db_load("key_registry", {})
    st._central_blacklist = db_load("blacklist", [])
    st._license_csv_database = db_load("license_csv", [])
    st._global_referral_tree = db_load("referral_tree", {})
    st._global_user_pnl_history = db_load("pnl_history", [])
    st._uid_to_username = db_load("uid_to_user", {})
    st._mlm_bonus_enabled = db_load("mlm_enabled", True)
    st._ref_system_active = db_load("ref_sys_active", True)
    st._mlm_deposit_bonus_rate = db_load("dep_rate", 5.18)
    st._mlm_gen_rates = db_load("gen_rates", {1: 5.0, 2: 4.0, 3: 3.0, 4: 2.0, 5: 1.0, 6: 0.5, 7: 0.5})
    st._mlm_id_thresholds = db_load("id_thresh", {1: 10, 2: 20, 3: 40, 4: 80, 5: 160, 6: 320, 7: 640})
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = st.query_params.get("session_user", None)

if "first_trade_done" not in st.session_state:
    st.session_state.first_trade_done = False

# 🔥 CLOUD HARD-LATCH: সেশন মেমোরি না থাকলেও লাস্ট একটিভ ইউজারের ক্লাউড ডাটা লক রিড করবে
last_active_uid = db_load("global_last_active_uid", "NONE")
if st.session_state.logged_in_user:
    u_data = st._central_user_creds.get(st.session_state.logged_in_user, {})
    allocated_user_id = u_data.get("uid", "GLOBAL")
    db_save("global_last_active_uid", allocated_user_id)
else:
    allocated_user_id = last_active_uid
if allocated_user_id != "NONE":
    st.session_state.bot_active = db_load(f"bot_active_{allocated_user_id}", False)
    st.session_state.first_trade_done = db_load(f"first_done_{allocated_user_id}", False)
    # ক্লাউড রান ট্র্যাকিংয়ের জন্য সাইডবার প্যারামিটার ব্যাকআপ রিকভারি লেয়ার
    price_jump_target = db_load(f"tp_target_{allocated_user_id}", 0.01)
    stop_loss_gap = db_load(f"sl_gap_{allocated_user_id}", 0.02)
    leverage = db_load(f"leverage_lock_{allocated_user_id}", 20)
    trade_amount = db_load(f"margin_lock_{allocated_user_id}", 20)
    target_symbol = db_load(f"trade_coin_{allocated_user_id}", "BTCUSDT")
    or_api_key = db_load(f"or_key_{allocated_user_id}", "")
    or_model_id = db_load(f"or_model_{allocated_user_id}", "google/gemini-2.5-flash:free")
else:
    if "bot_active" not in st.session_state:
        st.session_state.bot_active = False

if "engine_logs" not in st.session_state:
    st.session_state.engine_logs = ["System Swarm Gateway Init... 📡"]
# --- 🚀 PREMIUM NO-BORDER SPLASH SCREEN ANIMATION TRIGGER ---
if "splash_done" not in st.session_state:
    st.set_page_config(page_title="AI Scalper", page_icon="⚡", layout="wide")
    st.markdown(pro_ui.splash_html(), unsafe_allow_html=True)
    time.sleep(1.4)
    st.session_state.splash_done = True
    st.rerun()
@st.cache_data(ttl=30)
def fetch_bybit_future_coins():
    backup_database = {
        "🪙 BTC (Bitcoin)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0},
        "🔷 ETH (Ethereum)": {"symbol": "ETHUSDT", "max_leverage": 100, "default_tp": 8.0, "default_sl": 15.0, "step": 1.0},
        "☀️ SOL (Solana)": {"symbol": "SOLUSDT", "max_leverage": 50, "default_tp": 1.5, "default_sl": 3.0, "step": 0.1},
        "💥 XRP (Ripple)": {"symbol": "XRPUSDT", "max_leverage": 100, "default_tp": 0.015, "default_sl": 0.03, "step": 0.001},
        "🐶 DOGE (Dogecoin)": {"symbol": "DOGEUSDT", "max_leverage": 50, "default_tp": 0.004, "default_sl": 0.01, "step": 0.0005},
        "🌟 ADA (Cardano)": {"symbol": "ADAUSDT", "max_leverage": 50, "default_tp": 0.01, "default_sl": 0.02, "step": 0.0001},
        "🔮 DOT (Polkadot)": {"symbol": "DOTUSDT", "max_leverage": 50, "default_tp": 0.15, "default_sl": 0.30, "step": 0.01},
        "💜 MATIC (Polygon)": {"symbol": "MATICUSDT", "max_leverage": 50, "default_tp": 0.02, "default_sl": 0.04, "step": 0.0001},
        "🔗 LINK (Chainlink)": {"symbol": "LINKUSDT", "max_leverage": 50, "default_tp": 0.30, "default_sl": 0.60, "step": 0.01},
        "🚀 SHIB (Shiba Inu)": {"symbol": "SHIBUSDT", "max_leverage": 50, "default_tp": 0.0000005, "default_sl": 0.000001, "step": 0.00000001},
        "⚡ LTC (Litecoin)": {"symbol": "LTCUSDT", "max_leverage": 75, "default_tp": 1.5, "default_sl": 3.0, "step": 0.05},
        "🔺 AVAX (Avalanche)": {"symbol": "AVAXUSDT", "max_leverage": 50, "default_tp": 0.80, "default_sl": 1.50, "step": 0.01},
        "🔴 TRX (TRON)": {"symbol": "TRXUSDT", "max_leverage": 50, "default_tp": 0.002, "default_sl": 0.005, "step": 0.0001},
        "💵 BCH (Bitcoin Cash)": {"symbol": "BCHUSDT", "max_leverage": 75, "default_tp": 5.0, "default_sl": 10.0, "step": 0.1},
        "🪐 XLM (Stellar)": {"symbol": "XLMUSDT", "max_leverage": 50, "default_tp": 0.005, "default_sl": 0.01, "step": 0.0001},
        "💧 SUI (Sui Network)": {"symbol": "SUIUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.10, "step": 0.001},
        "🌿 NEAR (Near Protocol)": {"symbol": "NEARUSDT", "max_leverage": 50, "default_tp": 0.10, "default_sl": 0.20, "step": 0.001},
        "🧪 APT (Aptos)": {"symbol": "APTUSDT", "max_leverage": 50, "default_tp": 0.15, "default_sl": 0.30, "step": 0.001},
        "🔴 OP (Optimism)": {"symbol": "OPUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.10, "step": 0.001},
        "🔷 ARB (Arbitrum)": {"symbol": "ARBUSDT", "max_leverage": 50, "default_tp": 0.03, "default_sl": 0.06, "step": 0.001},
        "🎛️ INJ (Injective)": {"symbol": "INJUSDT", "max_leverage": 50, "default_tp": 0.40, "default_sl": 0.80, "step": 0.01},
        "🟢 RNDR (Render)": {"symbol": "RNDRUSDT", "max_leverage": 50, "default_tp": 0.20, "default_sl": 0.40, "step": 0.001},
        "🤖 FET (Artificial Superintelligence)": {"symbol": "FETUSDT", "max_leverage": 50, "default_tp": 0.04, "default_sl": 0.08, "step": 0.001},
        "🧱 TIA (Celestia)": {"symbol": "TIAUSDT", "max_leverage": 50, "default_tp": 0.12, "default_sl": 0.25, "step": 0.001},
        "🎮 GALA (Gala Games)": {"symbol": "GALAUSDT", "max_leverage": 50, "default_tp": 0.001, "default_sl": 0.003, "step": 0.0001}
    }
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000"
        res = requests.get(url, timeout=12).json()
        instruments = res.get("result", {}).get("list", [])
        for inst in instruments:
            if inst.get("status") == "Trading" and inst.get("quoteCoin") == "USDT":
                sym = inst["symbol"]
                base = inst["baseCoin"]
                max_lev = int(float(inst.get("leverageFilter", {}).get("maxLeverage", 100)))
                tick_size = float(inst.get("priceFilter", {}).get("tickSize", "0.01"))
                display_key = f"🪙 {base} (Bybit Futures Market)"
                if display_key not in backup_database:
                    backup_database[display_key] = {"symbol": sym, "max_leverage": max_lev, "default_tp": tick_size * 400, "default_sl": tick_size * 600, "step": tick_size}
        return backup_database
    except: return backup_database

BYBYT_DATABASE_CORE = fetch_bybit_future_coins()

@st.cache_data(ttl=600, show_spinner=False)
def fetch_exchange_coins(exch, testnet, extra=""):
    """Bybit chhara onno exchange er coin/pair list. Fail hole error text ferot (bar bar network call ar block kora hobe na)."""
    try:
        if exch == "binance":
            return BinanceData(testnet).coins()
        if exch == "bitget":
            return BitgetData(demo=testnet).coins()
        if exch == "oanda":
            return dict(OANDA_MAJORS)
        if exch == "mt5":
            return mt5_majors(extra)
        return dict(BYBYT_DATABASE_CORE)
    except Exception as e:
        return {"__error__": str(e)}
YOUR_SECRET_MASTER_CODE = os.environ.get("ADMIN_CODE", "ADMIN1234")   # Render e ADMIN_CODE env variable set koro
AI_COOLDOWN_SEC = 60        # AI signal protibar koto sec por por
AUTO_REFRESH_MS = 5000      # page auto refresh (ms)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_testnet_live_symbols():
    """Bybit TESTNET e ekhon jei USDT contract gulo asol e live (mainnet er list e onek coin testnet e nei)."""
    r = requests.get("https://api-testnet.bybit.com/v5/market/instruments-info?category=linear&limit=1000", timeout=10).json()
    return sorted(i["symbol"] for i in r.get("result", {}).get("list", []) if i.get("status") == "Trading" and i.get("quoteCoin") == "USDT")

def fetch_free_models():
    """OpenRouter er public model list theke free (price 0) model gulo, boro context age."""
    r = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
    r.raise_for_status()
    out = []
    for m in r.json().get("data", []):
        mid = m.get("id", "")
        p = m.get("pricing") or {}
        arch = m.get("architecture") or {}
        out_mods = arch.get("output_modalities") or ["text"]
        in_mods = arch.get("input_modalities") or ["text"]
        is_free = mid.endswith(":free") and str(p.get("prompt")) in ("0", "0.0") and str(p.get("completion")) in ("0", "0.0")
        if is_free and out_mods == ["text"] and "text" in in_mods:   # music/image/audio model baad
            sz = re.search(r"(\d+(?:\.\d+)?)b", mid.lower())
            out.append((mid, float(sz.group(1)) if sz else 50.0, int(m.get("context_length") or 0)))
    out.sort(key=lambda x: (-x[1], -x[2]))   # nam e 'NNb' thakle boro size age (mota-muti proxy)
    return [i for i, _, _ in out][:25]

@st.cache_resource(show_spinner=False)
def _ai_store():
    return {}   # "<uid>_<mode>" -> AI job state (process-level, session reconnect holeo thake)

AI_MODES = ["Secure (strict)", "Balanced", "Turbo (test: always trade)"]

def pick_ai_mode(selected, is_mainnet_real):
    """Mainnet (asol taka) e shudhu Secure. Balanced/Turbo shudhu Demo ba Testnet e."""
    return AI_MODES[0] if is_mainnet_real or selected not in AI_MODES else selected

def build_mode_instruction(mode, first_trade_done):
    """(log label, AI ke deya instruction)"""
    turbo = "CRITICAL: You must operate in TURBO SCALPING MODE. Find immediate next micro-trend breakout/breakdown and issue LONG or SHORT immediately. Avoid HOLD."
    strict = "CRITICAL: You must operate in ULTRA-SECURE INSTITUTIONAL MODE. Only issue LONG or SHORT if MA-7 breakout and RSI are 100% perfect. Otherwise output HOLD."
    balanced = ("CRITICAL: BALANCED MODE. Issue LONG if the last 3 candle closes are rising, price is above MA-7 and RSI is below 70. "
                "Issue SHORT if the last 3 candle closes are falling, price is below MA-7 and RSI is above 30. Otherwise output HOLD.")
    if mode == AI_MODES[2]: return "🚀 [TURBO AI]", turbo
    if mode == AI_MODES[1]: return "⚖️ [BALANCED AI]", balanced
    return ("🚀 [TURBO AI]", turbo) if not first_trade_done else ("🔒 [SECURE AI]", strict)

def _ai_job(store, key, api_key, models, prompt, symbol):
    """Background thread: OpenRouter ke dake. Streamlit (st.*) kono jinish ekhane use kora jabe na."""
    logs = []
    def L(m): logs.append(f"[{time.strftime('%H:%M:%S')}] {m}")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "HTTP-Referer": "https://streamlit.io", "X-Title": "Bybit AI Engine"}
    res = {"status": "done", "symbol": symbol, "consumed": False, "signal": "FAIL", "model": "", "raw": "", "err": "", "daily_exhausted": False}
    try:
        tried, box = set(), {"resp": None, "model": "", "fatal": False}
        def attempt(model_list):
            for m in model_list:
                if m in tried or box["resp"] is not None or box["fatal"]:
                    continue
                tried.add(m)
                try:
                    r = requests.post(url, headers=headers, json={"model": m, "messages": [{"role": "user", "content": prompt}]}, timeout=(5, 40))
                except Exception as e:
                    res["err"] = f"{m} -> {type(e).__name__}"
                    L(f"AI model error: {res['err']}")
                    continue
                if r.status_code == 200:
                    box["resp"], box["model"] = r, m
                    return
                res["err"] = f"{m} -> HTTP {r.status_code}: {r.text[:140]}"
                L(f"AI model failed: {res['err']}")
                if "free-models-per-day" in r.text:
                    res["daily_exhausted"] = True; box["fatal"] = True
                elif r.status_code in (401, 403):
                    box["fatal"] = True
        attempt(models)
        if box["resp"] is None and not box["fatal"]:
            L("Model kaj korena. OpenRouter er live free list theke try korchi...")
            try:
                attempt(fetch_free_models()[:3])
            except Exception as e:
                L(f"Free list ante parlam na: {e}")
        if box["resp"] is not None:
            try:
                text = (box["resp"].json()["choices"][0]["message"].get("content") or "").upper()
            except Exception:
                text = ""
            words = re.findall(r"[A-Z]+", text)
            found = {w for w in words if w in ("LONG", "SHORT", "HOLD")}
            # uttor chhoto (max 3 shobdo) ar thik ekta signal thakle tobei; nahole HOLD (real money te guess kora hobe na)
            res["signal"] = next(iter(found)) if (len(found) == 1 and len(words) <= 3) else "HOLD"
            res["model"], res["raw"] = box["model"], text.strip()[:60]
            L(f"AI answer ({box['model']}): '{res['raw'] or 'empty'}' -> {res['signal']}")
    except Exception as e:
        res["err"] = f"job crashed: {e}"
        L(res["err"])
    res["logs"], res["finished"] = logs, time.time()
    store[key] = res

@st.cache_data(ttl=3, show_spinner=False)
def feed_snapshot(exch, testnet, symbol, token="", account="", extra=""):
    """Price + candle: 3 sec cache, tai onek tab/session khola thakleo exchange e ek-i request jay (IP ban er jhunki kome)."""
    m = make_data(exch, testnet, token, account, extra)
    price, rows, err = None, [], ""
    try: price = float(m.last_price(symbol))
    except Exception as e: err = str(e)
    try: rows = m.klines(symbol, 30)
    except Exception as e: err = err or str(e)
    if price is None and not rows: raise RuntimeError(err or "no data")
    return {"price": price or 0.0, "rows": rows, "error": err if price is None else "", "cost": m.cost_frac(symbol, price or (rows[-1][4] if rows else 1.0)),
            "tradeable": getattr(m, "tradeable", True), "spread": getattr(m, "spread", 0.0)}

@st.cache_data(ttl=8, show_spinner=False)
def fetch_wallet_cached(exch, k, s, testnet, extra=""):   # underscore chhara: nahole cache key e user ba key dhora hoy na
    return make_engine(exch, k, s, testnet, extra).wallet()
# ==========================================
# 🧱 UPGRADED ULTRA-PREMIUM CYBERPUNK DARK THEME LAYER
# ==========================================
# ==========================================
# 🧱 ULTIMATE CYBERPUNK DARK ENGINE, ARROW RESTORE & FLOATING WINDOW
# ==========================================
# ==========================================
# 🧱 ULTIMATE CYBERPUNK DARK ENGINE, ARROW RESTORE & FLOATING WINDOW
# ==========================================
st.markdown(
    """
    <style>
    /* 🔵 ১. গ্লোবাল ব্যাকগ্রাউন্ড এবং বডি থিম হার্ড-লক (লাইট মোড ফোর্স ব্লক) */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stApp"] {
        background-color: #04070a !important;
        background-image: radial-gradient(circle at 50% 10%, #0d1627 0%, #04070a 80%) !important;
        color: #e2e8f0 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    /* 🔵 ২. কর্নারের অ্যারো বাটনটি শতভাগ পুনরুদ্ধার */
    [data-testid="stSidebarCollapseWrapper"] {
        display: block !important;
        visibility: visible !important;
        left: 8px !important;
        top: 8px !important;
        z-index: 999999 !important;
    }
    [data-testid="stSidebarCollapseWrapper"] button {
        background-color: #0f172a !important;
        color: #38bdf8 !important;
        border: 1px solid #1e2c3f !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.3) !important;
    }
    
    /* ৩. সাইডবার সুপার-ডার্ক ম্যাট ফিনিশিং ও স্মুথ ট্রানজিশন */
    div[data-testid="stSidebar"], section[data-testid="stSidebarView"] {
        background-color: #080c14 !important;
        background-image: linear-gradient(180deg, #080c14 0%, #030508 100%) !important;
        border-right: 1px solid #1e293b !important;
    }
    div[data-testid="stSidebar"] * { color: #f8fafc !important; }

    /* ৪. অল ইনপুট বক্স, সিলেক্টবক্স এবং টেক্সট এরিয়া লাইট-মোড প্রোটেকশন */
    div[data-baseweb="select"], div[data-baseweb="input"], input, .stTextArea textarea, div[role="radiogroup"] {
        background-color: #0b1322 !important;
        color: #ffffff !important;
        border: 1px solid #1e2c3f !important;
        border-radius: 8px !important;
    }

    /* 🟢 ৫. আপনার স্ক্রিনশট ২ এর সেই অরিজিনাল সুন্দর সবুজ গ্লোয়িং ম্যাտրিক্স বক্স */
    .custom-box-grid {
        background: #050a12 !important;
        padding: 22px !important;
        border-radius: 12px !important;
        margin-bottom: 12px !important;
        border: 1px solid #00e676 !important;
        box-shadow: 0 0 15px rgba(0, 230, 118, 0.15) !important;
    }
    .matrix-neon-text {
        font-family: 'Courier New', monospace !important;
        color: #00ff87 !important;
        text-shadow: 0 0 8px rgba(0, 255, 135, 0.4) !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }

    /* 🔵 💻 ৬. হাত দিয়ে টেনে নাড়ানোর মতো আল্ট্রা-প্রিমিয়াম সচল ফ্লোটিং উইন্ডো (Touch Draggable UI) */
    .crypto-floating-window {
        position: fixed !important;
        bottom: 120px !important;
        right: 20px !important;
        width: 155px !important;
        background: rgba(11, 19, 34, 0.9) !important;
        backdrop-filter: blur(12px) !important;
        border: 2px solid #38bdf8 !important;
        border-radius: 12px !important;
        padding: 12px !important;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.4) !important;
        z-index: 9999999 !important;
        font-family: monospace !important;
        text-align: center !important;
        cursor: move !important;
        touch-action: none !important;
    }

    div.stButton > button:first-child {
        width: 100% !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        color: #ffffff !important;
        border: 1px solid #2d3748 !important;
    }
    #MainMenu, footer { visibility: hidden !important; display: none !important; }
    </style>

    <!-- 🌐 জাভাস্ক্রিপ্ট সোয়াইপ এবং হাত দিয়ে ফ্লোটিং উইন্ডো ড্র্যাগ করার কিলার ইঞ্জিন -->
    <script>
    const parentDoc = window.parent.document;
    
    // ১. スマート মোবাইল স্ক্রিন সোয়াইপ ডিটেকশন (বাম থেকে টান দিলে সাইডবার ওপেন হবে)
    let startTouchX = 0;
    parentDoc.addEventListener('touchstart', e => {
        startTouchX = e.changedTouches[0].screenX;
    }, {passive: true});

    parentDoc.addEventListener('touchend', e => {
        let endTouchX = e.changedTouches[0].screenX;
        const sideBtn = parentDoc.querySelector('section[data-testid="stSidebar"] ~ button, [data-testid="stSidebarCollapseWrapper"] button');
        
        if (endTouchX - startTouchX > 130) {
            const isCollapsed = parentDoc.querySelector('section[data-testid="stSidebar"]').parentElement.getAttribute('aria-expanded') === 'false';
            if (isCollapsed && sideBtn) sideBtn.click();
        }
        if (startTouchX - endTouchX > 130) {
            const isOpen = parentDoc.querySelector('section[data-testid="stSidebar"]').parentElement.getAttribute('aria-expanded') === 'true';
            if (isOpen && sideBtn) sideBtn.click();
        }
    }, {passive: true});

    // ২. ফ্লোটিং উইন্ডো হাত দিয়ে স্ক্রিনের যেকোনো জায়গায় টেনে নাড়ানোর (Touch Draggable) অবিকল মেকানিজম
    function initDraggableWindow() {
        const targetElement = parentDoc.querySelector('.crypto-floating-window');
        if (!targetElement) {
            setTimeout(initDraggableWindow, 500);
            return;
        }
        
        let dragActive = false;
        let xCurrent, yCurrent, xInitial, yInitial;
        let offsetX = 0, offsetY = 0;

        targetElement.addEventListener('touchstart', onDragStart, {passive: false});
        parentDoc.addEventListener('touchend', onDragEnd, {passive: true});
        parentDoc.addEventListener('touchmove', onDrag, {passive: false});

        function onDragStart(e) {
            xInitial = e.touches[0].clientX - offsetX;
            yInitial = e.touches[0].clientY - offsetY;
            if (e.target === targetElement || targetElement.contains(e.target)) {
                dragActive = true;
            }
        }

        function onDragEnd() {
            xInitial = xCurrent;
            yInitial = yCurrent;
            dragActive = false;
        }

        function onDrag(e) {
            if (dragActive) {
                e.preventDefault();
                xCurrent = e.touches[0].clientX - xInitial;
                yCurrent = e.touches[0].clientY - yInitial;
                offsetX = xCurrent;
                offsetY = yCurrent;
                targetElement.style.transform = `translate3d(${xCurrent}px, ${yCurrent}px, 0)`;
            }
        }
    }
    setTimeout(initDraggableWindow, 1000);
    </script>
    """,
    unsafe_allow_html=True,
)
pro_ui.inject(st)
if st.session_state.logged_in_user is None:
    pro_ui.inject_auth(st)
    st.markdown(pro_ui.auth_hero(), unsafe_allow_html=True)
    auth_mode = st.radio("Choose Layer:", ["Login", "Sign Up", "Recover"], horizontal=True, label_visibility="collapsed")
    
    if auth_mode == "Sign Up":
        reg_username = st.text_input("Username", key="reg_u").strip()
        reg_password = st.text_input("Password", type="password", key="reg_p").strip()
        reg_email = st.text_input("Google Mail (Gmail ID):", key="reg_e").strip()
        global_country_list = ["Bangladesh", "United States", "United Kingdom", "United Arab Emirates", "Saudi Arabia", "Malaysia", "India", "Pakistan", "Kuwait", "Qatar", "Oman", "Singapore", "Canada", "Australia", "Germany"]
        reg_country = st.selectbox("Select Profile Country (Mandatory):", global_country_list, index=0)
        global_phone_flags = ["🇧🇩 +880 (Bangladesh)", "🇺🇸 +1 (United States)", "🇬🇧 +44 (United Kingdom)", "🇦🇪 +971 (UAE)", "🇸🇦 +966 (Saudi Arabia)", "🇲🇾 +60 (Malaysia)", "🇮🇳 +91 (India)", "🇵🇰 +92 (Pakistan)"]
        reg_flag_code = st.selectbox("Select Phone Flag Country Code:", global_phone_flags, index=0)
        reg_phone_raw = st.text_input("Mobile Number (Without Country Code):", key="reg_ph_num_raw").strip()
        reg_school = st.text_input("First School Name? (Security Answer Check):", key="reg_sch").strip()
        reg_sponsor = st.text_input("Sponsor Referral Token ID (Username or UID):", key="reg_s").strip()
        if st.button("Create account  →", key="reg_submit_btn"):
            st._central_user_creds = db_load("user_creds", {})
            if reg_username == "" or reg_password == "" or reg_email == "" or reg_school == "" or reg_phone_raw == "":
                st.error("Mandatory fields are blank! Process blocked.")
            elif reg_username in st._central_user_creds: st.error("Username already active!")
            else:
                new_uid = "UID-" + "".join(random.choices(string.digits, k=6))
                resolved_sponsor_uid = "None"
                if reg_sponsor != "":
                    resolved_sponsor_uid = reg_sponsor
                    if reg_sponsor in st._central_user_creds: resolved_sponsor_uid = st._central_user_creds[reg_sponsor].get("uid", reg_sponsor)
                    else:
                        for u_name, data in st._central_user_creds.items():
                            if data.get("uid") == reg_sponsor or u_name == reg_sponsor:
                                resolved_sponsor_uid = data.get("uid", reg_sponsor)
                                break
                full_mobile = f"{reg_flag_code.split(' ')[1]} {reg_phone_raw}"
                admin_fixed_bonus = float(db_load("admin_fixed_ref_usd", 10.0))
                st._central_user_creds[reg_username] = {"password": reg_password, "uid": new_uid, "email": reg_email, "country": reg_country, "phone": full_mobile, "school_answer": reg_school.lower(), "sponsor": resolved_sponsor_uid, "license_activated_before": False}
                st._uid_to_username[new_uid] = reg_username
                db_save("user_creds", st._central_user_creds)
                db_save("uid_to_user", st._uid_to_username)
                db_save(f"balance_{new_uid}", 5000.0)
                db_save(f"real_balance_{new_uid}", 0.0)
                db_save(f"win_{new_uid}", 0)
                db_save(f"loss_{new_uid}", 0)
                db_save(f"in_position_{new_uid}", False)
                db_save(f"buy_price_{new_uid}", 0.0)
                db_save(f"current_side_{new_uid}", "NONE")
                db_save(f"trade_coin_{new_uid}", "NONE")
                if resolved_sponsor_uid != "None" and st._ref_system_active:
                    st._global_referral_tree = db_load("referral_tree", {})
                    if resolved_sponsor_uid not in st._global_referral_tree: st._global_referral_tree[resolved_sponsor_uid] = []
                    if new_uid not in st._global_referral_tree[resolved_sponsor_uid]: st._global_referral_tree[resolved_sponsor_uid].append(new_uid)
                    db_save("referral_tree", st._global_referral_tree)
                    st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": resolved_sponsor_uid, "Coin": "REGISTRATION", "Action": "REF_COMMISSION_DIRECT", "Net P&L ($)": f"{admin_fixed_bonus:.2f}", "Type": "DEMO"})
                    db_save("pnl_history", st._global_user_pnl_history)
                st.success(f"Bound Identity Successful! UID Generated: {new_uid}")
        st.stop()
    elif auth_mode == "Recover":
        st.caption("Username ar security answer diye account recover koro.")
        f_user = st.text_input("Enter Username Handle to Recover:", key="forget_u_field").strip()
        f_school = st.text_input("Verification: First School Name?", key="forget_sch_field").strip()
        if st.button("⚡ Verify and Reveal Password", key="submit_forget_proc_btn"):
            st._central_user_creds = db_load("user_creds", {})
            if f_user in st._central_user_creds and st._central_user_creds[f_user].get("school_answer", "") == f_school.lower(): st.success(f"Identity Verified! Your Password is: **{st._central_user_creds[f_user]['password']}**")
            else: st.error("Verification parameters failed or mismatch!")
        st.stop()
        
    elif auth_mode == "Login":
        login_u = st.text_input("Username", key="log_u").strip()
        login_p = st.text_input("Password", type="password", key="log_p").strip()
        if st.button("Sign in  →", key="log_submit_btn"):
            st._central_user_creds = db_load("user_creds", {})
            if login_u in st._central_user_creds and st._central_user_creds[login_u]["password"] == login_p:
                st.session_state.logged_in_user = login_u
                st.query_params["session_user"] = login_u
                st.success("Access Granted!")
                st.rerun()
            else: st.error("Mismatch credentials input parameters!")
        st.stop()
user_data = st._central_user_creds[st.session_state.logged_in_user]
allocated_user_id = user_data["uid"]
my_sponsor_id = user_data["sponsor"]
my_profile_email = user_data.get("email", "Not Set")

# Persistent Firebase-Synced Trading States
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)
if 'win_count' not in st.session_state: st.session_state.win_count = db_load(f"win_{allocated_user_id}", 0)
if 'loss_count' not in st.session_state: st.session_state.loss_count = db_load(f"loss_{allocated_user_id}", 0)
if 'real_balance' not in st.session_state: st.session_state.real_balance = db_load(f"real_balance_{allocated_user_id}", 0.0)

st.session_state.in_position = db_load(f"in_position_{allocated_user_id}", False)
st.session_state.buy_price = db_load(f"buy_price_{allocated_user_id}", 0.0)
st.session_state.current_side = db_load(f"current_side_{allocated_user_id}", "NONE")
st.session_state.trade_coin = db_load(f"trade_coin_{allocated_user_id}", "NONE")

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#ffffff; font-size:13px; margin:0;'>👤 Handle Profile: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px; margin:4px 0;'>🆔 My Referral ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#00e676; font-size:12px; margin:0 0 4px 0;'>📧 Account Email: <b>{my_profile_email}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#94a3b8; font-size:12px; margin:0 0 12px 0;'>🔗 Sponsor UID Node: <b>{my_sponsor_id}</b></p>", unsafe_allow_html=True)
    
    if st.button("🚪 Logout Active Profile Handle Node", key="logout_sidebar_node_proc"):
        st.session_state.logged_in_user = None
        st.query_params.clear()
        st.rerun()
        
    bot_mode = st.radio("Trading Account Mode Settings:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Real Account API)"])
    is_real_live = "Live" in bot_mode
    exchange = st.selectbox("Exchange / Market:", EXCHANGES, index=min(int(db_load(f"exchange_idx_{allocated_user_id}", 0)), len(EXCHANGES) - 1), key="exchange_box",
                            help="Position khola thakle exchange bodlio na. Protita exchange er position/setting alada thake.")
    db_save(f"exchange_idx_{allocated_user_id}", EXCHANGES.index(exchange))
    exch_id = EXCHANGE_IDS[exchange]
    sticky_init(allocated_user_id, f"testnet_toggle_{exch_id}", _TN_DEFAULT[exch_id])
    if exch_id == "mt5": sticky_seed(allocated_user_id, "mt5_suffix_field")
    exch_sfx = "" if exch_id == "bybit" else f"_{exch_id}"
    mode_suffix = ("real" if is_real_live else "demo") + exch_sfx
    dashboard_mode_title = "Real Production Dashboard Mode 🟢" if is_real_live else "Demo Sandbox Dashboard Mode 🔵"

    # 🔒 মোড ভিত্তিক সম্পূর্ণ আলাদা আইসোলেটেড লকিং স্টেট
    in_position_state = db_load(f"in_position_{mode_suffix}_{allocated_user_id}", False)
    locked_trade_coin = db_load(f"trade_coin_{mode_suffix}_{allocated_user_id}", "NONE")
    
    if exch_id == "bybit":
        CATALOG = BYBYT_DATABASE_CORE
    else:
        CATALOG = fetch_exchange_coins(exch_id, bool(st.session_state.get(f"testnet_toggle_{exch_id}", _TN_DEFAULT[exch_id])) if is_real_live else False,
                                       st.session_state.get("mt5_suffix_field", "").strip() if exch_id == "mt5" else "")
        if "__error__" in CATALOG:
            st.error(f"{exchange} coin list ante parlam: {CATALOG['__error__'][:150]}. (Render region Singapore/Frankfurt hole bhalo; US block hote pare)")
            CATALOG = {k: v for k, v in BYBYT_DATABASE_CORE.items() if v["symbol"] in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")}
    coin_list = list(CATALOG.keys())
    if exch_id == "bybit" and is_real_live and st.session_state.get("testnet_toggle_bybit", False):
        try:   # testnet e jei coin live na, shegulo dropdown e dekhabo na (nahole "contract is not live" error)
            _live = set(fetch_testnet_live_symbols())
            _f = [k for k in coin_list if CATALOG[k]["symbol"] in _live]
            if _f: coin_list = _f
        except Exception:
            pass
    default_coin_idx = 0
    
    last_saved_db_coin = db_load(f"last_selected_coin_{mode_suffix}_{allocated_user_id}", "BTCUSDT")
    if in_position_state and locked_trade_coin != "NONE":
        last_saved_db_coin = locked_trade_coin

    for idx, k in enumerate(coin_list):
        v = CATALOG[k]
        if v["symbol"] == last_saved_db_coin:
            default_coin_idx = idx
            break

    if in_position_state:
        st.markdown(f"<div class='custom-box-grid' style='padding:10px; border-left:4px solid #38bdf8;'><b>🎯 Active Asset:</b> {last_saved_db_coin}</div>", unsafe_allow_html=True)
        coin_config = [v for v in CATALOG.values() if v["symbol"] == last_saved_db_coin][0]
        target_symbol = last_saved_db_coin
    else:
        selected_display_name = st.selectbox("Select Asset Contract Symbol Dropdown:", coin_list, index=default_coin_idx)
        coin_config = CATALOG[selected_display_name]
        target_symbol = coin_config["symbol"]
        db_save(f"trade_coin_{mode_suffix}_{allocated_user_id}", target_symbol)
        db_save(f"last_selected_coin_{mode_suffix}_{allocated_user_id}", target_symbol)

    ai_decision = st.toggle("AI Smart Crossover Filter Matrix", value=True)
    ai_mode = st.selectbox("AI Mode:", AI_MODES, index=min(int(db_load(f"ai_mode_idx_{allocated_user_id}", 0)), len(AI_MODES) - 1), key="ai_mode_box",
                           help="Secure: kom trade, 'perfect' setup lagbe. Balanced: trend + RSI mille trade. Turbo: sobsomoy trade (shudhu testnet/demo e pipeline test er jonno). Mainnet e shudhu Secure cholbe.")
    db_save(f"ai_mode_idx_{allocated_user_id}", AI_MODES.index(ai_mode))
    
    st.markdown("<b style='color:#38bdf8;'>🤖 OpenRouter AI Router Configuration:</b>", unsafe_allow_html=True)
    or_api_key = st.text_input("OpenRouter API Key:", type="password", value=db_load(f"or_key_{allocated_user_id}", ""), key="openrouter_api_key_field")
    or_model_id = st.text_input("Model ID:", value=db_load(f"or_model_{allocated_user_id}", "google/gemini-2.5-flash:free"), key="openrouter_model_id_field")
    if st.button("Save AI Router Node Config", key="save_or_config_btn"):
        db_save(f"or_key_{allocated_user_id}", or_api_key); db_save(f"or_model_{allocated_user_id}", or_model_id); st.toast("Config Saved!", icon="💾")
    ai_interval = st.number_input("AI signal interval (sec):", min_value=30, max_value=900, step=30, value=int(db_load(f"ai_interval_{allocated_user_id}", 120)), key="ai_interval_box")
    db_save(f"ai_interval_{allocated_user_id}", int(ai_interval))
    if st.button("🆓 Free model list dekhao (live)", key="free_models_btn"):
        try:
            st.session_state.free_models = fetch_free_models()
        except Exception as _e:
            st.session_state.free_models = []
            st.caption(f"List ante parlam na: {_e}")
    if st.session_state.get("free_models"):
        st.caption("Ekta ID copy kore upore 'Model ID' e boshao (comma diye 2-3 ta dile fallback hobe):")
        st.code("\n".join(st.session_state.free_models), language=None)
    
    max_leverage_bound = int(coin_config.get('max_leverage', 100))
    
    # 🔒 ডেমো ও রিয়ালের সেটিংস সম্পূর্ণ পৃথকীকরণ (text.file 12 মোড প্রোটেকশন)
    if in_position_state:
        leverage = db_load(f"leverage_lock_{mode_suffix}_{allocated_user_id}", 20)
        trade_amount = db_load(f"margin_lock_{mode_suffix}_{allocated_user_id}", 20)
        price_jump_target = db_load(f"tp_target_{mode_suffix}_{allocated_user_id}", float(coin_config["default_tp"]))
        stop_loss_gap = db_load(f"sl_gap_{mode_suffix}_{allocated_user_id}", float(coin_config["default_sl"]))
        
        st.markdown(f"""
        <div style="background-color:#1e293b; padding:12px; border-radius:8px; border-left: 4px solid #00e676; margin-top:10px;">
            <b style="color:#00e676; font-size:14px;">🔒 Position Active Parameter Lock</b><br>
            <span style="font-size:12px; color:#ffffff; font-family:monospace;">Leverage: {leverage}x | Margin: ${trade_amount}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        leverage = st.slider("Leverage Scale Selection Array (1x-100x Override):", min_value=1, max_value=max_leverage_bound, value=int(db_load(f"leverage_lock_{mode_suffix}_{allocated_user_id}", 20)), step=1, key="absolute_leverage_node_slider")
        trade_amount = st.number_input("Margin Requirement Block ($):", min_value=1, value=int(db_load(f"margin_lock_{mode_suffix}_{allocated_user_id}", 20)))
        _tp_db = f"tp_target_{mode_suffix}_{allocated_user_id}_{target_symbol}"
        _sl_db = f"sl_gap_{mode_suffix}_{allocated_user_id}_{target_symbol}"
        price_jump_target = st.number_input("Take Profit Target Interval ($):", value=float(db_load(_tp_db, float(coin_config["default_tp"]))), format="%.6f", key=f"tp_input_{mode_suffix}_{target_symbol}")
        stop_loss_gap = st.number_input("Stop Loss Boundary GAP Threshold ($):", value=float(db_load(_sl_db, float(coin_config["default_sl"]))), format="%.6f", key=f"sl_input_{mode_suffix}_{target_symbol}")
        db_save(_tp_db, price_jump_target)
        db_save(_sl_db, stop_loss_gap)
        
        db_save(f"leverage_lock_{mode_suffix}_{allocated_user_id}", leverage)
        db_save(f"margin_lock_{mode_suffix}_{allocated_user_id}", trade_amount)
        db_save(f"tp_target_{mode_suffix}_{allocated_user_id}", price_jump_target)
        db_save(f"sl_gap_{mode_suffix}_{allocated_user_id}", stop_loss_gap)

    api_key, secret_key, api_pass, mt5_region = "", "", "", "london"
    license_ok = False
    use_testnet = _TN_DEFAULT[exch_id]
    mainnet_ack = True
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><div style='background-color:#ff1744; padding:6px; border-radius:5px; text-align:center; margin-bottom:6px;'><b style='color:#ffffff; font-size:11px;'>🚨 LICENSE GATE ACTIVE</b></div>", unsafe_allow_html=True)
        input_license = sticky_text(allocated_user_id, "License Password:", "lic_field_sidebar", label_visibility="collapsed")
        if input_license in st._central_key_registry:
            if not user_data.get("license_activated_before", False) and my_sponsor_id != "None" and st._ref_system_active:
                st._central_user_creds[st.session_state.logged_in_user]["license_activated_before"] = True; db_save("user_creds", st._central_user_creds)
                admin_fixed_bonus = float(db_load("admin_fixed_ref_usd", 10.0))
                st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": my_sponsor_id, "Coin": "REAL_LICENSE_ACTIVATION", "Action": "REF_COMMISSION_DIRECT", "Net P&L ($)": f"{admin_fixed_bonus:.2f}", "Type": "REAL"}); db_save("pnl_history", st._global_user_pnl_history)
            license_ok = True
            if exch_id in ("bybit", "binance", "bitget"):
                _nm = EXCHANGE_NAMES[exch_id]
                use_testnet = sticky_check(allocated_user_id, f"🧪 {_nm} {'DEMO' if exch_id == 'bitget' else 'TESTNET'} (tick = test account, UNTICK = asol mainnet)", f"testnet_toggle_{exch_id}", _TN_DEFAULT[exch_id])
                api_key = sticky_text(allocated_user_id, f"{_nm} API Key:", f"api_field_{exch_id}")
                secret_key = sticky_text(allocated_user_id, f"{_nm} Secret Key:", f"sec_field_{exch_id}")
                if exch_id == "bitget":
                    api_pass = sticky_text(allocated_user_id, "Bitget API Passphrase:", "pass_field_bitget")
                if not use_testnet:
                    mainnet_ack = sticky_check(allocated_user_id, "⚠️ Ami bujhi eta ASOL taka. Loss hole daitto amar.", f"mainnet_ack_{exch_id}", False)
with st.sidebar:
    with st.expander("🩺 Server / Exchange connection check"):
        if st.button("Ekhon check koro", key="conn_check_btn"):
            _rows, _us = conn_check()
            for _n, _v in _rows: st.write(f"**{_n}:** {_v}")
            if _us: st.warning("Server USA te. Bybit/Binance/Bitget mainnet US IP block kore. Render e notun service banao Region = Singapore diye.")
    if is_real_live and st.button("🗑️ Saved API/License key muche felo", key="vault_clear_btn"):
        vault_clear(allocated_user_id); st.rerun()
# 🔥 লোগো ব্যানার পেজের একদম উপরে প্লেস করা হলো
if exch_id == "oanda":
    with st.sidebar:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><b style='color:#38bdf8;'>💱 OANDA Credentials</b>", unsafe_allow_html=True)
        st.caption("OANDA te price data-o token chhara ashe na, tai Demo mode e-o dorkar. Free Practice account diye shuru koro.")
        use_testnet = sticky_check(allocated_user_id, "🧪 OANDA PRACTICE account (age ekhane test koro)", "testnet_toggle_oanda", True)
        api_key = sticky_text(allocated_user_id, "OANDA API Token:", "api_field_oanda")
        secret_key = sticky_text(allocated_user_id, "OANDA Account ID (jemon 101-001-1234567-001):", "acct_field_oanda", secret=False)
        if is_real_live and not use_testnet:
            mainnet_ack = sticky_check(allocated_user_id, "⚠️ Ami bujhi eta ASOL taka. Loss hole daitto amar.", "mainnet_ack_oanda", False)
if exch_id == "mt5":
    with st.sidebar:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><b style='color:#38bdf8;'>📈 MT5 (MetaApi) Credentials</b>", unsafe_allow_html=True)
        st.caption("Exness/XM/IC Markets MT5 account metaapi.cloud e add kore nao (BETA: age DEMO account e test koro). Price data-o MetaApi theke ashe, tai Demo mode e-o dorkar.")
        use_testnet = sticky_check(allocated_user_id, "🧪 Ei MT5 account ta DEMO (age ekhane test koro)", "testnet_toggle_mt5", True)
        api_key = sticky_text(allocated_user_id, "MetaApi Token:", "api_field_mt5")
        secret_key = sticky_text(allocated_user_id, "MetaApi Account ID:", "acct_field_mt5", secret=False)
        mt5_region = sticky_text(allocated_user_id, "MetaApi Region (jemon london, new-york, singapore):", "region_field_mt5", secret=False, default="london") or "london"
        sticky_text(allocated_user_id, "Symbol suffix (Exness e prai 'm', na hole faka rakho):", "mt5_suffix_field", secret=False, help="Exness er onek account e symbol 'EURUSDm' hoy. MT5 er Market Watch e dekho.")
        _uuid = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
        if secret_key.startswith("eyJ") and _uuid.match(api_key):
            api_key, secret_key = secret_key, api_key
            st.info("🔄 Token ar Account ID ulte chhilo, ami thik kore nilam. Field gulo shothik jayga-y bosiye dao.")
        elif secret_key.startswith("eyJ"):
            st.error("❌ 'MetaApi Account ID' e tumi lomba Token (eyJ... diye shuru) boshiyecho. Account ID chhoto: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.")
        if is_real_live and not use_testnet:
            mainnet_ack = sticky_check(allocated_user_id, "⚠️ Ami bujhi eta ASOL taka. Loss hole daitto amar.", "mainnet_ack_mt5", False)
# (old banner replaced by pro_ui.hero below)

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011
live_price, current_rsi, ai_market_thesis, fig_candlestick = 0.0, 50.0, "SYNCING DATA FEED NODES... 📡", None
md_testnet = bool(use_testnet) if (is_real_live or exch_id in ("oanda", "mt5")) else False
exch_extra = api_pass if exch_id == "bitget" else (mt5_region if exch_id == "mt5" else "")
needs_creds_for_data = exch_id in ("oanda", "mt5")
md = make_data(exch_id, md_testnet, api_key if needs_creds_for_data else "", secret_key if needs_creds_for_data else "", exch_extra if exch_id == "mt5" else "")
real_engine, real_wallet, real_engine_error = None, None, ""
if is_real_live and license_ok and api_key and secret_key and (api_pass or exch_id != "bitget") and mainnet_ack:
    try:
        real_wallet = fetch_wallet_cached(exch_id, api_key, secret_key, use_testnet, exch_extra)
        real_engine = make_engine(exch_id, api_key, secret_key, use_testnet, exch_extra)
        st.session_state.real_balance = real_wallet["equity"]
    except Exception as e:
        real_engine, real_wallet, real_engine_error = None, None, str(e)
_ban_persist()
df_kline = pd.DataFrame()
data_error = ""
if needs_creds_for_data and not (api_key and secret_key):
    data_error = f"{exchange} price data er jonno sidebar e Token + Account ID dao."
else:
    rows = []
    try:
        _snap = feed_snapshot(exch_id, md_testnet, target_symbol, api_key if needs_creds_for_data else "", secret_key if needs_creds_for_data else "", exch_extra if exch_id == "mt5" else "")
        md.tradeable, md.spread = _snap["tradeable"], _snap["spread"]
        live_price, rows, data_error = float(_snap["price"] or 0.0), _snap["rows"], _snap["error"]
    except Exception as _e:
        data_error = str(_e)
    try:
        if rows:
            df_kline = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            if live_price == 0.0: live_price = df_kline['close'].iloc[-1]
            delta = df_kline['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            current_rsi = (100 - (100 / (1 + (gain / (loss + 1e-10))))).iloc[-1]
            fig_candlestick = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'])])
            fig_candlestick.add_trace(go.Scatter(x=df_kline.index, y=df_kline['close'].rolling(window=7).mean(), name="AI Geometric Tracking Vector", line=dict(color='#00e676', width=2, dash='dot')))
            fig_candlestick.update_layout(template="plotly_dark", margin=dict(l=6, r=6, t=6, b=6), height=250, xaxis_rangeslider_visible=False, paper_bgcolor='#06090e', plot_bgcolor='#06090e')
    except Exception as _e:
        data_error = data_error or str(_e)
if live_price == 0.0 and not df_kline.empty: live_price = float(df_kline['close'].iloc[-1])
if data_error and live_price == 0.0:
    st.warning(f"📡 {exchange}: price data ante parlam ({data_error[:180]})")
if not getattr(md, "tradeable", True):
    st.warning("⛔ Forex market ekhon bondho (weekend/holiday). Market khulle trade hobe.")
# ==========================================
# 🧱 BOX 17: REAL-TIME CHART RENDERING INTERFACE
# ==========================================
chart_display_box = st.container()
with chart_display_box:
    _pz_dec = 2 if live_price >= 1000 else (4 if live_price >= 1 else 6)
    _pz_bal = float(real_wallet["equity"]) if (is_real_live and real_wallet) else float(st.session_state.get("real_balance" if is_real_live else "demo_balance", 0.0))
    st.session_state.setdefault("_pz_t0", time.time())
    st.session_state.setdefault("_pz_bal0", _pz_bal)
    _pz_job = _ai_store().get(f"{allocated_user_id}_{mode_suffix}") or {}
    _pz_run = bool(db_load(f"bot_active_{mode_suffix}_{allocated_user_id}", False))
    _pz_in = bool(st.session_state.get("in_position", False))
    _pz_tp, _pz_sl = float(globals().get("price_jump_target", 0) or 0), float(globals().get("stop_loss_gap", 0) or 0)
    _pz_ai_state, _pz_ai_txt = ("idle", "off") if not ai_decision else (("active", "thinking...") if _pz_job.get("status") == "running" else (("bad", "FAIL") if _pz_job.get("signal") == "FAIL" else (("ok", str(_pz_job.get("signal"))) if _pz_job else ("idle", "waiting"))))
    st.markdown(pro_ui.hero(_pz_bal, "REAL" if is_real_live else "DEMO", EXCHANGE_NAMES[exch_id], target_symbol, _pz_run,
                            time.time() - st.session_state["_pz_t0"], st.session_state.get("win_count", 0), st.session_state.get("loss_count", 0),
                            _pz_bal - st.session_state["_pz_bal0"], "IN TRADE" if _pz_in else ("SCANNING" if _pz_run else "IDLE")), unsafe_allow_html=True)
    st.markdown(pro_ui.pipeline([
        ("feed", "DATA FEED", "ok" if (live_price > 0 and not data_error) else ("warn" if live_price > 0 else "bad"), f"{live_price:,.{_pz_dec}f}" if live_price > 0 else "no data"),
        ("signal", "INDICATORS", "warn" if (current_rsi >= 70 or current_rsi <= 30) else ("ok" if not df_kline.empty else "idle"), f"RSI {current_rsi:.1f}"),
        ("ai", "AI SWARM", _pz_ai_state, _pz_ai_txt),
        ("exec", "EXECUTOR", "active" if _pz_in else ("ok" if _pz_run else "idle"), f"{st.session_state.get('current_side', '')} open" if _pz_in else ("armed" if _pz_run else "stopped")),
        ("risk", "RISK", "ok", f"TP {_pz_tp:g} - SL {_pz_sl:g}"),
        ("log", "LOGGER", "ok", f"#{len(st.session_state.engine_logs)}"),
    ]), unsafe_allow_html=True)
    _pz_entry = float(st.session_state.get("buy_price", 0) or 0) if _pz_in else 0.0
    _pz_sg = 1 if "LONG" in str(st.session_state.get("current_side", "")) else -1
    _pz_fig = pro_ui.pro_chart(df_kline, _pz_entry, (_pz_entry + _pz_sg * _pz_tp) if _pz_entry else None, (_pz_entry - _pz_sg * _pz_sl) if _pz_entry else None) if not df_kline.empty else None
    if _pz_fig is not None:
        st.plotly_chart(_pz_fig, use_container_width=True)
    elif fig_candlestick:
        st.plotly_chart(fig_candlestick, use_container_width=True)
st.markdown(f"<div class='custom-box-grid' style='background-color:#050a12; border:1px solid #00e676; padding: 22px;'><div class='matrix-neon-text' style='font-size:14px;'>🧬 <b>DEEPSEEK REAL-TIME SWARM INTERFACE LAYER:</b><br>🔮 DEEPEST OPENROUTER ROUTER SCALPER LABELS ACTIVATED ({target_symbol})</div></div>", unsafe_allow_html=True)
local_win = st.session_state.get('win_count', 0)
local_loss = st.session_state.get('loss_count', 0)
total_trades = local_win + local_loss
win_rate = (local_win / total_trades * 100) if total_trades > 0 else 0.0

# (old WON/LOST bar replaced by pro_ui.stats_panel)

if not is_real_live:
    st.markdown(pro_ui.section('Sandbox Funds', 'demo balance manager'), unsafe_allow_html=True)
    cb_col1, cb_col2 = st.columns(2)
    with cb_col1: custom_balance_input = st.number_input("Input Target Amount to Load:", min_value=1.0, value=float(st.session_state.get('demo_balance', 5000.0)), key="sandbox_balance_changer")
    with cb_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Set Balance Amount", key="submit_custom_balance_btn"):
            st.session_state.demo_balance = custom_balance_input; db_save(f"balance_{allocated_user_id}", st.session_state.demo_balance); st.rerun()
floating_pnl = 0.0
if st.session_state.in_position and live_price > 0 and st.session_state.buy_price > 0:
    if "LONG" in st.session_state.current_side: floating_pnl = ((live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price))
    else: floating_pnl = ((st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price))


# ==========================================
# 🧱 BOX 15: GLOBAL PIPELINE SYNC & REAL-TIME FLOATING OVERLAY ENGINE
# ==========================================
# গ্লোবাল সেশন এবং মোড আইসোলেশন লেয়ার সিঙ্ক্রোনাইজেশন
st.session_state.in_position = db_load(f"in_position_{mode_suffix}_{allocated_user_id}", False)
st.session_state.buy_price = db_load(f"buy_price_{mode_suffix}_{allocated_user_id}", 0.0)
st.session_state.current_side = db_load(f"current_side_{mode_suffix}_{allocated_user_id}", "NONE")
st.session_state.trade_coin = db_load(f"trade_coin_{mode_suffix}_{allocated_user_id}", target_symbol)

# মোড ভিত্তিক লাইভ ক্যালকুলেটর রান এবং গাণিতিক সমীকরণ রিকভারি
leverage = db_load(f"leverage_lock_{mode_suffix}_{allocated_user_id}", 20)
trade_amount = db_load(f"margin_lock_{mode_suffix}_{allocated_user_id}", 20)
price_jump_target = db_load(f"tp_target_{mode_suffix}_{allocated_user_id}", 0.01)
stop_loss_gap = db_load(f"sl_gap_{mode_suffix}_{allocated_user_id}", 0.02)
effective_vol = trade_amount * leverage

# 🔄 রিয়েল-টাইম লাইভ টিকের ট্র্যাকিং আনফ্রিজার (০.০০০০ বাগ ফিক্স গেট)
floating_pnl = 0.0
if st.session_state.in_position and live_price > 0 and st.session_state.buy_price > 0:
    if "LONG" in st.session_state.current_side:
        floating_pnl = ((live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price))
    else:
        floating_pnl = ((st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price))

# ==========================================
# 🔁 TRADE ENGINE HELPERS (open / close / TP-SL sync)
# ==========================================
_rerun_after = False
try:
    FEE_RATE_ROUNDTRIP = float(md.cost_frac(target_symbol, live_price or 1.0))   # Bybit 0.11%, Binance 0.10%, OANDA = spread/price
except Exception:
    FEE_RATE_ROUNDTRIP = 0.0011

def release_and_record(net_pnl, symbol, reason):
    """Trade bondho hole: balance (demo), win/loss, ledger, position state sob update."""
    uid = allocated_user_id
    net_pnl = float(net_pnl)
    if not is_real_live:
        new_bal = float(db_load(f"balance_{uid}", 5000.0)) + net_pnl
        db_save(f"balance_{uid}", new_bal)
        st.session_state.demo_balance = new_bal
    if net_pnl >= 0:
        w = int(db_load(f"win_{uid}", 0)) + 1
        db_save(f"win_{uid}", w); st.session_state.win_count = w
    else:
        lo = int(db_load(f"loss_{uid}", 0)) + 1
        db_save(f"loss_{uid}", lo); st.session_state.loss_count = lo
    history = db_load("pnl_history", [])
    history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": uid, "Coin": symbol,
                    "Action": f"TRADE_{reason}", "Net P&L ($)": f"{net_pnl:.4f}", "Type": "REAL" if is_real_live else "DEMO"})
    st._global_user_pnl_history = history
    db_save("pnl_history", history)
    db_save(f"in_position_{mode_suffix}_{uid}", False)
    db_save(f"buy_price_{mode_suffix}_{uid}", 0.0)
    db_save(f"current_side_{mode_suffix}_{uid}", "NONE")
    db_save(f"trade_coin_{mode_suffix}_{uid}", "NONE")
    st.session_state.in_position = False
    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Closed {symbol} ({reason}) Net P&L: {net_pnl:+.4f} USDT")

def fetch_real_pnl(symbol):
    since_ms = int(db_load(f"real_open_ms_{mode_suffix}_{allocated_user_id}", 0))
    try:
        real_engine.after_close(symbol)   # Binance: baki TP/SL order batil
    except Exception:
        pass
    for _ in range(4):
        info = real_engine.last_closed_pnl(symbol, since_ms)
        if info: return info["pnl"], True
        time.sleep(0.8)
    return 0.0, False

def open_trade(side):
    """LONG / SHORT position open. Demo = virtual, Real = Bybit e asol order (TP/SL soho). Returns (ok, message)."""
    uid = allocated_user_id
    entry = float(live_price)
    if is_real_live:
        if real_engine is None:
            return False, "Real mode: License key + Bybit API key/secret lagbe."
        if real_wallet and real_wallet["available"] < float(trade_amount):
            return False, f"Available balance ${real_wallet['available']:.2f} < margin ${trade_amount}"
        try:
            res = real_engine.open_position(target_symbol, side, float(trade_amount), int(leverage), float(price_jump_target), float(stop_loss_gap))
        except Exception as e:
            return False, f"Bybit order failed: {e}"
        entry = float(res["entry_price"])
        st.session_state.real_open_ts = time.time()
        db_save(f"real_open_ms_{mode_suffix}_{uid}", int(res.get("opened_ms") or time.time() * 1000))
    elif entry <= 0:
        return False, "Live price ekhono ashe nai."
    db_save(f"in_position_{mode_suffix}_{uid}", True)
    db_save(f"buy_price_{mode_suffix}_{uid}", entry)
    db_save(f"current_side_{mode_suffix}_{uid}", side)
    db_save(f"trade_coin_{mode_suffix}_{uid}", target_symbol)
    db_save(f"leverage_lock_{mode_suffix}_{uid}", leverage)
    db_save(f"margin_lock_{mode_suffix}_{uid}", trade_amount)
    db_save(f"tp_target_{mode_suffix}_{uid}", price_jump_target)
    db_save(f"sl_gap_{mode_suffix}_{uid}", stop_loss_gap)
    st.session_state.in_position = True
    st.session_state.buy_price = entry
    st.session_state.current_side = side
    return True, f"{side} {target_symbol} @ {entry}"

# ---- TP/SL sync: position khola thakle protibar check ----
pos_symbol = st.session_state.trade_coin if st.session_state.trade_coin not in ("NONE", "", None) else target_symbol
if st.session_state.in_position:
    if is_real_live:
        # TP/SL Bybit er server e ache. Amra shudhu dekhi position bondho hoyeche kina.
        if real_engine is not None:
            try:
                _rp = real_engine.get_position(pos_symbol)
                if _rp:
                    floating_pnl = _rp["unrealised_pnl"]
                elif time.time() - st.session_state.get("real_open_ts", 0) > 12:
                    _pnl, _found = fetch_real_pnl(pos_symbol)
                    release_and_record(_pnl, pos_symbol, "BYBIT_TPSL_CLOSE")
                    st.rerun()
            except Exception as e:
                st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Bybit sync error: {e}")
    else:
        # Demo: price TP/SL e gele auto close
        _entry = float(st.session_state.buy_price)
        if _entry > 0 and live_price > 0:
            _is_long = "LONG" in st.session_state.current_side
            _tp_hit = live_price >= _entry + price_jump_target if _is_long else live_price <= _entry - price_jump_target
            _sl_hit = live_price <= _entry - stop_loss_gap if _is_long else live_price >= _entry + stop_loss_gap
            if _tp_hit or _sl_hit:
                _gap = price_jump_target if _tp_hit else -stop_loss_gap
                _net = _gap * (effective_vol / _entry) - effective_vol * FEE_RATE_ROUNDTRIP
                release_and_record(_net, pos_symbol, "TP_HIT" if _tp_hit else "SL_HIT")
                st.rerun()


# একক সিকিউর এভেলেবল ব্যালেন্স উইজেট (লাইভ ফ্লোটিং P&L সহ)
if is_real_live:
    _bal_val = real_wallet["equity"] if real_wallet else 0.0
else:
    _bal_val = st.session_state.get('demo_balance', 5000.0) + floating_pnl
balance_usd_text = f"${_bal_val:,.2f} USDT"
st.markdown(f"<div class='custom-box-grid'>💰 <b>AVAILABLE BALANCE ({bot_mode}):</b> <h2 style='margin:0; color:#fff;'>{balance_usd_text}</h2><p style='margin:0; font-size:14px; color:{'#00e676' if floating_pnl >= 0 else '#ff1744'}; font-weight:bold;'>Live Floating P&L Indicator: {floating_pnl:+.4f} USDT</p></div>", unsafe_allow_html=True)
if is_real_live:
    if real_engine_error: st.error(f"{exchange} connect error: {real_engine_error}")
    elif license_ok and api_key and secret_key and not use_testnet and not mainnet_ack: st.warning("⚠️ ASOL taka (mainnet) mode: sidebar er 'Ami bujhi eta ASOL taka' tick na dile trade shuru hobe na.")
    elif license_ok and exch_id == "bitget" and api_key and secret_key and not api_pass: st.info("🔑 Bitget er jonno API Passphrase-o dao (key banano-r somoy je password dichhile).")
    elif real_engine is None: st.info(f"🔒 Real mode: sidebar e License Password dao, tarpor {exchange} er API credentials dao. Tahole {exchange} er asol balance ekhane ashbe.")
    else:
        st.caption(f"🔗 {exchange} {'TESTNET/PRACTICE 🧪' if use_testnet else 'LIVE 🔴'} connected | Equity: ${real_wallet['equity']:,.2f} | Available: ${real_wallet['available']:,.2f} USDT")
        if real_wallet["equity"] == 0 and not real_wallet.get("raw", {}).get("coins_returned"):
            _uid = (real_wallet.get("raw", {}).get("API_KEY_INFO") or {}).get("userID", "?")
            st.warning(f"⚠️ Ei API key er {exchange} account (UID: {_uid}) e kono coin nei. Jei {'testnet' if use_testnet else 'mainnet'} account e USDT ache, **oi account e login kore** notun API key banao.")
        with st.expander("🔍 Wallet raw data (debug)"):
            st.json(real_wallet.get("raw", {}))
if live_price > 0 and effective_vol > 0:
    _fee = effective_vol * FEE_RATE_ROUNDTRIP
    _net_win = price_jump_target / live_price * effective_vol - _fee
    _net_loss = stop_loss_gap / live_price * effective_vol + _fee
    _be = (_net_loss / (_net_win + _net_loss) * 100) if (_net_win + _net_loss) > 0 else 100.0
    _sl_pct, _liq_pct = stop_loss_gap / live_price * 100, 80.0 / max(int(leverage), 1)
    if _sl_pct >= _liq_pct:
        st.error(f"🛑 Stop Loss ({_sl_pct:.2f}%) liquidation distance (~{_liq_pct:.2f}% @ {leverage}x) er cheye dure. SL trigger hobar age-i position liquidate hobe. Leverage komao ba SL chhoto koro.")
    if _net_win <= 0:
        st.error(f"🛑 TP jitleo fee (${_fee:.2f}) kate loss hobe (net {_net_win:+.2f}). TP onek barao.")
    elif _be > 60:
        st.warning(f"⚠️ Fee soho: jitle ~+${_net_win:.2f}, harle ~-${_net_loss:.2f}. Break-even korte **{_be:.0f}% trade jitte hobe**. TP barao ba SL komao.")
    else:
        st.caption(f"ℹ️ Fee soho: jitle +${_net_win:.2f} | harle -${_net_loss:.2f} | break-even win rate {_be:.0f}%")

position_overlay_container = st.container()
with position_overlay_container:
    if st.session_state.in_position:
        current_entry_price = st.session_state.buy_price
        current_active_side = st.session_state.current_side
        
        is_long_pos = "LONG" in current_active_side
        live_target = (current_entry_price + price_jump_target) if is_long_pos else (current_entry_price - price_jump_target)
        live_sl = (current_entry_price - stop_loss_gap) if is_long_pos else (current_entry_price + stop_loss_gap)
        
        est_profit_dollars = (price_jump_target * (effective_vol / (current_entry_price if current_entry_price > 0 else 1.0)))
        est_loss_dollars = (stop_loss_gap * (effective_vol / (current_entry_price if current_entry_price > 0 else 1.0)))
        
        st.markdown(f"""
        <div style="background-color:#0b0e14; padding:15px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; border-left: 5px solid #29b6f6; box-shadow: 0 0 10px rgba(41, 182, 246, 0.15);">
            <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Active Contract Asset: <b>{st.session_state.trade_coin}</b></span><br>
            <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Entry Target Metric: {current_entry_price:.6f} | Live Index Ticker: {live_price:.6f}</span><br>
            <span style="font-size:14px; color:#00e676; font-weight:bold; font-family: monospace;">Take Profit Limit: {live_target:.6f} (Estimated Gain: +${est_profit_dollars:.2f} USDT)</span><br>
            <span style="font-size:14px; color:#ff1744; font-weight:bold; font-family: monospace;">Stop Loss Boundary Node: {live_sl:.6f} (Estimated Loss: -${est_loss_dollars:.2f} USDT)</span>
        </div>
        """, unsafe_allow_html=True)
# 🔥 FULLY ACCURATE ISOLATION CHANNELS FOR DEMO & REAL TRADES
mode_suffix = ("real" if is_real_live else "demo") + exch_sfx
cloud_bot_trigger = db_load(f"bot_active_{mode_suffix}_{allocated_user_id}", False) if (allocated_user_id and allocated_user_id != "NONE") else st.session_state.get(f"bot_active_{mode_suffix}", False)

st.session_state.in_position = db_load(f"in_position_{mode_suffix}_{allocated_user_id}", False)
st.session_state.buy_price = db_load(f"buy_price_{mode_suffix}_{allocated_user_id}", 0.0)
st.session_state.current_side = db_load(f"current_side_{mode_suffix}_{allocated_user_id}", "NONE")
if cloud_bot_trigger and allocated_user_id != "NONE":
    or_api_key = db_load(f"or_key_{allocated_user_id}", "")
    or_model_id = db_load(f"or_model_{allocated_user_id}", "")
    _store = _ai_store()
    _jk = f"{allocated_user_id}_{mode_suffix}"
    _job = _store.get(_jk)

    def _try_open(sig, label):
        ok, msg = open_trade(sig)
        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] {'Order opened' if ok else 'Order blocked'}: {msg}")
        if ok:
            st.toast(f"{label} ({sig})", icon="🚀")
            if not st.session_state.first_trade_done:
                st.session_state.first_trade_done = True
                db_save(f"first_done_{allocated_user_id}", True)
        return ok

    # (1) background AI job shesh hole tar uttor ekhane nei
    if _job and _job.get("status") == "done" and not _job.get("consumed"):
        _job["consumed"] = True
        for _l in _job.get("logs", []):
            st.session_state.engine_logs.append(_l)
        if _job.get("daily_exhausted"):
            _store[_jk + "_pause"] = (int(time.time() // 86400) + 1) * 86400
            st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] OpenRouter free DAILY limit shesh. 00:00 UTC (Bangladesh e shokal 6:00) porjonto AI bondho. $10 credit dile 1000/din hoy.")
        elif not st.session_state.in_position and time.time() - _job.get("finished", 0) < 120 and _job.get("symbol") == target_symbol:
            _sig = _job.get("signal", "FAIL")
            if _sig == "FAIL":
                st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] AI unavailable ({str(_job.get('err', ''))[:150]})")
                if is_real_live:
                    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Real mode: AI uttor dey nai, tai kono trade kora holo na (HOLD).")
                else:
                    _local = "LONG" if current_rsi < 45 else ("SHORT" if current_rsi > 55 else "HOLD")
                    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Demo RSI backup signal: '{_local}' for {target_symbol}")
                    if _local in ("LONG", "SHORT") and _try_open(_local, "⚡ Technical Latch Executed"):
                        _rerun_after = True
            else:
                _resolved = _sig
                if _resolved == "HOLD" and not st.session_state.first_trade_done and not is_real_live:
                    _resolved = "LONG" if current_rsi < 50 else "SHORT"
                st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Active Signal: '{_resolved}'")
                if _resolved in ("LONG", "SHORT") and _try_open(_resolved, "🟢 AI Order Triggered"):
                    _rerun_after = True

    # (2) notun AI job shuru (background thread, page block hobe na)
    _running = bool(_job) and _job.get("status") == "running" and time.time() - _job.get("started", 0) < 150
    _paused = time.time() < _store.get(_jk + "_pause", 0)
    _eff_mode = pick_ai_mode(ai_mode, is_real_live and not use_testnet)
    _neutral = _eff_mode == AI_MODES[0] and bool(st.session_state.first_trade_done) and 45 <= float(current_rsi) <= 55   # RSI neutral: AI ke dakbo na (free limit bachano)
    if (not st.session_state.in_position and ai_decision and or_api_key and not _running and not _paused and not _neutral
            and time.time() - st.session_state.get("last_ai_ts", 0) > ai_interval
            and not df_kline.empty and len(df_kline) >= 5):
        st.session_state.last_ai_ts = time.time()
        news_context = "Steady global macro trend line pattern."
        try:
            if os.environ.get("CRYPTOPANIC_KEY"):
                _nr = requests.get(f"https://cryptopanic.com/api/v1/posts/?auth_token={os.environ.get('CRYPTOPANIC_KEY')}&public=true", timeout=3)
                if _nr.status_code == 200:
                    _titles = [p.get('title', '') for p in _nr.json().get('results', [])[:4]]
                    if _titles: news_context = " | ".join(_titles)
        except Exception: pass
        recent_candles = df_kline.tail(5).to_dict(orient="records")
        ma_series = df_kline['close'].rolling(window=7).mean()
        last_ma = float(ma_series.iloc[-1]) if not ma_series.empty else live_price
        ai_label, mode_instruction = build_mode_instruction(_eff_mode, bool(st.session_state.first_trade_done))
        market_context_prompt = (
            f"Asset: {target_symbol} | Live Price: {live_price} | RSI: {current_rsi:.2f} | MA-7: {last_ma:.6f}\n"
            f"News Summary: {news_context}\n"
            f"Matrix -> Leverage: {leverage}x, TP: {price_jump_target}, SL: {stop_loss_gap}\n"
            f"Candlesticks: {json.dumps(recent_candles)}\n\n"
            f"{mode_instruction}\n\n"
            f"RESPOND SYSTEM RULES: Output EXACTLY ONE UPPERCASE WORD: 'LONG' or 'SHORT' or 'HOLD'. No extra words."
        )
        _models = [m.strip() for m in str(or_model_id).replace("\n", ",").split(",") if m.strip()][:3]
        _store[_jk] = {"status": "running", "started": time.time(), "symbol": target_symbol, "consumed": False, "logs": []}
        threading.Thread(target=_ai_job, args=(_store, _jk, or_api_key, _models, market_context_prompt, target_symbol), daemon=True).start()
        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] {ai_label} AI request background e pathano holo...")
if _rerun_after:
    st.rerun()
# --- 🪐 PRO HUD: KPIs + position + stats + equity + terminal ---
_k_bal = float(real_wallet["equity"]) if (is_real_live and real_wallet) else float(st.session_state.get("real_balance" if is_real_live else "demo_balance", 0.0))
_k_w, _k_l = st.session_state.get("win_count", 0), st.session_state.get("loss_count", 0)
_k_wr = (_k_w / (_k_w + _k_l) * 100) if (_k_w + _k_l) else 0.0
_k_dec = 2 if live_price >= 1000 else (4 if live_price >= 1 else 6)
st.markdown(pro_ui.kpis([
    ("Balance", f"${_k_bal:,.2f}", "real wallet" if is_real_live else "demo wallet", "#38bdf8", ""),
    ("Floating PnL", f"{floating_pnl:+.2f}$", "open trade" if st.session_state.in_position else "no position", "#22f2a0" if floating_pnl >= 0 else "#ff4d6d", "pos" if floating_pnl > 0 else ("neg" if floating_pnl < 0 else "flat")),
    ("Win rate", f"{_k_wr:.1f}%", f"{_k_w}W / {_k_l}L", "#a78bfa", ""),
    ("Leverage", f"{leverage}x", f"margin ${trade_amount}", "#f5a623", ""),
    ("Live price", f"{live_price:,.{_k_dec}f}", target_symbol, "#243553", ""),
]), unsafe_allow_html=True)
_pc1, _pc2 = st.columns([2, 1])
with _pc1:
    st.markdown(pro_ui.position_card(pos_symbol, bool(st.session_state.in_position), st.session_state.current_side, float(st.session_state.buy_price or 0), live_price,
                                     float(price_jump_target), float(stop_loss_gap), floating_pnl, effective_vol, leverage, _k_dec), unsafe_allow_html=True)
with _pc2:
    st.markdown(pro_ui.stats_panel(_k_w, _k_l, float(current_rsi), f"spread {getattr(md, 'spread', 0) or 0:g}"), unsafe_allow_html=True)
try:
    _eq = [float(r.get("Net P&L ($)", 0)) for r in (st._global_user_pnl_history or [])
           if str(r.get("User ID")) == str(allocated_user_id) and r.get("Type") == ("REAL" if is_real_live else "DEMO") and "COMMISSION" not in str(r.get("Action", ""))]
    _eq_fig = pro_ui.equity_chart(_eq) if len(_eq) >= 2 else None
    if _eq_fig is not None:
        st.markdown("<div class='pz-h' style='margin-top:4px'><span>EQUITY CURVE &middot; <b>CUMULATIVE NET P&L</b></span></div>", unsafe_allow_html=True)
        st.plotly_chart(_eq_fig, use_container_width=True)
except Exception:
    pass
st.markdown(pro_ui.terminal(st.session_state.engine_logs), unsafe_allow_html=True)
if allocated_user_id and allocated_user_id != "NONE":
    _sj, _sk = _ai_store().get(f"{allocated_user_id}_{mode_suffix}"), f"{allocated_user_id}_{mode_suffix}_pause"
    if time.time() < _ai_store().get(_sk, 0):
        st.caption("⏸ OpenRouter free daily limit shesh. Kal 00:00 UTC (Bangladesh e shokal 6:00) e abar chalu hobe. (Log er somoy = UTC, Bangladesh = UTC+6)")
    elif _sj and _sj.get("status") == "running":
        st.caption(f"⏳ AI uttor opekkha korchi... (shuru {time.strftime('%H:%M:%S', time.localtime(_sj['started']))} UTC)")
    elif _sj:
        st.caption(f"{'✅' if _sj.get('signal') != 'FAIL' else '❌'} Last AI: {_sj.get('signal')} | model: {_sj.get('model') or '-'} | {str(_sj.get('err', ''))[:90]}")

# --- 🕹️ RESTORE FIXED MANUAL TRADING PANEL MATRIX ---
# --- 🕹️ RESTORE FIXED MANUAL TRADING PANEL MATRIX ---
# --- 🕹️ RESTORE FIXED MANUAL TRADING PANEL MATRIX ---
# --- 🕹️ RESTORE FIXED MANUAL TRADING PANEL MATRIX ---
if not ai_decision and not st.session_state.get("in_position", False):
    st.markdown("<p style='color:#ffcc00; font-weight:bold;'>🕹️ Manual Trading Panel Active</p>", unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        if st.button("🟢 EXECUTE BUY / LONG ENTRY", key="manual_long_gate"):
            ok, msg = open_trade("LONG")
            if ok: st.rerun()
            else: st.error(msg)
    with m_col2:
        if st.button("🔴 EXECUTE SELL / SHORT ENTRY", key="manual_short_gate"):
            ok, msg = open_trade("SHORT")
            if ok: st.rerun()
            else: st.error(msg)
c1, c2 = st.columns(2)
with c1:
    if not cloud_bot_trigger:
        if st.button(f"🟢 START ENGINE SCALPER LOOP SEQUENCE ({mode_suffix.upper()})", key=f"start_latch_{mode_suffix}"):
            db_save(f"bot_active_{mode_suffix}_{allocated_user_id}", True)
            st.session_state[f"bot_active_{mode_suffix}"] = True
            st.rerun()
    else:
        if st.button(f"🔴 STOP ENGINE SCALPER LOOP SEQUENCE ({mode_suffix.upper()})", key=f"stop_latch_{mode_suffix}"):
            db_save(f"bot_active_{mode_suffix}_{allocated_user_id}", False)
            st.session_state[f"bot_active_{mode_suffix}"] = False
            st.rerun()
with c2:
    if st.button("🚨 EMERGENCY LIQUIDATE CLOSE ORDER POSITION", disabled=not st.session_state.in_position, key="force_liquidate_btn"):
        if is_real_live:
            if real_engine is None:
                st.error("Real mode: Bybit API key connect kora nai.")
            else:
                try:
                    real_engine.close_position(pos_symbol)
                    time.sleep(1.0)
                    _pnl, _found = fetch_real_pnl(pos_symbol)
                    release_and_record(_pnl, pos_symbol, "MANUAL_CLOSE")
                    st.toast("🚨 Bybit position closed", icon="⚡")
                    st.rerun()
                except Exception as e:
                    st.error(f"Bybit close failed: {e}")
        else:
            _net = floating_pnl - (effective_vol * FEE_RATE_ROUNDTRIP)
            release_and_record(_net, pos_symbol, "MANUAL_CLOSE")
            st.toast("🚨 Position Liquidated & Balance Synced!", icon="⚡")
            st.rerun()

if st_autorefresh is not None:
    st_autorefresh(interval=AUTO_REFRESH_MS, key="live_tick_refresh")
else:
    st.caption("⚠️ Auto refresh off: requirements.txt e 'streamlit-autorefresh' add koro.")
# --- 🧬 100% RESTORE NAMEERROR: RE-DEFINED LOST CALCULATOR FUNCTION ---
def calculate_sub_generations(r_uid, tree):
    g_map = {"Gen 1": [], "Gen 2": [], "Gen 3": [], "Gen 4": [], "Gen 5": [], "Gen 6": [], "Gen 7": []}
    actual_search_uid = r_uid
    for uname, data in st._central_user_creds.items():
        if uname == r_uid or data.get("uid") == r_uid:
            actual_search_uid = data.get("uid")
            break
    if actual_search_uid in tree: g_map["Gen 1"] = list(tree[actual_search_uid])
    for idx in range(2, 8):
        prev_name = f"Gen {idx-1}"
        current_name = f"Gen {idx}"
        p_layer = g_map.get(prev_name, [])
        c_accum = []
        for p_uid in p_layer:
            if p_uid in tree:
                for c_uid in tree[p_uid]:
                    if c_uid not in c_accum: c_accum.append(c_uid)
        g_map[current_name] = c_accum
    return g_map
# --- 🌿 RESTORE NETWORK MARKETING MATRIX PANELS ---
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown(pro_ui.section('Network Marketing Desk', f'referral & 7-generation commissions · {dashboard_mode_title}'), unsafe_allow_html=True)
search_uid_input = st.text_input("Enter Target Member UID box input:", value=allocated_user_id, key="custom_uid_search_field_node").strip()

mode_filter_string = "REAL" if is_real_live else "DEMO"
ref_accum, gen_accum = 0.0, 0.0
if st._global_user_pnl_history:
    for r in st._global_user_pnl_history:
        try:
            if str(r.get("User ID")).strip() == str(search_uid_input).strip():
                action_str = r.get("Action", "")
                pnl_val = float(r.get("Net P&L ($)", 0))
                if "GEN_COMMISSION" in action_str and r.get("Type") == mode_filter_string: gen_accum += pnl_val
                elif "REF_COMMISSION" in action_str and r.get("Type") == mode_filter_string: ref_accum += pnl_val
        except: pass

cbx1, cbx2 = st.columns(2)
with cbx1: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #00e676; text-align:center;'><span>🔗 REFERRAL TOTAL NET BOX ({mode_filter_string})</span><h4 style='color:#00e676;'>${ref_accum:.2f} USDT</h4></div>", unsafe_allow_html=True)
with cbx2: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #29b6f6; text-align:center;'><span>🌐 7-GEN DAILY ROI COMMISSION ({mode_filter_string})</span><h4 style='color:#29b6f6;'>${gen_accum:.2f} USDT</h4></div>", unsafe_allow_html=True)
if search_uid_input:
    t1, t2 = st.tabs(["Real Production Earnings Gate 🟢", "Demo Sandbox Earnings Gate 🔵"])
    with t1:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            if not pnl_df.empty and "User ID" in pnl_df.columns:
                child_real_df = pnl_df[(pnl_df["User ID"] == search_uid_input) & (pnl_df["Type"] == "REAL")]
                if not child_real_df.empty:
                    child_real_df["Net P&L ($)"] = pd.to_numeric(child_real_df["Net P&L ($)"])
                    st.markdown(f"💰 Real Daily Earnings: <b style='color:#00e676;'>${child_real_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True)
                    st.dataframe(child_real_df.iloc[::-1], use_container_width=True)
                else: st.info("No live production real funds data records synced yet.")
        else: st.info("Ledger registry is empty.")
    with t2:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            if not pnl_df.empty and "User ID" in pnl_df.columns:
                child_demo_df = pnl_df[(pnl_df["User ID"] == search_uid_input) & (pnl_df["Type"] == "DEMO")]
                if not child_demo_df.empty:
                    child_demo_df["Net P&L ($)"] = pd.to_numeric(child_demo_df["Net P&L ($)"])
                    st.markdown(f"💰 Demo Virtual Sandbox Earnings: <b style='color:#29b6f6;'>${child_demo_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True)
                    st.dataframe(child_demo_df.iloc[::-1], use_container_width=True)
                else: st.info("No sandbox simulation records synced yet.")
        else: st.info("Ledger registry is empty.")
st.markdown(pro_ui.section('Downline Members', 'sub-generation status grid'), unsafe_allow_html=True)
sub_tree_records = []
mapped_gens = calculate_sub_generations(search_uid_input, st._global_referral_tree)
for g_key, sub_uids in mapped_gens.items():
    for sub_uid in sub_uids:
        demo_pnl, real_pnl = 0.0, 0.0
        if st._global_user_pnl_history:
            for r in st._global_user_pnl_history:
                if r.get("User ID") == sub_uid:
                    val = float(r.get("Net P&L ($)", 0))
                    if r.get("Type") == "REAL": real_pnl += val
                    else: demo_pnl += val
        sub_tree_records.append({"Hierarchy Level": g_key, "User ID": sub_uid, "Username": st._uid_to_username.get(sub_uid, f"Node-{sub_uid[:4]}"), "Demo Lifetime Profit": f"${demo_pnl:.2f} USDT", "Real Lifetime Profit": f"${real_pnl:.2f} USDT"})
if sub_tree_records: st.dataframe(pd.DataFrame(sub_tree_records), use_container_width=True)
else: st.info("No active downline nodes found.")
with st.expander("🛠️ Super Admin Panel"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        _uc = st._central_user_creds or {}
        _keys = st._central_key_registry or {}
        _led = st._global_user_pnl_history or []
        _trade_rows = [r for r in _led if "COMMISSION" not in str(r.get("Action", ""))]
        def _sumpnl(rows, typ):
            _t = 0.0
            for r in rows:
                try:
                    if r.get("Type") == typ: _t += float(r.get("Net P&L ($)", 0))
                except Exception: pass
            return _t
        _real_net, _demo_net = _sumpnl(_trade_rows, "REAL"), _sumpnl(_trade_rows, "DEMO")
        _comm = sum(float(r.get("Net P&L ($)", 0) or 0) for r in _led if "COMMISSION" in str(r.get("Action", "")))
        _free = sum(1 for v in _keys.values() if v == "FREE_SLOT")
        st.markdown(pro_ui.kpis([
            ("Members", f"{len(_uc)}", f"{sum(1 for u in _uc.values() if u.get('license_activated_before'))} licensed", "#38bdf8", ""),
            ("License keys", f"{len(_keys)}", f"{_free} unused - {len(st._central_blacklist)} banned", "#a78bfa", ""),
            ("Closed trades", f"{len(_trade_rows)}", "all members", "#f5a623", ""),
            ("Real net P&L", f"{_real_net:+,.2f}$", "all members", "#22f2a0" if _real_net >= 0 else "#ff4d6d", "pos" if _real_net > 0 else ("neg" if _real_net < 0 else "flat")),
            ("Demo net P&L", f"{_demo_net:+,.2f}$", "all members", "#22f2a0" if _demo_net >= 0 else "#ff4d6d", "pos" if _demo_net > 0 else ("neg" if _demo_net < 0 else "flat")),
            ("Commissions", f"{_comm:,.2f}$", "referral + generation", "#243553", ""),
        ]), unsafe_allow_html=True)
        _t_ov, _t_ref, _t_fund, _t_net, _t_lic = st.tabs(["Overview", "Referral & MLM", "Funds", "Network & Ledger", "Licenses & Users"])
        with _t_ov:
            try:
                _by_c = {}
                for _u in _uc.values(): _by_c[_u.get("country", "?")] = _by_c.get(_u.get("country", "?"), 0) + 1
                _f1 = pro_ui.bar_chart(list(_by_c.keys()), list(_by_c.values()), 230)
                if _f1 is not None:
                    st.markdown("<div class='pz-h'><span>MEMBERS BY <b>COUNTRY</b></span></div>", unsafe_allow_html=True); st.plotly_chart(_f1, use_container_width=True)
                _per = {}
                for r in _trade_rows:
                    try: _per[str(r.get("User ID"))] = _per.get(str(r.get("User ID")), 0.0) + float(r.get("Net P&L ($)", 0))
                    except Exception: pass
                _top = sorted(_per.items(), key=lambda kv: kv[1], reverse=True)[:10]
                if _top:
                    _f2 = pro_ui.bar_chart([st._uid_to_username.get(k, k) for k, _ in _top], [v for _, v in _top], 230, "#22f2a0")
                    if _f2 is not None:
                        st.markdown("<div class='pz-h'><span>TOP 10 MEMBERS &middot; <b>NET P&L</b></span></div>", unsafe_allow_html=True); st.plotly_chart(_f2, use_container_width=True)
                _eq_all = [float(r.get("Net P&L ($)", 0)) for r in _trade_rows if r.get("Type") == ("REAL" if is_real_live else "DEMO")]
                _f3 = pro_ui.equity_chart(_eq_all) if len(_eq_all) >= 2 else None
                if _f3 is not None:
                    st.markdown(f"<div class='pz-h'><span>PLATFORM EQUITY &middot; <b>{'REAL' if is_real_live else 'DEMO'}</b></span></div>", unsafe_allow_html=True); st.plotly_chart(_f3, use_container_width=True)
            except Exception as _e:
                st.caption(f"Chart load hoyni: {_e}")
        with _t_ref:
            st.markdown("<h2>⚙️ Referral Marketing Master Controls Desk:</h2>", unsafe_allow_html=True)
            old_ref_sys = st._ref_system_active
            st._ref_system_active = st.toggle("Activate Global Referral Sign-Up Bonus Matrix", value=st._ref_system_active, key="adm_ref_sys_toggle")
            if old_ref_sys != st._ref_system_active: db_save("ref_sys_active", st._ref_system_active)
            admin_current_ref_payout = float(db_load("admin_fixed_ref_usd", 10.0))
            admin_new_ref_payout = st.number_input("🚨 Referral Bonus Fixed Amount Settings ($) Input:", min_value=0.0, value=admin_current_ref_payout, step=1.0, key="adm_fixed_ref_amt_box")
            if admin_new_ref_payout != admin_current_ref_payout: db_save("admin_fixed_ref_usd", admin_new_ref_payout); st.rerun()
            old_val = st._mlm_bonus_enabled
            st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled, key="adm_mlm_active_toggle")
            if old_val != st._mlm_bonus_enabled: db_save("mlm_enabled", st._mlm_bonus_enabled)
            c_cols = st.columns(2)
            for g in range(1, 8):
                with c_cols[(g-1)%2]:
                    st._mlm_gen_rates[str(g)] = st.number_input(f"Gen {g} Share (%):", min_value=0.0, max_value=100.0, value=st._mlm_gen_rates.get(str(g), st._mlm_gen_rates.get(g, 5.0)), key=f"adm_rates_generation_input_g_{g}")
                    st._mlm_id_thresholds[str(g)] = st.number_input(f"Gen {g} Cap:", min_value=1, value=st._mlm_id_thresholds.get(str(g), st._mlm_id_thresholds.get(g, 10)), key=f"adm_thresholds_generation_input_g_{g}")
            db_save("gen_rates", st._mlm_gen_rates); db_save("id_thresh", st._mlm_id_thresholds)
        with _t_fund:
            st.markdown("<h3>✍️ Manual Balance Override Control (Edit User Funds)</h3>", unsafe_allow_html=True)
            target_edit_uid = st.text_input("Enter Target Member UID to Edit:", key="adm_edit_target_uid_field").strip()
            edit_mode_sel = st.selectbox("Select Balance Type to Modify:", ["Demo Simulation Balance", "Real Mainnet Balance"])
            new_edit_value = st.number_input("Input Absolute New Balance Value Amount ($):", min_value=0.0, value=0.0, step=10.0)
            if st.button("🚨 Save Hard Fund Override Changes", key="adm_execute_edit_funds_btn"):
                if target_edit_uid != "":
                    if "Real" in edit_mode_sel: db_save(f"real_balance_{target_edit_uid}", float(new_edit_value))
                    else: db_save(f"balance_{target_edit_uid}", float(new_edit_value))
                    st.success("User configuration funds updated inside database successfully!"); st.rerun()
        with _t_net:
            st.markdown("<h3>🌿 Global User Registry Network Map:</h3>", unsafe_allow_html=True)
            full_mapped_tree = {}
            for parent_uid in list(st._global_referral_tree.keys()):
                deep_tree = calculate_sub_generations(parent_uid, st._global_referral_tree)
                summary_node = {}
                for gen_name, uid_list in deep_tree.items():
                    if uid_list: summary_node[f"{gen_name} (Total: {len(uid_list)} Active IDs)"] = [f"{st._uid_to_username.get(uid, 'Unknown')} -> {uid}" for uid in uid_list]
                if summary_node:
                    user_label = st._uid_to_username.get(parent_uid, parent_uid)
                    full_mapped_tree[f"👤 Sponsor Handle: {user_label} [{parent_uid}]"] = summary_node
            st.json(full_mapped_tree)
            st.markdown("<h3>📊 Global Live Trade Ledger (All Users Tracking):</h3>", unsafe_allow_html=True)
            if st._global_user_pnl_history:
                full_ledger_df = pd.DataFrame(st._global_user_pnl_history)
                unique_uids_list = list(full_ledger_df["User ID"].unique()) if "User ID" in full_ledger_df.columns else []
                selected_audit_uid = st.selectbox("🎯 Select Specific Member UID to Filter Details Tree Ledger:", ["ALL USERS"] + unique_uids_list)
                if selected_audit_uid == "ALL USERS": st.dataframe(full_ledger_df.iloc[::-1], use_container_width=True)
                else:
                    filtered_ledger_df = full_ledger_df[full_ledger_df["User ID"] == selected_audit_uid]
                    st.dataframe(filtered_ledger_df.iloc[::-1], use_container_width=True)
        with _t_lic:
            if st.button("Mint New Randomized License Token Key", key="adm_mint_token_trigger_btn"):
                random_token = "SCLP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
                st._central_key_registry[random_token] = "FREE_SLOT"
                st._license_csv_database.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "License Key": random_token, "Status": "Active (Unused)"})
                db_save("key_registry", st._central_key_registry); db_save("license_csv", st._license_csv_database); st.code(f"{random_token}"); st.rerun()
            override_uid = st.text_input("Target User ID (UID) to Hack/Change:", key="adm_override_uid_field").strip()
            override_new_pass = st.text_input("Set Custom New Password Phrase:", key="adm_override_pass_field").strip()
            if st.button("Execute Hard Password Override Ban", key="adm_override_pass_submit_btn"):
                found_account = None
                for uname, data in st._central_user_creds.items():
                    if data.get("uid") == override_uid: found_account = uname; break
                if found_account and override_new_pass != "":
                    st._central_user_creds[found_account]["password"] = override_new_pass; db_save("user_creds", st._central_user_creds); st.success(f"Success!"); st.rerun()
            target_block_key = st.text_input("Paste Target License Token to BAN permanently:", key="adm_ban_token_input_field")
            if st.button("Execute Permanent Revocation Ban", key="adm_ban_token_trigger_btn"):
                if target_block_key in st._central_key_registry:
                    st._central_blacklist.append(target_block_key); del st._central_key_registry[target_block_key]
                    db_save("blacklist", st._central_blacklist); db_save("key_registry", st._central_key_registry); st.warning(f"Token blocked permanent."); st.rerun()
            if st._license_csv_database: st.dataframe(pd.DataFrame(st._license_csv_database).iloc[::-1], use_container_width=True, height=120)
            all_creds_df = pd.DataFrame.from_dict(st._central_user_creds, orient='index')
            if not all_creds_df.empty:
                _show_secret = st.checkbox("Password / security answer column-o dekhao", value=False, key="adm_show_secret_cols")
                if not _show_secret:
                    all_creds_df = all_creds_df.drop(columns=[c for c in ("password", "school_answer") if c in all_creds_df.columns])
                st.dataframe(all_creds_df, use_container_width=True)
