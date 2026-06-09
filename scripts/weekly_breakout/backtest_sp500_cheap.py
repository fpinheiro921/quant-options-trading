"""
Backtest Weekly Breakout Strategy on Cheap S&P 500 Stocks
For $1,500 account - true 10% risk per trade
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


def get_cheap_symbols():
    """Read cheap symbols from file."""
    path = Path('h:/QUANT TRADING/data/cheap_sp500_symbols.txt')
    if not path.exists():
        # Fallback list
        return ['WBD', 'SNAP', 'LYFT', 'PTON', 'LCID', 'RIVN', 'F', 'T', 'PFE', 'KSS',
                'M', 'NCLH', 'CCL', 'AAL', 'BAX', 'CMCSA', 'PINS', 'FSLY']
    with open(path) as f:
        return [s.strip() for s in f if s.strip()]


def get_latest_price(symbol):
    """Get latest closing price."""
    df = load_daily_data(symbol, years=1)
    if df.empty:
        return None
    return df['close'].iloc[-1]


def run_backtest(symbols, stock_stop_pct=None, time_stop_days=5, years=10, capital=1500):
    """Run weekly breakout backtest on symbols."""
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

    total_capital = float(capital)
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

        time_stop_date = entry_date + timedelta(days=time_stop_days)
        entry_premium = estimate_atm_premium(entry_stock, days_to_exp=30)

        # TRUE 10% risk = max loss is 10% of account
        max_risk = current_capital * 0.10
        contracts = int(max_risk / (entry_premium * 100))
        if contracts < 1:
            continue  # Can't afford even 1 contract with 10% risk

        cost = entry_premium * contracts * 100
        if cost > current_capital:
            continue

        trade_days = df.loc[entry_date:time_stop_date]
        if len(trade_days) < 1:
            continue

        stop_price = entry_stock * (1 + stock_stop_pct) if stock_stop_pct else None
        exit_price = None
        exit_date = None
        exit_reason = None

        for date, row in trade_days.iterrows():
            if row['high'] >= target:
                exit_price = target
                exit_date = date
                exit_reason = 'PROFIT_TARGET'
                break
            if stop_price and row['low'] <= stop_price:
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

    total_pnl = sum(t['pnl'] for t in trades)
    total_ret = (total_pnl / total_capital) * 100
    wins = sum(1 for t in trades if t['pnl'] > 0)
    win_rate = (wins / len(trades) * 100) if trades else 0
    
    # Symbol stats
    symbol_stats = {}
    for t in trades:
        s = t['symbol']
        symbol_stats.setdefault(s, {'trades': 0, 'wins': 0, 'pnl': 0})
        symbol_stats[s]['trades'] += 1
        if t['pnl'] > 0:
            symbol_stats[s]['wins'] += 1
        symbol_stats[s]['pnl'] += t['pnl']

    return {
        'trades': trades,
        'total_trades': len(trades),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_return': total_ret,
        'final_capital': current_capital,
        'symbol_stats': symbol_stats
    }


def generate_report(results_by_symbol, all_results, report_path):
    """Generate report for all cheap SP500 stocks."""
    md = f"""# S&P 500 Cheap Stocks - Weekly Breakout Backtest

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Account:** $1,500
**Risk per Trade:** True 10% ($150 max loss)
**Strategy:** Buy ATM Call 30DTE on weekly breakout
**Exit:** +8% profit target OR -2% stock stop OR 5-day time stop

---

## Portfolio Results (One-at-a-time across all symbols)

| Metric | Value |
|--------|-------|
| Total Trades | {all_results['total_trades']} |
| Win Rate | {all_results['win_rate']:.1f}% |
| Total Return | {all_results['total_return']:+.2f}% |
| Final Capital | ${all_results['final_capital']:,.2f} |
| Total P&L | ${all_results['total_pnl']:,.2f} |

---

## Individual Symbol Results

