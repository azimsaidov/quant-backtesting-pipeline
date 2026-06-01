# QUANTITATIVE BACKTESTING PIPELINE

A standalone, modular quantitative trading backtest engine and interactive web interface. Designed for historical testing of technical trading strategies, transaction accounting (slippage, commissions), and advanced portfolio metric calculation.

---

## 1. System Architecture

The pipeline consists of a Python 3.8+ FastAPI application backend and a static HTML5/CSS3/JavaScript frontend dashboard hosted on a single web server port.

```
├── backend/
│   ├── app.py          # FastAPI server and routing endpoints
│   ├── engine.py       # Event-driven backtesting execution logic
│   ├── strategies.py   # Strategy base class and implementations
│   ├── data.py         # Yahoo Finance (yfinance) integration & CSV parsing
│   ├── metrics.py      # Statistical performance indicators
│   └── uploads/        # Local directory storing uploaded CSV datasets
├── frontend/
│   ├── index.html      # UI structure (sidebar controllers and canvas tags)
│   ├── style.css       # Slate-dark theme, grid layouts, glassmorphism CSS
│   └── app.js          # API client operations, dynamic forms, Chart.js integrations
├── run.py              # Automating dependency verification and server execution
├── requirements.txt    # Python runtime requirements list
└── .gitignore          # Repository ignore rules
```

---

## 2. Core Mathematical Formulations

### The Volatility-Liquidity Squeeze Strategy (VLS)
The primary strategy models periods of low asset price volatility and dry liquidity (coiled spring effect), followed by explosive breakouts on volume expansion.

#### 1. Volatility Squeeze State
A volatility squeeze occurs when the Bollinger Bands contract fully inside the Keltner Channels:
$$\text{Squeeze Active} = (BB_{\text{upper}} < KC_{\text{upper}}) \land (BB_{\text{lower}} > KC_{\text{lower}})$$

Where:
*   **Bollinger Bands (BB)**:
    $$BB_{\text{mid}} = \text{SMA}(P_{\text{Close}}, N_{\text{BB}})$$
    $$BB_{\text{upper}} = BB_{\text{mid}} + (k_{\text{BB}} \cdot \sigma_{N_{\text{BB}}})$$
    $$BB_{\text{lower}} = BB_{\text{mid}} - (k_{\text{BB}} \cdot \sigma_{N_{\text{BB}}})$$
    *($N_{\text{BB}} = 20, k_{\text{BB}} = 2.0$)*
*   **Keltner Channels (KC)**:
    $$KC_{\text{mid}} = \text{SMA}(P_{\text{Close}}, N_{\text{KC}})$$
    $$KC_{\text{upper}} = KC_{\text{mid}} + (k_{\text{KC}} \cdot \text{ATR}_{N_{\text{KC}}})$$
    $$KC_{\text{lower}} = KC_{\text{mid}} - (k_{\text{KC}} \cdot \text{ATR}_{N_{\text{KC}}})$$
    *($N_{\text{KC}} = 20, k_{\text{KC}} = 1.5$)*

#### 2. Liquidity Contraction
Liquidity is evaluated via the volume moving average:
$$\text{Liquidity Squeezed} = V_t < \text{SMA}(V, N_{\text{Vol}})$$
*($N_{\text{Vol}} = 20$)*

#### 3. Breakout / Entry Signal
An entry trigger is generated when a squeeze has been active (either currently or in the previous period), volume expands, and price crosses the outer bands:
$$\text{BUY (Bullish Breakout)} = \text{Squeeze Active}_{t-1, t} \land (V_t > \text{SMA}(V, N_{\text{Vol}})) \land (P_{\text{Close}, t} > BB_{\text{upper}, t})$$
$$\text{SELL (Bearish Breakout)} = \text{Squeeze Active}_{t-1, t} \land (V_t > \text{SMA}(V, N_{\text{Vol}})) \land (P_{\text{Close}, t} < BB_{\text{lower}, t})$$

