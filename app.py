import streamlit as st
import pandas as pd
import time
import random
import string
import json
import os
import requests
import plotly.graph_objects as go
from datetime import datetime
from pybit.unified_trading import HTTP
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase Authentication Configuration Control Cloud Node
if not firebase_admin._apps:
    fb_json = os.environ.get("firebase_json", None)
    if fb_json:
        try:
            fb_dict = json.loads(fb_json) if isinstance(fb_json, str) else fb_json
            cred = credentials.Certificate(fb_dict)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Sync Error: {str(e)}")
            st.stop()
    else:
        if os.path.exists("firebase_key.json"):
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        else:
            st.error("Missing Config Database Keys!")
            st.stop()

db = firestore.client()

def db_load(key, default_val):
    try:
        ref = db.collection("scalper_system").document(key).get()
        if ref.exists:
            return ref.to_dict().get("data", default_val)
        return default_val
    except:
        return default_val

def db_save(key, val):
    try:
        db.collection("scalper_system").document(key).set({"data": val})
    except:
        pass

# Global States Persistence Memory Sync
if "init_sync" not in st.session_state:
    st._central_user_creds = db_load("user_creds", {})
    st._central_key_registry = db_load("key_registry", {})
    st._central_blacklist = db_load("blacklist", [])
    st._license_csv_database = db_load("license_csv", [])
    st._global_referral_tree = db_load("referral_tree", {})
    st._global_user_pnl_history = db_load("pnl_history", [])
    st._uid_to_username = db_load("uid_to_user", {})
    st._mlm_bonus_enabled = db_load("mlm_enabled", True)
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
    st._mlm_deposit_bonus_rate = db_load("dep_rate", 5.18)
    st._mlm_gen_rates = db_load("gen_rates", {})
    st._mlm_id_thresholds = db_load("id_thresh", {})

