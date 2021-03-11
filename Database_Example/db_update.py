import psycopg2
import datetime
import requests
import json
import pandas
import time
import market_indicators as mi

# TODO: Uncomment this when the coingeko api is fixed
url = 'https://api.binance.com/api/v3/klines'

current_date = datetime.datetime.now().date()

conn = psycopg2.connect(user='', password='', host='127.0.0.1', port='5432', database='')
cursor = conn.cursor()

query = 'select distinct "Crypto_Name" from indicators_dailyprices;'
try:
    cursor.execute(query)
    conn.commit()
    cryptos = cursor.fetchall()
except (Exception, psycopg2.Error) as error:
    if(conn):
        print(f'Failed to get names due to {error}')

crypto_data = {}

for c in cryptos:
    query = f'select max("Date") from indicators_dailyprices where "Crypto_Name" = \'{c[0]}\';'
    try:
        cursor.execute(query)
        conn.commit()
        date = cursor.fetchone()
        next_date = date[0] + datetime.timedelta(days=1)
        if next_date != current_date:
            crypto_data[c[0]] = {}
            crypto_data[c[0]]['Date'] = next_date

    except psycopg2.Error as error:
        if (conn):
            print(f'Failed to get date due to {error.pgcode}: {error.pgerror}')



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
    print(r.headers)
    crypto_data[d]['Data'] = json.loads(r.text)

actual_data = {}

for c in crypto_data:
    min_date = crypto_data[c]['Date']
    actual_data[c] = {}
    c_id = 0
    d = 0
    o = 0
    h = 0
    lo = 0
    cl = 0
    v = 0

    for i in crypto_data[c]['Data']:
        timestamp = datetime.datetime.fromtimestamp(i[0] / 1e3)
        print(timestamp)
        print(i)
        if min_date <= timestamp.date() < current_date:
            if c_id == 0:
                d = timestamp.date()
                o = float(i[1])
                lo = float(i[3])

            if timestamp.date() != d:
                actual_data[c][c_id] = {}
                actual_data[c][c_id]['Date'] = d
                actual_data[c][c_id]['Open'] = o
                actual_data[c][c_id]['High'] = h
                actual_data[c][c_id]['Low'] = lo
                actual_data[c][c_id]['Close'] = cl
                actual_data[c][c_id]['Volume'] = v

                c_id += 1
                d = timestamp.date()
                o = float(i[1])
                h = float(i[2])
                lo = float(i[3])

            if float(i[2]) > h:
                h = float(i[2])

            if float(i[3]) < lo:
                lo = float(i[3])

            cl = float(i[4])
            v = float(i[5])

    actual_data[c][c_id] = {}
    actual_data[c][c_id]['Date'] = d
    actual_data[c][c_id]['Open'] = o
    actual_data[c][c_id]['High'] = h
    actual_data[c][c_id]['Low'] = lo
    actual_data[c][c_id]['Close'] = cl
    actual_data[c][c_id]['Volume'] = v

# TODO: Get all the previous data, put into a df and calc this data: either do it as a one off or just recalc it all and only insert last row?

#Loop through actual data and do it all one at a time

