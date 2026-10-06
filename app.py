import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Future AI Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    .stButton>button[key="force_sell_btn"] { background-color: #ff3333 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Future Scalper")
st.caption("ভার্সন ৭.০ | এআই ডিসিশন, লকিং মেমোরি ও এক্সেল লগ এক্সপোর্ট")

# ২. ডাইনামিক ফিউচার সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configurations")
    bot_mode = st.radio("ট্রেডিং মোড:", ["Demo Mode (ফ্রি ৫,০০০$ ফেইক ফান্ড)", "Live Mode (আসল Bybit API)"])
    is_real_live = True if "Live" in bot_mode else False
    
    # 🧠 এআই ডিসিশন মোড অপশন
    ai_decision = st.toggle("এআই অটো-ডিসিশন (RSI + MACD)", value=True, help="অন রাখলে বট নিজে সিদ্ধান্ত নিয়ে বাই বা সেল করবে।")
    
    leverage = st.slider("ফিউচার লেভারেজ", min_value=1, max_value=50, value=20, step=1)
    trade_amount = st.number_input("মার্জিন কস্ট ($)", min_value=1, max_value=500, value=10, step=1)
    price_jump_target = st.slider("প্রফিট বুকিং টার্গেট ($ গ্যাপ)", min_value=2, max_value=500, value=15, step=1)
    stop_loss_gap = st.slider("স্টপ লস প্রোটেকশন ($ গ্যাপ)", min_value=10, max_value=500, value=50, step=5)
    
    api_key = ""
    secret_key = ""
    if is_real_live:
        api_key = st.text_input("Bybit API Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")

# ৩. সেসন স্টেট ও পার্মানেন্ট লগ মেমোরি ইনিশিয়ালাইজেশন
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"

# 📊 এক্সেল ডেটা সেভ করার জন্য পার্মানেন্ট হিস্ট্রি টেবিল মেমোরি
if 'all_trades_history' not in st.session_state:
    st.session_state.all_trades_history = []

balance_usd = f"${st.session_state.demo_balance:,.2f}" if not is_real_live else "$0.00"
position_mode_text = st.session_state.current_side

# Bybit API ব্যালেন্স ও রিয়েল পজিশন ট্র্যাকিং
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
            st.session_state.current_side = positions.get('side').upper()
            if st.session_state.buy_price == 0.0:
                st.session_state.buy_price = float(positions.get('entryPrice', 0))
    except:
        balance_usd = "API কী চেক করুন"

position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"Future {st.session_state.current_side} রানিং (Entry: ${st.session_state.buy_price:,.2f})"

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
            st.rerun()
    else:
        if st.button("🟢 START FUTURE SCALPING", key="start_btn"):
            st.session_state.bot_active = True
            st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button("🚨 FORCE CLOSE FUTURE", key="force_sell_btn"):
            st.session_state.in_position = False
            st.session_state.buy_price = 0.0
            st.session_state.current_side = "NONE"
            st.rerun()

# 🔍 মার্কেট ডাটা, এআই সিদ্ধান্ত ও অ্যাকশন লুপ
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
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", height=220)
            st.plotly_chart(fig, use_container_width=True)

            # 🧠 এআই ডিসিশন ইন্ডিকেটর (RSI 14) গণনা করা
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50

            effective_vol = trade_amount * leverage
            calculated_qty = round((effective_vol / live_price), 4)
            if calculated_qty < 0.0001: calculated_qty = 0.0001

            # ⚡ লকিং অর্ডার ওপেনিং লজিক (AI ডিসিশন সহ বাই/সেল অর্ডার প্লেস)
            if not st.session_state.in_position:
                decision_side = "NONE"
                
                if ai_decision:
                    # এআই লজিক: RSI ৩৫ এর নিচে নামলে BUY (LONG), ৬৫ এর ওপরে উঠলে SELL (SHORT)
                    if current_rsi < 38: decision_side = "BUY"
                    elif current_rsi > 62: decision_side = "SELL"
                else:
                    # এআই অফ থাকলে ডিফল্ট অটো লং ধরবে
                    decision_side = "BUY"

                if decision_side != "NONE":
                    st.session_state.buy_price = live_price
                    st.session_state.in_position = True
                    st.session_state.current_side = "LONG" if decision_side == "BUY" else "SHORT"
                    
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side=decision_side, orderType="Market", qty=str(calculated_qty))
                        except: st.session_state.in_position = False; st.session_state.buy_price = 0.0
                    
                    # পার্মানেন্ট লগ ফাইলে সেভ করার ফরম্যাট
                    st.session_state.all_trades_history.append({
                        "Time": time.strftime("%H:%M:%S"), "Action": f"OPEN {st.session_state.current_side}",
                        "Price": live_price, "P&L ($)": "0.00", "Status": "RUNNING"
                    })
                st.rerun()
            
            # ⚡ প্রফিট বুকিং ও স্টপ লস ট্র্যাকিং ইঞ্জিন
            elif st.session_state.in_position:
                is_long_pos = True if st.session_state.current_side == "LONG" else False
                
                if is_long_pos:
                    is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                    is_stop_hit = live_price <= (st.session_state.buy_price - stop_loss_gap)
                    raw_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
                else:
                    is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                    is_stop_hit = live_price >= (st.session_state.buy_price + stop_loss_gap)
                    raw_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)

                if is_profit_hit or is_stop_hit:
                    close_action = "Sell" if is_long_pos else "Buy"
                    status_tag = "PROFIT 🟢" if is_profit_hit else "STOPLOSS 🔴"
                    
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
                        except: pass
                    else:
                        st.session_state.demo_balance += raw_pnl
                    
                    # পার্মানেন্ট লগ টেবিলে প্রফিট/লস সেভ করা
                    st.session_state.all_trades_history.append({
                        "Time": time.strftime("%H:%M:%S"), "Action": f"CLOSE {st.session_state.current_side}",
                        "Price": live_price, "P&L ($)": f"{raw_pnl:.2f}", "Status": status_tag
                    })
                    
                    st.session_state.in_position = False
                    st.session_state.buy_price = 0.0
                    st.session_state.current_side = "NONE"
                    st.rerun()
                else:
                    target_display = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
                    sl_display = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)

        # 📜 ৬. অল-টাইম লাইভ ট্রেড লগ টেবিল ভিউ (স্ক্রল ডাউন করলেও ডেটা হারাবে না)
        st.subheader("📋 Permanent Trading Action History")
        if st.session_state.all_trades_history:
            history_df = pd.DataFrame(st.session_state.all_trades_history)
            st.dataframe(history_df.iloc[::-1], height=180, use_container_width=True) # নতুন ডাটা ওপরে দেখাবে
            
            # ⬇️ এক্সেল ও সিএসভি ফাইল জেনারেট এবং ডাউনলোড বাটন
            csv_data = history_df.to_csv(index=False).encode('utf-8')
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    label="📥 Download CSV Logs", data=csv_data,
                    file_name=f"scalper_logs_{time.strftime('%Y%m%d')}.csv", mime='text/csv'
                )
            with col_d2:
                # মেমোরিতে সরাসরি এক্সেল বাটন প্রিপারেশন
                st.info("💡 CSV ফাইলটি ডাউনলোড করে সরাসরি Excel অ্যাপে ওপেন করতে পারবেন।")
        else:
            st.info("ট্রেড শুরু হলে এখানে লাইভ রেকর্ড জমা হতে থাকবে।")

        time.sleep(1)
        st.rerun()
    except:
        time.sleep(1)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। ফিউচার স্ক্যাল্পিং চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
    if st.session_state.all_trades_history:
        st.subheader("📋 Past Session Trading History")
        st.dataframe(pd.DataFrame(st.session_state.all_trades_history).iloc[::-1], use_container_width=True)