# Dynamic Scraper Engine fetching all Live Bybit Future Symbols
@st.cache_data(ttl=300)
def fetch_bybit_future_coins():
    try:
        url = "https://bybit.com"
        res = requests.get(url).json()
        instruments = res.get("result", {}).get("list", [])
        coin_dict = {}
        for inst in instruments:
            if inst["status"] == "Trading" and inst["quoteCoin"] == "USDT":
                sym = inst["symbol"]
                base = inst["baseCoin"]
                max_lev = int(float(inst.get("leverageFilter", {}).get("maxLeverage", 100)))
                display_name = f"🪙 {base} (Future)"
                coin_dict[display_name] = {
                    "symbol": sym, "max_leverage": max_lev,
                    "default_tp": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 500,
                    "default_sl": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 750,
                    "step": float(inst.get("priceFilter", {}).get("tickSize", "0.01"))
                }
        return coin_dict if coin_dict else {"🪙 BTC (Future)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}
    except:
        return {"🪙 BTC (Future)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}

BYBYT_DATABASE_CORE = fetch_bybit_future_coins()
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(page_title="Bybit AI Scalper Pro", page_icon="⚡", layout="centered")

# Responsive CSS UI Overflow Handler prevents screen breakout
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #06090e !important;
        background-image: radial-gradient(circle at 50% 20%, #111723 0%, #06090e 80%) !important;
        overflow-y: auto !important; overflow-x: hidden !important; box-sizing: border-box !important;
    }
    div[data-testid="stSidebar"] { background-color: #0c1017 !important; border-right: 1px solid #1e293b; }
    div.stButton > button:first-child { width: 100%; border-radius: 8px; font-weight: bold; font-size: 16px; height: 46px; }
    .stDataFrame, .stTable, div[data-testid="stDataFrame"] { max-width: 100% !important; overflow-x: auto !important; display: block !important; }
    div[data-testid="stMarkdownContainer"] p, span, label, h1, h2, h3, b, code { word-wrap: break-word !important; white-space: normal !important; word-break: break-word !important; }
    .custom-box-grid { background-color: #141a24; padding: 15px; border-radius: 12px; margin-bottom: 12px; border: 1px solid #1f2c3f; }
    </style>
    """,
    unsafe_allow_html=True
)

if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = st.query_params.get("session_user", None)

if st.session_state.logged_in_user is None:
    st.markdown("<div style='background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center;'><h1 style='margin: 0; color: #0b0e14; font-size: 26px; font-weight: bold;'>BYBIT AI PRO SCALPER</h1></div>", unsafe_allow_html=True)
    st.subheader("🔑 Secure Identity Management Panel")
    auth_mode = st.radio("Choose Layer:", ["Secure Login Profile", "Mint New Account ID", "Forget Password Profile"])
    
    if auth_mode == "Mint New Account ID":
        reg_username = st.text_input("Username:", key="reg_u").strip()
        reg_password = st.text_input("Password Phrase:", type="password", key="reg_p").strip()
        reg_email = st.text_input("Google Mail (Gmail ID):", key="reg_e").strip()
        reg_school = st.text_input("First School Name?", key="reg_sch").strip()
        reg_sponsor = st.text_input("Sponsor Referral Token ID:", key="reg_s").strip()
        if st.button("🚀 Register My Handle", key="reg_submit_btn"):
            st._central_user_creds = db_load("user_creds", {})
            existing_emails = [d.get("email") for d in st._central_user_creds.values()]
            if reg_username == "" or reg_password == "" or reg_email == "" or reg_school == "":
                st.error("Fields blank!")
            elif "@gmail.com" not in reg_email: st.error("Invalid Gmail!")
            elif reg_email in existing_emails: st.error("Email active!")
            elif reg_username in st._central_user_creds: st.error("Handle active!")
            else:
                new_uid = "UID-" + "".join(random.choices(string.digits, k=6))
                st._central_user_creds[reg_username] = {
                    "password": reg_password, "uid": new_uid, "email": reg_email,
                    "school_answer": reg_school.lower(), "sponsor": reg_sponsor if reg_sponsor != "" else "None"
                }
                st._uid_to_username[new_uid] = reg_username
                db_save("user_creds", st._central_user_creds)
                db_save("uid_to_user", st._uid_to_username)
                db_save(f"balance_{new_uid}", 5000.0)
                db_save(f"win_{new_uid}", 0)
                db_save(f"loss_{new_uid}", 0)
                if reg_sponsor != "":
                    st._global_referral_tree = db_load("referral_tree", {})
                    if reg_sponsor not in st._global_referral_tree: st._global_referral_tree[reg_sponsor] = []
                    st._global_referral_tree[reg_sponsor].append(new_uid)
                    db_save("referral_tree", st._global_referral_tree)
                st.success(f"Bound! UID: {new_uid}")
        st.stop()
        
    elif auth_mode == "Secure Login Profile":
        login_u = st.text_input("Identity Handle:", key="log_u").strip()
        login_p = st.text_input("Password Phrase:", type="password", key="log_p").strip()
        if st.button("🔓 Authenticate In", key="log_submit_btn"):
            st._central_user_creds = db_load("user_creds", {})
            if login_u in st._central_user_creds and st._central_user_creds[login_u]["password"] == login_p:
                st.session_state.logged_in_user = login_u
                st.query_params["session_user"] = login_u
                st.success("Authorized!")
                st.rerun()
            else: st.error("Mismatch credentials!")
        st.stop()
user_data = st._central_user_creds[st.session_state.logged_in_user]
allocated_user_id = user_data["uid"]
my_sponsor_id = user_data["sponsor"]
my_profile_email = user_data.get("email", "Not Set")

# Isolated User Performance Adapters Loading Sequence
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)
if 'win_count' not in st.session_state: st.session_state.win_count = db_load(f"win_{allocated_user_id}", 0)
if 'loss_count' not in st.session_state: st.session_state.loss_count = db_load(f"loss_{allocated_user_id}", 0)

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Panel</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#e2a826; font-size:13px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px;'>🆔 Referral ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Logout Account"):
        st.session_state.logged_in_user = None
        st.rerun()
    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = "Live" in bot_mode
    selected_display_name = st.selectbox("Select Asset Contract:", list(BYBYT_DATABASE_CORE.keys()))
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter", value=True)
    leverage = st.slider(f"Leverage (Max {coin_config['max_leverage']}x):", 1, coin_config['max_leverage'], min(20, coin_config['max_leverage']))
    trade_amount = st.number_input("Margin Requirement (\$):", min_value=1, value=20)
    price_jump_target = st.number_input("Take Profit Target (\$):", value=coin_config["default_tp"], format="%.6f")
    stop_loss_gap = st.number_input("Stop Loss Threshold (\$):", value=coin_config["default_sl"], format="%.6f")

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011

# Live Analysis Indicators Rules Engine
live_price, current_rsi, market_trend, macd_signal = 0.0, 50.0, "SCANNING ⏳", "STABLE INDICATORS"
try:
    public_session = HTTP(testnet=False)
    response = public_session.get_kline(category="linear", symbol=target_symbol, interval="1", limit=30)
    klines = response.get('result', {}).get('list', [])
    if klines:
        df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover']).iloc[::-1].reset_index(drop=True)
        for c in ['open', 'high', 'low', 'close']: df_kline[c] = pd.to_numeric(df_kline[c])
        live_price = df_kline['close'].iloc[-1]
        delta = df_kline['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        current_rsi = (100 - (100 / (1 + rs))).iloc[-1]
        if pd.isna(current_rsi): current_rsi = 50.0
        
        ema_s = df_kline['close'].rolling(window=7).mean().iloc[-1]
        ema_l = df_kline['close'].rolling(window=25).mean().iloc[-1]
        if ema_s > ema_l and current_rsi < 60: market_trend = "BULLISH BUY SIGNAL DETECTED 🚀"
        elif ema_s < ema_l and current_rsi > 40: market_trend = "BEARISH SELL SIGNAL DETECTED 📉"
except:
    live_price = 95000.0

# Render Technical Scanner Analytics Cards
st.markdown("<h3 style='color:#f5a623;'>📊 Real-time AI Market Scanner</h3>", unsafe_allow_html=True)
ci1, ci2 = st.columns(2)
with ci1: st.markdown(f"<div class='custom-box-grid'>📈 <b>Price Index:</b> ${live_price:,.2f}</div>", unsafe_allow_html=True)
with ci2: st.markdown(f"<div class='custom-box-grid'>📡 <b>Hifi RSI Feed:</b> {current_rsi:.2f}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='custom-box-grid' style='border-left: 5px solid #ffcc00;'>🎯 <b>Technical Strategy Analysis:</b> {market_trend}</div>", unsafe_allow_html=True)

# Personal User Wallet Tracking Layout Dashboard
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

st.markdown(
    f"""<div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between;">
    <span style="color:#ffffff;">🏆 WON: <b style="color:#00e676;">{st.session_state.win_count}</b></span>
    <span style="color:#ffffff;">❌ LOST: <b style="color:#ff1744;">{st.session_state.loss_count}</b></span>
    <span style="color:#ffffff;">🎯 WIN RATE: <b style="color:#29b6f6;">{win_rate:.1f}%</b></span></div>""", 
    unsafe_allow_html=True
)
st.markdown(f"<div class='custom-box-grid'>💰 <b>Isolated Wallet Funds:</b> <h2 style='margin:0; color:#fff;'>${st.session_state.demo_balance:,.2f} USDT</h2></div>", unsafe_allow_html=True)

# Scalper Controls Systems Execution
cx, cy = st.columns(2)
with cx:
    if st.session_state.bot_active:
        if st.button("🔴 STOP ACTIVE ENGINE BLOCK"):
            st.session_state.bot_active = False
            st.rerun()
    else:
        if st.button("🟢 INITIALIZE ENGINE SCANNER"):
            st.session_state.bot_active = True
            st.rerun()
with cy:
    if st.button("🚨 EMERGENCY LIQUIDATE Close Position", disabled=not st.session_state.in_position):
        net_pnl = -estimated_fee
        st.session_state.demo_balance += net_pnl
        db_save(f"balance_{allocated_user_id}", st.session_state.demo_balance)
        st.session_state.in_position = False
        st.rerun()

# --- 🌿 DATE SCOPE CONFIGURABLE MULTI-GENERATION COMMISSION BOX HUB ---
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#f5a623;'>🌿 Dynamic Commissions Accounting Center</h3>", unsafe_allow_html=True)

col_d1, col_d2 = st.columns(2)
with col_d1: start_date = st.date_input("Start Registry Date:", datetime.now())
with col_d2: end_date = st.date_input("End Registry Date:", datetime.now())

ref_income, gen_income = 0.0, 0.0
if st._global_user_pnl_history:
    for row in st._global_user_pnl_history:
        try:
            r_date = datetime.strptime(row.get("Date", ""), "%Y-%m-%d").date()
            if start_date <= r_date <= end_date:
                if row.get("User ID") == allocated_user_id and "COMMISSION" in row.get("Action", ""):
                    gen_income += float(row.get("Net P&L ($)", 0))
        except: pass

cb1, cb2 = st.columns(2)
with cb1: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #00e676; text-align:center;'><span>🔗 DIRECT REFERRAL EARNINGS</span><h3 style='color:#00e676;'>${ref_income:.2f} USDT</h3></div>", unsafe_allow_html=True)
with cb2: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #29b6f6; text-align:center;'><span>🌐 7-GEN NETWORK Commission</span><h3 style='color:#29b6f6;'>${gen_income:.2f} USDT</h3></div>", unsafe_allow_html=True)

# Admin Operations Hub Expansion Desk Node
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="adm_password")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Admin Controller Access Verified.")
        if st.button("Mint New Randomized License Token"):
            random_token = "SCLP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            st._central_key_registry[random_token] = "FREE_SLOT"
            db_save("key_registry", st._central_key_registry)
            st.code(random_token)
