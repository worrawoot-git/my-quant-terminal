import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import sqlite3
from datetime import datetime

st.set_page_config(page_title="Pro Quant Terminal V7", layout="wide")
st.title("🏛️ Pro Quant: Daily Summary System")

# --- 🛠️ ฐานข้อมูลเดิมจาก V6 ---
def init_db():
    conn = sqlite3.connect('portfolio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  ticker TEXT, entry_price REAL, shares INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def get_trades():
    conn = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()
    return df

init_db()

# --- ⚙️ ส่วนตั้งค่า ---
tab1, tab2, tab3 = st.tabs(["🔍 Market Scanner", "💼 Permanent Portfolio", "⚙️ Setup"])

with tab3:
    st.subheader("LINE Config")
    token = st.text_input("Channel Access Token", type="password")
    uid = st.text_input("Your User ID", type="password")

with tab1:
    # (โค้ด Scanner และปุ่ม Buy จาก V6 ใส่ตรงนี้ได้เหมือนเดิมครับ)
    st.info("ใช้หน้า Scanner เพื่อเลือกหุ้นเข้าพอร์ตจำลองของคุณ")

with tab2:
    st.subheader("📊 Your Real-time Portfolio")
    df_trades = get_trades()
    
    if not df_trades.empty:
        summary_list = []
        total_pnl = 0
        
        with st.spinner('กำลังคำนวณยอดสรุป...'):
            for _, row in df_trades.iterrows():
                live = yf.download(row['ticker'], period="1d", progress=False)
                if isinstance(live.columns, pd.MultiIndex): live.columns = live.columns.get_level_values(0)
                
                current_p = live['Close'].iloc[-1]
                pnl = (current_p - row['entry_price']) * row['shares']
                pnl_pct = ((current_p / row['entry_price']) - 1) * 100
                total_pnl += pnl
                
                summary_list.append({
                    'Ticker': row['ticker'],
                    'Entry': row['entry_price'],
                    'Current': current_p,
                    'P/L ($)': pnl,
                    'P/L (%)': pnl_pct
                })
        
        df_summary = pd.DataFrame(summary_list)
        st.table(df_summary.style.format({'Entry': '{:.2f}', 'Current': '{:.2f}', 'P/L ($)': '{:.2f}', 'P/L (%)': '{:.2f}%'}))
        
        st.metric("Total Profit/Loss", f"${total_pnl:.2f}", delta=f"{total_pnl:.2f}")

        # --- 🔔 ปุ่มส่งสรุปเข้า LINE ---
        if st.button("📢 ส่งสรุปพอร์ตเข้า LINE ตอนนี้"):
            if token and uid:
                now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                report_msg = f"📋 สรุปพอร์ตรายวัน ({now_str})\n"
                report_msg += "------------------\n"
                
                for _, r in df_summary.iterrows():
                    icon = "🟢" if r['P/L ($)'] >= 0 else "🔴"
                    report_msg += f"{icon} {r['Ticker']}: {r['P/L (%)']:.2f}% (${r['P/L ($)']:.2f})\n"
                
                report_msg += "------------------\n"
                report_msg += f"💰 ยอดรวมทั้งหมด: ${total_pnl:.2f}"
                
                # ส่งเข้า LINE API
                url = 'https://api.line.me/v2/bot/message/push'
                headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
                payload = {'to': uid, 'messages': [{'type': 'text', 'text': report_msg}]}
                res = requests.post(url, headers=headers, json=payload)
                
                if res.status_code == 200:
                    st.success("ส่งรายงานสรุปเข้า LINE เรียบร้อยแล้ว!")
                else:
                    st.error("ส่งไม่สำเร็จ กรุณาเช็ครหัส Token/User ID")
            else:
                st.warning("กรุณากรอกรหัสใน Tab Setup ก่อนครับ")
