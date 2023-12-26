import queue
import threading
import time
from enum import Enum

from config import settings
from stock_api.order_conn import ByBitApi, logging, get_valid_order, calculate_pnl
from stock_api.socket_conn import SocketConn

bybit = ByBitApi(settings.api_key, settings.api_secret)


class OrderType(Enum):
    BID = "bid"
    ASK = "ask"


class TokenTrader(threading.Thread):
    def __init__(
        self,
        token: str,
        qty: float
    ) -> None:
        threading.Thread.__init__(self)
        self.qty = qty
        self.token = token
        self.order_queue = queue.LifoQueue()
        self.DELAY = 0.42

    def check_placed_orders(self):
        while True:
            order = bybit.get_open_order(
                'linear', self.token
            ).get('result', {}).get('list', None)

            if order:
                logging.info(f'Order {self.token} already made manually')
                logging.info(f'Waiting {self.DELAY} seconds before running again')
                time.sleep(self.DELAY)
                continue
            position_size = float(
                bybit.get_open_position(
                    'linear', self.token
                )['result']['list'][0]['size'])
            if position_size != 0:
                logging.info(f'Position {self.token} already made manually')
                logging.info(f'Waiting {self.DELAY} seconds before running again')
                time.sleep(self.DELAY)
                continue

            return

    def await_order_execution(self, order_id):
        while True:
            logging.info('Waiting for order to execute')
            time.sleep(self.DELAY)

            position_size = float(
                bybit.get_open_position(
                    'linear', self.token
                )['result']['list'][0]['size'])

            if position_size != 0:
                return

            amount, size = get_valid_order(self.order_queue, OrderType.ASK)
            bybit.amend_limit_order(
                'linear', self.token, 'Buy', self.qty, amount, orderId=order_id
            )

    def run(self):
        threading.Thread(target=SocketConn,
                         args=(
                             f'{settings.websocket_url}/v5/public/linear',
                             [f'orderbook.1.{self.token}'],
                             self.order_queue,
                             'subscribe'
                         )).start()

        while True:
            self.check_placed_orders()

            amount, size = get_valid_order(self.order_queue, OrderType.ASK)
            order_id = bybit.place_order(
                'linear', self.token, 'Buy', self.qty, amount
            ).get('result').get('orderId')

            self.await_order_execution(order_id)

            exit_order_id = None
            stop_percent = 0
            five_checkpoint = 0.5
            ten_checkpoint = 1

            while True:
                position_data = bybit.get_open_position('linear', self.token)
                position_size = float(position_data['result']['list'][0]['size'])
                if position_size == 0:
                    logging.info('Position closed. Starting again...')
                    break
                pnl = calculate_pnl(position_data)
                if -0.8 >= pnl:
                    if exit_order_id:
                        bybit.cancel_order('linear', self.token, orderId=exit_order_id)
                        bybit.place_order(
                            'linear', self.token, 'Sell', position_size,
                        )
                    else:
                        bybit.place_order(
                            'linear', self.token, 'Sell', position_size,
                        )
                elif -0.5 >= pnl:
                    amount, size = get_valid_order(self.order_queue, OrderType.BID)
                    if not exit_order_id:
                        exit_order_id = bybit.place_order(
                            'linear',
                            self.token,
                            'Sell',
                            position_size,
                            amount,
                        )['result']['orderId']
                if pnl >= five_checkpoint:
                    stop_percent += 0.0001
                    avg_price = float(position_data['result']['list'][0]['avgPrice'])
                    stop_loss = avg_price * (1 + stop_percent)
                    bybit.set_trading_stop(
                        'linear', self.token, stop_loss, 0,
                    )
                    five_checkpoint += 1

                if pnl >= ten_checkpoint:
                    stop_percent += 0.0004
                    avg_price = float(position_data['result']['list'][0]['avgPrice'])
                    stop_loss = avg_price * (1 + stop_percent)
                    bybit.set_trading_stop(
                        'linear', self.token, stop_loss, 0,
                    )
                    ten_checkpoint += 1
                time.sleep(self.DELAY)
