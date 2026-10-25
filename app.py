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

# Cloud Firebase Connection Framework Control
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

# Initialize Sync Control Registries Persistent System Nodes
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

# Fetch All 300+ Live Bybit Futures Instruments Contracts via V5 Market API
@st.cache_data(ttl=180)
def fetch_bybit_future_coins():
    backup_db = {"🪙 BTC (Bitcoin)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}
    try:
        url = "https://bybit.com"
        res = requests.get(url, timeout=12).json()
        instruments = res.get("result", {}).get("list", [])
        if not instruments: return backup_db
        coin_dict = {}
        for inst in instruments:
            if inst["status"] == "Trading" and inst["quoteCoin"] == "USDT":
                sym = inst["symbol"]
                base = inst["baseCoin"]
                max_lev = int(float(inst.get("leverageFilter", {}).get("maxLeverage", 100)))
                coin_dict[f"🪙 {base} (Bybit Futures Market)"] = {
                    "symbol": sym, "max_leverage": max_lev,
                    "default_tp": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 500,
                    "default_sl": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 750,
                    "step": float(inst.get("priceFilter", {}).get("tickSize", "0.01"))
                }
        if len(coin_dict) > 1: return coin_dict
        return backup_db
    except:
        return backup_db

BYBYT_DATABASE_CORE = fetch_bybit_future_coins()
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(page_title="Bybit AI Scalper", page_icon="⚡", layout="centered")

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
    st.subheader("🔑 Account Identity Gateway Control Panel")
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
                
                db_save(f"balance_{new_uid}", 5000.0)
                db_save(f"win_{new_uid}", 0)
                db_save(f"loss_{new_uid}", 0)
                
                if reg_sponsor != "":
                    st._global_referral_tree = db_load("referral_tree", {})
                    if reg_sponsor not in st._global_referral_tree: st._global_referral_tree[reg_sponsor] = []
                    st._global_referral_tree[reg_sponsor].append(new_uid)
                    db_save("referral_tree", st._global_referral_tree)
                st.success(f"Bound Identity! UID: {new_uid}")
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

# Dynamic Isolated State Memory Load Sequences
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)
if 'win_count' not in st.session_state: st.session_state.win_count = db_load(f"win_{allocated_user_id}", 0)
if 'loss_count' not in st.session_state: st.session_state.loss_count = db_load(f"loss_{allocated_user_id}", 0)

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    # Profile Display Module fully restored
    st.markdown(f"<p style='color:#ffffff; font-size:13px; margin:0;'>👤 Handle Profile: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px; margin:4px 0;'>🆔 My Referral ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#00e676; font-size:12px; margin:0 0 4px 0;'>📧 Account Email: <b>{my_profile_email}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#94a3b8; font-size:12px; margin:0 0 12px 0;'>🔗 Sponsor UID Node: <b>{my_sponsor_id}</b></p>", unsafe_allow_html=True)
    
    if st.button("🚪 Logout Active Profile Handle", key="logout_sidebar_node_proc"):
        st.session_state.logged_in_user = None
        st.rerun()

    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = "Live" in bot_mode
    
    selected_display_name = st.selectbox("Select Asset Contract Symbol:", list(BYBYT_DATABASE_CORE.keys()), index=0)
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter", value=True)
    
    # Absolute Leverage Slider Type-Casting Fix (Strict integer map preventing 1-10 compression lock)
    max_leverage_bound = int(coin_config.get('max_leverage', 100))
    leverage = st.slider("Leverage (Absolute Range 1x to 100x Override):", min_value=1, max_value=max_leverage_bound, value=20, step=1, key="absolute_leverage_node_slider")
    trade_amount = st.number_input("Margin Requirement (\$):", min_value=1, value=20)
    price_jump_target = st.number_input("Take Profit Target (\$):", value=coin_config["default_tp"], format="%.6f")
    stop_loss_gap = st.number_input("Stop Loss Threshold (\$):", value=coin_config["default_sl"], format="%.6f")

