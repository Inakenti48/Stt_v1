import sqlite3

# from orders_db_v1_5 import get_binance_futures_symbols

conn_asks = sqlite3.connect("orders_asks.db")
cursor_asks = conn_asks.cursor()

conn_bids = sqlite3.connect("orders_bids.db")
cursor_bids = conn_bids.cursor()

for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    cursor_asks.execute(f"DROP TABLE IF EXISTS orders_{symbol}")
    cursor_bids.execute(f"DROP TABLE IF EXISTS orders_{symbol}")
