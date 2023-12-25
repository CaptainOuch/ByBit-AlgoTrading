import _thread
import json
import os
import queue
import subprocess
import threading
import time
from enum import Enum
from threading import Thread
from typing import Optional, List

import websocket
from dotenv import load_dotenv

from db import save_trade_to_db
from modules import get_valid_order, calculate_pnl, ByBitApi, logging

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
if os.getenv('IS_TEST') == 'True':
    WEBSOCKET_URL = 'wss://stream-testnet.bybit.com'
else:
    WEBSOCKET_URL = 'wss://stream.bybit.com'

DELAY = 0.42

bybit = ByBitApi(API_KEY, API_SECRET)


def execution_websocket():
    order_queue = queue.Queue()
    threading.Thread(target=SocketConn,
                     args=(
                         f'{WEBSOCKET_URL}/v5/private',
                         ['execution.linear'],
                         order_queue,
                         'auth'
                     )).start()


class OrderType(Enum):
    BID = "bid"
    ASK = "ask"


class SocketConn(websocket.WebSocketApp):
    def __init__(
        self,
        url: str,
        params: Optional[List[str]] = None,
        message_queue: Optional[queue.Queue] = None,
        op: Optional[str] = None
    ) -> None:
        super().__init__(url=url, on_open=self.on_open)

        if params is None:
            params = []
        self.params = params
        self.message_queue = message_queue
        self.op = op
        self.on_message = lambda ws, msg: self.message(msg)
        self.on_error = lambda ws, e: logging.info('Error', e)
        self.on_close = lambda ws: logging.info('Closing')

        self.run_forever()

    @staticmethod
    def __send_ping(ws,):
        ping_message = {"req_id": "100001", "op": "ping"}
        ws.send(json.dumps(ping_message))

    @staticmethod
    def _send_auth(ws,):
        expires = int((time.time() + 10) * 1000)
        _val = f'GET/realtime{expires}'
        signature = bybit.hashing(f'GET/realtime{expires}')
        ws.send(json.dumps({"op": "auth", "args": [API_KEY, expires, signature]}))

    def _ping_loop(self, ws,):
        while True:
            self.__send_ping(ws)
            time.sleep(20)

    def on_open(self, ws,):
        logging.info('Wesocket was opened')

        threading.Thread(target=self._ping_loop, args=(ws,)).start()

        def run(*args):
            if self.op == 'auth':
                self._send_auth(ws)
            trade_str = {'op': 'subscribe', 'args': self.params}
            ws.send(json.dumps(trade_str))

        _thread.start_new_thread(run, ())

    @staticmethod
    def _process_message_to_db(msg):
        if isinstance(msg, str):
            msg = json.loads(msg)

        if not msg.get('data'):
            return

        data = msg.get('data', [])[-1]

        token = data.get('symbol')
        order_id = data.get('orderId')
        order_type = data.get('orderType')
        position_size = data.get('execQty')
        side = data.get('side')
        price = data.get('execPrice')

        if token == "":
            token = None
        if order_id == "":
            order_id = None
        if position_size == "":
            position_size = None
        if side == "":
            side = None
        if order_type == "":
            order_type = None
        if price == "":
            price = None

        save_trade_to_db(token, order_id, position_size, side, order_type, price)

        return

    def message(self, msg):
        if self.message_queue is not None:
            self.message_queue.put(msg)

        if self.op == 'auth':
            self._process_message_to_db(msg)


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

    def check_placed_orders(self):
        while True:
            order = bybit.get_open_order(
                'linear', self.token
            ).get('result', {}).get('list', None)

            if order:
                logging.info(f'Order {self.token} already made manually')
                logging.info(f'Waiting {DELAY} seconds before running again')
                time.sleep(DELAY)
                continue
            position_size = float(
                bybit.get_open_position(
                    'linear', self.token
                )['result']['list'][0]['size'])
            if position_size != 0:
                logging.info(f'Position {self.token} already made manually')
                logging.info(f'Waiting {DELAY} seconds before running again')
                time.sleep(DELAY)
                continue

            return

    def await_order_execution(self, order_id):
        while True:
            logging.info('Waiting for order to execute')
            time.sleep(DELAY)

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
                             f'{WEBSOCKET_URL}/v5/public/linear',
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
                time.sleep(DELAY)


def run_logging_script():
    subprocess.run(["python", "tg_log.py"])


def main(tokens):
    logging_thread = Thread(target=run_logging_script)
    logging_thread.start()
    execution_websocket()

    threads = []
    for token, qty in tokens:
        trader = TokenTrader(token, qty)
        trader.start()
        threads.append(trader)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    trading_pairs_str = os.getenv("TRADING_PAIRS")
    pairs = [tuple(pair.split(':')) for pair in trading_pairs_str.split(',')]
    pairs = [(pair, float(volume)) for pair, volume in pairs]
    main(pairs)
