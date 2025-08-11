# Tutorial 3: Advanced Usage of PyTechnicalIndicators

> In this tutorial we go deep on just one indicator: the Relative Strength Index (RSI).  
> We will systematically compare different `constant_model_type` variants and periods, score their signals, and rank configurations.  
> You can later apply the exact same framework to other indicators (see “Extending Further”).

Series so far:
- [01 - Using PyTechnicalIndicators with pandas](./01_pandas_and_pytechnicalindicators.md)
- [02 - Using PyTechnicalIndicators with Plotly](./02_using_plotly_and_pytechnicalindicators.md)
- 03 - Systematically Evaluating RSI Variants (this file)
- [04 - Connecting to an API](./04_api_connection.md)
- [05 - Using PyTechnicalIndicators with Jupyter Notebooks](./05_using_jupyter_and_pytechnicalindicators.ipynb)

---

## 🎯 Goal

You will learn how to:
1. Enumerate RSI variants via different `constant_model_type` values.
2. Iterate across a period grid (e.g., 5–30).
3. Generate oversold / overbought signals (long/short candidates).
4. Score each signal using a forward-looking heuristic.
5. Aggregate scores into a ranked table of configurations.
7. Plan how to extend the same pattern to other indicators.

---

## 🧩 Why Focus on RSI?

Keeping scope narrow:
- Makes the scoring logic clearer.
- Prevents tutorial bloat.
- Allows you to internalize the evaluation pattern before generalizing.

---

## 🔧 Variant Dimensions

We will vary:

| Dimension | Values (Example) |
|----------|------------------|
| `constant_model_type` | `simple`, `smoothed`, `exponential`, `median`, `mode` |
| `period`              | 5, 7, 10, 14, 20, 28 |

---

## 📂 Data Setup

```python
import pandas as pd
import pytechnicalindicators as pti

df = pd.read_csv("prices.csv", parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
df = df.dropna(subset=["Open","High","Low","Close"])
close = df["Close"].astype(float).tolist()
```

---

## 🔧 Define Model Types and Period

```python
CONSTANT_MODELS = [
    "simple",
    "smoothed",
    "exponential",
    "median",
    "mode"
]
RSI_PERIOD = 5
OVERSOLD = 30.0
```

---

## 🧮 Compute RSI Variants and Rate Signals

```python
results = []

for ctype in CONSTANT_MODELS:
    # Compute RSI for this model type
    rsi_vals = pti.momentum_indicators.bulk.relative_strength_index(
        close,
        constant_model_type=ctype,
        period=RSI_PERIOD
    )
    # The output is aligned to the tail, so index mapping:
    start_idx = len(close) - len(rsi_vals)
    rating = 0
    total_signals = 0
    for offset, rsi in enumerate(rsi_vals[:-1]):  # skip last (no future bar)
        idx = start_idx + offset
        price = close[idx]
        if rsi < OVERSOLD:
            total_signals += 1
            next_price = close[idx + 1]
            if next_price > price:
                rating += 1
    success_rate = rating / total_signals if total_signals > 0 else 0.0
    results.append({
        "model": ctype,
        "period": RSI_PERIOD,
        "signals": total_signals,
        "correct_signals": rating,
        "success_rate": success_rate
    })
```

---

## 📊 Present the Results

```python
import pandas as pd

score_df = pd.DataFrame(results)
score_df = score_df.sort_values("success_rate", ascending=False)

print("RSI Model Ratings (RSI < 30, period=5):")
print(score_df[["model", "period", "signals", "correct_signals", "success_rate"]])

best = score_df.iloc[0]
print(f"\nBest model: {best['model']} (Success Rate: {best['success_rate']:.2%})")
```

Example output:

```
RSI Model Ratings (RSI < 30, period=5):
         model  period  signals  correct_signals  success_rate
3       median       5       43               24      0.558140
0       simple       5       38               20      0.526316
1     smoothed       5       41               21      0.512195
4         mode       5       41               21      0.512195
2  exponential       5       46               22      0.478261

Best model: median (Success Rate: 55.81%)

```

---

## 🧠 Interpreting Results

| Column           | Description                                            |
|------------------|-------------------------------------------------------|
| model            | The constant model type tested                         |
| period           | RSI period used (fixed here at 5 for comparison)       |
| signals          | Number of "buy" signals (RSI < 30) generated           |
| correct_signals  | Number of times the next price was higher (win)        |
| success_rate     | correct_signals / signals                              |

- A higher success rate suggests that the model/period pair gives better "next bar up" predictions when oversold.
- If `signals` is very low, results may not be reliable—try longer history or adjust period.

---

## 📝 Extending Further

- Try other periods (repeat the loop for different `RSI_PERIOD` values).
- Add "sell" signal evaluation (`RSI > 70` and next bar down).
- Apply similar logic to other indicators (e.g., bands, moving averages).
- Try longer-forward horizons (e.g., check next N bars for improvement).
- Visualize where signals occurred on the price chart (see Tutorial 2).

---

## 🛡️ Disclaimer

This is a didactic example, not a trading strategy.  
Success rate on "next bar" is just one toy metric—real research requires out-of-sample testing, risk modeling, and more.

---

## ✅ Next Step

Continue to: [04 - Connecting to an API](./04_api_connection.md)

---

Happy model testing! 🦀🐍📈
