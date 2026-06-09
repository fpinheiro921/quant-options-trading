# Moneyness Comparison: ATM vs ITM vs OTM

**Generated:** 2026-05-11 13:13:10
**Model:** Black-Scholes with Historical Volatility
**Strategy:** Weekly Breakout, -2% Stock Stop, 5-Day Time Stop
**Account:** $1,500

---

## Option Model Details

| Parameter | Value |
|-----------|-------|
| Pricing Model | Black-Scholes |
| Volatility | Historical (30-60 day lookback) |
| Risk-Free Rate | 4.5% |
| Days to Expiration | 30 |
| **ITM Strike** | 90% of stock price |
| **ATM Strike** | 100% of stock price |
| **OTM Strike** | 110% of stock price |

---

## Summary Results

| Symbol | Moneyness | Strike | Avg Delta | Trades | Win Rate | Total Return | Profit Factor | MC Prob |
|--------|-----------|--------|-----------|--------|----------|--------------|---------------|---------|
| AAL | ITM10 | 90% | 0.79 | 110 | 38.2% | +93.2% | 1.96 | 100% |
| AAL | ATM | 100% | 0.54 | 165 | 35.2% | +318.8% | 1.95 | 100% |
| AAL | OTM10 | 110% | 0.29 | 262 | 33.6% | +1299.5% | 1.88 | 100% |
| AAPL | ITM10 | - | - | 0 | - | - | - | - |
| AAPL | ATM | 100% | 0.54 | 306 | 56.9% | +193718.4% | 2.58 | 100% |
| AAPL | OTM10 | 110% | 0.10 | 306 | 50.3% | +768246.1% | 2.16 | 100% |
| CCL | ITM10 | 90% | 0.77 | 69 | 46.4% | +116.7% | 3.06 | 100% |
| CCL | ATM | 100% | 0.54 | 154 | 42.2% | +701.3% | 2.42 | 100% |
| CCL | OTM10 | 110% | 0.32 | 164 | 39.6% | +1784.8% | 2.26 | 100% |
| FSLY | ITM10 | 90% | 0.70 | 41 | 31.7% | +14.0% | 1.63 | 90% |
| FSLY | ATM | 100% | 0.56 | 71 | 29.6% | +18.9% | 1.41 | 88% |
| FSLY | OTM10 | 110% | 0.43 | 118 | 31.4% | +71.0% | 1.61 | 98% |
| M | ITM10 | 90% | 0.86 | 167 | 38.9% | +311.1% | 1.83 | 100% |
| M | ATM | 100% | 0.53 | 251 | 36.3% | +2811.1% | 1.69 | 99% |
| M | OTM10 | 110% | 0.21 | 251 | 35.1% | +32690.5% | 1.61 | 98% |
| SNAP | ITM10 | 90% | 0.76 | 135 | 37.8% | +149.9% | 2.13 | 100% |
| SNAP | ATM | 100% | 0.54 | 205 | 36.6% | +501.7% | 1.96 | 100% |
| SNAP | OTM10 | 110% | 0.34 | 244 | 34.8% | +1693.3% | 1.91 | 100% |

---

## Detailed Analysis by Symbol

### AAL

**ITM10:** Return +93.2% | 110 trades | 38.2% WR | Avg Delta: 0.79 | Avg Contract: $163.52

**ATM:** Return +318.8% | 165 trades | 35.2% WR | Avg Delta: 0.54 | Avg Contract: $92.23

**OTM10:** Return +1299.5% | 262 trades | 33.6% WR | Avg Delta: 0.29 | Avg Contract: $60.81


---

### AAPL

**ITM10:** No trades

**ATM:** Return +193718.4% | 306 trades | 56.9% WR | Avg Delta: 0.54 | Avg Contract: $345.33

**OTM10:** Return +768246.1% | 306 trades | 50.3% WR | Avg Delta: 0.10 | Avg Contract: $36.81


---

### CCL

**ITM10:** Return +116.7% | 69 trades | 46.4% WR | Avg Delta: 0.77 | Avg Contract: $185.98

**ATM:** Return +701.3% | 154 trades | 42.2% WR | Avg Delta: 0.54 | Avg Contract: $133.14

**OTM10:** Return +1784.8% | 164 trades | 39.6% WR | Avg Delta: 0.32 | Avg Contract: $66.89


---

### FSLY

**ITM10:** Return +14.0% | 41 trades | 31.7% WR | Avg Delta: 0.70 | Avg Contract: $128.85

**ATM:** Return +18.9% | 71 trades | 29.6% WR | Avg Delta: 0.56 | Avg Contract: $105.68

**OTM10:** Return +71.0% | 118 trades | 31.4% WR | Avg Delta: 0.43 | Avg Contract: $102.50


---

### M

**ITM10:** Return +311.1% | 167 trades | 38.9% WR | Avg Delta: 0.86 | Avg Contract: $170.42

**ATM:** Return +2811.1% | 251 trades | 36.3% WR | Avg Delta: 0.53 | Avg Contract: $74.46

**OTM10:** Return +32690.5% | 251 trades | 35.1% WR | Avg Delta: 0.21 | Avg Contract: $19.67


---

### SNAP

**ITM10:** Return +149.9% | 135 trades | 37.8% WR | Avg Delta: 0.76 | Avg Contract: $138.53

**ATM:** Return +501.7% | 205 trades | 36.6% WR | Avg Delta: 0.54 | Avg Contract: $101.87

**OTM10:** Return +1693.3% | 244 trades | 34.8% WR | Avg Delta: 0.34 | Avg Contract: $74.72


---

## Key Insights

### ITM (10% In-The-Money)
- **Higher delta** (~0.70-0.80): Moves more with stock
- **More expensive** contracts: Less leverage
- **Lower time decay risk**: More intrinsic value
- **Better for trending stocks**: Captures more of the move

### ATM (At-The-Money)
- **Delta ~0.50**: Balanced stock sensitivity
- **Moderate cost**: Good leverage
- **Higher theta decay**: Pure time value
- **Best risk/reward**: Balanced approach

### OTM (10% Out-of-The-Money)
- **Lower delta** (~0.30-0.40): Less stock sensitivity
- **Cheaper contracts**: More leverage
- **High time decay**: All time value
- **Need bigger moves**: Must hit +8% target to profit

---

## Conclusions

- **ITM** may perform better with the -2% stop (higher delta = more directional)
- **ATM** is the balanced baseline
- **OTM** may underperform due to theta decay on 5-day holds
- Results depend heavily on stock's realized volatility vs implied volatility

---
*Backtest with proper Black-Scholes pricing*
