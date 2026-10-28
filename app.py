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

@st.cache_data(ttl=30)
def fetch_bybit_future_coins():
    backup_database = {
        "🪙 BTC (Bitcoin)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0},
        "🔷 ETH (Ethereum)": {"symbol": "ETHUSDT", "max_leverage": 100, "default_tp": 8.0, "default_sl": 15.0, "step": 1.0},
        "☀️ SOL (Solana)": {"symbol": "SOLUSDT", "max_leverage": 50, "default_tp": 1.5, "default_sl": 3.0, "step": 0.1},
        "💥 XRP (Ripple)": {"symbol": "XRPUSDT", "max_leverage": 100, "default_tp": 0.015, "default_sl": 0.03, "step": 0.001},
        "🐶 DOGE (Dogecoin)": {"symbol": "DOGEUSDT", "max_leverage": 50, "default_tp": 0.004, "default_sl": 0.01, "step": 0.0005}
    }
    try:
        url = "https://bybit.com"
        res = requests.get(url, timeout=12).json()
        instruments = res.get("result", {}).get("list", [])
        for inst in instruments:
            if inst["status"] == "Trading" and inst["quoteCoin"] == "USDT":
                sym = inst["symbol"]
                base = inst["baseCoin"]
                max_lev = int(float(inst.get("leverageFilter", {}).get("maxLeverage", 100)))
                backup_database[f"🪙 {base} (Bybit Futures Market)"] = {
                    "symbol": sym, "max_leverage": max_lev,
                    "default_tp": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 400,
                    "default_sl": float(inst.get("priceFilter", {}).get("tickSize", "0.01")) * 600,
                    "step": float(inst.get("priceFilter", {}).get("tickSize", "0.01"))
                }
        return backup_database
    except:
        return backup_database

BYBYT_DATABASE_CORE = fetch_bybit_future_coins()
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(page_title="Bybit AI Scalper", page_icon="⚡", layout="centered")

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

if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = st.query_params.get("session_user", None)

if st.session_state.logged_in_user is None:
    st.markdown("<div style='background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center;'><h1 style='margin: 0; color: #0b0e14; font-size: 26px; font-weight: bold;'>BYBIT AI PRO SCALPER</h1></div>", unsafe_allow_html=True)
    st.subheader("🔑 Account Identity Gateway Control Panel")
    auth_mode = st.radio("Choose Layer:", ["Secure Login Profile", "Mint New Account ID", "Forget Password Profile"])
    
    if auth_mode == "Mint New Account ID":
        reg_username = st.text_input("Username Handle:", key="reg_u").strip()
        reg_password = st.text_input("Password Phrase:", type="password", key="reg_p").strip()
        reg_email = st.text_input("Google Mail (Gmail ID):", key="reg_e").strip()
        
        global_country_list = ["Bangladesh", "United States", "United Kingdom", "United Arab Emirates", "Saudi Arabia", "Malaysia", "India", "Pakistan", "Kuwait", "Qatar", "Oman", "Singapore", "Canada", "Australia", "Germany", "Italy", "France", "Japan"]
        reg_country = st.selectbox("Select Profile Country (Mandatory):", global_country_list, index=0)
        
        global_phone_flags = [
            "🇧🇩 +880 (Bangladesh)", "🇺🇸 +1 (United States)", "🇬🇧 +44 (United Kingdom)", 
            "🇦🇪 +971 (UAE)", "🇸🇦 +966 (Saudi Arabia)", "🇲🇾 +60 (Malaysia)", 
            "🇮🇳 +91 (India)", "🇵🇰 +92 (Pakistan)", "🇰帶 +965 (Kuwait)", "🇶🇦 +974 (Qatar)", "🇨🇦 +1 (Canada)", "🇦🇺 +61 (Australia)"
        ]
        reg_flag_code = st.selectbox("Select Phone Flag Country Code:", global_phone_flags, index=0)
        reg_phone_raw = st.text_input("Mobile Number (Without Country Code):", key="reg_ph_num_raw").strip()
        reg_school = st.text_input("First School Name? (Security Answer Check):", key="reg_sch").strip()
        reg_sponsor = st.text_input("Sponsor Referral Token ID:", key="reg_s").strip()
        
        if st.button("🚀 Register My Handle", key="reg_submit_btn"):
            st._central_user_creds = db_load("user_creds", {})
            if reg_username == "" or reg_password == "" or reg_email == "" or reg_school == "" or reg_phone_raw == "":
                st.error("Mandatory registry input fields are left blank! Process blocked.")
            elif reg_username in st._central_user_creds: st.error("Username already active!")
            else:
                new_uid = "UID-" + "".join(random.choices(string.digits, k=6))
                resolved_sponsor_uid = "None"
                if reg_sponsor != "":
                    resolved_sponsor_uid = reg_sponsor
                    if reg_sponsor in st._central_user_creds:
                        resolved_sponsor_uid = st._central_user_creds[reg_sponsor].get("uid", reg_sponsor)
                    else:
                        for u_name, data in st._central_user_creds.items():
                            if data.get("uid") == reg_sponsor or u_name == reg_sponsor:
                                resolved_sponsor_uid = data.get("uid", reg_sponsor)
                                break
                
                full_mobile = f"{reg_flag_code.split(' ')[1]}{reg_phone_raw}"
                st._central_user_creds[reg_username] = {
                    "password": reg_password, "uid": new_uid, "email": reg_email,
                    "country": reg_country, "phone": full_mobile,
                    "school_answer": reg_school.lower(), "sponsor": resolved_sponsor_uid
                }
                st._uid_to_username[new_uid] = reg_username
                db_save("user_creds", st._central_user_creds)
                db_save("uid_to_user", st._uid_to_username)
                
                db_save(f"balance_{new_uid}", 5000.0)
                db_save(f"real_balance_{new_uid}", 0.0)
                db_save(f"win_{new_uid}", 0)
                db_save(f"loss_{new_uid}", 0)
                
                if resolved_sponsor_uid != "None":
                    st._global_referral_tree = db_load("referral_tree", {})
                    if resolved_sponsor_uid not in st._global_referral_tree: st._global_referral_tree[resolved_sponsor_uid] = []
                    if new_uid not in st._global_referral_tree[resolved_sponsor_uid]:
                        st._global_referral_tree[resolved_sponsor_uid].append(new_uid)
                    db_save("referral_tree", st._global_referral_tree)
                st.success(f"Bound Identity Successful! UID Generated: {new_uid}")
        st.stop()
