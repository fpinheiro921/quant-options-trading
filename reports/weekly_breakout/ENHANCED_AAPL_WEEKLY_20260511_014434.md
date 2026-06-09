# Enhanced Weekly Breakout Strategy Report

**Generated:** 2026-05-11 01:44:34

---

## Strategy Rules

| Parameter | Value |
|-----------|-------|
| **Timeframe** | Weekly |
| **Entry** | Break above previous week's high |
| **Instrument** | ATM Call (30 DTE) |
| **Profit Target** | Stock up +8% |
| **Time Stop** | 5 days |
| **Risk per Trade** | 10% |
| **Max Open** | 1 at a time |
| **Backtest Period** | 10 years |

---

## Performance Summary

| Metric | Value |
|--------|-------|
| **Total Return** | **+625.15%** |
| Final Capital | $362,576.52 |
| Total Trades | 306 |
| Winners | 208 |
| Losers | 98 |
| Win Rate | 68.0% |
| Profit Factor | 1.78 |
| Gross Profit | $710,838.14 |
| Gross Loss | $398,261.63 |

---

## Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target | 19 | 6.2% |
| Time Stop (5d) | 287 | 93.8% |

---

## Symbol Breakdown

| Symbol | Trades | Win Rate | Avg P&L | Total P&L |
|--------|--------|----------|---------|-----------|
| AAPL | 306 | 68.0% | $1,021.49 | $312,576.52 |

---

## Monte Carlo Simulation (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | +618.55% |
| Median Return | +622.45% |
| Std Deviation | 157.12% |
| 5th Percentile | +368.03% |
| 95th Percentile | +875.00% |
| **Probability of Profit** | **100.0%** |
| Mean Max Drawdown | 30.31% |
| Worst Case MDD | 61.92% |

---

## Walk-Forward Analysis (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample (214 trades) | +396.71% | 70.6% |
| Out-of-Sample (92 trades) | +228.45% | 62.0% |

---

## Sample Trades

| Symbol | Entry | Exit | Days | Stock% | P&L | Reason |
|--------|-------|------|------|--------|-----|--------|
| AAPL | $21.75 | $22.44 | 5d | +3.1% | $936.92 | TIME_STOP |
| AAPL | $22.89 | $22.13 | 5d | -3.3% | $-1,117.76 | TIME_STOP |
| AAPL | $21.99 | $22.07 | 5d | +0.4% | $109.55 | TIME_STOP |
| AAPL | $22.09 | $22.78 | 5d | +3.1% | $930.87 | TIME_STOP |
| AAPL | $22.64 | $23.46 | 5d | +3.6% | $1,087.10 | TIME_STOP |
| AAPL | $23.02 | $24.11 | 5d | +4.7% | $1,459.95 | TIME_STOP |
| AAPL | $23.83 | $24.74 | 5d | +3.8% | $1,203.17 | TIME_STOP |
| AAPL | $24.67 | $25.02 | 5d | +1.4% | $462.63 | TIME_STOP |
| AAPL | $24.97 | $24.75 | 5d | -0.9% | $-997.85 | TIME_STOP |
| AAPL | $24.75 | $25.61 | 5d | +3.4% | $1,106.37 | TIME_STOP |
| AAPL | $24.93 | $26.01 | 5d | +4.4% | $1,438.58 | TIME_STOP |
| AAPL | $26.61 | $26.11 | 5d | -1.9% | $-1,117.74 | TIME_STOP |
| AAPL | $26.25 | $26.83 | 5d | +2.2% | $715.99 | TIME_STOP |
| AAPL | $27.09 | $25.56 | 5d | -5.6% | $-1,461.32 | TIME_STOP |
| AAPL | $25.46 | $25.45 | 5d | -0.1% | $-902.76 | TIME_STOP |

---

## Conclusions

- **Strategy Return:** +625.15%
- **Monte Carlo Profit Probability:** 100.0%
- **Walk-Forward Consistency:** REVIEW
- **Overall Assessment:** ROBUST

---
*Enhanced backtest complete*
