import os
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

from tickers import tickers, raw_weights

# 1. Configuration & Custom Weights
sum_weights = sum(raw_weights)
weights = {
    ticker: w / sum_weights for ticker, w in zip(tickers, raw_weights)
}

lookback_months = 3

print("Downloading market data...")
df_5m = yf.download(
    tickers, period="60d", interval="5m", auto_adjust=True, progress=False
)["Close"]
df_1h = yf.download(
    tickers, period="366d", interval="60m", auto_adjust=True, progress=False
)["Close"]
df_daily = yf.download(
    tickers, period="366d", interval="1d", auto_adjust=True, progress=False
)["Close"]

# Group 5-minute data by market trading date and take ONLY the last day
grouped_5m = list(df_5m.groupby(df_5m.index.date))[-1:]

for current_date, day_5m in grouped_5m:
    # Forward-fill missing intraday bars to prevent empty gaps
    day_5m = day_5m.ffill().bfill().dropna(how="all")
    if day_5m.empty:
        continue

    # ----------------------------------------------------
    # 2. TOP GRAPH: 5-Minute Intraday % Change & 13:00 Weight Calculation
    # ----------------------------------------------------
    # Fetch true previous close from df_5m instead of df_daily to prevent missing row bugs
    prev_5m = df_5m[df_5m.index.date < current_date]
    if prev_5m.empty:
        continue

    base_5m = prev_5m.dropna(how="all").iloc[-1]
    pct_5m = ((day_5m - base_5m) / base_5m) * 100

    # Locate closest bar to 13:00 (1:00 PM) for the day
    at_13_data = pct_5m[pct_5m.index.time <= pd.to_datetime("13:00").time()]

    if not at_13_data.empty:
        returns_at_13 = at_13_data.iloc[-1]
        weighted_total_13 = sum(
            returns_at_13[t] * weights[t]
            for t in tickers
            if t in returns_at_13 and not pd.isna(returns_at_13[t])
        )
        label_13pm = f"Portfolio Return @ 13:00: {weighted_total_13:+.2f}%"
    else:
        label_13pm = "Portfolio Return @ 13:00: N/A"

    # ----------------------------------------------------
    # 3. BOTTOM GRAPH: Hourly Trend (Clean Sequential Index)
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
        f"1-Day Intraday 5m % Change — {current_date}\n[{label_13pm}]",
        fontsize=12,
        fontweight="bold",
    )
    ax_top.set_ylabel("% Change", fontsize=10)
    ax_top.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    ax_top.axvline(
        pd.Timestamp(f"{current_date} 13:00"),
        color="red",
        linestyle=":",
        linewidth=1,
        label="13:00 Mark",
    )
    ax_top.legend(loc="upper left")
    ax_top.grid(True, linestyle=":", alpha=0.6)

    # --- Bottom Plot (Sequential Index to Remove Gaps/Jumps) ---
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

    filename = f"today.png"
    plt.savefig(filename, dpi=150)
    plt.close()

print(
    f"\nSuccessfully generated chart for {grouped_5m[0][0]}/'."
)