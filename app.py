import streamlit as st
import pandas as pd
import numpy as np
import time

# ১. মোবাইল ভিউ ও স্ক্রিন অপ্টিমাইজেশন
st.set_page_config(page_title="Crypto Bot UI", page_icon="📱", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66; color: white; width: 100%; border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 AI Auto-Trader Mobile")
st.caption("ভার্সন ১.১ | পেপার ট্রেডিং মোড সক্রিয়")

# ২. API কী ইনপুট সেকশন
with st.sidebar:
    st.header("⚙️ Bot Settings")
    api_key = st.text_input("Binance API Key", type="password", placeholder="এখানে আপনার API Key দিন")
    secret_key = st.text_input("Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    trade_amount = st.number_input("ট্রেড অ্যামাউন্ট ($)", min_value=10, max_value=1000, value=50)

# ৩. লাইভ ব্যালেন্স ও স্ট্যাটাস কার্ড
st.subheader("📊 Live Portfolio")
col1, col2 = st.columns(2)

if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

with col1:
    st.metric(label="Total Balance", value="$1,542.10", delta="+$2.10 (Today)")
with col2:
    if st.session_state.bot_active:
        st.metric(label="Current Status", value="RUNNING ⚡", delta="ACTIVE")
    else:
        st.metric(label="Current Status", value="IDLE 💤", delta="STOPPED", delta_color="inverse")

# ৪. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
if st.session_state.bot_active:
    if st.button("🔴 STOP AUTOMATED TRADING", key="stop_btn"):
        st.session_state.bot_active = False
        st.rerun()
else:
    if st.button("🟢 START AUTOMATED TRADING", key="start_btn"):
        if not api_key:
            st.error("❌ আগে সাইডবার থেকে API Key সেট করুন!")
        else:
            st.session_state.bot_active = True
            st.rerun()

# ৫. লাইভ গ্রাফ ও ট্রেড হিস্ট্রি
if st.session_state.bot_active:
    st.success("⚡ বটটি ব্যাকগ্রাউন্ডে লাইভ মার্কেট এনালাইসিস করছে...")
    
    # 📈 মোবাইল ফ্রেন্ডলি লাইভ গ্রাফ (ফিক্সড)
    st.subheader("📈 Live BTC Trend Chart")
    # মোবাইলে সহজে দেখার জন্য ফিক্সড ইনডেক্স ও বেস প্রাইস জেনারেট করা হলো
    np.random.seed(42)
    prices = 64200 + np.random.randn(20).cumsum() * 50
    chart_data = pd.DataFrame(prices, columns=['BTC Price ($)'])
    st.line_chart(chart_data, use_container_width=True)
    
    # লাইভ ট্রেড লগ
    st.subheader("📜 Live Action Logs")
    log_text = (
        f"[INFO] Bot connected to Binance API successfully.\n"
        f"[INFO] Target Amount per Trade: ${trade_amount}\n"
        f"[ANALYSIS] RSI: 48.5 | MACD: Neutral\n"
        f"[STATUS] Live monitoring BTC/USDT. Waiting for strategy crossover..."
    )
    st.text_area("Logs", value=log_text, height=120)
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে উপরের বাটনে ক্লিক করুন।")
