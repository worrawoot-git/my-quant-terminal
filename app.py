import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Pro Quant V14.6.3", layout="wide")
st.title("🏛️ Pro Quant: Smart Volatility Alert")

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    # สร้างตารางถ้ายังไม่มี
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    
    # รายการ Watchlist ใหม่ (เอา PTT, TSLA, CPALL, KBANK ออกแล้ว)
    defaults = ['^SET.BK', '^DJI', 'GC=F', 'CL=F', 'BTC-USD', 'THB=X']
    
    # ล้างข้อมูลเก่าที่เป็นหุ้นรายตัวออก เพื่ออัปเดตตามคำขอ
    to_remove = ['PTT.BK', 'TSLA', 'CPALL.BK', 'KBANK.BK']
    for s in to_remove:
        c.execute("DELETE FROM watchlist WHERE ticker = ?", (s,))
        
    # เพิ่มรายการเริ่มต้นใหม่
    for s in defaults:
        c.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (s,))
    
    conn.commit()
    conn.close()

init_db()

# --- 2. ฟังก์ชันส่ง LINE ---
def send_line_alert(msg, token, uid):
    if token and uid:
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        payload = {'to': uid, 'messages': [{'type': 'text', 'text': msg}]}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            return res.status_code == 200
        except:
            return False
    return False

# --- 3. เมนู Tab ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ Settings")
    line_token = st.text_input("Line Token", type="password", key="tk")
    line_uid = st.text_input("Line User ID", type="password", key="uid")
    # ตั้งค่าความไวสำหรับการแจ้งเตือนราคาผิดปกติ
    sensitivity = st.slider("เกณฑ์แจ้งเตือนราคาผิดปกติ (%)", 0.5, 10.0, 2.0, help="หากราคาเปลี่ยนแปลงเกิน % นี้ ระบบจะแจ้งเตือนว่าผิดปกติ")

with tab1:
    st.subheader("📌 Market Watchlist & Abnormal Move Detection")
    
    # ฟอร์มเพิ่มหุ้น
    with st.form("add_stock_form", clear_on_submit=True):
        col_in, col_bt = st.columns([3, 1])
        new_stk = col_in.text_input("เพิ่มชื่อหุ้น/ดัชนี (เช่น NVDA, ETH-USD, ^GSPC):")
        if col_bt.form_submit_button("➕ เพิ่ม"):
            if new_stk:
                conn = sqlite3.connect('portfolio.db')
                conn.execute("INSERT OR IGNORE INTO watchlist VALUES (?)", (new_stk.upper().strip(),))
                conn.commit(); conn.close()
                st.rerun()

    db = sqlite3.connect('portfolio.db')
    watchlist = pd.read_sql_query("SELECT * FROM watchlist", db)['ticker'].tolist()
    db.close()

    if st.button("🚀 สแกนหาความผิดปกติและส่งเข้า LINE"):
        alert_msg = f"📢 [Pro Quant Abnormal Move]\nประจำวันที่: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        found_abnormal = False
        
        with st.spinner('กำลังตรวจสอบราคา...'):
            for s in watchlist:
                df = yf.download(s, period="5d", progress=False)
                if not df.empty and len(df) >= 2:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    curr = float(df['Close'].iloc[-1])
                    prev = float(df['Close'].iloc[-2])
                    pct = ((curr - prev) / prev) * 100
                    
                    status = "⚪ ปกติ"
                    if abs(pct) >= sensitivity:
                        found_abnormal = True
                        if pct > 0:
                            status = f"🔥 พุ่งแรงผิดปกติ! (+{pct:.2f}%)"
                        else:
                            status = f"⚠️ ร่วงหนักผิดปกติ! ({pct:.2f}%)"
                    
                    alert_msg += f"\n• {s}: {curr:,.2f}\n[{status}]\n"
        
        if send_line_alert(alert_msg, line_token, line_uid):
            st.success("ส่งข้อมูลวิเคราะห์เข้า LINE เรียบร้อย!")
        else:
            st.error("ไม่สามารถส่ง LINE ได้ กรุณาเช็ค Token/ID ในหน้า Setup")

    # ส่วนแสดงกราฟ 1 ปี
    for s in watchlist:
        with st.expander(f"📊 {s} Insight", expanded=False):
            df_y = yf.download(s, period="1y", progress=False)
            if not df_y.empty:
                if isinstance(df_y.columns, pd.MultiIndex): df_y.columns = df_y.columns.get_level_values(0)
                c_val = df_y['Close'].iloc[-1]
                p_val = df_y['Close'].iloc[-2]
                st.metric(f"{s}", f"{c_val:,.2f}", f"{((c_val-p_val)/p_val)*100:+.2f}%")
                st.plotly_chart(px.line(df_y, y='Close', title=f"แนวโน้ม 1 ปี: {s}"), use_container_width=True)
            
            if st.button(f"🗑️ ลบ {s}", key=f"del_{s}"):
                conn = sqlite3.connect('portfolio.db')
                conn.execute("DELETE FROM watchlist WHERE ticker = ?", (s,))
                conn.commit(); conn.close()
                st.rerun()

with tab2:
    st.info("หน้า Dashboard จะแสดงผลเมื่อมีการบันทึกการซื้อหุ้น (Trades) ในระบบ")
    # โค้ดส่วน Dashboard (เหมือนเดิม)
