from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import json
app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()

# Access environment variables
APCA_API_KEY_ID = os.getenv('APCA_API_KEY_ID')
APCA_API_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')
list = []
asset_id = ''
# Route for the home page
@app.route('/')
def home():
    return '<h1>Welcome to the Flask Backend!</h1>'

# Route to return JSON data
@app.route('/api/data', methods=['GET'])
def get_data():
    data = {
        "message": "Hello, this is your data!",
        "status": "success"
    }
    return jsonify(data)

# Route to handle POST requests
@app.route('/api/submit', methods=['POST'])
def submit_data():
    if request.is_json:
        content = request.get_json()
        if content["signaltype"] == 'entry' :
            data = {
                "signaltype" : content["signaltype"],
                "side" : content["side"],
                "sl" : float(content["sl"]),
                "qty" : float(content['qty']),
                "symbol" : content["symbol"]
            }
            print(data)
            list.append(data)
            print(list)
            alpaca_order_create(content["side"],content["symbol"],float(content["sl"]),float(content['qty']))
            return jsonify({"Success": "OK"})
            
        elif content["signaltype"] == 'takeprofit1' or content["signaltype"] == 'takeprofit2':
            data = {
                "signaltype" : content["signaltype"],
                'position_size' : float(content["position_size"])
            }
            print(data)
            list.append(data)
            print(list)
            alpaca_position_close(asset_id, float(content["position_size"]))
            return jsonify({"Success": "OK"})
        elif content["signaltype"] == 'exit' or content["signaltype"] == 'takeprofit3':
            data = {
                "signaltype" : content["signaltype"]
            }
            print(data)
            list.append(data)
            print(list)
            alpaca_position_closeAll()
            return jsonify({"Success": "OK"})
        else :
            return jsonify({"Failed": "Bad Requests"}), 400
        
    else:
        return jsonify({"error": "Request must be JSON"}), 400
    
# Route to Authenticate POST Alpaca
@app.route('/api/alpaca/login', methods=['POST'])
def alpaca_login():
    url = "https://paper-api.alpaca.markets/v2/account"

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
    }

    response = requests.get(url, headers=headers)

    print(response.text)
    
# @app.route('/api/alpaca/order', methods=['POST'])
def alpaca_order_create(side,symbol,stop_loss,qty):
    url = "https://paper-api.alpaca.markets/v2/orders"

    payload = {
        "type": "market",
        "time_in_force": "day",
        "stop_loss": { "stop_price": str(stop_loss) },
        "symbol": symbol,
        "qty": str(qty),
        "side": side
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "APCA-API-KEY-ID": APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
    }

    response = requests.post(url, json=payload, headers=headers)
    response_data = response.json()
    asset_id = response_data['asset_id']
    print(response_data)
    print(asset_id)

# @app.route('/api/alpaca/position/close', methods=['GET'])
def alpaca_position_closeAll():

    url = "https://paper-api.alpaca.markets/v2/positions?cancel_orders=true"

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
    }

    response = requests.delete(url, headers=headers)

    response_data = response.json()
    print(response_data)

def alpaca_position_close(assetid, qty):

    url = f"https://paper-api.alpaca.markets/v2/positions/{assetid}"
    params = {
        "qty": qty
    }
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
    }

    response = requests.get(url, headers=headers, params=params)
    response_data = response.json()
    print(response_data)

if __name__ == '__main__':
    app.run(debug=True)