# MARKET DATA SOURCES & RESILIENCE ARCHITECTURE

## 1. Provider Adapter Architecture

QUANTEX connects to market data through `YahooMarketDataProvider` which inherits from `MarketDataProvider`.

Supported Indian equity symbols:
- `RELIANCE.NS` (Reliance Industries Ltd - Energy)
- `TCS.NS` (Tata Consultancy Services Ltd - IT)
- `INFY.NS` (Infosys Ltd - IT)
- `HDFCBANK.NS` (HDFC Bank Ltd - Banking)
- `ICICIBANK.NS` (ICICI Bank Ltd - Banking)
- `SBIN.NS` (State Bank of India - PSU Bank)
- `ITC.NS` (ITC Ltd - FMCG)
- `LT.NS` (Larsen & Toubro Ltd - Infrastructure)
- `TATAMOTORS.NS` (Tata Motors Ltd - Auto)
- `BHARTIARTL.NS` (Bharti Airtel Ltd - Telecom)

---

## 2. Multi-Tier Caching & Resiliency Strategy

```
Client Request -> [ Check SQLite Cache ] -> (Valid TTL < 300s?) -> Return Cached Data
                           │
                          No
                           │
                           ▼
                  [ Query yfinance API ]
                           │
                 ┌─────────┴─────────┐
                 │                   │
              Success              Failure / Timeout
                 │                   │
                 ▼                   ▼
         [ Cache & Return ]   [ Fallback to Geometric Brownian Motion Generator ]
```

---

## 3. Data Transparency & Status Labels

Every data response carries an explicit status flag:
- `delayed`: Live historical data fetched from Yahoo Finance (15-20 min delayed).
- `cached`: Data served from the local SQLite cache within the TTL window.
- `sample`: Generated via deterministic Geometric Brownian Motion anchored to benchmark prices when external networks are unreachable.

*QUANTEX never labels delayed or simulated data as live exchange feeds.*
