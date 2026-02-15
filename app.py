with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    if st.button("🚀 สแกนหุ้น & ส่งสัญญาณพร้อมกราฟ"):
        db = sqlite3.connect('portfolio.db')
        df_trades = pd.read_sql_query("SELECT * FROM trades", db)
        db.close()
        
        st.write("---")
        for s in watch_list:
            data = yf.download(s, period="1mo", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                curr_price = float(data['Close'].iloc[-1])
                
                # โชว์ราคาบนหน้าจอทุกครั้งที่สแกน
                st.write(f"🔍 กำลังตรวจสอบ **{s}**: ราคาปัจจุบัน `{curr_price:,.2f}`")
                
                if not df_trades.empty and s in df_trades['ticker'].values:
                    # หาต้นทุนตัวล่าสุดที่ซื้อมา
                    entry = df_trades[df_trades['ticker'] == s]['entry_price'].iloc[-1]
                    pnl_pct = ((curr_price / entry) - 1) * 100
                    
                    # แสดงผลกำไร/ขาดทุนปัจจุบันบนหน้าจอ
                    color = "green" if pnl_pct >= 0 else "red"
                    st.markdown(f"↳ สถานะในพอร์ต: :{color}[{pnl_pct:.2f}%]")
                    
                    # เช็คเงื่อนไขส่ง LINE
                    if pnl_pct >= tp_target or pnl_pct <= -sl_target:
                        status = "💰 TAKE PROFIT" if pnl_pct >= tp_target else "⚠️ STOP LOSS"
                        add_alert_history(s, status, pnl_pct, curr_price)
                        
                        chart_url = f"https://finance.yahoo.com/chart/{s}"
                        alert_msg = f"{status}\nหุ้น: {s}\nกำไร/ขาดทุน: {pnl_pct:.2f}%\nราคาปัจจุบัน: {curr_price}\nดูรายละเอียด: {chart_url}"
                        
                        if 'line_token' in st.session_state and 'line_uid' in st.session_state:
                            url = 'https://api.line.me/v2/bot/message/push'
                            headers = {'Content-Type': 'application/json', 'Authorization': f"Bearer {st.session_state.line_token}"}
                            payload = {'to': st.session_state.line_uid, 'messages': [{'type': 'text', 'text': alert_msg}]}
                            requests.post(url, headers=headers, json=payload)
                            st.warning(f"🎯 ยิงสัญญาณ {status} ของ {s} เข้า LINE แล้ว!")
        st.success("✅ สแกนและตรวจสอบเงื่อนไขครบทุกตัวแล้ว!")
