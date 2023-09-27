
from pybit.unified_trading import HTTP
import json


api_key = ''
api_secret = ''

with open('auth/auth_info.json') as f:
    auth_info = json.load(f)
    api_key = auth_info['api_key']
    api_secret = auth_info['api_secret']

session = HTTP(
    testnet=False,
    api_key= api_key,
    api_secret= api_secret
)

# print(session.get_option_delivery_price(
#     category="option",
#     symbol="ETH-26DEC22-1400-C",
# ))

result = (session.get_positions(
    category="option"
))


if( result['retMsg'] == 'OK' ):
    result = result['result']['list']


jango_info = {}
symbol_list = []

for item in result:

    symbol_name = item['symbol']
    symbol_list.append( item['symbol'])
    for del_key in ['leverage', 'autoAddMargin', 'liqPrice', 'riskLimitValue', 'trailingStop', 'takeProfit', 'tpslMode', 'riskId', 'adlRankIndicator', 'positionMM', 'positionIdx', 'positionIM', 'bustPrice', 'positionBalance', 'stopLoss', 'tradeMode']:
        del item[del_key]
    jango_info[symbol_name] = item
    

for symbol_name in symbol_list:
    result = (session.get_orderbook(
        category="option",
        symbol= symbol_name,
        limit = 3 
    ))

    if( result['retMsg'] == "SUCCESS"):
        result = result['result']
        jango_info[symbol_name]['b'] = result['b']
        jango_info[symbol_name]['a'] = result['a']


        current_price = 0 
        if( len(result['b']) != 0):
            current_price = float(result['b'][0][0])
        else:
            current_price = 0

        current_size = float(jango_info[symbol_name]['size'])

        original_price = float( jango_info[symbol_name]['avgPrice'] ) 
        fee = - float(  jango_info[symbol_name]['cumRealisedPnl'] )

        jango_info[symbol_name]['profit'] = current_price * current_size  - original_price * current_size  - fee

        print( '{} profit: {} $'.format( symbol_name, round( jango_info[symbol_name]['profit'] , 2) ) )


total_profit = 0

for key, value in jango_info.items():
    total_profit += value['profit']



print( 'total profit {}'.format( total_profit))



# batch order
symbol_name1 = 'ETH-28SEP23-1550-P'
symbol_name2 = 'ETH-28SEP23-1625-C'

result = session.place_batch_order(
    category="option",
    request=[
        {
            "category": "option",
            "symbol": symbol_name1,
            "orderType": "Limit",
            "side": "Sell",
            "qty": "0.1",
            "price": "1.2",
            "orderLinkId": "option-test-001",
            "mmp": False,
            "reduceOnly": True # for option closing side Sell and must reduceOnly true 
        },
        {
            "category": "option",
            "symbol": symbol_name2, 
            "orderType": "Limit",
            "side": "Sell",
            "qty": "0.1",
            "price": "1.0",
            "orderLinkId": "option-test-002",
            "mmp": False,
            "reduceOnly": True # for option closing side Sell and must reduceOnly true 
        }
    ]
)
print( json.dumps(result, indent=2)  )

#  최근  거래  내역 (  내 거래 내역 아님 )
# print(session.get_public_trade_history(
#     category="option",
#     symbol="ETH-22SEP23-1600-P",
# ))
if __name__ == "__main__":
    # get postion
    # get orderbook repeatedly
    # market price, real bid price show differently
    pass