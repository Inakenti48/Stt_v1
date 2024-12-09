import json
import time
import locale
from pprint import pprint
from dateutil.relativedelta import relativedelta

import ccxt
from flask import Flask, render_template, request, jsonify
import plotly.graph_objs as go
import plotly.io as pio
import pandas as pd

from orders_db_v1_5 import *

app = Flask(__name__)
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")


def make_null_after_t(raw_datetime: str) -> str: return f"{raw_datetime.split('T')[0]}T00:00:00Z"


format_pattern_ = "%Y-%m-%dT%H:%M:%SZ"
dt_now_ = datetime.now(tz=timezone.utc)
START_TIMESTAMPS = {
    "5m": make_null_after_t((dt_now_ - relativedelta(days=3)).strftime(format_pattern_)),
    "15m": make_null_after_t((dt_now_ - relativedelta(days=5)).strftime(format_pattern_)),
    "30m": make_null_after_t((dt_now_ - relativedelta(days=15)).strftime(format_pattern_)),
    "1h": make_null_after_t((dt_now_ - relativedelta(months=1)).strftime(format_pattern_)),
    "2h": make_null_after_t((dt_now_ - relativedelta(days=45)).strftime(format_pattern_)),
    "4h": make_null_after_t((dt_now_ - relativedelta(months=2)).strftime(format_pattern_)),
}


def update_start_timestamps():
    global START_TIMESTAMPS

    format_pattern = "%Y-%m-%dT%H:%M:%SZ"
    dt_now = datetime.now(tz=timezone.utc)

    START_TIMESTAMPS["5m"] = make_null_after_t((dt_now - relativedelta(days=3)).strftime(format_pattern))
    START_TIMESTAMPS["15m"] = make_null_after_t((dt_now - relativedelta(days=5)).strftime(format_pattern))
    START_TIMESTAMPS["30m"] = make_null_after_t((dt_now - relativedelta(days=15)).strftime(format_pattern))
    START_TIMESTAMPS["1h"] = make_null_after_t((dt_now - relativedelta(months=1)).strftime(format_pattern))
    START_TIMESTAMPS["2h"] = make_null_after_t((dt_now - relativedelta(days=45)).strftime(format_pattern))
    START_TIMESTAMPS["4h"] = make_null_after_t((dt_now - relativedelta(months=2)).strftime(format_pattern))


TIMEFRAMES_REFERENCE = {
    "5m": (pd.Timedelta(hours=3), pd.Timedelta(minutes=2.5)),  # minutes  2.33
    "15m": (pd.Timedelta(hours=7), pd.Timedelta(minutes=7.5)),  # minutes
    "30m": (pd.Timedelta(hours=14), pd.Timedelta(minutes=15)),  # minutes
    "1h": (pd.Timedelta(hours=28), pd.Timedelta(minutes=30)),  # hour
    "2h": (pd.Timedelta(hours=56), pd.Timedelta(hours=1)),  # hours
    "4h": (pd.Timedelta(hours=112), pd.Timedelta(hours=2)),  # hours
}

EXCHANGE = ccxt.bybit(
    {
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future'
        }
    }
)

# todo: сделать величину количества криптовалюты в ордере зависимой от текущей цены при неизменной константе по индексу 0
SYMBOLS_CONSTANTS = {
    "BTCUSDT": [10000, 4],  # 1
    "ETHUSDT": [7000, 0.3],
    "SOLUSDT": [5000, 0.05]
}

asks_for_nz = []
bids_for_nz = []
SYMBOL = ""
DF = pd.DataFrame()
TF = ""
time_count = 0
BARS_SCALE_COEF = 0
ID_OF_COMPLETED_ORDERS = dict()
BINANCE_LIMIT = 5000  # 1000
NZ_VOLUME_ROUNDING_CONST = 4

UPDATE_INTERVAL_SEC = 10
total_ask_value = []
total_bid_value = []
nzVolume = 0
BASE_URL = "https://api.binance.com"


