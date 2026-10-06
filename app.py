import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit Hybrid Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Scalper")
st.caption("ভার্সন ৫.০ | কন্টিনিউয়াস ডুয়াল-মোড আল্ট্রা স্ক্যাল্পার")

# ২. ডাইনামিক সাইডবার সেটিংস (Real + Fake Switch)
with st.sidebar:
    st.header("⚙️ System Configuration")
    
    # 🔁 রিয়েল নাকি ডেমো তা সিলেক্ট করার ডুয়াল সুইচ
    bot_mode = st.radio("ট্রেডিং মোড সিলেক্ট করুন:", ["Demo Mode (ফ্রি ৫,০০০$ ফেইক ফান্ড)", "Live Mode (আসল Bybit API অ্যাকাউন্ট)"])
    is_real_live = True if bot_mode == "Live Mode (আসল Bybit API অ্যাকাউন্ট)" else False
    
    trade_amount = st.number_input("প্রতি ট্রেডের কস্ট/সাইজ ($)", min_value=1, max_value=500, value=10, step=1)
    
    # লাইভ মোড সিলেক্ট করলেই কেবল এপিআই বক্স দেখাবে
    api_key = ""
    secret_key = ""
    if is_real_live:
        api_key = st.text_input("Bybit API Key", type="password", placeholder="এখানে API Key দিন")
        secret_key = st.text_input("Secret Key", type="password", placeholder="এখানে Secret Key দিন")
    else:
        st.success("💡 ডেমো মোড সক্রিয়। কোনো Bybit API Key লাগবে না।")

# সেসন স্টেট ইনিশিয়ালাইজেশন (ফ্রি ৫০০০ ডলার ব্যাকআপ)
if 'demo_balance' not in st.session_state:
    st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False
if 'in_position' not in st.session_state:
    st.session_state.in_position = False
if 'buy_price' not in st.session_state:
    st.session_state.buy_price = 0.0
if 'trade_logs' not in st.session_state:
    st.session_state.trade_logs = ["[SYSTEM] Bot framework successfully initialized."]

# ব্যালেন্স ও পজিশন ডেটা প্রিপারেশন
balance_usd = f"${st.session_state.demo_balance:,.2f}" if not is_real_live else "$0.00"
position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else "LONG 🟢 (ট্রেড রানিং)"

# ৩. এপিআই লাইভ ব্যালেন্স রিডার লজিক
session = None
if is_real_live and api_key and secret_key:
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list and len(member_list) > 0:
            coin_list = member_list[0].get('coin', [])
            for c in coin_list:
                if c.get('coin') == 'USDT':
                    balance_usd = f"${float(c.get('walletBalance', 0)):,.2f}"
                    break
        
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and len(positions) > 0 and float(positions[0].get('size', 0)) > 0:
            position_status = f"LONG 🟢 ({positions[0].get('size')} BTC)"
            st.session_state.in_position = True
    except:
        balance_usd = "API কী চেক করুন"
        position_status = "কানেকশন ভুল"

# ৪. ডিসপ্লে ওয়ালেট ইনফো
st.subheader(f"📊 {bot_mode} Wallet Status")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Available Funds", value=balance_usd, delta="USDT Balance")
with col2:
    st.metric(label="Active Position", value=position_status)

# ৫. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
if st.session_state.bot_active:
    if st.button("🔴 STOP SCALPER BOT", key="stop_btn"):
        st.session_state.bot_active = False
        st.session_state.trade_logs.append(f"[SYSTEM] Bot stopped in {bot_mode}.")
        st.rerun()
else:
    if st.button("🟢 START QUICK SCALPING", key="start_btn"):
        if is_real_live and (not api_key or not secret_key):
            st.error("❌ লাইভ মোড চালানোর আগে সাইডবারে Bybit API কী দুটি বসিয়ে নিন!")
        else:
            st.session_state.bot_active = True
            st.session_state.trade_logs.append(f"[SYSTEM] Active Continuous Scalper in {bot_mode}.")
            st.rerun()

