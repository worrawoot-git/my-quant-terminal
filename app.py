import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Pro Quant V13", layout="wide")
st.title("🏛️ Pro Quant: Visual Alert System")

# --- 1. ฐานข้อมูล ---
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

# --- 2. ส่วนเมนู ---
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Scanner", "📈 Dashboard", "📜 History", "⚙️ Setup"])

with tab4:
    st.subheader("🔑 Config & Risk")
    st.session_state.line_token = st.text_input("Channel Access Token", type="password")
    st.session_state.line_uid = st.text_input("Your User ID", type="password")
    tp_target = st.slider("เป้าหมายกำไร (%)", 1, 50, 10)
    sl_target = st.slider("จุดตัดขาดทุน (%)", 1, 20, 5)

with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    if st.button("🚀 สแกนหุ้น & ส่งสัญญาณพร้อมกราฟ"):
        db = sqlite3.connect('portfolio.db')
        df_trades = pd.read_sql_query("SELECT * FROM trades", db)
        db.close()
        
        for s in watch_list:
            data = yf.download(s, period="1mo", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                curr_price = float(data['Close'].iloc[-1])
                st.write(f"📈 **{s}**: `{curr_price:,.2f}`")
                
                if not df_trades.empty and s in df_trades['ticker'].values:
                    entry = df_trades[df_trades['ticker'] == s]['entry_price'].iloc[-1]
                    pnl_pct = ((curr_price / entry) - 1) * 100
                    
                    if pnl_pct >= tp_target or pnl_pct <= -sl_target:
                        status = "💰 TAKE PROFIT" if pnl_pct >= tp_target else "⚠️ STOP LOSS"
                        add_alert_history(s, status, pnl_pct, curr_price)
                        
                        # --- ส่ง LINE พร้อมลิงก์กราฟย้อนหลัง ---
                        chart_url = f"https://finance.yahoo.com/chart/{s}"
                        alert_msg = f"{status}\nหุ้น: {s}\nกำไร/ขาดทุน: {pnl_pct:.2f}%\nราคาปัจจุบัน: {curr_price}\nดูรายละเอียด: {chart_url}"
                        
                        if 'line_token' in st.session_state and 'line_uid' in st.session_state:
                            url = 'https://api.line.me/v2/bot/message/push'
                            headers = {
                                'Content-Type': 'application/json',
                                'Authorization': f"Bearer {st.session_state.line_token}"
                            }
                            # ส่งเป็นข้อความที่มีลิงก์ ซึ่ง LINE จะพรีวิวรูปกราฟให้โดยอัตโนมัติในหลายๆ กรณี
                            payload = {
                                'to': st.session_state.line_uid,
                                'messages': [{'type': 'text', 'text': alert_msg}]
                            }
                            requests.post(url, headers=headers, json=payload)
                            st.warning(f"ส่งสัญญาณพร้อมลิงก์กราฟของ {s} แล้ว!")

with tab3:
    st.subheader("📜 ประวัติการแจ้งเตือน")
    db = sqlite3.connect('portfolio.db')
    df_history = pd.read_sql_query("SELECT * FROM alert_history ORDER BY id DESC", db)
    db.close()
    st.dataframe(df_history, use_container_width=True)
