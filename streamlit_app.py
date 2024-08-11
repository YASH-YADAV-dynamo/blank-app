import streamlit as st
import time
import requests
import threading
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

# Define your API key
API_KEY = "0UL65I2ILT0GTDAY"

# Function to fetch stock price
def get_stock_price(ticker):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=1min&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Time Series (1min)" not in data:
        raise ValueError(f"Error fetching data for {ticker}: {data.get('Note', 'Unknown error')}")
    
    latest_data = list(data["Time Series (1min)"].values())[0]
    return float(latest_data["4. close"])

# Function to fetch historical stock data for plotting
def get_historical_data(ticker):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Time Series (Daily)" not in data:
        raise ValueError(f"Error fetching historical data for {ticker}: {data.get('Note', 'Unknown error')}")

    df = pd.DataFrame(data["Time Series (Daily)"]).T
    df.index = pd.to_datetime(df.index)
    df = df.loc[start_date:end_date]
    df = df[['4. close']].astype(float)
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'Date', '4. close': 'Close'}, inplace=True)
    return df

# Function to monitor stock prices
def monitor_stocks(tickers, upper_limits, lower_limits, check_interval):
    while True:
        for i, ticker in enumerate(tickers):
            try:
                price = get_stock_price(ticker)
                st.session_state[ticker] = price  # Store price in session state

                if price > upper_limits[i]:
                    st.session_state[f"{ticker}_alert"] = f"Buy Alert: {ticker} has reached {price:.2f}"
                elif price < lower_limits[i]:
                    st.session_state[f"{ticker}_alert"] = f"Sell Alert: {ticker} has dropped to {price:.2f}"
                else:
                    st.session_state[f"{ticker}_alert"] = ""

            except Exception as e:
                st.session_state[f"{ticker}_alert"] = f"Error: {e}"

        time.sleep(check_interval)

# Streamlit UI
st.set_page_config(page_title="Stock Price Alert System", layout="wide")
st.title("Stock Price Alert System")

st.markdown("""
    <style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    .stTitle, .stSubtitle, .stText {
        color: #ffffff;
    }
    .stForm, .stAlert {
        background-color: #2c2c2c;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.5);
        color: #ffffff;
    }
    .stButton {
        margin-top: 10px;
    }
    .stSuccess {
        color: #28a745;
    }
    .stWarning {
        color: #ffc107;
    }
    .stError {
        color: #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)

# Form for user input
with st.form(key='input_form'):
    st.subheader("Configure Alerts")

    tickers_input = st.text_input("Enter stock ticker(s) separated by commas (e.g., MSFT, GOOGL, RELIANCE.BSE)", placeholder="MSFT, GOOGL, RELIANCE.BSE")
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(',') if ticker.strip()]

    if tickers:
        st.write("Set price limits for each ticker:")
        upper_limits = []
        lower_limits = []
        for ticker in tickers:
            col1, col2 = st.columns(2)
            with col1:
                upper = st.number_input(f"Upper limit for {ticker}", min_value=0.0, value=0.0, format="%.2f")
            with col2:
                lower = st.number_input(f"Lower limit for {ticker}", min_value=0.0, value=0.0, format="%.2f")
            upper_limits.append(upper)
            lower_limits.append(lower)

        check_interval = st.number_input("Enter check interval in seconds", min_value=1, value=60)
        submit_button = st.form_submit_button("Start Monitoring")

        if submit_button:
            if not upper_limits or not lower_limits:
                st.error("Please provide valid limits for all tickers.")
            else:
                st.write("Monitoring started...")
                for ticker in tickers:
                    st.session_state[ticker] = None
                    st.session_state[f"{ticker}_alert"] = ""

                # Start the monitoring thread
                threading.Thread(target=monitor_stocks, args=(tickers, upper_limits, lower_limits, check_interval), daemon=True).start()

# Display alerts and chart
if 'input_form' in st.session_state:
    st.subheader("Alerts")
    for ticker in tickers:
        alert_message = st.session_state.get(f"{ticker}_alert", "")
        if alert_message:
            if "Buy Alert" in alert_message:
                st.success(alert_message)
            elif "Sell Alert" in alert_message:
                st.warning(alert_message)
            else:
                st.error(alert_message)

    st.subheader("Stock Price Chart")
    for ticker in tickers:
        try:
            df = get_historical_data(ticker)
            if not df.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], mode='lines+markers', name=ticker))
                fig.update_layout(title=f"{ticker} Stock Price - Last 30 Days",
                                  xaxis_title='Date',
                                  yaxis_title='Price',
                                  template='plotly_dark')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write(f"No data available for {ticker}.")
        except Exception as e:
            st.error(f"Error fetching historical data for {ticker}: {e}")
