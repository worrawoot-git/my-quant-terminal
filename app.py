import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Pro Quant V14.1", layout="wide")
st.title("🏛️ Pro Quant: Full Visualization Dashboard")

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Scanner & Trade", "📊 Portfolio Dashboard", "📜 History", "⚙️ Setup"])

with tab4:
    st.subheader("⚙️ LINE Alert Settings")
    # ใช้ key เพื่อให้ค่าไม่หายเวลารีเฟรช
    line_token = st.text_input("Channel Access Token", type="password", key="token_val")
    line_uid = st.text_input("Your User ID", type="password", key="uid_val")
    st.info("กรอกรหัสเสร็จแล้ว ไปที่หน้า Dashboard เพื่อทดสอบส่งรายงานได้เลยครับ")

with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    for s in watch_list:
        # (ส่วนดึงราคาและปุ่มซื้อเหมือน V14 เดิม)
        pass

with tab2:
    st.header("📊 Visualization Center")
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()

    if not df_trades.empty:
        # กราฟวงกลมและกราฟเส้น (เหมือนในรูป line23.png)
        col_m1, col_m2 = st.columns(2)
        # ... (โค้ดกราฟเดิม) ...

        st.divider()
        st.subheader("📢 ระบบแจ้งเตือน LINE")
        if st.button("🚀 ส่งสรุปพอร์ตเข้า LINE ตอนนี้"):
            if line_token and line_uid:
                # สร้างข้อความสรุปพอร์ต
                msg = f"📊 รายงานพอร์ต Pro Quant\nวันที่: {datetime.now().strftime('%d/%m/%Y')}\n"
                msg += "------------------\n"
                for _, row in df_trades.iterrows():
                    msg += f"• {row['ticker']}: {row['shares']} หุ้น\n"
                
                # ฟังก์ชันส่ง LINE
                url = 'https://api.line.me/v2/bot/message/push'
                headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {line_token}'}
                payload = {'to': line_uid, 'messages': [{'type': 'text', 'text': msg}]}
                res = requests.post(url, headers=headers, json=payload)
                
                if res.status_code == 200:
                    st.success("✅ ข้อความส่งเข้า LINE เรียบร้อยแล้ว!")
                else:
                    st.error(f"❌ ส่งไม่สำเร็จ: {res.text}")
            else:
                st.warning("⚠️ กรุณากรอกรหัสในหน้า Setup ก่อนครับ")
