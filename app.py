import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="Pro Quant V15", layout="wide")
st.title("🏛️ Pro Quant: Technical & Risk Visualizer")

# --- ฟังก์ชันจัดการพอร์ต ---
def get_trades():
    db = sqlite3.connect('portfolio.db')
    df = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()
    return df

# --- Tab Layout ---
tab1, tab2, tab3 = st.tabs(["🔍 Scanner", "📊 Advanced Analysis", "⚙️ Setup"])

with tab3:
    st.subheader("🛡️ Risk Management Settings")
    tp_pct = st.number_input("Take Profit (%)", value=5.0)
    sl_pct = st.number_input("Stop Loss (%)", value=3.0)

with tab1:
    st.info("ใช้หน้า Scanner เพื่อบันทึกการซื้อหุ้น (เหมือนเวอร์ชัน V14)")
    # (โค้ดส่วนปุ่มซื้อคงเดิมจาก V14)

with tab2:
    df_portfolio = get_trades()
    if not df_portfolio.empty:
        selected_stock = st.selectbox("เลือกหุ้นเพื่อวิเคราะห์เทคนิค:", df_portfolio['ticker'].unique())
        
        # ดึงข้อมูลย้อนหลัง 3 เดือนเพื่อให้คำนวณ Indicator ได้แม่นยำ
        df = yf.download(selected_stock, period="3mo", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # --- คำนวณ Indicators ---
        # 1. RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))

        # 2. MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # --- สร้างกราฟ Subplots ---
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05, 
                           subplot_titles=(f'Price & Target ({selected_stock})', 'Volume', 'RSI', 'MACD'),
                           row_heights=[0.5, 0.15, 0.15, 0.2])

        # A. กราฟราคา
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='white')), row=1, col=1)
        
        # วาดเส้น TP/SL จากต้นทุนล่าสุดในพอร์ต
        entry_price = df_portfolio[df_portfolio['ticker'] == selected_stock]['entry_price'].iloc[-1]
        tp_price = entry_price * (1 + tp_pct/100)
        sl_price = entry_price * (1 - sl_pct/100)
        
        fig.add_hline(y=entry_price, line_dash="dot", line_color="yellow", annotation_text="Entry", row=1, col=1)
        fig.add_hline(y=tp_price, line_dash="dash", line_color="green", annotation_text="Take Profit", row=1, col=1)
        fig.add_hline(y=sl_price, line_dash="dash", line_color="red", annotation_text="Stop Loss", row=1, col=1)

        # B. Volume
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='gray'), row=2, col=1)

        # C. RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

        # D. MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue')), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='Signal', line=dict(color='orange')), row=4, col=1)

        fig.update_layout(height=800, template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("กรุณาซื้อหุ้นเข้าพอร์ตก่อนเพื่อดูจุด TP/SL บนกราฟครับ")
