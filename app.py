import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Pro Quant V14.5", layout="wide")
st.title("🏛️ Pro Quant: Market Insight & Alert")

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    defaults = ['PTT.BK', 'CPALL.BK', 'KBANK.BK', 'BTC-USD', 'TSLA']
    for s in defaults:
        c.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (s,))
    conn.commit()
    conn.close()

init_db()

# --- 2. ฟังก์ชันจัดการข้อมูล ---
def get_watchlist():
    conn = sqlite3.connect('portfolio.db'); df = pd.read_sql_query("SELECT * FROM watchlist", conn); conn.close()
    return df['ticker'].tolist()

def add_stock(ticker):
    if ticker:
        conn = sqlite3.connect('portfolio.db'); conn.execute("INSERT OR IGNORE INTO watchlist VALUES (?)", (ticker.upper().strip(),)); conn.commit(); conn.close()

def remove_stock(ticker):
    conn = sqlite3.connect('portfolio.db'); conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,)); conn.commit(); conn.close()

# --- 3. Tabs ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ LINE Settings")
    line_token = st.text_input("LINE Token", type="password", key="tk")
    line_uid = st.text_input("LINE User ID", type="password", key="uid")
    sensitivity = st.slider("ความไวสัญญาณ (%)", 1.0, 10.0, 3.0)

with tab1:
    st.subheader("📌 Watchlist Insight")
    
    # ส่วนเพิ่มหุ้น
    with st.form("add_form", clear_on_submit=True):
        col_input, col_btn = st.columns([3, 1])
        new_ticker = col_input.text_input("ระบุชื่อหุ้นใหม่:")
        if col_btn.form_submit_button("➕ เพิ่มหุ้น"):
            add_stock(new_ticker); st.rerun()

    st.divider()
    
    watchlist = get_watchlist()
    
    # วนลูปแสดงข้อมูลหุ้นแต่ละตัวพร้อมกราฟ 1 ปี
    for s in watchlist:
        with st.expander(f"📈 วิเคราะห์หุ้น: {s}", expanded=True):
            # ดึงข้อมูล 1 ปี
            df_year = yf.download(s, period="1y", progress=False)
            if not df_year.empty:
                if isinstance(df_year.columns, pd.MultiIndex): df_year.columns = df_year.columns.get_level_values(0)
                
                curr_price = float(df_year['Close'].iloc[-1])
                prev_price = float(df_year['Close'].iloc[-2])
                day_change = curr_price - prev_price
                pct_change = (day_change / prev_price) * 100
                
                # แสดงราคาและ Metric
                m1, m2, m3 = st.columns([1, 1, 2])
                m1.metric("ราคาล่าสุด", f"{curr_price:,.2f}", f"{pct_change:+.2f}%")
                
                # ปุ่มลบและปุ่มซื้อ
                if m2.button(f"🗑️ ลบ {s}", key=f"del_{s}"):
                    remove_stock(s); st.rerun()
                
                # กราฟราคา 1 ปี
                fig = px.line(df_year, y='Close', title=f"แนวโน้มราคา {s} ในรอบ 1 ปี", 
                             color_discrete_sequence=['#00ff00'] if pct_change >= 0 else ['#ff0000'])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"ไม่พบข้อมูลสำหรับ {s}")

with tab2:
    # โค้ดส่วน Dashboard (เหมือนเดิม)
    pass
