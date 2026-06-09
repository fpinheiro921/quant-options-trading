# Quick Start Guide - Quant Options Trading System

Get up and running in 5 minutes with the sandbox/backtesting environment.

---

## 🚀 3-Step Quick Start

### Step 1: Verify Installation (30 seconds)

```bash
# Check all files compile
python test_backtest.py
```

**Expected output:**
```
======================================================================
BACKTEST SYSTEM QUICK TEST
======================================================================

1️⃣ Testing Paper Trading Environment...
   ✅ Paper trading environment created
   ✅ Cash: $100,000.00
   ✅ Trades: 0
   ✅ P&L: $0.00

2️⃣ Testing Backtest Engine...
   ✅ Backtest engine imports successful
   ✅ BacktestResult created
   📊 Sample result: +5.0% return

3️⃣ Testing Configuration...
   ✅ Trading Mode: paper
   ✅ Paper Balance: $100,000.00
   ✅ API URL: https://api.tastyworks.com
   ✅ Available modes: paper, sandbox, live

4️⃣ Testing CLI Commands...
   ✅ CLI module loaded
   ✅ Commands available: status, wheel, analyze, risk, recommend, momentum, paper, backtest

======================================================================
✅ BACKTEST SYSTEM READY
======================================================================
```

---

### Step 2: Test Connection (1 minute)

```bash
# Test your TastyTrade credentials
python test_connection.py
```

**If successful:**
```
✅ AUTHENTICATION SUCCESSFUL!

💰 Account Balance:
   Cash Available: $XX,XXX.XX
   Net Liquidating: $XX,XXX.XX
   Buying Power: $XX,XXX.XX

✅ ALL SYSTEMS READY!
```

**If authentication fails:**
- Check credentials in `.env`
- Verify you're using the correct API URL (tastyworks.com)
- See [TASTYTRADE_API_INFO.md](TASTYTRADE_API_INFO.md) for troubleshooting

---

### Step 3: Run Your First Backtest (2 minutes)

```bash
# Backtest momentum strategy on NVDA for 30 days
python cli.py backtest NVDA 30
```

**Interactive prompts:**
```
======================================================================
  📊 STRATEGY BACKTEST
======================================================================

Symbol:        NVDA
Lookback:      30 days
Starting Cap:  $100,000

Select strategy:
  1. Wheel (Cash-secured puts → Covered calls)
  2. Compra a Seco (Momentum breakout)

Enter choice (1 or 2): 2
```

**Sample results:**
```
======================================================================
  BACKTEST RESULTS
======================================================================

Strategy:       Compra a Seco (Momentum Breakout)
Period:         2026-04-10 to 2026-05-10
Initial:        $100,000.00
Final:          $105,250.00
Return:         🟢 +5.25%

Total Trades:   8
Win Rate:       62.5%
Winners:        5
Losers:         3
Avg Trade:      $656.25

Max Drawdown:   3.20%
Sharpe Ratio:   1.85

TRADE LIST
  2026-04-15: buy NVDA @150.00
  2026-04-16: sell NVDA @155.00 | 🟢 $500.00
  ...

Save backtest report to file? (yes/no): yes
✅ Report would be saved to: backtest_NVDA_30d_20260510_143000.json
```

---

## 📊 Common Workflows

### Workflow 1: Paper Trading Testing

```bash
# 1. Check paper account
python cli.py paper

# 2. Reset if needed
python cli.py paper reset

# 3. Run backtest to populate with simulated trades
python cli.py backtest NVDA 30
python cli.py backtest AAPL 30
python cli.py backtest TSLA 30

# 4. Check results
python cli.py paper
```

### Workflow 2: Multi-Symbol Backtest

```bash
# Create a script for multiple symbols
cat > backtest_multiple.py << 'EOF'
import subprocess
import sys

symbols = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'AMD']
days = 60

for symbol in symbols:
    print(f"\n{'='*60}")
    print(f"Backtesting {symbol}...")
    print('='*60)
    subprocess.run([sys.executable, 'cli.py', 'backtest', symbol, str(days)])
EOF

python backtest_multiple.py
```

### Workflow 3: Start Dashboard

```bash
# Start web interface
python main.py --dashboard

# Or specify port
python main.py --dashboard --port 8080

# With debug mode
python main.py --dashboard --debug
```

Access at: `http://localhost:5000` (or your specified port)

---

## 🔧 Configuration Reference

### Environment Variables (`.env`)

