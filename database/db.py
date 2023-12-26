import psycopg2
import psycopg2.extensions

from config import settings


class DataBase:
    def __init__(self):
        self.dbname = settings.postgres_db
        self.user = settings.postgres_user
        self.password = settings.postgres_password
        self.host = settings.host
        self.port = settings.port

    def connect_to_db(self):
        return psycopg2.connect(
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            # host=self.host,
            # port=self.port
        )

    def insert(self, query, values):
        conn = self.connect_to_db()
        try:
            with conn.cursor() as cur:
                cur.execute(query, values)
                conn.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            if conn is not None:
                conn.close()

    def save_trade_to_db(self, token, order_id, position_size, side, order_type, price):
        query = """
            INSERT INTO trade_data
            (token, order_id, position_size, side, order_type, price)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        values = (token, order_id, position_size, side, order_type, price)
        self.insert(query, values)