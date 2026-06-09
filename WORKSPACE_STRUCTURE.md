# Workspace Structure

Organized for clarity and ease of navigation.

## Quick Navigation

| Folder | Purpose |
|--------|---------|
| `ACCOUNT_GROWTH/` | Growth plans and phase trackers |
| `scripts/weekly_breakout/` | Weekly breakout strategy scripts |
| `scripts/momentum/` | Momentum strategy scripts |
| `scripts/data/` | Data download scripts |
| `scripts/archive/` | Old/deprecated scripts |
| `reports/weekly_breakout/` | Weekly breakout backtest reports |
| `reports/momentum/` | Momentum backtest reports |
| `docs/` | Documentation and guides |
| `data/` | Cached market data |
| `backtest/` | Core backtest engine modules |
| `api/` | API endpoints and integrations |
| `dashboard/` | Dashboard UI |
| `models/` | Data models |
| `trading/` | Live trading modules |
| `utils/` | Utility functions |

## Root Files

| File | Purpose |
|------|---------|
| `README.md` | Main project readme |
| `WORKSPACE_STRUCTURE.md` | This file |
| `config.py` | Configuration |
| `cli.py` | Command line interface |
| `main.py` | Main entry point |
| `requirements.txt` | Python dependencies |
| `.env` | Environment variables |
| `.env.example` | Environment template |
| `.gitignore` | Git ignore rules |

## Account Growth

**Start here if you have a small account:**
`ACCOUNT_GROWTH/150_TO_PORTFOLIO_MASTER_PLAN.md`

## Running Backtests

### Weekly Breakout
```powershell
# AAPL with -2% stop
python "h:\QUANT TRADING\scripts\weekly_breakout\enhanced_aapl_minus2_stop.py"

# Top 5 cheap SP500 individually
python "h:\QUANT TRADING\scripts\weekly_breakout\enhanced_top5_individual.py"

# Top 5 cheap SP500 combined
python "h:\QUANT TRADING\scripts\weekly_breakout\enhanced_top5_sp500.py"
```

### Download Data
```powershell
# Download cheap SP500 stocks
python "h:\QUANT TRADING\scripts\data\download_sp500_cheap.py"
```

## Reports Location

All reports are organized by strategy:
- Weekly Breakout: `reports/weekly_breakout/`
- Momentum: `reports/momentum/`

## Data Cache

Downloaded stock data cached at:
`data/massive_cache/stocks/{SYMBOL}/1d_5y.csv`
