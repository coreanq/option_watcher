
from PyKakao import Message
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl, socketserver

from pybit.unified_trading import HTTP
import json,datetime, time, logging, datetime, numpy

api_key = ''
api_secret = ''
kakao_rest_api_key = ''
kakao_redirect_url = ''

with open('auth/auth_info.json') as f:
    auth_info = json.load(f)
    api_key = auth_info['api_key']
    api_secret = auth_info['api_secret']
    kakao_rest_api_key = auth_info.get('kakao_rest_api_key', '')

# 메시지 API 인스턴스 생성
MSG = Message(service_key = kakao_rest_api_key )

session = HTTP(
    testnet=False,
    api_key= api_key,
    api_secret= api_secret
)

log = logging.getLogger(__name__)
file_log = logging.getLogger(__name__ + '_file')

jango_info  = {}
order_book_info = {}
candle_info = {}

event_occur_date_time  = None

server_port_number = 5678

def get_positions(category :str, symbol :str):
    result = (session.get_positions(
        category= category,
        symbol = symbol
    ))


    if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
        result = result['result']['list']

    symbol_list = []

    # 잔고가 복수일수 있음 
    for item in result:
        symbol_name = item['symbol']

        for del_key in ['leverage', 'autoAddMargin', 'liqPrice', 'riskLimitValue', 'trailingStop', 
                        'takeProfit', 'tpslMode', 'riskId', 'adlRankIndicator', 'positionMM', 'positionIdx', 
                        'positionIM', 'bustPrice', 'positionBalance', 'stopLoss', 'tradeMode',
                        'createdTime', 'updatedTime', 'seq']:
            del item[del_key]
        if( item['size'] == '0' and symbol_name in jango_info):
            del jango_info[symbol_name] 
        else:
            jango_info[symbol_name] = item
    


def get_orderbook(category : str, symbol_name: str):
    result = (session.get_orderbook(
        category = category,
        symbol= symbol_name,
        limit = 5 
    ))

    if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
        result = result['result']
        # no longer contract avaliable 
        if( 'b' not in result  ):
            pass
        else:
            if( symbol_name not in order_book_info):
                order_book_info[symbol_name] = {}
            order_book_info[symbol_name]['b'] = result['b']
            order_book_info[symbol_name]['a'] = result['a']
            # bid_list = result['b']

            # current_price = 0 
            # current_size = float(jango_info[symbol_name]['size'])
            # # check size and bid_list amount             
            # bid_total_amount = 0
            # current_price = 0
            # for item in bid_list:
            #     bid_total_amount += float(item[1])

            #     if( current_size < bid_total_amount ):
            #         current_price = float(item[0])
            #         break

            # original_price = float( order_book_info[symbol_name]['avgPrice'] ) 
            # fee = - float(  order_book_info[symbol_name]['cumRealisedPnl'] )

            # fee * 2 when buy and sell
            # order_book_info[symbol_name]['profit'] = round( current_price * current_size  - original_price * current_size  - (fee * 2), 2)
            # order_book_info[symbol_name]['pnl value'] = round( original_price * current_size  + (fee * 2), 2)

            # print( '{} profit: {} $'.format( symbol_name, round( order_book_info[symbol_name]['profit'] , 2) ) )