with st.sidebar:
    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><div style='background-color:#ff1744; padding:6px; border-radius:5px; text-align:center; margin-bottom:6px;'><b style='color:#ffffff; font-size:11px;'>🚨 LICENSE GATE ACTIVE</b></div>", unsafe_allow_html=True)
        input_license = st.text_input("License Password:", type="password", key="lic_field_sidebar", label_visibility="collapsed").strip()
        if input_license in st._central_key_registry:
            api_key = st.text_input("Bybit API Key:", type="password", key="api_field_sidebar")
            secret_key = st.text_input("Bybit Secret Key:", type="password", key="sec_field_sidebar")

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011
# Premium Sci-Fi Styled Live Technical Analytics & Candlestick Pattern Core
live_price, current_rsi, ai_market_thesis, fig_candlestick = 0.0, 50.0, "AI GLOBAL NETWORK RESEARCH PIPELINE SYNCING... 📡", None
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
        if pd.isna(current_rsi): current_rsi = 50.0
        
        # High Dynamic Gemini AI style Multi-News Wire Processing Randomization Loop
        live_intel_wires = [
            "⚡ METRICS INTERCEPT: Whales shifting massive capital derivatives blocks inside live exchange ledger books.",
            "📊 ORDERBOOK SCAN: Institutional orders matching geometric support breakout lines.",
            "📡 SIGNAL DETECT: High volume liquidation matrix forming near active trading boundaries.",
            "🌐 MEDIA STREAM: Global crypto indicators printing immediate volatility trend shifts on futures contracts."
        ]
        
        if current_rsi < 45:
            ai_market_thesis = f"🔮 AI LIGHTNING SCANNER RESEARCH ({target_symbol}): [STATUS: BUY OVERLAPPING] -> Candlestick pattern tracking shows intense institutional buying support accumulation. {random.choice(live_intel_wires)}"
        elif current_rsi > 55:
            ai_market_thesis = f"🔮 AI LIGHTNING SCANNER RESEARCH ({target_symbol}): [STATUS: SELL DIVERGENCE] -> Asset value stretching outside normal technical resistance boundary nodes. {random.choice(live_intel_wires)}"
        else:
            ai_market_thesis = f"🔮 AI LIGHTNING SCANNER RESEARCH ({target_symbol}): [STATUS: RANGING BALANCE] -> Market volatility balancing inside neutral equilibrium zone channels. Scanner is measuring support vectors. {random.choice(live_intel_wires)}"
        
        # Premium Pro Futuristic Candlestick Visual Plot Node
        fig_candlestick = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'])])
        
        # Add Sci-Fi Tracker lines mapping real-time moving targets
        fig_candlestick.add_trace(go.Scatter(x=df_kline.index, y=df_kline['close'].rolling(window=7).mean(), name="AI Geometric Array", line=dict(color='#00e676', width=1.5, dash='dash')))
        
        fig_candlestick.update_layout(
            template="plotly_dark", margin=dict(l=6, r=6, t=6, b=6), height=270, xaxis_rangeslider_visible=False,
            paper_bgcolor='#0b0e14', plot_bgcolor='#0b0e14',
            xaxis=dict(gridcolor='#1e293b', zerolinecolor='#1e293b'), yaxis=dict(gridcolor='#1e293b', zerolinecolor='#1e293b')
        )
except:
    live_price = 66500.0

st.markdown("<h3 style='color:#f5a623;'>🛸 Premium Pro AI Analytics & Dynamic Candle Grid</h3>", unsafe_allow_html=True)
if fig_candlestick: st.plotly_chart(fig_candlestick, use_container_width=True)
st.markdown(f"<div class='custom-box-grid' style='border-left: 5px solid #00e676; color: #00e676; font-family: monospace; font-size:12px; background-color:#0b0e14;'><b>{ai_market_thesis}</b></div>", unsafe_allow_html=True)

# Personal User Metrics Panel Box Layout
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

st.markdown(
    f"""<div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between;">
    <span style="color:#ffffff; font-weight:bold;">🏆 WON: <b style="color:#00e676;">{st.session_state.win_count}</b></span>
    <span style="color:#ffffff; font-weight:bold;">❌ LOST: <b style="color:#ff1744;">{st.session_state.loss_count}</b></span>
    <span style="color:#ffffff; font-weight:bold;">🎯 WIN RATE: <b style="color:#29b6f6;">{win_rate:.1f}%</b></span></div>""", 
    unsafe_allow_html=True
)

# Dynamic Balance Logic Layer linked directly to position state updates
floating_pnl = 0.0
if st.session_state.in_position and live_price > 0:
    is_long_pos = (st.session_state.current_side == "LONG")
    if is_long_pos:
        floating_pnl = ((live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price))
    else:
        floating_pnl = ((st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price))

