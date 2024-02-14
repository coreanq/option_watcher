
from PyKakao import Message
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl, socketserver

from pybit.unified_trading import HTTP
import sys, json,datetime, time, logging, datetime, numpy

api_key = ''
api_secret = ''
kakao_rest_api_key = ''
kakao_redirect_url = ''
dollar_amount = 100


# 메시지 API 인스턴스 생성
MSG = Message(service_key = kakao_rest_api_key )


log = logging.getLogger(__name__)
file_log = logging.getLogger(__name__ + '_file')

jango_info  = {}
coin_info = {} # 코인 전반적인 정보로 보유하지 않아도 관련 정보를 가지고 있다 .
interval = 15

event_occur_date_time  = None

server_port_number = 5678

#최소 주문 단위를 얻기 위함 
def get_instruments_info(category :str, symbol_name_list : list):

    for symbol_name in symbol_name_list:
        result = (
            session.get_instruments_info(
                category= category,
                symbol= symbol_name
            ))
        coin_info[symbol_name] = {}
        if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
            instruments_info = result['result']['list'][0]
            coin_info[symbol_name]['min_qty'] = instruments_info['lotSizeFilter']['minOrderQty']
            coin_info[symbol_name]['max_qty'] = instruments_info['lotSizeFilter']['maxOrderQty']
            coin_info[symbol_name]['qty_step'] = instruments_info['lotSizeFilter']['qtyStep']


def get_positions(category :str, settle_coin :str):

    # for symbol in symbol_name_list:
    result = (session.get_positions(
        category= category,
        settleCoin = settle_coin,
    ))


    if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
        result = result['result']['list']

    global jango_info
    jango_info = {}
    # 잔고가 복수일수 있음 
    for item in result:
        symbol_name = item['symbol']

        for del_key in ['leverage', 'autoAddMargin', 'liqPrice', 'riskLimitValue', 'trailingStop', 
                        'takeProfit', 'tpslMode', 'riskId', 'adlRankIndicator', 'positionMM', 'positionIdx', 
                        'positionIM', 'bustPrice', 'positionBalance', 'stopLoss', 'tradeMode',
                        'createdTime', 'updatedTime', 'seq']:
            del item[del_key]
        if( item['size'] == '0' ):
            if( symbol_name in jango_info):
                del jango_info[symbol_name] 
        else:
            jango_info[symbol_name] = item
    


def get_orderbook(category : str, symbol_name_list: list):

    for symbol_name in symbol_name_list:
        result = (session.get_orderbook(
            category = category,
            symbol= symbol_name,
            limit = 100
        ))

        if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
            result = result['result']
            # no longer contract avaliable 
            if( 'b' not in result  ):
                pass
            else:
                if( symbol_name not in coin_info):
                    coin_info[symbol_name] = {}
                coin_info[symbol_name]['b'] = result['b']
                coin_info[symbol_name]['a'] = result['a']


