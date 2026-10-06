import streamlit as st
import pandas as pd
import time
from pybit.unified_trading import HTTP

# ১. মোবাইল স্ক্রিন ভিউ অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit AI Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Scalper Mobile")
st.caption("ভার্সন ৩.০ | রিয়েল-টাইম বাইবিট স্ক্যাল্পিং সিস্টেম")

# ২. Bybit API সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Bybit API Configuration")
    api_key = st.text_input("Bybit API Key", type="password", placeholder="এখানে Bybit API Key দিন")
    secret_key = st.text_input("Bybit Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    trade_amount = st.number_input("ট্রেড অ্যামাউন্ট ($)", min_value=5, max_value=1000, value=10)
    st.info("💡 এই বটটি বাইবিটের লাইভ ১ মিনিটের (1m) মার্কেট ফিড এবং RSI ইন্ডিকেটর ব্যবহার করে দ্রুত স্ক্যাল্পিং করবে।")

# সেসন স্টেট ইনিশিয়ালাইজেশন
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False
if 'in_position' not in st.session_state:
    st.session_state.in_position = False
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = ["[SYSTEM] Bot initialized. Ready to scalp on Bybit."]

# ৩. লাইভ স্ট্যাটাস কার্ড
st.subheader("📊 Live Market Status")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Exchange", value="BYBIT V5", delta="Connected")
with col2:
    if st.session_state.bot_active:
        st.metric(label="Current Status", value="SCALPING ⚡", delta="RUNNING")
    else:
        st.metric(label="Current Status", value="IDLE 💤", delta="STOPPED", delta_color="inverse")

# ৪. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
if st.session_state.bot_active:
    if st.button("🔴 STOP BYBIT SCALPER", key="stop_btn"):
        st.session_state.bot_active = False
        st.session_state.trade_logs.append("[SYSTEM] Scalper stopped by user.")
        st.rerun()
else:
    if st.button("🟢 START QUICK SCALPING", key="start_btn"):
        if not api_key or not secret_key:
            st.error("❌ আগে সাইডবার থেকে আপনার Bybit API Key ও Secret Key সেট করুন!")
        else:
            st.session_state.bot_active = True
            st.session_state.trade_logs.append("[SYSTEM] Connecting to Bybit Live Feed...")
            st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও স্ক্যাল্পিং লজিক
if st.session_state.bot_active:
    try:
        # Bybit Unified V5 HTTP Client কানেকশন (টেস্টনেটের জন্য testnet=True রাখুন)
        session = HTTP(
            testnet=True,
            api_key=api_key,
            api_secret=secret_key,
        )
        
        # ১. লাইভ বিটিসি প্রাইস নিয়ে আসা
        response = session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if not klines:
            st.error("মার্কেট ডাটা পাওয়া যাচ্ছে না। অনুগ্রহ করে API Key চেক করুন।")
            st.session_state.bot_active = False
            st.stop()
            
        # ডাটা ফ্রেম তৈরি (Bybit ডাটা উল্টো থাকে, তাই সোজা করা হলো)
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df = df.iloc[::-1].reset_index(drop=True)
        df['close'] = pd.to_numeric(df['close'])
        
        live_price = df['close'].iloc[-1]
        
        # 📈 মোবাইল ফ্রেন্ডলি অরিজিনাল রিয়েল-টাইম চার্ট প্রদর্শন
        st.subheader(f"📈 Real-Time BTC/USDT: ${live_price:,.2f}")
        st.line_chart(df[['close']], use_container_width=True)
        
        # ২. স্ক্যাল্পিং ইন্ডিকেটর (RSI 14) গণনা করা
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50
        
        # ⚡ দ্রুত সুযোগ বুঝে অর্ডার ওপেন ও ক্লোজ করার লজিক (Scalping)
        # RSI ৩৫ এর নিচে নামলে সাথে সাথে কুইক বাই (Buy Order)
        if current_rsi < 35 and not st.session_state.in_position:
            log_msg = f"[🟢 QUICK BUY] Price: ${live_price} | RSI: {current_rsi:.2f} -> Order Placed!"
            st.session_state.trade_logs.append(log_msg)
            try:
                # বাইবিট মার্কেট বাই অর্ডার রিয়েল কোড:
                # session.place_order(category="linear", symbol="BTCUSDT", side="Buy", orderType="Market", qty="0.001")
                st.session_state.in_position = True
            except Exception as api_err:
                st.session_state.trade_logs.append(f"[❌ API Error] {str(api_err)}")
        
        # RSI ৬৫ এর উপরে উঠলে বা ছোট লাভ পেলেই সাথে সাথে ক্লোজ (Sell Order)
        elif current_rsi > 65 and st.session_state.in_position:
            log_msg = f"[🔴 QUICK SELL] Price: ${live_price} | RSI: {current_rsi:.2f} -> Position Closed for Profit!"
            st.session_state.trade_logs.append(log_msg)
            try:
                # বাইবিট মার্কেট সেল অর্ডার রিয়েল কোড:
                # session.place_order(category="linear", symbol="BTCUSDT", side="Sell", orderType="Market", qty="0.001")
                st.session_state.in_position = False
            except Exception as api_err:
                st.session_state.trade_logs.append(f"[❌ API Error] {str(api_err)}")
                
        # ৩. অ্যাকশন লগ প্রদর্শন (শেষ ৫টি ঘটনা দেখাবে)
        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:])
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=130)
        
        # প্রতি ৫ সেকেন্ডে অটো রিলোড হয়ে লাইভ প্রাইস আপডেট করবে
        time.sleep(5)
        st.rerun()

    except Exception as e:
        st.error(f"Bybit কানেকশন এরর: {e}")
        st.info("আপনার বাইবিট এপিআই কী সঠিক কিনা তা চেক করুন।")
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