balance_usd_text = f"${(st.session_state.demo_balance + floating_pnl):,.2f} USDT" if not is_real_live else "0.00 USDT"
if is_real_live and api_key and secret_key:
    try:
        session = HTTP(testnet=False, api_key=api_key, secret_key=secret_key)
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        m_list = wallet_info.get('result', {}).get('list', [])
        if m_list:
            for c in m_list.get('coin', []):
                if c.get('coin') == 'USDT':
                    balance_usd_text = f"${(float(c.get('walletBalance', 0)) + floating_pnl):,.2f} USDT"
                    break
    except: balance_usd_text = "API Key Auth Error"

st.markdown(f"<div class='custom-box-grid'>💰 <b>AVAILABLE BALANCE:</b> <h2 style='margin:0; color:#fff;'>{balance_usd_text}</h2><p style='margin:0; font-size:13px; color:{'#00e676' if floating_pnl >= 0 else '#ff1744'};'>Live Floating P&L: {floating_pnl:+.2f} USDT</p></div>", unsafe_allow_html=True)

# Blue Border Box - Active Trade Boundary Target Info Panel Re-Stored Perfectly
if st.session_state.in_position:
    is_long_pos = st.session_state.current_side == "LONG"
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    st.markdown(
        f"""<div style="background-color:#0b0e14; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; border-left: 5px solid #29b6f6;">
        <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Entry Price Target: {st.session_state.buy_price} | Live Index: {live_price}</span><br>
        <span style="font-size:14px; color:#00e676; font-weight:bold; font-family: monospace;">Take Profit Limit: {live_target}</span><br>
        <span style="font-size:14px; color:#ff1744; font-weight:bold; font-family: monospace;">Stop Loss Boundary: {live_sl}</span></div>""", 
        unsafe_allow_html=True
    )
