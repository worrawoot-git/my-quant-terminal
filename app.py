import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Pro Quant V14.3 Fixed", layout="wide")
st.title("🏛️ Pro Quant: Smart Watchlist & Alert")

# --- 2. ฟังก์ชันฐานข้อมูล (หัวใจหลักที่ทำให้ปุ่มทำงาน) ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    # ตาราง Watchlist
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    # ตาราง Trades (สำหรับ Dashboard)
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    
    # เพิ่ม Default หุ้น 5 ตัวถ้ายังไม่มีในระบบ
    defaults = ['PTT.BK', 'CPALL.BK', 'KBANK.BK', 'BTC-USD', 'TSLA']
    for s in defaults:
        c.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (s,))
    
    conn.commit()
    conn.close()

def get_watchlist():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM watchlist", conn)
    conn.close()
    return df['ticker'].tolist()

def add_stock(ticker):
    if ticker:
        conn = sqlite3.connect('portfolio.db')
        try:
            conn.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (ticker.upper().strip(),))
            conn.commit()
        finally:
            conn.close()

def remove_stock(ticker):
    conn = sqlite3.connect('portfolio.db')
    conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
    conn.commit()
    conn.close()

init_db()

# --- 3. ส่วนเมนู Tab ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ LINE Settings")
    line_token = st.text_input("LINE Token", type="password", key="tk")
    line_uid = st.text_input("LINE User ID", type="password", key="uid")
    sensitivity = st.slider("ความไวสัญญาณ (%)", 1.0, 10.0, 3.0)

with tab1:
    st.subheader("📌 Manage Your Watchlist")
    
    # --- ส่วนการเพิ่มหุ้น (แก้ไขให้ทำงานแน่นอน) ---
    with st.form("add_stock_form", clear_on_submit=True):
        col_input, col_btn = st.columns([3, 1])
        input_ticker = col_input.text_input("ระบุชื่อหุ้นที่ต้องการเพิ่ม (เช่น DELTA.BK, AAPL):")
        submitted = col_btn.form_submit_button("➕ เพิ่มเข้า Watchlist")
        if submitted and input_ticker:
            add_stock(input_ticker)
            st.success(f"เพิ่ม {input_ticker} เรียบร้อย!")
            st.rerun()

    st.divider()

    # --- ส่วนการแสดงผลและส่งสัญญาณ ---
    watchlist = get_watchlist()
    
    if st.button("🚀 สแกนและส่งสัญญาณวิเคราะห์เข้า LINE"):
        if not line_token or not line_uid:
            st.error("กรุณากรอกรหัส LINE ในหน้า Setup ก่อนครับ")
        else:
            report_msg = "🎯 [Smart Signal Report]\n"
            for s in watchlist:
                df = yf.download(s, period="5d", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    curr_price = float(df['Close'].iloc[-1])
                    prev_close = float(df['Close'].iloc[-2])
                    change = ((curr_price - prev_close) / prev_close) * 100
                    
                    signal = "➖ Hold"
                    if change >= sensitivity: signal = f"🚀 High Volatility (+{change:.2f}%) Sell?"
                    elif change <= -sensitivity: signal = f"⚠️ Price Drop ({change:.2f}%) Buy/Wait?"
                    elif curr_price > df['Close'].rolling(5).mean().iloc[-1]: signal = "✅ Trend Up: Buy/Hold"
                    
                    report_msg += f"\n• {s}: {curr_price:,.2f}\n{signal}\n"
            
            # ส่งเข้า LINE
            url = 'https://api.line.me/v2/bot/message/push'
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {line_token}'}
            payload = {'to': line_uid, 'messages': [{'type': 'text', 'text': report_msg}]}
            requests.post(url, headers=headers, json=payload)
            st.success("ส่งสัญญาณสรุปยอดเข้า LINE เรียบร้อย!")

    # --- ส่วนปุ่มลบหุ้นออกจาก Watchlist ---
    st.write("### รายการหุ้นที่คุณติดตามอยู่:")
    cols = st.columns(3)
    for i, s in enumerate(watchlist):
        with cols[i % 3]:
            st.write(f"**{s}**")
            if st.button(f"🗑️ ลบ {s}", key=f"del_{s}"):
                remove_stock(s)
                st.rerun()

# --- Tab 2: Dashboard (รวมยอดหุ้นซ้ำ) ---
with tab2:
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()
    if not df_trades.empty:
        df_summary = df_trades.groupby('ticker').agg({'shares':'sum', 'entry_price':'mean'}).reset_index()
        st.plotly_chart(px.pie(df_summary, values='shares', names='ticker', title="สัดส่วนหุ้นในพอร์ต"))
        st.dataframe(df_summary, use_container_width=True)
    else:
        st.info("ยังไม่มีประวัติการซื้อหุ้น")
