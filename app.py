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

# Secure Cloud Firebase Gateway Authentication Layer
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
            st.error("Missing Config Database Keys Node Property!")
            st.stop()

db = firestore.client()
def db_load(key, default_val):
    try:
        ref = db.collection("scalper_system").document(key).get()
        if ref.exists: return ref.to_dict().get("data", default_val)
        return default_val
    except: return default_val

def db_save(key, val):
    try: db.collection("scalper_system").document(key).set({"data": val})
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
if 'logged_in_user' in st.session_state and st.session_state.logged_in_user:
    u_data = st._central_user_creds.get(st.session_state.logged_in_user, {})
    curr_uid = u_data.get("uid", "GLOBAL")
    st.session_state.bot_active = db_load(f"bot_active_{curr_uid}", False)
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
        url = "https://bybit.com"
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
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"] {
        background: #06090e !important;
        background-image: radial-gradient(circle at 50% 20%, #0d1527 0%, #06090e 80%) !important;
        overflow-y: auto !important; overflow-x: hidden !important; box-sizing: border-box !important;
    }
    div[data-testid="stSidebar"] { background-color: #0c1017 !important; border-right: 1px solid #1e293b; }
    div.stButton > button:first-child { width: 100%; border-radius: 8px; font-weight: bold; font-size: 16px; height: 46px; }
    .stDataFrame, .stTable, div[data-testid="stDataFrame"] { max-width: 100% !important; overflow-x: auto !important; display: block !important; }
    div[data-testid="stMarkdownContainer"] p, span, label, h1, h2, h3, b, code { 
        word-wrap: break-word !important; white-space: normal !important; word-break: break-word !important; max-width: 100% !important;
    }
    .custom-box-grid { background-color: #141a24; padding: 15px; border-radius: 12px; margin-bottom: 12px; border: 1px solid #1f2c3f; }
    .matrix-neon-text { font-family: 'Courier New', monospace; color: #00e676; text-shadow: 0 0 8px #00e676; font-size: 13px; line-height: 1.6; }
    div[data-testid="stSlider"] div { flex-direction: column !important; align-items: flex-start !important; }
    </style>
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
                full_mobile = f"{reg_flag_code.split(' ')} {reg_phone_raw}"
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
    dashboard_mode_title = "Real Production Dashboard Mode 🟢" if is_real_live else "Demo Sandbox Dashboard Mode 🔵"
    if is_real_live: st.session_state.real_balance = db_load(f"real_balance_{allocated_user_id}", 0.0)
    else: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)

    selected_display_name = st.selectbox("Select Asset Contract Symbol Dropdown:", list(BYBYT_DATABASE_CORE.keys()), index=0)
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    
    in_position_state = db_load(f"in_position_{allocated_user_id}", False)
    locked_trade_coin = db_load(f"trade_coin_{allocated_user_id}", "NONE")
    if in_position_state and locked_trade_coin != "NONE":
        for k, v in BYBYT_DATABASE_CORE.items():
            if v["symbol"] == locked_trade_coin: coin_config = v; break
    else:
        target_symbol = coin_config["symbol"]
        db_save(f"trade_coin_{allocated_user_id}", target_symbol)
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter Matrix", value=True)
    
    st.markdown("<b style='color:#38bdf8;'>🤖 OpenRouter AI Router Configuration:</b>", unsafe_allow_html=True)
    or_api_key = st.text_input("OpenRouter API Key:", type="password", value=db_load(f"or_key_{allocated_user_id}", ""), key="openrouter_api_key_field")
    or_model_id = st.text_input("Model ID:", value=db_load(f"or_model_{allocated_user_id}", "openrouter/free"), key="openrouter_model_id_field")
    if st.button("Save AI Router Node Config", key="save_or_config_btn"):
        db_save(f"or_key_{allocated_user_id}", or_api_key); db_save(f"or_model_{allocated_user_id}", or_model_id); st.toast("Config Saved!", icon="💾")
    max_leverage_bound = int(coin_config.get('max_leverage', 100))
    if in_position_state:
        leverage = db_load(f"leverage_lock_{allocated_user_id}", 20)
        trade_amount = db_load(f"margin_lock_{allocated_user_id}", 20)
        st.sidebar.markdown(f"<div style='background-color:#1e293b; padding:8px; border-radius:5px;'><b style='color:#00e676;'>🔒 Position Active</b><br><span style='font-size:12px;color:#fff;'>Leverage: {leverage}x | Margin: ${trade_amount}</span></div>", unsafe_allow_html=True)
    else:
        leverage = st.slider("Leverage Scale Selection Array (1x-100x Override):", min_value=1, max_value=max_leverage_bound, value=20, step=1, key="absolute_leverage_node_slider")
        trade_amount = st.number_input("Margin Requirement Block (\$):", min_value=1, value=20)
        db_save(f"leverage_lock_{allocated_user_id}", leverage); db_save(f"margin_lock_{allocated_user_id}", trade_amount)
    if not in_position_state:
        price_jump_target = st.number_input("Take Profit Target Interval (\$):", value=float(coin_config["default_tp"]), format="%.6f", key="tp_input_node_box")
        stop_loss_gap = st.number_input("Stop Loss Boundary GAP Threshold (\$):", value=float(coin_config["default_sl"]), format="%.6f", key="sl_input_node_box")
        db_save(f"tp_target_{allocated_user_id}", price_jump_target); db_save(f"sl_gap_{allocated_user_id}", stop_loss_gap)
    else:
        price_jump_target = db_load(f"tp_target_{allocated_user_id}", float(coin_config["default_tp"]))
        stop_loss_gap = db_load(f"sl_gap_{allocated_user_id}", float(coin_config["default_sl"]))

    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><div style='background-color:#ff1744; padding:6px; border-radius:5px; text-align:center; margin-bottom:6px;'><b style='color:#ffffff; font-size:11px;'>🚨 LICENSE GATE ACTIVE</b></div>", unsafe_allow_html=True)
        input_license = st.text_input("License Password:", type="password", key="lic_field_sidebar", label_visibility="collapsed").strip()
        if input_license in st._central_key_registry:
            if not user_data.get("license_activated_before", False) and my_sponsor_id != "None" and st._ref_system_active:
                st._central_user_creds[st.session_state.logged_in_user]["license_activated_before"] = True; db_save("user_creds", st._central_user_creds)
                admin_fixed_bonus = float(db_load("admin_fixed_ref_usd", 10.0))
                st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": my_sponsor_id, "Coin": "REAL_LICENSE_ACTIVATION", "Action": "REF_COMMISSION_DIRECT", "Net P&L ($)": f"{admin_fixed_bonus:.2f}", "Type": "REAL"}); db_save("pnl_history", st._global_user_pnl_history)
            api_key = st.text_input("Bybit API Key Node Token:", type="password", key="api_field_sidebar")
            secret_key = st.text_input("Bybit Secret Key Node Token:", type="password", key="sec_field_sidebar")
effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011
live_price, current_rsi, ai_market_thesis, fig_candlestick = 0.0, 50.0, "SYNCING DATA FEED NODES... 📡", None
public_session = HTTP(testnet=False)
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
if fig_candlestick: st.plotly_chart(fig_candlestick, use_container_width=True)
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

balance_usd_text = f"${(st.session_state.get('real_balance' if is_real_live else 'demo_balance', 5000.0) + floating_pnl):,.2f} USDT"
st.markdown(f"<div class='custom-box-grid'>💰 <b>AVAILABLE BALANCE ({bot_mode}):</b> <h2 style='margin:0; color:#fff;'>{balance_usd_text}</h2><p style='margin:0; font-size:14px; color:{'#00e676' if floating_pnl >= 0 else '#ff1744'}; font-weight:bold;'>Live Floating P&L Indicator: {floating_pnl:+.4f} USDT</p></div>", unsafe_allow_html=True)

if st.session_state.in_position:
    is_long_pos = "LONG" in st.session_state.current_side
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    est_profit_dollars = (price_jump_target * (effective_vol / st.session_state.buy_price))
    est_loss_dollars = (stop_loss_gap * (effective_vol / st.session_state.buy_price))
    st.markdown(f"""<div style="background-color:#0b0e14; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; border-left: 5px solid #29b6f6;">
        <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Active Contract Asset: <b>{target_symbol}</b></span><br>
        <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Entry Target Metric: {st.session_state.buy_price:.6f} | Live Index Ticker: {live_price:.6f}</span><br>
        <span style="font-size:14px; color:#00e676; font-weight:bold; font-family: monospace;">Take Profit Limit: {live_target:.6f} (Estimated Gain: +${est_profit_dollars:.2f} USDT)</span><br>
        <span style="font-size:14px; color:#ff1744; font-weight:bold; font-family: monospace;">Stop Loss Boundary Node: {live_sl:.6f} (Estimated Loss: -${est_loss_dollars:.2f} USDT)</span></div>""", unsafe_allow_html=True)

# =======================================================
# 🌐 DEEPSEEK OPENROUTER NEWS & INDICATOR SWARM INTELLIGENCE
# =======================================================
if st.session_state.bot_active:
    if not st.session_state.in_position and ai_decision and or_api_key:
        try:
            news_context = "Steady global macro trend line pattern."
            
            # --- 🛡️ FAIL-SAFE NEWS SEPARATOR: CRASH PROTECTION GUARD ---
            try:
                news_res = requests.get("https://cryptopanic.com", timeout=3)
                if news_res.status_code == 200:
                    news_data = news_res.json()
                    news_titles = [post.get('title', '') for post in news_data.get('results', [])[:4]]
                    if news_titles: news_context = " | ".join(news_titles)
            except:
                pass  # নিউজ সার্ভার ব্লক বা এরর দিলেও লুপ থামবে না, বাইপাস হয়ে যাবে
            
            if not df_kline.empty and len(df_kline) >= 5:
                recent_candles = df_kline.tail(5).to_dict(orient="records")
                ma_series = df_kline['close'].rolling(window=7).mean()
                last_ma = float(ma_series.iloc[-1]) if not ma_series.empty else live_price
                market_context_prompt = (
                    f"Asset: {target_symbol} | Live Price: {live_price} | RSI: {current_rsi:.2f} | MA-7: {last_ma:.6f}\n"
                    f"International Crypto News Summary: {news_context}\n"
                    f"Config Matrix -> Leverage: {leverage}x, TP: {price_jump_target}, SL: {stop_loss_gap}\n"
                    f"Candlesticks: {json.dumps(recent_candles)}\n\n"
                    f"INSTRUCTION: You are a professional crypto scalping bot. Respond with EXACTLY ONE UPPERCASE WORD: 'LONG' or 'SHORT'. If the market is chop or sideways, respond with 'HOLD'. No explanation, no punctuation, no markdown."
                )
                
                headers = {
                    "Authorization": f"Bearer {or_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://streamlit.io",
                    "X-Title": "Bybit AI Scalper Swarm Engine",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json"
                }
                
                payload = {
                    "model": or_model_id if or_model_id else "google/gemini-2.5-flash:free",
                    "messages": [{"role": "user", "content": market_context_prompt}]
                }
                
                st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Connecting DeepSeek Brain over OpenRouter...")
                or_response = requests.post("https://openrouter.ai", headers=headers, json=payload, timeout=10)
                if or_response.status_code == 200:
                    try:
                        res_json = or_response.json()
                        ai_raw_word = res_json['choices']['message']['content'].strip().upper()
                        
                        # এআই-এর বড় রেসপন্সের ভেতর থেকে সুনির্দিষ্ট সিগন্যাল ফিল্টার করা হচ্ছে
                        resolved_signal = "HOLD"
                        if "LONG" in ai_raw_word: resolved_signal = "LONG"
                        elif "SHORT" in ai_raw_word: resolved_signal = "SHORT"
                        
                        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Brain Signal: '{resolved_signal}'")
                        
                        if resolved_signal == "LONG":
                            db_save(f"in_position_{allocated_user_id}", True); db_save(f"buy_price_{allocated_user_id}", live_price); db_save(f"current_side_{allocated_user_id}", "LONG"); db_save(f"trade_coin_{allocated_user_id}", target_symbol)
                            db_save(f"tp_target_{allocated_user_id}", price_jump_target); db_save(f"sl_gap_{allocated_user_id}", stop_loss_gap)
                            st.toast(f"🟢 Auto Long Opened: {target_symbol}", icon="🚀"); st.rerun()
                        elif resolved_signal == "SHORT":
                            db_save(f"in_position_{allocated_user_id}", True); db_save(f"buy_price_{allocated_user_id}", live_price); db_save(f"current_side_{allocated_user_id}", "SHORT"); db_save(f"trade_coin_{allocated_user_id}", target_symbol)
                            db_save(f"tp_target_{allocated_user_id}", price_jump_target); db_save(f"sl_gap_{allocated_user_id}", stop_loss_gap)
                            st.toast(f"🔴 Auto Short Opened: {target_symbol}", icon="🚨"); st.rerun()
                    except Exception as parse_err:
                        st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Signal Blank or Range-bound. Waiting...")
                else:
                    # ওপেনরাউটার ব্লক বা এরর থাকলে লোকাল এআই অ্যালগরিদম ব্যাকআপ মোড চালু হবে
                    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Cloud Error {or_response.status_code}. Activating Local Backup Brain...")
                    local_decision = "HOLD"
                    if current_rsi < 32: local_decision = "LONG"
                    elif current_rsi > 68: local_decision = "SHORT"
                    
                    st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Local Signal: '{local_decision}' for {target_symbol}")
                    if local_decision in ["LONG", "SHORT"]:
                        db_save(f"in_position_{allocated_user_id}", True); db_save(f"buy_price_{allocated_user_id}", live_price); db_save(f"current_side_{allocated_user_id}", local_decision); db_save(f"trade_coin_{allocated_user_id}", target_symbol)
                        db_save(f"tp_target_{allocated_user_id}", price_jump_target); db_save(f"sl_gap_{allocated_user_id}", stop_loss_gap)
                        st.toast(f"⚡ Backup Engine Executed: {local_decision}", icon="⚙️"); st.rerun()
        except Exception as e:
            st.session_state.engine_logs.append(f"[{time.strftime('%H:%M:%S')}] Loop Error Node: {str(e)}")
    if st.session_state.in_position and live_price > 0:
        is_long_pos = "LONG" in st.session_state.current_side
        saved_tp = db_load(f"tp_target_{allocated_user_id}", float(coin_config["default_tp"]))
        saved_sl = db_load(f"sl_gap_{allocated_user_id}", float(coin_config["default_sl"]))
        target_tp_price = (st.session_state.buy_price + saved_tp) if is_long_pos else (st.session_state.buy_price - saved_tp)
        target_sl_price = (st.session_state.buy_price - saved_sl) if is_long_pos else (st.session_state.buy_price + saved_sl)
        hit_tp = (live_price >= target_tp_price) if is_long_pos else (live_price <= target_tp_price)
        hit_sl = (live_price <= target_sl_price) if is_long_pos else (live_price >= target_sl_price)
        
        if hit_tp or hit_sl:
            local_final_pnl = ((live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)) if is_long_pos else ((st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price))
            net_pnl = local_final_pnl - estimated_fee
            if is_real_live: st.session_state.real_balance += net_pnl; db_save(f"real_balance_{allocated_user_id}", st.session_state.real_balance)
            else: st.session_state.demo_balance += net_pnl; db_save(f"balance_{allocated_user_id}", st.session_state.demo_balance)
            if net_pnl > 0: st.session_state.win_count += 1
            else: st.session_state.loss_count += 1
            db_save(f"win_{allocated_user_id}", st.session_state.win_count); db_save(f"loss_{allocated_user_id}", st.session_state.loss_count)
            st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": allocated_user_id, "Coin": target_symbol, "Action": f"AUTO CLOSE {'TP' if hit_tp else 'SL'}", "Net P&L ($)": f"{net_pnl:.2f}", "Type": "REAL" if is_real_live else "DEMO"})
            db_save("pnl_history", st._global_user_pnl_history); db_save(f"in_position_{allocated_user_id}", False); db_save(f"buy_price_{allocated_user_id}", 0.0); db_save(f"current_side_{allocated_user_id}", "NONE"); st.session_state.in_position = False; st.rerun()
# --- 🪐 REAL-TIME LIVE BACKEND TECHNICAL LOG NODE BOX ---
st.markdown("<b>🖥️ Real-Time AI Swarm Scalper Loop Sequence Log Panel:</b>", unsafe_allow_html=True)
log_text = "\n".join(st.session_state.engine_logs[-6:])
st.text_area(label="Live Engine Activity Terminal Window Property Node", value=log_text, height=135, label_visibility="collapsed")

if not ai_decision and not st.session_state.in_position:
    st.markdown("<p style='color:#ffcc00; font-weight:bold;'>🕹️ Manual Trading Panel Active</p>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    # ফিক্সড হার্ড-ল্যাচ বাটন: ক্লিক করার সাথে সাথে ডাটাবেজে পার্মানেন্ট সত্য (True) বা মিথ্যা (False) লক হয়ে যাবে
    if not st.session_state.bot_active:
        if st.button("🟢 START ENGINE SCALPER LOOP SEQUENCE", key="final_latch_start_btn"):
            st.session_state.bot_active = True
            db_save(f"bot_active_{allocated_user_id}", True)
            st.toast("AI Scalper Engine Lock Activated!", icon="🚀")
            st.rerun()
    else:
        if st.button("🔴 STOP ENGINE SCALPER LOOP SEQUENCE", key="final_latch_stop_btn"):
            st.session_state.bot_active = False
            db_save(f"bot_active_{allocated_user_id}", False)
            st.toast("AI Scalper Engine Safely Disengaged.", icon="🛑")
            st.rerun()
with c2:
    if st.button("🚨 EMERGENCY LIQUIDATE CLOSE ORDER POSITION", disabled=not st.session_state.in_position, key="force_sell_engine_btn"):
        db_save(f"in_position_{allocated_user_id}", False)
        st.session_state.in_position = False
        st.rerun()

# 1.5 Second Background Heartbeat Refresher Frame Node Loop
st.markdown("""<iframe src="about:blank" style="display:none;" onload="setTimeout(function(){window.location.reload();}, 1500);"></iframe>""", unsafe_allow_html=True)
# --- 🌿 DYNAMIC MARKETING NETWORK MODULE PANEL HUB ---
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
st.markdown("<br><b style='color:#f5a623;'>📊 Sub-Downline Network Members Status Grid Management Node:</b>", unsafe_allow_html=True)
mapped_gens = calculate_sub_generations(search_uid_input, st._global_referral_tree)
sub_tree_records = []
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
