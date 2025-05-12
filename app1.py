from flask import Flask, request, jsonify
from threading import Thread
from dotenv import load_dotenv
import os
import requests
import json
import random
import time
import option

app = Flask(__name__)
# Load environment variables from .env file
load_dotenv()
stoploss = None
ask_type = None
signal_type = None
fixed_url = None
exit_signal = None
qty = 0
# Access environment variables
# APCA_API_KEY_ID = os.getenv('APCA_API_KEY_ID')
# APCA_API_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')
APCA_API_KEY_ID ="PK9SUAB04Z4RBO7779IE"
APCA_API_SECRET_KEY = "8KGiAzsFO0pay1xSLnQehNlmViqoiu0gr3iHru8j"
baseURL = os.getenv('paper_url')
list = []
asset_id = ''
# Route for the home page
@app.route('/')
def home():
    return '<h1>Welcome to the Flask Backend!</h1>'

if __name__ == "__app1__":
    app.run(port=5001)  # This will run the server on port 5001
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
        if content["signaltype"] == 'entry':
            data = {
                "signaltype" : content["signaltype"],
                "side" : content["side"],
                "price" : int(content['price']),
                "symbol" : content["symbol"],
                "update_date" : content["update_date"]
            }
            # print(APCA_API_KEY_ID)
            try:
                if qty == 0:
                    selected_symbol, entry_price, seleted_qty = option_info(content["symbol"],content["update_date"],int(content['price']),content["side"])
                # list.append(data)
                    long_signal, short_signal, avoid_trading = option.Delta_Volatility(selected_symbol)
                    print("long_signal ==>", long_signal, "short_signal==>", short_signal, "avoid_trading==>", avoid_trading)

                    if long_signal ==True or short_signal == True:
                        order_create_response = alpaca_order_create(selected_symbol,entry_price, seleted_qty)
                    else:
                        print("we can't find the correct signal")
                    if not order_create_response:
                        return jsonify({"Error": "Failed in creaing order"})
                    thread = Thread(target=monitor_price, args=(content["symbol"], selected_symbol, seleted_qty, entry_price))
                    thread.daemon = True  # Optional: thread will exit when main program exits
                    thread.start()
                    # print("ending of trading------->", exit_signal)
                    # Immediately send success response
                    return jsonify({"Success": "OK"})
                else:
                    print("There are open positions, so you can't call new position 🤷‍♀️🤷‍♂️")
                    return jsonify({"Error": "There are open positions, so you can't call new position 🤷‍♀️🤷‍♂️"})
            except Exception as e:
                print(f"There are open positions, so you can't call new position 🤷‍♀️🤷‍♂️: {e}")
                return jsonify({"Error": "Someting went wrong"})
        elif content["signaltype"] =='exit':
            try:
                global exit_signal
                if qty != 0:
                    exit_signal = True
                return jsonify({"Exit":"Daily ending"})
            except Exception as e:
                return jsonify({"Error":"Something went wrong in Exit session"})
        else:
            print(f"Invalid signaltype: {content["signaltype"]}")
            return jsonify({"error": "Invalid signaltype"}), 400
    else:
        print(f"Request must be JSON")
        return jsonify({"error": "Request must be JSON"}), 400

            
# Route to Authenticate POST Alpaca
@app.route('/api/alpaca/login', methods=['POST'])
def alpaca_login():
    url = baseURL + "/v2/account"
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
    }

    response = requests.get(url, headers=headers)
def option_info(symbol,update_data, price, side):
    try:
        global signal_type
        if side == "buy":
            signal_type = "call"
            url = f"https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}?feed=indicative&limit=1000&updated_since={update_data}T00%3A00%3A00Z&type={signal_type}&strike_price_lte={price}&root_symbol={symbol}"
        else:
            signal_type = "put"
            url = f"https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}?feed=indicative&limit=1000&updated_since={update_data}T00%3A00%3A00Z&type={signal_type}&strike_price_gte={price}&root_symbol={symbol}"
        global fixed_url
        fixed_url = url
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": APCA_API_KEY_ID,
            "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(response)
        data = response.json()
        ap_values = [
            (symbol, 
            snapshot["latestQuote"]["ap"] if signal_type == "call" else snapshot["latestQuote"]["bp"],
            snapshot["latestQuote"]["as"] if signal_type == "call" else snapshot["latestQuote"]["bs"])  # Extracting quantity
            for symbol, snapshot in data["snapshots"].items()
            if "latestQuote" in snapshot and (
                ("ap" in snapshot["latestQuote"] and signal_type == "call") or 
                ("bp" in snapshot["latestQuote"] and signal_type == "put")
            )
        ]

        # Filter based on the price range
        filtered = [(symbol, price, qty) for symbol, price, qty in ap_values if (signal_type == "call" and 1 < price < 5) or (signal_type == "put" and 1 < price < 5)]
        if filtered:
            selected_symbol, selected_price, selected_qty = random.choice(filtered)
            print(f"Symbol: {selected_symbol}, selected_price: {selected_price}, Quantity: {selected_qty}")
            return selected_symbol, selected_price, selected_qty
        else:
            print("No options found with 1 < price < 10,20")
            filtered = [(symbol, selected_price, qty) for symbol, selected_price, qty in ap_values if (signal_type == "call" and 1 < price < 10) or (signal_type == "put" and 1 < price < 10)]
            if filtered:
                selected_symbol, selected_price, selected_qty = random.choice(filtered)
                print(f"Symbol: {selected_symbol}, Price: {selected_price}, Quantity: {selected_qty}")
                return selected_symbol, selected_price, selected_qty
            else:
                print("No options found with 1 < price < 20,30")
                return None  # Return None if no options are found
    except Exception as e:
        print(f"An error occurred while getting option info: {e}")

    
