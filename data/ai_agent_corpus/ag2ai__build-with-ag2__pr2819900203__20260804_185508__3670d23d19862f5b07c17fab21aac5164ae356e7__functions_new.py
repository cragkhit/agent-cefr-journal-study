import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def retrieve_stock_data(ticker: str, days: int = 30) -> tuple[float, float]:
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    data = yf.download(ticker, start=start_date, end=end_date)
    current_price = data['Close'].iloc[-1]
    start_price = data['Close'].iloc[0]
    percent_change = ((current_price - start_price) / start_price) * 100
    return current_price, percent_change

def plot_stock_comparison(tickers: list[str], days: int = 30) -> str:
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    
    plt.figure(figsize=(12, 6))
    for ticker in tickers:
        data = yf.download(ticker, start=start_date, end=end_date)
        normalized_price = data['Close'] / data['Close'].iloc[0] * 100
        plt.plot(data.index, normalized_price, label=ticker)
    
    plt.title('Stock Price Performance Comparison')
    plt.xlabel('Date')
    plt.ylabel('Normalized Price (%)')
    plt.legend()
    plt.grid(True)
    
    filename = 'stock_comparison.png'
    plt.savefig(filename)
    plt.close()
    return filename

def analyze_market_data(ticker: str, days: int = 30) -> dict:
    data = yf.download(ticker, start=datetime.today()-timedelta(days=days), end=datetime.today())
    return {
        'avg_volume': data['Volume'].mean(),
        'volatility': data['Close'].pct_change().std() * 100,
        'high': data['High'].max(),
        'low': data['Low'].min(),
        'trading_days': len(data)
    }
