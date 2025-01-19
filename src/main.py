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
from trades.trade_specific_market import set_stop


load_dotenv()

def auto_make_markets(market_ids):
    print(f'[START]\tmarkets_to_trade={market_ids}\n')
    markets = []
    for i in range(len(market_ids)):
        markets.append(get_market(market_ids[i]))

    while True:
        for i in range(len(market_ids)):
            control = get_json('control.json')
            if control['stop'] == 'true':
                set_stop(False)
                return
            
            market_id = market_ids[i]
            market = markets[i]
            print(f'[MARKET {i}]\tmarket_id={market_id}')

            # Update everything
            update_all_order_info(market_id)
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
                if order['market_id'] == market_id:
                    outside_order_ids.append(order['order_id'])
            
            for band_num in range(bands['num_bands']):
                orders_in_band = get_orders_in_band(band_num, midpoint_yes, midpoint_no, market_id)

                for order in orders_in_band:
                    outside_order_ids.remove(order['order_id'])

            # Cancel orders outside bands
            if len(outside_order_ids) > 0:
                cancel_orders(outside_order_ids)

            for band_num in range(bands['num_bands']):
                orders_in_band = get_orders_in_band(band_num, midpoint_yes, midpoint_no, market_id)
                yes_total, no_total = calculate_totals_in_band(orders_in_band)

                if yes_total < bands[str(band_num)]['min_amount']:
                    open_buy_value = calculate_total_open_buy_value(market_id)
                    available_to_buy = round(account_balance - open_buy_value, 6)
                    yes_total, no_total = calculate_totals_in_band(orders_in_band)
                    open_sell_size_yes, open_sell_size_no = calculate_total_open_sell_size(market_id)
                    available_yes_to_sell = yes_position - open_sell_size_yes
                    available_no_to_sell = no_position - open_sell_size_no

                    conditional_order(market=market, outcome='yes', current_total_in_band=yes_total, bands=bands, band_num=band_num, midpoint_yes=midpoint_yes, midpoint_no=midpoint_no, available_to_buy=available_to_buy, available_yes_to_sell=available_yes_to_sell, available_no_to_sell=available_no_to_sell)

                if no_total < bands[str(band_num)]['min_amount']:
                    open_buy_value = calculate_total_open_buy_value(market_id)
                    available_to_buy = round(account_balance - open_buy_value, 6)
                    yes_total, no_total = calculate_totals_in_band(orders_in_band)
                    open_sell_size_yes, open_sell_size_no = calculate_total_open_sell_size(market_id)
                    available_yes_to_sell = yes_position - open_sell_size_yes
                    available_no_to_sell = no_position - open_sell_size_no

                    conditional_order(market=market, outcome='no', current_total_in_band=no_total, bands=bands, band_num=band_num, midpoint_yes=midpoint_yes, midpoint_no=midpoint_no, available_to_buy=available_to_buy, available_yes_to_sell=available_yes_to_sell, available_no_to_sell=available_no_to_sell)
                
                print(f'[BAND {band_num}]\tyes_total={yes_total}, no_total={no_total}')
            print()

control = get_json('control.json')
markets_to_trade = control['markets_to_trade']
auto_make_markets(markets_to_trade)