# 20봉/ 5봉 평균 추가 
def get_candle(category :str, symbol_name_list : list, interval : str):

    for symbol_name in symbol_name_list:
        result = (
            session.get_kline(
                category= category,
                symbol= symbol_name,
                interval= interval, 
                limit = 50,
            ))
        if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
            candle_list = result['result']['list']

            if( symbol_name not in coin_info ):
                coin_info[symbol_name] = {}

            coin_info[symbol_name]['candle'] = []
            for index, item in enumerate(candle_list):
                time_stamp  = int( int(item[0]) / 1000)
                candle_time = datetime.datetime.fromtimestamp(time_stamp).strftime("%y-%m-%d %H:%M:%S")
                open_price = float( item[1] )
                high_price = float ( item[2])
                low_price = float( item [3])
                close_price = float( item[4] )
                amount = float( item[5])
                coin_info[symbol_name]['candle'].append( {'time': candle_time, 'open': open_price, 'high': high_price, 'low': low_price, 'close': close_price, 'amount': amount } )

        close_price_list = [ n['close'] for n in coin_info[symbol_name]['candle']  ]
        close_price_list = close_price_list[::-1]

        coin_info[symbol_name]['mean20']  = []
        coin_info[symbol_name]['bol 20, 2 upper']  = []
        coin_info[symbol_name]['bol 20, 2 lower']  = []
        coin_info[symbol_name]['mean5']  = []
        coin_info[symbol_name]['is downtrend']  = []
        coin_info[symbol_name]['is uptrend']  = []
        coin_info[symbol_name]['is bol lower']  = []
        coin_info[symbol_name]['is bol upper']  = []
        # 20 avr
        for index, item in enumerate( close_price_list  ):

            mean_target = 20 

            if( index >= mean_target ):
                mean_target_list =  close_price_list[index - mean_target: index ]

                mean_value = numpy.mean( mean_target_list ) 
                std_value = numpy.std( mean_target_list ) * 2

                coin_info[symbol_name]['mean{}'.format( mean_target )].append( round( mean_value , 6 ) )
                coin_info[symbol_name]['bol 20, 2 upper'].append( round( mean_value + std_value , 6 ) )
                coin_info[symbol_name]['bol 20, 2 lower'].append( round( mean_value  - std_value , 6 ) )
                coin_info[symbol_name]['bol 20, 2 lower'].append( round( mean_value  - std_value , 6 ) )

                if( close_price_list[index] > mean_value ):
                    coin_info[symbol_name]['is downtrend'].append( False )
                    coin_info[symbol_name]['is uptrend'].append( True )
                else:
                    coin_info[symbol_name]['is downtrend'].append( True )
                    coin_info[symbol_name]['is uptrend'].append( False )

                if( close_price_list[index] > (mean_value + std_value) ):
                    coin_info[symbol_name]['is bol upper'].append( True )
                else:
                    coin_info[symbol_name]['is bol upper'].append( False )

                if( close_price_list[index] < (mean_value - std_value ) ):
                    coin_info[symbol_name]['is bol lower'].append( True )
                else:
                    coin_info[symbol_name]['is bol lower'].append( False )
            else:
                coin_info[symbol_name]['mean{}'.format( mean_target )].append(None)
                coin_info[symbol_name]['bol 20, 2 upper'].append(None)
                coin_info[symbol_name]['bol 20, 2 lower'].append(None)
                coin_info[symbol_name]['is downtrend'].append( None )
                coin_info[symbol_name]['is uptrend'].append( None )
                coin_info[symbol_name]['is bol upper'].append( None )
                coin_info[symbol_name]['is bol lower'].append( None )

            mean_target = 5

            if( index >= mean_target ):
                mean_target_list =  close_price_list[index - mean_target: index ]
                mean_value = numpy.mean( mean_target_list ) 
                coin_info[symbol_name]['mean{}'.format( mean_target )].append( round( mean_value, 6 ) )
            else:
                coin_info[symbol_name]['mean{}'.format( mean_target )].append( None )
        

   



def get_symbol_name_list() -> list:
    symbol_name_list = []
    jango_keys = jango_info.keys()

    return jango_keys




def calculate_option_pair_profit():
    total_profit = {}

    for key, value in jango_info.items():

        # option symbol 명 아닌경우 걸러냄 
        if( '-' not in key ):
            break
        if( '-P' not in key and '-C' not in key ):
            continue
        symbol_pair_name = key.split('-')[1]
        if( symbol_pair_name not in total_profit ):
            total_profit[symbol_pair_name] = {} 
            total_profit[symbol_pair_name]['profit'] = 0
            total_profit[symbol_pair_name]['pnl value'] = 0

        total_profit[symbol_pair_name]['profit'] = round( total_profit[symbol_pair_name]['profit'] + value['profit'], 6)
        total_profit[symbol_pair_name]['pnl value'] = round( total_profit[symbol_pair_name]['pnl value'] + value['pnl value'], 6)

    for key, value in total_profit.items():
        info = '{:>10}, profit: {:>20},  pnl: {:<30}'.format(key, value['profit'], value['pnl value']) 
        log.info(info)

        # 전체 투자 금액 대비 수익이 얼마나 나면 팔건지 결정 
        if( value['profit'] > value['pnl value'] * 0.10 ): # 10%
            for symbol_name in jango_info:
                if( key in symbol_name):
                    file_log.warning( '{}'.format( jango_info[symbol_name] ) )
            file_log.warning( info )
            make_place_order_option( key )


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