# ৬. লাইভ ক্যান্ডেল চার্ট ও অনবরত কুইক স্ক্যাল্পিং লজিক
if st.session_state.bot_active:
    try:
        # মার্কেট ডাটা নেওয়ার জন্য পাবলিক সেশন
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
            st.subheader(f"📈 Live BTC/USDT Rate: ${live_price:,.2f}")
            
            # 📊 প্রফেশনাল লোকাল ক্যান্ডেল চার্ট প্রদর্শন
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                increasing_line_color='#00cc66', decreasing_line_color='#ff3333'
            )])
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False, template="plotly_dark", height=260
            )
            st.plotly_chart(fig, use_container_width=True)

            # ⚡ কন্টিনিউয়াস আল্ট্রা-ফাস্ট স্ক্যাল্পিং অ্যালগরিদম (অনবরত ট্রেড লুপ)
            calculated_qty = round((trade_amount / live_price), 4)
            if calculated_qty < 0.0001:
                calculated_qty = 0.0001

            # কন্ডিশন ১: পজিশন খালি থাকলে সাথে সাথে ইনস্ট্যান্ট কুইক বাই (Quick Buy Entry)
            if not st.session_state.in_position:
                st.session_state.buy_price = live_price
                st.session_state.in_position = True
                
                if is_real_live and session:
                    try:
                        session.place_order(category="linear", symbol="BTCUSDT", side="Buy", orderType="Market", qty=str(calculated_qty))
                        st.session_state.trade_logs.append(f"[🟢 REAL BUY] Price: ${live_price} | Cost: ${trade_amount}")
                    except Exception as err:
                        st.session_state.trade_logs.append(f"[❌ API Order Reject] ফান্ড/মার্জিন কম বা এপিআই পারমিশন এরর।")
                        st.session_state.in_position = False
                else:
                    st.session_state.trade_logs.append(f"[🟢 SIMULATED BUY] Price: ${live_price} | Size: ${trade_amount}")
                st.rerun()
            
            # কন্ডিশন ২: পজিশন নেওয়া থাকলে ক্ষুদ্র প্রফিট (০.১৫%) পেলেই সাথে সাথে কুইক সেল (Quick Profit Exit)
            elif st.session_state.in_position:
                target_profit_price = st.session_state.buy_price * 1.0015  # মাত্র 0.15% লাভের টার্গেট
                
                # যদি দাম টার্গেটে পৌঁছায় অথবা মার্কেট রিভার্স করে
                if live_price >= target_profit_price or live_price < (st.session_state.buy_price * 0.995):
                    profit_loss = (live_price - st.session_state.buy_price) * (trade_amount / st.session_state.buy_price)
                    
                    if is_real_live and session:
                        try:
                            session.place_order(category="linear", symbol="BTCUSDT", side="Sell", orderType="Market", qty=str(calculated_qty))
                            st.session_state.trade_logs.append(f"[🔴 REAL SELL CLOSED] Price: ${live_price}")
                            st.session_state.in_position = False
                        except Exception as err:
                            st.session_state.trade_logs.append(f"[⚠️ Live Exit Scan] Closing target error...")
                    else:
                        st.session_state.demo_balance += profit_loss
                        st.session_state.in_position = False
                        sign = "+" if profit_loss >= 0 else ""
                        st.session_state.trade_logs.append(f"[🔴 SIMULATED SELL] Price: ${live_price} | P&L: {sign}${profit_loss:.2f}")
                    st.rerun()
                else:
                    # যদি টার্গেট হিট না হয়, তবে লগে স্ক্যানিং মেসেজ আপডেট হবে
                    st.session_state.trade_logs.append(f"[🔎 Monitoring Position] Buy: ${st.session_state.buy_price} | Current: ${live_price} | Target: ${target_profit_price:.2f}")

        # ৭. অ্যাকশন লগ প্রদর্শন (শেষ ৫টি লগ দেখাবে)
        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:])
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=130)
        
        # দ্রুত স্ক্যাল্পিংয়ের জন্য প্রতি ৪-৫ সেকেন্ড পর পর লুপ ঘুরবে
        time.sleep(4)
        st.rerun()

    except Exception as e:
        time.sleep(4)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। স্ক্যাল্পিং চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
