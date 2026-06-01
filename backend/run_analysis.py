import sys
import os
import pandas as pd
import numpy as np

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data import fetch_yfinance_data
from backend.strategies import STRATEGY_MAP
from backend.engine import BacktestEngine

def run_comparative_analysis():
    print("=" * 70)
    print("     QUANTITATIVE BACKTEST COMPARATIVE ANALYSIS RUNNER")
    print("=" * 70)
    
    # 1. Configuration
    assets = [
        {"symbol": "SPY", "name": "S&P 500 Index ETF (Equities)"},
        {"symbol": "QQQ", "name": "Nasdaq 100 Index ETF (Growth/Tech)"},
        {"symbol": "TSLA", "name": "Tesla Inc. (High-Beta Stock)"},
        {"symbol": "BTC-USD", "name": "Bitcoin USD (Crypto Asset)"}
    ]
    
    start_date = "2020-01-01"
    end_date = "2025-01-01"
    initial_cash = 10000.0
    
    # Default parameters matching backend
    strategy_configs = {
        "vls": {
            "strategy_class": STRATEGY_MAP["vls"],
            "params": {"bb_period": 20, "bb_std": 2.0, "kc_period": 20, "kc_atr": 1.5, "volume_period": 20}
        },
        "sma": {
            "strategy_class": STRATEGY_MAP["sma"],
            "params": {"fast_period": 20, "slow_period": 50}
        },
        "rsi": {
            "strategy_class": STRATEGY_MAP["rsi"],
            "params": {"period": 14, "oversold": 30, "overbought": 70}
        }
    }
    
    results = {}
    
    # 2. Execute Backtests
    for asset in assets:
        symbol = asset["symbol"]
        print(f"\n[*] Fetching and processing data for {symbol} ({start_date} to {end_date})...")
        try:
            data = fetch_yfinance_data(symbol, start_date, end_date)
        except Exception as e:
            print(f"[x] Error downloading {symbol}: {str(e)}")
            continue
            
        results[symbol] = {}
        
        # Benchmarks: Buy & Hold
        bench_ret = (data["Close"].iloc[-1] - data["Close"].iloc[0]) / data["Close"].iloc[0]
        days = (data.index[-1] - data.index[0]).days
        years = max(days / 365.25, 0.1)
        bench_cagr = (data["Close"].iloc[-1] / data["Close"].iloc[0]) ** (1.0 / years) - 1.0
        
        # Calculate daily drawdown for benchmark max drawdown
        bench_peaks = data["Close"].cummax()
        bench_drawdowns = (data["Close"] - bench_peaks) / bench_peaks
        bench_max_dd = bench_drawdowns.min()
        
        results[symbol]["Benchmark"] = {
            "total_return": float(bench_ret),
            "cagr": float(bench_cagr),
            "sharpe_ratio": 0.0, # approximation
            "max_drawdown": float(bench_max_dd),
            "win_rate": 0.0,
            "total_trades": 1
        }
        
        for name, config in strategy_configs.items():
            print(f"  [-] Running {name.upper()} backtest...")
            try:
                engine = BacktestEngine(
                    data=data,
                    strategy_class=config["strategy_class"],
                    strategy_params=config["params"],
                    initial_cash=initial_cash,
                    commission_rate=0.0015, # 0.15% standard
                    slippage_rate=0.0005     # 0.05% standard
                )
                res = engine.run()
                metrics = res["metrics"]
                
                results[symbol][name.upper()] = {
                    "total_return": metrics["total_return"],
                    "cagr": metrics["cagr"],
                    "sharpe_ratio": metrics["sharpe_ratio"],
                    "max_drawdown": metrics["max_drawdown"],
                    "win_rate": metrics["win_rate"],
                    "total_trades": metrics["total_trades"]
                }
            except Exception as e:
                print(f"  [x] Error running backtest: {str(e)}")
                continue
                
    # 3. Print Summary Table
    print("\n" + "="*80)
    print("                      COMPARATIVE RESULTS SUMMARY")
    print("="*80)
    print(f"{'Asset':<10} | {'Strategy':<10} | {'Total Return':<12} | {'CAGR':<10} | {'Sharpe':<8} | {'Max DD':<10} | {'Trades':<6}")
    print("-" * 80)
    
    for symbol, strats in results.items():
        for strat_name, stats in strats.items():
            tr = f"{stats['total_return']*100:+.2f}%"
            cagr = f"{stats['cagr']*100:+.2f}%"
            sharpe = f"{stats['sharpe_ratio']:.2f}" if strat_name != "Benchmark" else "N/A"
            mdd = f"{stats['max_drawdown']*100:.2f}%"
            trades = stats['total_trades']
            print(f"{symbol:<10} | {strat_name:<10} | {tr:<12} | {cagr:<10} | {sharpe:<8} | {mdd:<10} | {trades:<6}")
        print("-" * 80)

if __name__ == "__main__":
    run_comparative_analysis()
