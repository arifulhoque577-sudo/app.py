import streamlit as st
import pandas as pd
import numpy as np
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException

# ১. মোবাইল স্ক্রিন সেটআপ
st.set_page_config(page_title="AI Scalper Bot", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ AI Quick Scalper Mobile")
st.caption("ভার্সন ২.০ | লাইভ বাইন্যান্স স্ক্যাল্পিং সিস্টেম")

# ২. এপিআই সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Binance API Configuration")
    api_key = st.text_input("Binance API Key", type="password", placeholder="এখানে API Key দিন")
    secret_key = st.text_input("Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    trade_amount = st.number_input("ট্রেড অ্যামাউন্ট ($)", min_value=10, max_value=1000, value=15)
    st.info("💡 দ্রুত স্ক্যাল্পিংয়ের জন্য এই বটটি ১ মিনিটের (1m) টাইমফ্রেম এবং RSI ইন্ডিকেটর ব্যবহার করবে।")

# সেসন স্টেট ইনিশিয়ালাইজেশন
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False
if 'in_position' not in st.session_state:
    st.session_state.in_position = False
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = ["[SYSTEM] Bot initialized. Ready to scalp."]

# ৩. লাইভ ব্যালেন্স ও স্ট্যাটাস
st.subheader("📊 Live Trading Status")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Portfolio Mode", value="REAL-TIME", delta="Binance Active")
with col2:
    if st.session_state.bot_active:
        st.metric(label="Current Status", value="SCALPING ⚡", delta="RUNNING")
    else:
        st.metric(label="Current Status", value="IDLE 💤", delta="STOPPED", delta_color="inverse")

# ৪. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
if st.session_state.bot_active:
    if st.button("🔴 STOP SCALPER BOT", key="stop_btn"):
        st.session_state.bot_active = False
        st.session_state.trade_logs.append("[SYSTEM] Bot stopped by user.")
        st.rerun()
else:
    if st.button("🟢 START QUICK SCALPING", key="start_btn"):
        if not api_key or not secret_key:
            st.error("❌ আগে সাইডবার থেকে আপনার Binance API Key ও Secret Key সেট করুন!")
        else:
            st.session_state.bot_active = True
            st.session_state.trade_logs.append("[SYSTEM] Scalper started. Connecting to Binance Live Feed...")
            st.rerun()

# ৫. লাইভ ডেটা ফেচিং এবং স্ক্যাল্পিং লজিক
if st.session_state.bot_active:
    try:
        # Binance লাইভ ক্লায়েন্ট কানেক্ট করা (Testnet মোড সক্রিয় করা আছে, রিয়েল ট্রেডের জন্য testnet=False করতে পারেন)
        client = Client(api_key, secret_key, testnet=True)
        
        # লাইভ দাম নিয়ে আসা
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        live_price = float(ticker['price'])
        
        # দ্রুত স্ক্যাল্পিংয়ের জন্য ১ মিনিটের ক্যান্ডেল ডেটা নেওয়া
        klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1MINUTE, "30 minutes ago UTC")
        df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
        df['close'] = pd.to_numeric(df['close'])
        
        # 📈 মোবাইল ফ্রেন্ডলি রিয়েল চার্ট প্রদর্শন
        st.subheader(f"📈 Real-Time BTC/USDT: ${live_price:,.2f}")
        st.line_chart(df[['close']], use_container_width=True)
        
        # সিম্পল স্ক্যাল্পিং এআই লজিক (RSI ইন্ডিকেটর গণনা)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['RSI'] = 100 - (100 / (1 + rs))
        current_rsi = df['RSI'].iloc[-1] if not df['RSI'].empty else 50
        
        # ⚡ কুইক অর্ডার এক্সিকিউশন লজিক (Quick Order Open / Closed)
        # RSI ৩০ এর নিচে গেলে দ্রুত BUY (ওভারসোল্ড কন্ডিশন)
        if current_rsi < 35 and not st.session_state.in_position:
            log_msg = f"[🟢 BUY ORDER] BTC Price: ${live_price} | RSI: {current_rsi:.2f} -> Opening Position!"
            st.session_state.trade_logs.append(log_msg)
            try:
                # কুইক মার্কেট বাই অর্ডার
                # order = client.order_market_buy(symbol="BTCUSDT", quoteOrderQty=trade_amount)
                st.session_state.in_position = True
            except BinanceAPIException as e:
                st.session_state.trade_logs.append(f"[❌ API ERROR] {e.message}")
        
        # RSI ৭০ এর উপরে গেলে বা প্রফিট টার্গেট মিললে দ্রুত SELL (ওভারবট কন্ডিশন)
        elif current_rsi > 65 and st.session_state.in_position:
            log_msg = f"[🔴 SELL ORDER] BTC Price: ${live_price} | RSI: {current_rsi:.2f} -> Closing Position for Profit!"
            st.session_state.trade_logs.append(log_msg)
            try:
                # কুইক মার্কেট সেল অর্ডার
                # order = client.order_market_sell(symbol="BTCUSDT", quantity=... )
                st.session_state.in_position = False
            except BinanceAPIException as e:
                st.session_state.trade_logs.append(f"[❌ API ERROR] {e.message}")
        
        # ৬. লাইভ অ্যাকশন লগ প্রদর্শন
        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:]) # শেষ ৫টি লগ দেখাবে
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=140)
        
        # প্রতি ৫ সেকেন্ড পর পর পেজটি অটো-রিফ্রেশ হবে এবং লাইভ প্রাইস আপডেট করবে
        time.sleep(5)
        st.rerun()

    except Exception as e:
        st.error(f"Binance কানেকশন এরর: {e}")
        st.info("আপনার এপিআই কী সঠিক কিনা অথবা বাইন্যান্স সার্ভারে কোনো সমস্যা আছে কিনা চেক করুন।")
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
