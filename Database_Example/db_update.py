import psycopg2
import datetime
import requests
import json
import pandas
import math
import statistics
from PyTechnicalIndicators.Single import moving_averages, strength_indicators, candle_indicators

url = 'https://api.binance.com/api/v3/klines'

current_date = datetime.datetime.now().date()

conn = psycopg2.connect(user='user', password='password', host='127.0.0.1', port='5432', database='your_db')
cursor = conn.cursor()

query = 'select distinct "Crypto_Name" from your_table_name;'
try:
    cursor.execute(query)
    conn.commit()
    cryptos = cursor.fetchall()
except (Exception, psycopg2.Error) as error:
    if(conn):
        print(f'Failed to get names due to {error}')
        exit()

crypto_data = {}

for c in cryptos:
    query = f'select max("Date") from your_table_name where "Crypto_Name" = \'{c[0]}\';'
    try:
        cursor.execute(query)
        conn.commit()
        date = cursor.fetchone()[0]
        next_date = date + datetime.timedelta(days=1)
        if next_date != current_date:
            crypto_data[c[0]] = {}
            crypto_data[c[0]]['Date'] = date

    except psycopg2.Error as error:
        if (conn):
            print(f'Failed to get date due to {error.pgcode}: {error.pgerror}')
            exit()

if crypto_data == {}:
    print('No data to update, exiting...')
    exit()

crypto_name_dict = {
    'Bitcoin': 'BTCUSDT',
    'Ripple': 'XRPUSDT',
    'Bitcoin Cash': 'BCHUSDT',
    'Binance Coin': 'BNBUSDT',
    'Cardano': 'ADAUSDT',
    'Ethereum': 'ETHUSDT',
    'ChainLink': 'LINKUSDT',
    'Litecoin': 'LTCUSDT',
}

for d in crypto_data:
    # Binance doesn't like the python timestamp conversion of date so we'll need to count the number of missed days and
    # add 1 to include today which will then be excluded in the loop that populates actual_data
    day_diff = current_date - crypto_data[d]['Date']
    binance_data = {'symbol': crypto_name_dict[d], 'interval': '1d', 'limit': day_diff.days + 1}
    r = requests.get(url, params=binance_data)
    crypto_data[d]['Data'] = json.loads(r.text)

actual_data = {}

for c in crypto_data:
    # We already have current date we want the next one
    min_date = crypto_data[c]['Date'] + datetime.timedelta(days=1)
    actual_data[c] = {}
    open_time = 0
    open_price = 0
    high = 0
    low = 0
    close = 0
    volume = 0
    close_time = 0
    number_of_trades = 0

    actual_data[c] = []
    for i in crypto_data[c]['Data']:
        timestamp = datetime.datetime.fromtimestamp(i[0] / 1e3).date()
        if min_date <= timestamp < current_date:
            d = {
                'Date': timestamp,
                'Open': float(i[1]),
                'High': float(i[2]),
                'Low': float(i[3]),
                'Close': float(i[4]),
                'Volume': float(i[5]),
                'Number of Trades': float(i[8])
            }
            actual_data[c].append(d)

