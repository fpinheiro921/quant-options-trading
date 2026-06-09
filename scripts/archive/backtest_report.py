"""
Generate comprehensive markdown backtest reports for both strategies.
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
from backtest.backtest_engine import WheelStrategyBacktester, MomentumBreakoutBacktester
from backtest.paper_trading import create_paper_environment
from api.alpaca_client import AlpacaClient
from config import Config
import json


def generate_markdown_report(result, symbol, days, strategy_name):
    """Generate a detailed markdown report."""
    
    md = f"""# 📊 Backtest Report: {strategy_name}

## Overview

| Metric | Value |
|--------|-------|
| **Symbol** | {symbol} |
| **Strategy** | {result.strategy_name} |
| **Period** | {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')} |
| **Lookback** | {days} days |
| **Initial Capital** | ${result.initial_capital:,.2f} |
| **Final Capital** | ${result.final_capital:,.2f} |

---

## 📈 Performance Summary

| Metric | Value | Status |
|--------|-------|--------|
| **Total Return** | {result.total_return_pct:+.2f}% | {'🟢' if result.total_return_pct > 0 else '🔴'} |
| **Annualized Return** | {(result.total_return_pct * (365/days)):+.2f}% | {'🟢' if result.total_return_pct > 0 else '🔴'} |
| **Max Drawdown** | {result.max_drawdown_pct:.2f}% | {'🟢' if result.max_drawdown_pct < 20 else '🔴'} |
| **Sharpe Ratio** | {result.sharpe_ratio:.2f} | {'🟢' if result.sharpe_ratio > 1 else '⚪'} |

---

## 🎯 Trade Statistics

| Metric | Value |
|--------|-------|
| **Total Trades** | {result.total_trades} |
| **Winning Trades** | {result.winning_trades} |
| **Losing Trades** | {result.losing_trades} |
| **Win Rate** | {result.win_rate:.1%} |
| **Average Trade Return** | ${result.avg_trade_return:.2f} |

---

## 💰 Risk Metrics

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Max Drawdown** | {result.max_drawdown_pct:.2f}% | Peak-to-trough decline |
| **Sharpe Ratio** | {result.sharpe_ratio:.2f} | Risk-adjusted return |
| **Calmar Ratio** | {(result.total_return_pct / result.max_drawdown_pct) if result.max_drawdown_pct > 0 else 0:.2f} | Return/max drawdown |

---

## 📋 Trade List

| # | Date | Action | Symbol | Price | P&L | Notes |
|---|------|--------|--------|-------|-----|-------|
"""
    
    for i, trade in enumerate(result.trades[:20], 1):  # Show first 20 trades
        date_str = trade.timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(trade.timestamp, 'strftime') else str(trade.timestamp)[:16]
        price = trade.entry_price if hasattr(trade, 'entry_price') else trade.price
        pnl = trade.realized_pnl if trade.realized_pnl != 0 else '-'
        pnl_str = f"${pnl:.2f}" if isinstance(pnl, float) else pnl
        icon = "🟢" if trade.realized_pnl > 0 else "🔴" if trade.realized_pnl < 0 else "⚪"
        
        notes = trade.notes[:30] if hasattr(trade, 'notes') and trade.notes else '-'
        
        md += f"| {i} | {date_str} | {trade.action.value} | {trade.symbol} | ${price:.2f} | {pnl_str} {icon if trade.realized_pnl != 0 else ''} | {notes} |\n"
    
    if len(result.trades) > 20:
        md += f"\n*... and {len(result.trades) - 20} more trades*\n"
    
    # Add enhanced metrics if available
    if hasattr(result, 'mc_median_return'):
        md += f"""

---

## 🎲 Monte Carlo Simulation

| Metric | Value |
|--------|-------|
| **Median Return** | {result.mc_median_return:+.2f}% |
| **Worst Case (5%)** | {result.mc_worst_case:+.2f}% |
| **Best Case (95%)** | {result.mc_best_case:+.2f}% |
| **Probability of Profit** | {result.mc_probability_of_profit:.1%} |

---

## 📊 Statistical Significance

| Metric | Value | Status |
|--------|-------|--------|
| **P-Value** | {result.p_value:.4f} | {'✅ Significant' if result.is_statistically_significant else '❌ Not significant'} |
| **Confidence Interval** | [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}] | 95% CI |
"""
    
    md += f"""

---

## 📝 Analysis

### Strengths
"""
    
    strengths = []
    if result.total_return_pct > 0:
        strengths.append("- ✅ Profitable strategy with positive returns")
    if result.win_rate > 0.5:
        strengths.append(f"- ✅ Good win rate at {result.win_rate:.1%}")
    if result.max_drawdown_pct < 20:
        strengths.append(f"- ✅ Acceptable max drawdown ({result.max_drawdown_pct:.1f}%)")
    if hasattr(result, 'mc_probability_of_profit') and result.mc_probability_of_profit > 0.6:
        strengths.append("- ✅ Robust results confirmed by Monte Carlo")
    
    if not strengths:
        strengths.append("- ⚠️ No significant strengths identified in this period")
    
    md += '\n'.join(strengths)
    
    md += """

