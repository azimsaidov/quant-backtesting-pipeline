// Constants and Global State
const API_BASE = 'http://127.0.0.1:8000';
let activeStrategies = {};
let currentTrades = [];
let sortDirection = {};

// Chart.js global references for resetting
let equityChartInstance = null;
let drawdownChartInstance = null;

// Initial Setup on DOM Load
document.addEventListener('DOMContentLoaded', () => {
    fetchSymbols();
    fetchStrategies();
    setupEventListeners();
});

// Event Listeners Registration
function setupEventListeners() {
    // Strategy selection change
    document.getElementById('strategy-select').addEventListener('change', (e) => {
        renderStrategyParams(e.target.value);
    });

    // Custom CSV File Upload
    document.getElementById('csv-file-input').addEventListener('change', handleCsvUpload);

    // Run Backtest Action
    document.getElementById('run-backtest-btn').addEventListener('click', executeBacktest);

    // Trade Log Searching
    document.getElementById('trade-search').addEventListener('input', handleTradeSearch);

    // Trade Log Sorting headers
    document.querySelectorAll('#trades-table th').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.getAttribute('data-sort');
            if (column) sortTradesTable(column);
        });
    });
}

// Fetch Recommended Symbols
async function fetchSymbols() {
    try {
        const res = await fetch(`${API_BASE}/api/symbols`);
        if (!res.ok) throw new Error("Failed to load symbols");
        const symbols = await res.json();
        
        const select = document.getElementById('ticker-select');
        select.innerHTML = ''; // Reset
        
        symbols.forEach(sym => {
            const opt = document.createElement('option');
            opt.value = sym.symbol;
            opt.textContent = `${sym.symbol} (${sym.name}) - ${sym.type}`;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error("Fetch symbols error:", err);
    }
}

// Fetch Strategy Schemas
async function fetchStrategies() {
    try {
        const res = await fetch(`${API_BASE}/api/strategies`);
        if (!res.ok) throw new Error("Failed to load strategies");
        activeStrategies = await res.json();
        
        const select = document.getElementById('strategy-select');
        select.innerHTML = '';
        
        Object.entries(activeStrategies).forEach(([id, def]) => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = def.name;
            select.appendChild(opt);
        });
        
        // Render parameters for the first selected strategy by default
        if (select.value) {
            renderStrategyParams(select.value);
        }
    } catch (err) {
        console.error("Fetch strategies error:", err);
    }
}

// Dynamically Render Hyperparameter Forms based on Strategy Schema
function renderStrategyParams(strategyId) {
    const container = document.getElementById('strategy-params-container');
    container.innerHTML = ''; // Clear
    
    const strategy = activeStrategies[strategyId];
    if (!strategy || !strategy.params) return;
    
    // Add a strategy description card
    const desc = document.createElement('p');
    desc.style.fontSize = '0.78rem';
    desc.style.color = 'var(--text-secondary)';
    desc.style.marginBottom = '16px';
    desc.style.lineHeight = '1.4';
    desc.textContent = strategy.description;
    container.appendChild(desc);
    
    // Render each parameter input
    strategy.params.forEach(p => {
        const group = document.createElement('div');
        group.className = 'form-group';
        
        const labelRow = document.createElement('div');
        labelRow.style.display = 'flex';
        labelRow.style.justifyContent = 'space-between';
        
        const label = document.createElement('label');
        label.setAttribute('for', `param-${p.name}`);
        label.textContent = p.label;
        
        const valIndicator = document.createElement('span');
        valIndicator.id = `val-indicator-${p.name}`;
        valIndicator.style.fontSize = '0.78rem';
        valIndicator.style.color = 'var(--color-primary)';
        valIndicator.style.fontWeight = '600';
        valIndicator.textContent = p.default;
        
        labelRow.appendChild(label);
        labelRow.appendChild(valIndicator);
        group.appendChild(labelRow);
        
        // We use slider type for a premium touch, alongside updating indicators
        const input = document.createElement('input');
        input.type = 'range';
        input.id = `param-${p.name}`;
        input.min = p.min;
        input.max = p.max;
        input.step = p.type === 'float' ? '0.1' : '1';
        input.value = p.default;
        input.style.width = '100%';
        input.style.accentColor = 'var(--color-primary)';
        
        input.addEventListener('input', (e) => {
            valIndicator.textContent = e.target.value;
        });
        
        group.appendChild(input);
        container.appendChild(group);
    });
}

// Custom CSV File Upload Operations
async function handleCsvUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const label = document.getElementById('upload-label');
    const status = document.getElementById('upload-status');
    
    label.innerHTML = `Uploading ${file.name}...`;
    status.style.display = 'none';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Upload failed");
        }
        
        const result = await res.json();
        
        label.innerHTML = `Successfully Loaded!`;
        status.textContent = `Dataset parsed: ${result.records} rows (${result.start_date} to ${result.end_date})`;
        status.style.display = 'block';
        status.className = 'text-success';
        
        // Add to symbols selector and auto-select
        const select = document.getElementById('ticker-select');
        const opt = document.createElement('option');
        opt.value = result.symbol_key;
        opt.textContent = `📂 Custom Upload: ${result.filename}`;
        select.insertBefore(opt, select.firstChild);
        select.value = result.symbol_key;
        
        // Set date inputs boundaries automatically based on CSV metadata
        document.getElementById('start-date').value = result.start_date;
        document.getElementById('end-date').value = result.end_date;
        
    } catch (err) {
        label.innerHTML = `Upload Error!`;
        status.textContent = err.message;
        status.style.display = 'block';
        status.className = 'text-danger';
        console.error("CSV Upload failed:", err);
    }
}

