
from PyKakao import Message
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl, socketserver

from urllib.parse import urlparse

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

def get_positions(category :str, symbol :str):
    result = (session.get_positions(
        category= category,
        symbol = symbol
    ))


    if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
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

        if( result['retMsg'] == "SUCCESS" or result['retMsg'] == 'OK' or result['retMsg'] == "success" ):
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

        if( symbol_name not in jango_info ):
            jango_info[symbol_name] = {}

        jango_info[symbol_name]['candle'] = []
        for index, item in enumerate(candle_list):
            time_stamp  = int( int(item[0]) / 1000)
            candle_time = datetime.datetime.fromtimestamp(time_stamp).strftime("%y-%m-%d %H:%M:%S")
            close_price = float( item[4] )
            amount = float( item[5])
            jango_info[symbol_name]['candle'].append( [candle_time, close_price, amount] )

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

        if( last_price > last_std_upper_value ):
            print( 'bol upper cross')

        if( last_price < last_std_lower_value ):
            print( 'bol lower cross')

        pass



def calculate_option_pair_profit():
    total_profit = {}

    for key, value in jango_info.items():
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
            kakao_redirect_url = 'https://localhost:5000{}'.format(self.path)
            print(kakao_redirect_url)
            self.server.server_close()


    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    context.load_cert_chain("auth/server.pem") # PUT YOUR cert.pem HERE

    port = 5000
    server_address = ("localhost", port) # CHANGE THIS IP & PORT

    handler = SimpleHTTPRequestHandler

    print(f'Server running on port:{port}')
    try:
        with socketserver.TCPServer(server_address, handler) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            httpd.serve_forever()
    except Exception as e:
        print("except {}".format( e ))
    
def send_kakao_message():
    kakao_get_redirect_url()

    # 위 URL로 액세스 토큰 추출
    access_token = MSG.get_access_token_by_redirected_url(kakao_redirect_url)

    # 액세스 토큰 설정
    MSG.set_access_token(access_token)

    # 텍스트 메시지 전송
    content = {
            "title": "오늘의 디저트",
            "description": "아메리카노, 빵, 케익",
            "image_url": "https://mud-kage.kakao.com/dn/NTmhS/btqfEUdFAUf/FjKzkZsnoeE4o19klTOVI1/openlink_640x640s.jpg",
            "image_width": 640,
            "image_height": 640,
            "link": {
                "web_url": "http://www.daum.net",
                "mobile_web_url": "http://m.daum.net",
                "android_execution_params": "contentId=100",
                "ios_execution_params": "contentId=100"
            }
    }

    item_content = {
                "profile_text" :"Kakao",
                "profile_image_url" :"https://mud-kage.kakao.com/dn/Q2iNx/btqgeRgV54P/VLdBs9cvyn8BJXB3o7N8UK/kakaolink40_original.png",
                "title_image_url" : "https://mud-kage.kakao.com/dn/Q2iNx/btqgeRgV54P/VLdBs9cvyn8BJXB3o7N8UK/kakaolink40_original.png",
                "title_image_text" :"Cheese cake",
                "title_image_category" : "Cake",
                "items" : [
                    {
                        "item" :"Cake1",
                        "item_op" : "1000원"
                    },
                    {
                        "item" :"Cake2",
                        "item_op" : "2000원"
                    },
                    {
                        "item" :"Cake3",
                        "item_op" : "3000원"
                    },
                    {
                        "item" :"Cake4",
                        "item_op" : "4000원"
                    },
                    {
                        "item" :"Cake5",
                        "item_op" : "5000원"
                    }
                ],
                "sum" :"Total",
                "sum_op" : "15000원"
            }

    social = {
                "like_count": 100,
                "comment_count": 200,
                "shared_count": 300,
                "view_count": 400,
                "subscriber_count": 500
            }

    buttons = [
                {
                    "title": "웹으로 이동",
                    "link": {
                        "web_url": "http://www.daum.net",
                        "mobile_web_url": "http://m.daum.net"
                    }
                },
                {
                    "title": "앱으로 이동",
                    "link": {
                        "android_execution_params": "contentId=100",
                        "ios_execution_params": "contentId=100"
                    }
                }
            ]

    MSG.send_feed(content=content, item_content=item_content, social=social, buttons=buttons)
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
        # try:
        if( count % 20 == 0 ):
            # 모든 포지션 정보 얻음 
            # get_positions(category="linear", symbol = symbol_name)
            get_positions(category="option", symbol='')
        # get_orderbook(category="linear")
        # calculate_linear_profit()
        get_orderbook(category="option")
        calculate_option_pair_profit()

        get_candle(category="linear", symbol_name = symbol_name, interval="D")

        time.sleep(0.5)
        count = count + 1
        # except Exception as e:
        #     print("except {}".format( e ))
        #     time.sleep(1)



    pass