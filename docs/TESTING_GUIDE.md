# Testing & Backtesting Guide

## 🎯 3-Phase Testing Strategy

This system is designed to safely progress from paper testing to live trading through 3 phases:

### Phase 1: PAPER MODE (Local Simulation) ✅
**Status**: Ready to use immediately

```bash
# In .env file:
TRADING_MODE=paper
```

**What it does:**
- Simulates trades locally using historical data
- No connection to TastyTrade API for order execution
- Tracks P&L in local paper account (`paper_account.pkl`)
- Fast backtesting on historical data

**When to use:**
- Initial strategy development
- Testing new parameters
- Quick backtests on multiple symbols
- No API credentials needed (uses sample data)

**Commands:**
```bash
python cli.py paper              # Show paper account status
python cli.py paper reset        # Reset paper account
python cli.py backtest NVDA 30   # Backtest 30 days
```

---

### Phase 2: SANDBOX MODE (TastyTrade Test Environment) 🧪
**Status**: Requires sandbox credentials from TastyTrade

```bash
# In .env file:
TRADING_MODE=sandbox

# Add sandbox credentials (separate from live account):
TASTYTRADE_SANDBOX_USERNAME=your_sandbox_user
TASTYTRADE_SANDBOX_PASSWORD=your_sandbox_pass
```

**What it does:**
- Connects to TastyTrade's official sandbox environment
- Uses **test money** (not real funds)
- Real API behavior, realistic fills
- Access to live market data
- Orders appear in TastyTrade interface (marked as test)

**When to use:**
- Validating strategy with real market conditions
- Testing API integration
- Practicing execution timing
- Confirming results before live trading

**To get sandbox access:**
1. Contact TastyTrade support
2. Request developer sandbox credentials
3. Or use your live credentials on cert environment (if allowed)

**Test connection:**
```bash
python test_sandbox.py
```

---

### Phase 3: LIVE MODE (Real Money) 🔴
**Status**: ⚠️ DANGER - Only use after confirming good results

```bash
# In .env file:
TRADING_MODE=live
```

**What it does:**
- Connects to production TastyTrade API
- Uses **real money** for trades
- Requires manual confirmation before starting
- All orders are live and affect your account

**When to use:**
- Only after Phase 1 and Phase 2 show consistent profits
- When you're confident in strategy performance
- When risk management rules are validated

**Safety features:**
- Requires typing 'LIVE' to confirm on startup
- Clearly displays warning banners
- Position limits enforced (max 20% per symbol)
- Can instantly switch back to paper/sandbox

---

## 📊 Backtesting Commands

### Backtest Single Symbol
```bash
# Momentum Breakout (Compra a Seco)
python cli.py backtest NVDA 60
# Backtests last 60 days of 2-hour data

# Results show:
# - Total return
# - Win rate
# - Number of setups found
# - Profit factor
# - Max drawdown
```

### Paper Trading Status
```bash
python cli.py paper

# Shows:
# - Cash balance
# - Open positions
# - Trade history
# - P&L summary
```

### Reset Paper Account
```bash
python cli.py paper reset
# Resets to $100,000 starting balance
```

---

## 🔄 Quick Mode Switching

### Temporarily Override Mode
```bash
# Run dashboard in paper mode (regardless of .env)
python main.py --dashboard --mode paper

# Run dashboard in sandbox mode
python main.py --dashboard --mode sandbox

# ⚠️ Live mode requires confirmation
python main.py --dashboard --mode live
```

### Change Mode Permanently
Edit `.env` file:
```bash
# Change this line:
TRADING_MODE=paper
# to:
TRADING_MODE=sandbox
# or:
TRADING_MODE=live
```

---

## 📈 Expected Testing Progression

| Phase | Duration | Goal | Success Criteria |
|-------|----------|------|------------------|
| **Paper** | 1-2 weeks | Strategy validation | >60% win rate, positive expectancy |
| **Sandbox** | 2-4 weeks | Real market validation | Matches paper results, no execution issues |
| **Live** | Ongoing | Real profits | Consistent returns, drawdowns <20% |

---

## ⚠️ Safety Checklist Before Going Live

- [ ] Paper mode: 20+ trades with >60% win rate
- [ ] Sandbox mode: 20+ trades with similar results to paper
- [ ] Risk management tested (position sizing, stops)
- [ ] Understand maximum loss per trade (2% rule)
- [ ] Accept that losses are part of the strategy
- [ ] Have plan for when to stop (max daily/weekly loss)
- [ ] Start with small position sizes in live
- [ ] Never trade more than you can afford to lose

---

## 🆘 Emergency Procedures

### Stop All Trading Immediately
```bash
# 1. Kill the dashboard/CLI (Ctrl+C)
# 2. Switch to paper mode
edit .env  # Change TRADING_MODE=paper

# 3. Verify positions closed in TastyTrade app
```

### Switch Back to Safe Mode
```bash
# Switch to paper
python main.py --mode paper

# Or switch to sandbox
python main.py --mode sandbox
```

---

## 📊 Performance Benchmarks

### Wheel Strategy
- **Target Win Rate**: >70% (time decay works in your favor)
- **Expected Return**: 1-3% monthly on deployed capital
- **Max Drawdown**: <15%
- **Ideal Market**: Sideways to slightly bullish

### Compra a Seco (Momentum Breakout)
- **Target Win Rate**: >55% (momentum trading)
- **Expected Return**: 2-5% monthly (higher volatility)
- **Max Drawdown**: <20%
- **Ideal Market**: Strong trends, bull runs

---

## 🔧 Configuration Reference

### .env File Template
```env
# Trading Mode (CRITICAL)
TRADING_MODE=paper          # Options: paper, sandbox, live

# Live Account (for sandbox or live mode)
TASTYTRADE_USERNAME=your_live_username
TASTYTRADE_PASSWORD=your_live_password

# Sandbox Account (optional, separate from live)
TASTYTRADE_SANDBOX_USERNAME=your_sandbox_user
TASTYTRADE_SANDBOX_PASSWORD=your_sandbox_pass

# Paper Trading
PAPER_STARTING_BALANCE=100000.00

# API URLs
TASTYTRADE_API_URL=https://api.tastytrade.com
TASTYTRADE_SANDBOX_URL=https://api.cert.tastytrade.com
```

---

## 🎓 Testing Best Practices

1. **Start Small**: Begin with 1-2 symbols in paper mode
2. **Track Everything**: Log all trades, emotions, market conditions
3. **Be Honest**: Don't cherry-pick results, include all trades
4. **Test Different Markets**: Bull, bear, sideways conditions
5. **Time Commitment**: Strategies need 20+ trades for statistical validity
6. **Don't Rush**: Spend at least 2 weeks in each phase
7. **Review Regularly**: Weekly performance reviews

---

## 📞 Getting Help

- **TastyTrade Sandbox**: Contact support for sandbox credentials
- **API Issues**: Check TastyTrade API documentation
- **Strategy Questions**: Review the 5 papers that built quant finance
- **Bug Reports**: Check logs in console output

---

**Remember**: The goal is consistent, disciplined execution. Never rush to live trading.
