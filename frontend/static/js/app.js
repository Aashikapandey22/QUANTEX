/**
 * QUANTEX Main Application Controller
 * Orchestrates navigation, financial charts, order tickets, watchlist updates,
 * AI agent integration, and virtual paper trading telemetry.
 */
document.addEventListener('DOMContentLoaded', () => {
    class QuantexApp {
        constructor() {
            this.activeSymbol = 'RELIANCE.NS';
            this.activeTimeframe = '1Y';
            this.watchlistData = [];
            this.chart = null;
            this.backtestChart = null;

            this.init();
        }

        async init() {
            console.log('Initializing QUANTEX Institutional Terminal...');
            
            // 1. Initialize Chart
            this.chart = new window.FinancialChart('main-candle-canvas', 'chart-tooltip');

            // 2. Initialize Agent & Voice
            window.agentUI = new window.AgentUIManager();
            window.voiceAssistant = new window.VoiceAssistant({
                onCommand: (cmd) => {
                    window.agentUI.openDrawer();
                    window.agentUI.executeCommand(cmd);
                }
            });

            // 3. Bind UI Events
            this.bindNavigation();
            this.bindGlobalSearch();
            this.bindOrderTicket();
            this.bindChartControls();
            this.bindPredictionsTab();
            this.bindAnalystTab();
            this.bindBacktestTab();
            this.bindPaperTradingTab();

            // 4. Initial Data Hydration
            await this.checkSystemHealth();
            await this.loadWatchlist();
            await this.selectStock(this.activeSymbol);
            await this.refreshPortfolio();
            await this.loadRiskMetrics();
        }

        async checkSystemHealth() {
            try {
                const health = await window.API.getHealth();
                const geminiStatus = document.getElementById('settings-gemini-status');
                const geminiModel = document.getElementById('settings-gemini-model');
                const activeEngine = document.getElementById('settings-active-engine');
                const engineMode = document.getElementById('settings-engine-mode');
                const headerAiModeBadge = document.getElementById('header-ai-mode-badge');
                const drawerAiModeBadge = document.getElementById('drawer-ai-mode-badge');
                const analystEngineBadge = document.getElementById('analyst-engine-badge');

                if (geminiModel) {
                    geminiModel.textContent = health.configured_model || health.gemini_model || 'gemini-2.5-flash';
                }

                if (activeEngine) {
                    activeEngine.textContent = health.active_engine;
                }

                if (health.gemini_configured) {
                    if (geminiStatus) {
                        geminiStatus.textContent = 'ONLINE (ACTIVE)';
                        geminiStatus.className = 'badge positive';
                    }
                    if (engineMode) {
                        engineMode.textContent = `GEMINI (${health.gemini_model})`;
                        engineMode.className = 'badge positive';
                    }
                    if (headerAiModeBadge) {
                        headerAiModeBadge.textContent = 'GEMINI';
                        headerAiModeBadge.className = 'badge positive';
                    }
                    if (drawerAiModeBadge) {
                        drawerAiModeBadge.textContent = `GEMINI API (${health.gemini_model})`;
                        drawerAiModeBadge.className = 'badge positive';
                    }
                    if (analystEngineBadge) {
                        analystEngineBadge.textContent = 'GEMINI CLOUD AI';
                        analystEngineBadge.className = 'badge positive';
                    }
                } else {
                    if (geminiStatus) {
                        geminiStatus.textContent = 'UNCONFIGURED (Key missing)';
                        geminiStatus.className = 'badge';
                    }
                    if (engineMode) {
                        engineMode.textContent = 'LOCAL RULE ENGINE';
                        engineMode.className = 'badge';
                    }
                    if (headerAiModeBadge) {
                        headerAiModeBadge.textContent = 'LOCAL';
                        headerAiModeBadge.className = 'badge';
                    }
                    if (drawerAiModeBadge) {
                        drawerAiModeBadge.textContent = 'LOCAL RULE ENGINE';
                        drawerAiModeBadge.className = 'badge';
                    }
                    if (analystEngineBadge) {
                        analystEngineBadge.textContent = 'LOCAL QUANT ENGINE';
                        analystEngineBadge.className = 'badge';
                    }
                }
            } catch (err) {
                console.warn('Health check failed:', err);
            }
        }

        bindNavigation() {
            const tabs = document.querySelectorAll('.nav-item');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    tabs.forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');

                    const targetId = tab.getAttribute('data-tab');
                    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                    const targetPane = document.getElementById(targetId);
                    if (targetPane) targetPane.classList.add('active');

                    // Resize charts when respective tab opens
                    if (targetId === 'tab-overview' && this.chart) {
                        setTimeout(() => this.chart.handleResize(), 50);
                    } else if (targetId === 'tab-backtesting' && this.backtestChart) {
                        setTimeout(() => this.backtestChart.resize(), 50);
                    } else if (targetId === 'tab-paper-trading') {
                        this.refreshPortfolio();
                    } else if (targetId === 'tab-risk') {
                        this.loadRiskMetrics();
                    }
                });
            });

            // Quick analyst button on overview
            document.getElementById('btn-quick-analyst')?.addEventListener('click', () => {
                window.agentUI.openDrawer();
                window.agentUI.executeCommand(`Analyse ${this.activeSymbol}`);
            });
        }

        bindGlobalSearch() {
            const input = document.getElementById('global-stock-search');
            const dropdown = document.getElementById('search-dropdown');
            if (!input || !dropdown) return;

            input.addEventListener('input', () => {
                const q = input.value.trim().toUpperCase();
                if (!q) {
                    dropdown.classList.add('hidden');
                    return;
                }

                const matches = this.watchlistData.filter(item => 
                    item.symbol.includes(q) || item.name.toUpperCase().includes(q)
                );

                if (matches.length > 0) {
                    dropdown.innerHTML = matches.map(m => `
                        <div class="search-dropdown-item" data-sym="${m.symbol}">
                            <div>
                                <strong class="font-mono">${m.symbol}</strong>
                                <span style="font-size:11px;color:#94A3B8;margin-left:6px;">${m.name}</span>
                            </div>
                            <span class="font-mono">₹${m.price.toFixed(2)}</span>
                        </div>
                    `).join('');
                    dropdown.classList.remove('hidden');
                } else {
                    dropdown.classList.add('hidden');
                }
            });

            dropdown.addEventListener('click', (e) => {
                const item = e.target.closest('.search-dropdown-item');
                if (item) {
                    const sym = item.getAttribute('data-sym');
                    this.selectStock(sym);
                    dropdown.classList.add('hidden');
                    input.value = '';
                }
            });

            document.addEventListener('click', (e) => {
                if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                    dropdown.classList.add('hidden');
                }
            });
        }

        bindChartControls() {
            // Timeframe Selector
            const tfBtns = document.querySelectorAll('.tf-btn');
            tfBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    tfBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.activeTimeframe = btn.getAttribute('data-tf');
                    this.loadChartData(this.activeSymbol, this.activeTimeframe);
                });
            });

            // MA Overlay Toggles
            const s20 = document.getElementById('toggle-sma20');
            const s50 = document.getElementById('toggle-sma50');
            const e20 = document.getElementById('toggle-ema20');

            const updateOverlays = () => {
                if (this.chart) {
                    this.chart.setOverlaysVisibility(s20.checked, s50.checked, e20.checked);
                }
            };

            s20?.addEventListener('change', updateOverlays);
            s50?.addEventListener('change', updateOverlays);
            e20?.addEventListener('change', updateOverlays);
        }

        bindOrderTicket() {
            const buyBtn = document.getElementById('btn-side-buy');
            const sellBtn = document.getElementById('btn-side-sell');
            const qtyInput = document.getElementById('order-qty');
            const execBtn = document.getElementById('btn-execute-order');

            let activeSide = 'BUY';

            buyBtn?.addEventListener('click', () => {
                activeSide = 'BUY';
                buyBtn.classList.add('active');
                sellBtn.classList.remove('active');
                execBtn.textContent = 'EXECUTE VIRTUAL BUY';
                execBtn.className = 'btn-primary-action buy';
                this.updateOrderSummary();
            });

            sellBtn?.addEventListener('click', () => {
                activeSide = 'SELL';
                sellBtn.classList.add('active');
                buyBtn.classList.remove('active');
                execBtn.textContent = 'EXECUTE VIRTUAL SELL';
                execBtn.className = 'btn-primary-action sell';
                this.updateOrderSummary();
            });

            qtyInput?.addEventListener('input', () => this.updateOrderSummary());

            execBtn?.addEventListener('click', async () => {
                const qty = parseInt(qtyInput.value) || 0;
                if (qty <= 0) {
                    this.showOrderFeedback('Please enter a valid positive quantity.', 'error');
                    return;
                }

                execBtn.disabled = true;
                execBtn.textContent = 'EXECUTING ORDER...';

                try {
                    const res = await window.API.placeOrder(this.activeSymbol, activeSide, qty, 'Ticket execution');
                    if (res.success) {
                        this.showOrderFeedback(
                            `Order Executed: ${activeSide} ${qty} ${this.activeSymbol} @ ₹${res.data.order.execution_price.toFixed(2)}`,
                            'success'
                        );
                        await this.refreshPortfolio();
                        await this.loadRiskMetrics();
                    } else {
                        this.showOrderFeedback(res.error || 'Execution failed', 'error');
                    }
                } catch (err) {
                    this.showOrderFeedback(err.message, 'error');
                } finally {
                    execBtn.disabled = false;
                    execBtn.textContent = `EXECUTE VIRTUAL ${activeSide}`;
                }
            });
        }

        updateOrderSummary() {
            const qty = parseInt(document.getElementById('order-qty')?.value) || 0;
            const quote = this.watchlistData.find(w => w.symbol === this.activeSymbol);
            const price = quote ? quote.price : 1000.0;
            const fee = (price * qty) * 0.001; // 0.1% fee
            const total = (price * qty) + fee;

            document.getElementById('order-est-price').textContent = `₹${price.toFixed(2)}`;
            document.getElementById('order-est-fee').textContent = `₹${fee.toFixed(2)}`;
            document.getElementById('order-est-total').textContent = `₹${total.toFixed(2)}`;
        }

        showOrderFeedback(msg, type) {
            const fb = document.getElementById('order-feedback');
            if (!fb) return;
            fb.textContent = msg;
            fb.className = `order-feedback ${type}`;
            fb.classList.remove('hidden');
            setTimeout(() => fb.classList.add('hidden'), 4500);
        }

        async loadWatchlist() {
            try {
                const res = await window.API.getWatchlist();
                if (res.success && res.watchlist) {
                    this.watchlistData = res.watchlist;
                    this.renderWatchlist();
                    this.renderMarketsTable();
                    this.populateSymbolSelects();
                }
            } catch (err) {
                console.error('Failed to load watchlist:', err);
            }
        }

        populateSymbolSelects() {
            const selects = [
                document.getElementById('pred-symbol-select'),
                document.getElementById('analyst-symbol-select'),
                document.getElementById('analytics-symbol-select'),
                document.getElementById('bt-symbol-select')
            ];

            const optionsHtml = this.watchlistData.map(w => 
                `<option value="${w.symbol}">${w.symbol} - ${w.name}</option>`
            ).join('');

            selects.forEach(s => {
                if (s) {
                    s.innerHTML = optionsHtml;
                    s.value = this.activeSymbol;
                }
            });
        }

        renderWatchlist() {
            const tbody = document.getElementById('watchlist-tbody');
            const tickerStrip = document.getElementById('ticker-strip');
            if (!tbody) return;

            tbody.innerHTML = this.watchlistData.map(item => {
                const isPos = item.change >= 0;
                const isSelected = item.symbol === this.activeSymbol;
                return `
                    <tr class="${isSelected ? 'selected' : ''}" data-symbol="${item.symbol}">
                        <td>
                            <strong class="font-mono">${item.ticker || item.symbol.replace('.NS', '')}</strong>
                            <div style="font-size:10px;color:#64748B;">${item.name.slice(0, 18)}</div>
                        </td>
                        <td class="text-right font-mono">₹${item.price.toFixed(2)}</td>
                        <td class="text-right font-mono ${isPos ? 'positive' : 'negative'}">
                            ${isPos ? '+' : ''}${item.change_pct.toFixed(2)}%
                        </td>
                    </tr>
                `;
            }).join('');

            // Bind click
            tbody.querySelectorAll('tr').forEach(row => {
                row.addEventListener('click', () => {
                    const sym = row.getAttribute('data-symbol');
                    this.selectStock(sym);
                });
            });

            // Ticker Scroll Strip
            if (tickerStrip) {
                tickerStrip.innerHTML = this.watchlistData.map(item => {
                    const isPos = item.change >= 0;
                    return `
                        <span class="ticker-item" data-symbol="${item.symbol}">
                            <strong style="color:#FFF">${item.ticker || item.symbol.replace('.NS', '')}</strong>
                            <span>₹${item.price.toFixed(2)}</span>
                            <span class="${isPos ? 'positive' : 'negative'}">${isPos ? '+' : ''}${item.change_pct.toFixed(2)}%</span>
                        </span>
                    `;
                }).join('');

                tickerStrip.querySelectorAll('.ticker-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const sym = item.getAttribute('data-symbol');
                        this.selectStock(sym);
                    });
                });
            }
        }

        renderMarketsTable() {
            const tbody = document.getElementById('markets-tbody');
            if (!tbody) return;

            tbody.innerHTML = this.watchlistData.map(item => {
                const isPos = item.change >= 0;
                return `
                    <tr>
                        <td class="font-mono"><strong>${item.symbol}</strong></td>
                        <td>${item.name}</td>
                        <td><span class="badge">${item.sector}</span></td>
                        <td class="text-right font-mono">₹${item.price.toFixed(2)}</td>
                        <td class="text-right font-mono ${isPos ? 'positive' : 'negative'}">
                            ${isPos ? '+' : ''}₹${item.change.toFixed(2)} (${isPos ? '+' : ''}${item.change_pct.toFixed(2)}%)
                        </td>
                        <td class="text-right font-mono">₹${item.high.toFixed(2)}</td>
                        <td class="text-right font-mono">₹${item.low.toFixed(2)}</td>
                        <td class="text-right font-mono">${item.volume.toLocaleString()}</td>
                        <td><span class="badge ${item.status === 'sample' ? '' : 'positive'}">${item.status.toUpperCase()}</span></td>
                        <td class="text-center">
                            <button class="btn-secondary" style="padding:2px 8px;width:auto;" onclick="window.quantexApp.selectStock('${item.symbol}')">
                                Trade / Chart
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');

            document.getElementById('btn-refresh-markets')?.addEventListener('click', () => this.loadWatchlist());
        }

        async selectStock(symbol) {
            this.activeSymbol = symbol;

            // Highlight in watchlist table
            document.querySelectorAll('#watchlist-tbody tr').forEach(r => {
                if (r.getAttribute('data-symbol') === symbol) {
                    r.classList.add('selected');
                } else {
                    r.classList.remove('selected');
                }
            });

            // Update Header & Order Ticket Form
            document.getElementById('order-symbol').value = symbol;
            this.updateOrderSummary();

            // Load Chart Data
            await this.loadChartData(symbol, this.activeTimeframe);

            // Load Indicators & ML Summary
            await this.loadStockIntelligence(symbol);
        }

        async loadChartData(symbol, period) {
            try {
                const res = await window.API.getStockHistory(symbol, period);
                if (res.success && res.candles) {
                    const quote = this.watchlistData.find(w => w.symbol === symbol) || {};
                    
                    document.getElementById('chart-symbol').textContent = symbol;
                    document.getElementById('chart-name').textContent = quote.name || symbol;
                    document.getElementById('chart-sector').textContent = quote.sector || 'Equities';
                    
                    const lastCandle = res.candles[res.candles.length - 1];
                    const firstCandle = res.candles[0];
                    if (lastCandle) {
                        const change = lastCandle.close - (res.candles[res.candles.length - 2]?.close || firstCandle.close);
                        const changePct = ((change / lastCandle.close) * 100).toFixed(2);
                        const isPos = change >= 0;

                        document.getElementById('chart-current-price').textContent = `₹${lastCandle.close.toFixed(2)}`;
                        const chgEl = document.getElementById('chart-current-change');
                        chgEl.textContent = `${isPos ? '+' : ''}₹${change.toFixed(2)} (${isPos ? '+' : ''}${changePct}%)`;
                        chgEl.className = `price-change font-mono ${isPos ? 'positive' : 'negative'}`;
                    }

                    // Status disclaimer
                    const disc = res.status_meta?.disclaimer || 'Data served from provider.';
                    const date = res.status_meta?.last_market_date || '--';
                    document.getElementById('chart-data-disclaimer').textContent = `STATUS: ${res.status_meta?.status.toUpperCase()} FEED &bull; LAST DATE: ${date} &bull; ${disc}`;
                    document.getElementById('nav-market-date').textContent = `DATE: ${date}`;

                    // Fetch indicator overlays
                    const indRes = await window.API.getStockIndicators(symbol, period);
                    let overlays = {};
                    if (indRes.success && indRes.series) {
                        const sma20 = [];
                        const sma50 = [];
                        const ema20 = [];
                        
                        // Map series to candles by date
                        const seriesMap = new Map();
                        indRes.series.forEach(s => seriesMap.set(s.date, s));

                        res.candles.forEach(c => {
                            const match = seriesMap.get(c.date);
                            sma20.push(match ? match.sma_20 : null);
                            sma50.push(match ? match.sma_50 : null);
                            ema20.push(match ? match.ema_20 : null);
                        });

                        overlays = { sma20, sma50, ema20 };
                    }

                    this.chart.setData(res.candles, overlays);
                }
            } catch (err) {
                console.error(`Failed to load history for ${symbol}:`, err);
            }
        }

        async loadStockIntelligence(symbol) {
            try {
                // Indicators
                const indRes = await window.API.getStockIndicators(symbol, '6M');
                if (indRes.success && indRes.summary) {
                    const s = indRes.summary;
                    document.getElementById('summary-rsi').textContent = s.rsi_14?.value || '--';
                    const biasEl = document.getElementById('summary-bias');
                    biasEl.textContent = s.overall_technical_bias || 'Neutral';
                    biasEl.className = `val ${s.overall_technical_bias === 'Bullish' ? 'positive' : (s.overall_technical_bias === 'Bearish' ? 'negative' : '')}`;

                    // Populate Analytics Tab Cards
                    this.renderIndicatorsTab(s);
                }

                // Machine Learning Prediction
                const mlRes = await window.API.getStockPrediction(symbol, 'logistic_regression', 5);
                if (mlRes.success && mlRes.prediction) {
                    const p = mlRes.prediction;
                    const dirBadge = document.getElementById('summary-direction-badge');
                    const dirText = document.getElementById('summary-direction-text');
                    const probNum = document.getElementById('summary-prob-num');
                    const accEl = document.getElementById('summary-acc');

                    if (dirText) dirText.textContent = p.predicted_direction.toUpperCase();
                    if (probNum) probNum.textContent = `${p.probability_score}%`;
                    if (accEl) accEl.textContent = `${p.metrics?.accuracy || '--'}%`;

                    if (dirBadge) {
                        if (p.predicted_direction === 'Bearish') {
                            dirBadge.className = 'direction-indicator bearish';
                            dirBadge.querySelector('.dir-icon').textContent = '▼';
                        } else {
                            dirBadge.className = 'direction-indicator';
                            dirBadge.querySelector('.dir-icon').textContent = '▲';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to load intelligence metrics:', err);
            }
        }

        renderIndicatorsTab(summary) {
            if (!summary) return;
            const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

            setTxt('ind-sma20-val', `SMA 20: ₹${summary.sma_20?.value?.toFixed(2) || '--'}`);
            setTxt('ind-sma50-val', `SMA 50: ₹${summary.sma_50?.value?.toFixed(2) || '--'}`);
            setTxt('ind-ema20-val', `EMA 20: ₹${summary.ema_20?.value?.toFixed(2) || '--'}`);
            setTxt('ind-ma-desc', summary.explanations?.Moving_Averages || 'Trend indicators.');

            setTxt('ind-rsi-val', summary.rsi_14?.value || '--');
            setTxt('ind-rsi-badge', summary.rsi_14?.signal || 'NEUTRAL');
            setTxt('ind-rsi-desc', summary.explanations?.RSI_14 || 'Momentum.');

            setTxt('ind-macd-val', `MACD: ${summary.macd?.value || '--'}`);
            setTxt('ind-macd-sig', `SIGNAL: ${summary.macd?.signal_line || '--'}`);
            setTxt('ind-macd-badge', summary.macd?.signal || 'CROSSOVER');
            setTxt('ind-macd-desc', summary.explanations?.MACD || 'Moving average convergence divergence.');

            setTxt('ind-bb-upper', `UPPER: ₹${summary.bollinger_bands?.upper?.toFixed(2) || '--'}`);
            setTxt('ind-bb-mid', `MIDDLE: ₹${summary.bollinger_bands?.middle?.toFixed(2) || '--'}`);
            setTxt('ind-bb-lower', `LOWER: ₹${summary.bollinger_bands?.lower?.toFixed(2) || '--'}`);
            setTxt('ind-bb-desc', summary.explanations?.Bollinger_Bands || 'Volatility envelopes.');

            setTxt('ind-atr-val', `₹${summary.atr_14?.value?.toFixed(2) || '--'}`);
            setTxt('ind-atr-desc', summary.explanations?.ATR_14 || 'Average daily volatility.');

            setTxt('ind-vol-val', summary.historical_volatility?.value || '--');
        }

        bindPredictionsTab() {
            const symSelect = document.getElementById('pred-symbol-select');
            const modelSelect = document.getElementById('pred-model-select');
            const runBtn = document.getElementById('btn-run-prediction');
            const horizonBtns = document.querySelectorAll('.horizon-btn');

            let activeHorizon = 5;
            horizonBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    horizonBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    activeHorizon = parseInt(btn.getAttribute('data-horizon'));
                });
            });

            runBtn?.addEventListener('click', async () => {
                const sym = symSelect.value || this.activeSymbol;
                const model = modelSelect.value || 'logistic_regression';

                runBtn.disabled = true;
                runBtn.textContent = 'TRAINING MODEL...';

                try {
                    const res = await window.API.getStockPrediction(sym, model, activeHorizon);
                    if (res.success && res.prediction) {
                        const p = res.prediction;
                        const quote = this.watchlistData.find(w => w.symbol === sym) || {};

                        // Target & Meta
                        document.getElementById('pred-target-name').textContent = quote.name || p.symbol;
                        document.getElementById('pred-target-symbol').textContent = `${p.symbol} &bull; ${p.model_name}`;

                        // Predicted Direction Badge
                        const badge = document.getElementById('pred-hero-badge');
                        badge.textContent = p.predicted_direction.toUpperCase();
                        badge.className = `hero-badge ${p.predicted_direction.toLowerCase()}`;

                        // Separated Concepts: Class Probability & Directional Score
                        const bullP = p.class_probabilities?.bullish_pct ?? p.bullish_probability;
                        const bearP = p.class_probabilities?.bearish_pct ?? p.bearish_probability;
                        document.getElementById('pred-prob-text').textContent = `Class Probabilities: P(Bullish) = ${bullP}% | P(Bearish) = ${bearP}%`;
                        
                        const dirScoreEl = document.getElementById('pred-dir-score');
                        if (dirScoreEl) {
                            const score = p.directional_score ?? 0;
                            dirScoreEl.textContent = `Directional Score: ${score >= 0 ? '+' : ''}${score} / 100 (Model Signal)`;
                        }

                        document.getElementById('pred-res-horizon').textContent = `${p.prediction_horizon_days} Trading Days`;
                        document.getElementById('pred-res-price').textContent = `₹${p.latest_price?.toFixed(2) || '--'}`;
                        document.getElementById('pred-res-date').textContent = p.last_market_date;

                        // Model Reliability Warning Card
                        const relBox = document.getElementById('pred-reliability-box');
                        const relBadge = document.getElementById('pred-reliability-badge');
                        const relMsg = document.getElementById('pred-reliability-msg');
                        if (p.reliability) {
                            if (relBox) {
                                relBox.className = `pred-reliability-box ${p.reliability.level}`;
                            }
                            if (relBadge) {
                                relBadge.textContent = `${p.reliability.rating.toUpperCase()} RELIABILITY`;
                                relBadge.className = `badge ${p.reliability.level === 'weak' ? 'negative' : (p.reliability.level === 'acceptable' ? 'positive' : '')}`;
                            }
                            if (relMsg) {
                                relMsg.textContent = p.reliability.warning;
                            }
                        }

                        // Out-of-Sample Metrics
                        const acc = p.metrics?.out_of_sample_accuracy ?? p.metrics?.accuracy ?? '--';
                        document.getElementById('pred-metric-acc').textContent = `${acc}%`;
                        
                        const baselineEl = document.getElementById('pred-metric-baseline');
                        if (baselineEl && p.baselines) {
                            const edge = p.metrics?.edge_over_majority_baseline ?? 0;
                            baselineEl.textContent = `Baseline: ${p.baselines.majority_class_baseline_accuracy}% (${edge >= 0 ? '+' : ''}${edge}% edge)`;
                        }

                        document.getElementById('pred-metric-prec').textContent = `${p.metrics?.precision}%`;
                        document.getElementById('pred-metric-rec').textContent = `${p.metrics?.recall}%`;
                        document.getElementById('pred-metric-f1').textContent = `${p.metrics?.f1_score}%`;
                        
                        if (p.sample_counts) {
                            document.getElementById('pred-eval-status').textContent = `SAMPLES: ${p.sample_counts.train} TRAIN / ${p.sample_counts.test} TEST`;
                        }

                        // Confusion Matrix
                        if (p.confusion_matrix) {
                            const cm = p.confusion_matrix;
                            document.getElementById('cm-tn').textContent = cm.true_negative;
                            document.getElementById('cm-fp').textContent = cm.false_positive;
                            document.getElementById('cm-fn').textContent = cm.false_negative;
                            document.getElementById('cm-tp').textContent = cm.true_positive;
                            document.getElementById('cm-total-samples').textContent = `N = ${cm.total_test_samples}`;
                        }
                        if (p.period_dates?.test) {
                            document.getElementById('cm-period-text').textContent = `Test Window: ${p.period_dates.test.start} to ${p.period_dates.test.end} (Strict Chronological Split)`;
                        }

                        // Fair Model Comparison Table
                        const compTbody = document.getElementById('pred-comparison-tbody');
                        if (compTbody && p.model_comparison) {
                            const rows = Object.values(p.model_comparison).map(m => `
                                <tr>
                                    <td><strong>${m.name}</strong></td>
                                    <td><span class="badge ${m.direction === 'Bullish' ? 'positive' : (m.direction === 'Bearish' ? 'negative' : '')}">${m.direction}</span></td>
                                    <td class="text-right font-mono">${m.p_bullish}%</td>
                                    <td class="text-right font-mono"><strong>${m.accuracy}%</strong></td>
                                    <td class="text-right font-mono">${m.precision}%</td>
                                    <td class="text-right font-mono">${m.f1_score}%</td>
                                </tr>
                            `).join('');
                            compTbody.innerHTML = rows;
                        }
                    }
                } catch (err) {
                    alert('Prediction failed: ' + err.message);
                } finally {
                    runBtn.disabled = false;
                    runBtn.textContent = 'EXECUTE ML PREDICTION';
                }
            });
        }

        bindAnalystTab() {
            const symSelect = document.getElementById('analyst-symbol-select');
            const genBtn = document.getElementById('btn-generate-analyst-report');
            const speakBtn = document.getElementById('btn-speak-analyst');
            const content = document.getElementById('analyst-content');
            const loader = document.getElementById('analyst-loading');

            let lastReportText = '';

            genBtn?.addEventListener('click', async () => {
                const sym = symSelect.value || this.activeSymbol;
                loader.classList.remove('hidden');
                content.classList.add('hidden');

                try {
                    const res = await window.API.getAnalystExplanation(sym);
                    if (res.success && res.analyst_response) {
                        lastReportText = res.analyst_response;
                        content.innerHTML = window.agentUI.formatMarkdown(res.analyst_response);
                        document.getElementById('analyst-engine-badge').textContent = res.source.toUpperCase();
                    }
                } catch (err) {
                    content.innerHTML = `<p style="color:#F43F5E">Analyst error: ${err.message}</p>`;
                } finally {
                    loader.classList.add('hidden');
                    content.classList.remove('hidden');
                }
            });

            speakBtn?.addEventListener('click', () => {
                if (lastReportText && window.voiceAssistant) {
                    window.voiceAssistant.speak(lastReportText);
                }
            });
        }

        bindBacktestTab() {
            const runBtn = document.getElementById('btn-run-backtest');
            const symSelect = document.getElementById('bt-symbol-select');
            const fastInput = document.getElementById('bt-fast-period');
            const slowInput = document.getElementById('bt-slow-period');
            const capInput = document.getElementById('bt-initial-capital');

            runBtn?.addEventListener('click', async () => {
                const sym = symSelect.value || this.activeSymbol;
                const fast = parseInt(fastInput.value) || 20;
                const slow = parseInt(slowInput.value) || 50;
                const cap = parseFloat(capInput.value) || 1000000;

                runBtn.disabled = true;
                runBtn.textContent = 'SIMULATING TRADES...';

                try {
                    const res = await window.API.runBacktest({
                        symbol: sym,
                        fast_period: fast,
                        slow_period: slow,
                        initial_capital: cap
                    });

                    if (res.success && res.backtest) {
                        const bt = res.backtest;
                        document.getElementById('bt-strategy-badge').textContent = bt.strategy;
                        
                        const retEl = document.getElementById('bt-total-return');
                        retEl.textContent = `${bt.total_return_pct >= 0 ? '+' : ''}${bt.total_return_pct}%`;
                        retEl.className = `m-val font-mono ${bt.total_return_pct >= 0 ? 'positive' : 'negative'}`;

                        document.getElementById('bt-bh-return').textContent = `Buy & Hold: ${bt.buy_and_hold_return_pct}%`;
                        document.getElementById('bt-cagr').textContent = `${bt.cagr_pct}%`;
                        document.getElementById('bt-max-drawdown').textContent = `-${bt.max_drawdown_pct}%`;
                        document.getElementById('bt-sharpe').textContent = bt.sharpe_ratio;
                        document.getElementById('bt-win-rate').textContent = `${bt.win_rate_pct}%`;
                        document.getElementById('bt-trades-count').textContent = `${bt.total_trades} Trades (${bt.winning_trades} Win)`;

                        // Render Equity Curve Chart using Chart.js
                        this.renderBacktestChart(bt.equity_curve);

                        // Render Trades Table
                        this.renderTradesTable(bt.trades);
                    }
                } catch (err) {
                    alert('Backtest simulation failed: ' + err.message);
                } finally {
                    runBtn.disabled = false;
                    runBtn.textContent = 'RUN CHRONOLOGICAL SIMULATION';
                }
            });
        }

        renderBacktestChart(equityCurve) {
            const canvas = document.getElementById('bt-equity-canvas');
            if (!canvas || !equityCurve || !equityCurve.length) return;

            if (this.backtestChart) {
                this.backtestChart.destroy();
            }

            const labels = equityCurve.map(e => e.date);
            const strategyVals = equityCurve.map(e => e.portfolio_value);
            const benchVals = equityCurve.map(e => e.benchmark_value);

            this.backtestChart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'QUANTEX Strategy Equity (₹)',
                            data: strategyVals,
                            borderColor: '#38BDF8',
                            backgroundColor: 'rgba(56, 189, 248, 0.08)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.1,
                            pointRadius: 0
                        },
                        {
                            label: 'Buy & Hold Benchmark (₹)',
                            data: benchVals,
                            borderColor: '#64748B',
                            borderWidth: 1.5,
                            borderDash: [4, 4],
                            fill: false,
                            tension: 0.1,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: '#94A3B8', font: { family: 'JetBrains Mono', size: 10 } } },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#64748B', maxTicksLimit: 6, font: { family: 'JetBrains Mono', size: 10 } },
                            grid: { color: '#18222D' }
                        },
                        y: {
                            ticks: { color: '#64748B', font: { family: 'JetBrains Mono', size: 10 } },
                            grid: { color: '#18222D' }
                        }
                    }
                }
            });
        }

        renderTradesTable(trades) {
            const tbody = document.getElementById('bt-trades-tbody');
            if (!tbody) return;

            if (!trades || !trades.length) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No trades generated during this backtest window.</td></tr>';
                return;
            }

            tbody.innerHTML = trades.map(t => {
                const isWin = t.is_win;
                return `
                    <tr>
                        <td class="font-mono">${t.entry_date}</td>
                        <td class="font-mono">${t.exit_date}</td>
                        <td class="text-right font-mono">₹${t.entry_price.toFixed(2)}</td>
                        <td class="text-right font-mono">₹${t.exit_price.toFixed(2)}</td>
                        <td class="text-right font-mono">${t.shares}</td>
                        <td class="text-right font-mono ${isWin ? 'positive' : 'negative'}">
                            ${isWin ? '+' : ''}₹${t.pnl.toFixed(2)}
                        </td>
                        <td class="text-right font-mono ${isWin ? 'positive' : 'negative'}">
                            ${isWin ? '+' : ''}${t.pnl_pct.toFixed(2)}%
                        </td>
                    </tr>
                `;
            }).join('');
        }

        bindPaperTradingTab() {
            document.getElementById('btn-reset-portfolio')?.addEventListener('click', async () => {
                if (confirm('Are you sure you want to reset virtual paper trading to INR 10,00,000 capital?')) {
                    await window.API.resetPortfolio();
                    await this.refreshPortfolio();
                    await this.loadRiskMetrics();
                }
            });
        }

        async refreshPortfolio() {
            try {
                const res = await window.API.getPortfolio();
                if (res.success && res.portfolio) {
                    const p = res.portfolio;
                    
                    // Header pill
                    document.getElementById('header-cash-val').textContent = `₹${p.cash_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                    const headerPnl = document.getElementById('header-unrealized-pnl');
                    const isPos = p.unrealized_pnl >= 0;
                    headerPnl.textContent = `${isPos ? '+' : ''}₹${p.unrealized_pnl.toFixed(2)}`;
                    headerPnl.className = `pnl-val font-mono ${isPos ? 'positive' : 'negative'}`;

                    // Tab stats
                    document.getElementById('pt-total-val').textContent = `₹${p.total_portfolio_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                    document.getElementById('pt-cash-val').textContent = `₹${p.cash_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                    document.getElementById('pt-equity-val').textContent = `₹${p.holdings_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
                    
                    const unPnl = document.getElementById('pt-unrealized-pnl');
                    unPnl.textContent = `${isPos ? '+' : ''}₹${p.unrealized_pnl.toFixed(2)}`;
                    unPnl.className = `p-val font-mono ${isPos ? 'positive' : 'negative'}`;

                    const relPnl = document.getElementById('pt-realized-pnl');
                    const isRelPos = p.realized_pnl >= 0;
                    relPnl.textContent = `${isRelPos ? '+' : ''}₹${p.realized_pnl.toFixed(2)}`;
                    relPnl.className = `p-val font-mono ${isRelPos ? 'positive' : 'negative'}`;

                    document.getElementById('pt-holdings-count').textContent = `${p.holdings_count} POSITIONS`;

                    // Render holdings table
                    this.renderHoldingsTable(p.holdings);
                }

                // Render transactions ledger
                const txnRes = await window.API.getTransactions(50);
                if (txnRes.success && txnRes.transactions) {
                    this.renderTransactionsTable(txnRes.transactions);
                }
            } catch (err) {
                console.error('Failed to refresh portfolio:', err);
            }
        }

        renderHoldingsTable(holdings) {
            const tbody = document.getElementById('pt-holdings-tbody');
            if (!tbody) return;

            if (!holdings || !holdings.length) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center">No active positions. Place a virtual buy order to begin.</td></tr>';
                return;
            }

            tbody.innerHTML = holdings.map(h => {
                const isPos = h.unrealized_pnl >= 0;
                return `
                    <tr>
                        <td class="font-mono"><strong>${h.symbol}</strong></td>
                        <td>${h.name}</td>
                        <td class="text-right font-mono">${h.quantity}</td>
                        <td class="text-right font-mono">₹${h.avg_buy_price.toFixed(2)}</td>
                        <td class="text-right font-mono">₹${h.current_price.toFixed(2)}</td>
                        <td class="text-right font-mono">₹${h.current_value.toFixed(2)}</td>
                        <td class="text-right font-mono ${isPos ? 'positive' : 'negative'}">
                            ${isPos ? '+' : ''}₹${h.unrealized_pnl.toFixed(2)} (${isPos ? '+' : ''}${h.unrealized_pnl_pct.toFixed(2)}%)
                        </td>
                        <td class="text-right font-mono">${h.allocation_pct}%</td>
                        <td class="text-center">
                            <button class="btn-primary-action sell" style="height:24px;padding:0 8px;font-size:10px;"
                                onclick="window.quantexApp.quickSellHolding('${h.symbol}', ${h.quantity})">
                                SELL ALL
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        async quickSellHolding(symbol, quantity) {
            if (confirm(`Execute virtual SELL order for ${quantity} shares of ${symbol}?`)) {
                try {
                    const res = await window.API.placeOrder(symbol, 'SELL', quantity, 'Quick Sell from Holdings table');
                    if (res.success) {
                        alert(`Executed virtual SELL for ${quantity} shares of ${symbol}.`);
                        await this.refreshPortfolio();
                        await this.loadRiskMetrics();
                    } else {
                        alert(res.error || 'Failed to sell');
                    }
                } catch (err) {
                    alert(err.message);
                }
            }
        }

        renderTransactionsTable(txns) {
            const tbody = document.getElementById('pt-txns-tbody');
            if (!tbody) return;

            if (!txns || !txns.length) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center">No transaction records found.</td></tr>';
                return;
            }

            tbody.innerHTML = txns.map(t => {
                const isBuy = t.side === 'BUY';
                return `
                    <tr>
                        <td class="font-mono">${t.timestamp}</td>
                        <td class="font-mono"><strong>${t.symbol}</strong></td>
                        <td><span class="badge ${isBuy ? 'positive' : 'negative'}">${t.side}</span></td>
                        <td class="text-right font-mono">${t.quantity}</td>
                        <td class="text-right font-mono">₹${t.price.toFixed(2)}</td>
                        <td class="text-right font-mono">₹${t.fees.toFixed(2)}</td>
                        <td class="text-right font-mono">₹${t.total_amount.toFixed(2)}</td>
                        <td class="text-right font-mono ${t.realized_pnl >= 0 ? 'positive' : 'negative'}">
                            ${t.side === 'SELL' ? `₹${t.realized_pnl.toFixed(2)}` : '--'}
                        </td>
                        <td style="font-size:11px;color:#94A3B8;">${t.notes || '--'}</td>
                    </tr>
                `;
            }).join('');
        }

        async loadRiskMetrics() {
            try {
                const res = await window.API.getRiskMetrics();
                if (res.success && res.risk) {
                    const r = res.risk;
                    document.getElementById('risk-score-num').textContent = r.risk_score;
                    document.getElementById('risk-score-rating').textContent = r.risk_rating;
                    document.getElementById('risk-rating-badge').textContent = r.risk_rating.toUpperCase();

                    document.getElementById('risk-exposure-pct').textContent = `${r.equity_exposure_pct}%`;
                    document.getElementById('risk-cash-pct').textContent = `Cash: ${r.cash_pct}%`;

                    document.getElementById('risk-hhi-num').textContent = r.hhi_concentration;
                    document.getElementById('risk-hhi-level').textContent = r.concentration_level;

                    document.getElementById('risk-var-num').textContent = `-₹${r.var_95_daily_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

                    // Stress tests
                    const st = r.stress_tests;
                    if (st) {
                        document.getElementById('stress-2-loss').textContent = `-₹${st.market_down_2pct.loss_amount.toFixed(2)}`;
                        document.getElementById('stress-2-val').textContent = `Projected Val: ₹${st.market_down_2pct.projected_value.toFixed(2)}`;

                        document.getElementById('stress-5-loss').textContent = `-₹${st.market_down_5pct.loss_amount.toFixed(2)}`;
                        document.getElementById('stress-5-val').textContent = `Projected Val: ₹${st.market_down_5pct.projected_value.toFixed(2)}`;

                        document.getElementById('stress-10-loss').textContent = `-₹${st.market_down_10pct.loss_amount.toFixed(2)}`;
                        document.getElementById('stress-10-val').textContent = `Projected Val: ₹${st.market_down_10pct.projected_value.toFixed(2)}`;
                    }

                    // Warnings
                    const warnContainer = document.getElementById('risk-warnings-list');
                    if (warnContainer) {
                        if (r.warnings && r.warnings.length) {
                            warnContainer.innerHTML = r.warnings.map(w => `<div class="risk-alert">${w}</div>`).join('');
                        } else {
                            warnContainer.innerHTML = '<div style="color:#10B981;font-size:11px;">✔ All portfolio diversification and leverage metrics are within normal institutional risk tolerance parameters.</div>';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to load risk metrics:', err);
            }
        }

        refreshActiveData() {
            this.refreshPortfolio();
            this.loadRiskMetrics();
            this.loadChartData(this.activeSymbol, this.activeTimeframe);
        }
    }

    window.quantexApp = new QuantexApp();
});
