import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class BaseStrategy:
    """
    Base Strategy class. Inherit this class to create custom trading strategies.
    """
    name = "Base Strategy"
    
    def __init__(self, data: pd.DataFrame, params: Dict[str, Any]):
        """
        Parameters:
        - data (pd.DataFrame): OHLCV historical market data.
        - params (Dict[str, Any]): Strategy hyper-parameters.
        """
        self.data = data.copy()
        self.params = params
        self.indicators: Dict[str, pd.Series] = {}
        self.init()
        
    def init(self) -> None:
        """
        Calculate indicators. Override in child classes.
        """
        pass
        
    def next(self, idx: int, date: pd.Timestamp, row: pd.Series) -> Optional[str]:
        """
        Process a single bar and return trading signal: 'BUY', 'SELL', 'HOLD' or None.
        Override in child classes.
        
        Parameters:
        - idx (int): Row index in the data frame.
        - date (pd.Timestamp): Date of the current bar.
        - row (pd.Series): OHLCV data of the current bar.
        """
        return None

class SMACrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    Buys when fast SMA crosses above slow SMA.
    Sells when fast SMA crosses below slow SMA.
    """
    name = "SMA Crossover"
    
    def init(self) -> None:
        fast_period = int(self.params.get("fast_period", 20))
        slow_period = int(self.params.get("slow_period", 50))
        
        # Calculate SMAs
        self.indicators["fast_sma"] = self.data["Close"].rolling(window=fast_period).mean()
        self.indicators["slow_sma"] = self.data["Close"].rolling(window=slow_period).mean()
        
    def next(self, idx: int, date: pd.Timestamp, row: pd.Series) -> Optional[str]:
        if idx < 1:
            return None
            
        fast_sma = self.indicators["fast_sma"]
        slow_sma = self.indicators["slow_sma"]
        
        # We need values at current and previous index to detect crossover
        curr_fast = fast_sma.iloc[idx]
        curr_slow = slow_sma.iloc[idx]
        prev_fast = fast_sma.iloc[idx - 1]
        prev_slow = slow_sma.iloc[idx - 1]
        
        if pd.isna(curr_fast) or pd.isna(curr_slow) or pd.isna(prev_fast) or pd.isna(prev_slow):
            return None
            
        # Cross above: Buy
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return "BUY"
        # Cross below: Sell
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            return "SELL"
            
        return "HOLD"

class RSIStrategy(BaseStrategy):
    """
    Relative Strength Index (RSI) Strategy.
    Buys when RSI crosses above oversold line (reversal from bottom).
    Sells when RSI crosses below overbought line (reversal from top).
    """
    name = "RSI Reversal"
    
    def init(self) -> None:
        period = int(self.params.get("period", 14))
        
        # Calculate RSI
        delta = self.data["Close"].diff()
        gain = (delta.where(delta > 0, 0)).copy()
        loss = (-delta.where(delta < 0, 0)).copy()
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Standard Wilder's smoothing or simple rolling is fine
        # Here we use standard exponential smoothing for classic RSI
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        self.indicators["rsi"] = rsi.fillna(50)
        
    def next(self, idx: int, date: pd.Timestamp, row: pd.Series) -> Optional[str]:
        if idx < 1:
            return None
            
        rsi = self.indicators["rsi"]
        curr_rsi = rsi.iloc[idx]
        prev_rsi = rsi.iloc[idx - 1]
        
        oversold = float(self.params.get("oversold", 30))
        overbought = float(self.params.get("overbought", 70))
        
        # RSI crossing above oversold (bullish reversal)
        if prev_rsi <= oversold and curr_rsi > oversold:
            return "BUY"
        # RSI crossing below overbought (bearish reversal)
        elif prev_rsi >= overbought and curr_rsi < overbought:
            return "SELL"
            
        return "HOLD"

class VolatilityLiquiditySqueezeStrategy(BaseStrategy):
    """
    The Volatility-Liquidity Squeeze Strategy.
    - Volatility Squeeze: Bollinger Bands (BB) contract inside Keltner Channels (KC).
    - Liquidity Squeeze: Trading volume is lower than its historical average (low liquidity).
    - Breakout Trigger: Release/Trigger of the squeeze with price crossing BB/KC bands
      accompanied by a surge in volume (liquidity returning).
    """
    name = "Volatility-Liquidity Squeeze"
    
    def init(self) -> None:
        bb_period = int(self.params.get("bb_period", 20))
        bb_std = float(self.params.get("bb_std", 2.0))
        kc_period = int(self.params.get("kc_period", 20))
        kc_atr = float(self.params.get("kc_atr", 1.5))
        volume_period = int(self.params.get("volume_period", 20))
        
        close = self.data["Close"]
        high = self.data["High"]
        low = self.data["Low"]
        volume = self.data["Volume"]
        
        # 1. Bollinger Bands
        bb_mid = close.rolling(window=bb_period).mean()
        bb_std_dev = close.rolling(window=bb_period).std()
        self.indicators["bb_upper"] = bb_mid + (bb_std * bb_std_dev)
        self.indicators["bb_lower"] = bb_mid - (bb_std * bb_std_dev)
        self.indicators["bb_mid"] = bb_mid
        
        # 2. Keltner Channels (using simple moving average and ATR)
        kc_mid = close.rolling(window=kc_period).mean()
        
        # Calculate ATR (Average True Range)
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=kc_period).mean()
        
        self.indicators["kc_upper"] = kc_mid + (kc_atr * atr)
        self.indicators["kc_lower"] = kc_mid - (kc_atr * atr)
        self.indicators["kc_mid"] = kc_mid
        
        # 3. Volume Average
        self.indicators["volume_sma"] = volume.rolling(window=volume_period).mean()
        
        # 4. Volatility Squeeze State (BB inside KC)
        bb_up = self.indicators["bb_upper"]
        bb_lo = self.indicators["bb_lower"]
        kc_up = self.indicators["kc_upper"]
        kc_lo = self.indicators["kc_lower"]
        
        # Squeeze condition
        self.indicators["is_squeeze"] = (bb_up < kc_up) & (bb_lo > kc_lo)
        
    def next(self, idx: int, date: pd.Timestamp, row: pd.Series) -> Optional[str]:
        if idx < 1:
            return None
            
        close = self.data["Close"]
        volume = self.data["Volume"]
        
        bb_up = self.indicators["bb_upper"]
        bb_lo = self.indicators["bb_lower"]
        kc_up = self.indicators["kc_upper"]
        kc_lo = self.indicators["kc_lower"]
        vol_sma = self.indicators["volume_sma"]
        is_sq = self.indicators["is_squeeze"]
        
        curr_close = close.iloc[idx]
        prev_close = close.iloc[idx - 1]
        curr_vol = volume.iloc[idx]
        curr_vol_sma = vol_sma.iloc[idx]
        
        if pd.isna(bb_up.iloc[idx]) or pd.isna(kc_up.iloc[idx]) or pd.isna(curr_vol_sma):
            return None
            
        # Volatility squeeze indicator is active on previous or current bar
        squeeze_active = is_sq.iloc[idx] or is_sq.iloc[idx - 1]
        
        # Volume breakout (liquidity expanding/returning)
        volume_expansion = curr_vol > curr_vol_sma
        
        # Bullish breakout signal:
        # Price closes above upper Bollinger Band (or upper Keltner) and volume expands,
        # and we were in a squeeze (volatility compression) recently
        if squeeze_active and volume_expansion and prev_close <= bb_up.iloc[idx - 1] and curr_close > bb_up.iloc[idx]:
            return "BUY"
            
        # Bearish breakout signal:
        # Price closes below lower Bollinger Band (or lower Keltner) and volume expands
        elif squeeze_active and volume_expansion and prev_close >= bb_lo.iloc[idx - 1] and curr_close < bb_lo.iloc[idx]:
            return "SELL"
            
        return "HOLD"

# Helper list to register strategies
STRATEGY_MAP = {
    "vls": VolatilityLiquiditySqueezeStrategy,
    "sma": SMACrossoverStrategy,
    "rsi": RSIStrategy
}

def get_strategy_definitions() -> Dict[str, Any]:
    """
    Returns strategy structures and configurations for the frontend.
    """
    return {
        "vls": {
            "name": "Volatility-Liquidity Squeeze Strategy",
            "description": "Enters a trade when Bollinger Bands squeeze inside Keltner Channels (extremely low volatility with dry volume/liquidity), then releases with price breaking out on volume expansion.",
            "params": [
                {"name": "bb_period", "label": "Bollinger Bands Period", "type": "int", "default": 20, "min": 5, "max": 100},
                {"name": "bb_std", "label": "BB Std Dev Multiplier", "type": "float", "default": 2.0, "min": 0.5, "max": 4.0},
                {"name": "kc_period", "label": "Keltner Channels Period", "type": "int", "default": 20, "min": 5, "max": 100},
                {"name": "kc_atr", "label": "KC ATR Multiplier", "type": "float", "default": 1.5, "min": 0.5, "max": 4.0},
                {"name": "volume_period", "label": "Volume SMA Period", "type": "int", "default": 20, "min": 5, "max": 100}
            ]
        },
        "sma": {
            "name": "SMA Crossover Strategy",
            "description": "Standard trend-following system. Enters long when fast Simple Moving Average crosses above slow Simple Moving Average; exits or enters short when crossing below.",
            "params": [
                {"name": "fast_period", "label": "Fast SMA Period", "type": "int", "default": 20, "min": 2, "max": 100},
                {"name": "slow_period", "label": "Slow SMA Period", "type": "int", "default": 50, "min": 5, "max": 200}
            ]
        },
        "rsi": {
            "name": "RSI Reversal Strategy",
            "description": "Momentum oscillator system. Enters long when RSI rises above the oversold threshold from below. Enters short / exits when RSI falls below the overbought threshold from above.",
            "params": [
                {"name": "period", "label": "RSI Period", "type": "int", "default": 14, "min": 2, "max": 50},
                {"name": "oversold", "label": "Oversold Level", "type": "int", "default": 30, "min": 10, "max": 50},
                {"name": "overbought", "label": "Overbought Level", "type": "int", "default": 70, "min": 50, "max": 90}
            ]
        }
    }
