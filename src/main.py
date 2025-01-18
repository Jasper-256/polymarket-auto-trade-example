import os
from dotenv import load_dotenv

from helpers.generate_wallet import generate_new_wallet
from helpers.set_allowances import set_allowances
from api_keys.create_api_key import generate_api_keys
from markets.get_markets import get_market
from trades.trade_specific_market import limit_order
from trades.trade_specific_market import update_order_info
from trades.trade_specific_market import cancel_orders
from trades.trade_specific_market import get_order_book
from trades.trade_specific_market import get_best_bid
from trades.trade_specific_market import get_best_ask
from trades.trade_specific_market import get_spread
from trades.trade_specific_market import get_midpoint
from trades.trade_specific_market import update_all_order_info
from trades.trade_specific_market import remove_orders_from_file



load_dotenv()

def auto_make_market(market):
    open_order_ids = []
    order_book = get_order_book(market)

    while True:
        # Update order book
        order_book = get_order_book(market)

        # Get current position
        print("Cycle")

# Find the condition ID for the market you want to trade and retrieve market info from CLOB
trump_aliens = get_market('0xbb96f092cb5d54138c6af2ae824bb276c3e20969fb2acfced30ac7f88f60862e')
# print(trump_aliens)

# Get information about the order book
# order_book = get_order_book(trump_aliens)

# Fill order data and choose the side you want to buy
# limit_order(market=trump_aliens, side='buy', outcome='yes', price=0.002, size=91)
# limit_order(market=trump_aliens, side='buy', outcome='no', price=0.002, size=101)

# limit_order(market=trump_aliens, side='sell', outcome='yes', price=0.991, size=5)

# limit_order(market=trump_aliens, side='buy', outcome='no', price=0.939, size=2)

# Get existing order details
# update_order_info('0x1a28362aa37250725b400fabb0d0bd9ee9e3550a6d610a807a78ec4a1ddec50a')

# Update all orders in the json
update_all_order_info()

# Cancel an order
# cancel_orders(['0xa717f659b055c8d520e593c4b85078e7bff8c7747288b8b859cb6b3268ab7504'])

# remove_orders_from_file(['0x77c49c0adfa6347c94df1c14697e358de8b39c94a0c2ce3d8ab0be90baf9471b'])

# best_bid = get_best_bid(order_book)
# print('Best Bid:', best_bid)

# best_ask = get_best_ask(order_book)
# print('Best Ask:', best_ask)

# spread = get_spread(order_book)
# print('Spread:', spread)

# midpoint = get_midpoint(order_book)
# print('Midpoint:', midpoint)

# auto_make_market(trump_aliens)
