import yfinance as yf
import pandas as pd
import numpy as np
import ta
from sklearn.ensemble import RandomForestClassifier
import streamlit as st

def fetch_news_sentiment(ticker):
    """
    Fetches recent news headlines for the ticker and calculates a simple sentiment score.
    Returns:
        sentiment_score (float): -1 to 1 (negative to positive)
        headlines (list): List of recent headlines
    """
    try:
        # Use yfinance news
        stock = yf.Ticker(ticker)
        news = stock.news
        
        # Fallback for Indian stocks if no news found directly
        if not news and ".NS" in ticker:
            stock_alt = yf.Ticker(ticker.replace(".NS", ""))
            news = stock_alt.news

        headlines = []
        sentiment_score = 0
        
        if news:
            for item in news[:5]: # Analyze top 5 news items
                title = item.get('title', '')
                # Handle nested content if present (some yf versions)
                if not title and 'content' in item:
                     title = item['content'].get('title', '')

                link = item.get('link', '')
                if not link and 'content' in item:
                    link = item['content'].get('clickThroughUrl', {}).get('url', '')
                elif not link and 'canonicalUrl' in item.get('content', {}):
                    link = item['content']['canonicalUrl'].get('url', '')

                if title:
                    headlines.append({"title": title, "link": link})
                    
                    # Very basic keyword sentiment (replace with NLP model for better results)
                    title_lower = title.lower()
                    if any(w in title_lower for w in ['surge', 'jump', 'gain', 'record', 'bull', 'buy', 'profit', 'growth', 'beat', 'strong']):
                        sentiment_score += 1
                    elif any(w in title_lower for w in ['drop', 'fall', 'loss', 'crash', 'bear', 'sell', 'miss', 'down', 'weak', 'risk']):
                        sentiment_score -= 1
            
            # Normalize score
            if headlines:
                sentiment_score = sentiment_score / len(headlines)
                
        return sentiment_score, headlines
    except Exception as e:
        print(f"News Error: {e}")
        return 0, []

def generate_reasoning(row):
    reasons = []
    
    # RSI
    if row['RSI'] < 30:
        reasons.append(f"RSI is oversold ({row['RSI']:.1f}), suggesting a potential bounce.")
    elif row['RSI'] > 70:
        reasons.append(f"RSI is overbought ({row['RSI']:.1f}), suggesting a potential pullback.")
    else:
        reasons.append(f"RSI is neutral ({row['RSI']:.1f}).")
        
    # MACD
    if row['MACD'] > row['MACD_Signal']:
        reasons.append("MACD is above the signal line (Bullish).")
    else:
        reasons.append("MACD is below the signal line (Bearish).")
        
    # SMA
    if row['Close'] > row['SMA_200']:
        reasons.append("Price is above the 200-day SMA (Long-term Bullish).")
    else:
        reasons.append("Price is below the 200-day SMA (Long-term Bearish).")
        
    # Bollinger Bands
    if row['Close'] < row['BB_Lower']:
        reasons.append("Price broke below Lower Bollinger Band (Potential Reversal/Oversold).")
    elif row['Close'] > row['BB_Upper']:
        reasons.append("Price broke above Upper Bollinger Band (Strong Momentum/Overbought).")
        
    return " ".join(reasons)

import gc

@st.cache_data(ttl=3600) # Cache for 1 hour
def predict_signal(ticker):
    try:
        # 1. Fetch Data (Reduced to 2 years for memory efficiency)
        stock = yf.Ticker(ticker)
        df = stock.history(period="2y")
        
        if len(df) < 200:
            return {"signal": "NEUTRAL", "confidence": 0, "reason": "Insufficient data for analysis.", "metrics": {}, "news": []}
        
        # 2. Feature Engineering
        # Trend Indicators
        df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
        df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
        df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
        df['MACD'] = ta.trend.macd(df['Close'])
        df['MACD_Signal'] = ta.trend.macd_signal(df['Close'])
        
        # Momentum Indicators
        df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
        df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)
        
        # Volatility Indicators
        df['BB_Upper'] = ta.volatility.bollinger_hband(df['Close'], window=20, window_dev=2)
        df['BB_Lower'] = ta.volatility.bollinger_lband(df['Close'], window=20, window_dev=2)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
        
        # Volume Indicators
        df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
        
        # Target: 1 if price rises in next 5 days, else 0
        df['Target'] = (df['Close'].shift(-5) > df['Close']).astype(int)
        
        # Drop NaNs
        df.dropna(inplace=True)
        
        # 3. Train Model (Random Forest) - Optimized for Memory
        features = ['RSI', 'MACD', 'MACD_Signal', 'SMA_50', 'SMA_200', 'EMA_20', 'Stoch_K', 'ATR', 'OBV']
        X = df[features]
        y = df['Target']
        
        # Train on all data except last 5 rows
        X_train = X.iloc[:-5]
        y_train = y.iloc[:-5]
        
        # Reduced estimators and depth to save memory
        model = RandomForestClassifier(n_estimators=30, max_depth=10, min_samples_split=10, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        # 4. Predict Current State
        latest_features = X.iloc[[-1]]
        rf_probability = model.predict_proba(latest_features)[0][1] # Probability of Class 1 (Buy)
        
        # 5. Get News Sentiment
        sentiment_score, headlines = fetch_news_sentiment(ticker)
        
        # Integrate News
        sentiment_adjustment = np.clip(sentiment_score * 0.1, -0.2, 0.2)
        final_probability = np.clip(rf_probability + sentiment_adjustment, 0, 1)
        
        # Determine Signal
        if final_probability > 0.70:
            signal = "STRONG BUY"
        elif final_probability > 0.55:
            signal = "BUY"
        elif final_probability < 0.30:
            signal = "STRONG SELL"
        elif final_probability < 0.45:
            signal = "SELL"
        else:
            signal = "HOLD"
            
        # Generate Reasoning
        latest_row = df.iloc[-1]
        reason = generate_reasoning(latest_row)
        reason += f"\n\n🤖 **Model Confidence:** {final_probability:.1%} (Technical: {rf_probability:.1%}, News Adj: {sentiment_adjustment:+.1%})"
        
        if sentiment_score != 0:
            sentiment_str = "Bullish" if sentiment_score > 0 else "Bearish"
            reason += f"\n📰 **News Sentiment:** {sentiment_str} (Score: {sentiment_score})"
        elif not headlines:
             reason += f"\n📰 **News:** No recent news found."
        
        # Cleanup
        del df, X, y, X_train, y_train, model
        gc.collect()
            
        return {
            "signal": signal,
            "confidence": final_probability * 100,
            "reason": reason,
            "metrics": {
                "RSI": latest_row["RSI"],
                "MACD": latest_row["MACD"],
                "SMA_200": latest_row["SMA_200"],
                "Close": latest_row["Close"]
            },
            "news": headlines
        }
        
    except Exception as e:
        return {"signal": "ERROR", "confidence": 0, "reason": str(e), "metrics": {}, "news": []}
