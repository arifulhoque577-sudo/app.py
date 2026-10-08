import streamlit as st
import pandas as pd
import time
import random
import string
import requests
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# 1. Global Cross-Session Server Registry Emulation
if 'GLOBAL_KEY_REGISTRY' not in st.experimental_get_query_params():
    if not hasattr(st, "_global_key_pool"):
        st._global_key_pool = {}  # Format: {"KEY-TOKEN": "IP_ADDRESS_OR_FREE"}
    if not hasattr(st, "_global_blacklist"):
        st._global_blacklist = [] # Format: ["COMPROMISED_KEYS"]

# Page Setup Optimization
st.set_page_config(
    page_title="Bybit AI Frontline Scalper", 
    page_icon="⚡", 
    layout="centered"
)
st.markdown("""
    <style>
    .main { background-color: #06090e; }
    div[data-testid="stSidebar"] { 
        background-color: #0b0f17 !important; 
        border-right: 1px solid #1e293b; 
    }
    div.stButton > button:first-child { 
        width: 100%; border-radius: 8px; 
        font-weight: 800; font-size: 15px; height: 46px; 
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    iframe { border: none !important; }
    .ticker-wrap { 
        width: 100%; background: rgba(30, 41, 59, 0.25); 
        border: 1px solid #1e293b; border-radius: 8px; 
        overflow: hidden; padding: 6px 0; margin-bottom: 15px; 
    }
    .ticker { 
        display: inline-block; white-space: nowrap; 
        animation: marquee 20s linear infinite; padding-left: 100%; 
    }
    .ticker__item { 
        display: inline-block; color: #38bdf8; 
        font-size: 13px; font-family: monospace; font-weight: bold; 
    }
    @keyframes marquee { 
        0% { transform: translate3d(0, 0, 0); } 
        100% { transform: translate3d(-100%, 0, 0); } 
    }
    </style>
    """, unsafe_allow_html=True)
# Bybit Branding Logo Header Custom Web Widget Design
st.markdown("""
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 16px; border-radius: 12px; margin-bottom: 20px; text-align: center; border: 1px solid #f5a623; box-shadow: 0px 4px 20px rgba(245, 166, 35, 0.15);">
        <span style="font-size: 24px; vertical-align: middle;">🔶</span>
        <h1 style="display: inline; margin-left: 8px; color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; letter-spacing: 1px; vertical-align: middle;">BYBIT AI PRO SCALPER</h1>
        <p style="margin: 5px 0 0 0; color: #f5a623; font-weight: bold; font-family: monospace; font-size: 11px; letter-spacing: 2px;">FRONTLINE VERSION 15.0 • HIGH-LEVERAGE PERPETUAL ENGINE</p>
    </div>
    """, unsafe_allow_html=True)

# 2. Dynamic High-Leverage Multi-Coin Configuration Specifications
COIN_DATABASE = {
    "🪙 BTCUSDT (Bitcoin)": {"symbol": "BTCUSDT", "max_leverage": 100, "default_tp": 100.0, "default_sl": 150.0, "step": 10.0},
    "🔷 ETHUSDT (Ethereum)": {"symbol": "ETHUSDT", "max_leverage": 100, "default_tp": 8.0, "default_sl": 15.0, "step": 1.0},
    "☀️ SOLUSDT (Solana)": {"symbol": "SOLUSDT", "max_leverage": 50, "default_tp": 1.5, "default_sl": 3.0, "step": 0.1},
    "💥 XRPUSDT (Ripple)": {"symbol": "XRPUSDT", "max_leverage": 100, "default_tp": 0.015, "default_sl": 0.03, "step": 0.001},
    "🐶 DOGEUSDT (Dogecoin)": {"symbol": "DOGEUSDT", "max_leverage": 50, "default_tp": 0.004, "default_sl": 0.01, "step": 0.0005},
    "🔥 SHIBUSDT (Shiba Inu)": {"symbol": "SHIBUSDT", "max_leverage": 50, "default_tp": 0.0000005, "default_sl": 0.000001, "step": 0.0000001},
    "🔮 LINKUSDT (Chainlink)": {"symbol": "LINKUSDT", "max_leverage": 50, "default_tp": 0.25, "default_sl": 0.50, "step": 0.01},
    "🧬 ADAUSDT (Cardano)": {"symbol": "ADAUSDT", "max_leverage": 50, "default_tp": 0.01, "default_sl": 0.02, "step": 0.001},
    "💎 PEPEUSDT (Pepe)": {"symbol": "PEPEUSDT", "max_leverage": 50, "default_tp": 0.0000001, "default_sl": 0.0000003, "step": 0.00000001},
    "🌀 WIFUSDT (dogwifhat)": {"symbol": "WIFUSDT", "max_leverage": 50, "default_tp": 0.05, "default_sl": 0.12, "step": 0.01}
}

