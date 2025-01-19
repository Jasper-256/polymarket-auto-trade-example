import os
from dotenv import load_dotenv

from helpers.generate_wallet import generate_new_wallet
from helpers.set_allowances import set_allowances
from api_keys.create_api_key import generate_api_keys
from markets.get_markets import get_market
from trades.trade_specific_market import get_account_balance
from trades.trade_specific_market import limit_order
from trades.trade_specific_market import conditional_order
from trades.trade_specific_market import update_order_info
from trades.trade_specific_market import cancel_orders
from trades.trade_specific_market import get_order_book
from trades.trade_specific_market import get_best_bid_yes
from trades.trade_specific_market import get_best_ask_yes
from trades.trade_specific_market import get_best_bid_no
from trades.trade_specific_market import get_best_ask_no
from trades.trade_specific_market import get_spread
from trades.trade_specific_market import get_midpoint_yes
from trades.trade_specific_market import get_midpoint_no
from trades.trade_specific_market import update_all_order_info
from trades.trade_specific_market import remove_orders_from_file
from trades.trade_specific_market import get_json
from trades.trade_specific_market import get_orders_in_band
from trades.trade_specific_market import calculate_totals_in_band
from trades.trade_specific_market import calculate_total_open_buy_value
from trades.trade_specific_market import calculate_total_open_sell_size


load_dotenv()

control = get_json('control.json')
market_to_trade = control['market_to_trade']

def auto_make_market(market_id):
    market = get_market(market_id)

    while True:
        control = get_json('control.json')
        if control['stop'] == 'true':
            return

        # Update everything
        update_all_order_info()
        account_balance = get_account_balance()
        print(f'[ACCT BALANCE]\taccount_balance={account_balance}')
        order_book = get_order_book(market)

        best_bid_yes = get_best_bid_yes(order_book)
        best_ask_yes = get_best_ask_yes(order_book)
        midpoint_yes = get_midpoint_yes(order_book)
        best_bid_no = get_best_bid_no(order_book)
        best_ask_no = get_best_ask_no(order_book)
        midpoint_no = get_midpoint_no(order_book)
        spread = get_spread(order_book)

        orders = get_json('orders.json')
        positions = get_json('positions.json')
        bands = get_json('bands.json')

        if market_id in positions:
            yes_position = positions[market_id]['yes']
            no_position = positions[market_id]['no']
        else:
            yes_position = 0.0
            no_position = 0.0

        open_buy_value = calculate_total_open_buy_value(market_id)
        available_to_buy = round(account_balance - open_buy_value, 6)
        open_sell_size_yes, open_sell_size_no = calculate_total_open_sell_size(market_id)
        available_yes_to_sell = yes_position - open_sell_size_yes
        available_no_to_sell = no_position - open_sell_size_no

        owned_outcome = 'none'
        owned_yes = yes_position - no_position
        owned_outcome_value = 0
        cancelable_tokens = min(yes_position, no_position)
        if owned_yes > 0:
            owned_outcome = 'yes'
            owned_outcome_value = round(owned_yes * best_bid_yes, 6)
        elif owned_yes < 0:
            owned_outcome = 'no'
            owned_outcome_value = round(-owned_yes * best_bid_no, 6)

        print(f'[POSITION]\towned_yes={owned_yes}, owned_outcome_value={owned_outcome_value}, cancelable_tokens={cancelable_tokens}')
        print(f'[OPEN POS]\topen_buy_value={open_buy_value}, open_sell_size_yes={open_sell_size_yes}, open_sell_size_no={open_sell_size_no}')
        print(f'[AVAILABLE]\tavailable_to_buy={available_to_buy}, available_yes_to_sell={available_yes_to_sell}, available_no_to_sell={available_no_to_sell}')
        print(f'[YES PRICES]\tbest_bid_yes={best_bid_yes}, best_ask_yes={best_ask_yes}, midpoint_yes={midpoint_yes}')
        print(f'[NO PRICES]\tbest_bid_no={best_bid_no}, best_ask_no={best_ask_no}, midpoint_no={midpoint_no}, spread={spread}')

        outside_order_ids = []
        for order in orders:
            outside_order_ids.append(order['order_id'])
        
        for band_num in range(bands['num_bands']):
            orders_in_band = get_orders_in_band(band_num, midpoint_yes, midpoint_no)

            for order in orders_in_band:
                outside_order_ids.remove(order['order_id'])

        # Cancel orders outside bands
        if len(outside_order_ids) > 0:
            cancel_orders(outside_order_ids)

        for band_num in range(bands['num_bands']):
            orders_in_band = get_orders_in_band(band_num, midpoint_yes, midpoint_no)
            
            yes_total, no_total = calculate_totals_in_band(orders_in_band)

            if yes_total < bands[str(band_num)]['min_amount']:
                conditional_order(market=market, outcome='yes', current_total_in_band=yes_total, bands=bands, band_num=band_num, midpoint_yes=midpoint_yes, midpoint_no=midpoint_no, available_to_buy=available_to_buy, available_yes_to_sell=available_yes_to_sell, available_no_to_sell=available_no_to_sell)
            if no_total < bands[str(band_num)]['min_amount']:
                conditional_order(market=market, outcome='no', current_total_in_band=no_total, bands=bands, band_num=band_num, midpoint_yes=midpoint_yes, midpoint_no=midpoint_no, available_to_buy=available_to_buy, available_yes_to_sell=available_yes_to_sell, available_no_to_sell=available_no_to_sell)
            
            print(f'[BAND {band_num}]\tyes_total={yes_total}, no_total={no_total}')
        print()

auto_make_market(market_to_trade)

# Find the condition ID for the market you want to trade and retrieve market info from CLOB
# trump_aliens = get_market(trump_aliens_id)
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
# update_all_order_info()

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
