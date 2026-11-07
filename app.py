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
from bybit_engine import BybitEngine
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
    st.set_page_config(page_title="Bybit AI Scalper", page_icon="⚡", layout="centered")
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"], html, body { background-color: #06090e !important; margin: 0 !important; padding: 0 !important; border: none !important; }
        .splash-container { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 90vh; background-color: #06090e; color: white; font-family: 'Courier New', monospace; border: none !important; box-shadow: none !important; }
        .loader-circle { border: 4px solid rgba(255, 255, 255, 0.05); border-radius: 50%; border-top: 4px solid #00e676; border-bottom: 4px solid #ffcc00; width: 100px; height: 100px; animation: spin 1.0s linear infinite; margin-bottom: 35px; box-shadow: 0 0 15px rgba(0, 230, 118, 0.2); }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .progress-bar-container { width: 65%; background-color: #141a24; border-radius: 10px; padding: 2px; border: 1px solid #1f2c3f; }
        .progress-bar-fill { height: 5px; background: linear-gradient(90deg, #ff9900, #00e676); width: 0%; border-radius: 5px; animation: fillProgress 1.3s ease-in-out forwards; }
        @keyframes fillProgress { to { width: 100%; } }
        .splash-text { font-size: 24px; font-weight: 800; letter-spacing: 4px; margin-bottom: 25px; text-align: center; color: #ffffff; text-shadow: 0 0 10px rgba(255,255,255,0.1); }
        </style>
        <div class="splash-container">
            <div class="loader-circle"></div>
            <div class="splash-text">BYBIT AI PRO SCALPER</div>
            <div class="progress-bar-container"><div class="progress-bar-fill"></div></div>
        </div>
        """,
        unsafe_allow_html=True
    )
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
        p = m.get("pricing") or {}
        if str(p.get("prompt")) in ("0", "0.0") and str(p.get("completion")) in ("0", "0.0"):
            out.append((m.get("id", ""), int(m.get("context_length") or 0)))
    out.sort(key=lambda x: -x[1])
    return [i for i, _ in out if i][:25]

@st.cache_data(ttl=8, show_spinner=False)
def fetch_wallet_cached(k, s, testnet):   # underscore chhara: nahole cache key e user ba key dhora hoy na
    return BybitEngine(k, s, testnet=testnet).wallet()
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
if st.session_state.logged_in_user is None:
    st.markdown("<div style='background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center;'><h1 style='margin: 0; color: #0b0e14; font-size: 26px; font-weight: bold;'>BYBIT AI PRO SCALPER</h1></div>", unsafe_allow_html=True)
    st.subheader("🔑 Account Identity Gateway Control Panel")
    auth_mode = st.radio("Choose Layer:", ["Secure Login Profile", "Mint New Account ID", "Forget Password Profile"])
    
    if auth_mode == "Mint New Account ID":
        reg_username = st.text_input("Username Handle:", key="reg_u").strip()
        reg_password = st.text_input("Password Phrase:", type="password", key="reg_p").strip()
        reg_email = st.text_input("Google Mail (Gmail ID):", key="reg_e").strip()
        global_country_list = ["Bangladesh", "United States", "United Kingdom", "United Arab Emirates", "Saudi Arabia", "Malaysia", "India", "Pakistan", "Kuwait", "Qatar", "Oman", "Singapore", "Canada", "Australia", "Germany"]
        reg_country = st.selectbox("Select Profile Country (Mandatory):", global_country_list, index=0)
        global_phone_flags = ["🇧🇩 +880 (Bangladesh)", "🇺🇸 +1 (United States)", "🇬🇧 +44 (United Kingdom)", "🇦🇪 +971 (UAE)", "🇸🇦 +966 (Saudi Arabia)", "🇲🇾 +60 (Malaysia)", "🇮🇳 +91 (India)", "🇵🇰 +92 (Pakistan)"]
        reg_flag_code = st.selectbox("Select Phone Flag Country Code:", global_phone_flags, index=0)
        reg_phone_raw = st.text_input("Mobile Number (Without Country Code):", key="reg_ph_num_raw").strip()
        reg_school = st.text_input("First School Name? (Security Answer Check):", key="reg_sch").strip()
        reg_sponsor = st.text_input("Sponsor Referral Token ID (Username or UID):", key="reg_s").strip()
        if st.button("🚀 Register My Handle", key="reg_submit_btn"):
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
    elif auth_mode == "Forget Password Profile":
        st.markdown("<h3>🔒 Recover Password Profile System Node</h3>", unsafe_allow_html=True)
        f_user = st.text_input("Enter Username Handle to Recover:", key="forget_u_field").strip()
        f_school = st.text_input("Verification: First School Name?", key="forget_sch_field").strip()
        if st.button("⚡ Verify and Reveal Password", key="submit_forget_proc_btn"):
            st._central_user_creds = db_load("user_creds", {})
            if f_user in st._central_user_creds and st._central_user_creds[f_user].get("school_answer", "") == f_school.lower(): st.success(f"Identity Verified! Your Password is: **{st._central_user_creds[f_user]['password']}**")
            else: st.error("Verification parameters failed or mismatch!")
        st.stop()
        
    elif auth_mode == "Secure Login Profile":
        login_u = st.text_input("Identity Handle Name:", key="log_u").strip()
        login_p = st.text_input("Password Phrase Entry:", type="password", key="log_p").strip()
        if st.button("🔓 Authenticate In Dashboard Core", key="log_submit_btn"):
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
        
    bot_mode = st.radio("Trading Account Mode Settings:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = "Live" in bot_mode
    mode_suffix = "real" if is_real_live else "demo"
    dashboard_mode_title = "Real Production Dashboard Mode 🟢" if is_real_live else "Demo Sandbox Dashboard Mode 🔵"

    # 🔒 মোড ভিত্তিক সম্পূর্ণ আলাদা আইসোলেটেড লকিং স্টেট
    in_position_state = db_load(f"in_position_{mode_suffix}_{allocated_user_id}", False)
    locked_trade_coin = db_load(f"trade_coin_{mode_suffix}_{allocated_user_id}", "NONE")
    
    coin_list = list(BYBYT_DATABASE_CORE.keys())
    if is_real_live and st.session_state.get("bybit_testnet_toggle", True):
        try:   # testnet e jei coin live na, shegulo dropdown e dekhabo na (nahole "contract is not live" error)
            _live = set(fetch_testnet_live_symbols())
            _f = [k for k in coin_list if BYBYT_DATABASE_CORE[k]["symbol"] in _live]
            if _f: coin_list = _f
        except Exception:
            pass
    default_coin_idx = 0
    
    last_saved_db_coin = db_load(f"last_selected_coin_{mode_suffix}_{allocated_user_id}", "BTCUSDT")
    if in_position_state and locked_trade_coin != "NONE":
        last_saved_db_coin = locked_trade_coin

    for idx, k in enumerate(coin_list):
        v = BYBYT_DATABASE_CORE[k]
        if v["symbol"] == last_saved_db_coin:
            default_coin_idx = idx
            break

    if in_position_state:
        st.markdown(f"<div class='custom-box-grid' style='padding:10px; border-left:4px solid #38bdf8;'><b>🎯 Active Asset:</b> {last_saved_db_coin}</div>", unsafe_allow_html=True)
        coin_config = [v for v in BYBYT_DATABASE_CORE.values() if v["symbol"] == last_saved_db_coin][0]
        target_symbol = last_saved_db_coin
    else:
        selected_display_name = st.selectbox("Select Asset Contract Symbol Dropdown:", coin_list, index=default_coin_idx)
        coin_config = BYBYT_DATABASE_CORE[selected_display_name]
        target_symbol = coin_config["symbol"]
        db_save(f"trade_coin_{mode_suffix}_{allocated_user_id}", target_symbol)
        db_save(f"last_selected_coin_{mode_suffix}_{allocated_user_id}", target_symbol)

    ai_decision = st.toggle("AI Smart Crossover Filter Matrix", value=True)
    
    st.markdown("<b style='color:#38bdf8;'>🤖 OpenRouter AI Router Configuration:</b>", unsafe_allow_html=True)
    or_api_key = st.text_input("OpenRouter API Key:", type="password", value=db_load(f"or_key_{allocated_user_id}", ""), key="openrouter_api_key_field")
    or_model_id = st.text_input("Model ID:", value=db_load(f"or_model_{allocated_user_id}", "google/gemini-2.5-flash:free"), key="openrouter_model_id_field")
    if st.button("Save AI Router Node Config", key="save_or_config_btn"):
        db_save(f"or_key_{allocated_user_id}", or_api_key); db_save(f"or_model_{allocated_user_id}", or_model_id); st.toast("Config Saved!", icon="💾")
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

    api_key, secret_key = "", ""
    license_ok = False
    use_testnet = True
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><div style='background-color:#ff1744; padding:6px; border-radius:5px; text-align:center; margin-bottom:6px;'><b style='color:#ffffff; font-size:11px;'>🚨 LICENSE GATE ACTIVE</b></div>", unsafe_allow_html=True)
        input_license = st.text_input("License Password:", type="password", key="lic_field_sidebar", label_visibility="collapsed").strip()
        if input_license in st._central_key_registry:
            if not user_data.get("license_activated_before", False) and my_sponsor_id != "None" and st._ref_system_active:
                st._central_user_creds[st.session_state.logged_in_user]["license_activated_before"] = True; db_save("user_creds", st._central_user_creds)
                admin_fixed_bonus = float(db_load("admin_fixed_ref_usd", 10.0))
                st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": my_sponsor_id, "Coin": "REAL_LICENSE_ACTIVATION", "Action": "REF_COMMISSION_DIRECT", "Net P&L ($)": f"{admin_fixed_bonus:.2f}", "Type": "REAL"}); db_save("pnl_history", st._global_user_pnl_history)
            license_ok = True
            use_testnet = st.checkbox("🧪 Bybit TESTNET (age ekhane test koro)", value=True, key="bybit_testnet_toggle")
            api_key = st.text_input("Bybit API Key Node Token:", type="password", key="api_field_sidebar")
            secret_key = st.text_input("Bybit Secret Key Node Token:", type="password", key="sec_field_sidebar")
# 🔥 লোগো ব্যানার পেজের একদম উপরে প্লেস করা হলো
st.markdown("<div style='background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center;'><h1 style='margin: 0; color: #0b0e14; font-size: 26px; font-weight: bold;'>BYBIT AI PRO SCALPER</h1></div>", unsafe_allow_html=True)

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011
live_price, current_rsi, ai_market_thesis, fig_candlestick = 0.0, 50.0, "SYNCING DATA FEED NODES... 📡", None
public_session = HTTP(testnet=(is_real_live and use_testnet))
real_engine, real_wallet, real_engine_error = None, None, ""
if is_real_live and license_ok and api_key and secret_key:
    try:
        real_wallet = fetch_wallet_cached(api_key, secret_key, use_testnet)
        real_engine = BybitEngine(api_key, secret_key, testnet=use_testnet)
        st.session_state.real_balance = real_wallet["equity"]
    except Exception as e:
        real_engine, real_wallet, real_engine_error = None, None, str(e)
df_kline = pd.DataFrame()

try:
    ticker_res = public_session.get_tickers(category="linear", symbol=target_symbol)
    ticker_list = ticker_res.get('result', {}).get('list', [])
    if ticker_list: live_price = float(ticker_list[0].get('lastPrice', 0))
except: pass
try:
    response = public_session.get_kline(category="linear", symbol=target_symbol, interval="1", limit=30)
    klines = response.get('result', {}).get('list', [])
    if klines:
        df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover']).iloc[::-1].reset_index(drop=True)
        for c in ['open', 'high', 'low', 'close', 'volume']: df_kline[c] = pd.to_numeric(df_kline[c])
        if live_price == 0.0: live_price = df_kline['close'].iloc[-1]
        delta = df_kline['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        current_rsi = (100 - (100 / (1 + (gain / (loss + 1e-10))))).iloc[-1]
        fig_candlestick = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'])])
        fig_candlestick.add_trace(go.Scatter(x=df_kline.index, y=df_kline['close'].rolling(window=7).mean(), name="AI Geometric Tracking Vector", line=dict(color='#00e676', width=2, dash='dot')))
        fig_candlestick.update_layout(template="plotly_dark", margin=dict(l=6, r=6, t=6, b=6), height=250, xaxis_rangeslider_visible=False, paper_bgcolor='#06090e', plot_bgcolor='#06090e')
except: pass
if live_price == 0.0 and not df_kline.empty: live_price = float(df_kline['close'].iloc[-1])
# ==========================================
# 🧱 BOX 17: REAL-TIME CHART RENDERING INTERFACE
# ==========================================
chart_display_box = st.container()
with chart_display_box:
    if fig_candlestick: 
        st.plotly_chart(fig_candlestick, use_container_width=True)
st.markdown(f"<div class='custom-box-grid' style='background-color:#050a12; border:1px solid #00e676; padding: 22px;'><div class='matrix-neon-text' style='font-size:14px;'>🧬 <b>DEEPSEEK REAL-TIME SWARM INTERFACE LAYER:</b><br>🔮 DEEPEST OPENROUTER ROUTER SCALPER LABELS ACTIVATED ({target_symbol})</div></div>", unsafe_allow_html=True)
local_win = st.session_state.get('win_count', 0)
local_loss = st.session_state.get('loss_count', 0)
total_trades = local_win + local_loss
win_rate = (local_win / total_trades * 100) if total_trades > 0 else 0.0

st.markdown(f"""<div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between;">
    <span style="color:#ffffff; font-weight:bold;">🏆 WON: <b style="color:#00e676;">{local_win}</b></span>
    <span style="color:#ffffff; font-weight:bold;">❌ LOST: <b style="color:#ff1744;">{local_loss}</b></span>
    <span style="color:#ffffff; font-weight:bold;">🎯 WIN RATE: <b style="color:#29b6f6;">{win_rate:.1f}%</b></span></div>""", unsafe_allow_html=True)

if not is_real_live:
    st.markdown("<b>⚙️ Sandbox Fund Manager Module Panel:</b>", unsafe_allow_html=True)
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
FEE_RATE_ROUNDTRIP = 0.0011   # Bybit taker 0.055% x 2

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
    since_ms = int(db_load(f"real_open_ms_{allocated_user_id}", 0))
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
        db_save(f"real_open_ms_{uid}", int(time.time() * 1000))
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
    if real_engine_error: st.error(f"Bybit connect error: {real_engine_error}")
    elif real_engine is None: st.info("🔒 Real mode: sidebar e License Password dao, tarpor Bybit API Key + Secret dao. Tahole Bybit er asol balance ekhane ashbe.")
    else:
        st.caption(f"🔗 Bybit {'TESTNET 🧪' if use_testnet else 'MAINNET 🔴'} connected | Equity: ${real_wallet['equity']:,.2f} | Available: ${real_wallet['available']:,.2f} USDT")
        if real_wallet["equity"] == 0 and not real_wallet.get("raw", {}).get("coins_returned"):
            _uid = (real_wallet.get("raw", {}).get("API_KEY_INFO") or {}).get("userID", "?")
            st.warning(f"⚠️ Ei API key er Bybit account (UID: {_uid}) e kono coin nei. Jei {'testnet' if use_testnet else 'mainnet'} account e USDT ache, **oi account e login kore** notun API key banao.")
        with st.expander("🔍 Bybit wallet raw data (debug)"):
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
mode_suffix = "real" if is_real_live else "demo"
cloud_bot_trigger = db_load(f"bot_active_{mode_suffix}_{allocated_user_id}", False) if (allocated_user_id and allocated_user_id != "NONE") else st.session_state.get(f"bot_active_{mode_suffix}", False)

st.session_state.in_position = db_load(f"in_position_{mode_suffix}_{allocated_user_id}", False)
st.session_state.buy_price = db_load(f"buy_price_{mode_suffix}_{allocated_user_id}", 0.0)
st.session_state.current_side = db_load(f"current_side_{mode_suffix}_{allocated_user_id}", "NONE")
if cloud_bot_trigger and allocated_user_id != "NONE":
    or_api_key = db_load(f"or_key_{allocated_user_id}", "")
    or_model_id = db_load(f"or_model_{allocated_user_id}", "google/gemini-2.5-flash:free")
    
    if not st.session_state.in_position and ai_decision and or_api_key and (time.time() - st.session_state.get("last_ai_ts", 0) > AI_COOLDOWN_SEC):
        st.session_state.last_ai_ts = time.time()
        try:
            news_context = "Steady global macro trend line pattern."
            try:
                news_res = requests.get(f"https://cryptopanic.com/api/v1/posts/?auth_token={os.environ.get('CRYPTOPANIC_KEY', '')}&public=true", timeout=3) if os.environ.get("CRYPTOPANIC_KEY") else None
                if news_res is not None and news_res.status_code == 200:
                    news_data = news_res.json()
                    news_titles = [post.get('title', '') for post in news_data.get('results', [])[:4]]
                    if news_titles: news_context = " | ".join(news_titles)
            except: pass
            
            if not df_kline.empty and len(df_kline) >= 5:
                recent_candles = df_kline.tail(5).to_dict(orient="records")
                ma_series = df_kline['close'].rolling(window=7).mean()
                last_ma = float(ma_series.iloc[-1]) if not ma_series.empty else live_price
                
                is_turbo = not st.session_state.first_trade_done
                if is_turbo:
                    mode_instruction = "CRITICAL: You must operate in TURBO SCALPING MODE. Find immediate next micro-trend breakout/breakdown and issue LONG or SHORT immediately. Avoid HOLD."
                else:
                    mode_instruction = "CRITICAL: You must operate in ULTRA-SECURE INSTITUTIONAL MODE. Only issue LONG or SHORT if MA-7 breakout and RSI are 100% perfect. Otherwise output HOLD."
                
                market_context_prompt = (
                    f"Asset: {target_symbol} | Live Price: {live_price} | RSI: {current_rsi:.2f} | MA-7: {last_ma:.6f}\n"
                    f"News Summary: {news_context}\n"
                    f"Matrix -> Leverage: {leverage}x, TP: {price_jump_target}, SL: {stop_loss_gap}\n"
                    f"Candlesticks: {json.dumps(recent_candles)}\n\n"
                    f"{mode_instruction}\n\n"
                    f"RESPOND SYSTEM RULES: Output EXACTLY ONE UPPERCASE WORD: 'LONG' or 'SHORT' or 'HOLD'. No extra words."
                )
                headers = {"Authorization": f"Bearer {or_api_key}", "Content-Type": "application/json", "HTTP-Referer": "https://streamlit.io", "X-Title": "Bybit AI Engine"}
                payload = {"model": or_model_id, "messages": [{"role": "user", "content": market_context_prompt}]}
                
                log_prefix = "🚀 [TURBO AI]" if is_turbo else "🔒 [SECURE AI]"
                st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] {log_prefix} Analyzing Live Feeds...")
                _models = [m.strip() for m in str(or_model_id).replace("\n", ",").split(",") if m.strip()][:3] or [str(or_model_id)]
                or_response, _last_err = None, "no response"
                for _m in _models:
                    payload["model"] = _m
                    try:
                        _r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=12)
                    except Exception as _e:
                        _last_err = f"{_m} -> {_e}"
                        continue
                    if _r.status_code == 200:
                        or_response = _r
                        break
                    _last_err = f"{_m} -> HTTP {_r.status_code}: {_r.text[:140]}"
                    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] AI model failed: {_last_err}")
                    if _r.status_code in (401, 402, 403):
                        break
                if or_response is None and ("HTTP 400" in _last_err or "HTTP 404" in _last_err):
                    try:   # tomar Model ID invalid: OpenRouter er live free list theke ekta pick kori
                        for _m in [x for x in fetch_free_models() if x not in _models][:3]:
                            payload["model"] = _m
                            _r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=12)
                            if _r.status_code == 200:
                                or_response = _r
                                st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] ⚠️ Tomar Model ID invalid. Auto free model use holo: {_m} (sidebar e valo ekta ID boshiye Save koro)")
                                break
                            _last_err = f"{_m} -> HTTP {_r.status_code}: {_r.text[:100]}"
                    except Exception as _e:
                        _last_err = f"auto-pick failed: {_e}"
                if or_response is not None:
                    try:
                        ai_raw_word = ""
                        try:
                            res_json = or_response.json()
                            ai_raw_word = res_json['choices'][0]['message'].get('content', '').strip().upper()
                        except:
                            ai_raw_word = ""   # parse fail hole HOLD (error text e "too long" moto shobdo LONG hishebe dhora hobe na)
                        
                        resolved_signal = "HOLD"
                        if "LONG" in ai_raw_word and "SHORT" not in ai_raw_word: resolved_signal = "LONG"
                        elif "SHORT" in ai_raw_word and "LONG" not in ai_raw_word: resolved_signal = "SHORT"
                        
                        if resolved_signal == "HOLD" and not st.session_state.first_trade_done and not is_real_live:
                            resolved_signal = "LONG" if current_rsi < 50 else "SHORT"
                        
                        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Active Signal: '{resolved_signal}'")
                        
                        if resolved_signal in ["LONG", "SHORT"]:
                            ok, msg = open_trade(resolved_signal)
                            st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] {'Order opened' if ok else 'Order blocked'}: {msg}")
                            if ok:
                                st.toast(f"🟢 AI Order Triggered ({resolved_signal})", icon="🚀")
                                _rerun_after = True
                    except: pass
                else:
                    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] AI unavailable ({_last_err[:150]})")
                    if is_real_live:
                        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Real mode: AI uttor dey nai, tai kono trade kora holo na (HOLD).")
                    else:
                        local_decision = "HOLD"
                        if current_rsi < 45: local_decision = "LONG"
                        elif current_rsi > 55: local_decision = "SHORT"
                        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Demo RSI backup signal: '{local_decision}' for {target_symbol}")
                        if local_decision in ["LONG", "SHORT"]:
                            ok, msg = open_trade(local_decision)
                            st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] {'Order opened' if ok else 'Order blocked'}: {msg}")
                            if ok:
                                st.toast(f"⚡ Technical Latch Executed: {local_decision}", icon="⚙️")
                                _rerun_after = True
        except Exception as e:
            st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Loop Error Node: {str(e)}")
if _rerun_after:
    st.rerun()
# --- 🪐 LIVE TERMINAL BOX ---
st.markdown("<b>🖥️ Real-Time AI Swarm Scalper Loop Sequence Log Panel:</b>", unsafe_allow_html=True)
log_text = "\n".join(st.session_state.engine_logs[-8:])
st.text_area(label="Live Terminal", value=log_text, height=135, label_visibility="collapsed")

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
st.markdown(f"<h3 style='color:#f5a623;'>🌿 Network Marketing Matrix Desk ({dashboard_mode_title})</h3>", unsafe_allow_html=True)
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
st.markdown("<br><b style='color:#f5a623;'>📊 Sub-Downline Network Members Status Grid Management Node:</b>", unsafe_allow_html=True)
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
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        st.markdown("<h2>⚙️ Referral Marketing Master Controls Desk:</h2>", unsafe_allow_html=True)
        old_ref_sys = st._ref_system_active
        st._ref_system_active = st.toggle("Activate Global Referral Sign-Up Bonus Matrix", value=st._ref_system_active, key="adm_ref_sys_toggle")
        if old_ref_sys != st._ref_system_active: db_save("ref_sys_active", st._ref_system_active)
        admin_current_ref_payout = float(db_load("admin_fixed_ref_usd", 10.0))
        admin_new_ref_payout = st.number_input("🚨 Referral Bonus Fixed Amount Settings ($) Input:", min_value=0.0, value=admin_current_ref_payout, step=1.0, key="adm_fixed_ref_amt_box")
        if admin_new_ref_payout != admin_current_ref_payout: db_save("admin_fixed_ref_usd", admin_new_ref_payout); st.rerun()
        st.markdown("<h3>✍️ Manual Balance Override Control (Edit User Funds)</h3>", unsafe_allow_html=True)
        target_edit_uid = st.text_input("Enter Target Member UID to Edit:", key="adm_edit_target_uid_field").strip()
        edit_mode_sel = st.selectbox("Select Balance Type to Modify:", ["Demo Simulation Balance", "Real Mainnet Balance"])
        new_edit_value = st.number_input("Input Absolute New Balance Value Amount ($):", min_value=0.0, value=0.0, step=10.0)
        if st.button("🚨 Save Hard Fund Override Changes", key="adm_execute_edit_funds_btn"):
            if target_edit_uid != "":
                if "Real" in edit_mode_sel: db_save(f"real_balance_{target_edit_uid}", float(new_edit_value))
                else: db_save(f"balance_{target_edit_uid}", float(new_edit_value))
                st.success("User configuration funds updated inside database successfully!"); st.rerun()
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
        old_val = st._mlm_bonus_enabled
        st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled, key="adm_mlm_active_toggle")
        if old_val != st._mlm_bonus_enabled: db_save("mlm_enabled", st._mlm_bonus_enabled)
        c_cols = st.columns(2)
        for g in range(1, 8):
            with c_cols[(g-1)%2]:
                st._mlm_gen_rates[str(g)] = st.number_input(f"Gen {g} Share (%):", min_value=0.0, max_value=100.0, value=st._mlm_gen_rates.get(str(g), st._mlm_gen_rates.get(g, 5.0)), key=f"adm_rates_generation_input_g_{g}")
                st._mlm_id_thresholds[str(g)] = st.number_input(f"Gen {g} Cap:", min_value=1, value=st._mlm_id_thresholds.get(str(g), st._mlm_id_thresholds.get(g, 10)), key=f"adm_thresholds_generation_input_g_{g}")
        db_save("gen_rates", st._mlm_gen_rates); db_save("id_thresh", st._mlm_id_thresholds)
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
        if not all_creds_df.empty: st.dataframe(all_creds_df, use_container_width=True)
