import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Future Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    .stButton>button[key="force_sell_btn"] { background-color: #ff3333 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Future Scalper")
st.caption("ভার্সন ৬.২ | অর্ডার মেমোরি ও লকিং ফিক্সড")

# ২. ডাইনামিক ফিউচার সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configurations")
    bot_mode = st.radio("ট্রেডিং মোড:", ["Demo Mode (ফ্রি ৫,০০০$ ফেইক ফান্ড)", "Live Mode (আসল Bybit API)"])
    is_real_live = True if "Live" in bot_mode else False
    
    trade_direction = st.radio("ফিউচার পজিশন মোড:", ["LONG 🟢 (মার্কেট উপরে যাবে)", "SHORT 🔴 (মার্কেট নিচে যাবে)"])
    is_long = True if "LONG" in trade_direction else False
    
    leverage = st.slider("ফিউচার লেভারেজ", min_value=1, max_value=50, value=20, step=1)
    trade_amount = st.number_input("মার্জিন কস্ট ($)", min_value=1, max_value=500, value=10, step=1)
    
    # বড় প্রফিট বুক করার জন্য লিমিট বাড়িয়ে ৫০০ করা হলো
    price_jump_target = st.slider("প্রফিট বুকিং টার্গেট ($ গ্যাপ)", min_value=2, max_value=500, value=10, step=2)
    
    api_key = ""
    secret_key = ""
    if is_real_live:
        api_key = st.text_input("Bybit API Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")

# ৩. সেসন স্টেট ইনিশিয়ালাইজেশন (লকিং মেমোরি ফিক্স)
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'trade_logs' not in st.session_state: st.session_state.trade_logs = ["[SYSTEM] Scalper Core ready."]

balance_usd = f"${st.session_state.demo_balance:,.2f}" if not is_real_live else "$0.00"
position_mode_text = "LONG 🟢" if is_long else "SHORT 🔴"

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
            for c in member_list[0].get('coin', []):
                if c.get('coin') == 'USDT':
                    balance_usd = f"${float(c.get('walletBalance', 0)):,.2f}"
                    break
        
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and float(positions[0].get('size', 0)) > 0:
            st.session_state.in_position = True
            if st.session_state.buy_price == 0.0:
                st.session_state.buy_price = float(positions[0].get('entryPrice', 0))
    except:
        balance_usd = "API কী চেক করুন"

# পজিশন স্ট্যাটাস টেক্সট ফিক্স
position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"Future {position_mode_text} রানিং (Entry: ${st.session_state.buy_price:,.2f})"

st.subheader(f"📊 Future {bot_mode} (Leverage: {leverage}x)")
col1, col2 = st.columns(2)
with col1: st.metric(label="Available Margin", value=balance_usd)
with col2: st.metric(label="Active Future Position", value=position_status)

# ৪. বট কন্ট্রোল বাটন
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
            st.session_state.trade_logs.append(f"[SYSTEM] Scalper Activated in {position_mode_text}")
            st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button("🚨 FORCE CLOSE FUTURE", key="force_sell_btn"):
            st.session_state.in_position = False
            st.session_state.buy_price = 0.0
            st.session_state.trade_logs.append("[🚨 FORCE CLOSED] Position deleted manually!")
            st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও স্ক্যাল্পিং লুপ
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
            
            # ক্যান্ডেলস্টিক চার্ট প্রদর্শন
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00cc66', decreasing_line_color='#ff3333')])
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", height=230)
            st.plotly_chart(fig, use_container_width=True)

            effective_vol = trade_amount * leverage
            calculated_qty = round((effective_vol / live_price), 4)
            if calculated_qty < 0.0001: calculated_qty = 0.0001

            # ⚡ লকিং অর্ডার ওপেনিং লজিক (একবার বাই হলে আর রিসেট হবে না)
            if not st.session_state.in_position:
                st.session_state.buy_price = live_price
                st.session_state.in_position = True
                side_action = "Buy" if is_long else "Sell"
                
                if is_real_live and session:
                    try: session.place_order(category="linear", symbol="BTCUSDT", side=side_action, orderType="Market", qty=str(calculated_qty))
                    except: st.session_state.in_position = False; st.session_state.buy_price = 0.0
                else:
                    st.session_state.trade_logs.append(f"[🟢 OPENED] Entry: ${live_price} | Mode: {position_mode_text}")
                st.rerun()
            
            # ⚡ লকিং প্রফিট বুকিং ইঞ্জিন (টার্গেট না মিললে অর্ডার আজীবন ধরে রাখবে)
            elif st.session_state.in_position:
                if is_long:
                    is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                    is_stop_hit = live_price <= (st.session_state.buy_price - 80.0)
                    raw_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
                else:
                    is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                    is_stop_hit = live_price >= (st.session_state.buy_price + 80.0)
                    raw_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)

                if is_profit_hit or is_stop_hit:
                    close_action = "Sell" if is_long else "Buy"
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
                        except: pass
                    else:
                        st.session_state.demo_balance += raw_pnl
                        sign = "+" if raw_pnl >= 0 else ""
                        st.session_state.trade_logs.append(f"[🔴 CLOSED] ${live_price} | P&L: {sign}${raw_pnl:.2f}")
                    
                    # ট্রেড সফলভাবে শেষ হলে লক খুলে দেওয়া হবে নতুন ট্রেডের জন্য
                    st.session_state.in_position = False
                    st.session_state.buy_price = 0.0
                    st.rerun()
                else:
                    # টার্গেট না মিললে সে ডিলিট না করে অনবরত স্ক্যান করবে
                    target_display = (st.session_state.buy_price + price_jump_target) if is_long else (st.session_state.buy_price - price_jump_target)
                    st.session_state.trade_logs.append(f"[🔎 Scanning] Live: ${live_price} | Target: ${target_display:.2f}")

        st.subheader("📜 Live Action Logs")
        st.text_area("Logs", value="\n".join(st.session_state.trade_logs[-5:]), height=130)
        
        time.sleep(1)
        st.rerun()
    except:
        time.sleep(1)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। ফিউচার স্ক্যাল্পিং চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