// Backtest Execution Routine
async function executeBacktest() {
    const btn = document.getElementById('run-backtest-btn');
    const loader = document.getElementById('btn-loader');
    const arrow = document.getElementById('btn-arrow');
    
    // UI state loading
    btn.disabled = true;
    loader.style.display = 'block';
    arrow.style.display = 'none';
    
    // Read input configurations
    const ticker = document.getElementById('ticker-select').value;
    const strategyId = document.getElementById('strategy-select').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const initialCash = parseFloat(document.getElementById('initial-cash').value);
    
    // Percent values converted back to fractional decimals
    const commissionRate = parseFloat(document.getElementById('commission-rate').value) / 100.0;
    const slippageRate = parseFloat(document.getElementById('slippage-rate').value) / 100.0;
    
    // Retrieve strategy hyperparameters
    const strategyParams = {};
    const strategy = activeStrategies[strategyId];
    if (strategy && strategy.params) {
        strategy.params.forEach(p => {
            const input = document.getElementById(`param-${p.name}`);
            if (input) {
                strategyParams[p.name] = p.type === 'int' ? parseInt(input.value) : parseFloat(input.value);
            }
        });
    }
    
    try {
        const payload = {
            ticker: ticker,
            strategy_id: strategyId,
            start_date: startDate,
            end_date: endDate,
            initial_cash: initialCash,
            commission_rate: commissionRate,
            slippage_rate: slippageRate,
            strategy_params: strategyParams
        };
        
        const res = await fetch(`${API_BASE}/api/backtest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Backtest failed");
        }
        
        const data = await res.json();
        
        // Hide Splash Screen and show Terminal UI
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('dashboard-view').style.display = 'flex';
        
        // Set globally for table interactions
        currentTrades = data.trades.filter(t => t.type === 'SELL');
        
        // Update stats and draw graphs
        populateMetricsGrid(data.metrics);
        renderCharts(data);
        renderTradesTable(currentTrades);
        
    } catch (err) {
        alert(`Backtest Execution Error: ${err.message}`);
        console.error("Backtest failed:", err);
    } finally {
        // UI state idle
        btn.disabled = false;
        loader.style.display = 'none';
        arrow.style.display = 'block';
    }
}

// Populate Metric Highlights
function populateMetricsGrid(m) {
    const grid = document.getElementById('metrics-grid');
    grid.innerHTML = '';
    
    // Definitions of panels to build
    const cards = [
        { label: "Total Return", value: formatPercent(m.total_return), class: m.total_return >= 0 ? "positive" : "negative" },
        { label: "CAGR (Annualized)", value: formatPercent(m.cagr), class: m.cagr >= 0 ? "positive" : "negative" },
        { label: "Sharpe Ratio", value: m.sharpe_ratio.toFixed(2), class: m.sharpe_ratio >= 1.5 ? "positive" : (m.sharpe_ratio < 0 ? "negative" : "") },
        { label: "Sortino Ratio", value: m.sortino_ratio.toFixed(2), class: m.sortino_ratio >= 1.5 ? "positive" : (m.sortino_ratio < 0 ? "negative" : "") },
        { label: "Max Drawdown", value: formatPercent(m.max_drawdown), class: "negative" },
        { label: "Win Rate", value: formatPercent(m.win_rate), class: m.win_rate >= 0.5 ? "positive" : "negative" },
        { label: "Profit Factor", value: typeof m.profit_factor === 'number' ? m.profit_factor.toFixed(2) : m.profit_factor, class: m.profit_factor >= 1.5 ? "positive" : (m.profit_factor < 1.0 ? "negative" : "") },
        { label: "Total Trades", value: m.total_trades, class: "" }
    ];
    
    cards.forEach(c => {
        const div = document.createElement('div');
        div.className = `metric-card ${c.class}`;
        div.innerHTML = `
            <span class="metric-label">${c.label}</span>
            <span class="metric-value">${c.value}</span>
        `;
        grid.appendChild(div);
    });
}

// Chart.js Graph Rendering
function renderCharts(data) {
    // 1. Destroy existing charts if active
    if (equityChartInstance) equityChartInstance.destroy();
    if (drawdownChartInstance) drawdownChartInstance.destroy();
    
    // Extract dates and points
    const dates = data.metrics.equity_curve.map(e => e.date);
    const equityValues = data.metrics.equity_curve.map(e => e.value);
    const benchmarkValues = data.benchmark_curve.map(b => b.value);
    const drawdownValues = data.metrics.drawdown_curve.map(d => d.value * 100); // convert to %
    
    // Custom neon gradients for premium visual feel
    const ctxEquity = document.getElementById('equityChart').getContext('2d');
    const gradEquity = ctxEquity.createLinearGradient(0, 0, 0, 400);
    gradEquity.addColorStop(0, 'rgba(139, 92, 246, 0.35)');
    gradEquity.addColorStop(1, 'rgba(139, 92, 246, 0.00)');
    
    // Setup Equity Curve Chart
    equityChartInstance = new Chart(ctxEquity, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Strategy Equity Curve ($)',
                    data: equityValues,
                    borderColor: '#8b5cf6',
                    borderWidth: 2.5,
                    backgroundColor: gradEquity,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4
                },
                {
                    label: 'Buy & Hold Benchmark ($)',
                    data: benchmarkValues,
                    borderColor: '#64748b',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#9ca3af', font: { family: 'Inter', size: 11 } }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(10, 15, 26, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#e5e7eb',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#9ca3af', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: {
                        color: '#9ca3af',
                        font: { size: 10 },
                        callback: (val) => '$' + val.toLocaleString()
                    }
                }
            }
        }
    });
    
    // Setup Drawdown Area Chart
    const ctxDrawdown = document.getElementById('drawdownChart').getContext('2d');
    const gradDrawdown = ctxDrawdown.createLinearGradient(0, 0, 0, 400);
    gradDrawdown.addColorStop(0, 'rgba(239, 68, 68, 0.3)');
    gradDrawdown.addColorStop(1, 'rgba(239, 68, 68, 0.00)');
    
    drawdownChartInstance = new Chart(ctxDrawdown, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Drawdown (%)',
                    data: drawdownValues,
                    borderColor: '#ef4444',
                    borderWidth: 1.5,
                    backgroundColor: gradDrawdown,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(10, 15, 26, 0.95)',
                    bodyColor: '#e5e7eb',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: (ctx) => `Drawdown: ${ctx.parsed.y.toFixed(2)}%`
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#9ca3af', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: {
                        color: '#9ca3af',
                        font: { size: 10 },
                        callback: (val) => val.toFixed(1) + '%'
                    }
                }
            }
        }
    });
}

// Render Roundtrip Trades Table
function renderTradesTable(trades) {
    const tbody = document.getElementById('trades-table-body');
    tbody.innerHTML = '';
    
    if (trades.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center;" class="text-muted">No completed trades executed in this period.</td></tr>`;
        return;
    }
    
    trades.forEach(t => {
        const row = document.createElement('tr');
        const returnClass = t.return >= 0 ? 'text-success' : 'text-danger';
        const pnlClass = t.pnl >= 0 ? 'text-success' : 'text-danger';
        
        row.innerHTML = `
            <td>#${t.trade_id}</td>
            <td><span class="badge badge-sell">SELL</span></td>
            <td>${t.date}</td>
            <td>$${t.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>${t.qty.toLocaleString(undefined, {maximumFractionDigits: 4})}</td>
            <td>$${t.commission.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="${returnClass} font-semibold">${formatPercent(t.return)}</td>
            <td class="${pnlClass} font-semibold">$${t.pnl.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        `;
        tbody.appendChild(row);
    });
}

// Client Side Table Searching
function handleTradeSearch(e) {
    const query = e.target.value.toLowerCase().trim();
    if (!query) {
        renderTradesTable(currentTrades);
        return;
    }
    
    const filtered = currentTrades.filter(t => 
        t.trade_id.toString().includes(query) ||
        t.date.toLowerCase().includes(query) ||
        t.price.toString().includes(query) ||
        t.pnl.toString().includes(query)
    );
    renderTradesTable(filtered);
}

// Client Side Table Sorting
function sortTradesTable(column) {
    // Alternate sorting direction
    sortDirection[column] = sortDirection[column] === 'asc' ? 'desc' : 'asc';
    const isAsc = sortDirection[column] === 'asc';
    
    currentTrades.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];
        
        // Parse dates for accurate temporal sort
        if (column === 'date') {
            valA = new Date(valA);
            valB = new Date(valB);
        }
        
        if (valA < valB) return isAsc ? -1 : 1;
        if (valA > valB) return isAsc ? 1 : -1;
        return 0;
    });
    
    renderTradesTable(currentTrades);
}

// Numeric Formatter Utilities
function formatPercent(val) {
    if (typeof val !== 'number') return '0.00%';
    const pct = val * 100;
    return (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
}
