from typing import Literal

from py_clob_client.clob_types import  OrderArgs

from helpers.clob_client import create_clob_client

from py_clob_client.order_builder.constants import BUY
from py_clob_client.order_builder.constants import SELL


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
    resp = client.post_order(signed_order)
    print(resp)
    print('Done!')

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

    create_and_submit_order(token_id=token_id, side=side_literal, price=price, size=size)
