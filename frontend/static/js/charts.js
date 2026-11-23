/**
 * QUANTEX Financial Charting Engine
 * High-performance HTML5 Canvas Candlestick & Volume chart with MA overlays and crosshairs.
 */
class FinancialChart {
    constructor(canvasId, tooltipId) {
        this.canvas = document.getElementById(canvasId);
        this.tooltip = document.getElementById(tooltipId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        
        this.candles = [];
        this.overlays = { sma20: [], sma50: [], ema20: [] };
        this.showSMA20 = true;
        this.showSMA50 = true;
        this.showEMA20 = false;

        this.mousePos = null;
        this.hoverIndex = -1;

        if (this.canvas) {
            this.setupEvents();
            this.handleResize();
            window.addEventListener('resize', () => this.handleResize());
        }
    }

    handleResize() {
        if (!this.canvas) return;
        const rect = this.canvas.parentElement.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.width = rect.width;
        this.height = rect.height;
        this.canvas.width = this.width * dpr;
        this.canvas.height = this.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.render();
    }

    setupEvents() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.mousePos = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
            this.render();
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.mousePos = null;
            this.hoverIndex = -1;
            if (this.tooltip) this.tooltip.classList.add('hidden');
            this.render();
        });
    }

    setData(candles, overlays = {}) {
        this.candles = candles || [];
        this.overlays = overlays || {};
        this.render();
    }

    setOverlaysVisibility(sma20, sma50, ema20) {
        this.showSMA20 = sma20;
        this.showSMA50 = sma50;
        this.showEMA20 = ema20;
        this.render();
    }

    render() {
        if (!this.ctx || !this.width || !this.height) return;
        const ctx = this.ctx;
        const W = this.width;
        const H = this.height;

        // Clear Canvas
        ctx.fillStyle = '#0C1117';
        ctx.fillRect(0, 0, W, H);

        if (!this.candles.length) {
            ctx.fillStyle = '#64748B';
            ctx.font = '12px Inter';
            ctx.textAlign = 'center';
            ctx.fillText('Loading financial market candlesticks...', W / 2, H / 2);
            return;
        }

        const paddingRight = 70;
        const paddingBottom = 26;
        const chartW = W - paddingRight;
        const totalH = H - paddingBottom;
        const priceH = totalH * 0.74;
        const volH = totalH * 0.22;
        const volTop = totalH * 0.78;

        const count = this.candles.length;
        const candleW = Math.max(2, Math.floor(chartW / count) - 2);
        const slotW = chartW / count;

        // Min & Max Price Bounds
        let minPrice = Infinity;
        let maxPrice = -Infinity;
        let maxVol = 0;

        for (const c of this.candles) {
            if (c.low < minPrice) minPrice = c.low;
            if (c.high > maxPrice) maxPrice = c.high;
            if (c.volume > maxVol) maxVol = c.volume;
        }

        const priceRange = (maxPrice - minPrice) || 1;
        const paddedMin = minPrice - (priceRange * 0.05);
        const paddedMax = maxPrice + (priceRange * 0.05);
        const paddedRange = paddedMax - paddedMin;

        const getY = (val) => priceH - ((val - paddedMin) / paddedRange) * priceH;

        // Draw Price Grid lines
        ctx.strokeStyle = '#18222D';
        ctx.lineWidth = 1;
        ctx.font = '10px JetBrains Mono';
        ctx.fillStyle = '#64748B';
        ctx.textAlign = 'left';

        const gridSteps = 5;
        for (let i = 0; i <= gridSteps; i++) {
            const p = paddedMin + (paddedRange * (i / gridSteps));
            const y = getY(p);
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(chartW, y);
            ctx.stroke();
            ctx.fillText(`₹${p.toFixed(2)}`, chartW + 8, y + 3);
        }

        // Draw Volume Bars
        for (let i = 0; i < count; i++) {
            const c = this.candles[i];
            const x = i * slotW + (slotW / 2);
            const isBull = c.close >= c.open;
            const barH = (c.volume / (maxVol || 1)) * volH;
            const barY = H - paddingBottom - barH;

            ctx.fillStyle = isBull ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)';
            ctx.fillRect(x - (candleW / 2), barY, candleW, barH);
        }

        // Draw Candlesticks
        for (let i = 0; i < count; i++) {
            const c = this.candles[i];
            const x = i * slotW + (slotW / 2);
            const isBull = c.close >= c.open;
            const color = isBull ? '#10B981' : '#F43F5E';

            const openY = getY(c.open);
            const closeY = getY(c.close);
            const highY = getY(c.high);
            const lowY = getY(c.low);

            // Wick
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.2;
            ctx.beginPath();
            ctx.moveTo(x, highY);
            ctx.lineTo(x, lowY);
            ctx.stroke();

            // Candle Body
            const bodyY = Math.min(openY, closeY);
            const bodyH = Math.max(2, Math.abs(openY - closeY));
            ctx.fillStyle = color;
            ctx.fillRect(x - (candleW / 2), bodyY, candleW, bodyH);
        }

        // Draw Indicator Overlays
        const drawLine = (series, color) => {
            if (!series || !series.length) return;
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.4;
            ctx.beginPath();
            let started = false;

            for (let i = 0; i < series.length && i < count; i++) {
                const val = series[i];
                if (val !== null && val !== undefined && !isNaN(val)) {
                    const x = i * slotW + (slotW / 2);
                    const y = getY(val);
                    if (!started) {
                        ctx.moveTo(x, y);
                        started = true;
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
            }
            ctx.stroke();
        };

        if (this.showSMA20 && this.overlays.sma20) drawLine(this.overlays.sma20, '#38BDF8');
        if (this.showSMA50 && this.overlays.sma50) drawLine(this.overlays.sma50, '#F59E0B');
        if (this.showEMA20 && this.overlays.ema20) drawLine(this.overlays.ema20, '#A855F7');

        // Draw Dates on X-axis
        ctx.fillStyle = '#64748B';
        ctx.font = '10px JetBrains Mono';
        ctx.textAlign = 'center';
        const dateInterval = Math.max(1, Math.floor(count / 6));
        for (let i = 0; i < count; i += dateInterval) {
            const c = this.candles[i];
            const x = i * slotW + (slotW / 2);
            ctx.fillText(c.date, x, H - 8);
        }

        // Crosshair & Tooltip Handling
        if (this.mousePos && this.mousePos.x < chartW && this.mousePos.y < totalH) {
            const hoverIdx = Math.min(count - 1, Math.max(0, Math.floor(this.mousePos.x / slotW)));
            const candle = this.candles[hoverIdx];

            // Draw Crosshairs
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            // Vertical
            ctx.moveTo(this.mousePos.x, 0);
            ctx.lineTo(this.mousePos.x, totalH);
            // Horizontal
            ctx.moveTo(0, this.mousePos.y);
            ctx.lineTo(chartW, this.mousePos.y);
            ctx.stroke();
            ctx.setLineDash([]);

            // Show Tooltip
            if (this.tooltip && candle) {
                this.tooltip.classList.remove('hidden');
                this.tooltip.style.left = `${Math.min(W - 190, this.mousePos.x + 15)}px`;
                this.tooltip.style.top = `${Math.min(H - 140, Math.max(10, this.mousePos.y - 40))}px`;
                
                const change = candle.close - candle.open;
                const changePct = ((change / candle.open) * 100).toFixed(2);
                const isBull = change >= 0;

                this.tooltip.innerHTML = `
                    <div style="font-weight:700;color:#94A3B8;margin-bottom:4px;">${candle.date}</div>
                    <div>O: <span style="color:#FFF">₹${candle.open.toFixed(2)}</span></div>
                    <div>H: <span style="color:#FFF">₹${candle.high.toFixed(2)}</span></div>
                    <div>L: <span style="color:#FFF">₹${candle.low.toFixed(2)}</span></div>
                    <div>C: <span style="color:${isBull ? '#10B981':'#F43F5E'}">₹${candle.close.toFixed(2)}</span></div>
                    <div>Vol: <span style="color:#FFF">${candle.volume.toLocaleString()}</span></div>
                `;
            }
        }
    }
}

window.FinancialChart = FinancialChart;
