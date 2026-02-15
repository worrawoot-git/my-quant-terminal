import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Pro Quant V14.6", layout="wide")
st.title("🏛️ Pro Quant: Dashboard & Smart Auto-Alert")

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    defaults = ['DJI', 'GC=F', 'CL=F', 'BTC-USD', '^SET', 'THB=X','PTT.BK']
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
        requests.post(url, headers=headers, json=payload)

# --- 3. เมนู Tab ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ LINE & Logic Settings")
    line_token = st.text_input("Line Token", type="password", key="tk")
    line_uid = st.text_input("Line User ID", type="password", key="uid")
    sensitivity = st.slider("ระดับความอ่อนไหวการเตือน (%)", 0.5, 5.0, 2.0)

with tab1:
    st.subheader("📌 Watchlist & Market Status")
    
    # ดึงข้อมูล Watchlist
    db = sqlite3.connect('portfolio.db')
    watchlist = pd.read_sql_query("SELECT * FROM watchlist", db)['ticker'].tolist()
    db.close()

    if st.button("🚀 สแกนและส่งสัญญาณเตือนอัตโนมัติ"):
        alert_msg = "🔔 [Pro Quant Alert]\nสรุปสัญญาณวันนี้:\n"
        for s in watchlist:
            df = yf.download(s, period="5d", progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                curr = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2])
                pct = ((curr - prev) / prev) * 100
                
                score = "⚪ ปกติ"
                if pct >= sensitivity: score = f"🔥 พุ่งแรง! (+{pct:.2f}%) แนะนำ: พิจารณาขาย"
                elif pct <= -sensitivity: score = f"📉 ตกหนัก! ({pct:.2f}%) แนะนำ: พิจารณาซื้อ"
                
                alert_msg += f"\n• {s}: {curr:,.2f}\nสถานะ: {score}\n"
        
        send_line_alert(alert_msg, line_token, line_uid)
        st.success("ส่งคะแนนเตือนเข้า LINE เรียบร้อย!")

    # แสดงกราฟและราคา (เหมือน V14.5)
    for s in watchlist:
        with st.expander(f"📊 {s} Insight", expanded=False):
            df_y = yf.download(s, period="1y", progress=False)
            if not df_y.empty:
                if isinstance(df_y.columns, pd.MultiIndex): df_y.columns = df_y.columns.get_level_values(0)
                st.metric(f"ราคา {s}", f"{df_y['Close'].iloc[-1]:,.2f}", f"{((df_y['Close'].iloc[-1]-df_y['Close'].iloc[-2])/df_y['Close'].iloc[-2])*100:+.2f}%")
                st.plotly_chart(px.line(df_y, y='Close', title=f"กราฟ 1 ปี: {s}"), use_container_width=True)

with tab2:
    st.header("📊 Dashboard Overview")
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()

    # แก้ปัญหา Dashboard ว่าง: แสดงสถิติจาก Watchlist แทนถ้ายังไม่มีพอร์ต
    if df_trades.empty:
        st.warning("⚠️ คุณยังไม่มีหุ้นในพอร์ต (Trades) ระบบจึงแสดงภาพรวมจาก Watchlist แทน")
        # แสดงตารางเปรียบเทียบราคาหุ้นใน Watchlist
        watch_data = []
        for s in watchlist:
            d = yf.download(s, period="1d", progress=False)
            if not d.empty:
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                watch_data.append({"Ticker": s, "Current Price": d['Close'].iloc[-1]})
        
        if watch_data:
            df_watch = pd.DataFrame(watch_data)
            st.plotly_chart(px.bar(df_watch, x='Ticker', y='Current Price', title="ราคาหุ้นปัจจุบันใน Watchlist"), use_container_width=True)
            st.table(df_watch)
    else:
        # แสดงกราฟวงกลมพอร์ตจริง (เหมือน V14.3)
        df_sum = df_trades.groupby('ticker').agg({'shares':'sum', 'entry_price':'mean'}).reset_index()
        st.plotly_chart(px.pie(df_sum, values='shares', names='ticker', title="สัดส่วนหุ้นที่ถือครองจริง"), use_container_width=True)
        st.dataframe(df_sum)


