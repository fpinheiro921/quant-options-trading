# Quant Trading Workspace - Clean & Organized

## 📁 Directory Overview

```
H:\QUANT TRADING/
│
├── api/                    # API clients (internal modules)
├── backtest/               # Backtesting engine (internal modules)
├── dashboard/              # Web dashboard (internal modules)
├── data/                   # Cached data (43 symbols)
├── models/                 # Pricing & analysis (internal modules)
├── reports/                # Backtest reports (final only)
├── scripts/                # Executable scripts ⭐
├── trading/                # Strategies (internal modules)
├── templates/              # HTML templates
├── utils/                  # Utility functions
│
├── cli.py                  # Main CLI entry point ⭐
├── main.py                 # Dashboard server ⭐
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── .env                    # API keys (not committed)
│
├── README.md               # Project overview
├── QUICKSTART.md           # Getting started
├── WORKSPACE_STRUCTURE.md  # This file
│
└── .gitignore              # Git exclusions
```

---

## 🎯 How to Use This Workspace

### Quick Start (Most Common)

```bash
# Check what data is cached
python scripts/check_cache.py

# Run portfolio Wheel backtest (43 stocks, ONE position)
python scripts/backtest_wheel_portfolio.py

# Run 2-year backtest on any symbol
python scripts/backtest_2year.py NVDA

# Download more data
python scripts/download_portfolio_data.py --symbols JPM V

# Interactive CLI mode
python cli.py
```

### For Developers

```bash
# Start dashboard server
python main.py

# Check API connection
python -c "from api.alpaca_client import AlpacaClient; ..."
```

---

## 📂 Directory Details

### `/scripts/` - Executable Scripts ⭐
**Your main entry points for backtesting:**

| Script | Purpose | Example |
|--------|---------|---------|
| `backtest_wheel_portfolio.py` | Portfolio Wheel (43 stocks) | `python scripts/backtest_wheel_portfolio.py` |
| `backtest_2year.py` | 2-year comprehensive backtest | `python scripts/backtest_2year.py NVDA` |
| `backtest_report.py` | Generate comparison report | `python scripts/backtest_report.py TSLA 30` |
| `download_portfolio_data.py` | Download symbol data | `python scripts/download_portfolio_data.py --symbols AMD` |
| `check_cache.py` | Check cached symbols | `python scripts/check_cache.py` |

### `/api/` - API Clients (Internal)
- `alpaca_client.py` - Alpaca trading & data
- `massive_client.py` - Massive.com API wrapper
- `__init__.py` - Module exports

### `/backtest/` - Backtesting Engine (Internal)
- `backtest_engine.py` - Core backtesting (Wheel & Momentum)
- `enhanced_backtest.py` - Monte Carlo, walk-forward analysis
- `paper_trading.py` - Paper trading simulation

### `/data/` - Local Data Cache
```
data/
└── massive_cache/
    └── stocks/
        ├── AAPL/
        │   ├── 1d_3y.csv    # 3 years daily
        │   └── 1h_2y.csv    # 2 years hourly
        ├── NVDA/
        └── ... (43 symbols total)
```

### `/reports/` - Final Reports Only
**Principle:** Only successful, properly-configured backtests

| Report | Strategy | Result |
|--------|----------|--------|
| `portfolio_wheel_*.md` | Wheel (43 stocks, ONE position) | +7.58% |
| `backtest_2year_NVDA_*.md` | Wheel + Momentum 2-year | Wheel +9.45%, Momentum +1.36% |
| `backtest_comparison_*.md` | Side-by-side comparison | - |
| `backtest_momentum_*.md` | Momentum 30-day | +61.07% |
| `backtest_wheel_*.md` | Wheel 30-day | - |

### `/trading/` - Strategy Implementations (Internal)
- `wheel_strategy.py` - The Wheel strategy
- `momentum_breakout.py` - Compra a Seco momentum
- `strike_resolver.py` - Option strike selection

### `/models/` - Financial Models (Internal)
- `technical_analysis.py` - EMA, candlestick patterns
- `pricing.py` - Black-Scholes, option pricing

---

## 📊 Data Cache Summary

| Metric | Value |
|--------|-------|
| **Total Symbols** | 83 |
| **Daily Data** | 3-5 years per symbol |
| **Hourly Data** | 2 years per symbol |
| **Format** | CSV files |
| **Location** | `data/massive_cache/stocks/` |
| **Source** | yfinance primary, Massive API fallback |

### Symbol Categories
- **Tech:** AAPL, MSFT, NVDA, AMD, TSLA, AMZN, GOOGL, META, NFLX
- **Blue Chip:** JPM, JNJ, V, MA, PG, UNH, HD, BAC, XOM
- **Dividend:** WMT, PFE, CVX, KO, PEP, WFC
- **Tech Legacy:** CSCO, INTC, VZ, DIS, ADBE, CRM, NKE, CMCSA
- **ETFs:** QQQ, SPY, IWM, XLK, XLF, XLE
- **Growth:** PLTR, COIN, RBLX, SNOW, CRWD

---

## 🎯 Strategy Descriptions

---

### 1. WHEEL STRATEGY (Options Selling)

