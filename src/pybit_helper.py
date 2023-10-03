
from pybit.unified_trading import HTTP
import json,datetime, time, logging, datetime

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

log = logging.getLogger(__name__)
file_log = logging.getLogger(__name__ + '_file')

jango_info  = {}

def get_positions(category :str, symbol :str ):
    result = (session.get_positions(
        category= category,
        symbol = symbol
    ))


    if( result['retMsg'] == 'OK' ):
        result = result['result']['list']

    symbol_list = []

    for item in result:

        symbol_name = item['symbol']
        symbol_list.append( item['symbol'])
        for del_key in ['leverage', 'autoAddMargin', 'liqPrice', 'riskLimitValue', 'trailingStop', 
                        'takeProfit', 'tpslMode', 'riskId', 'adlRankIndicator', 'positionMM', 'positionIdx', 
                        'positionIM', 'bustPrice', 'positionBalance', 'stopLoss', 'tradeMode',
                        'createdTime', 'updatedTime', 'seq']:
            del item[del_key]
        jango_info[symbol_name] = item
    


def get_orderbook(category : str):
    target_symbol_name_list = []
    for symbol_name in jango_info:
        target_symbol_name_list.append(symbol_name)

    for symbol_name in target_symbol_name_list:
        result = (session.get_orderbook(
            category = category,
            symbol= symbol_name,
            limit = 5 
        ))

        if( result['retMsg'] == "SUCCESS", result['retMsg'] == 'OK'):
            result = result['result']
            # no longer contract avaliable 
            if( 'b' not in result  ):
                del jango_info[symbol_name]
            # elif( len(result['b']) ==  0):
            # # warinig 'b' is not showing short time
            #     del jango_info[symbol_name]
            else:
                jango_info[symbol_name]['b'] = result['b']
                jango_info[symbol_name]['a'] = result['a']
                bid_list = result['b']

                current_price = 0 
                current_size = float(jango_info[symbol_name]['size'])
                # check size and bid_list amount             
                bid_total_amount = 0
                current_price = 0
                for item in bid_list:
                    bid_total_amount += float(item[1])

                    if( current_size < bid_total_amount ):
                        current_price = float(item[0])
                        break

                original_price = float( jango_info[symbol_name]['avgPrice'] ) 
                fee = - float(  jango_info[symbol_name]['cumRealisedPnl'] )

                # fee * 2 when buy and sell
                jango_info[symbol_name]['profit'] = round( current_price * current_size  - original_price * current_size  - (fee * 2), 2)
                jango_info[symbol_name]['pnl value'] = round( original_price * current_size  + (fee * 2), 2)

                # print( '{} profit: {} $'.format( symbol_name, round( jango_info[symbol_name]['profit'] , 2) ) )


def get_candle(category :str, symbol : str, interval : str):
    result = (
        session.get_kline(
            category= category,
            symbol= symbol,
            interval= interval, 
            limit = 150,
        ))
    if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
        candle_list = result['result']['list']
        for item in candle_list:
            time_stamp  = int( int(item[0]) / 1000)
            candle_time = datetime.datetime.fromtimestamp(time_stamp).strftime("%y-%m-%d %H:%M:%S")
            open_price = float( item[1] )
            amount = float( item[5])
            print( candle_time )



def calculate_option_strangle_pair_profit():
    total_profit = {}

    for key, value in jango_info.items():
        symbol_pair_name = key.split('-')[1]
        if( symbol_pair_name not in total_profit ):
            total_profit[symbol_pair_name] = {} 
            total_profit[symbol_pair_name]['profit'] = 0
            total_profit[symbol_pair_name]['pnl value'] = 0


        total_profit[symbol_pair_name]['profit'] += round( value['profit'], 2)
        total_profit[symbol_pair_name]['pnl value'] += round( value['pnl value'], 2)

    for key, value in total_profit.items():
        info = '{}, profit: {:>20},  pnl: {:<30}'.format(key, value['profit'], value['pnl value']) 
        log.info(info)
        if( value['profit'] > value['pnl value'] * 0.2 ):
        # if( True ):
            for symbol_name in jango_info:
                if( key in symbol_name):
                    file_log.warning( '{}'.format( jango_info[symbol_name] ) )

            file_log.warning( info )
            make_place_order( key )

def calculate_linear_profit():

    for key, value in jango_info.items():
        info = '{}, profit: {:>20},  pnl: {:<30}'.format(key, value['profit'], value['pnl value']) 
        log.info(info)
        # if( value['profit'] > value['pnl value'] * 0.2 ):
        # # if( True ):
        #     for symbol_name in jango_info:
        #         if( key in symbol_name):
        #             file_log.warning( '{}'.format( jango_info[symbol_name] ) )

        #     file_log.warning( info )
        #     make_place_order( key )


def make_place_order(symbol_pair_name):
    target_symbol_list = [] 

    for key, value in jango_info.items():

        if( symbol_pair_name in key ):
            target_symbol_list.append(value)

    requests = []

    for item in target_symbol_list:
        request = {}

        if( len(item['b']) != 0):
            request['category'] = 'option', 
            request['symbol'] = item['symbol']
            request['orderType'] = 'Limit'
            request['side'] = 'Sell'
            request['qty'] = item['size']
            request['price'] = item['b'][-1][0]
            request['orderLinkId'] =  "{}-{}".format( item['symbol'], datetime.datetime.now().strftime("%H:%M:%S") ), # should be unique string 
            request['mmp'] = False,
            request['reduceOnly'] = True # for option closing side Sell and must reduceOnly true 
            requests.append( request )

    result = session.place_batch_order(
        category = "option",
        request = requests
    )

    if( result['retMsg'] == 'OK' ):
        result = result['result']['list']

        file_log.warning( json.dumps( result, indent=2 ))
        print( json.dumps(result, indent=2)  )

        for item in result:
            del jango_info[item['symbol']]


#  최근  거래  내역 ( 내 거래 내역 아님 )
# print(session.get_public_trade_history(
#     category="option",
#     symbol="ETH-22SEP23-1600-P",
# ))
if __name__ == "__main__":
    # get postion
    handler = logging.StreamHandler()
    file_handler = logging.FileHandler('warning.log')
    log.setLevel(logging.INFO)
    file_log.setLevel(logging.WARNING)

    handler.setFormatter(logging.Formatter( '%(asctime)s [%(levelname)s] %(message)s' ) )
    file_handler.setFormatter(logging.Formatter( '%(asctime)s %(message)s - %(lineno)d' ) )
    log.addHandler( handler ) 
    file_log.addHandler( file_handler )

    count = 0
    while True:
        try:
            if( count % 20 == 0 ):
                get_positions(category="linear", symbol = "XRPUSDT")
            get_orderbook(category="linear")
            calculate_linear_profit()

            get_candle(category="linear", symbol = "XRPUSDT", interval="D")

            time.sleep(0.1)
            count = count + 1
        except Exception as e:
            print("except {}".format( e ))
            time.sleep(10)



    pass