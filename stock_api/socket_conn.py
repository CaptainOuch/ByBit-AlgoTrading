import _thread
import json
import queue
import threading
import time
from typing import Optional, List

import websocket

from config import settings
from db import DataBase
from stock_api.order_conn import ByBitApi, logging

bybit = ByBitApi(settings.api_key, settings.api_secret)
database = DataBase()


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
        ws.send(json.dumps({"op": "auth", "args": [settings.api_key, expires, signature]}))

    def _ping_loop(self, ws,):
        while True:
            self.__send_ping(ws)
            time.sleep(20)

    def on_open(self, ws,):
        logging.info('Websocket was opened')

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

        database.save_trade_to_db(token, order_id, position_size, side, order_type, price)

        return

    def message(self, msg):
        if self.message_queue is not None:
            self.message_queue.put(msg)

        if self.op == 'auth':
            self._process_message_to_db(msg)
