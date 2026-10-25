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

# Cloud Firebase Connection Architecture
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

# Global Memory Sync Modules
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

# Fetch Dynamic Live Future Pairs from Bybit Exchange
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
                display_name = f"🪙 {base} (Bybit Futures)"
                coin_dict[display_name] = {
                    "symbol": sym, "max_leverage": max_lev,
                    "default_tp": 100.0, "default_sl": 150.0, "step": 10.0
                }
        return coin_dict if coin_dict else {"🪙 BTC": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}
    except:
        return {"🪙 BTC": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0}}

BYBYT_DATABASE_CORE = fetch_bybit_future_coins()
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(page_title="Bybit AI Scalper", page_icon="⚡", layout="centered")

# Responsive CSS Framework avoiding mobile layouts breaking
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
    st.subheader("🔑 Account Auth Panel")
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
                
                # Isolated dynamic setup per user account explicitly
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

# Isolated User Data Loaders
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)
if 'win_count' not in st.session_state: st.session_state.win_count = db_load(f"win_{allocated_user_id}", 0)
if 'loss_count' not in st.session_state: st.session_state.loss_count = db_load(f"loss_{allocated_user_id}", 0)

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Panel</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#e2a826; font-size:13px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px;'>🆔 My Referral ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Logout Account", key="logout_sidebar_btn"):
        st.session_state.logged_in_user = None
        st.rerun()

    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = "Live" in bot_mode
    selected_display_name = st.selectbox("Select Asset Contract:", list(BYBYT_DATABASE_CORE.keys()), index=0)
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter", value=True)
    
    # Absolute Leverage Fix preventing layout scale compression down to 1-10 slider error
    leverage = st.slider(f"Leverage (Max {coin_config['max_leverage']}x):", min_value=1, max_value=int(coin_config['max_leverage']), value=20)
    trade_amount = st.number_input("Margin Requirement (\$):", min_value=1, value=20)
    price_jump_target = st.number_input("Take Profit Target (\$):", value=coin_config["default_tp"], format="%.4f")
    stop_loss_gap = st.number_input("Stop Loss Threshold (\$):", value=coin_config["default_sl"], format="%.4f")

# Live Exchange License Gate Activation Module Re-Stored
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

# Advanced Technical Analytics Scanner & Gemini Research Pipeline Integration
live_price, current_rsi, ai_market_thesis, fig_candlestick = 0.0, 50.0, "MARKET ANALYTICS SCANNING... ⏳", None
try:
    public_session = HTTP(testnet=False)
    response = public_session.get_kline(category="linear", symbol=target_symbol, interval="1", limit=20)
    klines = response.get('result', {}).get('list', [])
    if klines:
        df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover']).iloc[::-1].reset_index(drop=True)
        for c in ['open', 'high', 'low', 'close']: df_kline[c] = pd.to_numeric(df_kline[c])
        live_price = df_kline['close'].iloc[-1]
        
        # Tech Indicators Computation Module
        delta = df_kline['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
        rs = gain / (loss + 1e-10)
        current_rsi = (100 - (100 / (1 + rs))).iloc[-1]
        
        # Gemini AI style pre-trade research observations engine simulation
        if current_rsi < 45: ai_market_thesis = "💡 GEMINI TECHNICAL ANALYSIS: Market is oversold. Research indicates highly favorable long entry opportunity confirmation."
        elif current_rsi > 55: ai_market_thesis = "💡 GEMINI TECHNICAL ANALYSIS: Asset displaying heavy buying volume pressure. Bearish trend reversal pattern building up."
        else: ai_market_thesis = "💡 GEMINI TECHNICAL ANALYSIS: Market moving sideways. Scanning support and resistance thresholds before safe position entry."
        
        # --- DYNAMIC CHART VISUALIZATION MODULE ---
        fig_candlestick = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'])])
        fig_candlestick.update_layout(theme="dark", margin=dict(l=10, r=10, t=10, b=10), height=250, xaxis_rangeslider_visible=False)
except:
    live_price = 62000.0

# Render Analytics Real-Time Observation Panels
st.markdown("<h3 style='color:#f5a623;'>📊 Live Bot Market Research & Candle Feed</h3>", unsafe_allow_html=True)
if fig_candlestick: st.plotly_chart(fig_candlestick, use_container_width=True)
st.markdown(f"<div class='custom-box-grid' style='border-left: 5px solid #29b6f6; color: #29b6f6;'><b>{ai_market_thesis}</b></div>", unsafe_allow_html=True)
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

st.markdown(
    f"""<div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between;">
    <span style="color:#ffffff; font-weight:bold;">🏆 WON: <b style="color:#00e676;">{st.session_state.win_count}</b></span>
    <span style="color:#ffffff; font-weight:bold;">❌ LOST: <b style="color:#ff1744;">{st.session_state.loss_count}</b></span>
    <span style="color:#ffffff; font-weight:bold;">🎯 WIN RATE: <b style="color:#29b6f6;">{win_rate:.1f}%</b></span></div>""", 
    unsafe_allow_html=True
)

st.markdown(f"<div class='custom-box-grid'>💰 <b>AVAILABLE BALANCE:</b> <h2 style='margin:0; color:#fff;'>${st.session_state.demo_balance:,.2f} USDT</h2></div>", unsafe_allow_html=True)

# Engine Controls Engine Loop Sequences
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button("🔴 STOP ENGINE BLOCK"):
            st.session_state.bot_active = False
            st.rerun()
    else:
        if st.button("🟢 START ACTIVE SCALPER"):
            st.session_state.bot_active = True
            st.rerun()
with c2:
    if st.button("🚨 EMERGENCY LIQUIDATE Close Position", disabled=not st.session_state.in_position):
        st.session_state.in_position = False
        st.rerun()

# --- 🌿 DEMA MODE 7-GENERATION REGISTRY NETWORKS FILTER BOX ---
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown("<h3 style='color:#f5a623;'>🌿 Network Marketing Matrix Desk (Demo Sandbox Dashboard Mode)</h3>", unsafe_allow_html=True)

col_t1, col_t2 = st.columns(2)
with col_t1: start_scope_date = st.date_input("Start Earning Scope Filter Date:", datetime.now(), key="matrix_start")
with col_t2: end_scope_date = st.date_input("End Earning Scope Filter Date:", datetime.now(), key="matrix_end")

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

# Original Downline Tree Status Processing Module
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
    for sub_uid in mapped_gens.get(g_idx, []):
        sub_pnl = 0.0
        if st._global_user_pnl_history:
            pdf = pd.DataFrame(st._global_user_pnl_history)
            if not pdf.empty and "User ID" in pdf.columns:
                m_df = pdf[pdf["User ID"] == sub_uid]
                if not m_df.empty: sub_pnl = pd.to_numeric(m_df["Net P&L ($)"], errors='coerce').sum()
        sub_tree_records.append({"Hierarchy Level": f"Gen {g_idx}", "User ID": sub_uid, "Username": st._uid_to_username.get(sub_uid, 'Unknown Node'), "Lifetime profit Balance": f"${sub_pnl:.2f} USDT"})

if sub_tree_records: st.dataframe(pd.DataFrame(sub_tree_records), use_container_width=True)
else: st.info("No active team network users registered under this target token UID.")

# --- 🛠️ DYNAMIC ORIGINAL HACK/ADMIN CONTROL HUB EXPANDER RESTORED ---
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
