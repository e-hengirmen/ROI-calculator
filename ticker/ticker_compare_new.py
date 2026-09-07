import os
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from tickers import tickers

# 1. Configuration
lookback_months = 6  # X months default (translates to ~63 trading days)
output_dir = f"charts_stacked_{lookback_months}m"
os.makedirs(output_dir, exist_ok=True)

# Calculate trading days lookback (~21 trading days per month)
hourly_trading_days = lookback_months * 21

print("Downloading market data...")
# Top graph data (5m intraday for 60d)
df_5m = yf.download(
    tickers, period="60d", interval="5m", auto_adjust=True, progress=False
)["Close"]

# Bottom graph data (1h intraday for ~2 years)
df_1h = yf.download(
    tickers, period="370d", interval="60m", auto_adjust=True, progress=False
)["Close"]

# Daily baseline data
df_daily = yf.download(
    tickers, period="370d", interval="1d", auto_adjust=True, progress=False
)["Close"]

# Group 5-minute data by market trading date
grouped_5m = list(df_5m.groupby(df_5m.index.date))

for current_date, day_5m in grouped_5m:
    day_5m = day_5m.dropna(how="all")
    if day_5m.empty:
        continue

    # ----------------------------------------------------
    # 2. TOP GRAPH: Single Day 5-Minute Intraday % Change
    # ----------------------------------------------------
    prev_daily = df_daily[df_daily.index.date < current_date]
    if prev_daily.empty:
        continue

    # Baseline 1: Day before current date close
    base_5m = prev_daily.iloc[-1]
    pct_5m = ((day_5m - base_5m) / base_5m) * 100

    # ----------------------------------------------------
    # 3. BOTTOM GRAPH: Multi-Month Hourly Trend % Change
    # ----------------------------------------------------
    # Filter 1-hour data up to the end of current_date
    df_1h_until_today = df_1h[df_1h.index.date <= current_date]

    # Get distinct trading dates available prior to/on current_date
    available_dates = sorted(list(set(df_1h_until_today.index.date)))

    if len(available_dates) < (hourly_trading_days + 1):
        # Fall back to max available dates if history is shorter
        start_idx = 0
    else:
        start_idx = len(available_dates) - (hourly_trading_days + 1)

    start_date = available_dates[start_idx]

    # Slice hourly data between start_date and current_date
    slice_1h = df_1h_until_today[
        df_1h_until_today.index.date >= start_date
    ].dropna(how="all")

    # Baseline 2: Day before start_date close
    pre_start_daily = df_daily[df_daily.index.date < start_date]
    if pre_start_daily.empty:
        base_1h = slice_1h.iloc[0]  # Fallback to first available hourly bar
    else:
        base_1h = pre_start_daily.iloc[-1]

    pct_1h = ((slice_1h - base_1h) / base_1h) * 100

    # ----------------------------------------------------
    # 4. PLOT STACKED SUBPLOTS
    # ----------------------------------------------------
    fig, (ax_top, ax_bottom) = plt.subplots(
        2, 1, figsize=(14, 10), sharex=False
    )

    # --- Top Plot (5-Minute Intraday) ---
    for ticker in tickers:
        if ticker in pct_5m.columns:
            ax_top.plot(
                pct_5m.index, pct_5m[ticker], label=ticker, linewidth=1.5
            )

    ax_top.set_title(
        f"1-Day Intraday 5m % Change — {current_date} (vs. Prev Day Close)",
        fontsize=12,
        fontweight="bold",
    )
    ax_top.set_ylabel("% Change", fontsize=10)
    ax_top.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    ax_top.legend(loc="upper left")
    ax_top.grid(True, linestyle=":", alpha=0.6)

    # --- Bottom Plot (Hourly Trend - X Months Lookback) ---
    for ticker in tickers:
        if ticker in pct_1h.columns:
            ax_bottom.plot(
                pct_1h.index, pct_1h[ticker], label=ticker, linewidth=1.2
            )

    ax_bottom.set_title(
        f"Macro Trend 1h % Change — {lookback_months} Months Lookback ({start_date} to {current_date})",
        fontsize=12,
        fontweight="bold",
    )
    ax_bottom.set_xlabel("Date / Time", fontsize=10)
    ax_bottom.set_ylabel("% Change", fontsize=10)
    ax_bottom.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    ax_bottom.legend(loc="upper left")
    ax_bottom.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()

    filename = os.path.join(output_dir, f"stacked_chart_{current_date}.png")
    plt.savefig(filename, dpi=150)
    plt.close()

print(
    f"\nSuccessfully generated dual stacked charts in '{output_dir}/' folder."
)