YOUR_SECRET_MASTER_CODE = "ADMIN1234"
# 3. Session State Initialization
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []
if 'win_count' not in st.session_state: st.session_state.win_count = 0
if 'loss_count' not in st.session_state: st.session_state.loss_count = 0

# Secure Public IP Sniffer
def fetch_live_network_ip():
    try: return requests.get("https://ipify.org", timeout=2).text
    except: return "127.0.0.1"

resolved_network_ip = fetch_live_network_ip()
with st.sidebar:
    st.markdown("<h2 style='color:#f5a623;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
    bot_mode = st.radio("Trading Account Mode:", ["Demo Simulation (Virtual Funds)", "Live Exchange (Bybit Mainnet API)"])
    is_real_live = True if "Live" in bot_mode else False
    
    selected_display_name = st.selectbox("Select Perpetual Contract:", list(COIN_DATABASE.keys()), index=0)
    coin_config = COIN_DATABASE[selected_display_name]
    target_symbol = coin_config["symbol"]
    
    ai_decision = st.toggle("AI Smart Crossover Filter (RSI Mean Reversion)", value=True)
    leverage = st.slider(f"Adjust Leverage (Max {coin_config['max_leverage']}x):", min_value=1, max_value=coin_config["max_leverage"], value=20, step=1)
    trade_amount = st.number_input("Margin Requirement ($):", min_value=1, max_value=1000, value=20, step=1)
    price_jump_target = st.number_input("Take Profit Target ($ Price Delta):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_tp"], step=coin_config["step"], format="%.8f")
    stop_loss_gap = st.number_input("Stop Loss Threshold ($ Price Delta):", min_value=0.00000001, max_value=5000.0, value=coin_config["default_sl"], step=coin_config["step"], format="%.8f")
    
    api_key, secret_key = "", ""
    if is_real_live:
        st.markdown("<hr style='border:1px solid #1e293b;'>", unsafe_allow_html=True)
        st.markdown("<p style='color:#ff3333; font-weight:bold; font-size:12px;'>🔒 LICENSE PROTECTION ACTIVE</p>", unsafe_allow_html=True)
        input_license = st.text_input("Enter License Token Key:", type="password")
        
        if input_license != "":
            # Check 1: If key is blacklisted due to multi-device fraud profile matching
            if input_license in st._global_blacklist:
                st.markdown("<div style='background-color:#450a0a; padding:10px; border-radius:5px; border:1px solid #f87171;'><p style='margin:0; color:#f87171; font-weight:bold; font-size:13px;'>❌ Access Revoked: Second Device Found!</p><p style='margin:5px 0 0 0; color:#cbd5e1; font-size:11px;'>This license token attempted an active connection from an unauthorized separate IP network profile and has been globally quarantined.</p></div>", unsafe_allow_html=True)
            # Check 2: Verify validation from cross-network storage registry
            elif input_license in st._global_key_pool:
                tracked_device_ip = st._global_key_pool[input_license]
                
                if tracked_device_ip == "FREE_REGISTRATION_SLOT":
                    # Lock the license token permanently to the network cell IP profile of first use
                    st._global_key_pool[input_license] = resolved_network_ip
                    st.success("🔓 First-Touch Activation Success! IP Bond Lock established.")
                    api_key = st.text_input("Bybit Authenticated API Key:", type="password")
                    secret_key = st.text_input("Bybit Authenticated Secret Key:", type="password")
                elif tracked_device_ip == resolved_network_ip:
                    st.success("🔓 Authorization Verified! Access Granted.")
                    api_key = st.text_input("Bybit Authenticated API Key:", type="password")
                    secret_key = st.text_input("Bybit Authenticated Secret Key:", type="password")
                else:
                    # Fraud Profile Detected! Instantly drop and blacklist the token from global storage registry
                    st._global_blacklist.append(input_license)
                    if input_license in st._global_key_pool: del st._global_key_pool[input_license]
                    st.markdown("<div style='background-color:#450a0a; padding:10px; border-radius:5px; border:1px solid #f87171;'><p style='margin:0; color:#f87171; font-weight:bold; font-size:13px;'>❌ Access Revoked: Second Device Found!</p></div>", unsafe_allow_html=True)
            else:
                st.error("❌ Key Validation Mismatch! Token not registered.")
