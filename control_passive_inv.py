import pandas as pd
import yfinance as yf
from datetime import datetime
from dateutil.relativedelta import relativedelta

def analyze_investment_strategies(
    ticker_symbol: str = "^GSPC",  # ^GSPC is the S&P 500 Index. You can use 'VOO', 'SPY', 'QQQ', 'AAPL', etc.
    total_amount: float = 12000.0,
    years_ago: int = 5
):
    """
    Compares two investment scenarios:
    1. Lump-Sum: Invest total_amount all at once 'years_ago' years ago.
    2. Dollar-Cost Averaging (DCA): Divide total_amount across (years_ago * 12) equal monthly investments.
    """
    # 1. Calculate Date Range
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=years_ago)
    
    print(f"Fetching data for {ticker_symbol} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...\n")
    
    # 2. Fetch Historical Stock/ETF Data
    data = yf.download(ticker_symbol, start=start_date, end=end_date, interval="1mo", progress=False)
    
    if data.empty:
        raise ValueError("No historical data found for the specified ticker and date range.")
    
    # Flatten multi-index columns if present (common in newer yfinance versions)
    if isinstance(data.columns, pd.MultiIndex):
        df = data['Close'].copy()
    else:
        df = data[['Close']].copy()
        
    df = df.dropna()
    
    # Extract monthly closing prices
    closing_prices = df.iloc[:, 0]
    current_price = float(closing_prices.iloc[-1])
    initial_price = float(closing_prices.iloc[0])
    
    # -------------------------------------------------------------
    # Scenario 1: Lump-Sum Investment
    # -------------------------------------------------------------
    lump_shares = total_amount / initial_price
    lump_final_value = lump_shares * current_price
    lump_profit = lump_final_value - total_amount
    lump_return_pct = (lump_profit / total_amount) * 100

    # -------------------------------------------------------------
    # Scenario 2: Monthly Dollar-Cost Averaging (DCA)
    # -------------------------------------------------------------
    total_months = len(closing_prices)
    monthly_investment = total_amount / total_months
    
    dca_total_shares = 0.0
    for price in closing_prices:
        dca_total_shares += monthly_investment / price
        
    dca_final_value = dca_total_shares * current_price
    dca_profit = dca_final_value - total_amount
    dca_return_pct = (dca_profit / total_amount) * 100

    # -------------------------------------------------------------
    # Display Results
    # -------------------------------------------------------------
    print("=" * 55)
    print(f" INVESTMENT ANALYSIS RESULT: {ticker_symbol}")
    print(f" Period: {years_ago} Years ({total_months} months)")
    print(f" Total Principal Invested: ${total_amount:,.2f}")
    print("=" * 55)
    
    print(f"\n--- SCENARIO 1: Lump-Sum Investment ---")
    print(f"Initial Share Price:     ${initial_price:,.2f}")
    print(f"Shares Purchased:        {lump_shares:.4f}")
    print(f"Current Value:           ${lump_final_value:,.2f}")
    print(f"Total Profit/Loss:       ${lump_profit:,.2f} ({lump_return_pct:+.2f}%)")
    
    print(f"\n--- SCENARIO 2: Monthly DCA Investment ---")
    print(f"Monthly Installment:     ${monthly_investment:,.2f} / month")
    print(f"Total Shares Accumulated: {dca_total_shares:.4f}")
    print(f"Current Value:           ${dca_final_value:,.2f}")
    print(f"Total Profit/Loss:       ${dca_profit:,.2f} ({dca_return_pct:+.2f}%)")
    
    print("\n" + "=" * 55)
    if lump_final_value > dca_final_value:
        diff = lump_final_value - dca_final_value
        print(f"OUTCOME: Lump-Sum outperformed DCA by ${diff:,.2f}")
    else:
        diff = dca_final_value - lump_final_value
        print(f"OUTCOME: Monthly DCA outperformed Lump-Sum by ${diff:,.2f}")
    print("=" * 55 + "\n")

# --- Example Usage ---
if __name__ == "__main__":
    # You can change these parameters as needed:
    TICKER = "VOO"         # Vanguard S&P 500 ETF (or "^GSPC", "QQQ", "MSFT", etc.)
    AMOUNT = 12000.0       # Total money invested ($12,000)
    YEARS = 40              # 5 years ago

    analyze_investment_strategies(
        ticker_symbol=TICKER,
        total_amount=AMOUNT,
        years_ago=YEARS
    )