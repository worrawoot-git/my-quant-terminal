import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import time
from datetime import datetime, timedelta

# --- 1. ตั้งค่าหน้าจอและการรีเฟรชอัตโนมัติ ---
st.set_page_config(page_title="Pro Quant V14.4 Auto-Pilot", layout="wide")
st.title("🏛️ Pro Quant: Auto-Pilot Scanner (1 Hr)")

# ใช้ streamlit-autorefresh หรือการใช้ st.empty กับ loop (ในที่นี้ใช้ logic เช็คเวลา)
if 'last_scan_time' not in st.session_state:
    st.session_state.last_scan_time = datetime.min

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scan_logs (last_run TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. ฟังก์ชันหลักในการสแกนและส่ง LINE ---
def run_auto_scan(token, uid, sensitivity):
    db = sqlite3.connect('portfolio.db')
    watchlist = pd.read_sql_query("SELECT * FROM watchlist", db)['ticker'].tolist()
    db.close()
    
    if not watchlist: return "Watchlist ว่างเปล่า"

    report_msg = f"🤖 [Auto-Pilot Report]\nประจำวันที่: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    for s in watchlist:
        df = yf.download(s, period="5d", progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            curr_price = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            change = ((curr_price - prev_close) / prev_close) * 100
            
            signal = "➖ ถือ/รอดูอาการ"
            if change >= sensitivity: signal = f"🚀 พุ่ง! (+{change:.2f}%) แนะนำ: ขายทำกำไร"
            elif change <= -sensitivity: signal = f"⚠️ ร่วง! ({change:.2f}%) แนะนำ: รอถัว/คัด"
            elif curr_price > df['Close'].rolling(5).mean().iloc[-1]: signal = "✅ ขาขึ้น แนะนำ: Buy/Hold"
            
            report_msg += f"\n• {s}: {curr_price:,.2f}\n{signal}\n"
    
    # ส่ง LINE
    url = 'https://api.line.me/v2/bot/message/push'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    payload = {'to': uid, 'messages': [{'type': 'text', 'text': report_msg}]}
    requests.post(url, headers=headers, json=payload)
    return "สแกนและส่ง LINE สำเร็จ"

# --- 3. UI & Control ---
tab1, tab2, tab3 = st.tabs(["🤖 Auto-Pilot Monitor", "📈 Watchlist Management", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ Settings")
    line_token = st.text_input("LINE Token", type="password", key="tk")
    line_uid = st.text_input("LINE User ID", type="password", key="uid")
    sensitivity = st.slider("ความไวสัญญาณ (%)", 1.0, 10.0, 3.0)
    auto_mode = st.toggle("เปิดระบบ Scan อัตโนมัติทุก 1 ชั่วโมง", value=True)

with tab1:
    st.subheader("🛰️ สถานะการทำงานปัจจุบัน")
    
    # Logic เช็คเวลา 1 ชั่วโมง
    next_scan = st.session_state.last_scan_time + timedelta(hours=1)
    time_to_wait = next_scan - datetime.now()
    
    if auto_mode:
        if datetime.now() >= next_scan:
            if line_token and line_uid:
                status = run_auto_scan(line_token, line_uid, sensitivity)
                st.session_state.last_scan_time = datetime.now()
                st.success(f"🔥 {status} เมื่อเวลา {datetime.now().strftime('%H:%M:%S')}")
            else:
                st.error("กรุณากรอกรหัส LINE ในหน้า Setup ก่อน")
        else:
            st.info(f"⏳ ระบบจะสแกนรอบถัดไปในอีกประมาณ {int(time_to_wait.total_seconds() // 60)} นาที")
            st.write(f"สแกนครั้งล่าสุดเมื่อ: {st.session_state.last_scan_time.strftime('%H:%M:%S')}")
    else:
        st.warning("ระบบ Auto-Pilot ถูกปิดอยู่")
        if st.button("🚀 สแกนทันที (Manual)"):
            run_auto_scan(line_token, line_uid, sensitivity)
            st.success("ส่งเข้า LINE เรียบร้อย")

with tab2:
    # โค้ดส่วนจัดการ Watchlist (เหมือน V14.3)
    pass
