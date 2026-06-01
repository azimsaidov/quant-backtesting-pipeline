import pandas as pd
import numpy as np
from typing import Dict, Any, List, Type
from backend.strategies import BaseStrategy
from backend.metrics import calculate_metrics

class BacktestEngine:
    """
    Modular Event-Driven Backtesting Engine.
    Simulates sequential trade execution, commissions, slippage, and portfolio equity tracking.
    """
    def __init__(
        self,
        data: pd.DataFrame,
        strategy_class: Type[BaseStrategy],
        strategy_params: Dict[str, Any],
        initial_cash: float = 10000.0,
        commission_rate: float = 0.0015, # 0.15% per trade
        slippage_rate: float = 0.0005,    # 0.05% price slippage
        risk_free_rate: float = 0.0       # 0% standard risk free rate
    ):
        self.data = data.copy()
        self.strategy_class = strategy_class
        self.strategy_params = strategy_params
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.risk_free_rate = risk_free_rate
        
        # Reset state variables
        self.cash = initial_cash
        self.holdings = 0.0
        self.trades_history: List[Dict[str, Any]] = []
        self.portfolio_history: List[float] = []
        self.dates_history: List[pd.Timestamp] = []
        
    def run(self) -> Dict[str, Any]:
        """
        Execute backtest bar-by-bar sequentially.
        
        Returns:
        - Dict[str, Any]: Combined results containing trade logs, indicators, and metrics.
        """
        # Instantiate strategy
        strategy = self.strategy_class(self.data, self.strategy_params)
        
        trade_id_counter = 1
        active_buy_trade: Dict[str, Any] = {}
        
        # Walk through the dataset chronologically bar-by-bar
        for idx in range(len(self.data)):
            date = self.data.index[idx]
            row = self.data.iloc[idx]
            close = float(row["Close"])
            
            # Fetch signal from strategy
            signal = strategy.next(idx, date, row)
            
            # Execute trades
            if signal == "BUY" and self.holdings == 0.0:
                # Buy at close price + slippage
                exec_price = close * (1.0 + self.slippage_rate)
                # Compute maximum quantity we can purchase including commission
                # cash = qty * exec_price * (1 + commission_rate)
                qty = self.cash / (exec_price * (1.0 + self.commission_rate))
                
                if qty > 0.00001: # Avoid fractional noise
                    buy_cost = qty * exec_price
                    commission = buy_cost * self.commission_rate
                    self.cash -= (buy_cost + commission)
                    self.holdings = qty
                    
                    active_buy_trade = {
                        "trade_id": trade_id_counter,
                        "type": "BUY",
                        "date": str(date.date()),
                        "price": float(exec_price),
                        "qty": float(qty),
                        "commission": float(commission),
                        "pnl": 0.0,
                        "return": 0.0,
                        "cash_after": float(self.cash),
                        "portfolio_value_after": float(self.cash + self.holdings * close)
                    }
                    self.trades_history.append(active_buy_trade)
                    trade_id_counter += 1
                    
            elif signal == "SELL" and self.holdings > 0.0:
                # Sell at close price - slippage
                exec_price = close * (1.0 - self.slippage_rate)
                qty = self.holdings
                gross_value = qty * exec_price
                commission = gross_value * self.commission_rate
                net_proceeds = gross_value - commission
                
                self.cash += net_proceeds
                self.holdings = 0.0
                
                # Calculate trade performance from matching active buy
                buy_price = active_buy_trade["price"]
                buy_comm = active_buy_trade["commission"]
                
                # PnL = Proceeds - (Initial cost + Entry commission)
                pnl = net_proceeds - (buy_price * qty + buy_comm)
                trade_return = pnl / (buy_price * qty + buy_comm) if (buy_price * qty + buy_comm) > 0 else 0.0
                
                sell_trade = {
                    "trade_id": active_buy_trade["trade_id"], # Link to buy trade
                    "type": "SELL",
                    "date": str(date.date()),
                    "price": float(exec_price),
                    "qty": float(qty),
                    "commission": float(commission),
                    "pnl": float(pnl),
                    "return": float(trade_return),
                    "cash_after": float(self.cash),
                    "portfolio_value_after": float(self.cash)
                }
                self.trades_history.append(sell_trade)
                
                # Update corresponding entry PnL in log history for full roundtrip tracking
                for t in self.trades_history:
                    if t["trade_id"] == active_buy_trade["trade_id"] and t["type"] == "BUY":
                        t["pnl"] = float(pnl)
                        t["return"] = float(trade_return)
                        break
                        
                active_buy_trade = {}
                
            # Track daily equity value
            current_portfolio_value = self.cash + (self.holdings * close)
            self.portfolio_history.append(current_portfolio_value)
            self.dates_history.append(date)
            
        # Convert histories to pandas for stats module
        portfolio_series = pd.Series(self.portfolio_history, index=self.dates_history)
        
        # Filter completed roundtrip trades for accurate win rate/profit factor
        roundtrip_trades = [t for t in self.trades_history if t["type"] == "SELL"]
        
        # Calculate full quantitative metrics
        metrics = calculate_metrics(portfolio_series, roundtrip_trades, self.risk_free_rate)
        
        # Benchmark curve (Buy and Hold)
        initial_price = float(self.data["Close"].iloc[0])
        benchmark_values = (self.data["Close"] / initial_price) * self.initial_cash
        benchmark_curve = [{"date": str(date.date()), "value": float(val)} for date, val in benchmark_values.items()]
        
        # Prepare strategy indicator curves for UI rendering
        ui_indicators = {}
        for ind_name, ind_series in strategy.indicators.items():
            # Replace NaNs with None for JSON compliance
            clean_series = ind_series.where(pd.notna(ind_series), None)
            
            # Convert series values appropriately
            if clean_series.dtype == bool:
                ui_indicators[ind_name] = [
                    {"date": str(date.date()), "value": bool(val) if val is not None else None}
                    for date, val in clean_series.items()
                ]
            else:
                ui_indicators[ind_name] = [
                    {"date": str(date.date()), "value": float(val) if val is not None else None}
                    for date, val in clean_series.items()
                ]
                
        return {
            "metrics": metrics,
            "trades": self.trades_history,
            "benchmark_curve": benchmark_curve,
            "indicators": ui_indicators,
            "ticker_close": [{"date": str(date.date()), "value": float(val)} for date, val in self.data["Close"].items()]
        }
