from typing import Literal

from py_clob_client.clob_types import  OrderArgs

from helpers.clob_client import create_clob_client
from py_clob_client.clob_types import TradeParams

from py_clob_client.order_builder.constants import BUY
from py_clob_client.order_builder.constants import SELL

import json
import os
import math


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
    
    # Create and submit the order
    order_response = create_and_submit_order(token_id=token_id, side=side_literal, price=price, size=size)

    print(f'[ORDER PLACED]\tside={side}, outcome={outcome}, price={price}, size={size}')

    # If the order was successfully created, record it to the JSON file
    if order_response.get('success') and 'orderID' in order_response:
        order_id = order_response['orderID']
        record_order_to_file(order_id, market['condition_id'], side, outcome, price, size)
    else:
        print(f"Failed to create order: {order_response.get('errorMsg', 'Unknown error')}")

def conditional_order(market, outcome, current_total, bands, band_num, midpoint_yes, midpoint_no):
    if outcome == 'yes':
        price = midpoint_yes - bands[str(band_num)]['avg_margin']
    elif outcome == 'no':
        price = midpoint_no - bands[str(band_num)]['avg_margin']
    else:
        return
    price = round(price, 3)
    
    size = bands[str(band_num)]['avg_amount'] - current_total
    if size < 5:
        size = 5
    if size * price < 1:
        size = math.ceil(1 / price)

    limit_order(market=market, side='buy', outcome=outcome, price=price, size=size)

def get_orders(file_path: str = 'orders.json'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    return data

def get_positions(file_path: str = 'positions.json'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    return data

def get_bands(file_path: str = 'bands.json'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    return data

def get_orders_in_band(band_num, midpoint_yes, midpoint_no, file_path='orders.json'):
    """
    Retrieve orders from orders.json that fall within a specific band range for yes and no outcomes.
    """
    bands = get_bands()
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
        price = order.get('price')
        outcome = order.get('outcome')

        if outcome == 'yes':
            if (midpoint_yes - max_margin) < price <= (midpoint_yes - min_margin) or \
               (midpoint_yes + min_margin) <= price < (midpoint_yes + max_margin):
                filtered_orders.append(order)

        elif outcome == 'no':
            if (midpoint_no - max_margin) < price <= (midpoint_no - min_margin) or \
               (midpoint_no + min_margin) <= price < (midpoint_no + max_margin):
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
        positions[market_id] = {'yes': 0, 'no': 0}

    # Update the appropriate position
    if side == 'buy':
        positions[market_id][outcome] += size_delta
    elif side == 'sell':
        positions[market_id][outcome] -= size_delta

    # Write the updated positions back to the file
    with open(file_path, 'w') as file:
        json.dump(positions, file, indent=4)

    print(f'[ORDER FILLED]\tside={side}, outcome={outcome}, filled={size_delta}')

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
            
            new_size_matched = float(order.get('size_matched', 0))
            price = float(order.get('price', 0))

            record['size_matched'] = new_size_matched
            record['price'] = price

            # Check for changes in size_matched and update position
            if old_size_matched != new_size_matched:
                size_delta = new_size_matched - old_size_matched
                update_position(record['market_id'], record['side'], record['outcome'], size_delta)

    if order['status'] == 'CANCELED':
        remove_orders_from_file([order['id']])
        return

    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

    # print(f"Order updated: {order_id} with size_matched: {order.get('size_matched', 0)}")

def update_all_order_info(file_path: str = 'orders.json'):
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
        update_order_info(order['order_id'], file_path)

def cancel_orders(order_ids):
    client = create_clob_client()

    resp = client.cancel_orders(order_ids=order_ids)
    successfully_canceled_orders = resp['canceled']

    remove_orders_from_file(order_ids)
    print(f'[CANCELED]\torder_ids={successfully_canceled_orders}')

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

    return math.floor(round((best_bid_yes + best_ask_yes) / 2, 4) * 100) / 100

def get_midpoint_no(order_book):
    best_bid_no = get_best_bid_no(order_book)
    best_ask_no = get_best_ask_no(order_book)

    if not best_bid_no or not best_ask_no:
        return None

    return math.floor(round((best_bid_no + best_ask_no) / 2, 4) * 100) / 100
