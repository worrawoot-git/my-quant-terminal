import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from prophet import Prophet
from datetime import datetime
import matplotlib.pyplot as plt

# --- 1. การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Pro Quant Terminal", layout="wide")
st.title("🏛️ Pro Quant Mini Bloomberg Terminal")

# --- 2. Sidebar สำหรับควบคุม ---
st.sidebar.header("Configuration")
ticker = st.sidebar.text_input("Enter Ticker (e.g., NVDA, BTC-USD, PTT.BK)", value="NVDA").upper().strip()
period = st.sidebar.selectbox("History Period", ["1y", "2y", "5y"], index=0)

watch_list = ['AAPL', 'NVDA', 'TSLA', 'GOOGL', 'BTC-USD', 'CPALL.BK', 'PTT.BK']

# --- 3. ฟังก์ชันหลัก ---
def get_data(symbol, p):
    df = yf.download(symbol, period=p)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- 4. หน้าจอหลัก (Main Dashboard) ---
tab1, tab2, tab3 = st.tabs(["📈 Terminal & AI", "🔍 Market Scanner", "📊 YTD Performance"])

with tab1:
    if ticker:
        data = get_data(ticker, period)
        if not data.empty:
            # คำนวณ RSI & MACD
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            data['RSI'] = 100 - (100 / (1 + (gain / loss)))
            
            # กราฟ Terminal
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI", line=dict(color='purple')), row=2, col=1)
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # AI Forecast Button
            if st.button("🔮 Run 30-Day AI Forecast"):
                df_train = data.reset_index()[['Date', 'Close']].rename(columns={'Date':'ds', 'Close':'y'})
                df_train['ds'] = df_train['ds'].dt.tz_localize(None)
                m = Prophet().fit(df_train)
                future = m.make_future_dataframe(periods=30)
                forecast = m.predict(future)
                st.pyplot(m.plot(forecast))

with tab2:
    if st.button("🚀 Start Market Scan (RSI)"):
        results = []
        for s in watch_list:
            d = yf.download(s, period="1mo", progress=False)
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            # คำนวณ RSI แบบย่อ
            diff = d['Close'].diff()
            r = (diff.where(diff>0,0).rolling(14).mean()) / (-diff.where(diff<0,0).rolling(14).mean())
            last_rsi = 100 - (100 / (1+r.iloc[-1]))
            results.append({"Ticker": s, "Price": d['Close'].iloc[-1], "RSI": last_rsi})
        st.table(pd.DataFrame(results))

with tab3:
    if st.button("📊 Calculate YTD Returns"):
        ytd_data = []
        for s in watch_list:
            df_ytd = yf.download(s, start=f"{datetime.now().year}-01-01", progress=False)
            if isinstance(df_ytd.columns, pd.MultiIndex): df_ytd.columns = df_ytd.columns.get_level_values(0)
            ret = ((df_ytd['Close'].iloc[-1] - df_ytd['Close'].iloc[0]) / df_ytd['Close'].iloc[0]) * 100
            ytd_data.append({"Ticker": s, "YTD Return (%)": round(ret, 2)})
        st.bar_chart(pd.DataFrame(ytd_data).set_index("Ticker"))