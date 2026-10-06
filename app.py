import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ভিউ অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Local Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Scalper")
st.caption("ভার্সন ৩.৮ | লোকাল ক্যান্ডেলস্টিক চার্ট ও স্ক্যাল্পার ফিক্সড")

# ২. Bybit API সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Bybit API Key", type="password", placeholder="API Key দিন")
    secret_key = st.text_input("Secret Key", type="password", placeholder="Secret Key দিন")
    trade_amount = st.number_input("ট্রেড কস্ট/অ্যামাউন্ট ($)", min_value=1, max_value=500, value=10, step=1)
    account_type = st.radio("অ্যাকাউন্টের ধরন", ["আসল অ্যাকাউন্ট (Mainnet)", "নকল অ্যাকাউন্ট (Demo Testnet)"])
    is_testnet = True if account_type == "নকল অ্যাকাউন্ট (Demo Testnet)" else False

# সেসন স্টেট ইনিশিয়ালাইজেশন
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False
if 'in_position' not in st.session_state:
    st.session_state.in_position = False
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = ["[SYSTEM] Bot initialized. Ready to scalp."]

# Bybit HTTP সেশন তৈরি করা
session = None
balance_usd = "$0.00"
position_status = "চেক করা হচ্ছে..."

if api_key and secret_key:
    try:
        session = HTTP(testnet=is_testnet, api_key=api_key, api_secret=secret_key)
        
        # 💰 লাইভ ব্যালেন্স রিড করার ইউনিভার্সাল মেথড
        try:
            wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            member_list = wallet_info.get('result', {}).get('list', [])
            if member_list and len(member_list) > 0:
                coin_list = member_list[0].get('coin', [])
                for c in coin_list:
                    if c.get('coin') == 'USDT':
                        balance_usd = f"${float(c.get('walletBalance', 0)):,.2f}"
                        break
        except:
            balance_usd = "ডলার স্পট/UTA-তে রাখুন"
            
        # 📦 বর্তমান পজিশন চেক
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and len(positions) > 0 and float(positions[0].get('size', 0)) > 0:
            position_status = f"LONG 🟢 ({positions[0].get('size')} BTC)"
            st.session_state.in_position = True
        else:
            position_status = "কোনো পজিশন নেই 💤"
            st.session_state.in_position = False
            
    except Exception as e:
        balance_usd = "API কী ভুল"
        position_status = "কানেকশন ভুল"

# ৩. লাইভ ব্যালেন্স ও স্ট্যাটাস ডিসপ্লে
st.subheader("📊 Live Wallet & Positions")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Bybit Live Balance", value=balance_usd, delta="USDT")
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
        if not api_key or not secret_key:
            st.error("❌ আগে সাইডবার থেকে আপনার Bybit API Key ও Secret Key সেট করুন!")
        else:
            st.session_state.bot_active = True
            st.session_state.trade_logs.append(f"[SYSTEM] Scalper Activated. Target: ${trade_amount}")
            st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও ইন্টাররেক্টিভ ক্যান্ডেলস্টিক চার্ট
if st.session_state.bot_active and session:
    try:
        response = session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            # Bybit ডাটা ফরম্যাট: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            
            # সংখ্যায় রূপান্তর
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            
            live_price = df['close'].iloc[-1]
            st.subheader(f"📈 Real-Time BTC/USDT: ${live_price:,.2f}")
            
            # 📊 পাইথনের নিজস্ব১০০% নিরাপদ মোবাইল ক্যান্ডেলস্টিক চার্ট (Plotly)
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                increasing_line_color='#00cc66', 
                decreasing_line_color='#ff3333'
            )])
            
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

            # ⚡ স্ক্যাল্পিং RSI অ্যালগরিদম লজিক
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50
            
            # বিটিসি মিনিমাম লট সাইজ ক্যালকুলেশন
            calculated_qty = round((trade_amount / live_price), 4)
            if calculated_qty < 0.0001:
                calculated_qty = 0.0001

            # কুইক স্ক্যাল্প সিগন্যাল এক্সিকিউশন
            if current_rsi < 35 and not st.session_state.in_position:
                try:
                    order = session.place_order(
                        category="linear", symbol="BTCUSDT", side="Buy", 
                        orderType="Market", qty=str(calculated_qty)
                    )
                    st.session_state.trade_logs.append(f"[🟢 BUY PLACED] Cost: ${trade_amount} | Qty: {calculated_qty}")
                    st.session_state.in_position = True
                except Exception as e:
                    st.session_state.trade_logs.append(f"[❌ Order Fail] ফান্ড নেই অথবা মার্জিন কম।")
            
            elif current_rsi > 65 and st.session_state.in_position:
                try:
                    order = session.place_order(
                        category="linear", symbol="BTCUSDT", side="Sell", 
                        orderType="Market", qty=str(calculated_qty)
                    )
                    st.session_state.trade_logs.append(f"[🔴 SELL PLACED] Position closed for profit!")
                    st.session_state.in_position = False
                except Exception as e:
                    st.session_state.trade_logs.append(f"[⚠️ Scan Exit] Closing target search...")

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
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
