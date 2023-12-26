import queue
import subprocess
import threading
from threading import Thread

from config import settings
from db import DataBase
from stock_api.order_conn import ByBitApi
from stock_api.socket_conn import SocketConn
from trade.token_trader import TokenTrader

bybit = ByBitApi(settings.api_key, settings.api_secret)
database = DataBase()


def execution_websocket():
    order_queue = queue.Queue()
    threading.Thread(target=SocketConn,
                     args=(
                         f'{settings.websocket_url}/v5/private',
                         ['execution.linear'],
                         order_queue,
                         'auth'
                     )).start()


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
    trading_pairs_str = settings.trading_pairs
    pairs = [tuple(pair.split(':')) for pair in trading_pairs_str.split(',')]
    pairs = [(pair, float(volume)) for pair, volume in pairs]
    main(pairs)
