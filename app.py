import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
import plotly.express as px
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Pro Quant V14.6.4", layout="wide")
st.title("🏛️ Pro Quant: Zero-Error Market Watch")

def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS watchlist (ticker TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    
    # ดัชนีหลักที่เอาหุ้นรายตัวที่คุณไม่ต้องการออกแล้ว
    defaults = ['^SET.BK', '^DJI', 'GC=F', 'CL=F', 'BTC-USD', 'THB=X']
    for s in defaults:
        c.execute("INSERT OR IGNORE INTO watchlist (ticker) VALUES (?)", (s,))
    conn.commit()
    conn.close()

init_db()

# --- 2. ฟังก์ชันส่ง LINE ---
def send_line(msg, token, uid):
    if token and uid:
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
        payload = {'to': uid, 'messages': [{'type': 'text', 'text': msg}]}
        try: requests.post(url, headers=headers, json=payload, timeout=10)
        except: pass

# --- 3. หน้าจอหลัก ---
tab1, tab2, tab3 = st.tabs(["🔍 Smart Monitor", "📊 Dashboard", "⚙️ Setup"])

with tab3:
    st.subheader("⚙️ Settings")
    line_token = st.text_input("Line Token", type="password", key="tk")
    line_uid = st.text_input("Line User ID", type="password", key="uid")
    sensitivity = st.slider("เกณฑ์แจ้งเตือนความผิดปกติ (%)", 0.5, 5.0, 1.5)

with tab1:
    st.subheader("📌 Global Market Watch")
    
    # ดึงรายชื่อจาก DB
    db = sqlite3.connect('portfolio.db')
    watchlist = pd.read_sql_query("SELECT * FROM watchlist", db)['ticker'].tolist()
    db.close()

    if st.button("🚀 สแกนและแจ้งเตือนเข้า LINE"):
        alert_msg = f"📢 [Market Update] {datetime.now().strftime('%H:%M')}\n"
        for s in watchlist:
            df = yf.download(s, period="5d", progress=False)
            if not df.empty and len(df) >= 2:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                curr, prev = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
                pct = ((curr - prev) / prev) * 100
                status = "🔥 พุ่ง!" if pct >= sensitivity else ("⚠️ ร่วง!" if pct <= -sensitivity else "⚪ ปกติ")
                alert_msg += f"• {s}: {curr:,.2f} ({pct:+.2f}%) [{status}]\n"
        send_line(alert_msg, line_token, line_uid)
        st.success("ส่งข้อมูลเข้า LINE แล้ว!")

    # แก้ไขจุดที่ทำให้เกิด IndexError ในรูป lc1.png
    for s in watchlist:
        with st.expander(f"📊 {s} Insight", expanded=(s == '^SET.BK')):
            # ดึงข้อมูลย้อนหลัง 1 ปี
            df_y = yf.download(s, period="1y", progress=False)
            
            # --- ส่วนที่เพิ่มเพื่อแก้ Error ---
            if not df_y.empty and len(df_y) >= 2:
                if isinstance(df_y.columns, pd.MultiIndex): df_y.columns = df_y.columns.get_level_values(0)
                
                c_val = df_y['Close'].iloc[-1]
                p_val = df_y['Close'].iloc[-2] # จุดที่เคย Error
                change_pct = ((c_val - p_val) / p_val) * 100
                
                st.metric(s, f"{c_val:,.2f}", f"{change_pct:+.2f}%")
                st.plotly_chart(px.line(df_y, y='Close', title=f"Trend 1 Year: {s}"), use_container_width=True)
            else:
                st.warning(f"⚠️ กำลังรอข้อมูลล่าสุดสำหรับ {s} หรือตลาดปิดทำการ")
            
            if st.button(f"🗑️ ลบ {s}", key=f"del_{s}"):
                conn = sqlite3.connect('portfolio.db')
                conn.execute("DELETE FROM watchlist WHERE ticker = ?", (s,))
                conn.commit(); conn.close(); st.rerun()

with tab2:
    st.header("📊 Portfolio Dashboard")
    # ป้องกัน NameError ในรูป line26.png
    db = sqlite3.connect('portfolio.db')
    df_trades = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()

    if df_trades.empty:
        st.info("💡 พอร์ตว่างเปล่า ระบบจะดึงราคาล่าสุดจาก Watchlist มาแสดงให้ดูเป็นตัวอย่าง")
        # (แสดงกราฟแท่งราคาปัจจุบันจาก Watchlist เหมือน V14.6)
    else:
        # แสดงพอร์ตจริง
        df_sum = df_trades.groupby('ticker').agg({'shares':'sum', 'entry_price':'mean'}).reset_index()
        st.plotly_chart(px.pie(df_sum, values='shares', names='ticker', title="สัดส่วนหุ้นที่ถือจริง"))
