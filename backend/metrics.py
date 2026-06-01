import numpy as np
import pandas as pd
from typing import Dict, Any, List

def calculate_metrics(portfolio_values: pd.Series, trades: List[Dict[str, Any]], risk_free_rate: float = 0.0) -> Dict[str, Any]:
    """
    Calculate standard quantitative portfolio performance metrics.
    
    Parameters:
    - portfolio_values (pd.Series): Daily equity curve Series indexed by Datetime.
    - trades (List[Dict]): List of executed trade records. Each trade contains:
      {'type': 'BUY'/'SELL', 'price': float, 'qty': float, 'date': Timestamp, 'pnl': float, 'return': float}
    - risk_free_rate (float): Annualized risk-free rate (e.g. 0.02 for 2%).
    
    Returns:
    - Dict[str, Any]: Dictionary containing all performance metrics.
    """
    if portfolio_values.empty:
        return {}
        
    initial_val = portfolio_values.iloc[0]
    final_val = portfolio_values.iloc[-1]
    
    # 1. Total Return
    total_return = (final_val - initial_val) / initial_val if initial_val != 0 else 0.0
    
    # 2. Time-based calculations for CAGR
    start_date = portfolio_values.index[0]
    end_date = portfolio_values.index[-1]
    days = (end_date - start_date).days
    years = max(days / 365.25, 1 / 365.25) # avoid division by zero
    
    cagr = (final_val / initial_val) ** (1.0 / years) - 1.0 if initial_val > 0 and final_val > 0 else 0.0
    
    # Daily returns for Sharpe and Volatility
    daily_returns = portfolio_values.pct_change().dropna()
    
    # 3. Annualized Volatility (assuming daily data, 252 trading days)
    ann_vol = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0.0
    
    # 4. Sharpe Ratio (using risk-free rate adjusted to daily)
    daily_rf = risk_free_rate / 252
    excess_returns = daily_returns - daily_rf
    sharpe = (excess_returns.mean() / daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 and len(daily_returns) > 1 else 0.0
    
    # 5. Sortino Ratio (only downside volatility)
    downside_returns = daily_returns[daily_returns < daily_rf]
    downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 1 else 0.0
    sortino = (excess_returns.mean() / downside_returns.std() * np.sqrt(252)) if downside_vol > 0 and len(daily_returns) > 1 else 0.0
    
    # 6. Maximum Drawdown & Drawdown Duration
    peaks = portfolio_values.cummax()
    drawdowns = (portfolio_values - peaks) / peaks
    max_drawdown = drawdowns.min() if not drawdowns.empty else 0.0
    
    # Max Drawdown Duration
    # Find the duration of drawdown periods (in days)
    is_in_drawdown = drawdowns < 0
    drawdown_durations = []
    current_duration = 0
    
    # Compute durations
    for val in is_in_drawdown:
        if val:
            current_duration += 1
        else:
            if current_duration > 0:
                drawdown_durations.append(current_duration)
                current_duration = 0
    if current_duration > 0:
        drawdown_durations.append(current_duration)
        
    max_drawdown_duration = max(drawdown_durations) if drawdown_durations else 0
    
    # 7-10. Trade Analysis
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    
    gross_profits = sum(t.get('pnl', 0) for t in winning_trades)
    gross_losses = sum(t.get('pnl', 0) for t in losing_trades) # negative or positive depending on sign
    
    # Normalize gross losses to positive for profit factor
    abs_gross_losses = abs(gross_losses)
    profit_factor = gross_profits / abs_gross_losses if abs_gross_losses > 0 else (float('inf') if gross_profits > 0 else 1.0)
    
    avg_trade_pnl = np.mean([t.get('pnl', 0) for t in trades]) if total_trades > 0 else 0.0
    avg_trade_return = np.mean([t.get('return', 0) for t in trades]) if total_trades > 0 else 0.0
    
    # Create equity curve list for graphing
    equity_curve = [{"date": str(date.date()), "value": float(val)} for date, val in portfolio_values.items()]
    
    # Create drawdown curve for graphing
    drawdown_curve = [{"date": str(date.date()), "value": float(val)} for date, val in drawdowns.items()]
    
    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "annualized_volatility": float(ann_vol),
        "sharpe_ratio": float(sharpe),
        "sortino_ratio": float(sortino),
        "max_drawdown": float(max_drawdown),
        "max_drawdown_duration_days": int(max_drawdown_duration),
        "total_trades": int(total_trades),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor) if np.isfinite(profit_factor) else "N/A",
        "average_trade_pnl": float(avg_trade_pnl),
        "average_trade_return": float(avg_trade_return),
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve
    }
