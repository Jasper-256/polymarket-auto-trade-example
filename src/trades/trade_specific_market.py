from typing import Literal

from py_clob_client.clob_types import  OrderArgs

from helpers.clob_client import create_clob_client
from py_clob_client.clob_types import TradeParams

from py_clob_client.order_builder.constants import BUY
from py_clob_client.order_builder.constants import SELL

import json
import os


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
    print(order_response)

    # If the order was successfully created, record it to the JSON file
    if order_response.get('success') and 'orderID' in order_response:
        order_id = order_response['orderID']
        record_order_to_file(order_id, market['condition_id'], side, outcome, price, size)
    else:
        print(f"Failed to create order: {order_response.get('errorMsg', 'Unknown error')}")

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

    print(f"Order recorded: {order_data}")

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

    print(f"Canceled orders removed from file: {order_ids}")

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

    print(f"Updated positions for market_id: {market_id}, side: {side}, outcome: {outcome}, size_delta: {size_delta}")

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
            
            new_size_matched = int(order.get('size_matched', 0))
            record['size_matched'] = new_size_matched

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

    print(f"Order updated: {order_id} with size_matched: {order.get('size_matched', 0)}")

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

    remove_orders_from_file(resp['canceled'])

def get_order_book(market):
    client = create_clob_client()

    token_id = next((item for item in market['tokens'] if item.get('outcome') == 'Yes'), None)['token_id']
    return client.get_order_book(token_id=token_id)

def get_best_bid(order_book):
    if not order_book.bids:
        return None
    
    best_bid = max(order_book.bids, key=lambda bid: float(bid.price))
    return float(best_bid.price)

def get_best_ask(order_book):
    if not order_book.asks:
        return None
    
    best_ask = min(order_book.asks, key=lambda ask: float(ask.price))
    return float(best_ask.price)

def get_spread(order_book):
    best_bid = get_best_bid(order_book)
    best_ask = get_best_ask(order_book)

    if not best_bid or not best_ask:
        return None

    return round(best_ask - best_bid, 3)

def get_midpoint(order_book):
    best_bid = get_best_bid(order_book)
    best_ask = get_best_ask(order_book)

    if not best_bid or not best_ask:
        return None

    return round((best_bid + best_ask) / 2, 4)