# def get_order_book(symbol="BTCUSDT", limit=100, book_type: str | None = None) -> dict | list:
#     """Fetch the order book for a given symbol."""
#     assert book_type in (None, "asks", "bids")
#
#     endpoint = f"/api/v3/depth"
#     params = {"symbol": symbol, "limit": limit}
#     response = requests.get(BASE_URL + endpoint, params=params)
#     response.raise_for_status()  # Raise an error if the request fails
#     return_response: dict = response.json()
#
#     if book_type is None:
#         return return_response
#     if book_type == "asks":
#         return [[round(float(asks_data[0])), round(float(asks_data[1]), 4)] for asks_data in return_response.get("asks")]
#     return [[round(float(bids_data[0])), round(float(bids_data[1]), 4)] for bids_data in return_response.get("bids")]
#
#
# def get_latest_price(symbol="BTCUSDT"):
#     """Fetch the latest price for a given symbol."""
#     endpoint = f"/api/v3/ticker/price"
#     params = {"symbol": symbol}
#     response = requests.get(BASE_URL + endpoint, params=params)
#     response.raise_for_status()
#     return round(float(response.json().get("price")), 4)
#
#
# def calculate_color(value, max_value, is_ask=True) -> str:
#     """
#     Calculate color of a bar in dependence on the value of an order
#     and the max. value of the entire orders dictionary.
#     """
#
#     intensity = value / max_value
#     if intensity > 0.58:  # 0.75
#         color = 'darkred' if is_ask else 'darkgreen'
#     elif intensity > 0.39:  # 0.5
#         color = 'red' if is_ask else 'green'
#     elif intensity > 0.1:  # 0.25
#         color = 'orange' if is_ask else 'lime'
#     else:
#         color = 'lightcoral' if is_ask else 'lightgreen'
#     return color
#
#
# def fetch_data(symbol, limit, minimum_value):
#     """
#     Fetch the order book and average price for the given symbol.
#     """
#     global ALL_ASKS, ALL_BIDS
#     # Fetch current price
#     current_price = get_latest_price(symbol)
#     order_book = get_order_book(symbol, limit)
#
#     print()
#     print('=' * 100)
#
#     def process_retrieved_data(key_to_order_book, all_dict: dict, _current_price: float):
#         preprocessed_data = {
#             round(float(orders_data[0]), -1): round(float(orders_data[1]), 3)
#             for orders_data in order_book[key_to_order_book] if round(float(orders_data[1]), 3) >= minimum_value  # 0.5
#         }
#         print(f"{key_to_order_book}: {preprocessed_data}")
#         for key_price in preprocessed_data.keys():
#             current_value = preprocessed_data.get(key_price)
#             if all_dict:
#                 max_value = max(all_dict.values(), key=lambda a: a[0])[0]
#             else:
#                 max_value = max(preprocessed_data.values())
#
#             if key_price not in all_dict.keys():
#                 all_dict[key_price] = [preprocessed_data.get(key_price), calculate_color(current_value, max_value, is_ask=True if key_to_order_book == "asks" else False)]
#             else:
#                 if preprocessed_data.get(key_price) != all_dict.get(key_price):
#                     print("\n\tMATCH\n")
#                     all_dict[key_price][0] += preprocessed_data.get(key_price)
#                     all_dict[key_price][1] = calculate_color(all_dict.get(key_price)[0], max_value, is_ask=True if key_to_order_book == "asks" else False)
#
#         i = 0
#         while i < len(all_dict.keys()):
#             data_price = list(all_dict.keys())[i]
#             if key_to_order_book == "asks":
#                 if data_price < _current_price:
#                     print(f"\n\tREMOVED: {data_price}\n")
#                     all_dict.pop(data_price)
#                 else:
#                     i += 1
#             elif key_to_order_book == "bids":
#                 if data_price > _current_price:
#                     print(f"\n\tREMOVED: {data_price}\n")
#                     all_dict.pop(data_price)
#                 else:
#                     i += 1
#             else:
#                 raise ValueError("Incorrect <key_to_order_book> value!")
#
#         return preprocessed_data
#
#     #  "скопление шортов"
#     asks = process_retrieved_data("asks", ALL_ASKS, current_price)
#     #  "скопление лонгов"
#     bids = process_retrieved_data("bids", ALL_BIDS, current_price)
#
#     print(f"Current price: {current_price}")
#     print("Asks (Long Clusters):")
#     pprint(asks)
#     print("Bids (Short Clusters):")
#     pprint(bids)
#     print()
#     print("ALL")
#     print("ALL ASKS:")
#     pprint(ALL_ASKS)
#     print("ALL_BIDS:")
#     pprint(ALL_BIDS)