user_data = st._central_user_creds[st.session_state.logged_in_user]
allocated_user_id = user_data["uid"]
my_sponsor_id = user_data["sponsor"]
my_profile_email = user_data.get("email", "Not Set")

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#ffffff; font-size:13px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px; margin:4px 0;'>🆔 My UID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    
    bot_mode = st.radio("Trading Account Mode Settings:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = "Live" in bot_mode
    dashboard_mode_title = "Real Production Dashboard Mode 🟢" if is_real_live else "Demo Sandbox Dashboard Mode 🔵"
    
    # Isolated Memory Loading Layer based strictly on Mode Switch Criteria
    if is_real_live:
        if 'real_balance' not in st.session_state: st.session_state.real_balance = db_load(f"real_balance_{allocated_user_id}", 0.0)
    else:
        if 'demo_balance' not in st.session_state: st.session_state.demo_balance = db_load(f"balance_{allocated_user_id}", 5000.0)

    selected_display_name = st.selectbox("Select Asset Contract Symbol Dropdown:", list(BYBYT_DATABASE_CORE.keys()), index=0)
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    ai_decision = st.toggle("AI Smart Crossover Filter Matrix", value=True)
    
    max_leverage_bound = int(coin_config.get('max_leverage', 100))
    leverage = st.slider("Leverage Scale Selection Array (1x-100x Override):", min_value=1, max_value=max_leverage_bound, value=20, step=1, key="absolute_leverage_node_slider")
    trade_amount = st.number_input("Margin Requirement Block (\$):", min_value=1, value=20)
    price_jump_target = st.number_input("Take Profit Target Interval (\$):", value=coin_config["default_tp"], format="%.6f")
    stop_loss_gap = st.number_input("Stop Loss Boundary GAP Threshold (\$):", value=coin_config["default_sl"], format="%.6f")

with st.sidebar:
    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'><div style='background-color:#ff1744; padding:6px; border-radius:5px; text-align:center; margin-bottom:6px;'><b style='color:#ffffff; font-size:11px;'>🚨 LICENSE GATE ACTIVE</b></div>", unsafe_allow_html=True)
        input_license = st.text_input("License Password:", type="password", key="lic_field_sidebar", label_visibility="collapsed").strip()
        if input_license in st._central_key_registry:
            api_key = st.text_input("Bybit API Key Node Token:", type="password", key="api_field_sidebar")
            secret_key = st.text_input("Bybit Secret Key Node Token:", type="password", key="sec_field_sidebar")

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011
st.markdown("<div style='background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center;'><h1 style='margin: 0; color: #0b0e14; font-size: 26px; font-weight: bold;'>BYBIT AI PRO SCALPER</h1></div>", unsafe_allow_html=True)

live_price, current_rsi, ai_market_thesis, fig_candlestick = 0.0, 50.0, "SYNCING DATA FEED NODES... 📡", None
try:
    public_session = HTTP(testnet=False)
    ticker_res = public_session.get_tickers(category="linear", symbol=target_symbol)
    ticker_list = ticker_res.get('result', {}).get('list', [])
    if ticker_list: live_price = float(ticker_list[0].get('lastPrice', 0))
        
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
        
        ai_market_thesis = f"🔮 AI LIGHTNING MATRIX SCANNER ({target_symbol}) -> Whales shifting capital derivatives blocks."
        fig_candlestick = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'])])
        fig_candlestick.update_layout(template="plotly_dark", margin=dict(l=6, r=6, t=6, b=6), height=250, xaxis_rangeslider_visible=False, paper_bgcolor='#06090e', plot_bgcolor='#06090e')
except:
    if live_price == 0.0: live_price = 66500.0

if fig_candlestick: st.plotly_chart(fig_candlestick, use_container_width=True)

st.markdown(f"<div class='custom-box-grid' style='background-color:#050a12; border:1px solid #00e676;'><div class='matrix-neon-text'>🧬 <b>AI SCAN FEED:</b><br>{ai_market_thesis}</div></div>", unsafe_allow_html=True)

# High Frequency Interactive Floating P&L Dynamic Compute Block Loops
floating_pnl = 0.0
if st.session_state.in_position and live_price > 0:
    if "LONG" in st.session_state.current_side:
        floating_pnl = ((live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price))
    else:
        floating_pnl = ((st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price))

# Mode Isolated Balance rendering preventing mixing logs
if is_real_live:
    balance_usd_text = f"${(st.session_state.real_balance + floating_pnl):,.2f} USDT"
else:
    balance_usd_text = f"${(st.session_state.demo_balance + floating_pnl):,.2f} USDT"

pnl_color_hex = "#00e676" if floating_pnl >= 0 else "#ff1744"
st.markdown(f"<div class='custom-box-grid'>💰 <b>AVAILABLE BALANCE ({bot_mode}):</b> <h2 style='margin:0; color:#fff;'>{balance_usd_text}</h2><p style='margin:0; font-size:13px; color:{pnl_color_hex}; font-weight:bold;'>Live Floating P&L: {floating_pnl:+.2f} USDT</p></div>", unsafe_allow_html=True)
if not ai_decision and not st.session_state.in_position:
    st.markdown("<p style='color:#ffcc00; font-weight:bold;'>🕹️ Manual Trading Panel Active (AI Crossover Bypassed)</p>", unsafe_allow_html=True)
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        if st.button("🟢 EXECUTE BUY / LONG ENTRY", key="manual_buy_long_btn"):
            st.session_state.buy_price = live_price
            st.session_state.in_position = True; st.session_state.current_side = "LONG"; st.rerun()
    with m_col2:
        if st.button("🔴 EXECUTE SELL / SHORT ENTRY", key="manual_sell_short_btn"):
            st.session_state.buy_price = live_price
            st.session_state.in_position = True; st.session_state.current_side = "SHORT"; st.rerun()

c1, c2 = st.columns(2)
with c1:
    if not st.session_state.bot_active:
        if st.button("🟢 START ENGINE SCALPER LOOP SEQUENCE", key="start_engine_bot_btn"):
            st.session_state.bot_active = True
            if not ai_decision and not st.session_state.in_position:
                st.session_state.buy_price = live_price; st.session_state.in_position = True; st.session_state.current_side = "LONG"
            st.rerun()
    else:
        if st.button("🔴 STOP ENGINE SCALPER LOOP SEQUENCE", key="stop_engine_bot_btn"):
            st.session_state.bot_active = False; st.rerun()
with c2:
    if st.button("🚨 EMERGENCY LIQUIDATE CLOSE ORDER POSITION", disabled=not st.session_state.in_position, key="force_sell_engine_btn"):
        local_final_pnl = 0.0
        if live_price > 0:
            if "LONG" in st.session_state.current_side:
                local_final_pnl = ((live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price))
            else:
                local_final_pnl = ((st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price))
                
        net_pnl = local_final_pnl - estimated_fee
        mode_type = "REAL" if is_real_live else "DEMO"
        
        if is_real_live:
            st.session_state.real_balance += net_pnl
            db_save(f"real_balance_{allocated_user_id}", st.session_state.real_balance)
        else:
            st.session_state.demo_balance += net_pnl
            db_save(f"balance_{allocated_user_id}", st.session_state.demo_balance)
        
        st._global_user_pnl_history.append({
            "Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"),
            "User ID": allocated_user_id, "Coin": target_symbol,
            "Action": f"CLOSE {st.session_state.current_side}", "Net P&L ($)": f"{net_pnl:.2f}", "Type": mode_type
        })
        
        # FIXED: Core Multi Generation Commission distribution directly on Total Trade Profit Value
        if st._mlm_bonus_enabled and net_pnl > 0:
            current_parent = my_sponsor_id
            for gen in range(1, 8):
                if current_parent == "None" or current_parent == "" or current_parent is None: break
                share_rate = float(st._mlm_gen_rates.get(gen, 5.0)) / 100
                bonus_payout = net_pnl * share_rate  # Strict linear percentage calculation
                st._global_user_pnl_history.append({
                    "Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"),
                    "User ID": current_parent, "Coin": target_symbol,
                    "Action": f"GEN_COMMISSION_L{gen}", "Net P&L ($)": f"{bonus_payout:.4f}", "Type": mode_type
                })
                # Find parent sponsor chain UID nodes safely
                parent_data = [u for u in st._central_user_creds.values() if u.get("uid") == current_parent]
                current_parent = parent_data[0].get("sponsor", "None") if parent_data else "None"

        db_save("pnl_history", st._global_user_pnl_history)
        st.session_state.in_position = False; st.rerun()

