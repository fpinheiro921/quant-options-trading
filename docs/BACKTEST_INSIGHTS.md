# Professional Backtesting Insights - Applied

## Source: Backtest Wizard Flagship Trading Course

This document summarizes the professional backtesting insights extracted from the course and how they've been implemented in the enhanced backtesting engine.

---

## 🎯 Core Backtesting Principles

### 1. Market Type Filtering (Regime Detection)

**Insight:** Strategies perform differently in different market conditions. A momentum strategy should only trade in bullish regimes.

**Implementation:**
- `MarketRegimeDetector` class in `enhanced_backtest.py`
- Uses ROC (20-day Rate of Change) + ATR% (14-day Average True Range)
- Classifies market into 6 regimes:
  - `bull_strong` - Strong uptrend (ROC > 5%, low volatility)
  - `bull_weak` - Weak uptrend (ROC > 5%, high volatility)
  - `bear_strong` - Strong downtrend (ROC < -5%, low volatility)
  - `bear_weak` - Weak downtrend (ROC < -5%, high volatility)
  - `sideway_volatile` - Choppy sideways (ATR% > 3%)
  - `sideway_quiet` - Quiet sideways (ATR% < 1.5%)

**Code:**
```python
if regime.market_type not in [MarketType.BULL_STRONG, MarketType.BULL_WEAK]:
    continue  # Skip trade in non-bullish regime
```

---

### 2. Proper Position Sizing

**Insight:** Position size should be based on volatility (ATR), not fixed dollar amounts.

**Implementation:**
- `PositionSizer` class with 4 methods:
  1. **Fixed Fractional** - Risk 2% per trade with 5% stop
  2. **Fixed Ratio** - Ryan Jones method (increase size after profit accumulation)
  3. **Kelly Criterion** - Optimal f = (p*b - q) / b, using half-Kelly for safety
  4. **Volatility-Based** - Position = (Capital × Risk%) / (ATR × Multiplier)

**Formula:**
```
Position Size = (Account Value × Risk%) / (ATR × 2)

Example:
- Account: $100,000
- Risk per trade: 2% = $2,000
- ATR: $5
- Position Size = $2,000 / ($5 × 2) = 200 shares
```

---

### 3. Monte Carlo Simulation

**Insight:** Backtest results depend on trade order. Monte Carlo validates robustness by reshuffling trades.

**Implementation:**
- `MonteCarloSimulator` class with 1,000 simulations
- Reshuffles trade order randomly
- Reports:
  - Median return
  - Worst case (5th percentile)
  - Best case (95th percentile)
  - Probability of profit

**Interpretation:**
- If probability of profit > 60%, strategy is likely robust
- If worst case is acceptable, strategy is safe
- If median > 0, edge exists

---

### 4. Walk-Forward Analysis

**Insight:** Strategy should work on "unseen" data. Split data: 70% in-sample (training), 30% out-of-sample (testing).

**Implementation:**
- `WalkForwardAnalyzer` class
- Splits equity curve into in-sample and out-of-sample
- Checks consistency between periods

**Rules:**
- In-sample return should be positive
- Out-of-sample return should be positive or at least 50% of in-sample
- If strategy fails out-of-sample, it's overfit

---

### 5. Statistical Significance

**Insight:** A profitable backtest might be luck. Need statistical validation.

**Implementation:**
- One-sample t-test against zero mean
- P-value < 0.05 = statistically significant
- 95% confidence interval for mean return

**Code:**
```python
t_stat, p_value = stats.ttest_1samp(returns, 0)
is_significant = p_value < 0.05
```

---

### 6. Risk Metrics

**Standard metrics implemented:**

| Metric | Formula | Target |
|--------|---------|--------|
| **Sharpe Ratio** | (Return - RiskFree) / Volatility | > 1.0 |
| **Sortino Ratio** | (Return - RiskFree) / DownsideDev | > 1.0 |
| **Calmar Ratio** | AnnualReturn / MaxDrawdown | > 1.0 |
| **Max Drawdown** | Peak to Trough decline | < 20% |
| **VaR 95%** | 5th percentile of returns | < -2% |

---

### 7. Equity Curve Analysis

**Insights:**
- Smooth upward curve = good
- Large drawdowns = dangerous
- Long underwater periods = strategy struggles

**Implementation:**
- Underwater curve (drawdown % over time)
- Max drawdown duration tracking
- Monthly return distribution

