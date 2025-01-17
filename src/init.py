import os
from dotenv import load_dotenv

from helpers.generate_wallet import generate_new_wallet
from helpers.set_allowances import set_allowances
from api_keys.create_api_key import generate_api_keys
from markets.get_markets import get_market
from trades.trade_specific_market import create_and_submit_order


load_dotenv()

# # Step 1: Generate a new wallet and save the PBK with PK to .env
# if os.getenv('PK') is None:
#     generate_new_wallet()

# Step 1: Fill out the .env

# Step 2: Send some MATIC to the generated wallet to update allowances (don't do this more than once, it wastes MATIC)
set_allowances()

# Step 3: Generate API credentials so that we can communicate with Polymarket
generate_api_keys()
