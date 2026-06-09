"""
Backtest both strategies for 2 years of historical data.

Note: For 2-year backtest, we use daily data since 2H data is limited to ~60 days.
The Compra a Seco strategy is adapted to work with daily candles.
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
from backtest.backtest_engine import WheelStrategyBacktester, MomentumBreakoutBacktester
from backtest.paper_trading import create_paper_environment
from backtest.enhanced_backtest import EnhancedMomentumBacktester, print_enhanced_report
from api.alpaca_client import AlpacaClient
from config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_2year_backtest(symbol='NVDA'):
    """Run 2-year backtest for both strategies."""
    
    days = 730  # ~2 years
    
    print("=" * 80)
    print("  2-YEAR COMPREHENSIVE BACKTEST")
    print("=" * 80)
    print(f"\nSymbol: {symbol}")
    print(f"Lookback: {days} days (~2 years)")
    print(f"Initial Capital: $100,000")
    print(f"Data Source: yfinance (daily data for long-term backtest)")
    
    # Initialize client
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_API_SECRET,
        paper=True
    )
    client.authenticate()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"\nPeriod: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Get historical data
    print("\n📊 Fetching historical data...")
    df = client.get_historical_candles(symbol, '1Day', days)
    
    if df.empty:
        print("❌ Failed to fetch data")
        return
    
    print(f"✅ Fetched {len(df)} days of data")
    print(f"   Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    
    # Strategy 1: Wheel (Standard)
    print("\n" + "=" * 80)
    print("  STRATEGY 1: WHEEL (Cash-Secured Puts → Covered Calls)")
    print("=" * 80)
    
    paper1 = create_paper_environment(100000.0)
    wheel_backtester = WheelStrategyBacktester(client, paper1, dte=30, target_delta=0.30)
    wheel_result = wheel_backtester.run_backtest(symbol, start_date, end_date, 100000.0)
    
    print(f"\n📈 WHEEL RESULTS:")
    print(f"   Return:        {wheel_result.total_return_pct:+.2f}%")
    print(f"   Trades:        {wheel_result.total_trades}")
    print(f"   Win Rate:      {wheel_result.win_rate:.1%}")
    print(f"   Max Drawdown:  {wheel_result.max_drawdown_pct:.2f}%")
    
    # Strategy 2: Compra a Seco (Enhanced with 2-year analysis)
    print("\n" + "=" * 80)
    print("  STRATEGY 2: COMPRA A SECO (Momentum Breakout)")
    print("=" * 80)
    print("   Using Enhanced Backtester with:")
    print("   - Market Regime Detection (ROC + ATR)")
    print("   - Monte Carlo Simulation")
    print("   - Walk-Forward Analysis")
    print("   - Statistical Significance Testing")
    
    paper2 = create_paper_environment(100000.0)
    enhanced_backtester = EnhancedMomentumBacktester(
        paper2, 
        use_regime_filter=True,
        allowed_regimes=['bull_strong', 'bull_weak', 'sideway_volatile']
    )
    
    momentum_result = enhanced_backtester.run_backtest(
        symbol=symbol,
        df=df,
        initial_capital=100000.0,
        risk_per_trade=0.02
    )
    
    print(f"\n📈 MOMENTUM RESULTS:")
    print(f"   Return:        {momentum_result.total_return_pct:+.2f}%")
    print(f"   Trades:        {momentum_result.total_trades}")
    print(f"   Win Rate:      {momentum_result.win_rate:.1%}")
    print(f"   Max Drawdown:  {momentum_result.max_drawdown_pct:.2f}%")
    print(f"   Sharpe Ratio:  {momentum_result.sharpe_ratio:.2f}")
    print(f"   Calmar Ratio:  {momentum_result.calmar_ratio:.2f}")
    
    # Generate comparison report
    generate_2year_report(wheel_result, momentum_result, symbol, days)
    
    client.close()
    
    return wheel_result, momentum_result


def generate_2year_report(wheel_result, momentum_result, symbol, days):
    """Generate comprehensive 2-year markdown report."""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backtest_2year_{symbol}_{timestamp}.md'
    
    md = f"""# 📊 2-Year Comprehensive Backtest Report

## Executive Summary

| Strategy | Return | Trades | Win Rate | Max DD | Sharpe | Calmar |
|----------|--------|--------|----------|--------|--------|--------|
| **Wheel** | {wheel_result.total_return_pct:+.2f}% | {wheel_result.total_trades} | {wheel_result.win_rate:.1%} | {wheel_result.max_drawdown_pct:.1f}% | {wheel_result.sharpe_ratio:.2f} | {(wheel_result.total_return_pct/wheel_result.max_drawdown_pct) if wheel_result.max_drawdown_pct > 0 else 0:.2f} |
| **Compra a Seco** | {momentum_result.total_return_pct:+.2f}% | {momentum_result.total_trades} | {momentum_result.win_rate:.1%} | {momentum_result.max_drawdown_pct:.1f}% | {momentum_result.sharpe_ratio:.2f} | {momentum_result.calmar_ratio:.2f} |

