import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอและหัวข้อ ---
st.set_page_config(page_title="Pro Quant V13.1", layout="wide")
st.title("🏛️ Pro Quant: Visual Alert System")

# --- 2. ฟังก์ชันจัดการฐานข้อมูล ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS alert_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, type TEXT, pnl_pct REAL, price REAL, timestamp TEXT)''')
    conn.commit()
    conn.close()

def add_alert_history(ticker, alert_type, pnl, price):
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute("INSERT INTO alert_history (ticker, type, pnl_pct, price, timestamp) VALUES (?, ?, ?, ?, ?)",
              (ticker, alert_type, pnl, price, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    conn.commit()
    conn.close()

init_db()

# --- 3. สร้างเมนู Tab ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Scanner", "📈 Dashboard", "📜 History", "⚙️ Setup"])

# --- Tab 4: ตั้งค่ารหัสและเป้าหมาย ---
with tab4:
    st.subheader("🔑 Config & Risk Settings")
    st.session_state.line_token = st.text_input("Channel Access Token", type="password", key="token")
    st.session_state.line_uid = st.text_input("Your User ID", type="password", key="uid")
    tp_target = st.slider("เป้าหมายกำไร (Take Profit %)", 1.0, 50.0, 10.0)
    sl_target = st.slider("จุดตัดขาดทุน (Stop Loss %)", 1.0, 20.0, 5.0)

# --- Tab 1: ระบบสแกนและแจ้งเตือน ---
with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    if st.button("🚀 เริ่มสแกนและตรวจสอบพอร์ต"):
        db = sqlite3.connect('portfolio.db')
        df_trades = pd.read_sql_query("SELECT * FROM trades", db)
        db.close()
        
        st.write("---")
        progress_bar = st.progress(0)
        for idx, s in enumerate(watch_list):
            data = yf.download(s, period="1mo", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                curr_price = float(data['Close'].iloc[-1])
                
                # แสดงผลราคาบนจอ
                st.write(f"🔍 ตรวจสอบ **{s}**: ราคาล่าสุด `{curr_price:,.2f}`")
                
                # ถ้ามีหุ้นตัวนี้ในพอร์ต ให้เช็คกำไร/ขาดทุน
                if not df_trades.empty and s in df_trades['ticker'].values:
                    entry = df_trades[df_trades['ticker'] == s]['entry_price'].iloc[-1]
                    pnl_pct = ((curr_price / entry) - 1) * 100
                    color = "green" if pnl_pct >= 0 else "red"
                    st.markdown(f"↳ สถานะพอร์ต: :{color}[{pnl_pct:.2f}%]")
                    
                    # เช็คเงื่อนไขแจ้งเตือน
                    if pnl_pct >= tp_target or pnl_pct <= -sl_target:
                        status = "💰 TAKE PROFIT" if pnl_pct >= tp_target else "⚠️ STOP LOSS"
                        add_alert_history(s, status, pnl_pct, curr_price)
                        
                        # ยิงเข้า LINE
                        if st.session_state.line_token and st.session_state.line_uid:
                            alert_msg = f"{status}\nหุ้น: {s}\nกำไร: {pnl_pct:.2f}%\nราคา: {curr_price}\nลิงก์กราฟ: https://finance.yahoo.com/chart/{s}"
                            url = 'https://api.line.me/v2/bot/message/push'
                            headers = {'Content-Type': 'application/json', 'Authorization': f"Bearer {st.session_state.line_token}"}
                            payload = {'to': st.session_state.line_uid, 'messages': [{'type': 'text', 'text': alert_msg}]}
                            requests.post(url, headers=headers, json=payload)
                            st.warning(f"📢 ส่งสัญญาณ {status} ของ {s} เข้า LINE แล้ว!")
            progress_bar.progress((idx + 1) / len(watch_list))
        st.success("✅ ตรวจสอบครบทุกตัวเรียบร้อย!")

# --- Tab 2 & 3: แสดงผลย้อนหลัง ---
with tab2:
    st.info("ไปที่หน้า Scanner เพื่อกดบันทึก 'ซื้อ' หุ้นเข้าพอร์ต แล้วกราฟจะขึ้นที่นี่ครับ")

with tab3:
    st.subheader("📜 ประวัติการแจ้งเตือน")
    db = sqlite3.connect('portfolio.db')
    df_hist = pd.read_sql_query("SELECT * FROM alert_history ORDER BY id DESC", db)
    db.close()
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.write("ยังไม่มีประวัติการแจ้งเตือน")