def find_walls(orders, threshold, is_ask=True):
    walls = []
    for price, amount in orders:
        total_value = price * amount
        if total_value >= threshold:
            walls.append((price, amount, total_value))
    return walls


def filter_spoof_orders(walls, threshold):
    filtered_walls = [wall for wall in walls if wall[1] < threshold]
    return filtered_walls


# Функция для получения данных свечного графика
def fetch_candlestick_data(symbol="BTC/USDT", timeframe='15m'):
    START_TIMESTAMP = START_TIMESTAMPS.get(timeframe)
    since = EXCHANGE.parse8601(START_TIMESTAMP)
    ohlcv = []
    while True:
        batch = EXCHANGE.fetch_ohlcv(symbol, timeframe, since=since)
        if len(batch) == 0:
            break
        ohlcv.extend(batch)
        since = batch[-1][0] + (EXCHANGE.parse_timeframe(timeframe) * 1000)
        time.sleep(EXCHANGE.rateLimit / 1000)  # Wait according to rate limit
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df


def retrieve_time_data(row_):
    date_str_ = row_["timestamp"].strftime("%Y-%m-%d")
    time_str_ = row_["timestamp"].strftime("%H:%M")
    minutes_ = row_["timestamp"].minute
    hours_ = row_["timestamp"].hour
    days_ = row_["timestamp"].day
    months_ = row_["timestamp"].month
    # print(f"{hour=} | {minute=} | {type(hour)=} | {type(minute)=}")
    return date_str_, time_str_, minutes_, hours_, days_, months_


def add_date(dates_dict_, date_str_, time_str_, row_) -> None:
    # если дата уже в словаре, добавить время
    if date_str_ in dates_dict_:
        dates_dict_[date_str_][0].append(time_str_)
        dates_dict_[date_str_][1].append(row_["timestamp"])
    else:
        # в ином случае, добавить новый ключ для этой даты
        dates_dict_[date_str_] = [[f"{datetime.strftime(datetime.strptime(date_str_, '%Y-%m-%d'), '%d %b')}"], [row_["timestamp"]]]


def add_date_advanced(dates_dict_, date_str_, time_str_, row_, time_count_) -> None:
    global time_count
    if date_str_ not in dates_dict_.keys():
        dates_dict_[date_str_] = [[f"{datetime.strftime(datetime.strptime(date_str_, '%Y-%m-%d'), '%d %b')}"], [row_["timestamp"]]]
        time_count = 0
    else:
        if time_count == time_count_:
            dates_dict_[date_str_][0].append(time_str_)
            dates_dict_[date_str_][1].append(row_["timestamp"])
            time_count = 0


def update_nz_volume(asks_, bids_, rounding_const: int = 4):
    total_ask_value_ = round(sum(volume for price, volume in asks_), rounding_const)
    total_bid_value_ = round(sum(volume for price, volume in bids_), rounding_const)
    return total_ask_value_, total_bid_value_, round(total_ask_value_ + total_bid_value_, rounding_const)


