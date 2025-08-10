# Tutorial 3: Systematically Evaluating RSI Variants

> In this tutorial we go deep on just one indicator: the Relative Strength Index (RSI).  
> We will systematically compare different `constant_model_type` variants and periods, score their signals, and rank configurations.  
> You can later apply the exact same framework to other indicators (see “Extending Further”).

Series so far:
- [01 - Using PyTechnicalIndicators with pandas](./01_pandas_and_pytechnicalindicators.md)
- [02 - Using PyTechnicalIndicators with Plotly](./02_using_plotly_and_pytechnicalindicators.md)
- 03 - Systematically Evaluating RSI Variants (this file)
- [04 - Connecting to an API](./04_api_connection.md)
- [05 - Using PyTechnicalIndicators with Jupyter Notebooks](./05_using_jupyter_and_pytechnicalindicators.md)

---

## 🎯 Goal

You will learn how to:
1. Enumerate RSI variants via different `constant_model_type` values.
2. Iterate across a period grid (e.g., 5–30).
3. Generate oversold / overbought signals (long/short candidates).
4. Score each signal using a forward-looking heuristic (inspired by the Rust version in `choose_right_model.md`).
5. Aggregate scores into a ranked table of configurations.
6. (Optional) Adjust thresholds, horizon, and scoring weights.
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
| constant_model_type | `simple`, `smoothed`, `exponential`, `median`, `mode` |
| period              | 5, 7, 10, 14, 20, 28 |
| oversold threshold  | 30 (default, can parametrize) |
| overbought threshold| 70 (default, can parametrize) |
| forward horizon (H) | 5 bars (example) |
| ATR normalization   | Optional (for move scaling) |

---

## 📂 Data Setup

```python
import pandas as pd
import numpy as np
import pytechnicalindicators as pti

df = pd.read_csv("prices.csv", parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
df = df.dropna(subset=["Open","High","Low","Close"])
close = df["Close"].astype(float).tolist()
```

---

## 🧮 Optional: ATR for Normalization

We normalize favorable move sizes by ATR to compare across volatility regimes.  
(You can skip normalization; just divide by price or leave raw.)

```python
ATR_PERIOD = 14
ATR_MODEL = "exponential_moving_average"

atr_vals = pti.other_indicators.bulk.average_true_range(
    close=close,
    high=df["High"].astype(float).tolist(),
    low=df["Low"].astype(float).tolist(),
    constant_model_type=ATR_MODEL,
    period=ATR_PERIOD
)

df.loc[df.index[-len(atr_vals):], f"ATR_{ATR_PERIOD}"] = atr_vals

def get_atr(i):
    v = df.iloc[i][f"ATR_{ATR_PERIOD}"]
    if pd.isna(v) or v <= 0:
        return df.iloc[i]["Close"] * 0.005  # fallback small scale
    return v
```

---

## 🧪 Signal Definition

For each RSI series:
- Long (expected upward move) if RSI < oversold threshold (default 30).
- Short (expected downward move) if RSI > overbought threshold (default 70).
- Neutral otherwise.

We then evaluate each signal using only FUTURE bars up to a forward horizon H (e.g., 5 bars). This is still an in-sample heuristic; for rigorous evaluation you must later time-split.

---

## 📏 Scoring Heuristic

For a signal at index i:
- Gather `future_prices = close[i+1 : i+1+H]`
- If long signal:
  - favorable_move = max(future_prices) - entry_price
- If short signal:
  - favorable_move = entry_price - min(future_prices)
- Normalize: `normalized_move = favorable_move / ATR(i)`
- Efficiency: `efficiency = normalized_move / H`
- Hit flag: 1 if favorable_move ≥ (target_atr_multiple * ATR(i)) else 0
- Weighted score:  
  `score = w_move * normalized_move + w_eff * efficiency + w_hit * hit_flag`

Example weights (tune):
- w_move = 0.6
- w_eff = 0.3
- w_hit = 0.1
- target_atr_multiple = 1.0

---

## 🧪 Core Evaluation Loop (RSI Only)

```python
from statistics import mean

CONSTANT_MODELS = ["simple", "smoothed", "exponential", "median", "mode"]
PERIODS = [5, 7, 10, 14, 20, 28]

OVERSOLD = 30.0
OVERBOUGHT = 70.0
HORIZON = 5

W_MOVE = 0.6
W_EFF  = 0.3
W_HIT  = 0.1
TARGET_ATR_MULTIPLE = 1.0

def score_signal(entry_index, direction):
    # direction: "up" (long) or "down" (short)
    end = min(len(close), entry_index + 1 + HORIZON)
    future = close[entry_index+1:end]
    if not future:
        return None
    entry_price = close[entry_index]
    atr_here = get_atr(entry_index)

    if direction == "up":
        favorable = max(future) - entry_price
    else:
        favorable = entry_price - min(future)

    if favorable < 0:
        favorable = 0.0

    normalized_move = favorable / atr_here
    efficiency = normalized_move / HORIZON
    hit = 1 if favorable >= TARGET_ATR_MULTIPLE * atr_here else 0
    total = W_MOVE * normalized_move + W_EFF * efficiency + W_HIT * hit
    return {
        "idx": entry_index,
        "direction": direction,
        "normalized_move": normalized_move,
        "efficiency": efficiency,
        "hit": hit,
        "score": total
    }

results = []

for ctype in CONSTANT_MODELS:
    for period in PERIODS:
        # Compute RSI variant
        rsi_vals = pti.momentum_indicators.bulk.relative_strength_index(
            close,
            constant_model_type=ctype,
            period=period
        )
        start_idx = len(close) - len(rsi_vals)
        signal_scores = []

        for offset, rsi in enumerate(rsi_vals):
            i = start_idx + offset
            if rsi < OVERSOLD:
                s = score_signal(i, "up")
                if s: signal_scores.append(s)
            elif rsi > OVERBOUGHT:
                s = score_signal(i, "down")
                if s: signal_scores.append(s)

        if not signal_scores:
            continue

        avg_score = mean(s["score"] for s in signal_scores)
        median_norm = np.median([s["normalized_move"] for s in signal_scores])
        hit_rate = np.mean([s["hit"] for s in signal_scores])
        avg_eff = mean(s["efficiency"] for s in signal_scores)

        results.append({
            "indicator": "RSI",
            "constant_model": ctype,
            "period": period,
            "signals": len(signal_scores),
            "avg_score": avg_score,
            "median_norm_move": median_norm,
            "hit_rate": hit_rate,
            "avg_efficiency": avg_eff
        })

rsi_rank = pd.DataFrame(results)

# Filter out too-few signals (avoid spurious wins)
MIN_SIGNALS = 5
rsi_rank = rsi_rank[rsi_rank["signals"] >= MIN_SIGNALS].copy()

# Composite ranking (tunable)
def composite(row):
    return (0.5 * row["avg_score"]
            + 0.25 * row["hit_rate"]
            + 0.15 * row["median_norm_move"]
            + 0.10 * row["avg_efficiency"])

rsi_rank["composite_score"] = rsi_rank.apply(composite, axis=1)
rsi_rank = rsi_rank.sort_values("composite_score", ascending=False)

print("Top RSI Variants:")
print(rsi_rank.head(10))
```

