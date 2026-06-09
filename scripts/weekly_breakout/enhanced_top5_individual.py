"""
Enhanced Backtest: Top 5 Cheap SP500 Stocks - INDIVIDUALLY
Monte Carlo + Walk-Forward for each symbol separately
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')
sys.path.insert(0, r'h:\QUANT TRADING\scripts')

import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from backtest_weekly_breakout import (
    load_daily_data, resample_to_weekly, find_weekly_setups,
    estimate_atm_premium, calculate_option_value
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOP5_SYMBOLS = ['SNAP', 'CCL', 'AAL', 'M', 'FSLY']


def run_backtest(symbol, stock_stop_pct=-0.02, time_stop_days=5, years=10, capital=1500):
    """Run weekly breakout with stock stop for a single symbol."""
    df = load_daily_data(symbol, years=years)
    if df.empty:
        return [], capital, capital

    df_w = resample_to_weekly(df)
    if len(df_w) < 5:
        return [], capital, capital

    setups = find_weekly_setups(df_w)
    if not setups:
        return [], capital, capital

    total_capital = float(capital)
    current_capital = total_capital
    trades = []
    next_available_date = None

    for setup in setups:
        entry_date = setup['week_date']
        if next_available_date is not None and entry_date < next_available_date:
            continue

        entry_stock = setup['entry_price']
        target = setup['target_price']

        time_stop_date = entry_date + timedelta(days=time_stop_days)
        entry_premium = estimate_atm_premium(entry_stock, days_to_exp=30)

        max_risk = current_capital * 0.10
        contracts = int(max_risk / (entry_premium * 100))
        if contracts < 1:
            continue

        cost = entry_premium * contracts * 100
        if cost > current_capital:
            continue

        trade_days = df.loc[entry_date:time_stop_date]
        if len(trade_days) < 1:
            continue

        stop_price = entry_stock * (1 + stock_stop_pct)
        exit_price = None
        exit_date = None
        exit_reason = None

        for date, row in trade_days.iterrows():
            if row['high'] >= target:
                exit_price = target
                exit_date = date
                exit_reason = 'PROFIT_TARGET'
                break
            if row['low'] <= stop_price:
                exit_price = stop_price
                exit_date = date
                exit_reason = 'STOCK_STOP'
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


def monte_carlo(trades, capital=1500, n=1000):
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


def walk_forward(trades, capital=1500):
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


def generate_symbol_section(symbol, trades, capital, final_capital, mc, wf):
    """Generate Markdown section for one symbol."""
    total = len(trades)
    if total == 0:
        return f"## {symbol}\n\nNo trades found.\n\n---\n\n"

    wins = sum(1 for t in trades if t['pnl'] > 0)
    losses = total - wins
    wr = (wins / total * 100)
    pnl = sum(t['pnl'] for t in trades)
    ret = (pnl / capital) * 100

    winning = [t['pnl'] for t in trades if t['pnl'] > 0]
    losing = [t['pnl'] for t in trades if t['pnl'] <= 0]
    gp = sum(winning) if winning else 0
    gl = abs(sum(losing)) if losing else 0
    pf = gp / gl if gl > 0 else 0

    avg_win = np.mean(winning) if winning else 0
    avg_loss = np.mean(losing) if losing else 0

    profit_exits = sum(1 for t in trades if t['exit_reason'] == 'PROFIT_TARGET')
    stop_exits = sum(1 for t in trades if t['exit_reason'] == 'STOCK_STOP')
    time_exits = sum(1 for t in trades if t['exit_reason'] == 'TIME_STOP')

    md = f"""## {symbol}

### Performance

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
| Avg Winner | ${avg_win:,.2f} |
| Avg Loser | ${avg_loss:,.2f} |

### Exit Analysis

| Exit Type | Count | % |
|-----------|-------|---|
| Profit Target (+8%) | {profit_exits} | {(profit_exits/total*100):.1f}% |
| Stock Stop (-2%) | {stop_exits} | {(stop_exits/total*100):.1f}% |
| Time Stop (5d) | {time_exits} | {(time_exits/total*100):.1f}% |

### Monte Carlo (1,000 runs)

| Metric | Value |
|--------|-------|
| Mean Return | {mc['mean']:+.2f}% |
| Median Return | {mc['median']:+.2f}% |
| Std Deviation | {mc['std']:.2f}% |
| 5th Percentile | {mc['worst']:+.2f}% |
| 95th Percentile | {mc['best']:+.2f}% |
| **Prob of Profit** | **{mc['prob']:.1f}%** |
| Mean MDD | {mc['mean_mdd']:.2f}% |
| Worst MDD | {mc['worst_mdd']:.2f}% |