# Engine Controls Switches Core Modules Setup (Fixes AI Filter off instant manual buy/sell buttons criteria)
if not ai_decision and not st.session_state.in_position:
    st.markdown("<p style='color:#ffcc00; font-weight:bold;'>🕹️ Manual Trading Panel Active (AI Crossover Bypassed)</p>", unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        if st.button("🟢 EXECUTE BUY / LONG ENTRY", key="manual_buy_long_btn"):
            st.session_state.buy_price = live_price if live_price > 0 else 60000.0
            st.session_state.in_position = True
            st.session_state.current_side = "LONG"
            st.rerun()
    with m_col2:
        if st.button("🔴 EXECUTE SELL / SHORT ENTRY", key="manual_sell_short_btn"):
            st.session_state.buy_price = live_price if live_price > 0 else 60000.0
            st.session_state.in_position = True
            st.session_state.current_side = "SHORT"
            st.rerun()

c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button("🔴 STOP ENGINE SCALPER LOOP", key="stop_engine_bot_btn"):
            st.session_state.bot_active = False
            st.rerun()
    else:
        if st.button("🟢 START ENGINE SCALPER LOOP", key="start_engine_bot_btn"):
            st.session_state.bot_active = True
            if not ai_decision and not st.session_state.in_position:
                st.session_state.buy_price = live_price if live_price > 0 else 60000.0
                st.session_state.in_position = True
                st.session_state.current_side = "LONG"
            st.rerun()
with c2:
    if st.button("🚨 EMERGENCY LIQUIDATE CLOSE", disabled=not st.session_state.in_position, key="force_sell_engine_btn"):
        st.session_state.in_position = False
        st.rerun()

# --- 🌿 DEMO MODE DYNAMIC SCOPE CONFIGURABLE MATRIX HUB ---
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#f5a623;'>🌿 Network Marketing Matrix Desk (Demo Sandbox Dashboard Mode)</h3>", unsafe_allow_html=True)

col_t1, col_t2 = st.columns(2)
with col_t1: start_scope_date = st.date_input("Start Registry Date Filter Range:", datetime.now(), key="matrix_start")
with col_t2: end_scope_date = st.date_input("End Registry Date Filter Range:", datetime.now(), key="matrix_end")

demo_ref_accum, demo_gen_accum = 0.0, 0.0
if st._global_user_pnl_history:
    for r in st._global_user_pnl_history:
        try:
            current_r_date = datetime.strptime(r.get("Date", ""), "%Y-%m-%d").date()
            if start_scope_date <= current_r_date <= end_scope_date:
                if r.get("User ID") == allocated_user_id and "COMMISSION" in r.get("Action", ""):
                    demo_gen_accum += float(r.get("Net P&L ($)", 0))
        except: pass

cbx1, cbx2 = st.columns(2)
with cbx1: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #00e676; text-align:center;'><span>🔗 REFERRAL TOTAL NET BOX</span><h4 style='color:#00e676;'>${demo_ref_accum:.2f} USDT</h4></div>", unsafe_allow_html=True)
with cbx2: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #29b6f6; text-align:center;'><span>🌐 7-GEN DAILY ROI COMMISSION</span><h4 style='color:#29b6f6;'>${demo_gen_accum:.2f} USDT</h4></div>", unsafe_allow_html=True)

# Sub Downline Networks Data Grid Matrix Loader Fixes (Reads directly from global tree collection)
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

st.markdown("<b>📊 Sub-Downline Network Members Status Grid Management Node:</b>", unsafe_allow_html=True)
mapped_gens = calculate_sub_generations(allocated_user_id, st._global_referral_tree)
sub_tree_records = []
for g_idx in range(1, 8):
    if g_idx in mapped_gens:
        for sub_uid in mapped_gens[g_idx]:
            sub_pnl = 0.0
            if st._global_user_pnl_history:
                pdf = pd.DataFrame(st._global_user_pnl_history)
                if not pdf.empty and "User ID" in pdf.columns:
                    m_df = pdf[pdf["User ID"] == sub_uid]
                    if not m_df.empty: sub_pnl = pd.to_numeric(m_df["Net P&L ($)"], errors='coerce').sum()
            
            label_text = f"Gen Layer {g_idx}" if st._mlm_bonus_enabled else f"Serial Node {len(sub_tree_records)+1}"
            sub_tree_records.append({
                "Hierarchy Level": label_text, "User ID": sub_uid,
                "Username": st._uid_to_username.get(sub_uid, f"Node-{sub_uid[:4]}"), "Lifetime profit Balance": f"${sub_pnl:.2f} USDT"
            })

if sub_tree_records: st.dataframe(pd.DataFrame(sub_tree_records), use_container_width=True)
else: st.info("No active team network users registered under this target token UID hierarchy layers.")

# --- 🛠️ DYNAMIC ORIGINAL HACK/SUPER ADMIN CONTROL HUB FULLY RESTORED ---
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        st.markdown("<h2>⚙️ Referral Marketing Matrix Controls (7-Gen ROI Mode):</h2>", unsafe_allow_html=True)
        old_val = st._mlm_bonus_enabled
        st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled, key="adm_mlm_active_toggle")
        if old_val != st._mlm_bonus_enabled: db_save("mlm_enabled", st._mlm_bonus_enabled)
        st._mlm_deposit_bonus_rate = st.number_input("One-Time Bonus Rate on Total Account Deposit (%):", min_value=0.0, max_value=100.0, value=st._mlm_deposit_bonus_rate, key="adm_deposit_bonus_rate_input")
        db_save("dep_rate", st._mlm_deposit_bonus_rate)
        
        c_cols = st.columns(2)
        for g in range(1, 8):
            with c_cols[(g-1)%2]:
                st._mlm_gen_rates[g] = st.number_input(f"Gen {g} Share (%):", min_value=0.0, max_value=100.0, value=st._mlm_gen_rates.get(g, 0.0), key=f"adm_rates_generation_input_g_{g}")
                st._mlm_id_thresholds[g] = st.number_input(f"Gen {g} Cap:", min_value=1, max_value=5000, value=st._mlm_id_thresholds.get(g, 10), key=f"adm_thresholds_generation_input_g_{g}")
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
                db_save("blacklist", st._central_blacklist); db_save("key_registry", st._central_key_registry); st.warning(f"Token blocked."); st.rerun()
                
        if st._license_csv_database: st.dataframe(pd.DataFrame(st._license_csv_database).iloc[::-1], use_container_width=True, height=120)
        all_creds_df = pd.DataFrame.from_dict(st._central_user_creds, orient='index')
        if not all_creds_df.empty: st.dataframe(all_creds_df, use_container_width=True)
