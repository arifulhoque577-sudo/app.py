import streamlit as st
import pandas as pd
import time
import random
import string
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# Official Bybit Linear Perpetual Multi-Asset Database Specifications
BYBYT_DATABASE_CORE = {
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
# হাই-ব্রাইটনেস অ্যাডমিন টেক্সট সিএসএস এবং ব্লিংক-ফ্রি লিকুইড অ্যানিমেশন গেটওয়ে উইজেট
st.markdown("""
    <style>
    .main { background: #07090e !important; }
    div[data-testid="stSidebar"] { background-color: #0c1017 !important; border-right: 1px solid #1e293b; }
    div.stButton > button:first-child { width: 100%; border-radius: 8px; font-weight: bold; font-size: 16px; height: 46px; }
    iframe { border: none !important; }
    .stExpander { background-color: #0c1017 !important; border: 1px solid #1e293b !important; border-radius: 8px !important; }
    /* Admin Inputs Brightness Max Boost CSS Control Section */
    div[data-testid="stExpander"] p, div[data-testid="stExpander"] label { color: #ffffff !important; font-weight: bold !important; font-size: 13px !important; }
    div[data-testid="stExpander"] h2, div[data-testid="stExpander"] b { color: #38bdf8 !important; font-weight: bold !important; }
    </style>
    <div style="position:fixed; top:0; left:0; width:100vw; height:100vh; background:#07090e; z-index:-1; overflow:hidden;">
        <div style="position:absolute; width:100%; height:100%; background: linear-gradient(180deg, rgba(7,9,14,1) 0%, rgba(20,26,36,1) 100%);"></div>
        <div style="position:absolute; width:600px; height:600px; background:radial-gradient(circle, rgba(245,166,35,0.04) 0%, rgba(0,0,0,0) 70%); top:-10%; left:-10%;"></div>
    </div>
    """, unsafe_allow_html=True)

# Central Global Shared Server Infrastructure Data Registries Pool Storage Spaces
if not hasattr(st, "_central_user_creds"): st._central_user_creds = {}
if not hasattr(st, "_central_key_registry"): st._central_key_registry = {}
if not hasattr(st, "_central_blacklist"): st._central_blacklist = []
if not hasattr(st, "_license_csv_database"): st._license_csv_database = []
if not hasattr(st, "_global_referral_tree"): st._global_referral_tree = {} 
if not hasattr(st, "_global_user_pnl_history"): st._global_user_pnl_history = [] 
if not hasattr(st, "_uid_to_username"): st._uid_to_username = {} 

# MLM Dynamic 7-Generation Configurations Management Engine Channels Property Slots
if not hasattr(st, "_mlm_bonus_enabled"): st._mlm_bonus_enabled = True
if not hasattr(st, "_mlm_bonus_type"): st._mlm_bonus_type = "Percentage %"
if not hasattr(st, "_mlm_fixed_usd_pool"): st._mlm_fixed_usd_pool = 10.0
if not hasattr(st, "_mlm_gen_rates"): st._mlm_gen_rates = {1:10.0, 2:5.0, 3:3.0, 4:2.0, 5:1.0, 6:0.5, 7:0.5}
if not hasattr(st, "_mlm_id_thresholds"): st._mlm_id_thresholds = {1:3, 2:9, 3:27, 4:81, 5:243, 6:729, 7:2187}
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
        <div style="background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center; box-shadow: 0px 6px 20px rgba(255, 153, 0, 0.3);">
            <h1 style="margin: 0; color: #0b0e14; font-family: sans-serif; font-size: 26px; font-weight: bold; letter-spacing: 1px;">BYBIT AI PRO SCALPER</h1>
        </div>
        """, unsafe_allow_html=True)
    st.subheader("🔑 Cryptographic Membership Authentication Desk")
    auth_mode = st.radio("Choose Operations Layer:", ["Secure Login Profile", "Mint New Membership Account ID"])
    
    if auth_mode == "Mint New Membership Account ID":
        reg_username = st.text_input("Choose Username:", key="reg_u_core").strip()
        reg_password = st.text_input("Set Password Phrase:", type="password", key="reg_p_core").strip()
        reg_sponsor = st.text_input("Enter Sponsor Referral ID Token (Optional):", key="reg_s_core").strip()
        if st.button("🚀 Register My Cryptographic Handle", key="reg_submit_btn"):
            if reg_username == "" or reg_password == "": st.error("Fields cannot be blank!")
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
        login_u = st.text_input("Identity Handle (Username):", key="log_u_core").strip()
        login_p = st.text_input("Hardened Password Phrase:", type="password", key="log_p_core").strip()
        if st.button("🔓 Authenticate Node Sign In", key="log_submit_btn"):
            if login_u in st._central_user_creds and st._central_user_creds[login_u]["password"] == login_p:
                st.session_state.logged_in_user = login_u
                st.success("Authorization verified successfully!")
                st.rerun()
            else: st.error("Authentication credentials mismatch!")
        st.stop()

user_data = st._central_user_creds[st.session_state.logged_in_user]
allocated_user_id = user_data["uid"]
my_sponsor_id = user_data["sponsor"]

# Icon logo banner restored back into home view layout
st.markdown("""
    <div style="background: linear-gradient(135deg, #ff9900 0%, #ffcc00 100%); padding: 18px; border-radius: 12px; margin-bottom: 25px; text-align: center; box-shadow: 0px 6px 20px rgba(255, 153, 0, 0.3);">
        <h1 style="margin: 0; color: #0b0e14; font-family: sans-serif; font-size: 26px; font-weight: bold; letter-spacing: 1px;">BYBIT AI PRO SCALPER</h1>
    </div>
    """, unsafe_allow_html=True)
with st.sidebar:
    st.markdown("<h2 style='color:#f5a623; margin-top:0;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#e2a826; font-size:13px; margin:0;'>👤 Handle: <b>{st.session_state.logged_in_user}</b></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#38bdf8; font-size:13px; margin:3px 0 12px 0;'>🆔 Your Referral ID: <b>{allocated_user_id}</b></p>", unsafe_allow_html=True)
    if st.button("🚪 Logout Account", key="logout_sidebar_btn"): 
        st.session_state.logged_in_user = None; st.rerun()
        
    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = True if "Live" in bot_mode else False
    selected_display_name = st.selectbox("Select Contract Asset:", list(BYBYT_DATABASE_CORE.keys()), index=0)
    coin_config = BYBYT_DATABASE_CORE[selected_display_name]
    target_symbol = coin_config["symbol"]
    
    ai_decision = st.toggle("AI Smart Crossover Filter", value=True)
    leverage = st.slider(f"Leverage (Max {coin_config['max_leverage']}x):", min_value=1, max_value=coin_config["max_leverage"], value=20)
    trade_amount = st.number_input("Margin Requirement (\$):", min_value=1, max_value=1000, value=20)
    price_jump_target = st.number_input("Take Profit Target (\$ Price Delta):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_tp"], format="%.8f")
    stop_loss_gap = st.number_input("Stop Loss Threshold (\$ Price Delta):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_sl"], format="%.8f")
    
    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b; margin:10px 0;'>", unsafe_allow_html=True)
        input_license = st.text_input("Enter License Key to Unlock Live Fields:", type="password", key="lic_field_sidebar").strip()
        if input_license in st._central_key_registry:
            api_key = st.text_input("Bybit API Key:", type="password", key="api_field_sidebar")
            secret_key = st.text_input("Bybit Secret Key:", type="password", key="sec_field_sidebar")

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 
if 'active_coin' not in st.session_state or st.session_state.active_coin != target_symbol:
    st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.session_state.active_coin = target_symbol
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Super Admin Module Panel)"):
    master_input = st.text_input("Input Master Security Override Code Password:", type="password", key="supreme_admin_password_node")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.success("Supreme Controller Access Verified.")
        
        # 👑 নতুন রিকোয়ারমেন্ট ফিচার: রেফারেল বোনাস এবং ফিক্সড ডলার/% কমিশন ক্যালকুলেশন অন-অফ হাব মডিউল
        st.markdown("<b style='color:#f5a623;'>⚙️ Referral Marketing Matrix Controls:</b>", unsafe_allow_html=True)
        st._mlm_bonus_enabled = st.toggle("Activate MLM Multi-Generation Incentive Commissions System", value=st._mlm_bonus_enabled, key="adm_mlm_active_toggle")
        st._mlm_bonus_type = st.selectbox("Incentive Computation Logic Engine Metric:", ["Percentage %", "Fixed USD Capital Pool"], index=0 if st._mlm_bonus_type == "Percentage %" else 1, key="adm_bonus_logic_select")
        
        if st._mlm_bonus_type == "Fixed USD Capital Pool":
            st._mlm_fixed_usd_pool = st.number_input("Total Fixed USD Reward Allocation per Account Minting:", min_value=0.1, max_value=500.0, value=st._mlm_fixed_usd_pool, key="adm_fixed_usd_input")
        
        st.markdown("🌐 **Configure 7-Generation Split Allocation Commission Rates & Member Caps:**")
        c_cols = st.columns(4)
        for g in range(1, 8):
            with c_cols[(g-1)%4]:
                st._mlm_gen_rates[g] = st.number_input(f"Gen {g} Rate (%):", min_value=0.0, max_value=100.0, value=st._mlm_gen_rates[g], key=f"adm_rates_generation_input_g_{g}")
                st._mlm_id_thresholds[g] = st.number_input(f"Gen {g} Members Limit:", min_value=1, max_value=5000, value=st._mlm_id_thresholds[g], key=f"adm_thresholds_generation_input_g_{g}")
        
        if st.button("Mint New Randomized License Token Key", key="adm_mint_token_trigger_btn"):
            random_token = "SCLP-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            st._central_key_registry[random_token] = "FREE_SLOT"
            st._license_csv_database.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "License Key": random_token, "Status": "Active (Unused)"})
            st.code(f"{random_token}", language="text"); st.rerun()
        if master_input == YOUR_SECRET_MASTER_CODE:
            st.markdown("<b style='color:#ff1744;'>🚫 Token Blacklist Revocation Panel:</b>", unsafe_allow_html=True)
            target_block_key = st.text_input("Paste Target License Token to BAN permanently:", key="adm_ban_token_input_field")
            if st.button("Execute Permanent Revocation Ban", key="adm_ban_token_trigger_btn"):
                if target_block_key in st._central_key_registry:
                    st._central_blacklist.append(target_block_key)
                    del st._central_key_registry[target_block_key]
                    for row in st._license_csv_database:
                        if row["License Key"] == target_block_key: row["Status"] = "Permanently Banned ❌"
                    st.warning(f"Token {target_block_key} blocked."); st.rerun()

            st.markdown("📋 **Central Token Registry Pool Storage Data Table Ledger:**")
            if st._license_csv_database: st.dataframe(pd.DataFrame(st._license_csv_database).iloc[::-1], use_container_width=True, height=120)
                
            st.markdown("<br><b style='color:#f5a623;'>🌿 Global Master Network Hierarchy Tree View:</b>", unsafe_allow_html=True)
            all_creds_df = pd.DataFrame.from_dict(st._central_user_creds, orient='index')
            if not all_creds_df.empty: st.dataframe(all_creds_df[["uid", "sponsor"]], use_container_width=True)
            if st._global_referral_tree:
                for parent, children in st._global_referral_tree.items():
                    p_user = st._uid_to_username.get(parent, parent)
                    st.markdown(f"👤 **Sponsor Handle:** `{p_user}` (`{parent}`)")
                    for child in children:
                        c_user = st._uid_to_username.get(child, child)
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;└── 📱 **Downline Node Handle:** `{c_user}` (`{child}`)")
            
            st.markdown("<br><b style='color:#38bdf8;'>📈 Global System Downline Performance Auditing Node Ledger:</b>", unsafe_allow_html=True)
            if st._global_user_pnl_history:
                global_pnl_df = pd.DataFrame(st._global_user_pnl_history)
                target_audit_uid = st.selectbox("Select Target Registered Node UID to Inspect logs:", global_pnl_df["User ID"].unique(), key="adm_audit_node_selector_dropdown")
                st.dataframe(global_pnl_df[global_pnl_df["User ID"] == target_audit_uid].iloc[::-1], use_container_width=True)
            else: st.info("No logs database ledger synchronized yet.")
    elif master_input != "": st.error("Administrative override password verification failed.")
# 🌿 Isolated Referral Network Engine Display for Logged-In Users (Masud Tree Fix Sync)
st.markdown("<h3 style='color:#f5a623; font-size:16px;'>🌿 My Referral Network Hub</h3>", unsafe_allow_html=True)

# 🔄 মেমরি সিঙ্ক্রোনাইজেশন লুপ সচল নোড এন্ট্রি
all_user_children = st._global_referral_tree.get(allocated_user_id, [])

if all_user_children:
    st.markdown(f"🎯 Total Direct Network Referrals: <b>{len(all_user_children)} Active Users</b>", unsafe_allow_html=True)
    child_display_map = {cid: f"{st._uid_to_username.get(cid, 'Unknown')} ({cid})" for cid in all_user_children}
    selected_child_cid = st.selectbox("Select Downline Handle to Audit Logs:", list(child_display_map.keys()), format_func=lambda x: child_display_map[x], key="user_referral_dropdown_node_select")
    
    t1, t2 = st.tabs(["实时 Real Production Earnings Gate 🟢", "模拟 Demo Sandbox Earnings Gate 🔵"])
    with t1:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            child_real_df = pnl_df[(pnl_df["User ID"] == selected_child_cid) & (pnl_df["Type"] == "REAL")]
            if not child_real_df.empty:
                child_real_df["Net P&L ($)"] = pd.to_numeric(child_real_df["Net P&L ($)"])
                st.markdown(f"💰 Real Capital Earnings: <b style='color:#00e676;'>${child_real_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True)
                st.dataframe(child_real_df.iloc[::-1], use_container_width=True)
            else: st.info("No live production funds data synchronized.")
        else: st.info("Ledger registry is empty.")
    with t2:
        if st._global_user_pnl_history:
            pnl_df = pd.DataFrame(st._global_user_pnl_history)
            child_demo_df = pnl_df[(pnl_df["User ID"] == selected_child_cid) & (pnl_df["Type"] == "DEMO")]
            if not child_demo_df.empty:
                child_demo_df["Net P&L ($)"] = pd.to_numeric(child_demo_df["Net P&L ($)"])
                st.markdown(f"💰 Demo Virtual Earnings: <b style='color:#29b6f6;'>${child_demo_df['Net P&L ($)'].sum():.2f} USDT</b>", unsafe_allow_html=True)
                st.dataframe(child_demo_df.iloc[::-1], use_container_width=True)
            else: st.info("No sandbox data synchronized.")
        else: st.info("Ledger registry is empty.")
else: st.info("You haven't referred anyone yet. Share your Referral ID Token to grow your matrix network tree!")
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

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

# Box 1 Component Display Modules Restored Completely
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
    # Box 2 Target Display Modules Restored Completely
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
        if st.button("🔴 STOP ENGINE", key="stop_engine_bot_btn"): st.session_state.bot_active = False; st.rerun()
    else:
        if st.button("🟢 START SCALPER", key="start_engine_bot_btn"): st.session_state.bot_active = True; st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button("🚨 EMERGENCY LIQUIDATE", key="force_sell_engine_btn"):
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
        raw_qty = effective_vol / live_price
        calculated_qty = max(0.1, round(raw_qty, 1 if live_price < 1.0 else (2 if live_price < 500.0 else 4)))
        if not st.session_state.in_position:
            decision_side = "NONE"
            if ai_decision:
                if current_rsi < 45.0: decision_side = "BUY"
                elif current_rsi > 55.0: decision_side = "SELL"
            else: decision_side = "BUY"
            if decision_side != "NONE":
                st.session_state.buy_price = live_price; st.session_state.in_position = True
                st.session_state.current_side = "LONG" if decision_side == "BUY" else "SHORT"
                st.session_state.all_trades_history.append({"Time": time.strftime("%H:%M:%S"), "Coin": target_symbol, "Action": f"OPEN {st.session_state.current_side}", "Price": live_price, "Target": f"${(live_price + price_jump_target) if decision_side == 'BUY' else (live_price - price_jump_target)}", "Trading Fee ($)": f"-{estimated_fee/2:.3f}", "Net P&L ($)": "0.00", "Status": "RUNNING"})
            st.rerun()
        elif st.session_state.in_position:
            is_long_pos = True if st.session_state.current_side == "LONG" else False
            is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target) if is_long_pos else live_price <= (st.session_state.buy_price - price_jump_target)
            is_stop_hit = live_price <= (st.session_state.buy_price - stop_loss_gap) if is_long_pos else live_price >= (st.session_state.buy_price + stop_loss_gap)
            if is_profit_hit or is_stop_hit:
                status_tag = "PROFIT 🟢" if is_profit_hit else "STOPLOSS 🔴"; net_pnl = floating_pnl - estimated_fee
                st._global_user_pnl_history.append({"Date": time.strftime("%Y-%m-%d"), "Time": time.strftime("%H:%M:%S"), "User ID": allocated_user_id, "Coin": target_symbol, "Action": f"CLOSE {st.session_state.current_side}", "Net P&L ($)": f"{net_pnl:.2f}", "Type": "REAL" if is_real_live else "DEMO"})
                if is_profit_hit: st.session_state.win_count += 1
                else: st.session_state.loss_count += 1
                if not is_real_live: st.session_state.demo_balance += net_pnl
                for idx, trade in enumerate(st.session_state.all_trades_history):
                    if trade["Status"] == "RUNNING" and trade["Coin"] == target_symbol:
                        st.session_state.all_trades_history[idx]["Status"] = status_tag
                        st.session_state.all_trades_history[idx]["Net P&L ($)"] = f"{net_pnl:.2f}"
                st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.rerun()
        time.sleep(1); st.rerun()
    except: time.sleep(1); st.rerun()
else: st.info("Engine Inactive. Invoke green trigger to start loop sequences.")
st.subheader("📋 Permanent Trading Action History")
if st.session_state.all_trades_history: st.dataframe(pd.DataFrame(st.session_state.all_trades_history).iloc[::-1], use_container_width=True)
