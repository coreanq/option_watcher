
from pybit.unified_trading import HTTP
import json


api_key = ''
api_secret = ''

with open('auth/auth_info.json') as f:
    auth_info = json.load(f)
    api_key = auth_info['api_key']
    api_secret = auth_info['api_secret']

session = HTTP(
    testnet=True,
    api_key= api_key,
    api_secret= api_secret
)

print(session.get_option_delivery_price(
    category="option",
    symbol="ETH-26DEC22-1400-C",
))

print(session.get_positions(
    category="option"
    # symbol="BTCUSD",
))

if __name__ == "__main__":
    pass