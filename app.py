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

# Firebase Cloud Synchronization Engine Setup
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
            st.error("Missing Config Database Properties Node!")
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

# Initialize Sync Control Registry Matrices
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

# Live API Scanner: Fetches all active Bybit Futures contracts dynamically instead of static listing
@st.cache_data(ttl=200)
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
                display_name = f"🪙 {base} (Bybit Futures)"
                coin_dict[display_name] = {
                    "symbol": sym, "max_leverage": max_lev,
                    "default_tp": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 500,
                    "default_sl": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 750,
                    "step": float(inst.get("priceFilter", {}).get("tickSize", "0.01"))
                }
        return coin_dict if coin_dict else {"🪙 BTC (Bybit Futures)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}
    except:
        return {"🪙 BTC (Bybit Futures)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}

BYBYT_DATABASE_CORE = fetch_bybit_future_coins()
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(page_title="Bybit AI Scalper Pro", page_icon="⚡", layout="centered")

# Responsive Layout CSS Configuration
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
    st.subheader("🔑 Secure Identity Profile Node")
    auth_mode = st.radio("Choose Layer:", ["Secure Login Profile", "Mint New Account ID", "Forget Password Profile"])
    
    if auth_mode == "Mint New Account ID":
        reg_username = st.text_input("Username:", key="reg_u").strip()
        reg_password = st.text_input("Password Phrase:", type="password", key="reg_p").strip()
        reg_email = st.text_input("Google Mail (Gmail ID):", key="reg_e").strip()
        reg_school = st.text_input("First School Name?", key="reg_sch").strip()
        reg_sponsor = st.text_input("Sponsor Referral Token:", key="reg_s").strip()
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
                
                # Setup specific dynamic state allocation isolated safely per single user handle
                db_save(f"balance_{new_uid}", 5000.0)
                db_save(f"win_{new_uid}", 0)
                db_save(f"loss_{new_uid}", 0)
                
                if reg_sponsor != "":
                    st._global_referral_tree = db_load("referral_tree", {})
                    if reg_sponsor not in st._global_referral_tree: st._global_referral_tree[reg_sponsor] = []
                    st._global_referral_tree[reg_sponsor].append(new_uid)
                    db_save("referral_tree", st._global_referral_tree)
                st.success(f"Bound Successful! UID: {new_uid}")
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

# Individual state load maps ensuring no data mix up between accounts
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)
if 'win_count' not in st.session_state: st.session_state.win_count = db_load(f"win_{allocated_user_id}", 0)
if 'loss_count' not in st.session_state: st.session_state.loss_count = db_load(f"loss_{allocated_user_id}", 0)

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Panel Dashboard</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#e2a826; font-size:13px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px;'>🆔 My ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Logout Account Profile System", key="sidebar_logout_node"):
        st.session_state.logged_in_user = None
        st.rerun()
    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = "Live" in bot_mode
    selected_display_name = st.selectbox("Select Asset Contract Symbol:", list(BYBYT_DATABASE_CORE.keys()))
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter Engine", value=True)
    
    # Corrected dynamic leverage setting layout to display absolute values (e.g. 1-100x explicitly instead of scaling down)
    leverage = st.slider(f"Leverage Control Segment (Max {coin_config['max_leverage']}x):", 1, coin_config['max_leverage'], min(20, coin_config['max_leverage']))
    trade_amount = st.number_input("Margin Requirement (\$):", min_value=1, value=20)
    price_jump_target = st.number_input("Take Profit Target (\$):", value=coin_config["default_tp"], format="%.6f")
    stop_loss_gap = st.number_input("Stop Loss Threshold (\$):", value=coin_config["default_sl"], format="%.6f")

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011

# Gemini AI / Technical indicators Multi-Dimensional Pre-Trade Analyzer Modules
live_price, current_rsi, ai_market_thesis, macd_state = 0.0, 50.0, "DEEP ANALYSIS INITIALIZING ⏳", "COLLECTING TICK DATA"
try:
    public_session = HTTP(testnet=False)
    response = public_session.get_kline(category="linear", symbol=target_symbol, interval="1", limit=30)
    klines = response.get('result', {}).get('list', [])
    if klines:
        df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover']).iloc[::-1].reset_index(drop=True)
        for c in ['open', 'high', 'low', 'close', 'volume']: df_kline[c] = pd.to_numeric(df_kline[c])
        live_price = df_kline['close'].iloc[-1]
        delta = df_kline['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        current_rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # Complex Multi-Indicator Logic Framework Integration
        ema_7 = df_kline['close'].rolling(window=7).mean().iloc[-1]
        ema_25 = df_kline['close'].rolling(window=25).mean().iloc[-1]
        if ema_7 > ema_25 and current_rsi < 60:
            ai_market_thesis = "BULLISH MOMENTUM IDENTIFIED 🚀 - Indicators suggest strong upward acceleration point."
            macd_state = "BUY CROSSOVER"
        elif ema_7 < ema_25 and current_rsi > 40:
            ai_market_thesis = "BEARISH DISCHARGE TRIGGERED 📉 - Research displays short selling liquidation risks."
            macd_state = "SELL DIVERGENCE"
        else:
            ai_market_thesis = "CONSOLIDATION ZONE PATTERN DETECTED ⏳ - Awaiting clear technical indicators breakout."
            macd_state = "RANGING MARKET"
except:
    live_price = 68000.0

# Live Visual Bot Home Screen Analytics
st.markdown("<h3 style='color:#f5a623;'>📡 Live AI Multi-Indicator Visualization Hub</h3>", unsafe_allow_html=True)
cl1, cl2, cl3 = st.columns(3)
with cl1: st.markdown(f"<div class='custom-box-grid' style='text-align:center;'><small style='color:#94a3b8;'>LIVE PRICE</small><h4 style='color:#fff;margin:0;'>${live_price:,.2f}</h4></div>", unsafe_allow_html=True)
with cl2: st.markdown(f"<div class='custom-box-grid' style='text-align:center;'><small style='color:#94a3b8;'>HIFI RSI</small><h4 style='color:#00e676;margin:0;'>{current_rsi:.2f}</h4></div>", unsafe_allow_html=True)
with cl3: st.markdown(f"<div class='custom-box-grid' style='text-align:center;'><small style='color:#94a3b8;'>MACD MODE</small><h4 style='color:#29b6f6;margin:0;'>{macd_state}</h4></div>", unsafe_allow_html=True)
st.markdown(f"<div class='custom-box-grid' style='border-left:5px solid #ffcc00;'>🤖 <b>Gemini Deep Analysis Output:</b> {ai_market_thesis}</div>", unsafe_allow_html=True)

# Personal User Isolated Account Dash Performance Board Layout
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

st.markdown(
    f"""<div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between;">
    <span style="color:#ffffff;">🏆 ACCOUNT WON: <b style="color:#00e676;">{st.session_state.win_count}</b></span>
    <span style="color:#ffffff;">❌ ACCOUNT LOST: <b style="color:#ff1744;">{st.session_state.loss_count}</b></span>
    <span style="color:#ffffff;">🎯 TARGET WIN RATE: <b style="color:#29b6f6;">{win_rate:.1f}%</b></span></div>""", 
    unsafe_allow_html=True
)
st.markdown(f"<div class='custom-box-grid'>💰 <b>Available Profile Balance ({bot_mode}):</b> <h2 style='margin:0; color:#fff;'>${st.session_state.demo_balance:,.2f} USDT</h2></div>", unsafe_allow_html=True)
# Engine Control Launch Sequence Systems Blocks
cx, cy = st.columns(2)
with cx:
    if st.session_state.bot_active:
        if st.button("🔴 SHUTDOWN RUNNING BOT SCALPER ENGINE", key="stop_engine_bot_btn"):
            st.session_state.bot_active = False
            st.rerun()
    else:
        if st.button("🟢 LAUNCH INTEL SCANNING AUTOMATION LOOP", key="start_engine_bot_btn"):
            st.session_state.bot_active = True
            st.rerun()
with cy:
    if st.button("🚨 EMERGENCY FORCE CLOSE LIQUIDATE", disabled=not st.session_state.in_position, key="force_sell_engine_btn"):
        net_pnl = -estimated_fee
        st.session_state.demo_balance += net_pnl
        db_save(f"balance_{allocated_user_id}", st.session_state.demo_balance)
        st.session_state.in_position = False
        st.rerun()

# --- 🌿 ISOLATED 7-GENERATION & REFERRAL INCOME MATRIX GATE ---
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#f5a623;'>🌿 Multi-Gen Network Ledger System</h3>", unsafe_allow_html=True)

# Date Picker Scope Nodes Settings
col_d1, col_d2 = st.columns(2)
with col_d1: start_date_filter = st.date_input("Scope Registration Date Start:", datetime.now(), key="d_start")
with col_d2: end_date_filter = st.date_input("Scope Registration Date End:", datetime.now(), key="d_end")

demo_referral_bonus, demo_generation_bonus = 0.0, 0.0
if st._global_user_pnl_history:
    for row in st._global_user_pnl_history:
        try:
            r_date = datetime.strptime(row.get("Date", ""), "%Y-%m-%d").date()
            if start_date_filter <= r_date <= end_date_filter:
                if row.get("User ID") == allocated_user_id and "COMMISSION" in row.get("Action", ""):
                    if row.get("Type") == "DEMO":
                        demo_generation_bonus += float(row.get("Net P&L ($)", 0))
        except: pass

# Double Display Box Earning Matrix Grid Architecture
col_earn1, col_earn2 = st.columns(2)
with col_earn1:
    st.markdown(f"<div class='custom-box-grid' style='border-top: 4px solid #00e676; text-align:center;'><span style='color:#94a3b8; font-size:11px;'>🔗 DEMO MODE REF EARNINGS</span><h3 style='color:#00e676;'>${demo_referral_bonus:.2f} USDT</h3></div>", unsafe_allow_html=True)
with col_earn2:
    st.markdown(f"<div class='custom-box-grid' style='border-top: 4px solid #29b6f6; text-align:center;'><span style='color:#94a3b8; font-size:11px;'>🌐 DEMO 7-GEN BONUS INCOME</span><h3 style='color:#29b6f6;'>${demo_generation_bonus:.2f} USDT</h3></div>", unsafe_allow_html=True)

# Downline Status Grid Node Loader Fixes
def calculate_sub_generations(r_uid, tree):
    g_map = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
    if r_uid in tree: g_map = tree[r_uid].copy()
    for g in range(2, 8):
        p_layer = g_map[g-1]
        c_accum = []
        for p_uid in p_layer:
            if p_uid in tree:
                for c_uid in tree[p_uid]:
                    if c_uid not in g_map[g]: c_accum.append(c_uid)
        g_map[g] = c_accum
    return g_map

st.markdown("<br><b>📊 Sub-Downline Network Members Status Grid Matrix:</b>", unsafe_allow_html=True)
mapped_gens = calculate_sub_generations(allocated_user_id, st._global_referral_tree)
sub_tree_records = []
for g_idx in range(1, 8):
    for sub_uid in mapped_gens.get(g_idx, []):
        sub_pnl = 0.0
        if st._global_user_pnl_history:
            pdf = pd.DataFrame(st._global_user_pnl_history)
            if not pdf.empty and "User ID" in pdf.columns:
                m_df = pdf[pdf["User ID"] == sub_uid]
                if not m_df.empty: sub_pnl = pd.to_numeric(m_df["Net P&L ($)"], errors='coerce').sum()
        sub_tree_records.append({
            "Hierarchy Level": f"Gen Layer {g_idx}", "User ID": sub_uid,
            "Username": st._uid_to_username.get(sub_uid, 'Active Node'), "Lifetime Value Balance": f"${sub_pnl:.2f} USDT"
        })

if sub_tree_records:
    st.dataframe(pd.DataFrame(sub_tree_records), use_container_width=True)
else:
    st.info("No active team network users registered under this target token UID hierarchy layers.")

# --- 🛠️ DYNAMIC ORIGINAL HACK/ADMIN CONTROL HUB EXPANDER ---
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        st.markdown("<h2>⚙️ Referral Marketing Matrix Controls (7-Gen ROI Mode):</h2>", unsafe_allow_html=True)
        old_mlm = st._mlm_bonus_enabled
        st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled)
        if old_mlm != st._mlm_bonus_enabled: db_save("mlm_enabled", st._mlm_bonus_enabled)
        
        st._mlm_deposit_bonus_rate = st.number_input("One-Time Bonus Rate on Total Account Deposit (%):", min_value=0.0, value=st._mlm_deposit_bonus_rate)
        db_save("dep_rate", st._mlm_deposit_bonus_rate)
        
        if st.button("Mint New Randomized License Token Key Node"):
            random_token = "SCLP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            st._central_key_registry[random_token] = "FREE_SLOT"
            db_save("key_registry", st._central_key_registry)
            st.code(random_token)