# --- 🌿 DYNAMIC MARKETING NETWORK MODULE PANEL HUB ---
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown(f"<h3 style='color:#f5a623;'>🌿 Network Marketing Matrix Desk ({dashboard_mode_title})</h3>", unsafe_allow_html=True)
search_uid_input = st.text_input("Enter Target Member UID box input:", value=allocated_user_id, key="custom_uid_search_field_node").strip()

# Mode Isolated Box Accumulator Layer mapping Real and Demo entries separately
mode_filter_string = "REAL" if is_real_live else "DEMO"
ref_accum, gen_accum = 0.0, 0.0
if st._global_user_pnl_history:
    for r in st._global_user_pnl_history:
        try:
            if str(r.get("User ID")).strip() == str(search_uid_input).strip() and r.get("Type") == mode_filter_string:
                action_str = r.get("Action", "")
                pnl_val = float(r.get("Net P&L ($)", 0))
                if "GEN_COMMISSION" in action_str: gen_accum += pnl_val
                elif "REF_COMMISSION" in action_str: ref_accum += pnl_val
        except: pass

cbx1, cbx2 = st.columns(2)
with cbx1: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #00e676; text-align:center;'><span>🔗 REFERRAL TOTAL NET BOX ({mode_filter_string})</span><h4 style='color:#00e676;'>${ref_accum:.2f} USDT</h4></div>", unsafe_allow_html=True)
with cbx2: st.markdown(f"<div class='custom-box-grid' style='border-top:4px solid #29b6f6; text-align:center;'><span>🌐 7-GEN DAILY ROI COMMISSION</span><h4 style='color:#29b6f6;'>${gen_accum:.2f} USDT</h4></div>", unsafe_allow_html=True)
def calculate_sub_generations(r_uid, tree):
    g_map = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
    actual_search_uid = r_uid
    for uname, data in st._central_user_creds.items():
        if uname == r_uid or data.get("uid") == r_uid:
            actual_search_uid = data.get("uid"); break
    if actual_search_uid in tree: g_map[1] = list(tree[actual_search_uid])
    for g in range(2, 8):
        p_layer = g_map[g-1]
        c_accum = []
        for p_uid in p_layer:
            if p_uid in tree:
                for c_uid in tree[p_uid]:
                    if c_uid not in c_accum and c_uid not in g_map[g-1]: c_accum.append(c_uid)
        g_map[g] = c_accum
    return g_map