def make_place_order_linear(symbol_name: str, maemae_side: str, qty: str, reduced_only : bool = True)-> list:
    request = {}

    price = str(coin_info[symbol_name]['candle'][0]['close']) # 어차피 시장가 갯수 계산용 
    request['price'] = price

    request['reduceOnly'] = reduced_only # Sell 주문이 Short 으로 나가면 역방향으로 계좌 증가하므로 증가하는 방향은 자제 하게 함 
    request['category'] = 'linear' 
    request['symbol'] = symbol_name
    request['orderType'] = 'Market'
    request['side'] =  maemae_side
    request['qty'] = qty

    avg_price = '0'
    if( symbol_name in jango_info ):
        avg_price = jango_info[symbol_name]['avgPrice']


    # 0.00055 fee
    avg_price_fee = float(avg_price)  * 0.00055 
    price_fee = float(price)  * 0.00055

    profit  = (float(price) - float(avg_price)) * float(qty) - avg_price_fee - price_fee

    position_type = ''
    if( symbol_name in jango_info ):
        position_type = "Close"
    else:
        position_type = "Open"

    link_order_id_string = "{} {}({})-{}, profit:{} ".format(  
        position_type, maemae_side, 
        qty,
        datetime.datetime.now().strftime("%H:%M:%S"), 
        round(profit, 6),

        ) # should be unique string 

    request['orderLinkId'] = link_order_id_string
    return request
def determine_buy_and_sell(symbol_name_list: list):

    requests = []
    maemae_side = 'Buy'
    position_type = ""

    for symbol_name in symbol_name_list:
        # exclude option
        if( 'maesu_wait_time' in coin_info[symbol_name] ):
            at_time_str = coin_info[symbol_name]['maesu_wait_time']
            at_time = datetime.datetime.strptime(at_time_str , "%H:%M:%S")

            time_span = datetime.timedelta(minutes=interval * 2)

            if( datetime.datetime.now().time() > (at_time + time_span).time() ):
                del coin_info[symbol_name]['maesu_wait_time']
            else:
                continue

        last_candle = coin_info[symbol_name]['candle'][1]
        current_candle = coin_info[symbol_name]['candle'][0]
        # print( current_candle )

        last_open_price = last_candle['open']
        last_close_price = last_candle['close']
        last_low_price = last_candle['low']
        last_high_price = last_candle['high']

        is_bol_20_lower = coin_info[symbol_name]['is bol lower'][-1]
        is_bol_20_upper = coin_info[symbol_name]['is bol upper'][-1]
        last_downtrend_list = coin_info[symbol_name]['is downtrend'][ len( coin_info[symbol_name]['is downtrend']) - 5:]
        last_uptrend_list = coin_info[symbol_name]['is uptrend'][ len( coin_info[symbol_name]['is uptrend']) - 5:]
        mean_20 = coin_info[symbol_name]['mean20'][-1]


        current_price = current_candle['close']
        qty_step = coin_info[symbol_name]['qty_step']

        if( symbol_name in jango_info ):
            # Position Close
            position_type = "Close"

            maemae_side = jango_info[symbol_name]['side']
            if( maemae_side == 'Buy'):
                #Long Side
                if( 
                    # True
                    (mean_20 < current_price) 
                    # cosequtive 3 True
                    or ( all (coin_info[symbol_name]['is bol lower'][ len(coin_info[symbol_name]['is bol lower']) -3: ] ) )

                    ):
                    print( '\nClose Long, {}, current:{}'.format( symbol_name, current_price) )
                    # qty = '0' # Close All Bug

                    # close 하기 위해서 반대 사이드로 같은 양을 주문을 내보낸다 
                    maemae_side = 'Sell'
                    qty = jango_info[symbol_name]['size']

                    requests.append( make_place_order_linear( symbol_name, maemae_side, qty=qty, reduced_only=True ) )
            else:
                # Short Side
                if(
                    # True
                    (mean_20 > current_price) 
                    # cosequtive 3 True
                    or ( all (coin_info[symbol_name]['is bol upper'][ len(coin_info[symbol_name]['is bol upper']) -3: ] ) )

                    ):
                    print( '\nClose Short, {}, current:{}'.format( symbol_name, current_price) )
                    # qty = '0' # Close All Bug

                    # close 하기 위해서 반대 사이드로 같은 양을 주문을 내보낸다 
                    maemae_side = 'Buy'
                    qty = jango_info[symbol_name]['size']

                    requests.append( make_place_order_linear( symbol_name, maemae_side, qty=qty, reduced_only=True ) )
        else:
            # Position Open
            position_type = "Open"
            if( 
                # True
                (is_bol_20_lower == True)  
                and (not all(last_downtrend_list) )
            ):
                # Long Side
                print( '\nOpen Long  {} current {}'.format( symbol_name,  current_price) )
                maemae_side = "Buy"

                # qty_step 0.001  0.1 string 을 제외하면 round 뒷자리 인수가 됨
                qty = str( round( float(dollar_amount) / float(current_price), len(qty_step) -2 ) )
                requests.append( make_place_order_linear( symbol_name, maemae_side, qty=qty, reduced_only=False) )
                pass
            elif( 
                # False and
                (is_bol_20_upper == True)  
                and (not all(last_uptrend_list) )
            ):
                # Short Side
                print( '\nOpen Short {} current {}'.format( symbol_name, current_price) )
                maemae_side = "Sell"

                # qty_step 0.001  0.1 string 을 제외하면 round 뒷자리 인수가 됨
                qty = str( round( float(dollar_amount) / float(current_price), len(qty_step) -2 ) )
                requests.append( make_place_order_linear( symbol_name, maemae_side, qty=qty, reduced_only=False) )
                pass
        
    if( len(requests) ):
        result = session.place_batch_order(
            category = "linear",
            request = requests
        )

        if( result['retMsg'] == 'OK' ):
            result = result['result']['list']

            for item in result:
                # 매도 결과이면 
                if( 'Close' in item['orderLinkId'] ):
                    coin_info[item['symbol']]['maesu_wait_time'] = datetime.datetime.now().strftime("%H:%M:%S")

            file_log.warning( json.dumps( result, indent=2 ))
            print( json.dumps(result, indent=2)  )
            get_positions(category="linear", settle_coin="USDT")
        else:
            print(result)

            # Close 무응답인 경우도 무한 매수 매도를 방지 하기 위한 코드 
            if( position_type == "Close"):
                # 매도 결과이면 
                for key, value in coin_info.items():
                    coin_info[key]['maesu_wait_time'] = datetime.datetime.now().strftime("%H:%M:%S")
                pass

        pass


