# Tutorial 1: Using PyTechnicalIndicators with pandas

> Leverage Rust-powered speed inside familiar pandas workflows.

This tutorial is the first in a series of tutorials:
- 01 - Using PyTechnicalIndicators with pandas
- [02 - Using PyTechnicalIndicators with Plotly](./02_using_plotly_and_pytechnicalindicators.md)
- [03 - More advanced use cases for PyTechnicalIndicators](./03_advanced_pytechnicalindicators.md)
- [04 - Connecting to an API](./04_api_connection.md)
- [05 - Using PyTechnicalIndicators with Jupyter Notebooks](./05_using_jupyter_and_pytechnicalindicators.ipynb)

---

## 🎯 Goal

In this tutorial you will learn how to:
- Install and import `pytechnicalindicators`
- Load OHLCV price data into a pandas `DataFrame`
- Convert columns to the list inputs expected by the library
- Call both `single` (scalar) and `bulk` (rolling / series) indicator functions
- Add indicator outputs back into your `DataFrame`
- Understand parameter and model choices (e.g. different moving average types)
- Handle common pitfalls (NaNs, alignment, window offsets)

---

## 📦 Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | (Match your environment; verify with `python --version`) |
| pip / virtualenv | Recommended to isolate dependencies |
| pandas | For data handling |

Install basics:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install pandas
```

Install PyTechnicalIndicators (assuming published wheel / build locally):

```bash
pip install pytechnicalindicators
# OR (from source after cloning)
# pip install maturin
# maturin develop
```

---

## 🧱 Library Structure (Quick Recap)

Modules are grouped by analysis area:

- `standard_indicators`
- `momentum_indicators`
- `trend_indicators`
- `strength_indicators`
- `volatility_indicators`
- `candle_indicators`
- `chart_trends`
- `correlation_indicators`
- `other_indicators`

Each module has two namespaces:
- `single`: operates on the entire list (returns one value or a tuple)
- `bulk`: rolling / windowed computation (returns a list aligned to the trailing end of each window)

Example:
```python
from pytechnicalindicators import standard_indicators

standard_indicators.single.simple_moving_average(prices)
standard_indicators.bulk.simple_moving_average(prices, period=20)
```

---

## 📥 Getting Some Data 

If you already have a CSV point to your CSV, we will be using `examples/prices.csv` for our tutorials:

```python
df = pd.read_csv("prices.csv", parse_dates=["Date"])
df = df.sort_values("Date").reset_index(drop=True)
```

---

## 🔄 Converting DataFrame Columns to Lists

Most functions expect Python `list[float]` (not Series, not NumPy arrays). Convert cleanly:

```python
close = df["Close"].astype(float).tolist()
high  = df["High"].astype(float).tolist()
low   = df["Low"].astype(float).tolist()
open_ = df["Open"].astype(float).tolist()
```

(You can keep naming consistent; `open_` avoids shadowing Python's built-in `open`.)

---

## ✅ Example 1: Simple Moving Average (SMA)

[API Reference](https://github.com/chironmind/PyTechnicalIndicators/wiki/API-Moving-Average)

### Single (all data as one window)
```python
from pytechnicalindicators import import moving_average as ma

sma_all = ma.single.moving_average(close, moving_average_type="simple")
print("Full-series SMA:", sma_all)
```

### Bulk (rolling window)
```python
period = 20
sma_series = ma.bulk.moving_average(close, period=period, moving_average_type="simple")
# Align back to DataFrame: last len(sma_series) rows correspond to rolling results
df.loc[df.index[-len(sma_series):], f"SMA_{period}"] = sma_series
```

Tip: The first `(period - 1)` rows have no value because a full window was not yet available. You can forward fill or leave as NaN depending on downstream needs.

---

## ✅ Example 2: Moving Constant Bands (Generic Bollinger Bands)

[API Reference](https://github.com/chironmind/PyTechnicalIndicators/wiki/API-Candle-Indicators)

`single` version returns a tuple `(lower, middle, upper)`; `bulk` returns a list of such tuples.

```python
lower, middle, upper = ci.single.moving_constant_bands(
        close[-20:],
        constant_model_type="exponential_moving_average",
        deviation_model="standard_deviation",
        deviation_multiplier=2.0,
)
print(lower, middle, upper)
```

Bulk usage:

```python
bands = ci.bulk.moving_constant_bands(
    close,
    constant_model_type="exponential_moving_average",
    deviation_model="standard_deviation",
    deviation_multiplier=2.0,
    period=20
)

# Unpack and assign (align to tail)
lower_vals, mid_vals, upper_vals = zip(*bands)
tail_index = df.index[-len(bands):]
df.loc[tail_index, "MCB_Lower"] = lower_vals
df.loc[tail_index, "MCB_EMA"] = mid_vals
df.loc[tail_index, "MCB_Upper"] = upper_vals
```

---

## ✅ Example 3: Relative Strength Index (RSI)

[API Reference](https://github.com/chironmind/PyTechnicalIndicators/wiki/API-Momentum-Indicators)

```python
rsi_values =  mi.bulk.relative_strength_index(
    close,
    constant_model_type="smoothed_moving_average",
    period=20
)

