from typing import Literal

from py_clob_client.clob_types import  OrderArgs

from helpers.clob_client import create_clob_client
from py_clob_client.clob_types import TradeParams

from py_clob_client.order_builder.constants import BUY
from py_clob_client.order_builder.constants import SELL

import json
import os
import math
import requests
from dotenv import load_dotenv


def create_and_submit_order(token_id: str, side: Literal['BUY'] | Literal['SELL'], price: float, size: int):
    client = create_clob_client()

    # Create and sign a limit order buying 100 YES tokens for 0.0005 each
    order_args = OrderArgs(
        price=price,
        size=size,
        side=side,
        token_id=token_id,
    )
    signed_order = client.create_order(order_args)
    return client.post_order(signed_order)

def limit_order(market: dict, side: str, outcome: str, price: float, size: int):
    if side == 'buy':
        side_literal = BUY
    elif side == 'sell':
        side_literal = SELL
    else:
        print('Invalid side.')
        return
    
    if outcome == 'yes':
        token_id = next((item for item in market['tokens'] if item.get('outcome') == 'Yes'), None)['token_id']
    elif outcome == 'no':
        token_id = next((item for item in market['tokens'] if item.get('outcome') == 'No'), None)['token_id']
    else:
        print('Invalid outcome.')
        return
    market_id = market['condition_id']

    print(f'[ORDER PLACED]\tside={side}, outcome={outcome}, price={price}, size={size}, market_id={market_id}')
    log_message(f'[ORDER PLACED]\tside={side}, outcome={outcome}, price={price}, size={size}, market_id={market_id}')

    # Create and submit the order
    order_response = create_and_submit_order(token_id=token_id, side=side_literal, price=price, size=size)

    # If the order was successfully created, record it to the JSON file
    if order_response.get('success') and 'orderID' in order_response:
        order_id = order_response['orderID']
        record_order_to_file(order_id, market['condition_id'], side, outcome, price, size)
    else:
        print(f"Failed to create order: {order_response.get('errorMsg', 'Unknown error')}")

def conditional_order(market, outcome, current_total_in_band, bands, band_num, midpoint_yes, midpoint_no, available_to_buy, available_yes_to_sell, available_no_to_sell, max_position, owned_outcome, owned_yes):
    if outcome == 'yes':
        buy_price = midpoint_yes - bands[str(band_num)]['avg_margin']
        available_to_sell = available_no_to_sell
        sell_outcome = 'no'
    elif outcome == 'no':
        buy_price = midpoint_no - bands[str(band_num)]['avg_margin']
        available_to_sell = available_yes_to_sell
        sell_outcome = 'yes'
    else:
        return
    
    buy_price = round_up_to_cents(buy_price)
    sell_price = round(1 - buy_price, 2)
    
    size = bands[str(band_num)]['avg_amount'] - current_total_in_band
    if size < 5:
        size = 5
    
    shares_to_buy = size - available_to_sell

    if available_to_sell >= size:
        limit_order(market=market, side='sell', outcome=sell_outcome, price=sell_price, size=size)
        return
    elif size >= 10 and shares_to_buy >= 5 and available_to_sell >= 5 and (shares_to_buy * buy_price) >= 1 and available_to_buy >= (shares_to_buy * buy_price):
        limit_order(market=market, side='buy', outcome=outcome, price=buy_price, size=shares_to_buy)
        limit_order(market=market, side='sell', outcome=sell_outcome, price=sell_price, size=available_to_sell)
        return

    if size * buy_price < 1:
        size = math.ceil(1 / buy_price)
    
    if available_to_buy >= size * buy_price:
        # Stop if we are overbuying one outcome
        if outcome == owned_outcome and (abs(owned_yes) + size) > max_position:
            size = max_position - owned_yes
            if size < 5 or size * buy_price < 1:
                return
        limit_order(market=market, side='buy', outcome=outcome, price=buy_price, size=size)
    else:
        print(f'[ERROR]\tnot enough balance, available_to_buy={available_to_buy}, size*buy_price={size * buy_price}')

def round_down_to_cents(number):
    return math.floor(number * 100) / 100

def round_up_to_cents(number):
    return math.ceil(number * 100) / 100

def get_json(file_path: str):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    return data

def calculate_total_open_buy_value(market_id, file_path='orders.json'):
    """
    Calculate the total value of buy orders (price * size) for a specific market.

    Args:
        market_id (str): The ID of the market to filter orders for.
        file_path (str): The path to the orders.json file.

    Returns:
        float: The total value of buy orders for the given market.
    """
    if not os.path.exists(file_path):
        print("Orders file does not exist.")
        return 0.0

    try:
        with open(file_path, 'r') as file:
            orders = json.load(file)
    except json.JSONDecodeError:
        print("Failed to read orders.json or it is empty.")
        return 0.0

    total_value = 0.0

    for order in orders:
        if order.get('market_id') == market_id and order.get('side') == 'buy':
            price = order.get('price', 0.0)
            size = order.get('size', 0)
            size_matched = order.get('size_matched', 0)
            total_value += price * (size - size_matched)

    return round(total_value, 4)