---

### Portfolio Performance Metrics
The system calculates daily equity adjustments and returns standard quantitative indicators:

#### 1. Compound Annual Growth Rate (CAGR)
$$\text{CAGR} = \left(\frac{V_{\text{Final}}}{V_{\text{Initial}}}\right)^{\frac{365.25}{D}} - 1.0$$
*Where $D$ represents total days in the backtest period.*

#### 2. Sharpe Ratio
$$\text{Sharpe} = \frac{\overline{R_d - R_f}}{\sigma(R_d)} \cdot \sqrt{252}$$
*Where $R_d$ is daily returns, $R_f$ is risk-free rate, and daily standard deviation is normalized over 252 trading days.*

#### 3. Sortino Ratio
$$\text{Sortino} = \frac{\overline{R_d - R_f}}{\sigma_{\text{downside}}(R_d)} \cdot \sqrt{252}$$
*Where $\sigma_{\text{downside}}$ represents the standard deviation of negative daily returns ($R_d < R_f$).*

#### 4. Maximum Drawdown (MDD)
$$\text{Drawdown}_t = \frac{E_t - \max_{0 \le i \le t}(E_i)}{\max_{0 \le i \le t}(E_i)}$$
$$\text{MDD} = \min_{0 \le t \le T}(\text{Drawdown}_t)$$
*Where $E_t$ represents the portfolio equity at day $t$.*

---

## 3. API Reference

### 1. Retrieve Tickers
*   **Endpoint**: `GET /api/symbols`
*   **Response Format**:
    ```json
    [
      { "symbol": "SPY", "name": "S&P 500 ETF Trust", "type": "Index ETF" },
      { "symbol": "BTC-USD", "name": "Bitcoin USD", "type": "Crypto" }
    ]
    ```

### 2. Retrieve Strategy Parameters
*   **Endpoint**: `GET /api/strategies`
*   **Response Format**: Dictionary detailing configuration options, parameter ranges, and default values.

### 3. Upload Custom CSV Data
*   **Endpoint**: `POST /api/upload`
*   **Payload**: `multipart/form-data` containing a file parameter with a CSV file.
*   **CSV Format Requirements**: Must contain standard headers (Date/Time, Open, High, Low, Close, Volume). Dates must be in chronological order.
*   **Response Format**:
    ```json
    {
      "success": true,
      "filename": "custom_asset.csv",
      "symbol_key": "csv_upload:custom_asset.csv",
      "records": 756,
      "start_date": "2020-01-01",
      "end_date": "2023-01-01"
    }
    ```

### 4. Run Strategy Backtest
*   **Endpoint**: `POST /api/backtest`
*   **Payload Format**:
    ```json
    {
      "ticker": "SPY",
      "strategy_id": "vls",
      "start_date": "2020-01-01",
      "end_date": "2023-01-01",
      "initial_cash": 10000.0,
      "commission_rate": 0.0015,
      "slippage_rate": 0.0005,
      "strategy_params": {
        "bb_period": 20,
        "bb_std": 2.0,
        "kc_period": 20,
        "kc_atr": 1.5,
        "volume_period": 20
      }
    }
    ```
*   **Response Format**: Combined payload containing historical equity curves, drawdown series, pre-calculated performance stats, indicator arrays, and individual roundtrip trade histories.

---

## 4. Execution and Setup

### Prerequisites
*   Python 3.8 or higher.
*   Pip package manager.

### Step 1: Install Dependencies
Run the install command inside the project directory:
```bash
pip install -r requirements.txt
```

### Step 2: Launch Server
Execute the automated bootstrapper python file:
```bash
python run.py
```
This script will verify your Python environment imports, install missing packages if required, launch the Uvicorn web server at `http://127.0.0.1:8000`, and mount the static single page dashboard at the host root `/`.

Open `http://127.0.0.1:8000` in any modern web browser to access the graphical user interface.
