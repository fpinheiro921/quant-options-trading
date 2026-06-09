# Strategy Combinations Reports

This folder contains the most up-to-date enhanced backtests and optimization studies for the complete trading journey.

## Current Reports (Last Updated: 2026-05-11)

| Report | Description | Key Insights |
|--------|-------------|--------------|
| **INDIVIDUAL_PHASES_20260511_142159.md** | Optimized individual phase backtests (1,000 MC sims each) | **Includes 10% OTM strike calculation examples for all OTM phases** |
| **OPTIMIZED_STRATEGY_20260511_141903.md** | Updated strategy descriptions with Sharpe improvements | **Includes OTM formula, mental math, and broker order examples** |
| **PHASES_TO_WHEEL_MOMENTUM_20260511_134918.md** | Full journey simulation: phases → Wheel + Momentum | Switch at $50K, median 6.7 years to transition |
| **SHARPE_OPTIMIZATION_20260511_141542.md** | Sharpe ratio optimization study | +44% average Sharpe improvement via parameter tuning |

## Applied Optimizations (vs Baseline)

| Parameter | Before | After | Impact |
|-----------|--------|-------|--------|
| Stock Stop | -2.0% | **-1.5%** | 25% tighter, cuts losses faster |
| Time Exit | 5 days | **3 days** | 40% less theta decay |
| VIX Filter | None | **< 25** (< 20 AAPL) | Avoid choppy markets |
| AAPL Position | 100% | **50%** | 50% variance reduction |
| AAPL Strike | ATM | **90-delta ITM** | Less time decay |

## Optimized Phase Summary

| Phase | Old Sharpe | **New Sharpe** | Improvement |
|-------|------------|----------------|-------------|
| SNAP OTM | 0.51 | **0.66** | +28% |
| SNAP + AAL | 0.62 | **0.80** | +29% |
| Top 5 OTM | 0.60 | **0.84** | +40% |
| Top 5 ATM | 0.73 | **1.08** | +49% |
| AAPL ATM | 1.45 | **2.81** | +94% |
| Wheel + Mom | 1.74 | **2.03** | +17% |

## Complete Journey (Optimized)

| Phase | Start | Median Final | Growth |
|-------|-------|--------------|--------|
| Paper | $150 | $400 | +167% |
| SNAP OTM | $400 | **$795** | +99% |
| SNAP + AAL | $1,000 | **$1,539** | +54% |
| Top 5 OTM | $1,500 | **$2,313** | +54% |
| Top 5 ATM | $3,000 | **$5,705** | +90% |
| AAPL ATM | $5,000 | **$34,773** | +595% |
| Wheel + Mom | $50,000 | **$162,402** | +225% |
| **TOTAL** | **$150** | **$162,402** | **+108,168%** |

**Total Journey Time:** ~11 years (132 months)

## Scripts Location

Source code: `H:\QUANT TRADING\STRATEGY_COMBINATIONS\`

- `enhanced_individual_phases.py` - Runs optimized phase backtests
- `optimized_weekly_breakout_backtest.py` - Backtest engine with optimizations
- `optimize_sharpe_ratios.py` - Sharpe optimization study
- `enhanced_phases_to_wheel_momentum.py` - Full journey simulation

---
*All reports use Monte Carlo simulation with 1,000 paths per scenario*
*Optimization based on Sharpe ratio improvements from parameter tuning*
