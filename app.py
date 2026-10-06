import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from pybit.unified_trading import HTTP

# ১. মোবাইল ও থিম অপ্টিমাইজেশন
st.set_page_config(page_title="Bybit AI Counter-Trend Scalper", page_icon="⚡", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div.stButton > button:first-child { width: 100%; border-radius: 10px; font-weight: bold; }
    .stButton>button[key="force_sell_btn"] { background-color: #ff3333 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Bybit AI Pro Future Scalper")
st.caption("ভার্সন ১৩.০ | পিওর কাউন্টার-ট্রেন্ড এআই এবং ৫-সেকেন্ড ক্যান্ডেল ইঞ্জিন")

# ২. ডাইনামিক ফিউচার সেটিংস (সাইডবার)
with st.sidebar:
    st.header("⚙️ Configurations")
    bot_mode = st.radio("ট্রেডিং মোড:", ["Demo Mode (ফ্রি ফেইক ফান্ড)", "Live Mode (আসল Bybit API)"])
    is_real_live = True if "Live" in bot_mode else False
    
    ai_decision = st.toggle("এআই অটো-ডিসিশন (Counter-Trend RSI)", value=True)
    
    leverage = st.slider("ফিউচার লেভারেজ", min_value=1, max_value=50, value=20, step=1)
    trade_amount = st.number_input("মার্জিন কস্ট ($)", min_value=1, max_value=500, value=20, step=1)
    price_jump_target = st.slider("প্রফিট বুকিং টার্গেট ($ গ্যাপ)", min_value=10, max_value=1000, value=300, step=10)
    stop_loss_gap = st.slider("স্টপ লস প্রোটেকশন ($ গ্যাপ)", min_value=10, max_value=500, value=100, step=5)
    
    api_key = ""
    secret_key = ""
    if is_real_live:
        api_key = st.text_input("Bybit API Key", type="password")
        secret_key = st.text_input("Secret Key", type="password")

# ৩. পার্মানেন্ট সেশন মেমোরি ও স্কোরবোর্ড ট্র্যাকার
if 'demo_balance' not in st.session_state: st.session_state.demo_balance = 5000.0
if 'bot_active' not in st.session_state: st.session_state.bot_active = False
if 'in_position' not in st.session_state: st.session_state.in_position = False
if 'buy_price' not in st.session_state: st.session_state.buy_price = 0.0
if 'current_side' not in st.session_state: st.session_state.current_side = "NONE"
if 'all_trades_history' not in st.session_state: st.session_state.all_trades_history = []
if 'win_count' not in st.session_state: st.session_state.win_count = 0
if 'loss_count' not in st.session_state: st.session_state.loss_count = 0

effective_vol = trade_amount * leverage
estimated_fee = effective_vol * 0.0011 

total_trades = st.session_state.win_count + st.session_state.loss_count
win_rate = (st.session_state.win_count / total_trades * 100) if total_trades > 0 else 0.0

st.markdown(f"""
    <div style="background-color:#1e293b; padding:10px; border-radius:10px; margin-bottom:12px; border-left: 5px solid #f59e0b; display: flex; justify-content: space-between;">
        <span style="color:#ffffff; font-size:13px; font-weight:bold;">🏆 WIN: <b style="color:#00cc66;">{st.session_state.win_count}</b></span>
        <span style="color:#ffffff; font-size:13px; font-weight:bold;">❌ LOSS: <b style="color:#ff3333;">{st.session_state.loss_count}</b></span>
        <span style="color:#ffffff; font-size:13px; font-weight:bold;">🎯 WIN RATE: <b style="color:#3b82f6;">{win_rate:.1f}%</b></span>
    </div>
""", unsafe_allow_html=True)
# 🔍 লাইভ মার্কেট ডাটা ইঞ্জিন (রিয়েল-টাইম ৫ সেকেন্ডের ফিড)
live_price = 0.0
current_rsi = 50.0
df_kline = None

if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol="BTCUSDT", interval="5", limit=15)
        klines = response.get('result', {}).get('list', [])
        if klines:
            df_kline = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df_kline = df_kline.iloc[::-1].reset_index(drop=True)
            for col in ['open', 'high', 'low', 'close']: df_kline[col] = pd.to_numeric(df_kline[col])
            live_price = df_kline['close'].iloc[-1]
            
            # ৫-সেকেন্ড ক্যান্ডেলের আরএসআই (RSI) গণনা
            delta = df_kline['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
            rs = gain / (loss + 1e-10)
            df_kline['RSI'] = 100 - (100 / (1 + rs))
            current_rsi = df_kline['RSI'].iloc[-1] if not df_kline['RSI'].isnull().iloc[-1] else 50.0
    except:
        pass

# 💰 লাইভ P&L ও ফ্লোটিং ব্যালেন্স হিসাব
floating_pnl = 0.0
expected_net_profit = 0.0

if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    if is_long_pos:
        floating_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
    else:
        floating_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)
    
    gross_target_profit = price_jump_target * (effective_vol / st.session_state.buy_price)
    expected_net_profit = gross_target_profit - estimated_fee

display_balance = st.session_state.demo_balance + floating_pnl if not is_real_live else 0.0
balance_usd_text = f"${display_balance:,.2f}"

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
        balance_usd_text = "API কী এরর"

position_status = "কোনো পজিশন নেই 💤" if not st.session_state.in_position else f"Future {st.session_state.current_side} রানিং"

# 📡 লাইভ আরএসআই সিগন্যাল মনিটর বক্স
rsi_color = "#ff3333" if current_rsi > 50 else "#00cc66"
st.markdown(f"""
    <div style="background-color:#1e293b; padding:10px; border-radius:10px; margin-bottom:12px; border-left: 5px solid {rsi_color}; text-align:center;">
        <span style="color:#94a3b8; font-size:12px; font-weight:bold; text-transform:uppercase;">📡 Live AI RSI (5s Counter-Trend Feed):</span>
        <h3 style="margin:2px 0; color:{rsi_color}; font-size:22px;">{current_rsi:.2f}</h3>
    </div>
""", unsafe_allow_html=True)

# নিচে-নিচে রেসপন্সিভ লেআউট
st.markdown(f"""
    <div style="background-color:#1e293b; padding:15px; border-radius:12px; margin-bottom:12px; border-top: 4px solid #f59e0b;">
        <p style="margin:0; font-size:12px; color:#94a3b8; text-transform:uppercase; font-weight:bold;">💰 Account Balance ({bot_mode})</p>
        <h2 style="margin:5px 0; color:#ffffff; font-size:26px;">{balance_usd_text}</h2>
        <p style="margin:0; font-size:14px; color:{'#00cc66' if floating_pnl >= 0 else '#ff3333'}; font-weight:bold;">Live Floating P&L: {floating_pnl:+.2f} USDT</p>
    </div>
    <div style="background-color:#1e293b; padding:15px; border-radius:12px; margin-bottom:15px; border-top: 4px solid #10b981;">
        <p style="margin:0; font-size:12px; color:#94a3b8; text-transform:uppercase; font-weight:bold;">📦 Active Future Position Status</p>
        <h3 style="margin:5px 0; color:{'#ffffff' if st.session_state.current_side == 'NONE' else ('#00cc66' if st.session_state.current_side == 'LONG' else '#ff3333')}; font-size:20px;">Future {st.session_state.current_side if st.session_state.current_side != 'NONE' else 'খালি (IDLE 💤)'}</h3>
    </div>
""", unsafe_allow_html=True)
# 🎯 লাইভ ফিউচার ট্র্যাকার উইজেট
if st.session_state.in_position and live_price > 0:
    is_long_pos = True if st.session_state.current_side == "LONG" else False
    live_target = (st.session_state.buy_price + price_jump_target) if is_long_pos else (st.session_state.buy_price - price_jump_target)
    live_sl = (st.session_state.buy_price - stop_loss_gap) if is_long_pos else (st.session_state.buy_price + stop_loss_gap)
    
    st.markdown(f"""
    <div style="background-color:#0f172a; padding:12px; border-radius:10px; margin-bottom:15px; border-left: 5px solid #3b82f6;">
        <span style="font-size:14px; color:#ffffff; font-weight:bold;">Entry: ${st.session_state.buy_price:,.2f} | Live Price: ${live_price:,.2f}</span><br>
        <span style="font-size:14px; color:#00cc66; font-weight:bold;">Take Profit Target: ${live_target:,.2f} (নিট লাভ হবে: +${expected_net_profit:.2f})</span><br>
        <span style="font-size:14px; color:#ff3333; font-weight:bold;">Stop Loss Price: ${live_sl:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

st.info(f"💡 আনুমানিক কমপ্লিট ট্রেড ফি কাটবে: **${estimated_fee:.3f} USDT**")

# ৬. বট কন্ট্রোল বোতামসমূহ
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
            net_pnl = floating_pnl - estimated_fee
            if not is_real_live: st.session_state.demo_balance += net_pnl
            if net_pnl >= 0: st.session_state.win_count += 1
            else: st.session_state.loss_count += 1
            st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"; st.rerun()

# ⚡ ৭. কাউন্টার-ট্রেন্ড এআই এক্সিকিউশন মেকানিজম
if st.session_state.bot_active and df_kline is not None:
    try:
        fig = go.Figure(data=[go.Candlestick(x=df_kline.index, open=df_kline['open'], high=df_kline['high'], low=df_kline['low'], close=df_kline['close'], increasing_line_color='#00cc66', decreasing_line_color='#ff3333')])
        fig.update_layout(margin=dict(l=5, r=5, t=5, b=5), xaxis_rangeslider_visible=False, template="plotly_dark", height=150)
        st.plotly_chart(fig, use_container_width=True)

        # পজিশন ওপেনিং (আপনার কাঙ্ক্ষিত কাউন্টার-ট্রেন্ড লজিক ফিক্সড)
        if not st.session_state.in_position:
            decision_side = "NONE"
            
            if ai_decision:
                # 🧠 আপনার সেই আসল এআই মোড: মার্কেট ওপরে গেলে (Overbought) করবে SHORT, নিচে নামলে (Oversold) করবে LONG
                if current_rsi < 45.0: 
                    decision_side = "BUY"   # Candle Down / RSI Low -> ওপরে ওঠার আশায় LONG 🟢
                elif current_rsi > 55.0: 
                    decision_side = "SELL"  # Candle Up / RSI High -> নিচে নামার আশায় SHORT 🔴
            else:
                decision_side = "BUY"

            if decision_side != "NONE":
                st.session_state.buy_price = live_price
                st.session_state.in_position = True
                st.session_state.current_side = "LONG" if decision_side == "BUY" else "SHORT"
                
                if is_real_live:
                    try:
                        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
                        session.place_order(category="linear", symbol="BTCUSDT", side=decision_side, orderType="Market", qty=str(calculated_qty))
                    except: 
                        st.session_state.in_position = False; st.session_state.buy_price = 0.0; st.session_state.current_side = "NONE"
                
                if st.session_state.in_position:
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
                
                if is_profit_hit: st.session_state.win_count += 1
                else: st.session_state.loss_count += 1
                
                if is_real_live:
                    try:
                        session = HTTP(testnet=False, api_key=api_key, api_secret=secret_key)
                        session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
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

        # হিস্ট্রি টেবিল ও সিএসভি ডাউনলোড
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
