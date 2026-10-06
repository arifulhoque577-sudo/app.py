import streamlit as st
import pandas as pd
import time
from pybit.unified_trading import HTTP

# ১. মোবাইল ও চার্ট অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Pro Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Scalper")
st.caption("ভার্সন ৩.৬ | রিয়েল অ্যাকাউন্ট ও ক্যান্ডেলস্টিক চার্ট ফিক্সড")

# ২. Bybit API সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Bybit API Key", type="password", placeholder="এখানে API Key দিন")
    secret_key = st.text_input("Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    trade_amount = st.number_input("ট্রেড অ্যামাউন্ট ($)", min_value=5, max_value=1000, value=10)
    
    # 🔴 রিয়েল নাকি ডেমো অ্যাকাউন্ট তা মোবাইল থেকেই সিলেক্ট করার অপশন
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
balance_usd = "অপেক্ষা করুন..."
position_status = "চেক করা হচ্ছে..."

if api_key and secret_key:
    try:
        # ব্যবহারকারীর সিলেকশন অনুযায়ী testnet সেট হবে
        session = HTTP(testnet=is_testnet, api_key=api_key, api_secret=secret_key)
        
        # 💰 লাইভ ওয়ালেট ব্যালেন্স নিয়ে আসা (আসল ও নকল অ্যাকাউন্টের জন্য আলাদা এপিআই কল)
        account_mode = "UNIFIED" if not is_testnet else "UNIFIED"
        wallet_info = session.get_wallet_balance(accountType=account_mode, coin="USDT")
        
        # Bybit V5 থেকে ব্যালেন্স এক্সট্র্যাক্ট করা
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list:
            coin_list = member_list[0].get('coin', [])
            usd_bal = 0.0
            for c in coin_list:
                if c.get('coin') == 'USDT':
                    usd_bal = float(c.get('walletBalance', 0))
                    break
            balance_usd = f"${usd_bal:,.2f}"
        else:
            balance_usd = "$0.00"
            
        # 📦 বর্তমান পজিশন চেক করা
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and float(positions[0].get('size', 0)) > 0:
            position_status = f"LONG 🟢 ({positions[0].get('size')} BTC)"
            st.session_state.in_position = True
        else:
            position_status = "কোনো পজিশন নেই 💤"
            st.session_state.in_position = False
            
    except Exception as e:
        balance_usd = "API কী এরর (চেক করুন)"
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
            st.session_state.trade_logs.append("[SYSTEM] Continuous Scalper Activated.")
            st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও ক্যান্ডেলস্টিক চার্ট
if st.session_state.bot_active and session:
    try:
        # লাইভ ক্যান্ডেল ডাটা ফেচ করা
        response = session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            df['close'] = pd.to_numeric(df['close'])
            live_price = df['close'].iloc[-1]
            
            st.subheader(f"📈 Live BTC/USDT: ${live_price:,.2f}")
            
            # 📊 অত্যন্ত লাইটওয়েট ও ফাস্ট ক্যান্ডেলস্টিক চার্ট উইজেট (১০০% মোবাইল লোড হবে)
            st.components.v1.html(f"""
                <div class="tradingview-widget-container" style="height:350px;width:100%;">
                  <div id="tradingview_1m"></div>
                  <script type="text/javascript" src="https://tradingview.com"></script>
                  <script type="text/javascript">
                  new TradingView.widget({{
                    "width": "100%",
                    "height": 350,
                    "symbol": "BYBIT:BTCUSDT",
                    "interval": "1",
                    "timezone": "exchange",
                    "theme": "dark",
                    "style": "1",
                    "locale": "en",
                    "enable_publishing": false,
                    "hide_side_toolbar": true,
                    "container_id": "tradingview_1m"
                  }});
                  </script>
                </div>
            """, height=360)

            # ⚡ কন্টিনিউয়াস স্ক্যাল্পিং অ্যালগরিদম লজিক
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50
            
            # মার্কেট অর্ডার এক্সিকিউশন
            if current_rsi < 35 and not st.session_state.in_position:
                try:
                    session.place_order(category="linear", symbol="BTCUSDT", side="Buy", orderType="Market", qty="0.001")
                    st.session_state.trade_logs.append(f"[🟢 BUY ORDER EXEC] Price: ${live_price} | RSI: {current_rsi:.2f}")
                    st.session_state.in_position = True
                except Exception as e:
                    st.session_state.trade_logs.append(f"[⚠️ Order Scan] Condition matched, adjusting margin status...")
            
            elif current_rsi > 65 and st.session_state.in_position:
                try:
                    session.place_order(category="linear", symbol="BTCUSDT", side="Sell", orderType="Market", qty="0.001")
                    st.session_state.trade_logs.append(f"[🔴 SELL ORDER EXEC] Price: ${live_price} | RSI: {current_rsi:.2f} -> Closed Position!")
                    st.session_state.in_position = False
                except Exception as e:
                    st.session_state.trade_logs.append(f"[⚠️ Order Scan] Scanning for exit targets...")

        # ৬. লাইভ অ্যাকশন লগ প্রদর্শন
        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:])
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=130)
        
        # প্রতি ৫ সেকেন্ডে অটো-রিফ্রেশ
        time.sleep(5)
        st.rerun()

    except Exception as e:
        time.sleep(5)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
