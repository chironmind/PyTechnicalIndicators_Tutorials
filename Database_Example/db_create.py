import psycopg2
import requests
import json
import datetime
from PyTechnicalIndicators.Bulk import basic_indicators, moving_averages, strength_indicators, candle_indicators
import pandas


url = 'https://api.binance.com/api/v3/klines'

params = [
    ({'symbol': 'BTCUSDT', 'interval': '1d', 'limit': 1000}, 'Bitcoin', 'BTC'),
    ({'symbol': 'XRPUSDT', 'interval': '1d', 'limit': 1000}, 'Ripple', 'XRP'),
    ({'symbol': 'BCHUSDT', 'interval': '1d', 'limit': 1000}, 'Bitcoin Cash', 'BCH'),
    ({'symbol': 'BNBUSDT', 'interval': '1d', 'limit': 1000}, 'Binance Coin', 'BNB'),
    ({'symbol': 'ADAUSDT', 'interval': '1d', 'limit': 1000}, 'Cardano', 'ADA'),
    ({'symbol': 'ETHUSDT', 'interval': '1d', 'limit': 1000}, 'Ethereum', 'ETH'),
    ({'symbol': 'LINKUSDT', 'interval': '1d', 'limit': 1000}, 'ChainLink', 'LINK'),
    ({'symbol': 'LTCUSDT', 'interval': '1d', 'limit': 1000}, 'Litecoin', 'LTC'),
]

# TODO: Do it one way with Pandas and another just with lists

for p in params:
    r = requests.get(url, params=p[0])
    out = json.loads(r.text)

    open_time = []
    open_price = []
    high = []
    low = []
    close = []
    volume = []
    close_time = []
    number_of_trades = []
    for i in out:
        open_time.append(datetime.datetime.fromtimestamp(i[0] / 1e3))
        open_price.append(float(i[1]))
        high.append(float(i[2]))
        low.append(float(i[3]))
        close.append(float(i[4]))
        volume.append(float(i[5]))
        number_of_trades.append(float(i[8]))

    d = {
        'Date': open_time,
        'Open': open_price,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
        'Number of Trades': number_of_trades
    }

    data = pandas.DataFrame(data=d)
    data.index.name = 'Date'
    data['Typical Price'] = (data['High'] + data['Low'] + data['Close']) / 3
    data['Crypto Name'] = p[1]
    data['Crypto Short Name'] = p[2]


    # basic indicators
    data['Log'] = basic_indicators.log(data['Typical Price'].values)
    data['Log Diff'] = basic_indicators.log_diff(data['Typical Price'].values)
    data['Median 10'] = basic_indicators.median(data['Typical Price'].values, 10, True)
    data['Mean 10'] = basic_indicators.mean(data['Typical Price'].values, 10, True)
    data['Std Dev 10'] = basic_indicators.stddev(data['Typical Price'].values, 10, True)
    data['Var 10'] = basic_indicators.variance(data['Typical Price'].values, 10, True)
    # moving averages
    data['MA 10'] = moving_averages.moving_average(data['Close'].values, 10, True)
    data['SMA 10'] = moving_averages.smoothed_moving_average(data['Close'].values, 10, True)
    data['EMA 10'] = moving_averages.exponential_moving_average(data['Close'].values, 10, True)
    data['PMA 10'] = moving_averages.personalised_moving_average(data['Close'].values, 10, 1.5, 0.5, True)
    data['MACD'] = moving_averages.moving_average_convergence_divergence(data['Close'].values, True)
    data['Signal Line'] = moving_averages.signal_line(data['MACD'].values, True)
    data['Personalised MACD'] = moving_averages.personalised_macd(data['Close'].values, 10, 20, 'ema', True)
    data['Personalised Signal'] = moving_averages.personalised_signal_line(data['Personalised MACD'].values, 10, 'ema', True)

    # Strength Indicators
    # Exception: There needs to be prices to be able to do an smoothed moving average
    data['RSI'] = strength_indicators.relative_strength_index(data['Typical Price'].values, True)
    # Exception: There needs to be prices to be able to do an expo moving average
    data['Personalised RSI'] = strength_indicators.personalised_rsi(data['Typical Price'].values, 10, 'ema', True)
    data['Stochastic Oscillator'] = strength_indicators.stochastic_oscillator(data['Typical Price'].values, True)
    data['Personalised SO'] = strength_indicators.personalised_stochastic_oscillator(data['Typical Price'].values, 10, True)

    # Candle Indicators
    bollinger_bands = candle_indicators.bollinger_bands(data['Typical Price'].values, True)
    data['Upper Bollinger Band'] = bollinger_bands[0]
    data['Lower Bollinger Band'] = bollinger_bands[1]
    pers_bollinger_bands = candle_indicators.personalised_bollinger_bands(data['Typical Price'].values, 10, 'ema', 2.5, True)
    data['Upper Personalised Bollinger Bands'] = pers_bollinger_bands[0]
    data['Lower Personalised Bollinger Bands'] = pers_bollinger_bands[1]
    ichimoku_cloud = candle_indicators.ichimoku_cloud(data['High'].values, data['Low'].values, True)
    data['Senkou Span A'] = ichimoku_cloud[0]
    data['Senkou Span B'] = ichimoku_cloud[1]
    personalised_ichimoku_cloud = candle_indicators.personalised_ichimoku_cloud(data['High'].values, data['Low'].values, 10, 20, 40, True)
    data['Senkou Span A'] = personalised_ichimoku_cloud[0]
    data['Senkou Span B'] = personalised_ichimoku_cloud[1]

    conn = psycopg2.connect(user='your username', password='your password', host='127.0.0.1', port='5432', database='your db')
    cursor = conn.cursor()

    try:
        columns = ','.join([i for i in data.columns.tolist()])
        for i, row in data.iterrows():
            query = f'INSERT INTO your_table_name ({columns}) values ({",".join([str(j) for j in row.values])})'
            print(query)
            cursor.execute(query)
        conn.commit()
        count = cursor.rowcount
        print(f'{count} rows updated')

    except (Exception, psycopg2.Error) as error:
        print(f'Failed due to {error}')

    if conn:
        cursor.close()
        conn.close()
        print("PostgreSQL connection is closed")