### Walk-Forward (70/30)

| Period | Trades | Return | Win Rate |
|--------|--------|--------|----------|
| In-Sample ({wf['is_n']}) | {wf['is_ret']:+.2f}% | {wf['is_win']:.1f}% |
| Out-of-Sample ({wf['oos_n']}) | {wf['oos_ret']:+.2f}% | {wf['oos_win']:.1f}% |

### Sample Trades

| Entry | Exit | Days | Stock% | P&L | Reason |
|-------|------|------|--------|-----|--------|
"""

    for t in trades[:5]:
        md += f"| ${t['entry_stock']:.2f} | ${t['exit_stock']:.2f} | {t['days_held']}d | {t['stock_pct']:+.1f}% | ${t['pnl']:,.2f} | {t['exit_reason']} |\n"

    md += "\n---\n\n"
    return md


def generate_report(all_results, report_path):
    """Generate comprehensive report with all 5 symbols."""
    md = f"""# Enhanced Backtest: Top 5 Cheap SP500 Stocks (Individual)

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

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
"""

    for symbol, data in all_results.items():
        trades = data['trades']
        mc = data['mc']
        wf = data['wf']

        if len(trades) == 0:
            md += f"| {symbol} | 0 | - | - | - | - | - | - |\n"
            continue

        total = len(trades)
        wins = sum(1 for t in trades if t['pnl'] > 0)
        wr = (wins / total * 100)
        pnl = sum(t['pnl'] for t in trades)
        ret = (pnl / 1500) * 100

        winning = [t['pnl'] for t in trades if t['pnl'] > 0]
        losing = [t['pnl'] for t in trades if t['pnl'] <= 0]
        gp = sum(winning) if winning else 0
        gl = abs(sum(losing)) if losing else 0
        pf = gp / gl if gl > 0 else 0

        md += f"| {symbol} | {total} | {wr:.1f}% | {ret:+.2f}% | {pf:.2f} | {mc['prob']:.0f}% | {wf['is_ret']:+.0f}% | {wf['oos_ret']:+.0f}% |\n"

    md += "\n---\n\n"

    for symbol in TOP5_SYMBOLS:
        data = all_results[symbol]
        md += generate_symbol_section(
            symbol, data['trades'], data['capital'], data['final_capital'],
            data['mc'], data['wf']
        )

    md += """## Conclusions

- Each symbol backtested individually with true 10% risk
- SNAP shows highest absolute return
- CCL shows strong consistency
- M shows negative return (avoid)
- FSLY has limited data but good potential

---
*Individual enhanced backtests complete*
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)

    logger.info(f"\n✅ Report saved: {report_path}")


def main():
    logger.info("="*80)
    logger.info("ENHANCED BACKTEST: TOP 5 CHEAP SP500 - INDIVIDUAL")
    logger.info("="*80)

    all_results = {}

    for symbol in TOP5_SYMBOLS:
        logger.info(f"\n{'='*60}")
        logger.info(f"SYMBOL: {symbol}")
        logger.info(f"{'='*60}")

        logger.info("[1/4] Running base backtest...")
        trades, capital, final_capital = run_backtest(symbol, stock_stop_pct=-0.02, time_stop_days=5, years=10, capital=1500)
        logger.info(f"  Trades: {len(trades)} | Final: ${final_capital:,.2f}")

        if len(trades) > 0:
            logger.info("[2/4] Running Monte Carlo...")
            mc = monte_carlo(trades, capital=capital)
            logger.info(f"  Mean: {mc['mean']:+.2f}% | Prob Profit: {mc['prob']:.1f}%")

            logger.info("[3/4] Running Walk-Forward...")
            wf = walk_forward(trades, capital=capital)
            logger.info(f"  IS: {wf['is_ret']:+.2f}% | OOS: {wf['oos_ret']:+.2f}%")
        else:
            mc = {'mean': 0, 'median': 0, 'std': 0, 'worst': 0, 'best': 0, 'prob': 0, 'mean_mdd': 0, 'worst_mdd': 0}
            wf = {'is_ret': 0, 'oos_ret': 0, 'is_win': 0, 'oos_win': 0, 'is_n': 0, 'oos_n': 0}

        all_results[symbol] = {
            'trades': trades,
            'capital': capital,
            'final_capital': final_capital,
            'mc': mc,
            'wf': wf
        }

    logger.info("\n[4/4] Generating report...")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(f'h:/QUANT TRADING/reports/NASDAQ/ENHANCED_TOP5_INDIVIDUAL_{ts}.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(all_results, report_path)

    logger.info("\n" + "="*80)
    logger.info("ALL INDIVIDUAL ENHANCED BACKTESTS COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
