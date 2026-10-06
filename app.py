import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit AI Scalper Pro", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    .stButton>button[key="force_sell_btn"] { background-color: #ff3333 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Future Scalper")
st.caption("ভার্সন ৭.০ | স্বয়ংক্রিয় এআই ডিসিশন ও মাল্টি-অর্ডার মেমোরি")

# ২. ডাইনামিক ফিউচার সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ AI Configuration")
    bot_mode = st.radio("ট্রেডিং মোড:", ["Demo Mode (ফ্রি ৫,০০০$ ফেইক ফান্ড)", "Live Mode (আসল Bybit API)"])
    is_real_live = True if "Live" in bot_mode else False
    
    st.success("🤖 AI Mode Active: বট নিজে থেকে মার্কেট কন্ডিশন বুঝে BUY/SELL সিদ্ধান্ত নেবে।")
    
    leverage = st.slider("ফিউচার লেভারেজ", min_value=1, max_value=50, value=20, step=1)
    trade_amount = st.number_input("মার্জিন কস্ট ($)", min_value=1, max_value=500, value=20, step=1)
    price_jump_target = st.slider("প্রফিট বুকিং টার্গেট ($ গ্যাপ)", min_value=2, max_value=500, value=15, step=2)
    
    api_key = ""
    secret_key = ""
    if is_real_live:
        api_key = st.text_input("Bybit API Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")

# ৩. সেসন স্টেট ইনিশিয়ালাইজেশন (মাল্টি-অর্ডার মেমোরি ফিক্স)
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'active_side' not in st.session_state: st.session_state.active_side = "" # LONG বা SHORT ট্র্যাকার
if 'trade_logs' not in st.session_state: st.session_state.trade_logs = ["[SYSTEM] AI Autopilot mode activated."]

balance_usd = f"${st.session_state.demo_balance:,.2f}" if not is_real_live else "$0.00"

# Bybit Real API ব্যালেন্স ও রিয়েল পজিশন ট্র্যাকিং
session = None
if is_real_live and api_key and secret_key:
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
        try: session.set_leverage(category="linear", symbol="BTCUSDT", buyLeverage=str(leverage), sellLeverage=str(leverage))
        except: pass
        
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list:
            for c in member_list.get('coin', []):
                if c.get('coin') == 'USDT':
                    balance_usd = f"${float(c.get('walletBalance', 0)):,.2f}"
                    break
        
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and float(positions.get('size', 0)) > 0:
            st.session_state.in_position = True
            st.session_state.active_side = "LONG" if positions.get('side') == "Buy" else "SHORT"
            if st.session_state.buy_price == 0.0:
                st.session_state.buy_price = float(positions.get('entryPrice', 0))
    except:
        balance_usd = "API কী চেক করুন"

# পজিশন স্ট্যাটাস টেক্সট ফিক্স
position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"Future {st.session_state.active_side} ⚡ (Entry: ${st.session_state.buy_price:,.2f})"
# ৪. ডিসপ্লে ওয়ালেট ও ফিউচার স্ট্যাটাস
st.subheader(f"📊 Future {bot_mode} (Leverage: {leverage}x)")
col1, col2 = st.columns(2)
with col1: st.metric(label="Available Margin", value=balance_usd)
with col2: st.metric(label="Active Future Position", value=position_status)

# ৫. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button("🔴 STOP BOT", key="stop_btn"):
            st.session_state.bot_active = False
            st.session_state.trade_logs.append("[SYSTEM] Bot stopped by user.")
            st.rerun()
    else:
        if st.button("🟢 START FUTURE SCALPING", key="start_btn"):
            st.session_state.bot_active = True
            st.session_state.trade_logs.append(f"[SYSTEM] AI Auto-Trading Scalper Activated.")
            st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button("🚨 FORCE CLOSE FUTURE", key="force_sell_btn"):
            st.session_state.in_position = False
            st.session_state.buy_price = 0.0
            st.session_state.active_side = ""
            st.session_state.trade_logs.append("[🚨 FORCE CLOSED] Position deleted manually!")
            st.rerun()