---

## 📊 Example Output (Structure)

```
  indicator constant_model  period  signals  avg_score  median_norm_move  hit_rate  avg_efficiency  composite_score
0       RSI        smoothed      14       22   0.84213            0.9712     0.545          0.1947          0.78211
1       RSI      exponential      10       25   0.83005            0.9104     0.520          0.1889          0.75844
...
```

(Your numbers will differ based on data.)

---

## 🧠 Interpreting Results

| Metric | Interpretation |
|--------|----------------|
| signals | Too low → unreliable statistic (e.g., <5) |
| avg_score | Weighted quality of all signals |
| median_norm_move | Typical reward vs ATR (robust to outliers) |
| hit_rate | Fraction achieving >= 1 ATR favorable move within horizon |
| avg_efficiency | Speed of move per bar |
| composite_score | Combined metric (tune per your objectives) |

---

## ⚠️ Limitations

- Still in-sample: no time-split or walk-forward here (add that before using results).
- Heuristic scoring: you chose weights; different weights → different ranking.
- Assumes symmetrical importance of long vs short (you can separate them).
- Forward horizon fixed (consider sensitivity testing).

---

## 🔄 Customization Knobs

| Parameter | Effect |
|-----------|--------|
| HORIZON | Longer → more chance of eventual move, dilutes efficiency |
| OVERSOLD / OVERBOUGHT | Stricter thresholds → fewer, possibly higher-quality signals |
| TARGET_ATR_MULTIPLE | Harder or easier to “hit” |
| Weights (W_MOVE, W_EFF, W_HIT) | Emphasize magnitude, speed, or binary success |
| MIN_SIGNALS | Filter out noise configurations |

---

## 🧪 Quick Variations

1. Separate Long / Short leaderboards:
   ```python
   # Tag signals with direction; split and aggregate separately.
   ```
2. Add penalty if adverse move > X * ATR before favorable move:
   ```python
   # Track min/max excursion inside horizon.
   ```
3. Replace ATR with rolling std or ulcer index for normalization.

---

## 🧾 Common Pitfalls

| Pitfall | Cause | Mitigation |
|---------|-------|------------|
| “Best” config has 2 signals | Small sample | Enforce MIN_SIGNALS |
| Overfitting to one period | In-sample bias | Time-based train/validation split |
| High hit_rate, low avg_score | Many small wins | Adjust weighting / inspect normalized_move |
| Negative normalized_move entries | Not filtered | We clamp unfavorable (<0) to 0 in this design |

---

## 🧩 Minimal Walk-Forward (Outline Only)

(Not coded fully here—add in a research workflow)

1. Split chronology into slices.
2. Run variant evaluation on slice 1 → pick top N.
3. Apply those N on slice 2 (no re-selection) → record performance.
4. Optionally re-select per window (but risk regime adaptation bias).
5. Final evaluation on last holdout period.

---

## 📦 Packaging the Evaluation (Optional Class)

You could wrap logic into an `RSIVariantEvaluator` with methods:
- `generate_variants()`
- `evaluate_variant(constant_model, period)`
- `rank()`
- `to_parquet()`

(Left out here to keep the tutorial tight.)

---

## 🚀 Extending Further (Reader Exercise)

Apply identical methodology to:
- Moving Constant Bands: vary (constant_model_type, deviation_model, period, deviation_multiplier)
- ATR strategies: vary (constant_model_type, period)
- Moving Averages crossovers: evaluate entry quality after cross
- Trend indicators (e.g., Aroon, Parabolic) by measuring reversal proximity

Key changes:
- Change signal triggers (e.g., band touches, crossovers, trend flips)
- Possibly adjust favorable move definition (e.g., trailing stops)

---

## 🛡️ Disclaimer

This is a heuristic research scaffold.  
Before deploying:
- Use strict out-of-sample evaluation
- Consider slippage, execution latency, regime changes
- Avoid over-weighting a single metric

---

## ✅ Next Step

Proceed to: [04 - Connecting to an API](./04_api_connection.md)  
We will fetch external data, then optionally plug the RSI evaluator into a scheduled workflow.

---

Happy variant hunting! 🦀🐍📈