---

### 8. Portfolio-Level Backtesting

**Insight:** Individual stock backtests don't account for correlation and portfolio effects.

**Current Status:** Framework in place for portfolio backtesting. Can extend to:
- Position correlation analysis
- Sector rotation
- Asset allocation
- Composite tickers (average of multiple stocks)

---

## 📊 Enhanced Metrics Summary

### Basic Metrics (Standard)
- Total Return
- Win Rate
- Number of Trades
- Average Winner/Loser

### Advanced Metrics (New)
- **Regime Performance** - Performance by market type
- **Sharpe/Sortino** - Risk-adjusted returns
- **Calmar** - Return vs max drawdown
- **Monte Carlo** - Robustness testing
- **Walk-Forward** - Out-of-sample validation
- **Statistical Significance** - P-value testing

---

## 🚀 Using the Enhanced Backtester

### Simple Example

```python
from backtest.enhanced_backtest import EnhancedMomentumBacktester
from backtest.paper_trading import create_paper_environment
from api import get_client

# Setup
client = get_client()
paper = create_paper_environment(100000.0)
backtester = EnhancedMomentumBacktester(paper)

# Get data
df = client.get_historical_candles('NVDA', '1Day', 252)

# Run backtest
result = backtester.run_backtest(
    symbol='NVDA',
    df=df,
    initial_capital=100000.0,
    risk_per_trade=0.02
)

# Print report
from backtest.enhanced_backtest import print_enhanced_report
print_enhanced_report(result)
```

---

## 🎯 Key Takeaways from Course

1. **Market Filtering is Critical**
   - Momentum strategies need bull markets
   - Mean reversion needs sideways markets
   - Trend following needs trending markets

2. **Position Sizing > Entry Rules**
   - 2% risk per trade is standard
   - ATR-based sizing adapts to volatility
   - Kelly Criterion optimizes growth

3. **Test Robustness, Not Just Profit**
   - Monte Carlo: Will it work with different trade orders?
   - Walk-Forward: Will it work on unseen data?
   - Statistical: Is it luck or skill?

4. **Risk Management First**
   - Max drawdown < 20%
   - Sharpe > 1.0
   - Always use stops

5. **Portfolio Context**
   - Single stock backtests are optimistic
   - Portfolio testing shows real-world performance
   - Correlation matters

---

## 📈 Recommended Workflow

1. **Screen symbols** by market regime (only bullish for momentum)
2. **Backtest individually** with enhanced metrics
3. **Filter strategies** that pass:
   - Win rate > 55%
   - Sharpe > 1.0
   - Max DD < 20%
   - MC probability of profit > 60%
   - Statistically significant (p < 0.05)
4. **Portfolio backtest** with top 5-10 symbols
5. **Paper trade** for 1-2 months
6. **Live trade** with 50% position size initially

---

## ✅ Implementation Status

| Feature | Status | File |
|---------|--------|------|
| Market Regime Detection | ✅ | `enhanced_backtest.py` |
| ATR-Based Position Sizing | ✅ | `enhanced_backtest.py` |
| Kelly Criterion | ✅ | `enhanced_backtest.py` |
| Monte Carlo Simulation | ✅ | `enhanced_backtest.py` |
| Walk-Forward Analysis | ✅ | `enhanced_backtest.py` |
| Statistical T-Test | ✅ | `enhanced_backtest.py` |
| Sharpe/Sortino/Calmar | ✅ | `enhanced_backtest.py` |
| VaR Calculation | ✅ | `enhanced_backtest.py` |
| Drawdown Analysis | ✅ | `enhanced_backtest.py` |
| Regime Performance | ✅ | `enhanced_backtest.py` |

---

## 📚 Course Lesson Mapping

| Lesson | Insight | Implementation |
|--------|---------|----------------|
| Lesson 04-05 | Amibroker Backtest | Core backtest engine |
| Lesson 06 | SetOptions | Position sizing, risk |
| Lesson 10 | ROC & ATR | Market regime detection |
| Lesson 13 | Market Type Filter | Regime filtering |
| Lesson 17-18 | Momentum Portfolios | Portfolio backtesting |
| Lesson 27 | MACD Strategies | Technical indicators |
| Lesson 28 | Choppiness Indicator | Volatility measurement |

---

**Your backtesting system now includes professional-grade features based on the Backtest Wizard methodology! 🎯**
