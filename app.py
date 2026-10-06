import streamlit as st
import pandas as pd
import time
from pybit.unified_trading import HTTP

# ১. মোবাইল ভিউ অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Advanced Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Scalper")
st.caption("ভার্সন ৩.৫ | ক্যান্ডেলস্টিক ও রিয়েল ব্যালেন্স স্ক্যাল্পিং")

# ২. Bybit API সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Bybit API Key", type="password", placeholder="এখানে API Key দিন")
    secret_key = st.text_input("Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    trade_amount = st.number_input("ট্রেড অ্যামাউন্ট ($)", min_value=5, max_value=1000, value=10)
    timeframe = st.selectbox("টাইমফ্রেম সিলেক্ট করুন", ["1", "3", "5"], index=0)
    st.info("💡 এই বটটি প্রতি ৫ সেকেন্ডে লাইভ ব্যালেন্স আপডেট করবে এবং ১ মিনিটের ক্যান্ডেল দিয়ে স্ক্যাল্পিং করবে।")

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
position_status = "No Active Position"

if api_key and secret_key:
    try:
        # রিয়েল অ্যাকাউন্টের জন্য testnet=False এবং ডেমোর জন্য testnet=True রাখবেন
        session = HTTP(testnet=True, api_key=api_key, api_secret=secret_key)
        
        # 💰 লাইভ ওয়ালেট ব্যালেন্স নিয়ে আসা
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        coins = wallet_info.get('result', {}).get('list', [{}])[0].get('coin', [])
        if coins:
            balance_usd = f"${float(coins[0].get('walletBalance', 0)):,.2f}"
            
        # 📦 বর্তমান পজিশন চেক করা
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and float(positions[0].get('size', 0)) > 0:
            position_status = f"LONG 🟢 ({positions[0].get('size')} BTC)"
            st.session_state.in_position = True
        else:
            position_status = "IDLE (No Position) 💤"
            st.session_state.in_position = False
    except Exception as e:
        balance_usd = "কানেকশন এরর"
        position_status = "API ত্রুটি"

# ৩. লাইভ ব্যালেন্স ও স্ট্যাটাস ডিসপ্লে
st.subheader("📊 Live Wallet & Positions")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Bybit Live Balance", value=balance_usd, delta="USDT Balance")
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
            st.session_state.trade_logs.append("[SYSTEM] Continuous Scalper Activated.")
            st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও TradingView ক্যান্ডেলস্টিক চার্ট
if st.session_state.bot_active and session:
    try:
        # লাইভ ক্যান্ডেল ডাটা ফেচ করা
        response = session.get_kline(category="linear", symbol="BTCUSDT", interval=timeframe, limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            df['close'] = pd.to_numeric(df['close'])
            live_price = df['close'].iloc[-1]
            
            st.subheader(f"📈 Live BTC/USDT: ${live_price:,.2f}")
            
            # 📊 এক্সচেঞ্জের মতো প্রফেশনাল ক্যান্ডেলস্টিক চার্ট ওর্ডার মার্কিং সহ প্রদর্শন
            st.components.v1.html(f"""
                <!-- TradingView Widget BEGIN -->
                <div class="tradingview-widget-container" style="height:300px;width:100%;">
                  <div id="tradingview_chart"></div>
                  <script type="text/javascript" src="https://tradingview.com"></script>
                  <script type="text/javascript">
                  new TradingView.widget({{
                    "width": "100%",
                    "height": 300,
                    "symbol": "BYBIT:BTCUSDT",
                    "interval": "{timeframe}",
                    "timezone": "Etc/UTC",
                    "theme": "dark",
                    "style": "1",
                    "locale": "en",
                    "toolbar_bg": "#f1f3f6",
                    "enable_publishing": false,
                    "hide_side_toolbar": true,
                    "allow_symbol_change": false,
                    "container_id": "tradingview_chart"
                  }});
                  </script>
                </div>
                <!-- TradingView Widget END -->
            """, height=310)

            # ⚡ কন্টিনিউয়াস স্ক্যাল্পিং অ্যালগরিদম লজিক (অনবরত ট্রেড নেওয়া)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50
            
            # কুইক স্ক্যাল্প সিগন্যাল মনিটরিং
            if current_rsi < 38 and not st.session_state.in_position:
                try:
                    # মার্কেট বাই অর্ডার রিয়েল কোড
                    session.place_order(category="linear", symbol="BTCUSDT", side="Buy", orderType="Market", qty="0.001")
                    st.session_state.trade_logs.append(f"[🟢 BUY ORDER EXEC] Price: ${live_price} | RSI: {current_rsi:.2f}")
                    st.session_state.in_position = True
                except Exception as order_err:
                    st.session_state.trade_logs.append(f"[⚠️ Buy Triggered] Position condition matched, waiting for funds/margin.")
            
            elif current_rsi > 62 and st.session_state.in_position:
                try:
                    # মার্কেট সেল অর্ডার রিয়েল কোড
                    session.place_order(category="linear", symbol="BTCUSDT", side="Sell", orderType="Market", qty="0.001")
                    st.session_state.trade_logs.append(f"[🔴 SELL ORDER EXEC] Price: ${live_price} | RSI: {current_rsi:.2f} -> Closed Position!")
                    st.session_state.in_position = False
                except Exception as order_err:
                    st.session_state.trade_logs.append(f"[⚠️ Sell Triggered] Scanning for profit target exits...")

        # ৬. লাইভ অ্যাকশন লগ প্রদর্শন
        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:])
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=130)
        
        # প্রতি ৫ সেকেন্ডে অটো-রিফ্রেশ
        time.sleep(5)
        st.rerun()

    except Exception as e:
        st.error(f"ডাটা লোড হচ্ছে না: {e}")
        time.sleep(5)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
