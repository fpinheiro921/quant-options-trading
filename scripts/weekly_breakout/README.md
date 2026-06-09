# Weekly Breakout Strategy Scripts

All scripts related to the **Weekly Breakout** strategy.

## Core Files

| Script | Purpose |
|--------|---------|
| `backtest_weekly_breakout.py` | Core backtest engine (load data, find setups, estimate premiums, calculate option values) |
| `enhanced_aapl_minus2_stop.py` | Enhanced backtest: AAPL with -2% stock stop + Monte Carlo + Walk-Forward |
| `enhanced_top5_individual.py` | Enhanced backtest: Top 5 cheap SP500 stocks individually |
| `enhanced_top5_sp500.py` | Enhanced backtest: Top 5 cheap SP500 as combined portfolio |
| `enhanced_weekly_breakout.py` | Original enhanced backtest runner |
| `report_aapl_minus2_stop.py` | Generate detailed report for AAPL -2% stop strategy |
| `run_enhanced_backtests.py` | Run multiple enhanced backtests |
| `run_enhanced_full.py` | Full enhanced backtest suite |
| `run_enhanced_weekly.py` | Weekly enhanced backtest runner |
| `backtest_stops_and_cheaper_stocks.py` | Backtest various stock stop losses + find cheap stocks |
| `backtest_sp500_cheap.py` | Backtest strategy on cheap SP500 stocks |
| `create_combined_report.py` | Create combined strategy report |
| `create_final_combined_report.py` | Create final combined report |

## Strategy Rules

- **Entry:** Buy ATM Call (30 DTE) when stock breaks above previous week's high
- **Stop:** -2% stock stop (exit option when stock drops 2%)
- **Target:** +8% stock gain
- **Time Stop:** 5 days maximum hold
- **Risk:** 10% of account per trade
- **Max Open:** 1 trade at a time

## How to Run

```powershell
python "h:\QUANT TRADING\scripts\weekly_breakout\enhanced_aapl_minus2_stop.py"
python "h:\QUANT TRADING\scripts\weekly_breakout\enhanced_top5_individual.py"
```

## Reports Output

Reports are saved to: `h:\QUANT TRADING\reports\weekly_breakout\`