def caculate_bollinger(symbol_name : str):
    last_price = close_price_list[-1]
    last_std_upper_value = candle_info[symbol_name]['bol 20, 2 upper'][-1]
    last_std_lower_value = candle_info[symbol_name]['bol 20, 2 lower'][-1]

    close_price_list = [ n[1] for n in jango_info[symbol_name]['candle']  ]
    close_price_list = close_price_list[::-1]

    jango_info[symbol_name]['mean20']  = []
    jango_info[symbol_name]['bol 20, 2 upper']  = []
    jango_info[symbol_name]['bol 20, 2 lower']  = []
    jango_info[symbol_name]['mean5']  = []
    # 20 avr
    for index, item in enumerate( close_price_list  ):

        mean_target = 20 

        if( index >= mean_target ):
            mean_target_list =  close_price_list[index - mean_target: index ]

            mean_value = numpy.mean( mean_target_list ) 
            std_value = numpy.std( mean_target_list ) * 2

            jango_info[symbol_name]['mean{}'.format( mean_target )].append( round( mean_value , 3 ) )
            jango_info[symbol_name]['bol 20, 2 upper'].append( round( mean_value + std_value , 3 ) )
            jango_info[symbol_name]['bol 20, 2 lower'].append( round( mean_value  - std_value , 3 ) )
        else:
            jango_info[symbol_name]['mean{}'.format( mean_target )].append(None)
            jango_info[symbol_name]['bol 20, 2 upper'].append(None)
            jango_info[symbol_name]['bol 20, 2 lower'].append(None)

        mean_target = 5

        if( index >= mean_target ):
            mean_target_list =  close_price_list[index - mean_target: index ]
            mean_value = numpy.mean( mean_target_list ) 
            jango_info[symbol_name]['mean{}'.format( mean_target )].append( round( mean_value, 3 ) )
        else:
            jango_info[symbol_name]['mean{}'.format( mean_target )].append( None )
        
    last_price = close_price_list[-1]
    last_std_upper_value = jango_info[symbol_name]['bol 20, 2 upper'][-1]
    last_std_lower_value = jango_info[symbol_name]['bol 20, 2 lower'][-1]

    current_time = datetime.datetime.now()
    diff_time = datetime.timedelta(hours=1)

    global event_occur_date_time

    if( last_price > last_std_upper_value ):
        text = "ETHUSDT 볼린저 밴드 상단 돌파"
        button_title = "바로 확인"

        if( event_occur_date_time == None ):
            MSG.send_text(text=text, link={}, button_title=button_title)
            event_occur_date_time = datetime.datetime.now()

        elif( event_occur_date_time + diff_time < current_time ):
            MSG.send_text(text=text, link={}, button_title=button_title)
            event_occur_date_time = datetime.datetime.now()

        print( 'bol upper cross')

    elif( last_price < last_std_lower_value ):
        text = "ETHUSDT 볼린저 밴드 하단 돌파"
        button_title = "바로 확인"

        if( event_occur_date_time == None ):
            MSG.send_text(text=text, link={}, button_title=button_title)
            event_occur_date_time = datetime.datetime.now()

        elif( event_occur_date_time + diff_time < current_time ):
            MSG.send_text(text=text, link={}, button_title=button_title)
            event_occur_date_time = datetime.datetime.now()

        print( 'bol lower cross')

        pass


