import yfinance as yf
import json

def check_news(symbol):
    print(f"Checking news for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news
        print(json.dumps(news, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_news("RELIANCE.NS")
    check_news("AAPL")
