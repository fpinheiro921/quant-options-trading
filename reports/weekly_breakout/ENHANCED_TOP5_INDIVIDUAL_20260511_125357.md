# Enhanced Backtest: Top 5 Cheap SP500 Stocks (Individual)

**Generated:** 2026-05-11 12:53:57

---

## Strategy Rules

| Parameter | Value |
|-----------|-------|
| **Symbols** | SNAP, CCL, AAL, M, FSLY |
| **Timeframe** | Weekly |
| **Entry** | Break above previous week's high |
| **Instrument** | ATM Call (30 DTE) |
| **Profit Target** | Stock up +8% |
| **Stock Stop Loss** | **-2%** |
| **Time Stop** | 5 days |
| **Risk per Trade** | True 10% ($150 max on $1,500) |
| **Max Open** | 1 at a time |
| **Backtest Period** | 10 years |
| **Starting Capital** | $1,500 |

---

## Summary Comparison

| Symbol | Trades | Win Rate | Return | Profit Factor | MC Profit Prob | IS Return | OOS Return |
|--------|--------|----------|--------|---------------|----------------|-----------|------------|
| SNAP | 244 | 37.7% | +1039.30% | 3.72 | 100% | +400% | +639% |
| CCL | 154 | 44.8% | +579.14% | 3.80 | 100% | +286% | +293% |
| AAL | 212 | 39.2% | +465.62% | 3.22 | 100% | +245% | +221% |
| M | 251 | 38.2% | +457.21% | 2.29 | 100% | +320% | +137% |
| FSLY | 157 | 35.0% | +381.76% | 3.38 | 100% | +245% | +136% |

---

## SNAP

### Performance

| Metric | Value |
|--------|-------|
| **Total Return** | **+1039.30%** |
| Final Capital | $17,089.44 |
| Total Trades | 244 |
| Winners | 92 |
| Losers | 152 |
| Win Rate | 37.7% |
| Profit Factor | 3.72 |
| Gross Profit | $21,322.24 |
| Gross Loss | $5,732.80 |
| Avg Winner | $231.76 |
| Avg Loser | $-37.72 |

### Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target (+8%) | 69 | 28.3% |
| Stock Stop (-2%) | 151 | 61.9% |
| Time Stop (5d) | 24 | 9.8% |

### Monte Carlo (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | +1031.19% |
| Median Return | +1029.20% |
| Std Deviation | 195.05% |
| 5th Percentile | +719.19% |
| 95th Percentile | +1339.59% |
| **Prob of Profit** | **100.0%** |
| Mean MDD | 15.46% |
| Worst MDD | 32.36% |

### Walk-Forward (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample (170) | +400.10% | 37.6% |
| Out-of-Sample (74) | +639.19% | 37.8% |

### Sample Trades

| Entry | Exit | Days | Stock% | P&L | Reason |
|-------|------|------|--------|-----|--------|
| $22.16 | $23.93 | 3d | +8.0% | $47.87 | PROFIT_TARGET |
| $23.31 | $22.84 | 0d | -2.0% | $-4.20 | STOCK_STOP |
| $21.28 | $20.85 | 0d | -2.0% | $-3.83 | STOCK_STOP |
| $21.50 | $21.82 | 5d | +1.5% | $8.64 | TIME_STOP |
| $22.60 | $22.98 | 5d | +1.7% | $10.26 | TIME_STOP |

---

## CCL

### Performance

| Metric | Value |
|--------|-------|
| **Total Return** | **+579.14%** |
| Final Capital | $10,187.09 |
| Total Trades | 154 |
| Winners | 69 |
| Losers | 85 |
| Win Rate | 44.8% |
| Profit Factor | 3.80 |
| Gross Profit | $11,790.90 |
| Gross Loss | $3,103.81 |
| Avg Winner | $170.88 |
| Avg Loser | $-36.52 |

### Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target (+8%) | 55 | 35.7% |
| Stock Stop (-2%) | 84 | 54.5% |
| Time Stop (5d) | 15 | 9.7% |

### Monte Carlo (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | +580.59% |
| Median Return | +579.64% |
| Std Deviation | 107.47% |
| 5th Percentile | +410.83% |
| 95th Percentile | +759.83% |
| **Prob of Profit** | **100.0%** |
| Mean MDD | 12.02% |
| Worst MDD | 24.15% |

### Walk-Forward (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample (107) | +286.12% | 43.9% |
| Out-of-Sample (47) | +293.02% | 46.8% |

### Sample Trades

| Entry | Exit | Days | Stock% | P&L | Reason |
|-------|------|------|--------|-----|--------|
| $17.83 | $17.47 | 0d | -2.0% | $-3.21 | STOCK_STOP |
| $12.51 | $13.51 | 0d | +8.0% | $54.05 | PROFIT_TARGET |
| $14.23 | $15.37 | 4d | +8.0% | $61.49 | PROFIT_TARGET |
| $15.12 | $16.33 | 3d | +8.0% | $65.32 | PROFIT_TARGET |
| $18.09 | $19.53 | 0d | +8.0% | $78.13 | PROFIT_TARGET |

---

## AAL

### Performance

