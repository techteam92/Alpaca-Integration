import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import os
import json
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

load_dotenv()  # Loads variables from .env

app = Flask(__name__)
window = 5  # Number of periods for MA

# Access variables
apca_account_Key = os.getenv('APCA_API_KEY_ID')
secret_key = os.getenv('APCA_API_SECRET_KEY')
database_url = os.getenv('paper_url')

# Use them in your app config
app.config['APCA_API_KEY_ID'] = apca_account_Key
app.config['APCA_API_SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = database_url




@app.route('/')
def home():
    return '<h1>Welcome to the Flask Backend!</h1>'

@app.route('/api/submit', methods=['GET'])
def Delta_Volatility(option_type):
    try:
        trades_data = Gather_OptionPrice(option_type)
        if 'bars' not in trades_data or option_type not in trades_data['bars']:
            return jsonify({"error": "No trades data available"}), 404
            
        trades_list = trades_data['bars'][option_type]
        if not trades_list:
            return jsonify({"message": "No trades found for the given option"}), 200
            
        open_array, high_array, close_array, low_array, volumn_array, volumnWeight_array, tradesCount_array = aggregate_trades(trades_list)
        # fibonacci_level(close_array)
        atr_values = calculate_atr(open_array, high_array, close_array, low_array, 14)
        rsi = calculate_rsi(close_array, 14)
        atr_threshold = atr_values.median()
        base_long = (rsi < 30) & (atr_values > atr_threshold)
        base_short = (rsi > 70 ) & (atr_values < atr_threshold)
        Market_Trend, Avoid_trend = confirm_Signal(volumn_array, tradesCount_array, 14)
        # Example: base_long, Market_Trend, and a third boolean Series (e.g., Avoid_trend)
        combined = (base_long | base_short) & Market_Trend

        # Get the timestamps where all are True
        true_times = combined[combined].index
        print(true_times)
        long_signal= base_long & Market_Trend
        short_signal = base_short & Market_Trend
        
        return bool(long_signal.iloc[0]), bool(short_signal.iloc[0]), bool(Avoid_trend.iloc[0])
        
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500



def Gather_OptionPrice(option_type):
    url = f"https://data.alpaca.markets/v1beta1/options/bars?symbols={option_type}&timeframe=1Min&start=2025-01-03T09%3A30%3A00-04%3A00&limit=1000&sort=asc"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": apca_account_Key,
        "APCA-API-SECRET-KEY": secret_key
    }
    response = requests.get(url, headers=headers)
    return response.json()


def aggregate_trades(trades_list):
    df = pd.DataFrame(trades_list)
    if df.empty:
        print("DataFrame is empty")
        return []

    # Parse the time column and set as index
    df['t'] = pd.to_datetime(df['t'])
    df.set_index('t', inplace=True)

    # Extract the close prices as a Series
    close_series = df['c']
    open_series = df['o']
    high_series = df['h']
    low_series = df['l']
    volumn_series = df['v']
    volumn_weight_series = df['vw']
    trades_count = df['n']

    # Remove nan values to get a clean array
    clean_close = [v for v in close_series if v is not None and not np.isnan(v)]
    clean_open = [v for v in open_series if v is not None and not np.isnan(v)]
    clean_high = [v for v in high_series if v is not None and not np.isnan(v)]
    clean_low = [v for v in low_series if v is not None and not np.isnan(v)]
    clean_volumn = [v for v in volumn_series if v is not None and not np.isnan(v)]
    clean_volumn_weight = [v for v in volumn_weight_series if v is not None and not np.isnan(v)]
    clean_trades_count = [v for v in trades_count if v is not None and not np.isnan(v)]

    return clean_open, clean_high, clean_close, clean_low, clean_volumn, clean_volumn_weight, clean_trades_count

def fibonacci_level (price_Data):
    # Convert to numpy array if it's a list
    price_Data = np.array(price_Data)
    # Find indices of local maxima and minima in a moving window (order)
    order = 5  # The number of points on each side to use for comparison   
    # Local maxima (swing highs)
    swing_high_idx = argrelextrema(price_Data, np.greater, order=order)[0]
    # Local minima (swing lows)
    swing_low_idx = argrelextrema(price_Data, np.less, order=order)[0]
    # Get timestamps and values
    swing_highs = price_Data[swing_high_idx]
    swing_lows = price_Data[swing_low_idx]
    print("swing high===>", swing_highs, " swing low===>", swing_lows)

def calculate_atr(open, high, close, low, period):
    open = pd.Series(open)
    high = pd.Series(high)
    close = pd.Series(close)
    low = pd.Series(low)
    # Calculate True Range
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    tr = pd.Series(tr)
    # Calculate ATR
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr

def calculate_rsi(series, period):
    series =pd.Series(series)
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    return rsi

# to filter the fake signal
def confirm_Signal(volume, trades_count, period):
    volume = pd.Series(volume)
    trades_count = pd.Series(trades_count)
    avg_volume = volume.rolling(window =  period).mean()
    avg_count= trades_count.rolling(window = period).mean()
    confirmed_trend = (volume > avg_volume) & (trades_count > avg_count)
    avoid_trading = (volume < avg_volume) & (trades_count < avg_count)
    return confirmed_trend, avoid_trading