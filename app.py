import streamlit as st
import pandas as pd
import numpy as np
import time

# ১. মোবাইল ভিউ অপ্টিমাইজেশন
st.set_page_config(page_title="Crypto Bot UI", page_icon="📱", layout="centered")

# কাস্টম সিএসএস স্টাইল (মোবাইল স্ক্রিনকে সুন্দর করার জন্য)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child {
        background-color: #00cc66; color: white; width: 100%; border-radius: 10px;
    }
    .reportview-container .main .block-container{ max-width: 400px; padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 AI Auto-Trader Mobile")
st.caption("ভার্সন ১.০ | পেপার ট্রেডিং মোড সক্রিয়")

# ২. API কী ইনপুট সেকশন (মোবাইল থেকেই সেট করা যাবে)
with st.sidebar:
    st.header("⚙️ Bot Settings")
    api_key = st.text_input("Binance API Key", type="password", placeholder="এখানে আপনার API Key দিন")
    secret_key = st.text_input("Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    trade_amount = st.number_input("ট্রেড অ্যামাউন্ট ($)", min_value=10, max_value=1000, value=50)

# ৩. লাইভ ব্যালেন্স ও স্ট্যাটাস কার্ড
st.subheader("📊 Live Portfolio")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Total Balance", value="$1,540.20", delta="+$42.10 (Today)")
with col2:
    st.metric(label="Current Status", value="IDLE 💤", delta_color="off")

# ৪. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

if st.session_state.bot_active:
    if st.button("🔴 STOP AUTOMATED TRADING", key="stop_btn"):
        st.session_state.bot_active = False
        st.experimental_rerun()
else:
    if st.button("🟢 START AUTOMATED TRADING", key="start_btn"):
        if not api_key:
            st.error("❌ আগে সাইডবার থেকে API Key সেট করুন!")
        else:
            st.session_state.bot_active = True
            st.experimental_rerun()

# ৫. লাইভ গ্রাফ ও ট্রেড হিস্ট্রি
if st.session_state.bot_active:
    st.success("⚡ বটটি ব্যাকগ্রাউন্ডে মার্কেট এনালাইসিস করছে...")
    
    # লাইভ প্রাইস চার্ট জেনারেট করা
    st.subheader("📈 Live BTC/USDT Chart")
    chart_data = pd.DataFrame(np.random.randn(20, 1) / 50 + 64.2, columns=['Price'])
    st.line_chart(chart_data)
    
    # নকল লাইভ ট্রেড লগ
    st.subheader("📜 Live Action Logs")
    st.text_area("Logs", value="[INFO] Bot started successfully.\n[INFO] Fetching 1h candles for BTC...\n[ANALYSIS] RSI: 48.5 | MACD: Neutral\n[STATUS] Waiting for Moving Average Crossover...", height=100)
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে উপরের বাটনে ক্লিক করুন।")