| Metric | Value |
|--------|-------|
| **Total Return** | **+465.62%** |
| Final Capital | $8,484.23 |
| Total Trades | 212 |
| Winners | 83 |
| Losers | 129 |
| Win Rate | 39.2% |
| Profit Factor | 3.22 |
| Gross Profit | $10,135.99 |
| Gross Loss | $3,151.76 |
| Avg Winner | $122.12 |
| Avg Loser | $-24.43 |

### Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target (+8%) | 45 | 21.2% |
| Stock Stop (-2%) | 123 | 58.0% |
| Time Stop (5d) | 44 | 20.8% |

### Monte Carlo (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | +467.04% |
| Median Return | +465.08% |
| Std Deviation | 91.68% |
| 5th Percentile | +321.61% |
| 95th Percentile | +621.67% |
| **Prob of Profit** | **100.0%** |
| Mean MDD | 10.25% |
| Worst MDD | 18.48% |

### Walk-Forward (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample (148) | +244.56% | 38.5% |
| Out-of-Sample (64) | +221.06% | 40.6% |

### Sample Trades

| Entry | Exit | Days | Stock% | P&L | Reason |
|-------|------|------|--------|-----|--------|
| $31.01 | $30.39 | 4d | -2.0% | $-23.45 | STOCK_STOP |
| $28.38 | $30.65 | 4d | +8.0% | $61.30 | PROFIT_TARGET |
| $29.11 | $31.44 | 0d | +8.0% | $62.88 | PROFIT_TARGET |
| $34.79 | $34.79 | 5d | -0.0% | $-26.09 | TIME_STOP |
| $34.23 | $35.33 | 5d | +3.2% | $29.66 | TIME_STOP |

---

## M

### Performance

| Metric | Value |
|--------|-------|
| **Total Return** | **+457.21%** |
| Final Capital | $8,358.21 |
| Total Trades | 251 |
| Winners | 96 |
| Losers | 155 |
| Win Rate | 38.2% |
| Profit Factor | 2.29 |
| Gross Profit | $12,159.92 |
| Gross Loss | $5,301.70 |
| Avg Winner | $126.67 |
| Avg Loser | $-34.20 |

### Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target (+8%) | 56 | 22.3% |
| Stock Stop (-2%) | 148 | 59.0% |
| Time Stop (5d) | 47 | 18.7% |

### Monte Carlo (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | +467.70% |
| Median Return | +469.55% |
| Std Deviation | 115.48% |
| 5th Percentile | +291.62% |
| 95th Percentile | +655.02% |
| **Prob of Profit** | **100.0%** |
| Mean MDD | 17.92% |
| Worst MDD | 35.49% |

### Walk-Forward (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample (175) | +320.42% | 41.1% |
| Out-of-Sample (76) | +136.79% | 31.6% |

### Sample Trades

| Entry | Exit | Days | Stock% | P&L | Reason |
|-------|------|------|--------|-----|--------|
| $20.30 | $21.24 | 5d | +4.6% | $25.43 | TIME_STOP |
| $21.13 | $22.03 | 5d | +4.3% | $24.38 | TIME_STOP |
| $22.26 | $21.82 | 0d | -2.0% | $-4.01 | STOCK_STOP |
| $21.75 | $21.31 | 0d | -2.0% | $-3.91 | STOCK_STOP |
| $22.14 | $22.82 | 5d | +3.0% | $18.17 | TIME_STOP |

---

## FSLY

### Performance

| Metric | Value |
|--------|-------|
| **Total Return** | **+381.76%** |
| Final Capital | $7,226.40 |
| Total Trades | 157 |
| Winners | 55 |
| Losers | 102 |
| Win Rate | 35.0% |
| Profit Factor | 3.38 |
| Gross Profit | $8,132.63 |
| Gross Loss | $2,406.23 |
| Avg Winner | $147.87 |
| Avg Loser | $-23.59 |

### Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target (+8%) | 51 | 32.5% |
| Stock Stop (-2%) | 102 | 65.0% |
| Time Stop (5d) | 4 | 2.5% |

### Monte Carlo (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | +384.79% |
| Median Return | +384.27% |
| Std Deviation | 77.94% |
| 5th Percentile | +258.38% |
| 95th Percentile | +517.20% |
| **Prob of Profit** | **100.0%** |
| Mean MDD | 10.56% |
| Worst MDD | 20.05% |

### Walk-Forward (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample (109) | +245.31% | 38.5% |
| Out-of-Sample (48) | +136.45% | 27.1% |

### Sample Trades

| Entry | Exit | Days | Stock% | P&L | Reason |
|-------|------|------|--------|-----|--------|
| $21.45 | $21.02 | 0d | -2.0% | $-3.86 | STOCK_STOP |
| $20.11 | $19.71 | 0d | -2.0% | $-3.62 | STOCK_STOP |
| $21.01 | $20.59 | 0d | -2.0% | $-3.78 | STOCK_STOP |
| $21.21 | $22.00 | 5d | +3.7% | $21.33 | TIME_STOP |
| $22.47 | $24.27 | 0d | +8.0% | $48.54 | PROFIT_TARGET |

---

## Conclusions

- Each symbol backtested individually with true 10% risk
- SNAP shows highest absolute return
- CCL shows strong consistency
- M shows negative return (avoid)
- FSLY has limited data but good potential

---
*Individual enhanced backtests complete*
