/**
 * QUANTEX API Client
 * Centralized HTTP client for backend REST communication with timeouts and error handling.
 */
const API = {
    async request(endpoint, options = {}) {
        const timeout = options.timeout || 12000;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout);

        try {
            const config = {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    ...(options.headers || {})
                }
            };
            const response = await fetch(`/api${endpoint}`, config);
            clearTimeout(timer);

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.error || `HTTP ${response.status}: ${response.statusText}`);
            }
            return await response.json();
        } catch (err) {
            clearTimeout(timer);
            console.error(`API Error on [${endpoint}]:`, err);
            throw err;
        }
    },

    // Market Data
    getHealth() { return this.request('/health'); },
    getWatchlist() { return this.request('/watchlist'); },
    getStockQuote(symbol) { return this.request(`/stock/${encodeURIComponent(symbol)}`); },
    getStockHistory(symbol, period = '1Y') { return this.request(`/stock/${encodeURIComponent(symbol)}/history?period=${period}`); },
    getStockIndicators(symbol, period = '6M') { return this.request(`/stock/${encodeURIComponent(symbol)}/indicators?period=${period}`); },

    // Machine Learning
    getStockPrediction(symbol, model = 'logistic_regression', horizon = 5) {
        return this.request(`/stock/${encodeURIComponent(symbol)}/prediction?model=${model}&horizon=${horizon}`);
    },

    // AI Analyst & Agent
    getAnalystExplanation(symbol) {
        return this.request('/analyst/explain', {
            method: 'POST',
            body: JSON.stringify({ symbol })
        });
    },
    runAgentCommand(command) {
        return this.request('/agent/command', {
            method: 'POST',
            body: JSON.stringify({ command }),
            timeout: 25000
        });
    },

    // Backtesting
    runBacktest(params) {
        return this.request('/backtest', {
            method: 'POST',
            body: JSON.stringify(params),
            timeout: 15000
        });
    },

    // Virtual Paper Trading
    getPortfolio() { return this.request('/trading/portfolio'); },
    placeOrder(symbol, side, quantity, notes = '') {
        return this.request('/trading/order', {
            method: 'POST',
            body: JSON.stringify({ symbol, side, quantity, notes })
        });
    },
    getTransactions(limit = 50) { return this.request(`/trading/transactions?limit=${limit}`); },
    getRiskMetrics() { return this.request('/trading/risk'); },
    resetPortfolio() {
        return this.request('/trading/reset', { method: 'POST' });
    }
};

window.API = API;
