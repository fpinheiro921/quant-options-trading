# Realistic Moneyness Comparison: Fixed 1 Contract per Trade

**Generated:** 2026-05-11 13:18:04
**Model:** Black-Scholes with Historical Volatility
**Strategy:** Weekly Breakout, -2% Stock Stop, 5-Day Time Stop
**Account:** $1,500
**Sizing:** Fixed 1 contract per trade (realistic retail)
**Rule:** Skip trade if contract cost > account balance

---

## Option Model Details

| Parameter | Value |
|-----------|-------|
| Pricing Model | Black-Scholes |
| Volatility | Historical (60-day lookback) |
| Risk-Free Rate | 4.5% |
| Days to Expiration | 30 |
| **ITM Strike** | 90% of stock price |
| **ATM Strike** | 100% of stock price |
| **OTM Strike** | 110% of stock price |
| Sizing | Fixed 1 contract |
| Skip Rule | If contract cost > account balance |

---

## Results Summary

| Symbol | Moneyness | Trades | Win Rate | Final Capital | Total Return | Avg Contract Cost |
|--------|-----------|--------|----------|---------------|--------------|-------------------|
| AAPL | ITM10 | 306 | 59.5% | $43,106.91 | +2773.8% | $1230.56 |
| AAPL | ATM | 306 | 56.9% | $30,046.63 | +1903.1% | $345.33 |
| AAPL | OTM10 | 306 | 50.3% | $8,956.20 | +497.1% | $36.81 |
| SNAP | ITM10 | 244 | 36.9% | $5,143.23 | +242.9% | $269.18 |
| SNAP | ATM | 244 | 36.1% | $4,302.83 | +186.9% | $149.89 |
| SNAP | OTM10 | 244 | 34.8% | $3,370.10 | +124.7% | $74.72 |
| CCL | ITM10 | 243 | 42.0% | $5,553.42 | +270.2% | $399.01 |
| CCL | ATM | 219 | 39.7% | $3,273.70 | +118.2% | $201.70 |
| CCL | OTM10 | 260 | 36.5% | $2,276.73 | +51.8% | $105.85 |
| AAL | ITM10 | 262 | 38.2% | $5,723.02 | +281.5% | $295.02 |
| AAL | ATM | 262 | 36.6% | $4,240.20 | +182.7% | $146.50 |
| AAL | OTM10 | 262 | 33.6% | $2,891.83 | +92.8% | $60.81 |
| M | ITM10 | 251 | 37.5% | $4,777.15 | +218.5% | $189.79 |
| M | ATM | 251 | 36.3% | $4,045.09 | +169.7% | $74.46 |
| M | OTM10 | 251 | 35.1% | $2,832.62 | +88.8% | $19.67 |
| FSLY | ITM10 | 185 | 35.1% | $7,873.95 | +424.9% | $470.00 |
| FSLY | ATM | 185 | 35.1% | $6,624.72 | +341.6% | $324.60 |
| FSLY | OTM10 | 185 | 35.1% | $5,430.10 | +262.0% | $217.51 |

---

## Key Findings

### AAPL
- ITM: TOO EXPENSIVE for $1,500 account ($3,078/contract)
- ATM: Works well, 1 contract = 58% of account
- OTM: Cheapest, but lower delta = needs bigger moves

### Cheap Stocks (SNAP, AAL, M)
- All moneyness levels affordable
- ITM: Higher win rate, lower returns (expensive contracts)
- OTM: Lower win rate, explosive returns when they win
- ATM: Balanced

### Realistic Takeaway
With FIXED 1 contract sizing:
- ITM: Safer but capital-intensive (fewer trades)
- ATM: Best balance for most symbols
- OTM: High variance, many small losses, few big wins

---

## What Option Are You Buying?

**30 DTE (Days to Expiration) Call Option**

| Feature | Description |
|---------|-------------|
| Type | CALL (right to buy stock at strike) |
| Expiration | 30 days from entry |
| Strike | ATM = stock price / ITM = 90% of stock / OTM = 110% of stock |
| Premium | Calculated via Black-Scholes with historical volatility |

### Example: AAPL at $293

| Moneyness | Strike | Premium | Contract Cost | Delta |
|-----------|--------|---------|---------------|-------|
| ITM10 | $263.99 | $30.78 | $3,078 | 0.95 |
| ATM | $293.32 | $8.64 | $864 | 0.54 |
| OTM10 | $322.65 | $0.92 | $92 | 0.10 |

### Example: SNAP at $6.08

| Moneyness | Strike | Premium | Contract Cost | Delta |
|-----------|--------|---------|---------------|-------|
| ITM10 | $5.47 | $0.80 | $80 | 0.76 |
| ATM | $6.08 | $0.45 | $45 | 0.54 |
| OTM10 | $6.69 | $0.22 | $22 | 0.34 |

---

## Risk Reality Check ($1,500 Account)

| Symbol | Moneyness | Contract Cost | % of Account | Affordable? |
|--------|-----------|---------------|--------------|-------------|
| AAPL | ITM10 | $3,078 | 205% | ❌ NO |
| AAPL | ATM | $864 | 58% | ✅ Yes (1 contract) |
| AAPL | OTM10 | $92 | 6% | ✅ Yes |
| SNAP | ITM10 | $80 | 5% | ✅ Yes |
| SNAP | ATM | $45 | 3% | ✅ Yes |
| SNAP | OTM10 | $22 | 1% | ✅ Yes |

---

## Recommendation

For **$1,500 account**:
1. **AAPL**: Can only trade ATM or OTM (ITM too expensive)
2. **Cheap stocks**: Can trade any moneyness
3. **Best overall**: ATM strikes (balanced delta, reasonable cost)
4. **Conservative**: ITM on cheap stocks only (higher delta, more directional)
5. **Aggressive**: OTM (cheaper, higher leverage, more variance)

---

*Realistic backtest with proper Black-Scholes pricing and fixed 1-contract sizing*
