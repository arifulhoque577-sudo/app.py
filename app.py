import streamlit as st
import pandas as pd
import time
from pybit.unified_trading import HTTP

# ১. মোবাইল ও চার্ট স্ক্রিন অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Premium Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    iframe { border: none !important; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Scalper")
st.caption("ভার্সন ৩.৭ | লাইভ ১-১০০$ অর্ডার ও ক্যান্ডেল চার্ট")

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
        
        # 💰 লাইভ ওয়ালেট ব্যালেন্স চেক (Unified & Spot উভয়ই ট্রাই করবে)
        try:
            wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
            member_list = wallet_info.get('result', {}).get('list', [])
            if member_list and 'coin' in member_list[0]:
                coin_list = member_list[0]['coin']
                for c in coin_list:
                    if c.get('coin') == 'USDT':
                        balance_usd = f"${float(c.get('walletBalance', 0)):,.2f}"
                        break
        except:
            balance_usd = "চেক করুন (ডলার স্পট/ইউটিএ-তে রাখুন)"
            
        # 📦 বর্তমান পজিশন চেক
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and float(positions[0].get('size', 0)) > 0:
            position_status = f"LONG 🟢 ({positions[0].get('size')} BTC)"
            st.session_state.in_position = True
        else:
            position_status = "কোনো পজিশন নেই 💤"
            st.session_state.in_position = False
            
    except Exception as e:
        balance_usd = "API কী এরর"
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
            st.session_state.trade_logs.append(f"[SYSTEM] Scalper Activated. Target per trade: ${trade_amount}")
            st.rerun()

# ৫. লাইভ মার্কেট ডাটা ও মোবাইল-ফ্রেন্ডলি TradingView ক্যান্ডেলস্টিক চার্ট
if st.session_state.bot_active and session:
    try:
        response = session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            df['close'] = pd.to_numeric(df['close'])
            live_price = df['close'].iloc[-1]
            
            st.subheader(f"📈 Live BTC/USDT: ${live_price:,.2f}")
            
            # 📊 ১০০% মোবাইল ফ্রেন্ডলি ও লাইটওয়েট ক্যান্ডেলস্টিক চার্ট আইফ্রেম (ফিক্সড)
            chart_html = f"""
            <iframe src="https://tradingview.com" 
                    width="100%" height="320" style="border:none;"></iframe>
            """
            st.components.v1.html(chart_html, height=330)

            # ⚡ স্ক্যাল্পিং RSI অ্যালগরিদম লজিক
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50
            
            # ডলার কস্ট থেকে বিটিসি কোয়ান্টিটি কনভার্ট (যেমন: ১০ ডলার = কত বিটিসি)
            calculated_qty = round((trade_amount / live_price), 4)
            if calculated_qty < 0.0001:
                calculated_qty = 0.0001  # Bybit-এর সর্বনিম্ন অর্ডার সাইজ লিমিট

            # কুইক স্ক্যাল্প বাই/সেল এক্সিকিউশন
            if current_rsi < 35 and not st.session_state.in_position:
                try:
                    order = session.place_order(
                        category="linear", symbol="BTCUSDT", side="Buy", 
                        orderType="Market", qty=str(calculated_qty)
                    )
                    st.session_state.trade_logs.append(f"[🟢 BUY PLACED] Cost: ${trade_amount} | Qty: {calculated_qty} BTC")
                    st.session_state.in_position = True
                except Exception as e:
                    st.session_state.trade_logs.append(f"[❌ Order Fail] চেক করুন ব্যালেন্স স্পট/ইউটিএ অ্যাকাউন্টে আছে কি না।")
            
            elif current_rsi > 65 and st.session_state.in_position:
                try:
                    order = session.place_order(
                        category="linear", symbol="BTCUSDT", side="Sell", 
                        orderType="Market", qty=str(calculated_qty)
                    )
                    st.session_state.trade_logs.append(f"[🔴 SELL PLACED] Position closed for ${trade_amount} worth BTC")
                    st.session_state.in_position = False
                except Exception as e:
                    st.session_state.trade_logs.append(f"[⚠️ Scan Exit] Closing targets scanning...")

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
