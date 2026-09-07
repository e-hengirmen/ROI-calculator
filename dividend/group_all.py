import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import warnings

# Uyarıları kapat
warnings.filterwarnings('ignore')

# 1. Veri Okuma (Dosyanızın formatına göre güncellendi)
def read_input(file_path):
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "Hisse" in line or "---" in line: continue
            parts = line.split()
            # Örn: NUHCM 2025-01-06 %0.81
            if len(parts) >= 3:
                data.append({"Ticker": parts[0], "Date": parts[1], "Yield": parts[2]})
    return data

# 2. İşlem
input_file = "processed_data.txt" # Kendi dosya isminizi buraya yazın
raw_data = read_input(input_file)
hours_to_track = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"]

with open("day_before_data.txt", "w", encoding="utf-8") as f:
    # Başlıklar
    header = f"{'Ticker':<10}{'Tarih':<15}{'Verim':<10}{'T-2 Close':<12}" + "".join([f"{h:<10}" for h in hours_to_track])
    f.write(header + "\n" + "-" * len(header) + "\n")
    
    # Geometrik ortalama tutucu
    geo_data = {h: [] for h in hours_to_track}

    for row in raw_data:
        ticker = row["Ticker"]
        t_date = pd.to_datetime(row["Date"])
        
        # T-2 ve T-1 tarihlerini bul
        start_date = t_date - pd.Timedelta(days=7)
        daily = yf.download(f"{ticker}.IS", start=start_date, end=t_date, interval="1d", progress=False)
        if len(daily) < 2: continue
        
        t1_date = daily.index[-1]
        t2_date = daily.index[-2]
        t2_close = float(daily["Close"].iloc[-1])
        
        # Saatlik veriyi çek
        hourly = yf.download(f"{ticker}.IS", start=t2_date, end=t1_date + pd.Timedelta(days=1), interval="1h", progress=False)
        hourly.index = hourly.index.tz_convert('Europe/Istanbul')
        t1_hourly = hourly[hourly.index.date == t1_date.date()]
        
        # Satır verisi oluştur
        row_str = f"{ticker:<10}{row['Date']:<15}{row['Yield']:<10}{t2_close:<12.2f}"
        
        for h_str in hours_to_track:
            h_int = int(h_str.split(":")[0])
            
            # 18:00 için Daily Close kullan (Forward fill değil, resmi kapanış)
            if h_int == 18:
                price = float(daily["Close"].iloc[-1]) # T-1 Günlük Kapanış
            else:
                # O saate ait barı bul
                bars = t1_hourly[t1_hourly.index.hour == h_int]
                if not bars.empty:
                    price = float(bars["Close"].iloc[-1])
                else:
                    price = np.nan # Veri yoksa nan kalsın (Forward fill yapmıyoruz)
            
            if not np.isnan(price):
                change = ((price - t2_close) / t2_close) * 100
                row_str += f"{change:+.2f}%".ljust(10)
                geo_data[h_str].append(1 + (change / 100))
            else:
                row_str += f"{'N/A':<10}"
        
        f.write(row_str + "\n")
        print(f"İşlendi: {ticker}")

    # Geometrik Ortalama Satırı
    geo_str = f"{'G.Mean':<10}{'':<15}{'':<10}{'':<12}"
    for h in hours_to_track:
        if geo_data[h]:
            gm = (np.prod(geo_data[h]) ** (1.0 / len(geo_data[h])) - 1) * 100
            geo_str += f"{gm:+.2f}%".ljust(10)
        else:
            geo_str += f"{'N/A':<10}"
    f.write("-" * len(header) + "\n" + geo_str + "\n")

print("day_before_data.txt başarıyla oluşturuldu!")