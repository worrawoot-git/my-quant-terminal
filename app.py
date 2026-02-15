import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Pro Quant V9", layout="wide")
st.title("🏛️ Pro Quant: Trend & Dashboard")

# --- 1. ฐานข้อมูล ---
def get_trades():
    db = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()
    return df

# --- 2. ส่วนหน้าจอ ---
watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "📈 Dashboard & Trends", "⚙️ Setup & Alert"])

with tab1:
    st.info("ใช้ปุ่ม Scan เพื่อดูราคาปัจจุบันและบันทึกการซื้อ")
    if st.button("🚀 เริ่มต้นสแกนหุ้น (Refresh)"):
        for s in watch_list:
            df = yf.download(s, period="1d", progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                curr_price = float(df['Close'].iloc[-1])
                st.write(f"📊 **{s}**: `{curr_price:.2f}`")
                if st.button(f"🛒 ซื้อ {s}", key=f"buy_{s}"):
                    db = sqlite3.connect('portfolio.db')
                    db.execute("INSERT INTO trades (ticker, entry_price, shares, timestamp) VALUES (?, ?, ?, ?)",
                              (s, curr_price, 100, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    db.commit()
                    db.close()
                    st.success(f"บันทึก {s} เรียบร้อย!")

with tab2:
    df_trades = get_trades()
    if not df_trades.empty:
        st.subheader("📊 ภาพรวมพอร์ตจำลอง")
        
        # ส่วนกราฟราคาและสัดส่วน
        col_pie, col_line = st.columns([1, 2])
        
        with col_pie:
            # กราฟวงกลมเดิม
            fig_pie = px.pie(df_trades, values='entry_price', names='ticker', title="สัดส่วนหุ้น (Entry Cost)")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_line:
            # --- ใหม่: กราฟเส้นราคาหุ้นย้อนหลัง ---
            selected_stock = st.selectbox("เลือกดูแนวโน้มหุ้น:", df_trades['ticker'].unique())
            hist_df = yf.download(selected_stock, period="1mo", progress=False)
            if isinstance(hist_df.columns, pd.MultiIndex): hist_df.columns = hist_df.columns.get_level_values(0)
            
            fig_line = px.line(hist_df, x=hist_df.index, y='Close', title=f"แนวโน้มราคา {selected_stock} (1 เดือน)")
            fig_line.update_traces(line_color='#00ff00')
            st.plotly_chart(fig_line, use_container_width=True)
        
        st.divider()
        st.write("📋 รายละเอียดพอร์ตในฐานข้อมูล")
        st.dataframe(df_trades, use_container_width=True)
        
        if st.button("📢 ส่งสรุปเข้า LINE"):
            st.info("กำลังประมวลผลการส่งสรุป...")
    else:
        st.info("ยังไม่มีข้อมูลหุ้นในมือ ลองไปซื้อหุ้นที่หน้า Scanner ก่อนครับ")

with tab3:
    st.subheader("🔑 LINE & Alert Setup")
    token = st.text_input("Channel Access Token", type="password")
    uid = st.text_input("Your User ID", type="password")
