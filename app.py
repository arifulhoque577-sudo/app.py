# ৪. ডিসপ্লে ওয়ালেট ও ফিউচার স্ট্যাটাস
st.subheader(f"📊 Future {bot_mode} (Leverage: {leverage}x)")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Available Margin", value=balance_usd, delta="USDT Balance")
with col2:
    st.metric(label="Active Future Position", value=position_status)

# ৫. বট কন্ট্রোল বাটন
st.subheader("🎮 Bot Controls")
c1, c2 = st.columns(2)
with c1:
    if st.session_state.bot_active:
        if st.button("🔴 STOP BOT", key="stop_btn"):
            st.session_state.bot_active = False
            st.session_state.trade_logs.append(f"[SYSTEM] Bot stopped.")
            st.rerun()
    else:
        if st.button("🟢 START FUTURE SCALPING", key="start_btn"):
            if is_real_live and (not api_key or not secret_key):
                st.error("❌ আগে সাইডবার থেকে এপিআই কী সেট করুন!")
            else:
                st.session_state.bot_active = True
                st.session_state.trade_logs.append(f"[SYSTEM] Activated Fast Scalper. Mode: {position_mode_text}")
                st.rerun()

with c2:
    if st.session_state.in_position:
        if st.button("🚨 FORCE CLOSE FUTURE", key="force_sell_btn"):
            st.session_state.in_position = False
            st.session_state.trade_logs.append("[🚨 FUTURE CLOSED] Position closed manually!")
            st.rerun()

# 🔍 লাইভ ফিউচার মার্কেট ডাটা ও অ্যাকশন লুপ
if st.session_state.bot_active:
    try:
        public_session = HTTP(testnet=False)
        response = public_session.get_kline(category="linear", symbol="BTCUSDT", interval="1", limit=30)
        klines = response.get('result', {}).get('list', [])
        
        if klines:
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df.iloc[::-1].reset_index(drop=True)
            df['close'] = pd.to_numeric(df['close'])
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            
            live_price = df['close'].iloc[-1]
            st.subheader(f"📈 Future BTC/USDT Price: ${live_price:,.2f}")
            
            # ফিউচার ক্যান্ডেল চার্ট
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                increasing_line_color='#00cc66', decreasing_line_color='#ff3333'
            )])
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False, template="plotly_dark", height=240)
            st.plotly_chart(fig, use_container_width=True)

            effective_vol = trade_amount * leverage
            calculated_qty = round((effective_vol / live_price), 4)
            if calculated_qty < 0.0001:
                calculated_qty = 0.0001

            # ⚡ ফিউচার পজিশন ওপেনিং লজিক (ইনস্ট্যান্ট কুইক বাই/সেল)
            if not st.session_state.in_position:
                st.session_state.buy_price = live_price
                st.session_state.in_position = True
                side_action = "Buy" if is_long else "Sell"
                log_tag = "LONG 🟢" if is_long else "SHORT 🔴"
                
                if is_real_live and session:
                    try:
                        session.place_order(category="linear", symbol="BTCUSDT", side=side_action, orderType="Market", qty=str(calculated_qty))
                        st.session_state.trade_logs.append(f"[🟢 FUTURE {log_tag} OPENED] Entry: ${live_price}")
                    except:
                        st.session_state.trade_logs.append(f"[❌ API Reject] চেক করুন এপিআই পারমিশন।")
                        st.session_state.in_position = False
                else:
                    st.session_state.trade_logs.append(f"[🟢 SIMULATED {log_tag} OPENED] Entry: ${live_price}")
                st.rerun()
            
            # ⚡ ফিক্সড প্রাইস গ্যাপ প্রফিট বুকিং ইঞ্জিন (১০০% ইনস্ট্যান্ট কন্টিনিউয়াস ক্লোজ)
            elif st.session_state.in_position:
                if is_long:
                    # সেট করা ডলার গ্যাপ টাচ করলেই মুহূর্তের মধ্যে ক্লোজ হয়ে যাবে
                    is_profit_hit = live_price >= (st.session_state.buy_price + price_jump_target)
                    is_stop_hit = live_price <= (st.session_state.buy_price - 40.0)
                    raw_pnl = (live_price - st.session_state.buy_price) * (effective_vol / st.session_state.buy_price)
                else:
                    is_profit_hit = live_price <= (st.session_state.buy_price - price_jump_target)
                    is_stop_hit = live_price >= (st.session_state.buy_price + 40.0)
                    raw_pnl = (st.session_state.buy_price - live_price) * (effective_vol / st.session_state.buy_price)

                if is_profit_hit or is_stop_hit:
                    close_action = "Sell" if is_long else "Buy"
                    
                    if is_real_live and session:
                        try:
                            session.place_order(category="linear", symbol="BTCUSDT", side=close_action, orderType="Market", qty=str(calculated_qty))
                            st.session_state.trade_logs.append(f"[🔴 REAL FUTURE CLOSED] Profit Booked at ${live_price}")
                            st.session_state.in_position = False
                        except:
                            st.session_state.trade_logs.append(f"[⚠️ Exit Scan] Closing future position...")
                    else:
                        st.session_state.demo_balance += raw_pnl
                        st.session_state.in_position = False
                        sign = "+" if raw_pnl >= 0 else ""
                        st.session_state.trade_logs.append(f"[🔴 SIMULATED CLOSED] Closed: ${live_price} | P&L: {sign}${raw_pnl:.2f}")
                    st.rerun()
                else:
                    target_price_display = (st.session_state.buy_price + price_jump_target) if is_long else (st.session_state.buy_price - price_jump_target)
                    st.session_state.trade_logs.append(f"[🔎 Future Scanning] Current: ${live_price} | Target: ${target_price_display:.2f}")

        st.subheader("📜 Live Action Logs")
        logs_display = "\n".join(st.session_state.trade_logs[-5:])
        st.text_area("Logs (Auto-refreshing)", value=logs_display, height=130)
        
        # রিফ্রেশ রেট ১ সেকেন্ড করা হলো আল্ট্রা-ফাস্ট স্ক্যাল্পিংয়ের জন্য
        time.sleep(1)
        st.rerun()

    except Exception as e:
        time.sleep(1)
        st.rerun()
else:
    st.info("বটটি বর্তমানে বন্ধ আছে। ফিউচার স্ক্যাল্পিং চালু করতে ওপরের সবুজ বাটনে ক্লিক করুন।")