### Weaknesses / Concerns
"""
    
    weaknesses = []
    if result.total_return_pct <= 0:
        weaknesses.append("- ❌ Strategy unprofitable in this period")
    if result.max_drawdown_pct > 20:
        weaknesses.append(f"- ⚠️ High max drawdown ({result.max_drawdown_pct:.1f}%)")
    if result.sharpe_ratio < 1 and result.sharpe_ratio != 0:
        weaknesses.append(f"- ⚠️ Low Sharpe ratio ({result.sharpe_ratio:.2f})")
    if result.win_rate < 0.4 and result.total_trades > 5:
        weaknesses.append(f"- ⚠️ Low win rate ({result.win_rate:.1%})")
    if len(result.trades) < 5:
        weaknesses.append(f"- ⚠️ Insufficient sample size ({len(result.trades)} trades)")
    
    if not weaknesses:
        weaknesses.append("- ✅ No major concerns identified")
    
    md += '\n'.join(weaknesses)
    
    md += f"""

---

## 🎯 Recommendations

Based on this backtest:

"""
    
    if result.total_return_pct > 20 and result.win_rate > 0.5 and result.max_drawdown_pct < 25:
        md += """1. **✅ Strategy appears viable** - Consider paper trading
2. **Monitor** - Run additional backtests on different symbols/time periods
3. **Risk Management** - Maintain position sizing discipline
"""
    elif result.total_return_pct > 0:
        md += """1. **⚠️ Mixed results** - Requires more testing
2. **Improve** - Analyze losing trades for patterns
3. **Extend** - Test on longer time period
"""
    else:
        md += """1. **❌ Strategy underperformed** - Do not use in current form
2. **Analyze** - Review entry/exit criteria
3. **Modify** - Consider parameter adjustments
"""
    
    md += f"""
---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Data source: Alpaca (paper) + yfinance historical*
"""
    
    return md


def run_both_backtests(symbol='NVDA', days=30):
    """Run both strategies and generate reports."""
    
    print("=" * 80)
    print("  QUANT TRADING BACKTEST SUITE")
    print("=" * 80)
    print(f"\nSymbol: {symbol}")
    print(f"Lookback: {days} days")
    print(f"Initial Capital: $100,000")
    
    # Initialize client
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_API_SECRET,
        paper=True
    )
    client.authenticate()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    reports = {}
    
    # Strategy 1: Wheel
    print("\n" + "-" * 80)
    print("  STRATEGY 1: WHEEL (Cash-Secured Puts → Covered Calls)")
    print("-" * 80)
    
    paper1 = create_paper_environment(100000.0)
    wheel_backtester = WheelStrategyBacktester(client, paper1, dte=30, target_delta=0.30)
    wheel_result = wheel_backtester.run_backtest(symbol, start_date, end_date, 100000.0)
    
    wheel_md = generate_markdown_report(wheel_result, symbol, days, "Wheel Strategy")
    reports['wheel'] = wheel_md
    
    print(f"\nReturn: {wheel_result.total_return_pct:+.2f}%")
    print(f"Trades: {wheel_result.total_trades}")
    print(f"Win Rate: {wheel_result.win_rate:.1%}")
    
    # Strategy 2: Compra a Seco
    print("\n" + "-" * 80)
    print("  STRATEGY 2: COMPRA A SECO (Momentum Breakout)")
    print("-" * 80)
    
    paper2 = create_paper_environment(100000.0)
    momentum_backtester = MomentumBreakoutBacktester(client, paper2)
    momentum_result = momentum_backtester.run_backtest(symbol, start_date, end_date, 100000.0)
    
    momentum_md = generate_markdown_report(momentum_result, symbol, days, "Compra a Seco")
    reports['momentum'] = momentum_md
    
    print(f"\nReturn: {momentum_result.total_return_pct:+.2f}%")
    print(f"Trades: {momentum_result.total_trades}")
    print(f"Win Rate: {momentum_result.win_rate:.1%}")
    
    # Generate comparison
    comparison = f"""# 📊 Strategy Comparison Report

## Summary

| Strategy | Return | Win Rate | Max DD | Trades | Sharpe |
|----------|--------|----------|--------|--------|--------|
| **Wheel** | {wheel_result.total_return_pct:+.2f}% | {wheel_result.win_rate:.1%} | {wheel_result.max_drawdown_pct:.1f}% | {wheel_result.total_trades} | {wheel_result.sharpe_ratio:.2f} |
| **Momentum** | {momentum_result.total_return_pct:+.2f}% | {momentum_result.win_rate:.1%} | {momentum_result.max_drawdown_pct:.1f}% | {momentum_result.total_trades} | {momentum_result.sharpe_ratio:.2f} |

## Winner: {'🎯 Compra a Seco' if momentum_result.total_return_pct > wheel_result.total_return_pct else '⚙️ Wheel'}

---

{wheel_md}

---

{momentum_md}

---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # Save reports
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with open(f'backtest_wheel_{symbol}_{days}d_{timestamp}.md', 'w', encoding='utf-8') as f:
        f.write(wheel_md)
    
    with open(f'backtest_momentum_{symbol}_{days}d_{timestamp}.md', 'w', encoding='utf-8') as f:
        f.write(momentum_md)
    
    with open(f'backtest_comparison_{symbol}_{days}d_{timestamp}.md', 'w', encoding='utf-8') as f:
        f.write(comparison)
    
    print("\n" + "=" * 80)
    print("  REPORTS SAVED")
    print("=" * 80)
    print(f"\n✅ Wheel Report: backtest_wheel_{symbol}_{days}d_{timestamp}.md")
    print(f"✅ Momentum Report: backtest_momentum_{symbol}_{days}d_{timestamp}.md")
    print(f"✅ Comparison: backtest_comparison_{symbol}_{days}d_{timestamp}.md")
    
    client.close()
    
    return reports


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'NVDA'
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    run_both_backtests(symbol, days)
