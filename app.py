import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Pro Quant V15.1", layout="wide")
st.title("🏛️ Pro Quant: Technical & Risk Visualizer")

# --- 2. ฟังก์ชันฐานข้อมูล ---
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

# --- 3. ส่วนเมนู Tab ---
tab1, tab2, tab3 = st.tabs(["🔍 Scanner & Trade", "📊 Advanced Analysis", "⚙️ Setup"])

with tab3:
    st.subheader("🛡️ Risk & LINE Settings")
    st.session_state.line_token = st.text_input("LINE Token", type="password")
    st.session_state.line_uid = st.text_input("LINE User ID", type="password")
    tp_pct = st.number_input("Take Profit Target (%)", value=5.0)
    sl_pct = st.number_input("Stop Loss Target (%)", value=3.0)

with tab1:
    watch_list = ['PTT.BK', 'AOT.BK', 'CPALL.BK', 'DELTA.BK', 'NVDA', 'AAPL', 'BTC-USD']
    st.info("ตรวจสอบราคาและกด 'ซื้อ' เพื่อนำหุ้นเข้าสู่ระบบวิเคราะห์")
    
    for s in watch_list:
        data = yf.download(s, period="1d", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            curr_price = float(data['Close'].iloc[-1])
            
            col_info, col_buy = st.columns([3, 2])
            with col_info:
                st.write(f"📈 **{s}**: ราคาล่าสุด `{curr_price:,.2f}`")
            with col_buy:
                col_n, col_btn = st.columns([1, 1])
                n_shares = col_n.number_input(f"จำนวน", min_value=1, value=100, step=100, key=f"n_{s}")
                if col_btn.button(f"🛒 ซื้อ {s}", key=f"buy_{s}"):
                    add_trade(s, curr_price, n_shares)
                    st.success(f"บันทึก {s} เข้าพอร์ตแล้ว!")

with tab2:
    db = sqlite3.connect('portfolio.db')
    df_portfolio = pd.read_sql_query("SELECT * FROM trades", db)
    db.close()

    if not df_portfolio.empty:
        selected_stock = st.selectbox("🎯 เลือกหุ้นในพอร์ตเพื่อดู Indicators:", df_portfolio['ticker'].unique())
        df = yf.download(selected_stock, period="3mo", progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # --- คำนวณ RSI & MACD ---
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss))
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # --- สร้างกราฟ 4 ชั้น ---
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                           subplot_titles=(f'Price & Risk ({selected_stock})', 'Volume', 'RSI', 'MACD'),
                           row_heights=[0.5, 0.15, 0.15, 0.2])

        # 1. Price + TP/SL
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Price', line=dict(color='cyan')), row=1, col=1)
        entry = df_portfolio[df_portfolio['ticker'] == selected_stock]['entry_price'].iloc[-1]
        fig.add_hline(y=entry, line_dash="dot", line_color="yellow", annotation_text="Entry", row=1, col=1)
        fig.add_hline(y=entry*(1+tp_pct/100), line_dash="dash", line_color="green", annotation_text="TP", row=1, col=1)
        fig.add_hline(y=entry*(1-sl_pct/100), line_dash="dash", line_color="red", annotation_text="SL", row=1, col=1)

        # 2. Volume
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='gray'), row=2, col=1)
        # 3. RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI', line=dict(color='purple')), row=3, col=1)
        # 4. MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD', line=dict(color='blue')), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name='Signal', line=dict(color='orange')), row=4, col=1)

        fig.update_layout(height=800, template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("ยังไม่มีข้อมูลหุ้นในพอร์ต กรุณาซื้อหุ้นที่หน้า Scanner ก่อนครับ")
