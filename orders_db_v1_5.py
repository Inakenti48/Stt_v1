import mysql
import requests
from mysql import connector

import os
import sqlite3
from re import search
from time import sleep
from datetime import datetime, timezone
from multiprocessing import Pool
from pprint import pprint


BASE_URL = "https://api.binance.com"


ROUNDING_CONSTANTS = {
    "BTCUSDT": -1,
    "ETHUSDT": 0,
    # "SOLUSDT": 1
}


# def get_binance_futures_symbols() -> list:
#     exchange_info_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
#
#     exchange_info_response = requests.get(exchange_info_url)
#     exchange_info_response.raise_for_status()
#     data = exchange_info_response.json()
#
#     return [symbol_info["symbol"].replace('/', '') for symbol_info in data["symbols"] if not search(r'\d', symbol_info["symbol"])]


def create_databases_by_symbols(cursor, symbols_: list | tuple):
    for symbol in symbols_:
        symbol = symbol.replace('/', '_')
        # AUTO_INCREMENT or AUTOINCREMENT
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS orders_{symbol} (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                price REAL,
                volume REAL,
                color VARCHAR(30)
            )
        ''')


def store_order_in_db(conn, cursor, symbol, price, volume, color):
    cursor.execute(f'''
        INSERT INTO orders_{symbol} (price, volume, color)
        VALUES (?, ?, ?)
    ''', (price, volume, color))
    conn.commit()


def get_orders_dict(cursor, symbol: str, without_colors=False) -> dict:
    cursor.execute(f"SELECT COUNT(*) FROM orders_{symbol}")
    row_count = cursor.fetchone()[0]
    if row_count == 0:  # если количество строк = 0, то есть, если БД пуста
        print(f"Эта БД (orders_{symbol}) пустая!")
        return dict()

    if without_colors:
        cursor.execute(f"SELECT price, volume FROM orders_{symbol}")
        all_orders_list: list = cursor.fetchall()
        all_orders_dict = {row[0]: row[1] for row in all_orders_list}
        pprint(all_orders_dict)
        return all_orders_dict

    cursor.execute(f"SELECT price, volume, color FROM orders_{symbol}")
    all_orders_list: list = cursor.fetchall()
    all_orders_dict = {row[0]: [row[1], row[2]] for row in all_orders_list}
    pprint(all_orders_dict)
    return all_orders_dict


def update_value_in_db(conn,
                       cursor,
                       symbol,
                       column_to_update,
                       condition_column,
                       new_value,
                       condition_value):
    query_for_update = f"UPDATE orders_{symbol} SET {column_to_update} = ? WHERE {condition_column} = ?"
    cursor.execute(query_for_update, (new_value, condition_value))
    conn.commit()


def remove_order_from_db(conn,
                         cursor,
                         symbol,
                         condition_column,
                         condition_value):
    query_for_delete = f"DELETE FROM orders_{symbol} WHERE {condition_column} = ?"
    cursor.execute(query_for_delete, (condition_value,))
    conn.commit()
    print(f"Deleted {cursor.rowcount} row(s)")


def get_order_book(symbol="BTCUSDT", limit=100, book_type: str | None = None) -> dict | list:
    """Fetch the order book for a given symbol."""
    assert book_type in (None, "asks", "bids")

    endpoint = f"/api/v3/depth"
    params = {"symbol": symbol, "limit": limit}
    response = requests.get(BASE_URL + endpoint, params=params, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()  # Raise an error if the request fails
    return_response: dict = response.json()

    if book_type is None:
        return return_response
    if book_type == "asks":
        return [[round(float(asks_data[0])), round(float(asks_data[1]), 4)] for asks_data in return_response.get("asks")]
    return [[round(float(bids_data[0])), round(float(bids_data[1]), 4)] for bids_data in return_response.get("bids")]


def get_latest_price(symbol="BTCUSDT"):
    """Fetch the latest price for a given symbol."""
    endpoint = f"/api/v3/ticker/price"
    params = {
        "symbol": symbol
    }
    response = requests.get(BASE_URL + endpoint, params=params, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return round(float(response.json().get("price")), 4)


def calculate_color(value, max_value, is_ask=True) -> str:
    """
    Calculate color of a bar in dependence on the value of an order
    and the max. value of the entire orders dictionary.
    """

    intensity = value / max_value
    if intensity > 0.58:  # 0.75
        color = "darkred" if is_ask else "darkgreen"
    elif intensity > 0.39:  # 0.5
        color = "red" if is_ask else "green"
    elif intensity > 0.1:  # 0.25
        color = "orange" if is_ask else "lime"
    else:
        color = "lightcoral" if is_ask else "lightgreen"
    return color




def fetch_data(conn_asks,
               cursor_asks,
               conn_bids,
               cursor_bids,
               symbol,
               limit,
               minimum_value):
    """
    Fetch the order book and average price for the given symbol.
    """
    # Fetch current price
    current_price = get_latest_price(symbol)
    order_book = get_order_book(symbol, limit)

    print()
    print('=' * 100)

    def process_retrieved_data(key_to_order_book: str, _current_price: float):
        all_dict = get_orders_dict(cursor_asks if key_to_order_book == "asks" else cursor_bids, symbol)  # 1
        preprocessed_data = {
            round(float(orders_data[0]), ROUNDING_CONSTANTS.get(symbol)): round(float(orders_data[1]), 3)
            for orders_data in order_book[key_to_order_book] if round(float(orders_data[1]), 3) >= minimum_value  # 0.5
        }
        print(f"{key_to_order_book}: {preprocessed_data}")
        for key_price in preprocessed_data.keys():
            current_value = preprocessed_data.get(key_price)
            if all_dict:
                max_value = max(all_dict.values(), key=lambda a: a[0])[0]
            else:
                max_value = max(preprocessed_data.values())

            if key_price not in all_dict.keys():
                store_order_in_db(
                    conn_asks if key_to_order_book == "asks" else conn_bids,
                    cursor_asks if key_to_order_book == "asks" else cursor_bids,
                    symbol,
                    key_price,
                    preprocessed_data.get(key_price),
                    calculate_color(
                        current_value,
                        max_value,
                        is_ask=True if key_to_order_book == "asks" else False
                    )
                )
                # all_dict[key_price] = [preprocessed_data.get(key_price), calculate_color(current_value, max_value, is_ask=True if key_to_order_book == "asks" else False)]
            else:
                if preprocessed_data.get(key_price) != all_dict.get(key_price):
                    print(f"\n\tMATCH: {key_price=} {current_price=}\n")
                    update_value_in_db(
                        conn_asks if key_to_order_book == "asks" else conn_bids,
                        cursor_asks if key_to_order_book == "asks" else cursor_bids,
                        symbol,
                        "volume",
                        "price",
                        all_dict[key_price][0] + preprocessed_data.get(key_price),
                        key_price
                    )
                    # all_dict[key_price][0] += preprocessed_data.get(key_price)

                    update_value_in_db(
                        conn_asks if key_to_order_book == "asks" else conn_bids,
                        cursor_asks if key_to_order_book == "asks" else cursor_bids,
                        symbol,
                        "color",
                        "price",
                        calculate_color(all_dict.get(key_price)[0], max_value, is_ask=True if key_to_order_book == "asks" else False),
                        key_price
                    )
                    # all_dict[key_price][1] = calculate_color(all_dict.get(key_price)[0], max_value, is_ask=True if key_to_order_book == "asks" else False)
        all_dict = get_orders_dict(cursor_asks if key_to_order_book == "asks" else cursor_bids, symbol)  # 2
        i = 0
        while i < len(all_dict.keys()):
            data_price = list(all_dict.keys())[i]
            if key_to_order_book == "asks":
                if data_price < _current_price:
                    print(f"\n\tREMOVED: {data_price}\n")
                    remove_order_from_db(
                        conn_asks,
                        cursor_asks,
                        symbol,
                        "price",
                        data_price
                    )
                    # all_dict.pop(data_price)
                i += 1
            elif key_to_order_book == "bids":
                if data_price > _current_price:
                    print(f"\n\tREMOVED: {data_price}\n")
                    remove_order_from_db(
                        conn_bids,
                        cursor_bids,
                        symbol,
                        "price",
                        data_price
                    )
                    # all_dict.pop(data_price)
                i += 1
            else:
                raise ValueError("Incorrect <key_to_order_book> value!")

        return preprocessed_data

    #  "скопление шортов"
    asks = process_retrieved_data("asks", current_price)
    #  "скопление лонгов"
    bids = process_retrieved_data("bids", current_price)

    print(f"Current price: {current_price}")
    print("Asks (Long Clusters):")
    pprint(asks)
    print("Bids (Short Clusters):")
    pprint(bids)
    print()

    # print("ALL")
    # print("ALL ASKS:")
    # pprint(ALL_ASKS)
    # print("ALL_BIDS:")
    # pprint(ALL_BIDS)


def main(symbol_):
    # symbols = get_binance_futures_symbols()
    symbols_ = ("BTCUSDT", "ETHUSDT")

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


    # conn_asks = sqlite3.connect("orders_asks.db")
    # cursor_asks = conn_asks.cursor()
    #
    # conn_bids = sqlite3.connect("orders_bids.db")
    # cursor_bids = conn_bids.cursor()

    create_databases_by_symbols(cursor_asks, symbols_)
    create_databases_by_symbols(cursor_bids, symbols_)

    fetch_data(
        conn_asks,
        cursor_asks,
        conn_bids,
        cursor_bids,
        symbol_,
        5000,
        1  # 0.103
    )

    cursor_asks.close()
    conn_asks.close()
    cursor_bids.close()
    conn_bids.close()

if __name__ == "__main__":
    # symbols = get_binance_futures_symbols()
    symbols = ("BTCUSDT", "ETHUSDT")

    # asks_test = get_orders_dict(cursor_asks, "BTCUSDT")
    # print(asks_test)

    while True:
        with Pool() as pool:
            pool.map(main, symbols)
            # try:
            #     pool.map(main, symbols)
            # except Exception as e:
            #     print(f"\n\tThe connection was terminated!\nError: {e}")
        sleep(10)

        # TEST
        # asks:
        # print("\nASKS")
        # fetch_data(
        #     conn_asks,
        #     cursor_asks,
        #     conn_bids,
        #     cursor_bids,
        #     "BTCUSDT",
        #     5000,
        #     1  # 0.103
        # )
        # print("ALL ASKS!")
        # pprint(get_orders_dict(cursor_asks, "BTCUSDT"))

        # bids:
        # print("\nBIDS")
        # fetch_data(
        #     conn_bids,
        #     cursor_bids,
        #     "BTCUSDT",
        #     5000,
        #     1  # 0.103
        # )
        # print("ALL BIDS!")
        # pprint(get_orders_dict(cursor_bids, "BTCUSDT"))
        # sleep(10)
