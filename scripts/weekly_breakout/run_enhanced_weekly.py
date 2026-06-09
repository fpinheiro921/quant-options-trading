"""
Enhanced Weekly Breakout Backtest with Monte Carlo, Walk-Forward, and Stats.
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')
sys.path.insert(0, r'h:\QUANT TRADING\scripts')

import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from backtest_weekly_breakout import (
    NASDAQ_SYMBOLS, load_daily_data, resample_to_weekly,
    find_weekly_setups, estimate_atm_premium, calculate_option_value
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_backtest(symbols, years=10):
    """Run the weekly breakout backtest."""
    all_data = {}
    all_weekly = {}

    for symbol in symbols:
        df = load_daily_data(symbol, years=years)
        if not df.empty:
            df_w = resample_to_weekly(df)
            if len(df_w) >= 5:
                all_data[symbol] = df
                all_weekly[symbol] = df_w

    all_setups = []
    for symbol, df_w in all_weekly.items():
        setups = find_weekly_setups(df_w)
        for s in setups:
            all_setups.append({
                'week_date': s['week_date'],
                'symbol': symbol,
                'entry_price': s['entry_price'],
                'target_price': s['target_price'],
                'df': all_data[symbol]
            })

    all_setups.sort(key=lambda x: x['week_date'])

    total_capital = 50000.0
    current_capital = total_capital
    trades = []
    next_available_date = None

    for setup in all_setups:
        entry_date = setup['week_date']
        if next_available_date is not None and entry_date < next_available_date:
            continue

        symbol = setup['symbol']
        entry_stock = setup['entry_price']
        target = setup['target_price']
        df = setup['df']

        time_stop_date = entry_date + timedelta(days=5)
        entry_premium = estimate_atm_premium(entry_stock, days_to_exp=30)

        max_risk = current_capital * 0.10
        contracts = int(max_risk / (entry_premium * 100))
        if contracts < 1:
            contracts = 1

        cost = entry_premium * contracts * 100
        if cost > current_capital:
            continue

        trade_days = df.loc[entry_date:time_stop_date]
        if len(trade_days) < 1:
            continue

        exit_price = None
        exit_date = None
        exit_reason = None

        for date, row in trade_days.iterrows():
            if row['high'] >= target:
                exit_price = target
                exit_date = date
                exit_reason = 'PROFIT_TARGET'
                break
            if date >= time_stop_date:
                exit_price = row['close']
                exit_date = date
                exit_reason = 'TIME_STOP'
                break

        if exit_price is None:
            last_day = trade_days.iloc[-1]
            exit_price = last_day['close']
            exit_date = trade_days.index[-1]
            exit_reason = 'TIME_STOP'

        days_held = (exit_date - entry_date).days
        final_premium = calculate_option_value(
            entry_stock, exit_price, entry_premium,
            max(0, (30 - days_held)), 30
        )
        pnl = (final_premium - entry_premium) * contracts * 100

        trades.append({
            'symbol': symbol,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'days_held': days_held,
            'entry_stock': entry_stock,
            'exit_stock': exit_price,
            'entry_premium': entry_premium,
            'exit_premium': final_premium,
            'contracts': contracts,
            'cost': cost,
            'pnl': pnl,
            'pnl_pct': (pnl / cost) * 100,
            'stock_pct': ((exit_price - entry_stock) / entry_stock) * 100,
            'exit_reason': exit_reason
        })

        current_capital += pnl
        next_available_date = time_stop_date + timedelta(days=1)

    return trades, total_capital, current_capital


def monte_carlo(trades, capital=50000, n=1000):
    """Monte Carlo simulation."""
    np.random.seed(42)
    returns = []
    mdds = []

    for _ in range(n):
        indices = np.random.choice(len(trades), size=len(trades), replace=True)
        sim = [trades[i] for i in indices]

        eq = capital
        max_eq = eq
        mdd = 0

        for t in sim:
            eq += t['pnl']
            max_eq = max(max_eq, eq)
            dd = (max_eq - eq) / max_eq if max_eq > 0 else 0
            mdd = max(mdd, dd)

        returns.append((eq - capital) / capital)
        mdds.append(mdd)

    return {
        'mean': np.mean(returns) * 100,
        'median': np.median(returns) * 100,
        'std': np.std(returns) * 100,
        'worst': np.percentile(returns, 5) * 100,
        'best': np.percentile(returns, 95) * 100,
        'prob': np.mean([r > 0 for r in returns]) * 100,
        'mean_mdd': np.mean(mdds) * 100,
        'worst_mdd': np.percentile(mdds, 95) * 100
    }


def walk_forward(trades, capital=50000):
    """70/30 walk-forward."""
    split = int(len(trades) * 0.7)
    is_trades = trades[:split]
    oos_trades = trades[split:]

    def ret(tl):
        return (sum(t['pnl'] for t in tl) / capital) * 100

    def wr(tl):
        return (sum(1 for t in tl if t['pnl'] > 0) / len(tl) * 100) if tl else 0

    return {
        'is_ret': ret(is_trades),
        'oos_ret': ret(oos_trades),
        'is_win': wr(is_trades),
        'oos_win': wr(oos_trades),
        'is_n': len(is_trades),
        'oos_n': len(oos_trades)
    }


def generate_report(trades, capital, final_capital, mc, wf, report_path):
    """Generate enhanced Markdown report."""
    total = len(trades)
    wins = sum(1 for t in trades if t['pnl'] > 0)
    losses = total - wins
    wr = (wins / total * 100) if total > 0 else 0
    pnl = sum(t['pnl'] for t in trades)
    ret = (pnl / capital) * 100

    winning = [t['pnl'] for t in trades if t['pnl'] > 0]
    losing = [t['pnl'] for t in trades if t['pnl'] <= 0]
    gp = sum(winning) if winning else 0
    gl = abs(sum(losing)) if losing else 0
    pf = gp / gl if gl > 0 else 0

    profit_exits = sum(1 for t in trades if t['exit_reason'] == 'PROFIT_TARGET')
    time_exits = sum(1 for t in trades if t['exit_reason'] == 'TIME_STOP')

    symbol_stats = {}
    for t in trades:
        s = t['symbol']
        symbol_stats.setdefault(s, {'trades': 0, 'wins': 0, 'pnl': 0})
        symbol_stats[s]['trades'] += 1
        if t['pnl'] > 0:
            symbol_stats[s]['wins'] += 1
        symbol_stats[s]['pnl'] += t['pnl']

    md = f"""# Enhanced Weekly Breakout Strategy Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