for i in actual_data:
    previous_data = []

    earliest_date = 0
    retrieved_date = []
    retrieved_open = []
    retrieved_high = []
    retrieved_low = []
    retrieved_close = []
    retrieved_volume = []
    for j in actual_data[i]:
        retrieved_date.append(actual_data[i][j]['Date'])
        retrieved_open.append(actual_data[i][j]['Open'])
        retrieved_high.append(actual_data[i][j]['High'])
        retrieved_low.append(actual_data[i][j]['Low'])
        retrieved_close.append(actual_data[i][j]['Close'])
        retrieved_volume.append(actual_data[i][j]['Volume'])

        if earliest_date == 0:
            earliest_date = actual_data[i][j]['Date']

        if earliest_date > actual_data[i][j]['Date']:
            earliest_date = actual_data[i][j]

    min_date = earliest_date - datetime.timedelta(days=200)

    query = f'select "Date", "Open", "High", "Low", "Close", "Volume", "Crypto_Tick_Name" ' \
            f'from indicators_dailyprices ' \
            f'where "Crypto_Name" = \'{i}\' ' \
            f'and "Date" >= \'{min_date}\';'
    try:
        cursor.execute(query)
        conn.commit()
        previous_data = cursor.fetchall()
    except (Exception, psycopg2.Error) as error:
        if(conn):
            print(f'Failed to get previous data due to {error}')

    if not previous_data:
        print('No data retrieved')
        if (conn):
            cursor.close()
            conn.close()
            print("PostgreSQL connection is closed")
        exit()

    date = []
    open = []
    high = []
    low = []
    close = []
    volume = []

    for j in previous_data:
        date.append(j[0])
        open.append(j[1])
        high.append(j[2])
        low.append(j[3])
        close.append(j[4])
        volume.append(j[5])

    # Add what was just retrieved
    for j in range(len(retrieved_date)):
        date.append(retrieved_date[j])
        open.append(retrieved_open[j])
        high.append(retrieved_high[j])
        low.append(retrieved_low[j])
        close.append(retrieved_close[j])
        volume.append(retrieved_volume[j])

    d = {
        'Open': open,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
    }

    data = pandas.DataFrame(data=d, index=date)
    data.index.name = 'Date'

    data['Typical Price'] = (data['High'] + data['Low'] + data['Close']) / 3
    data['Crypto_Name'] = i
    data['Crypto_Short_Name'] = previous_data[0][-1]

    mean = mi.mean(data['Close'], 14)
    var = mi.variance(data['Close'], 14)
    stddev = mi.stddev(data['Close'], 14)
    ma50 = mi.MovingAverage(data['Close'], 50)
    ma200 = mi.MovingAverage(data['Close'], 200)
    ema20 = mi.ExponentialMovingAverage(data['Close'], 20)
    ema50 = mi.ExponentialMovingAverage(data['Close'], 50)
    ema200 = mi.ExponentialMovingAverage(data['Close'], 200)
    macd = mi.MovingAverageConvergenceDivergence(data['Close'])
    signal = mi.SignalLine(macd)
    rsi = mi.RelativeStrengthIndicator(data['Close'])
    dx = mi.AverageDirectionalIndex(data['High'], data['Low'], data['Close'])
    bands = mi.BolingerBands(data['Typical Price'])
    stochastic_oscillator = mi.StochasticOscillator(data['Close'])
    ichimoku_cloud = mi.IchimokuCloud(data['High'], data['Low'])

    adx = dx[0]
    pdx = dx[1]
    ndx = dx[2]

    upper_band = bands[0]
    lower_band = bands[1]

    senkou_span_a = ichimoku_cloud[0]
    senkou_span_b = ichimoku_cloud[1]

    data_len = len(data)
    mean_start = data_len - len(mean)
    var_start = data_len - len(var)
    stddev_start = data_len - len(stddev)
    ma50_start = data_len - len(ma50)
    ma200_start = data_len - len(ma200)
    ema20_start = data_len - len(ema20)
    ema50_start = data_len - len(ema50)
    ema200_start = data_len - len(ema200)
    macd_start = data_len - len(macd)
    signal_start = data_len - len(signal)
    rsi_start = data_len - len(rsi)
    # Assume that length adx = pdx = ndx
    dx_start = data_len - len(adx)
    # Assume len upper = lower band
    band_start = data_len - len(upper_band)
    so_start = data_len - len(stochastic_oscillator)
    # assumer len span a = span b
    # +26 as the cloud is plotted 26 periods in the future
    senkou_start = data_len - len(senkou_span_a) + 26

    mean_data = []
    var_data = []
    stddev_data = []
    ma50_data = []
    ma200_data = []
    ema20_data = []
    ema50_data = []
    ema200_data = []
    macd_data = []
    signal_data = []
    rsi_data = []
    adx_data = []
    pdx_data = []
    ndx_data = []
    upper_band_data = []
    lower_band_data = []
    stochastic_oscillator_data = []
    senkou_span_a_data = []
    senkou_span_b_data = []

    for i in range(data_len):

        if i < mean_start:
            mean_data.append(0)
        else:
            mean_data.append(mean[i-mean_start])
        if i < var_start:
            var_data.append(0)
        else:
            var_data.append(var[i-var_start])
        if i < stddev_start:
            stddev_data.append(0)
        else:
            stddev_data.append(stddev[i-stddev_start])

        if i < ma50_start:
            ma50_data.append(0)
        else:
            ma50_data.append(ma50[i-ma50_start])

        if i < ma200_start:
            ma200_data.append(0)
        else:
            ma200_data.append(ma200[i-ma200_start])

        if i < ema20_start:
            ema20_data.append(0)
        else:
            ema20_data.append(ema20[i-ema20_start])

        if i < ema50_start:
            ema50_data.append(0)
        else:
            ema50_data.append(ema50[i-ema50_start])

        if i < ema200_start:
            ema200_data.append(0)
        else:
            ema200_data.append(ema200[i-ema200_start])

        if i < macd_start:
            macd_data.append(0)
        else:
            macd_data.append(macd[i-macd_start])

        if i < signal_start:
            signal_data.append(0)
        else:
            signal_data.append(signal[i-signal_start])

        if i < rsi_start:
            rsi_data.append(0)
        else:
            rsi_data.append(rsi[i-rsi_start])

        if i < dx_start:
            adx_data.append(0)
            pdx_data.append(0)
            ndx_data.append(0)
        else:
            adx_data.append(adx[i - dx_start])
            pdx_data.append(pdx[i - dx_start])
            ndx_data.append(ndx[i - dx_start])

        if i < band_start:
            upper_band_data.append(0)
            lower_band_data.append(0)
        else:
            upper_band_data.append(upper_band[i-band_start])
            lower_band_data.append(lower_band[i-band_start])

        if i < so_start:
            stochastic_oscillator_data.append(0)
        else:
            stochastic_oscillator_data.append(stochastic_oscillator[i-so_start])

        if i < senkou_start:
            senkou_span_a_data.append(0)
            senkou_span_b_data.append(0)
        else:
            senkou_span_a_data.append(senkou_span_a[i-senkou_start])
            senkou_span_b_data.append(senkou_span_b[i-senkou_start])

    data['Mean'] = mean_data
    data['Variance'] = var_data
    data['Standard Deviation'] = stddev_data
    data['Log'] = mi.log(data['Close'])
    data['Log Difference'] = mi.logdiff(data['Close'])
    data['50 Period MA'] = ma50_data
    data['200 Period MA'] = ma200_data
    data['20 Period EMA'] = ema20_data
    data['50 Period EMA'] = ema50_data
    data['200 Period EMA'] = ema200_data
    data['MACD'] = macd_data
    data['Signal Line'] = signal_data
    data['MACD Histogram'] = data['MACD'] - data['Signal Line']
    data['RSI'] = rsi_data
    data['ADX'] = adx_data
    data['+ve DX'] = pdx_data
    data['-ve DX'] = ndx_data
    data['Upper Band'] = upper_band_data
    data['Lower Band'] = lower_band_data
    data['Stochastic Oscillator'] = stochastic_oscillator_data
    data['Senkou Span A'] = senkou_span_a_data
    data['Senkou Span B'] = senkou_span_b_data

    t = 0 - len(retrieved_date)
    needed_data = data[t:]

    for n in range(len(needed_data)):
        # query = f'INSERT INTO indicators_dailyprices VALUES ({needed_data.index[n]}, {needed_data.iloc[n]["Open"]},' \
        #         f' {needed_data.iloc[n]["Close"]}, {needed_data.iloc[n]["High"]}, {needed_data.iloc[n]["Low"]}, {needed_data.iloc[n]["Typical Price"]},' \
        #         f' {needed_data.iloc[n]["Mean"]}, {needed_data.iloc[n]["Variance"]}, {needed_data.iloc[n]["Standard Deviation"]}, {needed_data.iloc[n]["Log"]},' \
        #         f' {needed_data.iloc[n]["Log Difference"]}, {needed_data.iloc[n]["50 Period MA"]}, {needed_data.iloc[n]["200 Period MA"]}, {needed_data.iloc[n]["20 Period EMA"]},' \
        #         f' {needed_data.iloc[n]["50 Period EMA"]}, {needed_data.iloc[n]["200 Period EMA"]}, {needed_data.iloc[n]["MACD"]}, {needed_data.iloc[n]["Signal Line"]},' \
        #         f' {needed_data.iloc[n]["MACD Histogram"]}, {needed_data.iloc[n]["RSI"]}, {needed_data.iloc[n]["ADX"]}, {needed_data.iloc[n]["+ve DX"]},' \
        #         f' {needed_data.iloc[n]["-ve DX"]}, {needed_data.iloc[n]["Upper Band"]}, {needed_data.iloc[n]["Lower Band"]}, {needed_data.iloc[n]["Stochastic Oscillator"]},' \
        #         f' {needed_data.iloc[n]["Senkou Span A"]}, {needed_data.iloc[n]["Senkou Span B"]}, {needed_data.iloc[n]["Volume"]}, ' \
        #         f' {needed_data.iloc[n]["Crypto_Name"]}, {needed_data.iloc[n]["Crypto_Short_Name"]})'
        # print(query)

        try:
            query = 'select max("id") from indicators_dailyprices'
            cursor.execute(query)
            conn.commit()
            max_id = cursor.fetchone()
            if max_id[0] is None:
                print('Error getting ID')
                exit()
            curr_id = max_id[0] + 1

            query = f'INSERT INTO indicators_dailyprices (id, "Date", "Open", "Close", "High", "Low", "Typical_Price", "Mean", "Variance", "Standard_Deviation",' \
                    f' "Log", "Log_Difference", "Moving_Avg_50", "Moving_Avg_200", "Exp_Moving_Avg_20", "Exp_Moving_Avg_50", "Exp_Moving_Avg_200", ' \
                    f'"MACD", "Signal_Line", "MACD_Histogram", "RSI", "Average_Direction_Movement", "Positive_Direction_Movement", "Negative_Direction_Movement", ' \
                    f'"Upper_B_Band", "Lower_B_Band", "Stochastic_Oscillator", "Senkou_Span_A", "Senkou_Span_B", "Volume", "Crypto_Name", ' \
                    f'"Crypto_Tick_Name") VALUES ({curr_id},\'{needed_data.index[n]}\', {needed_data.iloc[n]["Open"]},' \
                    f' {needed_data.iloc[n]["Close"]}, {needed_data.iloc[n]["High"]}, {needed_data.iloc[n]["Low"]}, {needed_data.iloc[n]["Typical Price"]},' \
                    f' {needed_data.iloc[n]["Mean"]}, {needed_data.iloc[n]["Variance"]}, {needed_data.iloc[n]["Standard Deviation"]}, {needed_data.iloc[n]["Log"]},' \
                    f' {needed_data.iloc[n]["Log Difference"]}, {needed_data.iloc[n]["50 Period MA"]}, {needed_data.iloc[n]["200 Period MA"]}, {needed_data.iloc[n]["20 Period EMA"]},' \
                    f' {needed_data.iloc[n]["50 Period EMA"]}, {needed_data.iloc[n]["200 Period EMA"]}, {needed_data.iloc[n]["MACD"]}, {needed_data.iloc[n]["Signal Line"]},' \
                    f' {needed_data.iloc[n]["MACD Histogram"]}, {needed_data.iloc[n]["RSI"]}, {needed_data.iloc[n]["ADX"]}, {needed_data.iloc[n]["+ve DX"]},' \
                    f' {needed_data.iloc[n]["-ve DX"]}, {needed_data.iloc[n]["Upper Band"]}, {needed_data.iloc[n]["Lower Band"]}, {needed_data.iloc[n]["Stochastic Oscillator"]},' \
                    f' {needed_data.iloc[n]["Senkou Span A"]}, {needed_data.iloc[n]["Senkou Span B"]}, {needed_data.iloc[n]["Volume"]}, ' \
                    f' \'{needed_data.iloc[n]["Crypto_Name"]}\', \'{needed_data.iloc[n]["Crypto_Short_Name"]}\')'
            cursor.execute(query)
            conn.commit()
            count = cursor.rowcount
            print(f'{count} rows updated')

        except (Exception, psycopg2.Error) as error:
            if (conn):
                print(f'Failed due to {error}')

if(conn):
    cursor.close()
    conn.close()
    print("PostgreSQL connection is closed")