**What it is:**
A conservative options strategy where you sell cash-secured puts to collect premium, and if assigned, sell covered calls on the shares.

**How it works:**

| Phase | Action | Goal |
|-------|--------|------|
| **Phase 1** | Sell 20 Delta put (6% OTM) | Collect premium (~$500-$1000/month) |
| **If assigned** | Buy 100 shares at strike | Own the stock at a discount |
| **Phase 2** | Sell covered call above cost basis | Collect more premium |
| **If called away** | Sell shares at profit | Cash + premium collected |

**Key Rules:**
- ✅ **ONE position at a time** across the portfolio
- ✅ **20 Delta puts** = ~80% win probability
- ✅ **Monthly expiration** (30 DTE)
- ✅ **Never sell calls below cost basis** (protects against losses)
- ✅ **Portfolio rotation** - scan 20 symbols, pick best opportunity

**Position Sizing:**
- Max 30% of capital per position
- Premium collected adds to capital

---

### 2. COMPRA A SECO (Momentum Options)

**What it is:**
An intraday momentum strategy that detects explosive breakouts using candlestick patterns on 2-hour charts, then buys ATM calls for leveraged upside.

**Pattern Detection (4 Steps):**

| Step | What Happens | Signal |
|------|-------------|--------|
| **1. Trend** | Price above rising EMA 8 & EMA 80 | Bull run confirmed |
| **2. Propulsion** | Large bullish candle (2x average size, close near high) | Momentum surge |
| **3. Pin Bar** | Small body candle (indecision) | Consolidation |
| **4. Breakout** | Next candle breaks above pin bar high | **ENTRY SIGNAL** |

**Trade Execution:**

| Parameter | Rule |
|-----------|------|
| **Entry** | Buy ATM Call (30 DTE) when breakout detected |
| **Premium** | ~4% of stock price |
| **Stop Loss** | Sell if stock hits pin bar LOW |
| **Take Profit** | Sell if stock hits 2x propulsion amplitude |
| **Time Stop** | Sell on Thursday of expiration week |

**Position Sizing:**
- Fixed risk per trade: 2% of initial capital ($1,000 on $50K)
- Risk = premium paid (max loss on long call)
- No compounding - consistent risk across all trades

**Why Options Instead of Stock:**
- **Leverage:** Control 100 shares per contract with limited capital
- **Defined Risk:** Maximum loss = premium paid
- **Higher Returns:** Options amplify moves (delta ~0.5)

---

### Risk Management (Both Strategies)
- Max 30% capital per position (Wheel)
- Fixed $1,000 risk per trade (Momentum)
- Independent operation - no interference between strategies
- $50K capital per strategy ($100K total)

---

### Portfolio Configurations (6 Options)

| Portfolio | Symbols | Best For |
|-----------|---------|----------|
| **NASDAQ** | AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, NFLX, AMD, ADBE, CRM, CSCO, INTC, PLTR, COIN, RBLX, SNOW, CRWD, QQQ | Tech-heavy growth |
| **S&P 500** | AAPL, MSFT, AMZN, GOOGL, JPM, JNJ, V, PG, UNH, HD, MA, BAC, ABBV, PFE, KO, PEP, WMT, DIS, SPY, XOM | Blue chip stability |
| **High Volatility** | TSLA, NVDA, PLTR, COIN, RBLX, SNOW, CRWD, AMD, SQ, SHOP, UPST, SOFI, LCID, RIVN, GME, AMC, MRNA, ARKK, TQQQ, NET | Aggressive growth |
| **Dividend** | JNJ, PG, KO, PEP, WMT, MCD, TGT, COST, LOW, HD, VZ, T, XOM, CVX, BMY, ABBV, MSFT, AAPL, CSCO, INTC | Income + stability |
| **Sector** | NVDA, MSFT, AAPL, JPM, V, BLK, JNJ, UNH, ABBV, AMZN, WMT, KO, XOM, CVX, CAT, GE, GOOGL, VZ, LIN, AMT | Sector diversification |
| **Small Cap** | AVAV, DKNG, HOOD, AFRM, TOST, BILL, ASAN, MDB, TWLO, OKTA, ZI, HUBS, FSLY, ESTC, SPLK, DOCU, PD, S, CYBR, IWM | Small growth companies |

---

## 🗑️ Cleanup History

### Deleted Files
| Type | Count | Examples |
|------|-------|----------|
| Test files | 6 | `test_*.py` |
| Old reports | 19 | Failed/duplicate JSONs |
| Outdated docs | 1 | `TASTYTRADE_API_INFO.md` |

### Moved Files
- All backtest scripts → `/scripts/`
- All reports → `/reports/`

---

## ✅ Workspace Status

| Category | Status | Details |
|----------|--------|---------|
| Scripts | ✅ 5 executables in `/scripts/` | Ready to run |
| Modules | ✅ 6 internal packages | api, backtest, models, etc. |
| Data | ✅ 43 symbols cached | ~50 MB total |
| Reports | ✅ 5 final reports | In `/reports/` |
| Docs | ✅ 5 markdown files | README, QUICKSTART, etc. |

**Total:** ~40 core files, clean & organized  
**Ready for:** Production backtesting  

---

*Last updated: 2026-05-10*