if 'active_coin' not in st.session_state or st.session_state.active_coin != target_symbol:
    st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.session_state.active_coin = target_symbol

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 
total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

# Redesigned Developer Expansion Terminal Layout Console
with st.expander("🛠️ Advanced Licensing Cryptographic Hub (Administrative Master Controls)"):
    master_input = st.text_input("Input Master Security Override Code:", type="password")
    if master_input == YOUR_SECRET_MASTER_CODE:
        st.markdown("<div style='color:#00e676; font-size:13px; font-weight:bold; margin-bottom:10px;'>🔓 Global Registry Subsystem Access Granted.</div>", unsafe_allow_html=True)
        
        # Token Generator Node Block 
        st.markdown("<p style='margin:0; font-size:13px; font-weight:bold; color:#f5a623;'>🎰 Token Minting Production:</p>", unsafe_allow_html=True)
        st.markdown("<p style='margin:0; font-size:11px; color:#94a3b8;'>Generates a network-wide token key card. Valid for single network usage.</p>", unsafe_allow_html=True)
        if st.button("Mint New Token License Key"):
            fresh_token = "SCLP-PRO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            st._global_key_pool[fresh_token] = "FREE_REGISTRATION_SLOT"
            st.markdown("<p style='margin:8px 0 2px 0; font-size:12px; font-weight:bold; color:#cbd5e1;'>📋 Isolated Output Key (Click top-right box to copy ONLY the code):</p>", unsafe_allow_html=True)
            # Isolated native markdown code box block for one-click pure content extraction
            st.code(f"{fresh_token}", language="text")
            
        # Token Revocation Sub-Node Block
        st.markdown("<p style='margin:15px 0 2px 0; font-size:13px; font-weight:bold; color:#ff1744;'>🚫 Central Token Revocation Ban-List:</p>", unsafe_allow_html=True)
        target_ban_token = st.text_input("Paste Target License Token to Ban Manually:", placeholder="SCLP-PRO-XXXXXX")
        if st.button("Execute Permanent Administrative Ban"):
            if target_ban_token in st._global_key_pool or target_ban_token in st._global_blacklist:
                if target_ban_token not in st._global_blacklist: st._global_blacklist.append(target_ban_token)
                if target_ban_token in st._global_key_pool: del st._global_key_pool[target_ban_token]
                st.warning(f"TOKEN TERMINATED: {target_ban_token} has been stripped of network access privileges.")
            else:
                st.error("Token signature validation match failed inside server registries.")
    elif master_input != "":
        st.error("Administrative credential mismatch. Subsystem encrypted.")
# Synchronized Symmetric UI Layout Grid Dashboard Panel
st.markdown(f"""
    <div style="background-color:#141a24; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; display: flex; justify-content: space-between; text-align: center;">
        <div style="flex: 1; border-right: 1px solid #1f2c3f;">
            <p style="margin:0; font-size:11px; color:#94a3b8; font-weight:bold;">🏆 PERFORMANCES WON</p>
            <span style="font-size:16px; font-weight:800; color:#00e676; font-family:monospace;">{st.session_state.win_count}</span>
        </div>
        <div style="flex: 1; border-right: 1px solid #1f2c3f;">
            <p style="margin:0; font-size:11px; color:#94a3b8; font-weight:bold;">❌ EXITS LOST</p>
            <span style="font-size:16px; font-weight:800; color:#ff1744; font-family:monospace;">{st.session_state.loss_count}</span>
        </div>
        <div style="flex: 1;">
            <p style="margin:0; font-size:11px; color:#94a3b8; font-weight:bold;">🎯 NET WIN RATE</p>
            <span style="font-size:16px; font-weight:800; color:#29b6f6; font-family:monospace;">{win_rate:.1f}%</span>
        </div>
    </div>
""", unsafe_allow_html=True)
# Real-Time Market Data Stream Ingestion Feed
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
        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list:
            for c in member_list.get('coin', []):
                if c.get('coin') == 'USDT': balance_usd_text = f"${(float(c.get('walletBalance', 0)) + floating_pnl):,.2f}"; break
    except: balance_usd_text = "API Key Error"

