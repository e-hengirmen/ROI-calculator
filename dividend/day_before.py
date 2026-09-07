import re
import datetime
from zoneinfo import ZoneInfo
import yfinance as yf
import pandas as pd
import warnings

# Uyarıları bastır
warnings.filterwarnings('ignore')

# Türkiye saat dilimini tanımla
tr_tz = ZoneInfo("Europe/Istanbul")

raw_data = []
with open("processed_data.txt", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line or "Hisse" in line or "---" in line: continue
        parts = re.split(r'\s+', line)
        if len(parts) >= 3:
            raw_data.append({"Hisse": parts[0], "Temettü Tar": parts[1], "Verim": parts[2]})

hours_list = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
hourly_growth_factors = {h: [] for h in hours_list}

with open("day_before_data.txt", "w", encoding="utf-8") as f:
    # Başlık kısmına T-1 Açılış% eklendi
    header = f"{'Ticker':<10}{'Temettü Tar':<15}{'Verim':<10}{'T-2 Kapanış':<15}{'T-1 Açılış%':<15}"
    for hour in hours_list: header += f"{hour:<12}"
    f.write(header + "\n" + "-" * len(header) + "\n")
    
    for row in raw_data:
        ticker, t_date_str, verim = row["Hisse"], row["Temettü Tar"], row["Verim"]
        t_date = datetime.datetime.strptime(t_date_str, "%Y-%m-%d").date()
        yf_ticker = f"{ticker}.IS"
        
        # 1. İş günü tespiti
        stock_daily = yf.download(yf_ticker, start=t_date - datetime.timedelta(days=12), end=t_date, interval="1d", auto_adjust=False, progress=False)
        if len(stock_daily) < 2: continue
        
        trading_days = [d.tz_localize(None).date() for d in stock_daily.index]
        t1_day, t2_day = trading_days[-1], trading_days[-2]
        
        # 2. Saatlik veri çekimi
        stock_hourly = yf.download(yf_ticker, start=t2_day.strftime("%Y-%m-%d"), end=(t1_day + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), interval="1h", auto_adjust=False, progress=False)
        
        if stock_hourly.empty: continue
        
        if stock_hourly.index.tz is None:
            stock_hourly.index = stock_hourly.index.tz_localize('UTC')
        stock_hourly.index = stock_hourly.index.tz_convert(tr_tz)
        
        t2_data = stock_hourly[stock_hourly.index.date == t2_day]
        if t2_data.empty: continue
        t2_close = float(t2_data["Close"].iloc[-1].item() if hasattr(t2_data["Close"].iloc[-1], "item") else t2_data["Close"].iloc[-1])
        
        # T-1 Açılış hesaplaması
        t1_data = stock_hourly[stock_hourly.index.date == t1_day]
        t1_open_pct = 0.0
        if not t1_data.empty:
            t1_open_val = float(t1_data["Open"].iloc[0].item() if hasattr(t1_data["Open"].iloc[0], "item") else t1_data["Open"].iloc[0])
            t1_open_pct = ((t1_open_val - t2_close) / t2_close) * 100.0
        
        row_str = f"{ticker:<10}{t_date_str:<15}{verim:<10}{t2_close:<15.2f}{t1_open_pct:<+14.2f}% "
        
        last_known_price = t2_close 
        for hour in hours_list:
            target_hour = int(hour.split(":")[0])
            matched_row = t1_data[t1_data.index.hour == target_hour]
            
            if not matched_row.empty:
                val = matched_row["Close"].iloc[0]
                last_known_price = float(val.item() if hasattr(val, "item") else val)
            
            pct_change = ((last_known_price - t2_close) / t2_close) * 100.0
            row_str += f"{pct_change:+.2f}%".ljust(12)
            
            factor = 1.0 + (pct_change / 100.0)
            hourly_growth_factors[hour].append(max(factor, 0.0001))
                
        f.write(row_str.rstrip() + "\n")
        print(f"İşlendi: {ticker}")