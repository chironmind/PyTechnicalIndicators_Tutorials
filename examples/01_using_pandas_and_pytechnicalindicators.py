import pandas as pd
from pytechnicalindicators import moving_average as ma
from pytechnicalindicators import candle_indicators as ci
from pytechnicalindicators import momentum_indicators as mi
from pytechnicalindicators import other_indicators as oi

# Getting Data

df = pd.read_csv("prices.csv", parse_dates=["Date"])
df = df.sort_values("Date").reset_index(drop=True)

# Converting DataFrame Columns to Lists

close = df["Close"].astype(float).tolist()
high  = df["High"].astype(float).tolist()
low   = df["Low"].astype(float).tolist()
open_ = df["Open"].astype(float).tolist()

# Simple Moving Average

# Single

sma_all = ma.single.moving_average(close, moving_average_type="simple")
print("Full-series SMA:", sma_all)

# Bulk 

period = 20 # 1 month
sma_series = ma.bulk.moving_average(close, period=period, moving_average_type="simple")

# Moving Constant Bands

# Single

lower, middle, upper = ci.single.moving_constant_bands(
        close[-20:],
        constant_model_type="exponential_moving_average",
        deviation_model="standard_deviation",
        deviation_multiplier=2.0,
)

print(lower, middle, upper)

# Bulk

bands = ci.bulk.moving_constant_bands(
    close,
    constant_model_type="exponential_moving_average",
    deviation_model="standard_deviation",
    deviation_multiplier=2.0,
    period=20
)

# RSI

rsi_values = mi.bulk.relative_strength_index(
    close,
    constant_model_type="smoothed_moving_average",
    period=20
)

# ATR

atr_series = oi.bulk.average_true_range(
    close=close,
    high=high,
    low=low,
    constant_model_type="simple_moving_average",
    period=20
)



# Align back to DataFrame: last len(sma_series) rows correspond to rolling results
df.loc[df.index[-len(sma_series):], f"SMA_{period}"] = sma_series

# Unpack and assign (align to tail)
lower_vals, mid_vals, upper_vals = zip(*bands)
tail_index = df.index[-len(bands):]
df.loc[tail_index, "MCB_Lower"] = lower_vals
df.loc[tail_index, "MCB_EMA"] = mid_vals
df.loc[tail_index, "MCB_Upper"] = upper_vals

df.loc[df.index[-len(rsi_values):], "RSI"] = rsi_values
df.loc[df.index[-len(atr_series):], f"ATR_{period}"] = atr_series

print(df.tail())

