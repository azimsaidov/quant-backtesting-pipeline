import sys
import os
import pandas as pd
import numpy as np

# Ensure root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.strategies import STRATEGY_MAP
from backend.engine import BacktestEngine
from backend.metrics import calculate_metrics

def generate_synthetic_data() -> pd.DataFrame:
    """
    Generate synthetic stock price and volume dataset.
    """
    print("[*] Generating synthetic OHLCV data for testing...")
    np.random.seed(42)
    dates = pd.date_range(start="2022-01-01", periods=100, freq="D")
    
    # Simple sine wave trend for price
    close = 100.0 + np.sin(np.linspace(0, 4 * np.pi, 100)) * 10.0 + np.random.normal(0, 0.5, 100)
    open_prices = close - np.random.uniform(-1.0, 1.0, 100)
    high = np.maximum(open_prices, close) + np.random.uniform(0.1, 1.0, 100)
    low = np.minimum(open_prices, close) - np.random.uniform(0.1, 1.0, 100)
    
    # Volume: low initially (squeeze), then spike (breakout)
    volume = np.random.uniform(50000, 80000, 100)
    volume[40:50] = volume[40:50] * 0.3  # squeeze
    volume[51:55] = volume[51:55] * 3.0  # volume spike breakout
    
    df = pd.DataFrame({
        "Open": open_prices,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume
    }, index=dates)
    
    return df

def test_metrics():
    print("\n=== TESTING METRICS MODULE ===")
    dates = pd.date_range(start="2022-01-01", periods=5, freq="D")
    portfolio_values = pd.Series([10000, 10100, 9900, 10300, 10400], index=dates)
    
    trades = [
        {"trade_id": 1, "type": "SELL", "date": "2022-01-03", "price": 101.0, "qty": 100.0, "commission": 1.5, "pnl": 100.0, "return": 0.01}
    ]
    
    res = calculate_metrics(portfolio_values, trades)
    assert res is not None
    assert "total_return" in res
    assert "sharpe_ratio" in res
    assert "max_drawdown" in res
    assert res["total_trades"] == 1
    print("[+] Metrics calculations test passed.")

def test_engine_strategies():
    print("\n=== TESTING STRATEGIES & ENGINE ===")
    df = generate_synthetic_data()
    
    # 1. Test Volatility-Liquidity Squeeze Strategy
    print("[*] Running VLS Strategy backtest...")
    engine_vls = BacktestEngine(
        data=df,
        strategy_class=STRATEGY_MAP["vls"],
        strategy_params={"bb_period": 10, "bb_std": 1.5, "kc_period": 10, "kc_atr": 1.0, "volume_period": 10},
        initial_cash=10000.0
    )
    res_vls = engine_vls.run()
    assert res_vls is not None
    assert "metrics" in res_vls
    assert "trades" in res_vls
    assert "indicators" in res_vls
    print(f"[+] VLS backtest complete. Total trades: {res_vls['metrics']['total_trades']}. Total return: {res_vls['metrics']['total_return'] * 100:.2f}%")
    
    # 2. Test SMA Strategy
    print("[*] Running SMA Crossover backtest...")
    engine_sma = BacktestEngine(
        data=df,
        strategy_class=STRATEGY_MAP["sma"],
        strategy_params={"fast_period": 5, "slow_period": 15},
        initial_cash=10000.0
    )
    res_sma = engine_sma.run()
    assert res_sma is not None
    print(f"[+] SMA backtest complete. Total trades: {res_sma['metrics']['total_trades']}. Total return: {res_sma['metrics']['total_return'] * 100:.2f}%")

if __name__ == "__main__":
    try:
        test_metrics()
        test_engine_strategies()
        print("\n[+++] ALL ENGINE INTEGRATION TESTS PASSED SUCCESSFULLY! [+++]")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"\n[x] Test validation failed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
