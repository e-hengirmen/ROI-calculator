import os
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from tickers import tickers


# 1. Configuration

output_dir = "charts_5m_relative"
os.makedirs(output_dir, exist_ok=True)

# 2. Download 60d of 5-minute intraday data + 65d of daily data for exact baseline closes
print("Downloading 5-minute intraday data...")
df_5m = yf.download(
    tickers, period="60d", interval="5m", auto_adjust=True, progress=False
)["Close"]

print("Downloading daily data to get exact previous day close prices...")
df_daily = yf.download(
    tickers, period="65d", interval="1d", auto_adjust=True, progress=False
)["Close"]

# Group 5-minute data by market trading date
grouped_5m = list(df_5m.groupby(df_5m.index.date))

# 3. Process each day using the previous day's daily Close as baseline
for i, (current_date, day_data) in enumerate(grouped_5m):
    day_data = day_data.dropna(how="all")
    if day_data.empty:
        continue

    # Get daily closes prior to the current trading date
    prev_daily_closes = df_daily[df_daily.index.date < current_date]

    if prev_daily_closes.empty:
        # Skip if no prior daily baseline exists
        continue

    # Extract the exact previous trading day's closing price
    baseline_series = prev_daily_closes.iloc[-1]

    # Calculate percentage change from previous day's close
    pct_change_df = ((day_data - baseline_series) / baseline_series) * 100

    # 4. Plot current day chart
    plt.figure(figsize=(12, 6))

    for ticker in tickers:
        if ticker in pct_change_df.columns:
            plt.plot(
                pct_change_df.index,
                pct_change_df[ticker],
                label=ticker,
                linewidth=1.5,
            )

    plt.title(
        f"5-Minute Intraday % Change (vs. Prev Day Close) — {current_date}",
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel("Time (UTC)", fontsize=10)
    plt.ylabel("% Change from Previous Day Close", fontsize=10)
    plt.axhline(0, color="black", linestyle="--", linewidth=1, alpha=0.7)
    plt.legend(loc="upper left")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.tight_layout()

    filename = os.path.join(output_dir, f"chart_{current_date}.png")
    plt.savefig(filename)
    plt.close()

print(
    f"Successfully generated relative intraday charts in '{output_dir}/' folder."
)