import os
import sqlite3

from mysql import connector

# from orders_db_v1_5 import get_binance_futures_symbols

# conn_asks = sqlite3.connect("orders_asks.db")
# cursor_asks = conn_asks.cursor()
#
# conn_bids = sqlite3.connect("orders_bids.db")
# cursor_bids = conn_bids.cursor()

DB1_URL = os.getenv("MYSQL_DB1_URL")
DB2_URL = os.getenv("MYSQL_DB2_URL")

# 3306
conn_asks = connector.connect(
    host="mysql.railway.internal",
    user="root",
    password="wjSXUlNJVChjUwEbflMFtqwcNPGJhmIC",
    database="railway"
)

# 3306
conn_bids = connector.connect(
    host="mysql-os9e.railway.internal",
    user="root",
    password="GcBreYeqWjpuPUtVYqjeDwSUQvWxedUo",
    database="railway"
)

cursor_asks = conn_asks.cursor()
cursor_bids = conn_asks.cursor()

for symbol in ("BTCUSDT", "ETHUSDT"):
    cursor_asks.execute(f"DROP TABLE IF EXISTS orders_{symbol}")
    cursor_bids.execute(f"DROP TABLE IF EXISTS orders_{symbol}")