# @app.route('/api/alpaca/order', methods=['POST'])
def alpaca_order_create(selected_symbol,price, seleted_qty):
    try:
        # url = "https://paper-api.alpaca.markets/v2/orders"
        url = baseURL + "/v2/orders"
        global stoploss
        stoploss = price - 0.5
        global takeprofit1
        takeprofit1 = price + 0.1
        global takeprofit2
        takeprofit2 = price + 0.2
        global takeprofit3
        takeprofit3 = price + 0.3
        global ask_type
        ask_type = "buy"
        global qty
        global exit_signal
        account_data = alpaca_account_balance()
        # if url == "https://paper-api.alpaca.markets/v2/orders":
        #     balance = 100000
        # else:

        account_dict = json.loads(account_data)
        balance = float(account_dict['cash'])  # Convert to float 

        qty = round(balance/(price*100))
        print("qty==>", qty, " balance =" , balance)
        payload = {
            "type": "market",
            "time_in_force": "day",
            "symbol": selected_symbol,
            "qty": qty,
            "side": ask_type,
            # "limit_price": limit,
            "order_class": "simple"
        }
        print(exit_signal)
        print(payload)
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "APCA-API-KEY-ID": APCA_API_KEY_ID,
            "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
        }
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        if response_data['asset_id']:
            asset_id = response_data['asset_id']  # Extracts asset ID
            print("asset id====>", asset_id)      # Prints the ID
            return True
        else:
            print("✨==>", response_data["message"], "🧩 Currently Market is closed, Please wait until Market is opened ⏰")
            return False
            

    except Exception as e:
        print(f"An error occured while creating the Order :{e}")
        return False
# @app.route('/api/alpaca/position/close', methods=['GET'])

def monitor_price(symbol, option_symbol, quantity, entry_price):
    trail_price = entry_price
    last_stock_price = None
    global qty
    # qty = quantity
    position_division1 = round(quantity * 0.25)
    position_division2 = round(quantity * 0.25)
    position_division3 = quantity - position_division1 - position_division2
    current_quantity = quantity
    while True:
        try:
            current_stock_price = get_stock_price(symbol)
            # Check if the stock price has changed
            if current_stock_price != last_stock_price:
                last_stock_price = current_stock_price
                option_price = get_option_price(symbol, option_symbol)
                global stoploss
                global takeprofit1
                global exit_signal

                # print(f"🤔  Entry_price: {entry_price} for option Price: {option_price}", "stoploss", stoploss,"takeprofit1", takeprofit1,"takeprofit2", takeprofit2,"takeprofit3", takeprofit3, " ask_type", signal_type , "Entry Stock price:", last_stock_price)
                print(f"🤔  Entry_price: {entry_price} for option Price: {option_price}", "stoploss", stoploss,"takeprofit", takeprofit1," ask_type", signal_type , "Entry Stock price:", last_stock_price)
                # if option_price > trail_price + 0.1:
                #     print("💪Stop loss is updated!💪")
                #     stoploss = option_price - 0.1
                #     trail_price = option_price
                # Check stop loss condition
                if exit_signal:
                    print("😲Stop loss triggered. Closing all positions.😢")
                    # alpaca_order_create(content["side"],selected_symbol,selected_ap, seleted_qty)
                    opposite_side = "sell" if ask_type =="buy" else "buy"
                    print(f"current quantity: {qty}")
                    alpaca_position_closeAll(option_symbol,qty,opposite_side)
                    print("alpaca position closeAll for stoploss completed")
                    exit_signal = False
                    qty = 0
                    break
                # if (takeprofit1 is not None and option_price > takeprofit1):
                #     print("😇takeprofit triggered. Closing all positions.🤗")
                #     # opposite_side = "sell" if ask_type =="buy" else "buy"
                #     # print(f"position devision1: {position_division1}, current quantity: {current_quantity}")
                #     # alpaca_position_closeAll(option_symbol,position_division1,opposite_side)
                #     takeprofit1 = option_price + 0.1
                #     stoploss = option_price - 0.2
                #     # print("alpaca position closeAll for takeprofit1 completed")
                #     print("💪Stop loss is updated!💪")
                    # qty = quantity * 0.75
                    # current_quantity = current_quantity - position_division1
                    # stoploss = entry_price
                # if (takeprofit2 is not None and option_price > takeprofit2) and qty == quantity * 0.75:
                #     print("😇takeprofit2 triggered. Closing all positions.🤗")
                #     opposite_side = "sell" if ask_type =="buy" else "buy"
                #     print(f"position devision2: {position_division2}, current quantity: {current_quantity}")
                #     alpaca_position_closeAll(option_symbol,position_division2,opposite_side)
                #     print("alpaca position closeAll for takeprofit2 completed")
                #     print("💪Stop loss is updated!💪")
                #     stoploss = takeprofit1
                #     current_quantity = current_quantity - position_division2
                #     qty = quantity * 0.5
                # if (takeprofit3 is not None and option_price > takeprofit3) and qty == quantity*0.5:
                #     print("😇takeprofit3 triggered. Closing all positions.🤗")
                #     opposite_side = "sell" if ask_type =="buy" else "buy"
                #     print(f"position devision3: {position_division3}, current quantity: {current_quantity}")
                #     # alpaca_position_closeAll(option_symbol,position_division3,opposite_side)
                #     takeprofit3 = option_price + 0.1
                #     stoploss = option_price - 0.1
                #     print("alpaca position closeAll for takeprofit3 completed")
                #     qty = 0
                #     break
                else:
                    continue
        
        except Exception as e:
            print(f"An error occurred: {e}")

        # Sleep for a specified interval before checking again
        time.sleep(60)  # Check every minute

