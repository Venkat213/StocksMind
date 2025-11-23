import yfinance as yf
from datetime import datetime, timedelta

# Test TCS data accuracy
ticker = yf.Ticker('TCS.NS')

# Get 1 year data
hist_1y = ticker.history(period='1y')
print("=" * 60)
print("TCS 1 YEAR DATA ANALYSIS")
print("=" * 60)
print(f"\nTotal data points: {len(hist_1y)}")
print(f"\nFirst date: {hist_1y.index[0]}")
print(f"First close price: Rs.{hist_1y['Close'].iloc[0]:.2f}")
print(f"\nLast date: {hist_1y.index[-1]}")
print(f"Last close price: Rs.{hist_1y['Close'].iloc[-1]:.2f}")

change = hist_1y['Close'].iloc[-1] - hist_1y['Close'].iloc[0]
pct_change = (change / hist_1y['Close'].iloc[0]) * 100

print(f"\n1Y Change: Rs.{change:.2f}")
print(f"1Y % Change: {pct_change:.2f}%")
print("\n*** THIS IS INCORRECT - NOT EXACTLY 1 YEAR AGO ***")

# Also check exact 365 days ago
print("\n" + "=" * 60)
print("EXACT 365 DAYS AGO COMPARISON (CORRECT METHOD)")
print("=" * 60)

# Get 2 years of data to ensure we have data from 1 year ago
hist_2y = ticker.history(period='2y')
today = datetime.now()
one_year_ago = today - timedelta(days=365)

# Find closest date to exactly 1 year ago
closest_date = None
min_diff = timedelta(days=999)

for date in hist_2y.index:
    diff = abs(date.to_pydatetime().replace(tzinfo=None) - one_year_ago)
    if diff < min_diff:
        min_diff = diff
        closest_date = date

if closest_date:
    price_1y_ago = hist_2y.loc[closest_date, 'Close']
    current_price = hist_2y['Close'].iloc[-1]
    
    print(f"\nClosest date to 1 year ago: {closest_date}")
    print(f"Price 1 year ago: Rs.{price_1y_ago:.2f}")
    print(f"Current price: Rs.{current_price:.2f}")
    
    exact_change = current_price - price_1y_ago
    exact_pct = (exact_change / price_1y_ago) * 100
    
    print(f"\nExact 1Y Change: Rs.{exact_change:.2f}")
    print(f"Exact 1Y % Change: {exact_pct:.2f}%")
    print("\n*** THIS IS THE CORRECT CALCULATION ***")

# Show first and last 5 rows
print("\n" + "=" * 60)
print("FIRST 5 ROWS OF 1Y DATA")
print("=" * 60)
print(hist_1y.head())

print("\n" + "=" * 60)
print("LAST 5 ROWS OF 1Y DATA")
print("=" * 60)
print(hist_1y.tail())