position_status = "NO ACTIVE POSITION 💤" if not st.session_state.in_position else f"FUTURE {target_symbol} {st.session_state.current_side} CONTRACT RUNNING"
rsi_color = "#ff1744" if current_rsi > 50 else "#00e676"

st.markdown(f"""
    <div style="background-color:#141a24; padding:10px; border-radius:10px; margin-bottom:12px; border-left: 5px solid {rsi_color}; text-align:center; border: 1px solid #1f2c3f;">
        <span style="color:#94a3b8; font-size:12px; font-weight:bold;">📡 LIVE AI RSI OSCILLATOR (5s FEED):</span>
        <h3 style="margin:2px 0; color:{rsi_color}; font-size:24px; font-family: monospace; font-weight:800;">{current_rsi:.2f}</h3>
    </div>
    <div style="background-color:#141a24; padding:15px; border-radius:12px; margin-bottom:12px; border: 1px solid #1f2c3f;">
        <p style="margin:0; font-size:12px; color:#94a3b8; font-weight:bold;">💰 AVAILABLE BALANCE ACCOUNT ({bot_mode})</p>
        <h2 style="margin:5px 0; color:#ffffff; font-size:28px; font-family: monospace; font-weight:800;">{balance_usd_text}</h2>
        <p style="margin:0; font-size:14px; color:{'#00e676' if floating_pnl >= 0 else '#ff1744'}; font-weight:bold;">Live Floating P&L: {floating_pnl:+.2f} USDT</p>
    </div>
    <div style="background-color:#141a24; padding:15px; border-radius:12px; margin-bottom:15px; border: 1px solid #1f2c3f;">
        <p style="margin:0; font-size:12px; color:#94a3b8; font-weight:bold;">📦 MARGIN STATUS EXECUTION</p>
        <h3 style="margin:5px 0; color:{'#ffffff' if st.session_state.current_side == 'NONE' else ('#00e676' if st.session_state.current_side == 'LONG' else '#ff1744')}; font-size:16px;">{position_status}</h3>
    </div>
    <div class="ticker-wrap"><div class="ticker"><div class="ticker__item">🎞️ SLIDING MARKET WATCH SYSTEM LOG INDEX FEE: {estimated_fee:.4f} USDT &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; • &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ENGINE STATUS: ACTIVE LIQUIDITY SCALPER LOOP PRO UNLOCKED 🎞️</div></div></div>
""", unsafe_allow_html=True)
if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    st.markdown(f"""
    <div style="background-color:#0b0e14; padding:12px; border-radius:10px; margin-bottom:15px; border: 1px solid #1f2c3f; border-left: 5px solid #29b6f6;">
        <span style="font-size:14px; color:#ffffff; font-weight:bold; font-family: monospace;">Entry Price: {st.session_state.buy_price} | Live Index: {live_price}</span><br>
        <span style="font-size:14px; color:#00e676; font-weight:bold; font-family: monospace;">Take Profit Target: {live_target} (Expected Net: +${expected_net_profit:.2f})</span><br>
        <span style="font-size:14px; color:#ff1744; font-weight:bold; font-family: monospace;">Stop Loss Boundary: {live_sl}</span>
    </div>
    """, unsafe_allow_html=True)

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
            if net_pnl >= 0: st.session_state.win_count += 1
            else: st.session_state.loss_count += 1
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
                        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
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
                if is_profit_hit: st.session_state.win_count += 1
                else: st.session_state.loss_count += 1
                if is_real_live:
                    try:
                        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
                        session.place_order(category="linear", symbol=target_symbol, side=close_action, orderType="Market", qty=str(calculated_qty))
                    except: pass
                else: st.session_state.demo_balance += net_pnl
                target_display = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
                st.session_state.all_trades_history.append({"Time": time.strftime("%H:%M:%S"), "Coin": target_symbol, "Action": f"CLOSE {st.session_state.current_side}", "Price": live_price, "Target": f"${target_display}", "Trading Fee ($)": f"-{estimated_fee:.3f}", "Net P&L ($)": f"{net_pnl:.2f}", "Status": status_tag})
                st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.rerun()
        st.subheader("📋 Permanent Trading Action History")
        if st.session_state.all_trades_history:
            history_df = pd.DataFrame(st.session_state.all_trades_history)
            st.dataframe(history_df.iloc[::-1], height=180, use_container_width=True)
            csv_data = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Complete CSV Logs", data=csv_data, file_name=f"scalper_fee_logs_{time.strftime('%Y%m%d')}.csv", mime='text/csv')
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
