import pandas as pd
import yfinance as yf
import os
from typing import Optional, Dict, Any, List

# Recommended popular tickers for user quick-start
POPULAR_SYMBOLS = [
    {"symbol": "SPY", "name": "S&P 500 ETF Trust", "type": "Index ETF"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust (Nasdaq 100)", "type": "Index ETF"},
    {"symbol": "AAPL", "name": "Apple Inc.", "type": "Stock"},
    {"symbol": "TSLA", "name": "Tesla, Inc.", "type": "Stock"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "Stock"},
    {"symbol": "BTC-USD", "name": "Bitcoin USD", "type": "Crypto"},
    {"symbol": "ETH-USD", "name": "Ethereum USD", "type": "Crypto"},
    {"symbol": "GLD", "name": "SPDR Gold Shares", "type": "Commodity ETF"}
]

def fetch_yfinance_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch historical OHLCV data from Yahoo Finance.
    
    Parameters:
    - symbol (str): Ticker symbol.
    - start_date (str): Start date string (YYYY-MM-DD).
    - end_date (str): End date string (YYYY-MM-DD).
    
    Returns:
    - pd.DataFrame: Cleaned OHLCV DataFrame with DatetimeIndex.
    """
    try:
        # Download data
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            raise ValueError(f"No data returned for ticker {symbol}")
            
        # Standardize columns
        df = df.copy()
        
        # yfinance can return multi-index columns for some tickers under newer versions, flatten them
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Clean column names to standard Capitalized
        df.columns = [col.strip().capitalize() for col in df.columns]
        
        # Validate columns
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required OHLCV column: {col}")
                
        # Clean up columns and ensure floats
        for col in required:
            df[col] = df[col].astype(float)
            
        # Ensure Datetime index is sorted
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        return df[required]
        
    except Exception as e:
        raise ValueError(f"Failed to fetch data for {symbol} from Yahoo Finance: {str(e)}")

def parse_custom_csv(file_path: str) -> pd.DataFrame:
    """
    Parse a custom uploaded CSV file containing OHLCV data.
    
    Parameters:
    - file_path (str): Absolute path to the CSV file.
    
    Returns:
    - pd.DataFrame: Cleaned standard OHLCV DataFrame.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"CSV file not found: {file_path}")
        
    try:
        # Load the CSV
        df = pd.read_csv(file_path)
        
        # Case insensitive mapping of columns
        col_mapping = {}
        for col in df.columns:
            cleaned = col.strip().lower()
            if 'date' in cleaned or 'time' in cleaned:
                col_mapping[col] = 'Date'
            elif 'open' in cleaned:
                col_mapping[col] = 'Open'
            elif 'high' in cleaned:
                col_mapping[col] = 'High'
            elif 'low' in cleaned:
                col_mapping[col] = 'Low'
            elif 'close' in cleaned:
                col_mapping[col] = 'Close'
            elif 'volume' in cleaned or 'vol' in cleaned:
                col_mapping[col] = 'Volume'
                
        df = df.rename(columns=col_mapping)
        
        # Check required columns
        required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"CSV file missing required column or matches: {col}. Identified columns: {list(df.columns)}")
                
        # Convert Date and set as Index
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date')
        
        # Convert price/volume columns to float
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            # Strip any currency signs or commas if present
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(r'[^\d\.]', '', regex=True)
            df[col] = df[col].astype(float)
            
        # Sort and clean index
        df = df.sort_index()
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
    except Exception as e:
        raise ValueError(f"Failed to parse custom CSV file: {str(e)}")