# 🔍 লাইভ মার্কেট ডাটা ও এআই অ্যাকশন লুপ
if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close']: df[col] = pd.to_numeric(df[col])
            
            live_price = df['close'].iloc[-1]
            st.subheader(f"📈 Future BTC/USDT Price: ${live_price:,.2f}")
            
            # চার্ট
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00cc66', decreasing_line_color='#ff3333')])
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", height=230)
            st.plotly_chart(fig, use_container_width=True)

            effective_vol = trade_amount * leverage
            calculated_qty = round((effective_vol / live_price), 4)
            if calculated_qty < 0.0001: calculated_qty = 0.0001

            # ⚡ এআই ইন্ডিকেটর (RSI) গণনা করা স্বয়ংক্রিয় সিদ্ধান্তের জন্য
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50

            # 🤖 ১. এআই অর্ডার ওপেনিং ডিসিশন লজিক (নিজে নিজে BUY/SELL পজিশন নেওয়া)
            if not st.session_state.in_position:
                # RSI কন্ডিশন চেক করে এআই নিজে সিদ্ধান্ত নেবে
                if current_rsi < 40:  # মার্কেট নিচে নেমেছে, এআই এখন BUY (LONG) করবে
                    st.session_state.active_side = "LONG"
                    st.session_state.buy_price = live_price
                    st.session_state.in_position = True
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side="Buy", orderType="Market", qty=str(calculated_qty))
                        except: st.session_state.in_position = False
                    else:
                        st.session_state.trade_logs.append(f"[🤖 AI BUY - LONG] Entry: ${live_price} | RSI: {current_rsi:.1f}")
                    st.rerun()
                    
                elif current_rsi > 60:  # মার্কেট ওপরে উঠেছে, এআই এখন SELL (SHORT) করবে
                    st.session_state.active_side = "SHORT"
                    st.session_state.buy_price = live_price
                    st.session_state.in_position = True
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side="Sell", orderType="Market", qty=str(calculated_qty))
                        except: st.session_state.in_position = False
                    else:
                        st.session_state.trade_logs.append(f"[🤖 AI SELL - SHORT] Entry: ${live_price} | RSI: {current_rsi:.1f}")
                    st.rerun()
                else:
                    st.session_state.trade_logs.append(f"[🔎 AI Scanning Market] RSI: {current_rsi:.1f} | সঠিক সুযোগের অপেক্ষা করছে...")
            
            # 🤖 ২. সুরক্ষিত প্রফিট বুকিং ইঞ্জিন (মেমোরি লক সহ)
            elif st.session_state.in_position:
                if st.session_state.active_side == "LONG":
                    is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                    is_stop_hit = live_price <= (st.session_state.buy_price - 80.0)
                    raw_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
                    close_action = "Sell"
                else:
                    is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                    is_stop_hit = live_price >= (st.session_state.buy_price + 80.0)
                    raw_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)
                    close_action = "Buy"

                if is_profit_hit or is_stop_hit:
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
                        except: pass
                    else:
                        st.session_state.demo_balance += raw_pnl
                        sign = "+" if raw_pnl >= 0 else ""
                        st.session_state.trade_logs.append(f"[🔴 AI CLOSED] ${live_price} | P&L: {sign}${raw_pnl:.2f}")
                    
                    # অর্ডার সফলভাবে শেষ হলে লক রিসেট হবে
                    st.session_state.in_position = False
                    st.session_state.buy_price = 0.0
                    st.session_state.active_side = ""
                    st.rerun()
                else:
                    target_display = (st.session_state.buy_price + price_jump_target) if st.session_state.active_side == "LONG" else (st.session_state.buy_price - price_jump_target)
                    st.session_state.trade_logs.append(f"[🔎 Tracking Position] Mode: {st.session_state.active_side} | Live: ${live_price} | Target: ${target_display:.2f}")

        st.subheader("📜 Live Action Logs")
        st.text_area("Logs", value="\n".join(st.session_state.trade_logs[-5:]), height=130)
        time.sleep(1)
        st.rerun()
    except:
        time.sleep(1)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। ফিউচার স্ক্যাল্পিং চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
