import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from prophet import Prophet
from datetime import datetime
import requests

st.set_page_config(page_title="Pro Quant Terminal", layout="wide")
st.title("🏛️ Pro Quant Mini Bloomberg Terminal")

ticker = st.sidebar.text_input("Enter Ticker", value="NVDA").upper().strip()
period = st.sidebar.selectbox("History Period", ["1y", "2y", "5y"])
watch_list = ['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'BTC-USD', 'CPALL.BK', 'PTT.BK']

tab1, tab2, tab3, tab4 = st.tabs(["📈 Terminal & AI", "🔍 Market Scanner", "📊 YTD Performance", "🧪 Strategy Backtest"])

# --- Tab 2: นี่คือส่วนที่เพิ่มช่องกรอกรหัส ---
with tab2:
    st.subheader("🔍 Market Scanner & LINE Alert")
    
    # เพิ่มช่องกรอกข้อมูลตรงนี้
    line_access_token = st.text_input("1. วาง Channel Access Token ตรงนี้", type="password")
    line_user_id = st.text_input("2. วาง Your User ID ตรงนี้ (ที่ขึ้นต้นด้วยตัว U)")

    if st.button("🚀 Start Scan & Send to LINE"):
        if not line_access_token or not line_user_id:
            st.error("❌ กรุณากรอกรหัสทั้ง 2 ช่องก่อนกดสแกนครับ!")
        else:
            results = []
            alert_stocks = []
            with st.spinner('กำลังสแกนหุ้นและส่งข้อมูลเข้า LINE...'):
                for s in watch_list:
                    d = yf.download(s, period="1mo", progress=False)
                    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                    
                    diff = d['Close'].diff()
                    gain = (diff.where(diff > 0, 0)).rolling(window=14).mean()
                    loss = (-diff.where(diff < 0, 0)).rolling(window=14).mean()
                    last_rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
                    
                    results.append({"Ticker": s, "Price": round(d['Close'].iloc[-1], 2), "RSI": round(last_rsi, 2)})
                    
                    # ตั้งค่าให้แจ้งเตือนถ้า RSI < 45 (เพื่อทดสอบการส่งข้อความ)
                    if last_rsi < 45: 
                        alert_stocks.append(f"✅ {s}: RSI = {last_rsi:.2f}")

                st.table(pd.DataFrame(results))

                if alert_stocks:
                    full_msg = "🏛️ Quant Alert!\n" + "\n".join(alert_stocks)
                    url = 'https://api.line.me/v2/bot/message/push'
                    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {line_access_token}'}
                    payload = {'to': line_user_id, 'messages': [{'type': 'text', 'text': full_msg}]}
                    res = requests.post(url, headers=headers, json=payload)
                    if res.status_code == 200:
                        st.success("🔔 บอทส่งข้อความเข้า LINE เรียบร้อยแล้ว!")
                    else:
                        st.error(f"Error: {res.text}")

# (ส่วน Tab อื่นๆ คงไว้เหมือนเดิม...)