```env
# CRITICAL: Trading Mode
TRADING_MODE=paper              # Options: paper, sandbox, live

# TastyTrade Credentials
TASTYTRADE_USERNAME=your_username
TASTYTRADE_PASSWORD=your_password
TASTYTRADE_ACCOUNT_ID=           # Optional, auto-detected

# Sandbox Credentials (separate from live)
TASTYTRADE_SANDBOX_USERNAME=    # Get from developer.tastytrade.com
TASTYTRADE_SANDBOX_PASSWORD=

# Paper Trading
PAPER_STARTING_BALANCE=100000.00
PAPER_SAVE_FILE=paper_account.pkl

# API Configuration (FIXED - per official docs)
TASTYTRADE_API_URL=https://api.tastyworks.com
TASTYTRADE_SANDBOX_URL=https://api.cert.tastyworks.com
TASTYTRADE_DXFEED_URL=wss://tasty-open-api-ws.dxfeed.com/realtime
API_USER_AGENT=QuantOptionsBot/1.0

# Trading Parameters
DEFAULT_DELTA_THRESHOLD=0.30
MIN_PREMIUM_THRESHOLD=0.50
MAX_POSITION_PCT=0.20
RISK_FREE_RATE=0.045
```

---

## 🧪 Available Commands

### CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `status` | Account status | `python cli.py status` |
| `wheel` | Wheel strategy status | `python cli.py wheel` |
| `analyze` | Analyze symbol | `python cli.py analyze NVDA` |
| `risk` | Risk analysis | `python cli.py risk` |
| `recommend` | Get recommendations | `python cli.py recommend NVDA AAPL` |
| `momentum` | Momentum strategy info | `python cli.py momentum NVDA` |
| `paper` | Paper trading status | `python cli.py paper` |
| `paper reset` | Reset paper account | `python cli.py paper reset` |
| `backtest` | Run backtest | `python cli.py backtest NVDA 30` |

### Main Commands

| Command | Description |
|---------|-------------|
| `--dashboard` | Start web dashboard |
| `--cli` | Run CLI mode |
| `--check` | Check configuration |
| `--analyze SYMBOL` | Analyze symbol |
| `--mode MODE` | Override trading mode |

---

## 📡 API Endpoints

### Paper Trading
- `GET /api/paper/status` - Account status
- `POST /api/paper/reset` - Reset account
- `GET /api/paper/trades` - Trade history
- `GET /api/paper/positions` - Open positions

### Backtesting
- `POST /api/backtest/run` - Run backtest
- `GET /api/backtest/history` - Backtest history

### Wheel Strategy
- `GET /api/wheel/status` - Strategy status
- `GET /api/wheel/analyze/<symbol>` - Symbol analysis
- `GET /api/wheel/risk` - Risk metrics

### Momentum Strategy
- `GET /api/momentum/status` - Strategy status
- `GET /api/momentum/watchlist` - Get watchlist
- `POST /api/momentum/watchlist` - Update watchlist
- `GET /api/momentum/setups/<symbol>` - Scan for setups
- `GET /api/momentum/performance` - Performance metrics
- `GET /api/momentum/trades` - Active trades

See [API_ENDPOINTS.md](API_ENDPOINTS.md) for full documentation.

---

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError`
```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue: Authentication Failed
```bash
# Check credentials
python test_connection.py

# Verify API URL in .env
cat .env | grep TASTYTRADE_API_URL
# Should show: https://api.tastyworks.com (not tastytrade.com)
```

### Issue: `invalid_credentials`
- Using sandbox credentials on production API (or vice versa)
- Solution: Use correct credentials for each environment

### Issue: `unconfirmed_user`
- Email not confirmed within 3 days
- Solution: 
```bash
curl -X POST https://api.cert.tastyworks.com/confirmation \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'
```

### Issue: Port already in use
```bash
# Use different port
python main.py --dashboard --port 8080
```

---

## 📚 Next Steps

1. **Read Documentation**
   - [TESTING_GUIDE.md](TESTING_GUIDE.md) - Complete testing guide
   - [TASTYTRADE_API_INFO.md](TASTYTRADE_API_INFO.md) - API documentation
   - [API_ENDPOINTS.md](API_ENDPOINTS.md) - REST API reference

2. **Run Tests**
   ```bash
   python test_backtest.py      # System test
   python test_connection.py    # API connection
   python test_sandbox.py       # Sandbox (if available)
   ```

3. **Explore Strategies**
   ```bash
   # Wheel Strategy
   python cli.py wheel
   python cli.py analyze SPY
   
   # Momentum Strategy
   python cli.py momentum NVDA
   python cli.py backtest NVDA 60
   ```

4. **Start Dashboard**
   ```bash
   python main.py --dashboard
   ```

---

## 🎯 Progression Path

```
Week 1-2:  PAPER mode
           - Test strategies on multiple symbols
           - Validate 60%+ win rate
           - Understand drawdown periods

Week 3-4:  SANDBOX mode (if available)
           - Real API behavior
           - 15-min delayed quotes
           - Test money only

Week 5+:   LIVE mode (with caution!)
           - Real money trading
           - Start with small positions
           - Gradually scale up
```

---

## ⚠️ Safety Reminders

- ✅ Default is `TRADING_MODE=paper` (safe)
- ✅ Visual warnings for LIVE mode
- ✅ Confirmation required before LIVE trading
- ✅ Position limits enforced (20% max per symbol)
- ✅ Never trade more than you can afford to lose

---

**You're ready to start! Run `python test_backtest.py` to verify everything works.** 🚀
