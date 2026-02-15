import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Pro Quant V9.1", layout="wide")
st.title("🏛️ Pro Quant: Trend & Dashboard (Fixed)")

# --- 1. ฟังก์ชันจัดการฐานข้อมูล ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def add_to_portfolio(ticker, price):
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute("INSERT INTO trades (ticker, entry_price, shares, timestamp) VALUES (?, ?, ?, ?)",
              (ticker, price, 100, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

init_db()

# --- 2. ส่วนเมนู ---
watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "📈 Dashboard & Trends", "⚙️ Setup & Alert"])

with tab1:
    st.info("กดปุ่ม 'ซื้อ' เพื่อบันทึกหุ้นเข้าพอร์ตจำลอง")
    
    # ดึงราคาหุ้นทั้งหมดมาก่อน เพื่อลดการรีโหลดซ้ำซ้อน
    if st.button("🚀 อัปเดตราคาล่าสุด (Refresh Prices)"):
        st.session_state.prices_loaded = True

    for s in watch_list:
        with st.container():
            # ดึงข้อมูลรายตัว
            data = yf.download(s, period="1d", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                curr_price = float(data['Close'].iloc[-1])
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📈 **{s}** ราคาปัจจุบัน: `{curr_price:,.2f}`")
                with col2:
                    # ใช้ปุ่มซื้อพร้อมฟังก์ชัน Callback เพื่อความเสถียร
                    if st.button(f"🛒 ซื้อ {s}", key=f"btn_{s}"):
                        add_to_portfolio(s, curr_price)
                        st.success(f"✅ บันทึก {s} ที่ราคา {curr_price} แล้ว! ไปดูที่หน้า Dashboard ได้เลย")

with tab2:
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()
    
    if not df_trades.empty:
        st.subheader("📊 สรุปพอร์ตจำลองของคุณ")
        
        # ส่วนแสดง Dashboard และกราฟ
        col_pie, col_line = st.columns([1, 2])
        with col_pie:
            fig_pie = px.pie(df_trades, values='entry_price', names='ticker', title="สัดส่วนหุ้นที่ซื้อ")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_line:
            selected = st.selectbox("เลือกดูแนวโน้มหุ้นในพอร์ต:", df_trades['ticker'].unique())
            hist = yf.download(selected, period="1mo", progress=False)
            if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
            fig_line = px.line(hist, x=hist.index, y='Close', title=f"Trend ของ {selected}")
            st.plotly_chart(fig_line, use_container_width=True)
            
        st.divider()
        st.write("📋 รายการหุ้นที่บันทึกไว้")
        st.dataframe(df_trades, use_container_width=True)
        
        if st.button("🗑️ ล้างพอร์ตทั้งหมด"):
            conn = sqlite3.connect('portfolio.db')
            conn.execute("DELETE FROM trades")
            conn.commit()
            conn.close()
            st.rerun()
    else:
        st.warning("⚠️ ยังไม่มีข้อมูลหุ้นในพอร์ต กรุณากดซื้อจากหน้า Scanner ก่อนครับ")

with tab3:
    st.subheader("🔑 LINE Config")
    st.text_input("Channel Access Token", type="password", key="token_input")
    st.text_input("Your User ID", type="password", key="uid_input")