def processLinear():

    count = 0

    symbol_name_list = [
                        'BTCUSDT', 
                        'ETHUSDT', 
                        'XRPUSDT', 
                        'SOLUSDT' 
                        ]

    get_instruments_info(category="linear", symbol_name_list= symbol_name_list)
    get_positions(category="linear", settle_coin= 'USDT')

    while True:
        try:
            # for linear
            # Kline interval. 1,3,5,15,30,60,120,240,360,720,D,M,W
            get_candle(category="linear", symbol_name_list = symbol_name_list, interval= str(interval) )
            determine_buy_and_sell(symbol_name_list)
            time.sleep(0.1)
            count = count + 1
            print("-", end='')
        except Exception as e:
            print("except {}".format( e ))
            time.sleep(3)

def processOption():

    get_positions(category="option", settle_coin= 'USDC')
    symbol_name_list = list( get_symbol_name_list() )

    while True:
        try:
            # for option
            get_orderbook(category="option", symbol_name_list=symbol_name_list)

            for symbol_name in symbol_name_list:
                bid_list = coin_info[symbol_name]['b']

                current_price = 0 
                current_size = float(jango_info[symbol_name]['size'])
                # check size and bid_list amount             
                bid_total_amount = 0
                current_price = 0
                for item in bid_list:
                    bid_total_amount += float(item[1])

                    # 보유 수량에 따라 bid 수량을 검색해 최적으로 팔수 있는 가격을 찾아냄 
                    if( current_size < bid_total_amount ):
                        current_price = float(item[0])
                        break

                original_price = float( jango_info[symbol_name]['avgPrice'] ) 
                fee = - float(  jango_info[symbol_name]['cumRealisedPnl'] )

                # fee * 2 when buy and sell
                jango_info[symbol_name]['profit'] = round( current_price * current_size  - original_price * current_size  - (fee * 2), 2)
                jango_info[symbol_name]['pnl value'] = round( original_price * current_size , 2)

            calculate_option_pair_profit()

            time.sleep(0.1)
            print("-", end='')
        except Exception as e:
            print("except {}".format( e ))
            time.sleep(3)





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

    arg = ''
    if( len(sys.argv) > 1):
        arg = sys.argv[1]
    with open('auth/auth_info{}.json'.format( arg )) as f:
        auth_info = json.load(f)
        api_key = auth_info['api_key']
        api_secret = auth_info['api_secret']
        kakao_rest_api_key = auth_info.get('kakao_rest_api_key', '')

    session = HTTP(
        testnet=False,
        api_key= api_key,
        api_secret= api_secret
    )

    dollar_amount = 100

    # processLinear()
    processOption()

    pass