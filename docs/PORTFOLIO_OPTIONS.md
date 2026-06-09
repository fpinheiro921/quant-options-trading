# 📊 Portfolio Options for Wheel Strategy

## Overview

The Portfolio Wheel backtester supports **6 different portfolio configurations** optimized for different risk profiles and strategies.

**Core Principle:** ONE open position at a time, scan all portfolio stocks monthly, pick the best opportunity.

---

## 🎯 Portfolio Selection Guide

| Portfolio | Risk Level | Best For | Expected Premiums | Volatility |
|-----------|-----------|----------|-------------------|------------|
| **NASDAQ** | Medium-High | Tech growth, higher premiums | High | 30-50% |
| **S&P 500** | Low-Medium | Conservative, blue chip | Medium | 15-25% |
| **High Vol** | Very High | Aggressive income, experienced | Very High | 50-100% |
| **Dividend** | Low | Income focus, stability | Low-Medium | 10-20% |
| **Sector** | Medium | Balanced diversification | Medium | 20-35% |
| **Small Cap** | High | Aggressive growth | High | 40-60% |

---

## 📈 Portfolio Details

### 1️⃣ NASDAQ_PORTFOLIO (Top 20 NASDAQ)
**Best for:** Growth-oriented investors seeking higher premiums

**Stocks:**
- **Magnificent 7:** AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA
- **Tech:** NFLX, AMD, ADBE, CRM, CSCO, INTC
- **Growth:** PLTR, COIN, RBLX, SNOW, CRWD
- **ETF:** QQQ, NVDA (weighted)

**Characteristics:**
- ✅ High volatility = better option premiums
- ✅ Tech-focused growth
- ⚠️ Higher drawdown potential
- 💰 Best for: 20-40 year olds, growth-focused

**How to run:**
```bash
# Default (already set)
python scripts/backtest_wheel_portfolio.py

# Or manually select
# Edit scripts/backtest_wheel_portfolio.py:
# DEFAULT_PORTFOLIO = NASDAQ_PORTFOLIO
```

---

### 2️⃣ SP500_PORTFOLIO (Top 20 S&P 500)
**Best for:** Conservative investors, dividend income

**Stocks:**
- **Blue Chips:** AAPL, MSFT, AMZN, GOOGL, BRK-B, JPM, JNJ, V, PG
- **Dividend Aristocrats:** UNH, HD, MA, BAC, ABBV, PFE, KO, PEP, WMT, DIS
- **ETF/Energy:** SPY, XOM

**Characteristics:**
- ✅ Lower volatility, stable companies
- ✅ Many dividend payers
- ✅ Better for retirees/conservative
- 💰 Best for: 50+ year olds, income-focused

**How to run:**
```bash
# Edit scripts/backtest_wheel_portfolio.py line 260:
DEFAULT_PORTFOLIO = SP500_PORTFOLIO

python scripts/backtest_wheel_portfolio.py
```

---

### 3️⃣ HIGH_VOL_PORTFOLIO (Maximum Volatility)
**Best for:** Experienced traders, aggressive income

**Stocks:**
- **Extreme Vol:** TSLA, NVDA, PLTR, COIN, RBLX, SNOW, CRWD, NET, DDOG, ZM
- **High Growth:** AMD, SQ, SHOP, UPST, SOFI, LCID, RIVN, GME, AMC, MRNA
- **ETFs:** ARKK, TQQQ (3x leveraged)

**Characteristics:**
- ⚠️ Very high volatility (50-100% annual)
- 💰 Highest premiums available
- ⚠️ Frequent assignments
- ⚠️ Not for beginners
- 💰 Best for: Experienced options traders

**How to run:**
```bash
# Edit scripts/backtest_wheel_portfolio.py line 260:
DEFAULT_PORTFOLIO = HIGH_VOL_PORTFOLIO

python scripts/backtest_wheel_portfolio.py
```

---

### 4️⃣ DIVIDEND_PORTFOLIO (Income Focus)
**Best for:** Retirees, passive income seekers

**Stocks:**
- **Dividend Aristocrats:** JNJ, PG, KO, PEP, WMT, MCD, TGT, COST, LOW, HD
- **High Yield:** VZ (6.8%), T (6.5%), XOM (5.4%), CVX (5.2%), BMY (4.8%), ABBV (4.3%)
- **Tech Dividends:** MSFT, AAPL, CSCO, INTC
- **ETFs:** SCHD, VYM

**Characteristics:**
- ✅ Low volatility (10-20%)
- ✅ 4-6% dividend yield
- ✅ Stable companies
- ⚠️ Lower option premiums
- 💰 Best for: Income over growth

**How to run:**
```bash
# Edit scripts/backtest_wheel_portfolio.py line 260:
DEFAULT_PORTFOLIO = DIVIDEND_PORTFOLIO

python scripts/backtest_wheel_portfolio.py
```

---

### 5️⃣ SECTOR_PORTFOLIO (Balanced Sectors)
**Best for:** Diversification, sector rotation

