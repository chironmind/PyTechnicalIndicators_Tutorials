import pandas as pd
import requests
from pytechnicalindicators import moving_average as ma
from pytechnicalindicators import candle_indicators as ci
from pytechnicalindicators import momentum_indicators as mi
from pytechnicalindicators import other_indicators as oi

import plotly.graph_objects as go
from plotly.subplots import make_subplots


# From tutorial 1

# Getting Data

def fetch_binance_ohlcv(symbol="BTCUSDT", interval="1d", limit=365):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    # Binance returns a list of lists:
    # [Open time, Open, High, Low, Close, Volume, Close time, ...]
    df = pd.DataFrame(data, columns=[
        "OpenTime", "Open", "High", "Low", "Close", "Volume",
        "CloseTime", "QuoteAssetVolume", "NumTrades", "TakerBuyBase", "TakerBuyQuote", "Ignore"
    ])
    df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms")
    cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    df = df[cols].astype({"Open": float, "High": float, "Low": float, "Close": float, "Volume": float})
    df = df.sort_values("Date").reset_index(drop=True)
    return df

# Example usage
df = fetch_binance_ohlcv(symbol="BTCUSDT", interval="1d", limit=365)
print(df.head())

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

# Tutorial 2

fig = make_subplots(
    rows=3,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    row_heights=[0.6, 0.2, 0.2],
    subplot_titles=("Price & Overlays", "RSI", "ATR")
)

# --- Row 1: Candlestick ---
fig.add_trace(
    go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        showlegend=True
    ),
    row=1, col=1
)

# --- Row 1: SMA ---
sma_col = f"SMA_20"
if sma_col in df:
    fig.add_trace(
        go.Scatter(
            x=df["Date"], y=df[sma_col],
            name=sma_col,
            line=dict(color="orange", width=1.3),
            hovertemplate="SMA %{y:.2f}<extra></extra>"
        ),  
        row=1, col=1
    )   

# --- Row 1: Moving Constant Bands (shaded) --- 
if {"MCB_Lower","MCB_Upper","MCB_EMA"}.issubset(df.columns):
    fig.add_trace(
        go.Scatter(
            x=df["Date"], y=df["MCB_Upper"],
            name="MCB Upper",
            line=dict(color="royalblue", width=1),
            hovertemplate="Upper %{y:.2f}<extra></extra>",
            opacity=0.7
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df["Date"], y=df["MCB_Lower"],
            name="MCB Lower",
            line=dict(color="royalblue", width=1),
            fill="tonexty",
            fillcolor="rgba(65,105,225,0.15)",
            hovertemplate="Lower %{y:.2f}<extra></extra>",
            opacity=0.7
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df["Date"], y=df["MCB_EMA"],
            name="MCB Mid",
            line=dict(color="royalblue", width=0.8, dash="dot"),
            hovertemplate="Mid %{y:.2f}<extra></extra>",
            opacity=0.6
        ),
        row=1, col=1
    )

# --- Row 2: RSI ---
if "RSI" in df:
    fig.add_trace(
        go.Scatter(
            x=df["Date"], y=df["RSI"],
            name="RSI (20)",
            line=dict(color="purple"),
            hovertemplate="RSI %{y:.2f}<extra></extra>"
        ),
        row=2, col=1
    )
    # Overbought / Oversold reference lines
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

# --- Row 3: ATR ---
atr_col = "ATR_20"
if atr_col in df:
    fig.add_trace(
        go.Bar(
            x=df["Date"], y=df[atr_col],
            name=atr_col,
            marker_color="gray",
            hovertemplate="ATR %{y:.2f}<extra></extra>",
            opacity=0.7
        ),
        row=3, col=1
    )

fig.update_layout(
    title=f"API Dashboard",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_rangeslider_visible=False,
    template="plotly_white",
    margin=dict(l=40, r=40, t=60, b=40),
    hovermode="x unified"
)

# Improve y-axis titles
fig.update_yaxes(title_text="Price", row=1, col=1)
fig.update_yaxes(title_text="RSI",   row=2, col=1, range=[0,100])
fig.update_yaxes(title_text="ATR",   row=3, col=1)

fig.show()

# If using kaleido
# fig.write_image("api_dashboard.png", scale=2, width=1400, height=900)