def get_stock_price(symbol):
    try:
        # Replace with your actual API call to get the stock price
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest"
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": APCA_API_KEY_ID,
            "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
        }

        response = requests.get(url, headers=headers)
            # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            return data['quote']['ap']  # Accessing the ask price from the quote
        else:
            print(f"Error fetching data: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred while get stock price: {e}")


# update the latest price confluently
def get_option_price(symbol, option_symbol):
    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": APCA_API_KEY_ID,
        "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
    }
    
    # url = f"https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}?feed=indicative&type={signal_type}&root_symbol={symbol}"
    url = fixed_url
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an error for bad responses (4xx or 5xx)
        
        # Parse the JSON response
        data = response.json()
        
        # Check if 'snapshots' and the specific option_symbol exist in the response
        if 'snapshots' in data and option_symbol in data['snapshots']:
            latest_quote = data['snapshots'][option_symbol].get('latestQuote')
            if latest_quote:
                ask_price = latest_quote.get('ap') if ask_type =="call" else latest_quote.get('bp')
                if ask_price is not None:
                    print(f"current option Price 🌟: {ask_price}")
                    return ask_price
                else:
                    print(f"Ask price not found for {option_symbol}.")
            else:
                print(f"No latest quote found for {option_symbol}.")
        else:
            print(f"Option symbol {option_symbol} not found in the response.")
        
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching option price: {e}")
    except ValueError as e:
        print(f"Error parsing JSON response: {e}")
    
    return None  # Return None if the price could not be retrieved


def alpaca_position_closeAll(option_symbol, quantity,side):
    try:
        # url = "https://paper-api.alpaca.markets/v2/orders"
        url = baseURL+"/v2/orders"
        payload = {
            "type": "market",
            "time_in_force": "day",
            "symbol": option_symbol,
            "qty": quantity,
            "side": side
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "APCA-API-KEY-ID": APCA_API_KEY_ID,
            "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
        }

        response = requests.post(url, json=payload, headers=headers)
        print(response.text)
    except Exception as e:
        print(f"An error occured while closing all the positions: {e}")

        
def alpaca_position_close(assetid, qty):
    try:
        # url = f"https://paper-api.alpaca.markets/v2/positions/{assetid}"
        url = baseURL+f"/v2/positions/{assetid}"

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
        # print(response_data)
    except Exception as e:
        print(f"An error occured while running alpaca position close function")
if __name__ == '__main__':
    app.run(debug=True)

def alpaca_account_balance():
    try:
        # url = "https://paper-api.alpaca.markets/v2/account"
        url = baseURL+"/v2/account"
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": APCA_API_KEY_ID,
            "APCA-API-SECRET-KEY": APCA_API_SECRET_KEY
        }
        response = requests.get(url, headers=headers)
        data = response.text
        return data
    except Exception as e:
        print(f"An error occured while getting account balance :{e}")
        return 1000