# 20봉/ 5봉 평균 추가 
def get_candle(category :str, symbol_name : str, interval : str):
    result = (
        session.get_kline(
            category= category,
            symbol= symbol_name,
            interval= interval, 
            limit = 70,
        ))
    if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
        candle_list = result['result']['list']

        if( symbol_name not in candle_info ):
            candle_info[symbol_name] = {}

        candle_info[symbol_name]['candle'] = []
        for index, item in enumerate(candle_list):
            time_stamp  = int( int(item[0]) / 1000)
            candle_time = datetime.datetime.fromtimestamp(time_stamp).strftime("%y-%m-%d %H:%M:%S")
            open_price = float( item[1] )
            high_price = float ( item[2])
            low_price = float( item [3])
            close_price = float( item[4] )
            amount = float( item[5])
            candle_info[symbol_name]['candle'].append( {'time': candle_time, 'open': open_price, 'high': high_price, 'low': low_price, 'close': close_price, 'amount': amount } )

    close_price_list = [ n['close'] for n in candle_info[symbol_name]['candle']  ]
    close_price_list = close_price_list[::-1]

    candle_info[symbol_name]['mean20']  = []
    candle_info[symbol_name]['bol 20, 2 upper']  = []
    candle_info[symbol_name]['bol 20, 2 lower']  = []
    candle_info[symbol_name]['mean5']  = []
    # 20 avr
    for index, item in enumerate( close_price_list  ):

        mean_target = 20 

        if( index >= mean_target ):
            mean_target_list =  close_price_list[index - mean_target: index ]

            mean_value = numpy.mean( mean_target_list ) 
            std_value = numpy.std( mean_target_list ) * 2

            candle_info[symbol_name]['mean{}'.format( mean_target )].append( round( mean_value , 3 ) )
            candle_info[symbol_name]['bol 20, 2 upper'].append( round( mean_value + std_value , 3 ) )
            candle_info[symbol_name]['bol 20, 2 lower'].append( round( mean_value  - std_value , 3 ) )
        else:
            candle_info[symbol_name]['mean{}'.format( mean_target )].append(None)
            candle_info[symbol_name]['bol 20, 2 upper'].append(None)
            candle_info[symbol_name]['bol 20, 2 lower'].append(None)

        mean_target = 5

        if( index >= mean_target ):
            mean_target_list =  close_price_list[index - mean_target: index ]
            mean_value = numpy.mean( mean_target_list ) 
            candle_info[symbol_name]['mean{}'.format( mean_target )].append( round( mean_value, 3 ) )
        else:
            candle_info[symbol_name]['mean{}'.format( mean_target )].append( None )
        

   




def calculate_option_pair_profit():
    total_profit = {}

    for key, value in jango_info.items():
        if( '-' not in key ):
            break
        if( '-P' not in key and '-C' not in key ):
            continue
        symbol_pair_name = key.split('-')[1]
        if( symbol_pair_name not in total_profit ):
            total_profit[symbol_pair_name] = {} 
            total_profit[symbol_pair_name]['profit'] = 0
            total_profit[symbol_pair_name]['pnl value'] = 0


        total_profit[symbol_pair_name]['profit'] = round( total_profit[symbol_pair_name]['profit'] + value['profit'], 2)
        total_profit[symbol_pair_name]['pnl value'] = round( total_profit[symbol_pair_name]['pnl value'] + value['pnl value'], 2)

    for key, value in total_profit.items():
        info = '{:>10}, profit: {:>20},  pnl: {:<30}'.format(key, value['profit'], value['pnl value']) 
        log.info(info)
        if( value['profit'] > value['pnl value'] * 0.02 ):
            for symbol_name in jango_info:
                if( key in symbol_name):
                    file_log.warning( '{}'.format( jango_info[symbol_name] ) )
            file_log.warning( info )
            make_place_order_option( key )

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


def make_place_order_option(symbol_pair_name: str, maemae_type : str):
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
            request['side'] = maemae_type
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

def make_place_order_linear(symbol_name: str, maemae_type: str, qty: str):

    requests = []
    request = {}

    if( len(order_book_info[symbol_name]['b']) != 0):
        request['category'] = 'linear' 
        request['symbol'] = symbol_name
        request['orderType'] = 'Market'
        request['side'] =  maemae_type
        request['qty'] = qty

        # 호가가 자주 변하므로 3호가 위 가격으로 매매  
        price = ''
        if( maemae_type == "Sell"):
            price = order_book_info[symbol_name]['b'][3][0]
        else:
            price = order_book_info[symbol_name]['a'][3][0]
        request['price'] = price

        request['orderLinkId'] =  "{}-{}, {}, {}".format(  symbol_name, datetime.datetime.now().strftime("%H:%M:%S"), maemae_type, price ) # should be unique string 
        requests.append( request )

    result = session.place_batch_order(
        category = "linear",
        request = requests
    )

    if( result['retMsg'] == 'OK' ):
        result = result['result']['list']

        file_log.warning( json.dumps( result, indent=2 ))
        print( json.dumps(result, indent=2)  )