df.loc[df.index[-len(rsi_values):], "RSI"] = rsi_values
```

---

## ✅ Example 4: Average True Range (ATR)

[API Reference](https://github.com/chironmind/PyTechnicalIndicators/wiki/API-Other-Indicators)

Valid constant model strings (case-insensitive aliases):  
`simple`, `smoothed`, `exponential`, `median`, `mode`  
(Full forms also accepted: `simple_moving_average`, `smoothed_moving_average`, etc.)

```python
from pytechnicalindicators import other_indicators

model = "exponential_moving_average"
period = 14

atr_series = other_indicators.bulk.average_true_range(
    close=close,
    high=high,
    low=low,
    constant_model_type=model,
    period=period
)
df.loc[df.index[-len(atr_series):], f"ATR_{period}"] = atr_series
```

---

## 🧪 Single vs Bulk: When to Use Which?

| Use Case | Pick |
|----------|------|
| One summary value for entire dataset | `single` |
| Rolling feature engineering for models | `bulk` |
| Signal snapshot at latest bar | `single` on a sliced tail |
| Chart overlays / time series indicators | `bulk` |

---

## 🛠️ Handling Alignment

Bulk outputs are shorter than the original price history when a window (`period`) is specified. Strategies:

```python
# Method 1: Right-align (as shown earlier)
df.loc[df.index[-len(series):], "Indicator"] = series

# Method 2: Pad with NaN at front
import numpy as np
padded = [np.nan] * (len(df) - len(series)) + series
df["Indicator"] = padded
```

---

## 🧪 Missing Data / NaNs

Before extracting lists:

```python
df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
```

If you forward-fill:

```python
df[["Open","High","Low","Close","Volume"]] = df[["Open","High","Low","Close","Volume"]].ffill()
```

Be cautious: forward-filling can create artificial continuity.

---

## ⚙️ Choosing Constant / Deviation Models

Many functions accept a `constant_model_type` or `deviation_model` to alter smoothing or dispersion behavior.  
Experiment:

Consult the project wiki/API reference for model-specific effects:
- Wiki: https://github.com/chironmind/PyTechnicalIndicators/wiki
- API Reference: https://github.com/chironmind/PyTechnicalIndicators/wiki/API-Reference

---

## 🧩 Putting It All Together

A runnable example of the full code can be found in [`01_using_pandas_and_pytechnicalindicators.py`](./examples/01_using_pandas_and_pytechnicalindicators.py)

```shell
python3 01_using_pandas_and_pytechnicalindicators.py
```

**Output:**
```shell
Full-series SMA: 5624.867410358566
5367.04826935573 5755.587345685254 6144.126422014779
          Date     Open     High      Low    Close     SMA_20     BB_Lower    BB_Middle     BB_Upper        RSI   ATR_20
246 2025-03-10  5705.37  5705.37  5564.02  5614.56  5956.2700  5579.906354  5877.649008  6175.391662  33.281207  84.9520
247 2025-03-11  5603.65  5636.30  5528.41  5572.07  5931.5515  5504.588851  5841.191158  6177.793465  36.744063  88.9195
248 2025-03-12  5624.84  5642.19  5546.09  5599.30  5908.0915  5451.413841  5811.173289  6170.932737  33.949163  92.0275
249 2025-03-13  5594.45  5597.78  5504.65  5521.52  5881.5690  5385.361698  5775.695387  6166.029075  33.043555  93.6840
250 2025-03-14  5563.85  5645.27  5563.85  5638.94  5857.7625  5367.048269  5755.587346  6144.126422  39.573869  94.4570
```

---

## 🚀 Performance Tips

- Convert Series to plain Python lists only once; reuse.
- Gather all indicators first, then assign to DataFrame to minimize index alignment overhead.
- For large backtests, consider chunking historical data and streaming features forward.

---

## 🧾 Common Pitfalls

| Issue | Cause | Fix |
|-------|-------|-----|
| ValueError for model type | Misspelled string | Use accepted aliases (`simple`, `exponential`, etc.) |
| Mismatched lengths when merging | Rolling window shrinks output | Right-align or pad with NaNs |
| NaNs propagate into indicators | Missing OHLC data | Clean with `dropna` or controlled fills |
| Confusing `single` vs `bulk` | Wrong namespace | Use `module.single.*` or `module.bulk.*` |

---

## 🛡️ Disclaimer

Educational example only. Not financial advice. Validate results independently before using in production or live trading.

---

## ✅ Next Step

You now know how to integrate PyTechnicalIndicators into a pandas workflow and engineer feature columns efficiently.

Next discover how to integrate [Plotly charts](./02_using_plotly_and_pytechnicalindicators.md)

---

Happy analyzing! 🦀🐍📈