def calculate_total_open_sell_size(market_id, file_path='orders.json'):
    """
    Calculate the total size for 'yes' and 'no' sell orders for a specific market.

    Args:
        market_id (str): The ID of the market to filter orders for.
        file_path (str): The path to the orders.json file.

    Returns:
        tuple: A tuple containing the total size for 'yes' and 'no' sell orders (yes_sell_total, no_sell_total).
    """
    if not os.path.exists(file_path):
        print("Orders file does not exist.")
        return 0, 0

    try:
        with open(file_path, 'r') as file:
            orders = json.load(file)
    except json.JSONDecodeError:
        print("Failed to read orders.json or it is empty.")
        return 0, 0

    yes_sell_total = 0.0
    no_sell_total = 0.0

    for order in orders:
        if order.get('market_id') == market_id and order.get('side') == 'sell':
            outcome = order.get('outcome')
            size = order.get('size', 0)
            size_matched = order.get('size_matched', 0)

            if outcome == 'yes':
                yes_sell_total += size - size_matched
            elif outcome == 'no':
                no_sell_total += size - size_matched

    return round(yes_sell_total, 4), round(no_sell_total, 4)

def get_orders_in_band(band_num, midpoint_yes, midpoint_no, market_id, file_path='orders.json'):
    """
    Retrieve orders from orders.json that fall within a specific band range for yes and no outcomes.
    """
    rnd_amt = 4

    bands = get_json('bands.json')
    min_margin = bands[str(band_num)]['min_margin']
    max_margin = bands[str(band_num)]['max_margin']

    if not os.path.exists(file_path):
        print("Orders file does not exist.")
        return []

    try:
        with open(file_path, 'r') as file:
            orders = json.load(file)
    except json.JSONDecodeError:
        print("Failed to read orders.json or it is empty.")
        return []

    filtered_orders = []

    for order in orders:
        if order['market_id'] == market_id:
            price = order.get('price')
            outcome = order.get('outcome')

            if outcome == 'yes':
                if round((midpoint_yes - max_margin), rnd_amt) < round(price, rnd_amt) <= round((midpoint_yes - min_margin), rnd_amt) or \
                round((midpoint_yes + min_margin), rnd_amt) <= round(price, rnd_amt) < round((midpoint_yes + max_margin), rnd_amt):
                    filtered_orders.append(order)

            elif outcome == 'no':
                if round((midpoint_no - max_margin), rnd_amt) < round(price, rnd_amt) <= round((midpoint_no - min_margin), rnd_amt) or \
                round((midpoint_no + min_margin), rnd_amt) <= round(price, rnd_amt) < round((midpoint_no + max_margin), rnd_amt):
                    filtered_orders.append(order)

    return filtered_orders

def calculate_totals_in_band(orders_in_band):
    """
    Calculate the total effective amount of 'yes' and 'no' contracts in a band.

    Args:
        orders_in_band (list): A list of order objects from get_orders_in_band().

    Returns:
        tuple: A tuple containing the total 'yes' and 'no' amounts (yes_total, no_total).
    """
    yes_total = 0
    no_total = 0

    for order in orders_in_band:
        size_delta = order.get('size', 0) - order.get('size_matched', 0)
        side = order.get('side')
        outcome = order.get('outcome')

        if side == 'buy' and outcome == 'yes':
            yes_total += size_delta
        elif side == 'buy' and outcome == 'no':
            no_total += size_delta
        elif side == 'sell' and outcome == 'yes':
            no_total += size_delta
        elif side == 'sell' and outcome == 'no':
            yes_total += size_delta

    return yes_total, no_total