# Функция для создания свечного графика
@app.route("/create_candle_plot", methods=["GET"])
def create_candle_plot():
    global time_count

    tf = request.args.get("timeframe", "15m")
    print(f"{tf=}\n")
    symbol = request.args.get("symbol", "BTC/USDT")
    symbol = symbol.replace('/', '')  # in an appropriate for Binance API format
    df = fetch_candlestick_data(symbol, tf)  # symbol, tf

    fig = go.Figure()

    # Свечной график
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlestick',
        increasing_line_color='lime',
        decreasing_line_color='red',
    ))

    update_layout_xaxis = dict(
        title='Время',
        showgrid=False,
        tickformat="%H:%M",  # Формат времени на часовой основе
        rangeslider=dict(visible=False)
    )

    dates_dict = dict()
    last_timestamp = df.iloc[-1]["timestamp"]
    print(f"{last_timestamp=}")

    # использовать эти данные для масштабирования высоты полоски
    low_max = df["low"].max() - (abs(df["low"].mean() - df["low"].min()) // 2)
    high_min = df["high"].min() + (abs(df["high"].mean() - df["high"].max()) // 2)

    xaxis_range = []
    right_x_value = last_timestamp + TIMEFRAMES_REFERENCE.get(tf)[0]
    match tf:
        case "5m":
            for idx, row in df.iterrows():
                date_str, time_str, minutes, _, _, _ = retrieve_time_data(row)
                time_count += 1
                if minutes in (0, 30):
                    add_date_advanced(dates_dict, date_str, time_str, row, 18)

            dates_dict_list = list(dates_dict.values())[-2][1]
            xaxis_range = [dates_dict_list[len(dates_dict_list) - len(dates_dict_list) // 3], right_x_value]
            fig.update_xaxes(
                range=xaxis_range
            )

        case "15m":
            for idx, row in df.iterrows():
                date_str, time_str, minutes, _, _, _ = retrieve_time_data(row)
                # print(date_str, time_str, minutes)
                time_count += 1
                if minutes == 0:
                    add_date_advanced(dates_dict, date_str, time_str, row, 12)
            xaxis_range = [list(dates_dict.values())[-2][1][0], right_x_value]

            fig.update_xaxes(
                range=xaxis_range
            )

        case "30m":
            for idx, row in df.iterrows():
                date_str, time_str, minutes, _, _, _ = retrieve_time_data(row)
                time_count += 1
                if minutes in (0, 30):
                    add_date_advanced(dates_dict, date_str, time_str, row, 13)
            xaxis_range = [list(dates_dict.values())[-3][1][0], right_x_value]
            fig.update_xaxes(
                range=xaxis_range
            )

        case "1h":
            for idx, row in df.iterrows():
                date_str, time_str, _, hours, _, _ = retrieve_time_data(row)
                time_count += 1
                if hours in (0, 12):
                    add_date_advanced(dates_dict, date_str, time_str, row, 12)
            xaxis_range = [list(dates_dict.values())[-4][1][0], right_x_value]
            fig.update_xaxes(
                range=xaxis_range
            )

        case "2h":
            for idx, row in df.iterrows():
                date_str, time_str, _, hours, _, _ = retrieve_time_data(row)
                if hours == 0:
                    add_date(dates_dict, date_str, time_str, row)
            xaxis_range = [list(dates_dict.values())[-5][1][0], right_x_value]
            fig.update_xaxes(
                range=xaxis_range
            )

        case "4h":
            for idx, row in df.iterrows():
                date_str, time_str, _, _, days, _ = retrieve_time_data(row)
                time_count += 1
                if days % 2 == 0:
                    add_date_advanced(dates_dict, date_str, time_str, row, 12)
            xaxis_range = [list(dates_dict.values())[-6][1][0], right_x_value]
            fig.update_xaxes(
                range=xaxis_range
            )

    # pprint(dates_dict)
    tickvals = []
    ticktext = []
    for val in dates_dict.values():
        tickvals.extend(val[1])
        ticktext.extend(val[0])

    update_layout_xaxis["tickvals"] = tickvals
    update_layout_xaxis["ticktext"] = ticktext

    update_layout_xaxis["range"] = xaxis_range

    global asks_for_nz, bids_for_nz, total_ask_value, total_bid_value, nzVolume

    shapes = []
    asks_for_nz = get_order_book(symbol, BINANCE_LIMIT, "asks")
    bids_for_nz = get_order_book(symbol, BINANCE_LIMIT, "asks")

    total_ask_value, total_bid_value, nzVolume = update_nz_volume(asks_for_nz, bids_for_nz, NZ_VOLUME_ROUNDING_CONST)

    conn_asks = sqlite3.connect("orders_asks.db")
    cursor_asks = conn_asks.cursor()
    conn_bids = sqlite3.connect("orders_bids.db")
    cursor_bids = conn_bids.cursor()

    print(f"\nFETCH DATA INFO (START)\n")
    print(f"{symbol=} {get_latest_price(symbol)=}")
    fetch_data(
        conn_asks,
        cursor_asks,
        conn_bids,
        cursor_bids,
        symbol,
        BINANCE_LIMIT,
        round(SYMBOLS_CONSTANTS.get(symbol)[0] / get_latest_price(symbol), 4)
    )
    print(f"\nFETCH DATA INFO (END)\n")

    def create_shapes_from_orders(orders_dict: dict[float: [float, str]]):
        # y_bar_constant = get_latest_price(symbol) * 0.000052  # 5, 7, 10
        y_bar_constant = SYMBOLS_CONSTANTS.get(symbol)[1]
        for key_price in orders_dict:
            current_color = orders_dict.get(key_price)[1]
            rect = {
                "type": "rect",
                "x0": last_timestamp + TIMEFRAMES_REFERENCE.get(tf)[1],
                "y0": key_price - y_bar_constant,
                "x1": right_x_value,
                "y1": key_price + y_bar_constant,
                "fillcolor": current_color,
                "opacity": 0.9,
                "line": {
                    "width": 0
                }
            }
            shapes.append(rect)

    all_asks = get_orders_dict(cursor_asks, symbol)
    create_shapes_from_orders(all_asks)  # asks bars
    cursor_asks.close()
    conn_asks.close()

    all_bids = get_orders_dict(cursor_bids, symbol)
    create_shapes_from_orders(all_bids)  # bids bars
    cursor_bids.close()
    conn_bids.close()

    # Обновление графика с временными метками

    update_start_timestamps()
    fig.update_layout(
        plot_bgcolor='#101014',
        paper_bgcolor='#101014',
        font=dict(color="#7A7A7C"),
        xaxis=update_layout_xaxis,
        yaxis=dict(
            title='Цена',
            showgrid=True,
            gridcolor='darkgrey',
        ),
        # title='Свечной график с зонами ордеров',
        template='plotly_dark',
        height=600,
        margin=dict(t=5),
        annotations=[
            {
                'x': 0,
                'y': 1,
                "text": f"asks: {total_ask_value} bids: {total_bid_value} nzVolume: {nzVolume}",
                "showarrow": False,
                "xref": "paper",
                "yref": "paper",
                "xanchor": "left",
                "yanchor": "top",
                "font": {
                    "size": 13,
                    "color": "#7A7A7C"
                }
            }
        ],
        shapes=shapes
    )

    def orders_front_end_format(orders_dict: dict) -> list:
        return [[order_dict_key, orders_dict.get(order_dict_key)[0]] for order_dict_key in orders_dict.keys()]

    graph_json = pio.to_json(fig)
    graph_json_dict = json.loads(graph_json)

    asks_for_nz = orders_front_end_format(all_asks)
    bids_for_nz = orders_front_end_format(all_bids)

    graph_json_dict["total_ask_value"] = total_ask_value
    graph_json_dict["total_bid_value"] = total_bid_value
    graph_json_dict["asks"] = asks_for_nz
    graph_json_dict["bids"] = bids_for_nz
    graph_json_dict["nzvolume"] = nzVolume

    # print("orders_front_end_format(all_asks)")
    # pprint(graph_json_dict["asks"])
    # print()
    # print("orders_front_end_format(all_bids)")
    # pprint(graph_json_dict["bids"])

    graph_json = json.dumps(graph_json_dict)

    return jsonify(graph_json)


@app.route("/update_chart")
def get_updated_text():
    global asks_for_nz, bids_for_nz, total_ask_value, total_bid_value, nzVolume

    total_ask_value, total_bid_value, nzVolume = update_nz_volume(asks_for_nz, bids_for_nz, NZ_VOLUME_ROUNDING_CONST)

    return jsonify({
        "annotation_text": f"asks: {total_ask_value} bids: {total_bid_value} nzVolume: {nzVolume}",
        "total_ask_value": total_ask_value,
        "total_bid_value": total_bid_value,
        "asks": asks_for_nz,
        "bids": bids_for_nz,
        "nzvolume": nzVolume
    })


@app.route('/', methods=['GET', 'POST'])
def index():
    global asks_for_nz, bids_for_nz, total_ask_value, total_bid_value, nzVolume
    symbols = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    # symbols = get_binance_futures_symbols()
    selected_option_symbol = "BTC/USDT"
    print("RENDER:")
    print(f"{total_ask_value=}")
    print(f"{total_bid_value=}")
    print(f"{asks_for_nz=}")
    print(f"{bids_for_nz=}")
    print(f"{nzVolume=}")

    return render_template(
        'index.html',
        symbols=symbols,
        selected_option_symbol=selected_option_symbol,
        total_ask_value=total_ask_value,
        total_bid_value=total_bid_value,
        asks=asks_for_nz,
        bids=bids_for_nz,
        nzvolume=nzVolume
    )


if __name__ == '__main__':
    app.run(
        debug=True,
        port=8080
    )
