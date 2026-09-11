import os
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
import math

from tickers import tickers, raw_weights
from util import get_weights


# 1. Configuration & Custom Weights & collected data
# Last_X_days = 10
data_13 = []
data_close = []

# Normalize weights so they sum to 1.0
weights = get_weights(tickers, raw_weights)

lookback_months = 3
days = 60
output_dir = f"charts_weighted_{lookback_months}m"
os.makedirs(output_dir, exist_ok=True)

print("Downloading market data...")
df_5m = yf.download(
    tickers, period=f"{days}d", interval="5m", auto_adjust=True, progress=False
)["Close"]
df_1h = yf.download(
    tickers, period="366d", interval="60m", auto_adjust=True, progress=False
)["Close"]
df_daily = yf.download(
    tickers, period="366d", interval="1d", auto_adjust=True, progress=False
)["Close"]

print("Download complete. Generating charts...")
# Group 5-minute data by market trading date
grouped_5m = list(df_5m.groupby(df_5m.index.date))



for current_date, day_5m in grouped_5m:
    # Forward-fill missing intraday bars to prevent empty gaps
    day_5m = day_5m.ffill().bfill().dropna(how="all")
    if day_5m.empty:
        continue

    # ----------------------------------------------------
    # 2. TOP GRAPH: Intraday % Change & Weighted Return Calculations
    # ----------------------------------------------------
    prev_daily = df_daily[df_daily.index.date < current_date]
    if prev_daily.empty:
        continue

    base_5m = prev_daily.iloc[-1]
    pct_5m = ((day_5m - base_5m) / base_5m) * 100

    # --- A. Portfolio Return @ 13:00 ---
    at_13_data = pct_5m[pct_5m.index.time <= pd.to_datetime("13:00").time()]

    if not at_13_data.empty:
        returns_at_13 = at_13_data.iloc[-1]
        weighted_total_13 = sum(
            returns_at_13[t] * weights[t]
            for t in tickers
            if t in returns_at_13 and not pd.isna(returns_at_13[t])
        )
        label_13pm = f"13:00: {weighted_total_13:+.2f}%"
    else:
        label_13pm = "13:00: N/A"

    # --- B. Portfolio Return @ Last Timestep ---
    returns_last = pct_5m.iloc[-1]
    weighted_total_last = sum(
        returns_last[t] * weights[t]
        for t in tickers
        if t in returns_last and not pd.isna(returns_last[t])
    )
    last_time_str = returns_last.name.strftime("%H:%M")
    label_last = f"Close/Latest ({last_time_str}): {weighted_total_last:+.2f}%"

    # Combined title label
    combined_label = f"Portfolio Return -> {label_13pm} | {label_last}"

    data_13.append(float(weighted_total_13))
    data_close.append(float(weighted_total_last))

    # ----------------------------------------------------
    # 3. BOTTOM GRAPH: Hourly Trend
    # ----------------------------------------------------
    df_1h_until_today = df_1h[df_1h.index.date <= current_date]
    available_dates = sorted(list(set(df_1h_until_today.index.date)))

    hourly_trading_days = lookback_months * 21
    start_idx = max(0, len(available_dates) - (hourly_trading_days + 1))
    start_date = available_dates[start_idx]

    slice_1h = (
        df_1h_until_today[df_1h_until_today.index.date >= start_date]
        .ffill()
        .bfill()
        .dropna(how="all")
    )

    pre_start_daily = df_daily[df_daily.index.date < start_date]
    base_1h = (
        pre_start_daily.iloc[-1]
        if not pre_start_daily.empty
        else slice_1h.iloc[0]
    )

    pct_1h = ((slice_1h - base_1h) / base_1h) * 100

    # ----------------------------------------------------
    # 4. PLOT STACKED SUBPLOTS
    # ----------------------------------------------------
    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, figsize=(14, 10), sharex=False
    )

    # --- Top Plot ---
    for ticker in tickers:
        if ticker in pct_5m.columns:
            ax_top.plot(
                pct_5m.index, pct_5m[ticker], label=ticker, linewidth=1.5
            )

    ax_top.set_title(
        f"1-Day Intraday 5m % Change — {current_date}\n[{combined_label}]",
        fontsize=12,
        fontweight="bold",
    )
    ax_top.set_ylabel("% Change", fontsize=10)
    ax_top.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    
    # --- Timezone-aware 13:00 Reference Line Fix ---
    timestamp_13 = pd.Timestamp(f"{current_date} 13:00")
    if pct_5m.index.tz is not None:
        timestamp_13 = timestamp_13.tz_localize(pct_5m.index.tz)

    if pct_5m.index.min() <= timestamp_13 <= pct_5m.index.max():
        ax_top.axvline(
            timestamp_13,
            color="red",
            linestyle=":",
            linewidth=1,
            label="13:00 Mark",
        )

    ax_top.legend(loc="upper left")
    ax_top.grid(True, linestyle=":", alpha=0.6)

    # --- Bottom Plot ---
    df_1h_reset = pct_1h.reset_index()
    time_col = df_1h_reset.columns[0]

    for ticker in tickers:
        if ticker in df_1h_reset.columns:
            ax_bottom.plot(
                df_1h_reset.index,
                df_1h_reset[ticker],
                label=ticker,
                linewidth=1.2,
            )

    tick_locs = range(0, len(df_1h_reset), max(1, len(df_1h_reset) // 6))
    tick_labs = [
        df_1h_reset[time_col].iloc[i].strftime("%b %d") for i in tick_locs
    ]
    ax_bottom.set_xticks(tick_locs)
    ax_bottom.set_xticklabels(tick_labs)

    ax_bottom.set_title(
        f"Macro Trend 1h % Change — {lookback_months} Months ({start_date} to {current_date})",
        fontsize=12,
        fontweight="bold",
    )
    ax_bottom.set_xlabel("Date", fontsize=10)
    ax_bottom.set_ylabel("% Change", fontsize=10)
    ax_bottom.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    ax_bottom.legend(loc="upper left")
    ax_bottom.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()

    filename = os.path.join(output_dir, f"chart_{current_date}.png")
    plt.savefig(filename, dpi=150)
    plt.close()



n = len(data_13)
period = days / 30.0
mult_13 = (math.exp(sum(math.log(x/100+1) for x in data_13) / n) - 1) * 100
mult_close = (math.exp(sum(math.log(x/100+1) for x in data_close) / n) - 1) * 100
monthly_return = (math.exp(sum(math.log((y - x)/100+1) for x, y in zip(data_13, data_close)) / period) - 1) * 100
with open(os.path.join(output_dir, "summary.txt"), "w") as f:
    for i,j in zip(data_13, data_close):
        f.write(f"13:00: {i:+.2f}% | Close/Latest: {j:+.2f}% | Diff: {(j-i):+.2f}%\n")
    f.write("\n")
    f.write(f"13:00: {mult_13:+.2f}% | Close/Latest: {mult_close:+.2f}% | Diff: {(mult_close-mult_13):+.2f}%\n")
    f.write("\n")
    for i,j in weights.items():
        f.write(f"{i}: {j*100:.2f}%\n")
    f.write(f"Monthly Return: {monthly_return:+.2f}%\n")

