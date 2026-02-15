import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Pro Quant V14.3", layout="wide")
st.title("🏛️ Pro Quant: Smart Signal & Auto Alert")

# --- 1. Database Setup ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 2. ฟังก์ชันส่ง LINE (แบบรวม) ---
def send_line(msg, token, uid):
    if token and uid:
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        payload = {'to': uid, 'messages': [{'type': 'text', 'text': msg}]}
        requests.post(url, headers=headers, json=payload)

# --- 3. Tabs ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ Settings")
    line_token = st.text_input("Channel Access Token", type="password", key="tk")
    line_uid = st.text_input("Your User ID", type="password", key="uid")
    sensitivity = st.slider("ความไวของสัญญาณ (%)", 1.0, 10.0, 3.0)

with tab1:
    st.subheader("📌 Watchlist & Auto Signal")
    col_add, _ = st.columns([2, 3])
    new_stock = col_add.text_input("เพิ่มหุ้น (เช่น DELTA.BK):")
    if col_add.button("➕ เพิ่ม"):
        if new_stock:
            conn = sqlite3.connect('portfolio.db'); conn.execute("INSERT OR IGNORE INTO watchlist VALUES (?)", (new_stock.upper(),)); conn.commit(); conn.close()
            st.rerun()

    if st.button("🚀 สแกนและส่งสัญญาณเข้า LINE อัตโนมัติ"):
        db = sqlite3.connect('portfolio.db')
        watchlist = pd.read_sql_query("SELECT * FROM watchlist", db)['ticker'].tolist()
        db.close()
        
        report_msg = "🎯 [Smart Signal Report]\n"
        for s in watchlist:
            df = yf.download(s, period="5d", progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                curr_price = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2])
                change = ((curr_price - prev_close) / prev_close) * 100
                
                # --- Logic การวิเคราะห์ ---
                signal = "➖ ถือ/รอดูอาการ"
                if change >= sensitivity:
                    signal = f"🚀 พุ่งแรง! ({change:.2f}%) แนะนำ: แบ่งขายทำกำไร"
                elif change <= -sensitivity:
                    signal = f"⚠️ ตกหนัก! ({change:.2f}%) แนะนำ: รอถัวหรือคัด"
                elif curr_price > df['Close'].rolling(5).mean().iloc[-1]:
                    signal = "✅ เทรนด์ขาขึ้น แนะนำ: เริ่มสะสม (Buy)"
                
                report_msg += f"\n• {s}: {curr_price:,.2f}\n{signal}\n"
                st.write(f"✅ ตรวจสอบ {s} สำเร็จ")
        
        send_line(report_msg, line_token, line_uid)
        st.success("ส่งสัญญาณวิเคราะห์เข้า LINE เรียบร้อย!")

    # แสดงรายการ Watchlist และปุ่มลบ (เหมือน V14.2)
