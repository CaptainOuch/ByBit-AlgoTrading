import os

import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv

load_dotenv()


def connect_to_db() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        host='db',
        port=5432
    )


def save_trade_to_db(
    token: str,
    order_id: str,
    position_size: float,
    side: str,
    order_type: str,
    price: float
) -> None:
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trade_data
                (token, order_id, position_size, side, order_type, price)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (token, order_id, position_size, side, order_type, price))
            conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn is not None:
            conn.close()