**Stocks by Sector:**
- **Tech (3):** NVDA, MSFT, AAPL
- **Financials (3):** JPM, V, BLK
- **Healthcare (3):** JNJ, UNH, ABBV
- **Consumer (3):** AMZN, WMT, KO
- **Energy (2):** XOM, CVX
- **Industrial (2):** CAT, GE
- **Communications (2):** GOOGL, VZ
- **Materials (1):** LIN
- **Real Estate (1):** AMT
- **ETFs:** SPY, QQQ

**Characteristics:**
- ✅ Balanced sector exposure
- ✅ No sector >15% weight
- ✅ Good for economic cycles
- 💰 Best for: Moderate risk, diversification

**How to run:**
```bash
# Edit scripts/backtest_wheel_portfolio.py line 260:
DEFAULT_PORTFOLIO = SECTOR_PORTFOLIO

python scripts/backtest_wheel_portfolio.py
```

---

### 6️⃣ SMALL_CAP_PORTFOLIO (Aggressive Growth)
**Best for:** Higher risk/reward than large caps

**Stocks:**
- **Russell 2000:** IWM, AVAV, DKNG, HOOD, AFRM, TOST, BILL, ASAN, MDB, TWLO
- **Small Cap Tech:** OKTA, ZI, HUBS, FSLY, ESTC, SPLK, DOCU, PD, S, CYBR
- **ETFs:** VTWO, IWM

**Characteristics:**
- ✅ Higher growth potential
- ⚠️ Higher volatility (40-60%)
- ⚠️ Less liquid options
- 💰 Best for: Young investors, high risk tolerance

**How to run:**
```bash
# Edit scripts/backtest_wheel_portfolio.py line 260:
DEFAULT_PORTFOLIO = SMALL_CAP_PORTFOLIO

python scripts/backtest_wheel_portfolio.py
```

---

## 🔄 Switching Portfolios

### Method 1: Edit the script (Recommended)
```python
# In scripts/backtest_wheel_portfolio.py, line 260:

# Uncomment your choice:
# DEFAULT_PORTFOLIO = NASDAQ_PORTFOLIO      # High growth
# DEFAULT_PORTFOLIO = SP500_PORTFOLIO       # Blue chip
# DEFAULT_PORTFOLIO = HIGH_VOL_PORTFOLIO    # Aggressive
# DEFAULT_PORTFOLIO = DIVIDEND_PORTFOLIO  # Income
# DEFAULT_PORTFOLIO = SECTOR_PORTFOLIO    # Balanced
# DEFAULT_PORTFOLIO = SMALL_CAP_PORTFOLIO # Growth

DEFAULT_PORTFOLIO = NASDAQ_PORTFOLIO  # Current
```

### Method 2: Command line (Custom symbols)
```bash
# Run with any custom set of symbols
python scripts/backtest_wheel_portfolio.py AAPL MSFT NVDA TSLA AMD
```

---

## 📊 Comparison Matrix

| Metric | NASDAQ | S&P 500 | High Vol | Dividend | Sector | Small Cap |
|--------|--------|---------|----------|----------|--------|-----------|
| **Avg Volatility** | 35% | 20% | 70% | 15% | 25% | 50% |
| **Expected Premium** | High | Medium | Very High | Low | Medium | High |
| **Assignment Freq** | Medium | Low | High | Low | Medium | High |
| **Dividend Yield** | 0.5% | 2.0% | 0% | 4.0% | 1.5% | 0% |
| **Risk Level** | Med-High | Low-Med | Very High | Low | Medium | High |
| **Best Age Group** | 25-40 | 50+ | 30-45 | 55+ | 35-50 | 25-35 |
| **Time Horizon** | 5-10yr | 10+yr | 2-5yr | 10+yr | 5-10yr | 5-10yr |

---

## 💡 Recommendations by Profile

### 🎓 Young Professional (25-35)
**Portfolio:** NASDAQ or SMALL_CAP
- Higher risk tolerance
- Longer time horizon
- Growth focus

### 🏠 Family Builder (35-50)
**Portfolio:** SECTOR or S&P 500
- Balanced growth/income
- Moderate risk
- Diversification important

### 🏖️ Pre-Retiree (50-65)
**Portfolio:** S&P 500 or DIVIDEND
- Capital preservation
- Income generation
- Lower volatility

### 🌴 Retiree (65+)
**Portfolio:** DIVIDEND
- Income focus
- Stability paramount
- Dividend payers

### 🎯 Aggressive Trader (Any Age)
**Portfolio:** HIGH_VOL
- Maximize premiums
- Frequent trading
- High risk tolerance

---

## 🚀 Quick Start

```bash
# 1. Choose your portfolio (edit the script)
nano scripts/backtest_wheel_portfolio.py
# Change line 260 to your preferred portfolio

# 2. Run the backtest
python scripts/backtest_wheel_portfolio.py

# 3. Check results
cat reports/portfolio_wheel_*.md
```

---

## 📁 File Structure

```
scripts/
└── backtest_wheel_portfolio.py  # Contains all 6 portfolios

PORTFOLIO_OPTIONS.md  # This guide
```

---

**Ready to test different portfolios?** Edit `scripts/backtest_wheel_portfolio.py` line 260 and run! 🎉