| **Total Return** | **{ret:+.2f}%** |
| Final Capital | ${final_capital:,.2f} |
| Total Trades | {total} |
| Winners | {wins} |
| Losers | {losses} |
| Win Rate | {wr:.1f}% |
| Profit Factor | {pf:.2f} |
| Gross Profit | ${gp:,.2f} |
| Gross Loss | ${gl:,.2f} |

---

## Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target | {profit_exits} | {(profit_exits/total*100):.1f}% |
| Time Stop (5d) | {time_exits} | {(time_exits/total*100):.1f}% |

---

## Symbol Breakdown

| Symbol | Trades | Win Rate | Avg P&L | Total P&L |
|--------|--------|----------|---------|-----------|
"""

    for sym, data in sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr_sym = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
        avg = data['pnl'] / data['trades'] if data['trades'] > 0 else 0
        md += f"| {sym} | {data['trades']} | {wr_sym:.1f}% | ${avg:,.2f} | ${data['pnl']:,.2f} |\n"

    md += f"""
---

## Monte Carlo Simulation (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | {mc['mean']:+.2f}% |
| Median Return | {mc['median']:+.2f}% |
| Std Deviation | {mc['std']:.2f}% |
| 5th Percentile | {mc['worst']:+.2f}% |
| 95th Percentile | {mc['best']:+.2f}% |
| **Probability of Profit** | **{mc['prob']:.1f}%** |
| Mean Max Drawdown | {mc['mean_mdd']:.2f}% |
| Worst Case MDD | {mc['worst_mdd']:.2f}% |

---

## Walk-Forward Analysis (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample ({wf['is_n']} trades) | {wf['is_ret']:+.2f}% | {wf['is_win']:.1f}% |
| Out-of-Sample ({wf['oos_n']} trades) | {wf['oos_ret']:+.2f}% | {wf['oos_win']:.1f}% |

---

## Sample Trades

| Symbol | Entry | Exit | Days | Stock% | P&L | Reason |
|--------|-------|------|------|--------|-----|--------|
"""

    for t in trades[:15]:
        md += f"| {t['symbol']} | ${t['entry_stock']:.2f} | ${t['exit_stock']:.2f} | {t['days_held']}d | {t['stock_pct']:+.1f}% | ${t['pnl']:,.2f} | {t['exit_reason']} |\n"

    md += f"""
---

## Conclusions

- **Strategy Return:** {ret:+.2f}%
- **Monte Carlo Profit Probability:** {mc['prob']:.1f}%
- **Walk-Forward Consistency:** {'PASS' if abs(wf['is_ret'] - wf['oos_ret']) < 100 else 'REVIEW'}
- **Overall Assessment:** {'ROBUST' if mc['prob'] > 70 and pf > 1.2 else 'MARGINAL'}

---
*Enhanced backtest complete*
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)

    logger.info(f"\n✅ Report saved: {report_path}")


def main():
    logger.info("="*80)
    logger.info("ENHANCED WEEKLY BREAKOUT BACKTEST - AAPL ONLY")
    logger.info("="*80)

    logger.info("\n[1/4] Running base backtest...")
    trades, capital, final_capital = run_backtest(['AAPL'], years=10)
    logger.info(f"  Trades: {len(trades)} | Final: ${final_capital:,.2f}")

    logger.info("\n[2/4] Running Monte Carlo...")
    mc = monte_carlo(trades, capital=capital)
    logger.info(f"  Mean: {mc['mean']:+.2f}% | Prob Profit: {mc['prob']:.1f}%")

    logger.info("\n[3/4] Running Walk-Forward...")
    wf = walk_forward(trades, capital=capital)
    logger.info(f"  IS: {wf['is_ret']:+.2f}% | OOS: {wf['oos_ret']:+.2f}%")

    logger.info("\n[4/4] Generating report...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(f'h:/QUANT TRADING/reports/NASDAQ/ENHANCED_AAPL_WEEKLY_{ts}.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(trades, capital, final_capital, mc, wf, report_path)

    logger.info("\n" + "="*80)
    logger.info("ENHANCED AAPL BACKTEST COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
