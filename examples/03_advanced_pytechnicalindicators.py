import pandas as pd
import pytechnicalindicators as pti 

df = pd.read_csv("prices.csv", parse_dates=["Date"]).sort_values("Date").reset_index(drop=True)
df = df.dropna(subset=["Open","High","Low","Close"])
close = df["Close"].astype(float).tolist()

CONSTANT_MODELS = [
    "simple",
    "smoothed",
    "exponential",
    "median",
    "mode"
]
RSI_PERIOD = 5
OVERSOLD = 30.0

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

score_df = pd.DataFrame(results)
score_df = score_df.sort_values("success_rate", ascending=False)

print("RSI Model Ratings (RSI < 30, period=5):")
print(score_df[["model", "period", "signals", "correct_signals", "success_rate"]])

best = score_df.iloc[0]
print(f"\nBest model: {best['model']} (Success Rate: {best['success_rate']:.2%})")

