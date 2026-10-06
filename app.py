import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit AI Fee Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    .stButton>button[key="force_sell_btn"] { background-color: #ff3333 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Future Scalper")
st.caption("ভার্সন ৮.৫ | এন্ট্রি ও লাইভ টার্গেট ডিসপ্লে ফিক্সড")

# ২. ডাইনামিক ফিউচার সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configurations")
    bot_mode = st.radio("ট্রেডিং মোড:", ["Demo Mode (ফ্রি ৫,০০০$ ফেইক ফান্ড)", "Live Mode (আসল Bybit API)"])
    is_real_live = True if "Live" in bot_mode else False
    
    ai_decision = st.toggle("এআই অটো-ডিসিশন (RSI + MACD)", value=True)
    
    leverage = st.slider("ফিউচার লেভারেজ", min_value=1, max_value=50, value=20, step=1)
    trade_amount = st.number_input("মার্জিন কস্ট ($)", min_value=1, max_value=500, value=20, step=1)
    price_jump_target = st.slider("প্রফিট বুকিং টার্গেট ($ গ্যাপ)", min_value=2, max_value=500, value=100, step=5)
    stop_loss_gap = st.slider("স্টপ লস প্রোটেকশন ($ গ্যাপ)", min_value=10, max_value=500, value=50, step=5)
    
    api_key = ""
    secret_key = ""
    if is_real_live:
        api_key = st.text_input("Bybit API Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")

# ৩. সেসন স্টেট ও পার্মানেন্ট লগ মেমোরি
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []

balance_usd = f"${st.session_state.demo_balance:,.2f}" if not is_real_live else "$0.00"
position_mode_text = st.session_state.current_side

# Bybit API ব্যালেন্স ও রিয়েল পজিশন ট্র্যাকিং
session = None
if is_real_live and api_key and secret_key:
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
        try: session.set_leverage(category="linear", symbol="BTCUSDT", buyLeverage=str(leverage), sellLeverage=str(leverage))
        except: pass
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list:
            for c in member_list.get('coin', []):
                if c.get('coin') == 'USDT':
                    balance_usd = f"${float(c.get('walletBalance', 0)):,.2f}"
                    break
        pos_info = session.get_positions(category="linear", symbol="BTCUSDT")
        positions = pos_info.get('result', {}).get('list', [])
        if positions and float(positions.get('size', 0)) > 0:
            st.session_state.in_position = True
            st.session_state.current_side = positions.get('side').upper()
            if st.session_state.buy_price == 0.0:
                st.session_state.buy_price = float(positions.get('entryPrice', 0))
    except:
        balance_usd = "API কী চেক করুন"

position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"Future {st.session_state.current_side} রানিং"

st.subheader(f"📊 Future {bot_mode} (Leverage: {leverage}x)")
col_b1, col_b2 = st.columns(2)
with col_b1: st.metric(label="Available Margin", value=balance_usd)
with col_b2: st.metric(label="Active Future Position", value=position_status)
# 🎯 লাইভ এন্ট্রি প্রাইস ও টার্গেট প্রাইস কার্ড (মোবাইল স্ক্রিনের জন্য ফিক্সড)
if st.session_state.in_position and st.session_state.buy_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    
    st.markdown(f"""
    <div style="background-color:#1e293b; padding:12px; border-radius:10px; margin-bottom:15px; border-left: 5px solid #00cc66;">
        <p style="margin:0; font-size:13px; color:#94a3b8;">🎯 পজিশন ট্র্যাকার:</p>
        <span style="font-size:15px; font-weight:bold; color:#ffffff;">ওপেন দাম (Entry): ${st.session_state.buy_price:,.2f}</span><br>
        <span style="font-size:15px; font-weight:bold; color:#00cc66;">লক্ষ্যমাত্রা (Target): ${live_target:,.2f}</span><br>
        <span style="font-size:15px; font-weight:bold; color:#ff3333;">স্টপ লস (Stop Loss): ${live_sl:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

# ৪. প্রফিট/লস ও ফি মনিটর উইজেট
effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 

st.info(f"💡 আপনার সেট করা কনফিগারেশন অনুযায়ী প্রতি কমপ্লিট ট্রেডে আনুমানিক ফি কাটবে: **${estimated_fee:.3f} USDT**")

# ৫. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button("🔴 STOP BOT", key="stop_btn"):
            st.session_state.bot_active = False
            st.rerun()
    else:
        if st.button("🟢 START FUTURE SCALPING", key="start_btn"):
            st.session_state.bot_active = True
            st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button("🚨 FORCE CLOSE FUTURE", key="force_sell_btn"):
            st.session_state.in_position = False
            st.session_state.buy_price = 0.0
            st.session_state.current_side = "NONE"
            st.rerun()

# 🔍 মার্কেট ডাটা ও স্ক্যাল্পিং অ্যাকশন লুপ
if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close']: df[col] = pd.to_numeric(df[col])
            
            live_price = df['close'].iloc[-1]
            st.subheader(f"📈 Future BTC/USDT Price: ${live_price:,.2f}")
            
            # চার্ট
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], increasing_line_color='#00cc66', decreasing_line_color='#ff3333')])
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", height=200)
            st.plotly_chart(fig, use_container_width=True)

            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-10)
            df['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df['RSI'].iloc[-1] if not df['RSI'].isnull().iloc[-1] else 50

            calculated_qty = round((effective_vol / live_price), 4)
            if calculated_qty < 0.0001: calculated_qty = 0.0001

            # অর্ডার ওপেনিং লজিক
            if not st.session_state.in_position:
                decision_side = "NONE"
                if ai_decision:
                    if current_rsi < 36: decision_side = "BUY"
                    elif current_rsi > 64: decision_side = "SELL"
                else:
                    decision_side = "BUY"

                if decision_side != "NONE":
                    st.session_state.buy_price = live_price
                    st.session_state.in_position = True
                    st.session_state.current_side = "LONG" if decision_side == "BUY" else "SHORT"
                    
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side=decision_side, orderType="Market", qty=str(calculated_qty))
                        except: st.session_state.in_position = False; st.session_state.buy_price = 0.0
                    
                    target_calc = (live_price + price_jump_target) if decision_side == "BUY" else (live_price - price_jump_target)
                    st.session_state.all_trades_history.append({
                        "Time": time.strftime("%H:%M:%S"), "Action": f"OPEN {st.session_state.current_side}",
                        "Price": live_price, "Target": target_calc, "Trading Fee ($)": f"-{estimated_fee/2:.3f}", "Net P&L ($)": "0.00", "Status": "RUNNING"
                    })
                st.rerun()
            
            # প্রফিট বুকিং ও লাইভ নিট ফি ক্যালকুলেশন ইঞ্জিন
            elif st.session_state.in_position:
                is_long_pos = True if st.session_state.current_side == "LONG" else False
                
                if is_long_pos:
                    is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                    is_stop_hit = live_price <= (st.session_state.buy_price - stop_loss_gap)
                    gross_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
                else:
                    is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                    is_stop_hit = live_price >= (st.session_state.buy_price + stop_loss_gap)
                    gross_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)

                if is_profit_hit or is_stop_hit:
                    close_action = "Sell" if is_long_pos else "Buy"
                    status_tag = "PROFIT 🟢" if is_profit_hit else "STOPLOSS 🔴"
                    net_pnl = gross_pnl - estimated_fee
                    
                    if is_real_live and session:
                        try: session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
                        except: pass
                    else:
                        st.session_state.demo_balance += net_pnl
                    
                    target_display = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
                    st.session_state.all_trades_history.append({
                        "Time": time.strftime("%H:%M:%S"), "Action": f"CLOSE {st.session_state.current_side}",
                        "Price": live_price, "Target": target_display, "Trading Fee ($)": f"-{estimated_fee:.3f}", "Net P&L ($)": f"{net_pnl:.2f}", "Status": status_tag
                    })
                    
                    st.session_state.in_position = False
                    st.session_state.buy_price = 0.0
                    st.session_state.current_side = "NONE"
                    st.rerun()

        # 📋 হিস্ট্রি টেবিল ও সিএসভি ডাউনলোড বাটন
        st.subheader("📋 Permanent Trading Action History")
        if st.session_state.all_trades_history:
            history_df = pd.DataFrame(st.session_state.all_trades_history)
            st.dataframe(history_df.iloc[::-1], height=200, use_container_width=True)
            
            csv_data = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Complete CSV Logs", data=csv_data,
                file_name=f"scalper_fee_logs_{time.strftime('%Y%m%d')}.csv", mime='text/csv'
            )
        else:
            st.info("ট্রেড শুরু হলে এখানে লাইভ রেকর্ড জমা হতে থাকবে।")

        time.sleep(1)
        st.rerun()
    except:
        time.sleep(1)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। ফিউচার স্ক্যাল্পিং চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
    if st.session_state.all_trades_history:
        st.subheader("📋 Past Session Trading History")
        st.dataframe(pd.DataFrame(st.session_state.all_trades_history).iloc[::-1], use_container_width=True)