def record_order_to_file(order_id: str, market_id: str, side: str, outcome: str, price: float, size: int, file_path: str = 'orders.json'):
    """Record the order ID and size to an external JSON file."""
    order_data = {
        'order_id': order_id,
        'market_id': market_id,
        'side': side,
        'outcome': outcome,
        'price': price,
        'size': size,
        'size_matched': 0
    }

    # Check if the file exists
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Append the new order
    data.append(order_data)

    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def remove_orders_from_file(order_ids, file_path: str = 'orders.json'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Filter out the canceled orders
    data = [order for order in data if order['order_id'] not in order_ids]

    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    log_message(f'[REMOVED]\torder_ids={order_ids}')

def update_position(market_id, side, outcome, size_delta, file_path: str = 'positions.json'):
    positions = {}

    # Check if the positions file exists
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                positions = json.load(file)
            except json.JSONDecodeError:
                positions = {}

    # Ensure the market_id exists in the positions
    if market_id not in positions:
        positions[market_id] = {'yes': 0.0, 'no': 0.0}

    # Update the appropriate position
    if side == 'buy':
        positions[market_id][outcome] += size_delta
    elif side == 'sell':
        positions[market_id][outcome] -= size_delta

    # Write the updated positions back to the file
    with open(file_path, 'w') as file:
        json.dump(positions, file, indent=4)

    print(f'[ORDER FILLED]\tside={side}, outcome={outcome}, filled={size_delta}, market_id={market_id}')
    log_message(f'[ORDER FILLED]\tside={side}, outcome={outcome}, filled={size_delta}, market_id={market_id}')

def get_order_info(order_id):
    client = create_clob_client()

    return client.get_order(order_id=order_id)

def update_order_info(order_id, file_path: str = 'orders.json'):

    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    for record in data:
        if record['order_id'] == order_id:
            old_size_matched = record['size_matched']

            total_size = record['size']
            if old_size_matched == total_size:
                return # Don't fetch order info if it's been fully filled to save time
            
            order = get_order_info(order_id)
            print(f'[UPDATE ORDER]\torder_id={order_id}')

            if order['status'] == 'CANCELED':
                remove_orders_from_file([order['id']])
                return
            
            new_size_matched = float(order.get('size_matched', 0))
            price = float(order.get('price', 0))

            record['size_matched'] = new_size_matched
            record['price'] = price

            # Check for changes in size_matched and update position
            if old_size_matched != new_size_matched:
                size_delta = new_size_matched - old_size_matched
                update_position(record['market_id'], record['side'], record['outcome'], size_delta)

    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def update_all_order_info(market_id, file_path: str = 'orders.json'):
    """Update the size_matched value for all orders in the JSON file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                print("Failed to read orders.json or it is empty.")
                return
    else:
        print("orders.json does not exist.")
        return

    for order in data:
        if order['market_id'] == market_id:
            update_order_info(order['order_id'])

def cancel_orders(order_ids):
    client = create_clob_client()

    resp = client.cancel_orders(order_ids=order_ids)
    successfully_canceled_orders = resp['canceled']

    remove_orders_from_file(order_ids)
    print(f'[CANCELED]\torder_ids={successfully_canceled_orders}')
    log_message(f'[CANCELED]\torder_ids={successfully_canceled_orders}')

def get_order_book(market):
    client = create_clob_client()

    token_id = next((item for item in market['tokens'] if item.get('outcome') == 'Yes'), None)['token_id']
    return client.get_order_book(token_id=token_id)

def get_best_bid_yes(order_book):
    if not order_book.bids:
        return None
    
    best_bid = max(order_book.bids, key=lambda bid: float(bid.price))
    return float(best_bid.price)

def get_best_ask_yes(order_book):
    if not order_book.asks:
        return None
    
    best_ask = min(order_book.asks, key=lambda ask: float(ask.price))
    return float(best_ask.price)

def get_best_bid_no(order_book):
    return round(1 - get_best_ask_yes(order_book), 3)

def get_best_ask_no(order_book):
    return round(1 - get_best_bid_yes(order_book), 3)

def get_spread(order_book):
    best_bid_yes = get_best_bid_yes(order_book)
    best_ask_yes = get_best_ask_yes(order_book)

    if not best_bid_yes or not best_ask_yes:
        return None

    return round(best_ask_yes - best_bid_yes, 3)

def get_midpoint_yes(order_book):
    best_bid_yes = get_best_bid_yes(order_book)
    best_ask_yes = get_best_ask_yes(order_book)

    if not best_bid_yes or not best_ask_yes:
        return None

    return round((best_bid_yes + best_ask_yes) / 2, 4)

def get_midpoint_no(order_book):
    best_bid_no = get_best_bid_no(order_book)
    best_ask_no = get_best_ask_no(order_book)

    if not best_bid_no or not best_ask_no:
        return None

    return round((best_bid_no + best_ask_no) / 2, 4)

def get_account_balance():
    load_dotenv()
    polyscan_api_key = os.getenv('POLYSCAN_API_KEY')
    funder = os.getenv('FUNDER')
    USDC_e = '0x2791bca1f2de4661ed88a30c99a7a9449aa84174'

    url = (
        "https://api.polygonscan.com/api"
        "?module=account"
        "&action=tokenbalance"
        f"&contractaddress={USDC_e}"
        f"&address={funder}"
        "&tag=latest"
        f"&apikey={polyscan_api_key}"
    )


    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "1" and "result" in data:
            return int(data["result"]) / 1000000
        else:
            raise ValueError(f"Error in response: {data.get('message', 'Unknown error')}")
    else:
        response.raise_for_status()

def set_stop(new_stop_value):
    # Define the path to the JSON file
    json_file_path = "control.json"

    try:
        # Open the file and load the JSON data
        with open(json_file_path, "r") as file:
            data = json.load(file)

        # Update the "stop" key with the new value
        data["stop"] = str(new_stop_value).lower()  # Ensure it's a string ("true" or "false")

        # Write the updated JSON data back to the file
        with open(json_file_path, "w") as file:
            json.dump(data, file, indent=4)

    except FileNotFoundError:
        print(f"Error: The file {json_file_path} does not exist.")
    except json.JSONDecodeError:
        print(f"Error: The file {json_file_path} contains invalid JSON.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def log_message(message):
    # Define the path to the log file
    log_file_path = "log.txt"

    try:
        # Open the file in append mode and write the message with a newline
        with open(log_file_path, "a") as file:
            file.write(message + "\n")

    except Exception as e:
        print(f"An unexpected error occurred while logging the message: {e}")