st.markdown("<br><b style='color:#f5a623;'>📊 Sub-Downline Network Members Status Grid Management Node:</b>", unsafe_allow_html=True)
mapped_gens = calculate_sub_generations(search_uid_input, st._global_referral_tree)
sub_tree_records = []
for g_idx in range(1, 8):
    if g_idx in mapped_gens:
        for sub_uid in mapped_gens[g_idx]:
            demo_pnl, real_pnl = 0.0, 0.0
            if st._global_user_pnl_history:
                for r in st._global_user_pnl_history:
                    if r.get("User ID") == sub_uid:
                        val = float(r.get("Net P&L ($)", 0))
                        if r.get("Type") == "REAL": real_pnl += val
                        else: demo_pnl += val
            
            sub_tree_records.append({
                "Hierarchy Level": f"Gen Layer {g_idx}", "User ID": sub_uid,
                "Username": st._uid_to_username.get(sub_uid, f"Node-{sub_uid[:4]}"), 
                "Demo Lifetime Profit": f"${demo_pnl:.2f} USDT", "Real Lifetime Profit": f"${real_pnl:.2f} USDT"
            })

if sub_tree_records: st.dataframe(pd.DataFrame(sub_tree_records), use_container_width=True)
else: st.info("No active downline nodes found.")

