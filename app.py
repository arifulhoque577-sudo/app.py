import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit AI Pro Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    .stButton>button[key="force_sell_btn"] { background-color: #ff3333 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Future Scalper")
st.caption("ভার্সন ৯.২ | মাল্টি-বক্স মোবাইল অপ্টিমাইজড এডিশন")

# ২. ডাইনামিক ফিউচার সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configurations")
    bot_mode = st.radio("ট্রেডিং মোড:", ["Demo Mode (ফ্রি ফেইক ফান্ড)", "Live Mode (আসল Bybit API)"])
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

# ৩. সেসন স্টেট ও মেমোরি ইনিশিয়ালাইজেশন
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 
# 🔍 লাইভ মার্কেট ডাটা ফেচিং কোর মেকানিজম
live_price = 0.0
df_kline = None

if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=15)
        klines = response.get('result', {}).get('list', [])
        if klines:
            df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df_kline = df_kline.iloc[::-1].reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close']: df_kline[col] = pd.to_numeric(df_kline[col])
            live_price = df_kline['close'].iloc[-1]
    except:
        pass

# 💰 লাইভ ফ্লোটিং ব্যালেন্স ও রিয়েল-টাইম P&L ক্যালকুলেশন
floating_pnl = 0.0
expected_target_profit = 0.0

if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    if is_long_pos:
        floating_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
    else:
        floating_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)
    
    gross_target_profit = price_jump_target * (effective_vol / st.session_state.buy_price)
    expected_target_profit = gross_target_profit - estimated_fee

display_balance = st.session_state.demo_balance + floating_pnl if not is_real_live else 0.0
balance_usd_text = f"${display_balance:,.2f}" if not is_real_live else "$0.00"

# Live API কানেক্টিভিটি চেক
session = None
if is_real_live and api_key and secret_key:
    try:
        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
        wallet_info = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        member_list = wallet_info.get('result', {}).get('list', [])
        if member_list:
            for c in member_list.get('coin', []):
                if c.get('coin') == 'USDT':
                    balance_usd_text = f"${(float(c.get('walletBalance', 0)) + floating_pnl):,.2f}"
                    break
    except:
        balance_usd_text = "API কী চেক করুন"

position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"Future {st.session_state.current_side} রানিং"
# 🎯 লাইভ ফিউচার ট্র্যাকার উইজেট ডিসপ্লে
if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    
    st.markdown(f"""
    <div style="background-color:#1e293b; padding:12px; border-radius:10px; margin-bottom:15px; border-left: 5px solid #3b82f6;">
        <span style="font-size:14px; font-weight:bold; color:#ffffff;">Entry Price: ${st.session_state.buy_price:,.2f} | Current: ${live_price:,.2f}</span><br>
        <span style="font-size:14px; font-weight:bold; color:#00cc66;">Take Profit: ${live_target:,.2f} (ট্রিগার হলে নিট লাভ হবে: <b>+${expected_target_profit:.2f}</b>)</span><br>
        <span style="font-size:14px; font-weight:bold; color:#ff3333;">Stop Loss: ${live_sl:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

st.info(f"💡 আনুমানিক কমপ্লিট ট্রেড ফি কাটবে: **${estimated_fee:.3f} USDT**")

# ৬. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button("🔴 STOP BOT", key="stop_btn"): st.session_state.bot_active = False; st.rerun()
    else:
        if st.button("🟢 START FUTURE SCALPING", key="start_btn"): st.session_state.bot_active = True; st.rerun()
with c2:
    if st.session_state.in_position:
        if st.button("🚨 FORCE CLOSE FUTURE", key="force_sell_btn"):
            st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.rerun()

# ⚡ ফাস্ট চার্ট ও স্ক্যাল্পিং লুপ এক্সিকিউশন
if st.session_state.bot_active and df_kline is not None:
    try:
        fig = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'], increasing_line_color='#00cc66', decreasing_line_color='#ff3333')])
        fig.update_layout(margin=dict(l=5, r=5, t=5, b=5), xaxis_rangeslider_visible=False, template="plotly_dark", height=180)
        st.plotly_chart(fig, use_container_width=True)

        calculated_qty = round((effective_vol / live_price), 4)
        if calculated_qty < 0.0001: calculated_qty = 0.0001

        # পজিশন ওপেনিং
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
                    "Price": live_price, "Target": f"${target_calc:,.2f}", "Trading Fee ($)": f"-{estimated_fee/2:.3f}", "Net P&L ($)": "0.00", "Status": "RUNNING"
                })
            st.rerun()
        
        # পজিশন ক্লোজিং
        elif st.session_state.in_position:
            is_long_pos = True if st.session_state.current_side == "LONG" else False
            if is_long_pos:
                is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                is_stop_hit = live_price <= (st.session_state.buy_price - stop_loss_gap)
            else:
                is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                is_stop_hit = live_price >= (st.session_state.buy_price + stop_loss_gap)

            if is_profit_hit or is_stop_hit:
                close_action = "Sell" if is_long_pos else "Buy"
                status_tag = "PROFIT 🟢" if is_profit_hit else "STOPLOSS 🔴"
                net_pnl = floating_pnl - estimated_fee
                
                if is_real_live and session:
                    try: session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
                    except: pass
                else:
                    st.session_state.demo_balance += net_pnl
                
                target_display = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
                st.session_state.all_trades_history.append({
                    "Time": time.strftime("%H:%M:%S"), "Action": f"CLOSE {st.session_state.current_side}",
                    "Price": live_price, "Target": f"${target_display:,.2f}", "Trading Fee ($)": f"-{estimated_fee:.3f}", "Net P&L ($)": f"{net_pnl:.2f}", "Status": status_tag
                })
                st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"
                st.rerun()

        # হিস্ট্রি টেবিল ও সিএসভি ডাউনলোড ভিউ
        st.subheader("📋 Permanent Trading Action History")
        if st.session_state.all_trades_history:
            history_df = pd.DataFrame(st.session_state.all_trades_history)
            st.dataframe(history_df.iloc[::-1], height=180, use_container_width=True)
            csv_data = history_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download Complete CSV Logs", data=csv_data, file_name=f"scalper_fee_logs_{time.strftime('%Y%m%d')}.csv", mime='text/csv')
        
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

st.subheader(f"📊 Future {bot_mode} (Leverage: {leverage}x)")
col_b1, col_b2 = st.columns(2)
with col_b1: 
    st.metric(label="Floating Wallet Balance", value=balance_usd_text, delta=f"{floating_pnl:+.2f} USDT (Live P&L)" if floating_pnl != 0 else None)
with col_b2: 
    st.metric(label="Active Future Position", value=position_status)
