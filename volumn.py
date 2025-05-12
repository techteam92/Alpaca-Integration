import requests
from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import json
import pandas as pd
import numpy as np


load_dotenv()  # Loads variables from .env

app = Flask(__name__)

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
def Delta_Volatility():
    try:
        option_type = "SPY250506C00571000"
        trades_data = Gather_OptionPrice(option_type)
        
        if not trades_data.get('trades') or option_type not in trades_data['trades']:
            return jsonify({"error": "No trades data available"}), 404
            
        trades_list = trades_data['trades'][option_type]
        
        if not trades_list:
            return jsonify({"message": "No trades found for the given option"}), 200
            
        aggregated_data = aggregate_trades(trades_list)
        # 1. Get all values as a list
        values = list(aggregated_data.values())
        # 2. Remove nan values
        clean_values = [v for v in values if not (v is None or np.isnan(v))]
        # Now clean_values is your array of weighted averages without nans
        print(clean_values)
        return jsonify(aggregated_data)
        
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500



def Gather_OptionPrice(option_type):
    url = f"https://data.alpaca.markets/v1beta1/options/trades?symbols={option_type}&start=2025-01-03T01%3A02%3A03.123456789Z&limit=1000"
    print("url==>", url)
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": apca_account_Key,
        "APCA-API-SECRET-KEY": secret_key
    }
    response = requests.get(url, headers=headers)
    return response.json()

def weighted_average(group):
    total_size = group['s'].sum()
    if total_size > 0:
        return (group['p'] * group['s'] * 100).sum() / total_size
    else:
        return None  # or 0 if you prefer

def aggregate_trades(trades_list):
    df = pd.DataFrame(trades_list)
    if df.empty:
        print("DataFrame is empty")
        return {}
    df['t'] = pd.to_datetime(df['t'])
    df.set_index('t', inplace=True)
    
    # Group by 5-minute intervals and calculate weighted average price per group
    aggregated = df.groupby(pd.Grouper(freq='1Min')).apply(weighted_average)
    aggregated.name = 'weighted_average'  # name the resulting Series
    return aggregated.to_dict()
