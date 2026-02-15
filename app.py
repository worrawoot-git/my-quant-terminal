import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Pro Quant V14.3 Pro", layout="wide")
st.title("🏛️ Pro Quant: Watchlist & Smart Alert")

# --- 2. ระบบฐานข้อมูล (จัดการ Default และ Watchlist) ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    # ใส่ Default Watchlist 5 ตัว
    defaults = ['PTT.BK', 'CPALL.BK', 'KBANK.BK', 'BTC-USD', 'TSLA']
    for s in defaults:
        c.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (s,))
    conn.commit()
    conn.close()

init_db()

# --- 3. ฟังก์ชันการทำงาน ---
def get_watchlist():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM watchlist", conn)
    conn.close()
    return df['ticker'].tolist()

def add_stock(ticker):
    if ticker:
        conn = sqlite3.connect('portfolio.db')
        conn.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker.upper().strip(),))
        conn.commit()
        conn.close()

def remove_stock(ticker):
    conn = sqlite3.connect('portfolio.db')
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()

# --- 4. เมนู Tab ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ LINE Settings")
    line_token = st.text_input("LINE Token", type="password", key="tk")
    line_uid = st.text_input("LINE User ID", type="password", key="uid")
    sensitivity = st.slider("ความไวสัญญาณ (%)", 1.0, 10.0, 3.0)

with tab1:
    st.subheader("📌 จัดการ Watchlist ของคุณ")
    
    # ส่วนเพิ่มหุ้นแบบ Form (ป้องกันกดแล้วไม่ทำงาน)
    with st.form("add_form", clear_on_submit=True):
        col_input, col_btn = st.columns([3, 1])
        new_ticker = col_input.text_input("ระบุชื่อหุ้นใหม่ (เช่น DELTA.BK, AAPL):")
        if col_btn.form_submit_button("➕ เพิ่มหุ้น"):
            if new_ticker:
                add_stock(new_ticker)
                st.rerun()

    st.divider()
    
    # ส่วนสแกนและส่ง LINE
    watchlist = get_watchlist()
    if st.button("🚀 สแกนและส่งสัญญาณสรุปเข้า LINE"):
        if line_token and line_uid:
            report_msg = "🎯 [Smart Signal Report]\n"
            for s in watchlist:
                df = yf.download(s, period="5d", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    curr = float(df['Close'].iloc[-1])
                    prev = float(df['Close'].iloc[-2])
                    diff = ((curr - prev) / prev) * 100
                    
                    signal = "➖ Hold"
                    if diff >= sensitivity: signal = f"🚀 พุ่งแรง! (+{diff:.2f}%)"
                    elif diff <= -sensitivity: signal = f"⚠️ ตกหนัก! ({diff:.2f}%)"
                    
                    report_msg += f"\n• {s}: {curr:,.2f}\n{signal}\n"
            
            requests.post('https://api.line.me/v2/bot/message/push', 
                          headers={'Authorization': f'Bearer {line_token}'},
                          json={'to': line_uid, 'messages': [{'type': 'text', 'text': report_msg}]})
            st.success("ส่งเข้า LINE เรียบร้อย!")

    # ส่วนแสดงรายชื่อและปุ่มลบ (แบ่งเป็น 3 คอลัมน์เหมือนในรูป line26)
    st.write("### รายการหุ้นที่คุณติดตามอยู่:")
    cols = st.columns(3)
    for i, s in enumerate(watchlist):
        with cols[i % 3]:
            st.info(f"**{s}**")
            if st.button(f"🗑️ ลบ {s}", key=f"del_{s}"):
                remove_stock(s)
                st.rerun()

with tab2:
    st.header("📊 Portfolio Visualization")
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()
    
    if not df_trades.empty:
        # รวมยอดหุ้นซ้ำให้เป็นบรรทัดเดียว
        df_sum = df_trades.groupby('ticker').agg({'shares':'sum', 'entry_price':'mean'}).reset_index()
        st.plotly_chart(px.pie(df_sum, values='shares', names='ticker', title="สัดส่วนหุ้นในพอร์ต"), use_container_width=True)
        st.dataframe(df_sum, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลการซื้อหุ้นในพอร์ต (ไปที่หน้า Monitor เพื่อกดซื้อหุ้นก่อนครับ)")
