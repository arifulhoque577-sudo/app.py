import streamlit as st
import pandas as pd
import time
import random
import string
import requests
import plotly.graph_objects as go
from pybit.unified_trading import HTTP
BYBIT_USDT_DATABASE = {
    "🪙 BTCUSDT (Bitcoin)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0},
    "🔷 ETHUSDT (Ethereum)": {"symbol": "ETHUSDT", "max_leverage": 100, "default_tp": 8.0, "default_sl": 15.0, "step": 1.0},
    "☀️ SOLUSDT (Solana)": {"symbol": "SOLUSDT", "max_leverage": 50, "default_tp": 1.5, "default_sl": 3.0, "step": 0.1},
    "💥 XRPUSDT (Ripple)": {"symbol": "XRPUSDT", "max_leverage": 100, "default_tp": 0.015, "default_sl": 0.03, "step": 0.001},
    "🐶 DOGEUSDT (Dogecoin)": {"symbol": "DOGEUSDT", "max_leverage": 50, "default_tp": 0.004, "default_sl": 0.01, "step": 0.0005},
    "🔮 LINKUSDT (Chainlink)": {"symbol": "LINKUSDT", "max_leverage": 50, "default_tp": 0.25, "default_sl": 0.50, "step": 0.01},
    "🧬 ADAUSDT (Cardano)": {"symbol": "ADAUSDT", "max_leverage": 50, "default_tp": 0.01, "default_sl": 0.02, "step": 0.001},
    "💎 PEPEUSDT (Pepe)": {"symbol": "PEPEUSDT", "max_leverage": 20, "default_tp": 0.0000001, "default_sl": 0.0000003, "step": 0.00000001},
    "🌀 WIFUSDT (dogwifhat)": {"symbol": "WIFUSDT", "max_leverage": 20, "default_tp": 0.05, "default_sl": 0.12, "step": 0.01},
    "🔥 SHIBUSDT (Shiba Inu)": {"symbol": "SHIBUSDT", "max_leverage": 50, "default_tp": 0.0000005, "default_sl": 0.000001, "step": 0.0000001},
    "🪐 DOTUSDT (Polkadot)": {"symbol": "DOTUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.12, "step": 0.01},
    "🔺 AVAXUSDT (Avalanche)": {"symbol": "AVAXUSDT", "max_leverage": 50, "default_tp": 0.20, "default_sl": 0.50, "step": 0.01},
    "🦄 UNIUSDT (Uniswap)": {"symbol": "UNIUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.15, "step": 0.01},
    "⚡ LTCUSDT (Litecoin)": {"symbol": "LTCUSDT", "max_leverage": 60, "default_tp": 0.50, "default_sl": 1.20, "step": 0.1},
    "🔗 ATOMUSDT (Cosmos)": {"symbol": "ATOMUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.15, "step": 0.01},
    "🌿 XLMUSDT (Stellar)": {"symbol": "XLMUSDT", "max_leverage": 50, "default_tp": 0.002, "default_sl": 0.005, "step": 0.0001},
    "🦅 FILUSDT (Filecoin)": {"symbol": "FILUSDT", "max_leverage": 50, "default_tp": 0.04, "default_sl": 0.10, "step": 0.01},
    "👻 AAVEUSDT (Aave)": {"symbol": "AAVEUSDT", "max_leverage": 50, "default_tp": 1.0, "default_sl": 2.50, "step": 0.1},
    "📦 NEARUSDT (Near)": {"symbol": "NEARUSDT", "max_leverage": 50, "default_tp": 0.04, "default_sl": 0.10, "step": 0.01},
    "🎮 IMXUSDT (Immutable)": {"symbol": "IMXUSDT", "max_leverage": 20, "default_tp": 0.02, "default_sl": 0.05, "step": 0.001},
    "🥞 CAKEUSDT (Pancake)": {"symbol": "CAKEUSDT", "max_leverage": 20, "default_tp": 0.02, "default_sl": 0.05, "step": 0.001},
    "🚀 SUIUSDT (Sui Token)": {"symbol": "SUIUSDT", "max_leverage": 50, "default_tp": 0.02, "default_sl": 0.06, "step": 0.001},
    "🌊 APTUSDT (Aptos)": {"symbol": "APTUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.15, "step": 0.01},
    "🪙 OPUSDT (Optimism)": {"symbol": "OPUSDT", "max_leverage": 50, "default_tp": 0.02, "default_sl": 0.05, "step": 0.001},
    "🧱 ARBUSDT (Arbitrum)": {"symbol": "ARBUSDT", "max_leverage": 50, "default_tp": 0.01, "default_sl": 0.03, "step": 0.001}
}
YOUR_SECRET_MASTER_CODE = "ADMIN1234"
st.set_page_config(page_title="Bybit AI Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0b0e14; }
    div[data-testid="stSidebar"] { background-color: #0c1017 !important; border-right: 1px solid #1e293b; }
    div.stButton > button:first-child { width: 100%; border-radius: 8px; font-weight: bold; font-size: 16px; height: 46px; }
    iframe { border: none !important; }
    </style>
    """, unsafe_allow_html=True)
st.markdown("""
    <div style="background: linear-gradient(90deg, #f5a623 0%, #ffcc00 100%); padding: 15px; border-radius: 12px; margin-bottom: 20px; text-align: center; box-shadow: 0px 4px 15px rgba(245, 166, 35, 0.2);">
        <h1 style="margin: 0; color: #0b0e14; font-family: 'Arial Black', sans-serif; font-size: 28px; letter-spacing: 1px;">BYBIT AI PRO SCALPER</h1>
        <p style="margin: 5px 0 0 0; color: #1c2434; font-weight: bold; font-size: 13px;">FRONTLINE VERSION 15.0 • HIGH-LEVERAGE PERPETUAL ENGINE</p>
    </div>
    """, unsafe_allow_html=True)
if not hasattr(st, "_central_user_creds"): st._central_user_creds = {}
if not hasattr(st, "_central_key_registry"): st._central_key_registry = {}
if not hasattr(st, "_central_blacklist"): st._central_blacklist = []
if not hasattr(st, "_license_csv_database"): st._license_csv_database = []
if not hasattr(st, "_global_referral_tree"): st._global_referral_tree = {} 
if not hasattr(st, "_global_user_pnl_history"): st._global_user_pnl_history = [] 
if not hasattr(st, "_uid_to_username"): st._uid_to_username = {} 
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []
if 'win_count' not in st.session_state: st.session_state.win_count = 0
if 'loss_count' not in st.session_state: st.session_state.loss_count = 0
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None

if 'my_hardware_signature' not in st.session_state:
    st.session_state.my_hardware_signature = "DEV-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
my_signature = st.session_state.my_hardware_signature
if st.session_state.logged_in_user is None:
    st.markdown("""
        <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:#07090e; z-index:-1; overflow:hidden;">
            <div style="position:absolute; width:200px; height:200px; background:rgba(245,166,35,0.06); filter:blur(80px); top:15%; left:10%; animation: float 8s ease-in-out infinite;"></div>
            <div style="position:absolute; width:250px; height:200px; background:rgba(56,189,248,0.05); filter:blur(90px); bottom:20%; right:15%;"></div>
        </div>
        <style> @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-20px); } } </style>
        """, unsafe_allow_html=True)
    
    st.subheader("🔑 Cryptographic Membership Authentication Desk")
    auth_mode = st.radio("Choose Operations Layer:", ["Secure Login Profile", "Mint New Membership Account ID"])
    if auth_mode == "Mint New Membership Account ID":
        reg_username = st.text_input("Choose Username:", key="reg_u").strip()
        reg_password = st.text_input("Set Password Phrase:", type="password", key="reg_p").strip()
        reg_sponsor = st.text_input("Enter Sponsor Referral ID Token:", key="reg_s").strip()
        
        if st.button("🚀 Register My Cryptographic Handle"):
            if reg_username == "" or reg_password == "": st.error("Fields cannot be left blank!")
            elif reg_username in st._central_user_creds: st.error("Handle already active in nodes!")
            else:
                new_uid = "UID-" + "".join(random.choices(string.digits, k=6))
                st._central_user_creds[reg_username] = {"password": reg_password, "uid": new_uid, "sponsor": reg_sponsor if reg_sponsor != "" else "None"}
                st._uid_to_username[new_uid] = reg_username
                if reg_sponsor != "":
                    if reg_sponsor not in st._global_referral_tree: st._global_referral_tree[reg_sponsor] = []
                    if new_uid not in st._global_referral_tree[reg_sponsor]: st._global_referral_tree[reg_sponsor].append(new_uid)
                st.success(f"Account Bound! Your Permanent Access UID: {new_uid}")
        st.stop()
    elif auth_mode == "Secure Login Profile":
        login_u = st.text_input("Identity Handle (Username):", key="log_u").strip()
        login_p = st.text_input("Hardened Password Phrase:", type="password", key="log_p").strip()
        if st.button("🔓 Authenticate Node Sign In"):
            if login_u in st._central_user_creds and st._central_user_creds[login_u]["password"] == login_p:
                st.session_state.logged_in_user = login_u
                st.success("Authorization verified successfully!")
                st.rerun()
            else: st.error("Authentication credentials mismatch!")
        st.stop()
user_data = st._central_user_creds[st.session_state.logged_in_user]
allocated_user_id = user_data["uid"]
my_sponsor_id = user_data["sponsor"]

with st.sidebar:
    st.markdown("<h2 style='color:#f5a623;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#e2a826; font-size:12px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:12px; margin:0;'>🆔 Your UID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#94a3b8; font-size:12px; margin:0;'>🔗 Sponsor UID: <b>{my_sponsor_id}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Disconnect Node Session"): st.session_state.logged_in_user = None; st.rerun()
        
    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = True if "Live" in bot_mode else False
    selected_display_name = st.selectbox("Select Perpetual Contract:", list(BYBIT_USDT_DATABASE.keys()), index=0)
    coin_config = BYBIT_USDT_DATABASE[selected_display_name]
    target_symbol = coin_config["symbol"]
    
    ai_decision = st.toggle("AI Smart Crossover Filter (RSI Mean Reversion)", value=True)
    leverage = st.slider(f"Execution Leverage (Max {coin_config['max_leverage']}x):", min_value=1, max_value=coin_config["max_leverage"], value=20, step=1)
    trade_amount = st.number_input("Margin Requirement ($):", min_value=1, max_value=1000, value=20, step=1)
    price_jump_target = st.number_input("Take Profit Target ($ Price Delta):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_tp"], step=coin_config["step"], format="%.8f")
    stop_loss_gap = st.number_input("Stop Loss Threshold ($ Price Delta):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_sl"], step=coin_config["step"], format="%.8f")
    
    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
        st.markdown("<p style='color:#ff3333; font-weight:bold; font-size:11px;'>🔒 HARDWARE LAYERS PROTECTION ACTIVE</p>", unsafe_allow_html=True)
        input_license = st.text_input("Enter License Key:", type="password").strip()
        if input_license != "":
            if input_license in st._central_blacklist: st.error("❌ Access Revoked: Key BLOCKED!")
            elif input_license in st._central_key_registry:
                locked_device_signature = st._central_key_registry[input_license]
                if locked_device_signature == "FREE_SLOT":
                    st._central_key_registry[input_license] = my_signature
                    st.success("🔓 First-Touch Activation Success!")
                    api_key = st.text_input("Bybit API Key:", type="password")
                    secret_key = st.text_input("Bybit Secret Key:", type="password")
                elif locked_device_signature == my_signature:
                    st.success("🔓 Authorization Verified!")
                    api_key = st.text_input("Bybit API Key:", type="password")
                    secret_key = st.text_input("Bybit Secret Key:", type="password")
                else:
                    st._central_blacklist.append(input_license)
                    if input_license in st._central_key_registry: del st._central_key_registry[input_license]
                    st.error("❌ Second Device Detected!")
            else: st.error("❌ Invalid Key!")
if 'active_coin' not in st.session_state or st.session_state.active_coin != target_symbol:
    st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.session_state.active_coin = target_symbol
effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Module Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Authorization successful. Key Pool Registry unlocked.")
        if st.button("Mint New Randomized License Token Key"):
            random_token = "SCLP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            st._central_key_registry[random_token] = "FREE_SLOT"
            st._license_csv_database.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "License Key": random_token, "Status": "Active (Unused)"})
            st.code(f"{random_token}", language="text"); st.rerun()
            
        target_block_key = st.text_input("Paste Target License Token to BAN permanently:")
        if st.button("Execute Permanent Revocation Ban"):
            found = False
            if target_block_key in st._central_key_registry or target_block_key in st._central_blacklist:
                if target_block_key not in st._central_blacklist: st._central_blacklist.append(target_block_key)
                if target_block_key in st._central_key_registry: del st._central_key_registry[target_block_key]
                found = True
            for row in st._license_csv_database:
                if row["License Key"] == target_block_key: row["Status"] = "Permanently Banned ❌"; found = True
            if found: st.warning(f"TOKEN REVOKED: {target_block_key} banned."); st.rerun()
            else: st.error("Token matching failed!")
            
        st.markdown("<br><b style='color:#f5a623;'>🌿 Global Master Network Hierarchy Tree View:</b>", unsafe_allow_html=True)
        all_creds_df = pd.DataFrame.from_dict(st._central_user_creds, orient='index')
        if not all_creds_df.empty: st.dataframe(all_creds_df[["uid", "sponsor"]], use_container_width=True)
        if st._global_referral_tree:
            for parent, children in st._global_referral_tree.items():
                p_user = st._uid_to_username.get(parent, parent)
                st.markdown(f"👤 **Sponsor:** `{p_user}` (`{parent}`)")
                for child in children:
                    c_user = st._uid_to_username.get(child, child)
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└── 📱 **Downline Node:** `{c_user}` (`{child}`)")
        
        st.markdown("<br><b style='color:#38bdf8;'>📈 Global System Downline Performance Auditing Node Ledger:</b>", unsafe_allow_html=True)
        if st._global_user_pnl_history:
            global_pnl_df = pd.DataFrame(st._global_user_pnl_history)
            target_audit_uid = st.selectbox("Select Target Registered Node UID:", global_pnl_df["User ID"].unique(), key="admin_audit_select")
            filtered_admin_df = global_pnl_df[global_pnl_df["User ID"] == target_audit_uid]
            st.dataframe(filtered_admin_df.iloc[::-1], use_container_width=True)
        else: st.info("No network node pipelines trading ledger synchronized yet.")
        if st._license_csv_database: st.dataframe(pd.DataFrame(st._license_csv_database).iloc[::-1], height=100, use_container_width=True)
    elif master_input != "": st.error("Administrative override credential authorization mismatch.")
st.markdown("<h3 style='color:#f5a623; font-size:16px;'>🌿 My Referral Network Hub</h3>", unsafe_allow_html=True)
my_children = st._global_referral_tree.get(allocated_user_id, [])

if my_children:
    st.markdown(f"🎯 Total Direct Network Referrals: <b>{len(my_children)} Active Users</b>", unsafe_allow_html=True)
    child_display_map = {cid: f"{st._uid_to_username.get(cid, 'Unknown')} ({cid})" for cid in my_children}
    selected_child_cid = st.selectbox("Select Downline Node Handle to audit performance data logs:", list(child_display_map.keys()), format_func=lambda x: child_display_map[x])
    
    t1, t2 = st.tabs(["实时 Real Production Earnings Gate 🟢", "模拟 Demo Sandbox Earnings Gate 🔵"])
    with t1:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            child_real_df = pnl_df[(pnl_df["User ID"] == selected_child_cid) & (pnl_df["Type"] == "REAL")]
            if not child_real_df.empty:
                child_real_df["Net P&L ($)"] = pd.to_numeric(child_real_df["Net P&L ($)"])
                st.markdown(f"💰 Real Capital Earnings: <b style='color:#00e676;'>${child_real_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True)
                st.dataframe(child_real_df.iloc[::-1], use_container_width=True)
            else: st.info("No live production real funds data records synced yet.")
        else: st.info("Ledger registry timeline is empty.")
    with t2:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            child_demo_df = pnl_df[(pnl_df["User ID"] == selected_child_cid) & (pnl_df["Type"] == "DEMO")]
            if not child_demo_df.empty:
                child_demo_df["Net P&L ($)"] = pd.to_numeric(child_demo_df["Net P&L ($)"])
                st.markdown(f"💰 Demo Virtual Sandbox Earnings: <b style='color:#29b6f6;'>${child_demo_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True)
                st.dataframe(child_demo_df.iloc[::-1], use_container_width=True)
            else: st.info("No sandbox simulation records synced yet.")
        else: st.info("Ledger registry timeline is empty.")
else: st.info("You haven't referred anyone yet. Share your Referral ID Token to grow your matrix network tree!")
st.markdown("<hr style='border:1px solid #1f2c3f;'>", unsafe_allow_html=True)
st.markdown(f"""
    <div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between;">
        <span style="color:#ffffff; font-size:14px; font-weight:bold;">🏆 PERFORMANCES WON: <b style="color:#00e676;">{st.session_state.win_count}</b></span>
        <span style="color:#ffffff; font-size:14px; font-weight:bold;">❌ EXITS LOST: <b style="color:#ff1744;">{st.session_state.loss_count}</b></span>
        <span style="color:#ffffff; font-size:14px; font-weight:bold;">🎯 NET WIN RATE: <b style="color:#29b6f6;">{win_rate:.1f}%</b></span>
    </div>
""", unsafe_allow_html=True)

live_price, current_rsi, df_kline = 0.0, 50.0, None
if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol=target_symbol, interval="5", limit=15)
        klines = response.get('result', {}).get('list', [])
        if klines:
            df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df_kline = df_kline.iloc[::-1].reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close']: df_kline[col] = pd.to_numeric(df_kline[col])
            live_price = df_kline['close'].iloc[-1]
            delta = df_kline['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
            rs = gain / (loss + 1e-10)
            df_kline['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df_kline['RSI'].iloc[-1] if not df_kline['RSI'].isnull().iloc[-1] else 50.0
    except: pass

floating_pnl, expected_net_profit = 0.0, 0.0
if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    if is_long_pos: floating_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
    else: floating_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)
    expected_net_profit = (price_jump_target * (effective_vol / st.session_state.buy_price)) - estimated_fee
display_balance = st.session_state.demo_balance + floating_pnl if not is_real_live else 0.0
balance_usd_text = f"${display_balance:,.2f}"

if is_real_live and api_key and secret_key:
    try:
        session = HTTP(testnet=False, api_key=api_key, secret_key=secret_key)
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list:
            for c in member_list.get('coin', []):
                if c.get('coin') == 'USDT': balance_usd_text = f"${(float(c.get('walletBalance', 0)) + floating_pnl):,.2f}"; break
    except: balance_usd_text = "API Key Error"

position_status = "NO ACTIVE POSITION 💤" if not st.session_state.in_position else f"FUTURE {target_symbol} {st.session_state.current_side} CONTRACT RUNNING"
rsi_color = "#ff1744" if current_rsi > 50 else "#00e676"

# 📦 RESTORED BOX 1: MARGIN STATUS EXECUTION COMPONENT BLOCK 
st.markdown(f"""
    <div style="background-color:#141a24; padding:10px; border-radius:10px; margin-bottom:12px; border-left: 5px solid {rsi_color}; text-align:center; border: 1px solid #1f2c3f;">
        <span style="color:#94a3b8; font-size:12px; font-weight:bold;">📡 LIVE AI RSI OSCILLATOR (5s FEED):</span>
        <h3 style="margin:2px 0; color:#ffffff; font-size:24px; font-family: monospace;">{current_rsi:.2f}</h3>
    </div>
    <div style="background-color:#141a24; padding:15px; border-radius:12px; margin-bottom:12px; border: 1px solid #1f2c3f;">
        <p style="margin:0; font-size:12px; color:#94a3b8; font-weight:bold;">💰 AVAILABLE BALANCE ACCOUNT ({bot_mode})</p>
        <h2 style="margin:5px 0; color:#ffffff; font-size:28px; font-family: monospace;">{balance_usd_text}</h2>
        <p style="margin:0; font-size:14px; color:{'#00e676' if floating_pnl >= 0 else '#ff1744'}; font-weight:bold;">Live Floating P&L: {floating_pnl:+.2f} USDT</p>
    </div>
    <div style="background-color:#141a24; padding:15px; border-radius:12px; margin-bottom:15px; border: 1px solid #1f2c3f;">
        <p style="margin:0; font-size:12px; color:#94a3b8; font-weight:bold;">📦 MARGIN STATUS EXECUTION</p>
        <h3 style="margin:5px 0; color:#ffffff; font-size:16px; font-weight:bold;">{position_status}</h3>
    </div>
""", unsafe_allow_html=True)
if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    # 💎 RESTORED BOX 2: SKY BLUE NEON-BORDER TARGETS PANEL
    st.markdown(f"""
    <div style="background-color:#0b0e14; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; border-left: 5px solid #29b6f6;">
        <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Entry Price: {st.session_state.buy_price} | Live Index: {live_price}</span><br>
        <span style="font-size:14px; color:#00e676; font-weight:bold; font-family: monospace;">Take Profit Target: {live_target} (Expected Net: +${expected_net_profit:.2f})</span><br>
        <span style="font-size:14px; color:#ff1744; font-weight:bold; font-family: monospace;">Stop Loss Boundary: {live_sl}</span>
    </div>
    """, unsafe_allow_html=True)

st.info(f"💡 Estimated Execution Trading Fee: **${estimated_fee:.3f} USDT**")
st.markdown("<h3 style='color:#ffffff; font-size:16px;'>🎮 Engine Controls</h3>", unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        st.markdown("<style>div.stButton > button[key='stop_btn'] {background-color:#d50000 !important; color:white;}</style>", unsafe_allow_html=True)
        if st.button("🔴 STOP ENGINE", key="stop_btn"): st.session_state.bot_active = False; st.rerun()
    else:
        st.markdown("<style>div.stButton > button[key='start_btn'] {background-color:#00c853 !important; color:white;}</style>", unsafe_allow_html=True)
        if st.button("🟢 START SCALPER", key="start_btn"): st.session_state.bot_active = True; st.rerun()
with c2:
    if st.session_state.in_position:
        st.markdown("<style>div.stButton > button[key='force_sell_btn'] {background-color:#ff3d00 !important; color:white;}</style>", unsafe_allow_html=True)
        if st.button("🚨 EMERGENCY LIQUIDATE", key="force_sell_btn"):
            net_pnl = floating_pnl - estimated_fee
            if not is_real_live: st.session_state.demo_balance += net_pnl
            status_tag = "MANUAL CLOSE 🛑"
            st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": allocated_user_id, "Coin": target_symbol, "Action": f"CLOSE {st.session_state.current_side}", "Net P&L ($)": f"{net_pnl:.2f}", "Type": "REAL" if is_real_live else "DEMO"})
            if net_pnl >= 0: st.session_state.win_count += 1
            else: st.session_state.loss_count += 1
            for idx, trade in enumerate(st.session_state.all_trades_history):
                if trade["Status"] == "RUNNING" and trade["Coin"] == target_symbol:
                    st.session_state.all_trades_history[idx]["Status"] = status_tag
                    st.session_state.all_trades_history[idx]["Net P&L ($)"] = f"{net_pnl:.2f}"
            st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.rerun()

if st.session_state.bot_active and df_kline is not None:
    try:
        fig = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'], increasing_line_color='#00e676', decreasing_line_color='#ff1744')])
        fig.update_layout(margin=dict(l=5, r=5, t=5, b=5), xaxis_rangeslider_visible=False, template="plotly_dark", height=150, paper_bgcolor='#0b0e14', plot_bgcolor='#0b0e14')
        st.plotly_chart(fig, use_container_width=True)
        raw_qty = effective_vol / live_price
        if live_price < 1.0: calculated_qty = round(raw_qty, 1)
        elif live_price < 500.0: calculated_qty = round(raw_qty, 2)
        else: calculated_qty = round(raw_qty, 4)
        if calculated_qty <= 0: calculated_qty = 0.1

        if not st.session_state.in_position:
            decision_side = "NONE"
            if ai_decision:
                if current_rsi < 45.0: decision_side = "BUY"
                elif current_rsi > 55.0: decision_side = "SELL"
            else: decision_side = "BUY"
            if decision_side != "NONE":
                st.session_state.buy_price = live_price; st.session_state.in_position = True
                st.session_state.current_side = "LONG" if decision_side == "BUY" else "SHORT"
                if is_real_live:
                    try:
                        session = HTTP(testnet=False, api_key=api_key, secret_key=secret_key)
                        session.place_order(category="linear", symbol=target_symbol, side=decision_side, orderType="Market", qty=str(calculated_qty))
                    except: st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"
                if st.session_state.in_position:
                    target_calc = (live_price + price_jump_target) if decision_side == "BUY" else (live_price - price_jump_target)
                    st.session_state.all_trades_history.append({"Time": time.strftime("%H:%M:%S"), "Coin": target_symbol, "Action": f"OPEN {st.session_state.current_side}", "Price": live_price, "Target": f"${target_calc}", "Trading Fee ($)": f"-{estimated_fee/2:.3f}", "Net P&L ($)": "0.00", "Status": "RUNNING"})
            st.rerun()
        elif st.session_state.in_position:
            is_long_pos = True if st.session_state.current_side == "LONG" else False
            if is_long_pos:
                is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                is_stop_hit = live_price <= (st.session_state.buy_price - stop_loss_gap)
            else:
                is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                is_stop_hit = live_price >= (st.session_state.buy_price + stop_loss_gap)
            if is_profit_hit or is_stop_hit:
                close_action = "Sell" if is_long_pos else "Buy"; status_tag = "PROFIT 🟢" if is_profit_hit else "STOPLOSS 🔴"; net_pnl = floating_pnl - estimated_fee
                st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": allocated_user_id, "Coin": target_symbol, "Action": f"CLOSE {st.session_state.current_side}", "Net P&L ($)": f"{net_pnl:.2f}", "Type": "REAL" if is_real_live else "DEMO"})
                if is_profit_hit: st.session_state.win_count += 1
                else: st.session_state.loss_count += 1
                if is_real_live:
                    try:
                        session = HTTP(testnet=False, api_key=api_key, secret_key=secret_key)
                        session.place_order(category="linear", symbol=target_symbol, side=close_action, orderType="Market", qty=str(calculated_qty))
                    except: pass
                else: st.session_state.demo_balance += net_pnl
                target_display = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
                for idx, trade in enumerate(st.session_state.all_trades_history):
                    if trade["Status"] == "RUNNING" and trade["Coin"] == target_symbol:
                        st.session_state.all_trades_history[idx]["Status"] = status_tag
                        st.session_state.all_trades_history[idx]["Net P&L ($)"] = f"{net_pnl:.2f}"
                st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.rerun()
        st.subheader("📋 Permanent Trading Action History")
        if st.session_state.all_trades_history:
            history_df = pd.DataFrame(st.session_state.all_trades_history)
            st.dataframe(history_df.iloc[::-1], height=180, use_container_width=True)
        time.sleep(1)
        st.rerun()
    except:
        time.sleep(1)
        st.rerun()
else:
    st.info("The trading core engine is currently inactive. Press the green button to boot the scalper loops.")
    if st.session_state.all_trades_history:
        st.subheader("📋 Past Session Trading History")
        st.dataframe(pd.DataFrame(st.session_state.all_trades_history).iloc[::-1], use_container_width=True)
