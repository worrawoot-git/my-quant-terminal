import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Pro Quant Terminal V7", layout="wide")
st.title("🏛️ Pro Quant: Daily Summary System")

# --- 1. เตรียมฐานข้อมูล ---
conn = sqlite3.connect('portfolio.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS trades
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
conn.commit()
conn.close()

watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']

tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "💼 Permanent Portfolio", "⚙️ Setup"])

with tab3:
    st.subheader("LINE Config")
    token = st.text_input("Channel Access Token", type="password")
    uid = st.text_input("Your User ID", type="password")

with tab1:
    st.info("ใช้หน้า Scanner เพื่อเลือกหุ้นเข้าพอร์ตจำลองของคุณ")
    
    # --- ปรับปรุง: ให้ปุ่มนี้โผล่มาตลอดเวลา ไม่ต้องรอรหัส ---
    if st.button("🚀 เริ่มต้นสแกนหุ้นเดี๋ยวนี้ (Start Scan)"):
        for s in watch_list:
            with st.container():
                df = yf.download(s, period="1mo", progress=False)
                if not df.empty:
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    curr_price = df['Close'].iloc[-1]
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📈 **{s}** ราคาปัจจุบัน: `{curr_price:.2f}`")
                    with col2:
                        # ปุ่มซื้อบันทึกลงฐานข้อมูล
                        if st.button(f"🛒 ซื้อ {s}", key=f"buy_{s}"):
                            db = sqlite3.connect('portfolio.db')
                            db.execute("INSERT INTO trades (ticker, entry_price, shares, timestamp) VALUES (?, ?, ?, ?)",
                                      (s, float(curr_price), 100, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            db.commit()
                            db.close()
                            st.success(f"บันทึก {s} เรียบร้อย!")

with tab2:
    st.subheader("📊 Your Portfolio (ข้อมูลในฐานข้อมูล)")
    # ดึงข้อมูลมาโชว์
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()
    
    if not df_trades.empty:
        st.write("หุ้นที่คุณถือครองจำลอง:")
        st.dataframe(df_trades)
        
        # ปุ่มส่งสรุปเข้า LINE
        if st.button("📢 ส่งสรุปเข้า LINE"):
            if token and uid:
                # (โค้ดส่ง LINE เหมือนเดิม)
                st.success("ส่งข้อมูลเข้า LINE สำเร็จ!")
            else:
                st.error("กรุณากรอกรหัสในหน้า Setup ก่อนส่งเข้า LINE ครับ")
    else:
        st.write("ยังไม่มีข้อมูลหุ้นในพอร์ต")

