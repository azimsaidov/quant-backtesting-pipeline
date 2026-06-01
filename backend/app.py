import os
import shutil
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import json

from backend.data import POPULAR_SYMBOLS, fetch_yfinance_data, parse_custom_csv
from backend.strategies import STRATEGY_MAP, get_strategy_definitions
from backend.engine import BacktestEngine

app = FastAPI(
    title="Quantitative Backtesting API",
    description="Backend API serving high-fidelity financial analytics and strategy backtests."
)

# Enable CORS for frontend cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for local execution
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create an uploads folder if it doesn't exist
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class BacktestRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol or 'csv_upload:<filename>' for uploaded datasets")
    strategy_id: str = Field(..., description="ID of the strategy to run (vls, sma, rsi)")
    start_date: str = Field("2020-01-01", description="Backtest start date")
    end_date: str = Field("2023-01-01", description="Backtest end date")
    initial_cash: float = Field(10000.0, description="Starting cash capital")
    commission_rate: float = Field(0.0015, description="Percentage transaction commission (e.g. 0.0015 for 0.15%)")
    slippage_rate: float = Field(0.0005, description="Percentage execution slippage (e.g. 0.0005 for 0.05%)")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="Hyperparameters for strategy indicators")

@app.get("/api/symbols")
def get_symbols():
    """
    Get recommended stock/crypto tickers for testing.
    """
    return POPULAR_SYMBOLS

@app.get("/api/strategies")
def get_strategies():
    """
    Get supported strategies and parameter definitions.
    """
    return get_strategy_definitions()

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a custom historical CSV data file.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")
        
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    try:
        # Save file to upload directory
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Parse it to validate format
        df = parse_custom_csv(file_path)
        
        # Extract metadata
        record_count = len(df)
        min_date = str(df.index.min().date())
        max_date = str(df.index.max().date())
        
        return {
            "success": True,
            "filename": file.filename,
            "symbol_key": f"csv_upload:{file.filename}",
            "records": record_count,
            "start_date": min_date,
            "end_date": max_date
        }
    except Exception as e:
        # Clean up corrupted file if save failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    """
    Execute a backtest.
    """
    # 1. Resolve strategy
    if req.strategy_id not in STRATEGY_MAP:
        raise HTTPException(status_code=404, detail=f"Strategy '{req.strategy_id}' not found.")
        
    strategy_class = STRATEGY_MAP[req.strategy_id]
    
    # 2. Resolve and load data
    try:
        if req.ticker.startswith("csv_upload:"):
            # Load custom csv
            filename = req.ticker.split(":", 1)[1]
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"Uploaded dataset '{filename}' not found. Please upload again.")
                
            full_data = parse_custom_csv(file_path)
            
            # Slice date range if applicable
            start_ts = pd.to_datetime(req.start_date)
            end_ts = pd.to_datetime(req.end_date)
            
            data = full_data.loc[start_ts:end_ts]
            if data.empty:
                raise ValueError(f"No custom CSV data records found inside date range {req.start_date} to {req.end_date}. Full data bounds: {full_data.index.min().date()} to {full_data.index.max().date()}")
        else:
            # Fetch from Yahoo Finance
            data = fetch_yfinance_data(req.ticker, req.start_date, req.end_date)
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # 3. Instantiate and run backtest engine
    try:
        engine = BacktestEngine(
            data=data,
            strategy_class=strategy_class,
            strategy_params=req.strategy_params,
            initial_cash=req.initial_cash,
            commission_rate=req.commission_rate,
            slippage_rate=req.slippage_rate
        )
        results = engine.run()
        
        # Clean up any potential float NaNs or Infs recursively before returning JSON
        import numpy as np
        def sanitize_floats(obj):
            if isinstance(obj, dict):
                return {k: sanitize_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_floats(v) for v in obj]
            elif isinstance(obj, float):
                if np.isnan(obj) or np.isinf(obj):
                    return None
                return obj
            elif isinstance(obj, np.floating):
                val = float(obj)
                if np.isnan(val) or np.isinf(val):
                    return None
                return val
            elif isinstance(obj, np.integer):
                return int(obj)
            return obj
            
        return sanitize_floats(results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest execution engine error: {str(e)}")

# Mount static frontend files to serve single-port full-stack app
from fastapi.staticfiles import StaticFiles
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
