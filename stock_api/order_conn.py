import hashlib
import hmac
import json
import logging
import time
from enum import Enum
from queue import Queue
from typing import Any, Dict, Optional, Tuple, Union

import requests
from dotenv import load_dotenv

from config import settings

load_dotenv()

logging.basicConfig(level=logging.INFO)

DELAY = 0.42


def get_valid_order(message_queue: Queue, order_type: Enum) -> Tuple[float, float]:
    while True:
        msg = message_queue.get()
        msg_data = json.loads(msg)
        order_data = msg_data.get('data', {}).get(order_type.value[0])

        if order_data and len(order_data) > 0:
            logging.info(f'Valid {order_type.value} received - Price: {order_data[0][0]}, Size: {order_data[0][1]}')
            return order_data[0][0], order_data[0][1]
        else:
            logging.error(f'{order_type.value} list is empty, waiting for next message.')
            time.sleep(DELAY)


def calculate_pnl(data: Dict[str, Any]) -> Optional[float]:
    if float(data['result']['list'][0]['size']) != 0:
        position_data = data['result']['list'][0]

        pnl_percent = ((float(position_data['unrealisedPnl']) / float(position_data['positionValue']))
                       * 100 * float(position_data['leverage']))
        return pnl_percent
    else:
        logging.error('Position not available')
        return False


class ByBitApi:
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()

    def hashing(self, query_string: str) -> str:
        return hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def _header(
        self,
        sign: str,
        timestamp: int,
        recv_window: str
    ) -> Dict[str, str]:
        return {
            "X-BAPI-SIGN": sign,
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-RECV-WINDOW": recv_window
        }

    def _send_request(
        self,
        method: str,
        endpoint: str,
        params: Union[Dict | str]
    ) -> Optional[Dict[str, Any]]:
        url = f"{settings.api_url}/{endpoint}"
        timestamp = int(time.time() * 1000)
        if isinstance(params, dict):
            params = ','.join(f'"{key}": "{value}"' for key, value in params.items())
            params = '{' + params + '}'

        sign = self.hashing(str(timestamp) + self.api_key + "5000" + params)

        headers = self._header(sign, timestamp, '5000')

        try:
            if method.lower() == 'get':
                response = self.session.get(url, headers=headers, params=params)
            elif method.lower() == 'post':
                response = self.session.post(url, headers=headers, data=params)
            else:
                logging.info(f"Неподдерживаемый метод HTTP")
                raise ValueError("Неподдерживаемый метод HTTP")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.info(f"Ошибка запроса: {e}")
            return None

    def get_open_position(self, category: str, coin: str) -> Dict[str, Any]:
        endpoint = '/v5/position/list'
        params = f"category={category}&symbol={coin}"
        return self._send_request('get', endpoint, params)

    def get_open_order(self, category: str, coin: str) -> Dict[str, Any]:
        endpoint = '/v5/order/realtime'
        params = f"category={category}&symbol={coin}"
        return self._send_request('get', endpoint, params)

    def place_order(
        self,
        category: str,
        coin: str,
        side: str,
        qty: float,
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        endpoint = 'v5/order/create'
        if price:
            order_type = 'Limit'
        else:
            order_type = 'Market'
        order_data = {
            "symbol": coin,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "category": category
        }
        if price:
            order_data["price"] = price

        response = self._send_request('post', endpoint, params=order_data)

        logging.info(response)

        return response

    def amend_limit_order(
        self,
        category: str,
        coin: str,
        side: str,
        qty: float,
        price: float,
        orderId: Optional[str] = None
    ) -> Dict[str, Any]:
        endpoint = 'v5/order/amend'
        order_data = {
            "symbol": coin,
            "side": side,
            "orderType": "Limit",
            "qty": qty,
            "price": price,
            "category": category
        }
        if orderId:
            order_data["orderId"] = orderId
        response = self._send_request('post', endpoint, order_data)

        logging.info(response)

        return response

    def cancel_order(
        self,
        category: str,
        coin: str,
        orderId: str
    ) -> Dict[str, Any]:
        endpoint = 'v5/order/cancel'
        order_data = {
            "symbol": coin,
            "orderId": orderId,
            "category": category
        }

        response = self._send_request('post', endpoint, order_data)

        logging.info(response)

        return response

    def set_trading_stop(
        self,
        category: str,
        coin: str,
        stopLoss: float,
        positionIdx: int
    ) -> Dict[str, Any]:
        endpoint = 'v5/position/trading-stop'
        order_data = {
            "symbol": coin,
            "stopLoss": stopLoss,
            "positionIdx": positionIdx,
            "category": category
        }

        response = self._send_request('post', endpoint, order_data)

        logging.info(f'{response}')

        return response