for i in actual_data:

    previous_data = []

    earliest_date = 0
    retrieved_date = []
    retrieved_open = []
    retrieved_high = []
    retrieved_low = []
    retrieved_close = []
    retrieved_volume = []
    retrieved_no_of_trades = []

    for j in actual_data[i]:
        retrieved_date.append(j['Date'])
        retrieved_open.append(j['Open'])
        retrieved_high.append(j['High'])
        retrieved_low.append(j['Low'])
        retrieved_close.append(j['Close'])
        retrieved_volume.append(j['Volume'])
        retrieved_no_of_trades.append(j['Number of Trades'])

        if earliest_date == 0:
            earliest_date = j['Date']

        if earliest_date > j['Date']:
            earliest_date = actual_data[i][j]

    min_date = (earliest_date - datetime.timedelta(days=365))

    column_name_query = 'select column_name from information_schema.columns where table_name = \'your_table_name\''

    try:
        cursor.execute(column_name_query)
        conn.commit()
        fetched_column_names = cursor.fetchall()
    except (Exception, psycopg2.Error) as error:
        if(conn):
            print(f'Failed to get previous data due to {error}')
            exit()
    if not fetched_column_names:
        print('No columns retrieved')
        if (conn):
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")
        exit()

    column_names = tuple([j[0] for j in fetched_column_names])

    query = f'select * ' \
            f'from your_table_name ' \
            f'where "Crypto_Name" = \'{i}\' ' \
            f'and "Date" >= \'{min_date}\';'
    try:
        cursor.execute(query)
        conn.commit()
        previous_data = cursor.fetchall()
    except (Exception, psycopg2.Error) as error:
        if(conn):
            print(f'Failed to get previous data due to {error}')
            exit()
    if not previous_data:
        print('No data retrieved')
        if (conn):
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")
        exit()

    data = pandas.DataFrame(data=previous_data, columns=column_names)
    data.index.name = 'Date'

    data_to_insert = pandas.DataFrame(columns=column_names)

    for j in range(len(retrieved_date)):
        new_row = {
            'Date': f"'{retrieved_date[j]}'",
            'Open': retrieved_open[j],
            'High': retrieved_high[j],
            'Low': retrieved_low[j],
            'Close': retrieved_close[j],
            'Volume': retrieved_volume[j],
            'Typical_Price': (retrieved_high[j] + retrieved_low[j] + retrieved_close[j]) / 3,
            'Crypto_Name': f"'{i}'",
            'Crypto_Tick_Name': f"'{data['Crypto_Tick_Name'][0]}'",
            'Number_of_Trades': retrieved_no_of_trades[j]
        }

        typical_prices = list(data['Typical_Price'][-29:].values)
        typical_prices.append(new_row['Typical_Price'])
        close_prices = list(data['Close'].values)
        close_prices.append(new_row['Close'])
        low_prices = list(data['Low'][-51:].values)
        low_prices.append(new_row['Low'])
        high_prices = list(data['High'][-51:].values)
        high_prices.append(new_row['High'])

        # basic indicators
        new_row['Log'] = math.log(new_row['Typical_Price'])
        new_row['Log_Difference'] = math.log(typical_prices[-2]) - new_row['Log']
        new_row['Median'] = statistics.median(typical_prices[-7:])
        new_row['Mean'] = statistics.mean(typical_prices[-7:])
        new_row['Standard_Deviation'] = statistics.stdev(typical_prices[-7:])
        new_row['Variance'] = statistics.variance(typical_prices[-7:])
        # moving averages
        new_row['MA_7'] = moving_averages.moving_average(close_prices[-7:])
        new_row['MA_14'] = moving_averages.moving_average(close_prices[-14:])
        new_row['MA_30'] = moving_averages.moving_average(close_prices[-30:])
        new_row['MA_90'] = moving_averages.moving_average(close_prices[-90:])
        new_row['MA_365'] = moving_averages.moving_average(close_prices[-365:])
        new_row['SMA_7'] = moving_averages.smoothed_moving_average(close_prices[-7:])
        new_row['SMA_14'] = moving_averages.smoothed_moving_average(close_prices[-14:])
        new_row['SMA_30'] = moving_averages.smoothed_moving_average(close_prices[-30:])
        new_row['SMA_90'] = moving_averages.smoothed_moving_average(close_prices[-90:])
        new_row['SMA_365'] = moving_averages.smoothed_moving_average(close_prices[-365:])
        new_row['EMA_7'] = moving_averages.exponential_moving_average(close_prices[-7:])
        new_row['EMA_14'] = moving_averages.exponential_moving_average(close_prices[-14:])
        new_row['EMA_30'] = moving_averages.exponential_moving_average(close_prices[-30:])
        new_row['EMA_90'] = moving_averages.exponential_moving_average(close_prices[-90:])
        new_row['EMA_365'] = moving_averages.exponential_moving_average(close_prices[-365:])
        #new_row['MACD'] = moving_averages.moving_average_convergence_divergence(close_prices[-26:], True)
        new_row['MACD'] = moving_averages.moving_average_divergence_convergence(close_prices[-26:])
        signal = list(data['MACD'][-8:])
        signal.append(new_row['MACD'])
        new_row['Signal_Line'] = moving_averages.signal_line(signal)
        new_row['MACD_Histogram'] = new_row['MACD'] - new_row['Signal_Line']
        new_row['Personalised_MACD'] = moving_averages.personalised_macd(typical_prices[-30:], 14, 30, 'ema')
        pers_signal = list(data['Personalised_MACD'][-6:])
        pers_signal.append(new_row['Personalised_MACD'])
        new_row['Personalised_Signal_Line'] = moving_averages.personalised_signal_line(pers_signal, 'ema')
        new_row['Personalised_MACD_Histogram'] = new_row['Personalised_MACD'] - new_row['Personalised_Signal_Line']
        # Strength Indicators
        new_row['RSI'] = strength_indicators.relative_strength_index(typical_prices[-14:])
        new_row['Stochastic_Oscillator'] = strength_indicators.stochastic_oscillator(typical_prices[-14:])
        # Candle Indicators
        bollinger_bands = candle_indicators.bollinger_bands(typical_prices[-20:])
        new_row['Upper_Bollinger_Band'] = bollinger_bands[0]
        new_row['Lower_Bollinger_Band'] = bollinger_bands[1]
        ichimoku_cloud = candle_indicators.ichimoku_cloud(high_prices[-52:], low_prices[-52:])
        new_row['Senkou_Span_A'] = ichimoku_cloud[0]
        new_row['Senkou_Span_B'] = ichimoku_cloud[1]

        data_to_insert = data_to_insert.append(new_row, ignore_index=True)

    data_to_insert = data_to_insert.drop(columns=['id'])
    columns = ','.join(['"' + i + '"' for i in data_to_insert.columns.tolist()])
    try:
        for i, row in data_to_insert.iterrows():
            values = ",".join([str(j) for j in row.values])
            query = f'INSERT INTO your_table_name ({columns}) values ({values})'
            print(query)
            cursor.execute(query)
        conn.commit()
        count = cursor.rowcount
        print(f'{count} rows updated')

    except (Exception, psycopg2.Error) as error:
        print(f'Failed due to {error}')

if(conn):
    cursor.close()
    conn.close()
    print("PostgreSQL connection is closed")
