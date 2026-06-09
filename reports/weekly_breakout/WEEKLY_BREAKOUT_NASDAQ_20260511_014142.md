# Weekly Breakout Strategy - NASDAQ Backtest
**ONE POSITION AT A TIME ACROSS PORTFOLIO**

## Strategy Rules

| Parameter | Value |
|-----------|-------|
| **Timeframe** | Weekly |
| **Entry Signal** | Break above previous week's high |
| **Instrument** | ATM Call (30 DTE) |
| **Profit Target** | Stock up +8% |
| **Stop Loss** | None - hold to expiration Thursday |
| **Time Stop** | 10 days (tightened to cut theta decay) |
| **Position Sizing** | 10% risk per trade |
| **Max Open Trades** | **1 (across entire portfolio)** |
| **Initial Capital** | $50,000.00 |

## Performance Summary

| Metric | Value |
|--------|-------|
| **Total Return** | **+271.65%** |
| Final Capital | $185,825.85 |
| Total Trades | 499 |
| Winners | 294 |
| Losers | 205 |
| Win Rate | 58.9% |
| Profit Factor | 1.27 |

## Exit Analysis

| Exit Type | Count | Percentage |
|-----------|-------|------------|
| Profit Target (+8%) | 35 | 7.0% |
| Option Stop (-70%) | 0 | 0.0% |
| Time Stop (Thursday) | 464 | 93.0% |

## Symbol Breakdown (All 19 NASDAQ Symbols)

| Symbol | Trades | Win Rate | Avg P&L/Trade | Total P&L |
|--------|--------|----------|---------------|-----------|
| AAPL | 306 | 68.0% | $638.71 | $195,443.95 |
| MSFT | 90 | 46.7% | $-356.34 | $-32,070.41 |
| NVDA | 32 | 37.5% | $-485.42 | $-15,533.45 |
| AMZN | 13 | 46.2% | $-1,214.71 | $-15,791.24 |
| META | 11 | 45.5% | $-346.54 | $-3,811.95 |
| GOOGL | 11 | 54.5% | $681.15 | $7,492.66 |
| TSLA | 12 | 50.0% | $181.62 | $2,179.46 |
| NFLX | 2 | 0.0% | $-2,385.47 | $-4,770.95 |
| AMD | 2 | 50.0% | $214.90 | $429.80 |
| ADBE | 3 | 33.3% | $-1,581.33 | $-4,744.00 |
| CRM | 3 | 33.3% | $-327.64 | $-982.91 |
| CSCO | 5 | 20.0% | $-1,517.94 | $-7,589.69 |
| INTC | 3 | 0.0% | $-2,800.69 | $-8,402.06 |
| PLTR | 2 | 100.0% | $5,235.72 | $10,471.45 |
| COIN | 1 | 100.0% | $8,342.76 | $8,342.76 |
| RBLX | 0 | - | - | Skipped (one-at-a-time) |
| SNOW | 1 | 100.0% | $6,304.09 | $6,304.09 |
| CRWD | 2 | 50.0% | $-570.84 | $-1,141.67 |
| QQQ | 0 | - | - | Skipped (one-at-a-time) |

## Recent Trades

| Symbol | Entry | Exit | Days | Stock % | P&L | Reason |
|--------|-------|------|------|---------|-----|--------|
| AAPL | $21.75 | $22.44 | 5d | +3.1% | $936.92 | TIME_STOP |
| MSFT | $46.52 | $46.11 | 5d | -0.9% | $-910.90 | TIME_STOP |
| AAPL | $22.89 | $22.13 | 5d | -3.3% | $-1,094.95 | TIME_STOP |
| NVDA | $1.17 | $1.16 | 5d | -1.3% | $-921.71 | TIME_STOP |
| MSFT | $44.95 | $44.78 | 5d | -0.4% | $-804.63 | TIME_STOP |
| AMZN | $36.12 | $36.88 | 5d | +2.1% | $598.60 | TIME_STOP |
| AAPL | $21.99 | $22.07 | 5d | +0.4% | $105.17 | TIME_STOP |
| AAPL | $22.09 | $22.78 | 5d | +3.1% | $893.63 | TIME_STOP |
| AAPL | $22.64 | $23.46 | 5d | +3.6% | $1,042.73 | TIME_STOP |
| AAPL | $23.02 | $24.11 | 5d | +4.7% | $1,401.55 | TIME_STOP |
| AAPL | $23.83 | $24.74 | 5d | +3.8% | $1,154.06 | TIME_STOP |
| AAPL | $24.67 | $25.02 | 5d | +1.4% | $443.75 | TIME_STOP |
| AAPL | $24.97 | $24.75 | 5d | -0.9% | $-957.12 | TIME_STOP |
| MSFT | $51.84 | $51.23 | 5d | -1.2% | $-956.76 | TIME_STOP |
| NVDA | $1.57 | $1.53 | 5d | -2.4% | $-1,053.12 | TIME_STOP |

---
*Report generated: 2026-05-11 01:41:42*
*Strategy: Weekly Breakout + ATM Call*
*Rule: ONE open position at a time across portfolio*