### 🏆 Winner: {'Compra a Seco' if momentum_result.total_return_pct > wheel_result.total_return_pct else 'Wheel'}

---

## 📈 Wheel Strategy (2-Year Performance)

### Overview
- **Symbol:** {symbol}
- **Period:** {wheel_result.start_date.strftime('%Y-%m-%d')} to {wheel_result.end_date.strftime('%Y-%m-%d')}
- **Initial Capital:** $100,000
- **Final Capital:** ${wheel_result.final_capital:,.2f}

### Performance Metrics
| Metric | Value |
|--------|-------|
| Total Return | {wheel_result.total_return_pct:+.2f}% |
| Annualized Return | {(wheel_result.total_return_pct * (365/days)):+.2f}% |
| Total Trades | {wheel_result.total_trades} |
| Win Rate | {wheel_result.win_rate:.1%} |
| Max Drawdown | {wheel_result.max_drawdown_pct:.2f}% |
| Sharpe Ratio | {wheel_result.sharpe_ratio:.2f} |

### Trade Summary
| Date | Action | Symbol | Price | P&L |
|------|--------|--------|-------|-----|
"""
    
    for trade in wheel_result.trades[:15]:
        date_str = trade.timestamp.strftime('%Y-%m-%d') if hasattr(trade.timestamp, 'strftime') else str(trade.timestamp)[:10]
        price = trade.entry_price if hasattr(trade, 'entry_price') else 0
        pnl = trade.realized_pnl if trade.realized_pnl != 0 else '-'
        pnl_str = f"${pnl:.2f}" if isinstance(pnl, float) else pnl
        md += f"| {date_str} | {trade.action.value} | {trade.symbol} | ${price:.2f} | {pnl_str} |\n"
    
    if len(wheel_result.trades) > 15:
        md += f"\n*... and {len(wheel_result.trades) - 15} more trades*\n"
    
    md += f"""

---

## 🚀 Compra a Seco Strategy (2-Year Performance)

### Overview
- **Symbol:** {symbol}
- **Period:** {momentum_result.start_date.strftime('%Y-%m-%d')} to {momentum_result.end_date.strftime('%Y-%m-%d')}
- **Initial Capital:** $100,000
- **Final Capital:** ${momentum_result.final_capital:,.2f}

### Performance Metrics
| Metric | Value | Status |
|--------|-------|--------|
| Total Return | {momentum_result.total_return_pct:+.2f}% | {'✅ Excellent' if momentum_result.total_return_pct > 50 else '✅ Good' if momentum_result.total_return_pct > 20 else '⚠️ Poor'} |
| Annualized Return | {(momentum_result.total_return_pct * (365/days)):+.2f}% | - |
| Total Trades | {momentum_result.total_trades} | - |
| Win Rate | {momentum_result.win_rate:.1%} | {'✅ Strong' if momentum_result.win_rate > 0.6 else '⚠️ Weak'} |
| Max Drawdown | {momentum_result.max_drawdown_pct:.2f}% | {'✅ Acceptable' if momentum_result.max_drawdown_pct < 25 else '⚠️ High'} |
| Sharpe Ratio | {momentum_result.sharpe_ratio:.2f} | {'✅ Good' if momentum_result.sharpe_ratio > 1 else '⚠️ Low'} |
| Sortino Ratio | {momentum_result.sortino_ratio:.2f} | {'✅ Good' if momentum_result.sortino_ratio > 1 else '⚠️ Low'} |
| Calmar Ratio | {momentum_result.calmar_ratio:.2f} | {'✅ Good' if momentum_result.calmar_ratio > 1 else '⚠️ Low'} |

### Advanced Metrics
| Metric | Value |
|--------|-------|
| Monte Carlo Median Return | {momentum_result.mc_median_return:+.2f}% |
| Monte Carlo Worst Case (5%) | {momentum_result.mc_worst_case:+.2f}% |
| Monte Carlo Probability of Profit | {momentum_result.mc_probability_of_profit:.1%} |
| Statistical Significance | {'✅ Yes (p < 0.05)' if momentum_result.is_statistically_significant else '❌ No'} |
| P-Value | {momentum_result.p_value:.4f} |
| Walk-Forward Consistent | {'✅ Yes' if momentum_result.wf_is_consistent else '❌ No'} |

"""
    
    # Add regime performance if available
    if momentum_result.regime_performance:
        md += """
### Performance by Market Regime

