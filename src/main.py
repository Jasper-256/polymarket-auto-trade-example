import os
from dotenv import load_dotenv

from helpers.generate_wallet import generate_new_wallet
from helpers.set_allowances import set_allowances
from api_keys.create_api_key import generate_api_keys
from markets.get_markets import get_market
from trades.trade_specific_market import limit_order


load_dotenv()

# Find the condition ID for the market you want to trade and retrieve market info from CLOB
trump_aliens = get_market('0xbb96f092cb5d54138c6af2ae824bb276c3e20969fb2acfced30ac7f88f60862e')

# Fill order data and choose the side you want to buy
# limit_order(market=trump_aliens, side='buy', outcome='yes', price=0.002, size=91)
# limit_order(market=trump_aliens, side='buy', outcome='no', price=0.002, size=101)