# kakao 에 로그인 하여 access 토큰을 얻어야 함 
# 한번 얻으면 계속 사용 가능 
def kakao_get_redirect_url():

    # 카카오 인증코드 발급 URL 생성
    auth_url = MSG.get_url_for_generating_code()
    print("")
    print( auth_url )
    print("")

    # redirect url 에서 parameter 정보를 얻기 위함 
    class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write('<h1>redirect url 수집이 완료되었습니다</h1>'.encode('utf-8'))
            global kakao_redirect_url
            kakao_redirect_url = 'https://localhost:{}{}}'.format(server_port_number, self.path)
            print(kakao_redirect_url)
            self.server.server_close()


    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.load_cert_chain( certfile="auth/CA.pem", keyfile="auth/CA.key") # PUT YOUR cert.pem HERE

    server_address = ("localhost", server_port_number) # CHANGE THIS IP & PORT

    handler = SimpleHTTPRequestHandler

    print(f'Server running on port:{server_port_number}')
    try:
        with socketserver.TCPServer(server_address, handler) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            httpd.serve_forever()
    except Exception as e:
        print("except {}".format( e ))
    
def connect_kakao_api():
    # 카카오 엑세스 토큰을 받으려면 카카오에 로그인후 redirect 되는 url 을 넣어주어야 하는데
    # 로컬로 서버를 만들어서 리다이렉트 url 을 얻어 오는 방식을 취함 
    kakao_get_redirect_url()

    # 위 URL로 액세스 토큰 추출
    access_token = MSG.get_access_token_by_redirected_url(kakao_redirect_url)

    # 액세스 토큰 설정
    MSG.set_access_token(access_token)

    text = "option wather 실행하였습니다."
    button_title = "바로 확인"
    MSG.send_text(text=text, link={}, button_title=button_title)


def determine_buy_and_sell(symbol_name: str):
    # exclude option
    maemae_type = 'Buy'

    last_candle = candle_info[symbol_name]['candle'][1]
    current_candle = candle_info[symbol_name]['candle'][0]
    # print( current_candle )

    last_low_price = last_candle['low']
    last_high_price = last_candle['high']
    current_price = current_candle['close']


    qty = "0.01"

    # 매수 된게 없고 천고가 넘으면 
    if( 
        # True
        last_high_price < current_price  
        and symbol_name not in jango_info
       ):
        # bid 기준 current price
        current_price = order_book_info[symbol_name]['b'][0][0]
        print( '\nbuy  last low {}, high {} current {}'.format( last_low_price, last_high_price, current_price) )
        maemae_type = "Buy"
        make_place_order_linear( symbol_name, maemae_type, qty )
        pass
    elif( 
        # True
        last_low_price > current_price and symbol_name in jango_info
        ):
        print( '\nsell  last low {}, high {} current {}'.format( last_low_price, last_high_price, current_price) )
        current_price = order_book_info[symbol_name]['a'][0][0]
        # ask 기준 current price
        # qty = '0' # Sell All
        qty = jango_info[symbol_name]['size']
        maemae_type = 'Sell'
        make_place_order_linear( symbol_name, maemae_type, qty )
        pass


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
    # symbol_name = "XRPUSDT"
    symbol_name = "ETHUSDT"
    while True:
        try:

            get_positions(category="linear", symbol = symbol_name)


            get_orderbook(category="linear", symbol_name= symbol_name)
            # calculate_linear_profit()
            # calculate_option_strangle_pair_profit()

            # Kline interval. 1,3,5,15,30,60,120,240,360,720,D,M,W
            # get_candle(category="linear", symbol_name = symbol_name, interval="D")
            get_candle(category="linear", symbol_name = symbol_name, interval="15")

            determine_buy_and_sell(symbol_name)

            time.sleep(0.1)
            count = count + 1
            print("-", end='')
        except Exception as e:
            print("except {}".format( e ))
            time.sleep(5)



    pass