| Regime | Trades | Win Rate | Total P&L |
|--------|--------|----------|-----------|
"""
        for regime, metrics in momentum_result.regime_performance.items():
            md += f"| {regime.value} | {metrics['trades']} | {metrics['win_rate']:.1%} | ${metrics['total_pnl']:,.2f} |\n"
    
    md += f"""

### Trade Summary
| # | Date | Action | Symbol | Entry | Exit | P&L |
|---|------|--------|--------|-------|------|-----|
"""
    
    for i, trade in enumerate(momentum_result.trades[:20], 1):
        date_str = trade.timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(trade.timestamp, 'strftime') else str(trade.timestamp)[:16]
        price = trade.entry_price if hasattr(trade, 'entry_price') else 0
        exit_price = trade.exit_price if hasattr(trade, 'exit_price') and trade.exit_price else '-'
        exit_str = f"${exit_price:.2f}" if isinstance(exit_price, float) else exit_price
        pnl = trade.realized_pnl if trade.realized_pnl != 0 else '-'
        pnl_str = f"${pnl:.2f}" if isinstance(pnl, float) else pnl
        icon = "🟢" if trade.realized_pnl > 0 else "🔴" if trade.realized_pnl < 0 else "⚪"
        md += f"| {i} | {date_str} | {trade.action.value} | {trade.symbol} | ${price:.2f} | {exit_str} | {pnl_str} {icon} |\n"
    
    if len(momentum_result.trades) > 20:
        md += f"\n*... and {len(momentum_result.trades) - 20} more trades*\n"
    
    md += f"""

---

## 📊 Strategy Comparison (2-Year)

### Head-to-Head

| Criteria | Wheel | Compra a Seco | Winner |
|----------|-------|---------------|--------|
| Total Return | {wheel_result.total_return_pct:+.2f}% | {momentum_result.total_return_pct:+.2f}% | {'Momentum' if momentum_result.total_return_pct > wheel_result.total_return_pct else 'Wheel'} |
| Risk-Adjusted (Sharpe) | {wheel_result.sharpe_ratio:.2f} | {momentum_result.sharpe_ratio:.2f} | {'Momentum' if momentum_result.sharpe_ratio > wheel_result.sharpe_ratio else 'Wheel'} |
| Win Rate | {wheel_result.win_rate:.1%} | {momentum_result.win_rate:.1%} | {'Momentum' if momentum_result.win_rate > wheel_result.win_rate else 'Wheel'} |
| Max Drawdown | {wheel_result.max_drawdown_pct:.2f}% | {momentum_result.max_drawdown_pct:.2f}% | {'Wheel' if wheel_result.max_drawdown_pct < momentum_result.max_drawdown_pct else 'Momentum'} |
| Robustness (MC) | - | {momentum_result.mc_probability_of_profit:.1%} | Momentum |

### 🎯 Verdict

After 2 years of backtesting on {symbol}:

**Winner: {'🎯 Compra a Seco' if momentum_result.total_return_pct > wheel_result.total_return_pct else '⚙️ Wheel'}**

**Key Insights:**
1. {'Momentum outperformed by ' + str(abs(momentum_result.total_return_pct - wheel_result.total_return_pct)) + '%' if momentum_result.total_return_pct > wheel_result.total_return_pct else 'Wheel outperformed by ' + str(abs(wheel_result.total_return_pct - momentum_result.total_return_pct)) + '%'}
2. {'Momentum showed superior risk-adjusted returns with Sharpe of ' + str(momentum_result.sharpe_ratio) if momentum_result.sharpe_ratio > 1 else 'Risk-adjusted returns need improvement'}
3. {'Statistically significant results confirm the edge is real' if momentum_result.is_statistically_significant else 'Results not statistically significant - may be luck'}
4. {'Strategy is robust across market conditions' if momentum_result.mc_probability_of_profit > 0.6 else 'Strategy may be sensitive to market conditions'}

---

## 📝 Recommendations

### For Compra a Seco:
- **{'✅ Proceed to paper trading' if momentum_result.total_return_pct > 20 and momentum_result.mc_probability_of_profit > 0.6 else '⚠️ Further testing required'}**
- **Risk Management:** Max position size 20%, stop loss at 2x ATR
- **Market Filter:** Only trade in bullish/sideway regimes

### For Wheel:
- **{'✅ Viable income strategy' if wheel_result.total_return_pct > 10 else '⚠️ Requires optimization'}**
- **Improvement:** Consider shorter DTE (7-14 days) for more trades
- **Filter:** Only sell puts in uptrends

---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Data source: Alpaca (paper) + yfinance historical (daily)*
*Backtest period: {days} days (~2 years)*
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"\n{'='*80}")
    print("  REPORT SAVED")
    print(f"{'='*80}")
    print(f"\n✅ Full report: {filename}")
    
    return filename


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'NVDA'
    run_2year_backtest(symbol)