# High speed javascript clock running macro updates dynamically every 1 second
st.markdown("""<iframe src="about:blank" style="display:none;" onload="setTimeout(function(){window.location.reload();}, 1000);"></iframe>""", unsafe_allow_html=True)

with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        
        # RESTORED: Advanced Admin Audit Layer showing global referral tree structures mapping
        st.markdown("<h3>🌿 Global User Registry Network Map:</h3>", unsafe_allow_html=True)
        st.json(st._global_referral_tree)
        
        # RESTORED: UID-Based Active Positions & Trade History Monitoring Matrix Table
        st.markdown("<h3>📊 Global Live Trade Ledger (All Users Tracking):</h3>", unsafe_allow_html=True)
        if st._global_user_pnl_history:
            st.dataframe(pd.DataFrame(st._global_user_pnl_history).iloc[::-1], use_container_width=True)
        else: st.info("Global Ledger is currently empty.")
        
        st.markdown("<h2>⚙️ Referral Marketing Matrix Controls (7-Gen ROI Mode):</h2>", unsafe_allow_html=True)
        old_val = st._mlm_bonus_enabled
        st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled, key="adm_mlm_active_toggle")
        if old_val != st._mlm_bonus_enabled: db_save("mlm_enabled", st._mlm_bonus_enabled)
        
        c_cols = st.columns(2)
        for g in range(1, 8):
            with c_cols[(g-1)%2]:
                st._mlm_gen_rates[g] = st.number_input(f"Gen {g} Share (%):", min_value=0.0, max_value=100.0, value=st._mlm_gen_rates.get(g, 5.0), key=f"adm_rates_generation_input_g_{g}")
                st._mlm_id_thresholds[g] = st.number_input(f"Gen {g} Cap:", min_value=1, value=st._mlm_id_thresholds.get(g, 10), key=f"adm_thresholds_generation_input_g_{g}")
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
                st._central_user_creds[found_account]["password"] = override_new_pass; db_save("user_creds", st._central_user_creds); st.success(f"Success Account Modified!"); st.rerun()
        
        target_block_key = st.text_input("Paste Target License Token to BAN permanently:", key="adm_ban_token_input_field")
        if st.button("Execute Permanent Revocation Ban", key="adm_ban_token_trigger_btn"):
            if target_block_key in st._central_key_registry:
                st._central_blacklist.append(target_block_key); del st._central_key_registry[target_block_key]
                db_save("blacklist", st._central_blacklist); db_save("key_registry", st._central_key_registry); st.warning(f"Token blocked permanent."); st.rerun()
                
        if st._license_csv_database: st.dataframe(pd.DataFrame(st._license_csv_database).iloc[::-1], use_container_width=True, height=120)
        all_creds_df = pd.DataFrame.from_dict(st._central_user_creds, orient='index')
        if not all_creds_df.empty: st.dataframe(all_creds_df, use_container_width=True)
