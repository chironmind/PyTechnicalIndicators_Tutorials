import psycopg2
import requests
import json
import datetime
from PyTechnicalIndicators.Bulk import moving_averages
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
    open = []
    high = []
    low = []
    close = []
    volume = []
    close_time = []
    number_of_trades = []
    for i in out:
        open_time.append(datetime.datetime.fromtimestamp(i[0] / 1e3))
        open.append(float(i[1]))
        high.append(float(i[2]))
        low.append(float(i[3]))
        close.append(float(i[4]))
        volume.append(float(i[5]))
        # only use it for non daily data
        #close_time.append(datetime.datetime.fromtimestamp(i[6] / 1e3))
        number_of_trades.append(float(i[8]))

    # Only need time for the non daily data
    d = {
        # 'Date': open_time,
        'Open': open,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
        #'Close Time': close_time,
        'Number of Trades': number_of_trades
    }

    data = pandas.DataFrame(data=d, index=open_time)
    data.index.name = 'Date'

    data['Typical Price'] = (data['High'] + data['Low'] + data['Close']) / 3
    data['Crypto_Name'] = p[1]
    data['Crypto_Short_Name'] = p[2]

    # TODO: Figure what to use instead of close as there is no close in crypto markets
    # TODO: find a much better way to do this
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

    # for i in range(len(data)):
    #     query = f'INSERT INTO indicators_dailyprices VALUES ({data.index[i]}, {data.iloc[i]["Open"]},' \
    #             f' {data.iloc[i]["Close"]}, {data.iloc[i]["High"]}, {data.iloc[i]["Low"]}, {data.iloc[i]["Typical Price"]},' \
    #             f' {data.iloc[i]["Mean"]}, {data.iloc[i]["Variance"]}, {data.iloc[i]["Standard Deviation"]}, {data.iloc[i]["Log"]},' \
    #             f' {data.iloc[i]["Log Difference"]}, {data.iloc[i]["50 Period MA"]}, {data.iloc[i]["200 Period MA"]}, {data.iloc[i]["20 Period EMA"]},' \
    #             f' {data.iloc[i]["50 Period EMA"]}, {data.iloc[i]["200 Period EMA"]}, {data.iloc[i]["MACD"]}, {data.iloc[i]["Signal Line"]},' \
    #             f' {data.iloc[i]["MACD Histogram"]}, {data.iloc[i]["RSI"]}, {data.iloc[i]["ADX"]}, {data.iloc[i]["+ve DX"]},' \
    #             f' {data.iloc[i]["-ve DX"]}, {data.iloc[i]["Upper Band"]}, {data.iloc[i]["Lower Band"]}, {data.iloc[i]["Stochastic Oscillator"]},' \
    #             f' {data.iloc[i]["Senkou Span A"]}, {data.iloc[i]["Senkou Span B"]}, {data.iloc[i]["Volume"]}, {p[1]}, {p[2]})'
    #     print(query)

    #Do db insert here
    #
    conn = psycopg2.connect(user='', password='', host='127.0.0.1', port='5432', database='')
    cursor = conn.cursor()

    try:
        query = 'select max("id") from '
        cursor.execute(query)
        conn.commit()
        max_id = cursor.fetchone()
        curr_id = 0
        if max_id[0] is not None:
            curr_id = max_id[0] + 1

        for i in range(len(data)):
            query = f'INSERT INTO indicators_dailyprices (id, "Date", "Open", "Close", "High", "Low", "Typical_Price", "Mean", "Variance", "Standard_Deviation",' \
                    f' "Log", "Log_Difference", "Moving_Avg_50", "Moving_Avg_200", "Exp_Moving_Avg_20", "Exp_Moving_Avg_50", "Exp_Moving_Avg_200", ' \
                    f'"MACD", "Signal_Line", "MACD_Histogram", "RSI", "Average_Direction_Movement", "Positive_Direction_Movement", "Negative_Direction_Movement", ' \
                    f'"Upper_B_Band", "Lower_B_Band", "Stochastic_Oscillator", "Senkou_Span_A", "Senkou_Span_B", "Volume", "Crypto_Name", ' \
                    f'"Crypto_Tick_Name") VALUES ({curr_id+i},\'{data.index[i]}\', {data.iloc[i]["Open"]},' \
                    f' {data.iloc[i]["Close"]}, {data.iloc[i]["High"]}, {data.iloc[i]["Low"]}, {data.iloc[i]["Typical Price"]},' \
                    f' {data.iloc[i]["Mean"]}, {data.iloc[i]["Variance"]}, {data.iloc[i]["Standard Deviation"]}, {data.iloc[i]["Log"]},' \
                    f' {data.iloc[i]["Log Difference"]}, {data.iloc[i]["50 Period MA"]}, {data.iloc[i]["200 Period MA"]}, {data.iloc[i]["20 Period EMA"]},' \
                    f' {data.iloc[i]["50 Period EMA"]}, {data.iloc[i]["200 Period EMA"]}, {data.iloc[i]["MACD"]}, {data.iloc[i]["Signal Line"]},' \
                    f' {data.iloc[i]["MACD Histogram"]}, {data.iloc[i]["RSI"]}, {data.iloc[i]["ADX"]}, {data.iloc[i]["+ve DX"]},' \
                    f' {data.iloc[i]["-ve DX"]}, {data.iloc[i]["Upper Band"]}, {data.iloc[i]["Lower Band"]}, {data.iloc[i]["Stochastic Oscillator"]},' \
                    f' {data.iloc[i]["Senkou Span A"]}, {data.iloc[i]["Senkou Span B"]}, {data.iloc[i]["Volume"]}, ' \
                    f' \'{data.iloc[i]["Crypto_Name"]}\', \'{data.iloc[i]["Crypto_Short_Name"]}\')'
            cursor.execute(query)
        conn.commit()
        count = cursor.rowcount
        print(f'{count} rows updated')

    except (Exception, psycopg2.Error) as error:
        if(conn):
            print(f'Failed due to {error}')

    #'#finally:
        #closing database connection.
    if(conn):
        cursor.close()
        conn.close()
        print("PostgreSQL connection is closed")
