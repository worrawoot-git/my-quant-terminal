import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าพื้นฐาน ---
st.set_page_config(page_title="Pro Quant V14.1", layout="wide")
st.title("🏛️ Pro Quant: Full Visualization Dashboard")

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
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

# --- Tab 4: ตั้งค่ารหัส LINE ---
with tab4:
    st.subheader("⚙️ LINE Alert Settings")
    line_token = st.text_input("Channel Access Token", type="password", key="tk")
    line_uid = st.text_input("Your User ID", type="password", key="uid")
    st.info("กรอกรหัสเสร็จแล้ว ไปที่หน้า Dashboard เพื่อกดส่งรายงานได้เลยครับ")

# --- Tab 1: หน้าสแกนและซื้อหุ้น (กลับมาแล้ว!) ---
with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    if st.button("🚀 อัปเดตราคาล่าสุด"):
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

# --- Tab 2: หน้า Dashboard กราฟวงกลมและเส้น (กลับมาแล้ว!) ---
with tab2:
    st.header("📊 Visualization Center")
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()

    if not df_trades.empty:
        df_trades['total_cost'] = df_trades['entry_price'] * df_trades['shares']
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            fig_pie = px.pie(df_trades, values='total_cost', names='ticker', 
                             title="💰 สัดส่วนเงินลงทุนในพอร์ต (Cost Basis)")
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_m2:
            selected_stock = st.selectbox("🎯 เลือกหุ้นเพื่อดูแนวโน้ม:", df_trades['ticker'].unique())
            hist_data = yf.download(selected_stock, period="1mo", progress=False)
            if isinstance(hist_data.columns, pd.MultiIndex): hist_data.columns = hist_data.columns.get_level_values(0)
            fig_line = px.line(hist_data, y='Close', title=f"📈 แนวโน้มราคา {selected_stock}")
            st.plotly_chart(fig_line, use_container_width=True)

        st.divider()
        # --- ปุ่มส่ง LINE ---
        if st.button("📢 ส่งสรุปพอร์ตเข้า LINE ตอนนี้"):
            if line_token and line_uid:
                msg = f"📊 สรุปพอร์ต Pro Quant\n------------------\n"
                for _, row in df_trades.iterrows():
                    msg += f"• {row['ticker']}: {row['shares']} หุ้น\n"
                
                url = 'https://api.line.me/v2/bot/message/push'
                headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {line_token}'}
                payload = {'to': line_uid, 'messages': [{'type': 'text', 'text': msg}]}
                res = requests.post(url, headers=headers, json=payload)
                if res.status_code == 200: st.success("✅ ส่งเข้า LINE แล้ว!")
                else: st.error(f"❌ ล้มเหลว: {res.text}")
            else:
                st.warning("⚠️ กรุณากรอกรหัสในหน้า Setup ก่อน")
    else:
        st.info("ยังไม่มีหุ้นในพอร์ต")

# --- Tab 3: ประวัติ ---
with tab3:
    db = sqlite3.connect('portfolio.db')
    df_hist = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC", db)
    db.close()
    st.dataframe(df_hist, use_container_width=True)
