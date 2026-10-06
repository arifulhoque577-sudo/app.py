import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ভিউ অপ্টিমাইজেশন
st.set_page_config(page_title="AI Scalper Simulator", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ AI Pro Scalper Simulator")
st.caption("ভার্সন ৪.৫ | ইন-বিল্ট ফ্রি ৫,০০০$ ডেমো ফান্ড মোড")

# ২. ডেমো সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Simulator Settings")
    trade_amount = st.number_input("প্রতি ট্রেডের সাইজ ($)", min_value=1, max_value=500, value=50, step=1)
    st.success("💡 এই মোডে কোনো Bybit API Key লাগবে না। সরাসরি ফেইক ডলার দিয়ে টেস্ট শুরু হবে।")

# সেসন স্টেট ইনিশিয়ালাইজেশন (ফ্রি ৫০০০ ডলার সেট করা হলো)
if 'demo_balance' not in st.session_state:
    st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False
if 'in_position' not in st.session_state:
    st.session_state.in_position = False
if 'buy_price' not in st.session_state:
    st.session_state.buy_price = 0.0
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = ["[SYSTEM] Bot initialized with $5,000 Free Demo Fund."]

position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"LONG 🟢 (ট্রেডে আছে)"

# ৩. ডেমো ব্যালেন্স ও স্ট্যাটাস ডিসপ্লে
st.subheader("📊 Virtual Wallet & Positions")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Demo Wallet Balance", value=f"${st.session_state.demo_balance:,.2f}", delta="USDT (Fake Fund)")
with col2:
    st.metric(label="Active Position", value=position_status)

# ৪. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
if st.session_state.bot_active:
    if st.button("🔴 STOP SCALPER BOT", key="stop_btn"):
        st.session_state.bot_active = False
        st.session_state.trade_logs.append("[SYSTEM] Scalper stopped by user.")
        st.rerun()
else:
    if st.button("🟢 START QUICK SCALPING", key="start_btn"):
        st.session_state.bot_active = True
        st.session_state.trade_logs.append(f"[SYSTEM] Scalper Activated with ${trade_amount} per order.")
        st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও ইন্টাররেক্টিভ ক্যান্ডেলস্টিক চার্ট
if st.session_state.bot_active:
    try:
        # কোনো পাবলিক এপিআই কী ছাড়াই লাইভ মার্কেট ডাটা নেওয়ার জন্য বাইবিট পাবলিক ক্লায়েন্ট
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            
            live_price = df['close'].iloc[-1]
            st.subheader(f"📈 Real-Time BTC/USDT: ${live_price:,.2f}")
            
            # 📊 লোকাল ক্যান্ডেলস্টিক চার্ট (Plotly)
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                increasing_line_color='#00cc66', decreasing_line_color='#ff3333'
            )])
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False, template="plotly_dark", height=280
            )
            st.plotly_chart(fig, use_container_width=True)

            # ⚡ স্ক্যাল্পিং RSI অ্যালগরিদম লজিক
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50
            
            # ডেমো স্ক্যাল্প অর্ডার লজিক এক্সিকিউশন
            if current_rsi < 35 and not st.session_state.in_position:
                st.session_state.buy_price = live_price
                st.session_state.in_position = True
                st.session_state.trade_logs.append(f"[🟢 DEMO BUY ORDER] Price: ${live_price} | RSI: {current_rsi:.2f}")
                st.rerun()
            
            elif current_rsi > 65 and st.session_state.in_position:
                # লাভ বা লস হিসাব করা
                profit_loss = (live_price - st.session_state.buy_price) * (trade_amount / st.session_state.buy_price)
                st.session_state.demo_balance += profit_loss
                st.session_state.in_position = False
                
                sign = "+" if profit_loss >= 0 else ""
                st.session_state.trade_logs.append(f"[🔴 DEMO SELL ORDER] Price: ${live_price} | P&L: {sign}${profit_loss:.2f}")
                st.rerun()

        # ৬. লগ প্রদর্শন
        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:])
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=130)
        
        time.sleep(5)
        st.rerun()

    except Exception as e:
        time.sleep(5)
        st.rerun()
else:
    st.info("সিমুলেটরটি বর্তমানে বন্ধ আছে। টেস্ট করার জন্য ওপরের সবুজ বাটনে ক্লিক করুন।")
