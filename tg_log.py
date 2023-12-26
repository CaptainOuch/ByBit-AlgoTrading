import json
import os
import select
from typing import Optional

import psycopg2.extensions
from dotenv import load_dotenv
from pyrogram import Client

from db import DataBase
from stock_api.order_conn import logging

load_dotenv()

database = DataBase()


api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
channel_id = os.getenv('CHANNEL_ID')


last_buy_price: Optional[float] = None


def _format_message(raw_message: str) -> str:
    global last_buy_price
    data = json.loads(raw_message)

    if data['side'] == 'Buy':
        last_buy_price = data['price']

    if data['side'] == 'Sell' and last_buy_price is not None:
        pnl = (data['price'] - last_buy_price) * data.get('position_size')
        pnl = round(pnl, 3)
        data['pnl'] = pnl

    formatted_message = ""
    keys_to_exclude = ['id', 'order_id', 'date_created']
    for key, value in data.items():
        if key not in keys_to_exclude and value is not None:
            formatted_message += f'{key}: {value}\n'
    return formatted_message


def send_telegram_message(raw_message: str) -> None:
    message = _format_message(raw_message)
    app.send_message(channel_id, message)


conn = database.connect_to_db()
conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()
cur.execute('LISTEN new_trade_channel;')

logging.info('Waiting for notifications on channel \'new_trade_channel\'')

try:
    with Client('my_account', api_id=api_id, api_hash=api_hash) as app:
        while True:
            if not select.select([conn], [], [], 5) == ([], [], []):
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    print('Got NOTIFY:', notify.pid, notify.channel, notify.payload)
                    send_telegram_message(notify.payload)
finally:
    cur.close()
    conn.close()
