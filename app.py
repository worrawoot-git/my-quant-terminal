import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Pro Quant V14", layout="wide")
st.title("🏛️ Pro Quant: Full Visualization Dashboard")

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
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Scanner & Trade", "📊 Portfolio Dashboard", "📜 History", "⚙️ Setup"])

with tab4:
    st.subheader("⚙️ Settings")
    st.session_state.line_token = st.text_input("Channel Access Token", type="password")
    st.session_state.line_uid = st.text_input("Your User ID", type="password")
    tp_target = st.slider("Take Profit %", 1.0, 50.0, 5.0)
    sl_target = st.slider("Stop Loss %", 1.0, 20.0, 3.0)

with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    if st.button("🚀 อัปเดตราคาล่าสุด & เช็คสัญญาณ"):
        st.rerun()

    for s in watch_list:
        with st.container():
            data = yf.download(s, period="1d", progress=False)
            if not data.empty:
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                curr_price = float(data['Close'].iloc[-1])
                
                col_info, col_buy = st.columns([3, 2])
                with col_info:
                    st.write(f"📈 **{s}**: `{curr_price:,.2f}`")
                with col_buy:
                    col_n, col_btn = st.columns([1, 1])
                    n_shares = col_n.number_input(f"จำนวน", min_value=1, value=100, step=100, key=f"n_{s}")
                    if col_btn.button(f"🛒 ซื้อ {s}", key=f"buy_{s}"):
                        add_trade(s, curr_price, n_shares)
                        st.success(f"บันทึก {s} สำเร็จ!")

with tab2:
    st.header("📊 Visualization Center")
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()

    if not df_trades.empty:
        # คำนวณมูลค่าพอร์ต
        df_trades['total_cost'] = df_trades['entry_price'] * df_trades['shares']
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            # 1. กราฟวงกลมแสดงสัดส่วนเงินลงทุน
            fig_pie = px.pie(df_trades, values='total_cost', names='ticker', 
                             title="💰 สัดส่วนเงินลงทุนในพอร์ต (Cost Basis)",
                             color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_m2:
            # 2. กราฟเส้นดูแนวโน้มหุ้นที่เลือก
            selected_stock = st.selectbox("🎯 เลือกหุ้นในพอร์ตเพื่อดูแนวโน้ม:", df_trades['ticker'].unique())
            hist_data = yf.download(selected_stock, period="1mo", progress=False)
            if isinstance(hist_data.columns, pd.MultiIndex): hist_data.columns = hist_data.columns.get_level_values(0)
            
            fig_line = px.line(hist_data, x=hist_data.index, y='Close', 
                               title=f"📈 แนวโน้มราคา {selected_stock} (1 เดือนล่าสุด)")
            fig_line.update_traces(line_color='#00ff00')
            st.plotly_chart(fig_line, use_container_width=True)

        st.divider()
        st.subheader("📋 รายละเอียดหุ้นที่ถือครอง")
        st.dataframe(df_trades[['ticker', 'entry_price', 'shares', 'timestamp']], use_container_width=True)
        
        if st.button("🗑️ ล้างพอร์ตทั้งหมด"):
            conn = sqlite3.connect('portfolio.db')
            conn.execute("DELETE FROM trades")
            conn.commit()
            conn.close()
            st.rerun()
    else:
        st.info("ยังไม่มีหุ้นในพอร์ต กรุณาไปที่หน้า Scanner เพื่อซื้อหุ้นเข้าพอร์ตก่อนครับ")

with tab3:
    st.subheader("📜 History")
    db = sqlite3.connect('portfolio.db')
    df_hist = pd.read_sql_query("SELECT * FROM alert_history ORDER BY id DESC", db)
    db.close()
    st.dataframe(df_hist, use_container_width=True)