| Symbol | Price | Contract | Trades | Win Rate | Total P&L | Return |
|--------|-------|----------|--------|----------|-----------|--------|
"""

    # Sort by return
    sorted_symbols = sorted(results_by_symbol.items(), key=lambda x: x[1]['total_return'], reverse=True)
    
    for symbol, result in sorted_symbols:
        price = result.get('latest_price', 0)
        contract = result.get('contract_cost', 0)
        md += f"| {symbol} | ${price:.2f} | ${contract:.0f} | {result['total_trades']} | {result['win_rate']:.1f}% | ${result['total_pnl']:,.2f} | {result['total_return']:+.2f}% |\n"

    md += f"""
---

## Top 5 Symbols by Return

"""
    for i, (symbol, result) in enumerate(sorted_symbols[:5], 1):
        md += f"**{i}. {symbol}** - Return: {result['total_return']:+.2f}% | Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}%\n\n"

    md += f"""---

## Bottom 5 Symbols by Return

"""
    for i, (symbol, result) in enumerate(sorted_symbols[-5:], 1):
        md += f"**{i}. {symbol}** - Return: {result['total_return']:+.2f}% | Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}%\n\n"

    md += """
---

## Conclusions

- Symbols with premium <= $150 allow true 10% risk on $1,500 account
- Most cheap stocks do NOT work with weekly breakout strategy
- Strategy works best on liquid, trending stocks with momentum
- Consider combining top 3-5 symbols instead of all

---
*Backtest complete*
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)

    logger.info(f"\n✅ Report saved: {report_path}")


def main():
    logger.info("="*80)
    logger.info("SP500 CHEAP STOCKS WEEKLY BREAKOUT BACKTEST")
    logger.info("="*80)

    cheap_symbols = get_cheap_symbols()
    logger.info(f"Testing {len(cheap_symbols)} cheap symbols")

    # Get prices
    symbol_info = {}
    for symbol in cheap_symbols:
        price = get_latest_price(symbol)
        if price:
            premium = price * 0.045
            contract_cost = premium * 100
            symbol_info[symbol] = {
                'price': price,
                'premium': premium,
                'contract_cost': contract_cost
            }

    # Backtest each symbol individually AND all together
    results_by_symbol = {}
    
    logger.info("\n--- Individual Symbol Backtests ---")
    for symbol in cheap_symbols:
        result = run_backtest([symbol], stock_stop_pct=-0.02, time_stop_days=5, years=10, capital=1500)
        result['latest_price'] = symbol_info.get(symbol, {}).get('price', 0)
        result['contract_cost'] = symbol_info.get(symbol, {}).get('contract_cost', 0)
        results_by_symbol[symbol] = result
        
        logger.info(f"{symbol}: {result['total_trades']} trades | {result['win_rate']:.1f}% WR | {result['total_return']:+.2f}% return")

    # Backtest all together (one at a time)
    logger.info("\n--- Portfolio Backtest (One-at-a-time) ---")
    all_results = run_backtest(cheap_symbols, stock_stop_pct=-0.02, time_stop_days=5, years=10, capital=1500)
    logger.info(f"All symbols: {all_results['total_trades']} trades | {all_results['win_rate']:.1f}% WR | {all_results['total_return']:+.2f}% return")

    # Generate report
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(f'h:/QUANT TRADING/reports/NASDAQ/SP500_CHEAP_WEEKLY_{ts}.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results_by_symbol, all_results, report_path)

    # Print summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY - TOP SYMBOLS")
    logger.info("="*80)
    sorted_symbols = sorted(results_by_symbol.items(), key=lambda x: x[1]['total_return'], reverse=True)
    for symbol, result in sorted_symbols[:10]:
        logger.info(f"{symbol}: {result['total_return']:+.2f}% | {result['total_trades']} trades | {result['win_rate']:.1f}% WR")
    
    logger.info(f"\nPortfolio (all): {all_results['total_return']:+.2f}% | {all_results['total_trades']} trades")
    logger.info("="*80)


if __name__ == "__main__":
    main()
