import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
from datetime import datetime

# --- 1. ตั้งค่าและฐานข้อมูล ---
st.set_page_config(page_title="Pro Quant V13.2", layout="wide")
st.title("🏛️ Pro Quant: Visual Alert & Trader")

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

def add_trade(ticker, price, shares):
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute("INSERT INTO trades (ticker, entry_price, shares, timestamp) VALUES (?, ?, ?, ?)",
              (ticker, price, shares, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

init_db()

# --- 2. เมนู Tab ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Scanner & Trade", "📈 Dashboard", "📜 History", "⚙️ Setup"])

with tab4:
    st.subheader("⚙️ Settings")
    st.session_state.line_token = st.text_input("Channel Access Token", type="password")
    st.session_state.line_uid = st.text_input("Your User ID", type="password")
    tp_target = st.slider("Take Profit %", 1.0, 50.0, 5.0)
    sl_target = st.slider("Stop Loss %", 1.0, 20.0, 3.0)

with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    
    if st.button("🚀 เริ่มสแกนและตรวจสอบพอร์ต"):
        db = sqlite3.connect('portfolio.db')
        df_trades = pd.read_sql_query("SELECT * FROM trades", db)
        db.close()
        
        st.write("---")
        for s in watch_list:
            data = yf.download(s, period="1d", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                curr_price = float(data['Close'].iloc[-1])
                
                # --- ส่วนแสดงราคาและซื้อหุ้น ---
                col_info, col_buy = st.columns([2, 1])
                with col_info:
                    st.write(f"🔍 **{s}**: `{curr_price:,.2f}`")
                    # เช็คสถานะพอร์ต (ถ้ามีหุ้นตัวนี้อยู่แล้ว)
                    if not df_trades.empty and s in df_trades['ticker'].values:
                        entry = df_trades[df_trades['ticker'] == s]['entry_price'].iloc[-1]
                        pnl = ((curr_price / entry) - 1) * 100
                        st.markdown(f"↳ พอร์ตปัจจุบัน: :{'green' if pnl >= 0 else 'red'}[{pnl:.2f}%]")
                
                with col_buy:
                    # เพิ่มช่องใส่จำนวนหุ้นและปุ่มซื้อ
                    n_shares = st.number_input(f"จำนวนหุ้น ({s})", min_value=1, value=100, step=100, key=f"n_{s}")
                    if st.button(f"🛒 ซื้อ {s}", key=f"buy_{s}"):
                        add_trade(s, curr_price, n_shares)
                        st.success(f"บันทึก {s} จำนวน {n_shares} หุ้นสำเร็จ!")

with tab3:
    st.subheader("📜 History")
    # (โค้ดแสดงประวัติเหมือนเดิม)
