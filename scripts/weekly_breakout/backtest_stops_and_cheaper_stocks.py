"""
Backtest Weekly Breakout with Stock Stop Losses + Cheaper Stocks for $1,500 Account

Two tasks:
1. Test AAPL with stock-based stop losses: -2%, -4%, -6%, -8%, -10%
2. Find cheaper stocks where 30DTE ATM call allows true 10% risk ($150) on $1,500 account
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')
sys.path.insert(0, r'h:\QUANT TRADING\scripts')

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from backtest_weekly_breakout import (
    load_daily_data, resample_to_weekly, find_weekly_setups,
    estimate_atm_premium, calculate_option_value
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_all_available_symbols():
    """Get all symbols from cache."""
    cache_dir = Path('h:/QUANT TRADING/data/massive_cache/stocks')
    symbols = []
    for subdir in cache_dir.iterdir():
        if subdir.is_dir() and (subdir / '1d_5y.csv').exists():
            symbols.append(subdir.name)
    return sorted(symbols)


def get_latest_price(symbol):
    """Get latest closing price."""
    df = load_daily_data(symbol, years=1)
    if df.empty:
        return None
    return df['close'].iloc[-1]


def run_backtest_with_stop(symbols, stock_stop_pct=None, time_stop_days=5, years=10, capital=1500):
    """
    Run weekly breakout backtest.
    
    Args:
        symbols: list of symbols to trade
        stock_stop_pct: stock stop loss (e.g., -0.04 for -4%). None = no stop.
        time_stop_days: days to hold max
        years: backtest years
        capital: starting capital
    """
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

        # Risk 10% per trade = max loss
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

        # Stock stop level
        if stock_stop_pct is not None:
            stop_price = entry_stock * (1 + stock_stop_pct)
        else:
            stop_price = None

        for date, row in trade_days.iterrows():
            # Check profit target first
            if row['high'] >= target:
                exit_price = target
                exit_date = date
                exit_reason = 'PROFIT_TARGET'
                break
            
            # Check stock stop loss
            if stop_price is not None and row['low'] <= stop_price:
                exit_price = stop_price
                exit_date = date
                exit_reason = 'STOCK_STOP'
                break
            
            # Check time stop
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
    
    # Stop loss stats
    stop_exits = sum(1 for t in trades if t['exit_reason'] == 'STOCK_STOP') if stock_stop_pct else 0
    profit_exits = sum(1 for t in trades if t['exit_reason'] == 'PROFIT_TARGET')
    time_exits = sum(1 for t in trades if t['exit_reason'] == 'TIME_STOP')

    return {
        'trades': trades,
        'total_trades': len(trades),
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_return': total_ret,
        'final_capital': current_capital,
        'profit_exits': profit_exits,
        'time_exits': time_exits,
        'stop_exits': stop_exits,
        'stop_pct': stock_stop_pct
    }


def find_cheaper_stocks(max_premium=150, symbols=None):
    """Find stocks where 30DTE ATM call premium <= max_premium."""
    if symbols is None:
        symbols = get_all_available_symbols()
    
    cheap = []
    logger.info(f"\nChecking {len(symbols)} symbols for premium <= ${max_premium}...")
    
    for symbol in symbols:
        price = get_latest_price(symbol)
        if price is None:
            continue
        premium = price * 0.045
        contract_cost = premium * 100
        if contract_cost <= max_premium:
            cheap.append({
                'symbol': symbol,
                'price': price,
                'premium': premium,
                'contract_cost': contract_cost
            })
    
    return sorted(cheap, key=lambda x: x['contract_cost'])


def print_results(name, result):
    """Print backtest results."""
    stop_label = f"Stock Stop {result['stop_pct']*100:.0f}%" if result['stop_pct'] else "No Stock Stop"
    logger.info(f"\n{'='*60}")
    logger.info(f"{name} - {stop_label}")
    logger.info(f"{'='*60}")
    logger.info(f"  Trades: {result['total_trades']}")
    logger.info(f"  Win Rate: {result['win_rate']:.1f}%")
    logger.info(f"  Total P&L: ${result['total_pnl']:,.2f}")
    logger.info(f"  Total Return: {result['total_return']:+.2f}%")
    logger.info(f"  Final Capital: ${result['final_capital']:,.2f}")
    logger.info(f"  Profit Target: {result['profit_exits']} ({result['profit_exits']/result['total_trades']*100:.1f}%)")
    if result['stop_exits'] > 0:
        logger.info(f"  Stock Stop: {result['stop_exits']} ({result['stop_exits']/result['total_trades']*100:.1f}%)")
    logger.info(f"  Time Stop: {result['time_exits']} ({result['time_exits']/result['total_trades']*100:.1f}%)")


def main():
    logger.info("="*80)
    logger.info("WEEKLY BREAKOUT: STOP LOSS & CHEAPER STOCKS BACKTEST")
    logger.info("="*80)
    
    # =====================================================================
    # PART 1: AAPL with different stock stop losses
    # =====================================================================
    logger.info("\n\n[PART 1] AAPL with Stock Stop Losses")
    logger.info("-" * 60)
    
    stop_levels = [-0.02, -0.04, -0.06, -0.08, -0.10]
    aapl_results = []
    
    for stop in stop_levels:
        result = run_backtest_with_stop(['AAPL'], stock_stop_pct=stop, time_stop_days=5, years=10, capital=1500)
        aapl_results.append(result)
        print_results("AAPL", result)
    
    # Also baseline (no stop)
    baseline = run_backtest_with_stop(['AAPL'], stock_stop_pct=None, time_stop_days=5, years=10, capital=1500)
    aapl_results.append(baseline)
    print_results("AAPL", baseline)
    
    # =====================================================================
    # PART 2: Find cheaper stocks for true 10% risk
    # =====================================================================
    logger.info("\n\n[PART 2] Finding Cheaper Stocks for $1,500 Account")
    logger.info("-" * 60)
    
    # Get all available symbols
    all_symbols = get_all_available_symbols()
    logger.info(f"Found {len(all_symbols)} symbols in cache")
    
    # Find stocks where 1 contract costs <= $150 (true 10% risk)
    cheap_stocks = find_cheaper_stocks(max_premium=150, symbols=all_symbols)
    
    logger.info(f"\nStocks with option premium <= $150 (true 10% risk on $1,500):")
    logger.info(f"{'Symbol':<10} {'Price':>8} {'Premium':>10} {'Contract':>10}")
    logger.info("-" * 45)
    for s in cheap_stocks[:15]:
        logger.info(f"{s['symbol']:<10} ${s['price']:>7.2f} ${s['premium']:>9.2f} ${s['contract_cost']:>9.2f}")
    
    # =====================================================================
    # PART 3: Backtest cheaper stocks
    # =====================================================================
    if cheap_stocks:
        # Top 10 cheapest
        test_symbols = [s['symbol'] for s in cheap_stocks[:10]]
        logger.info(f"\n\n[PART 3] Backtesting Top {len(test_symbols)} Cheapest Stocks")
        logger.info(f"Symbols: {', '.join(test_symbols)}")
        logger.info("-" * 60)
        
        for symbol_data in cheap_stocks[:10]:
            symbol = symbol_data['symbol']
            result = run_backtest_with_stop([symbol], stock_stop_pct=None, time_stop_days=5, years=10, capital=1500)
            
            logger.info(f"\n{symbol} @ ${symbol_data['price']:.2f} (Contract: ${symbol_data['contract_cost']:.0f})")
            logger.info(f"  Trades: {result['total_trades']} | Win Rate: {result['win_rate']:.1f}% | Return: {result['total_return']:+.2f}%")
            logger.info(f"  Final: ${result['final_capital']:,.2f} | P&L: ${result['total_pnl']:,.2f}")
    
    # =====================================================================
    # PART 4: Summary comparison
    # =====================================================================
    logger.info("\n\n" + "="*80)
    logger.info("SUMMARY COMPARISON")
    logger.info("="*80)
    
    logger.info("\nAAPL with Different Stock Stops ($1,500 account):")
    logger.info(f"{'Stop Loss':<15} {'Trades':>8} {'Win%':>8} {'Return':>10} {'Final':>12}")
    logger.info("-" * 60)
    for r in aapl_results:
        stop_label = f"{r['stop_pct']*100:.0f}%" if r['stop_pct'] else "None (Base)"
        logger.info(f"{stop_label:<15} {r['total_trades']:>8} {r['win_rate']:>7.1f}% {r['total_return']:>+9.2f}% ${r['final_capital']:>10,.2f}")
    
    # Best cheap stocks
    if cheap_stocks:
        logger.info("\n\nTop Cheap Stocks ($1,500 account, true 10% risk):")
        logger.info(f"{'Symbol':<8} {'Price':>8} {'Contract':>10} {'Trades':>8} {'Win%':>8} {'Return':>10} {'Final':>12}")
        logger.info("-" * 70)
        for symbol_data in cheap_stocks[:10]:
            symbol = symbol_data['symbol']
            result = run_backtest_with_stop([symbol], stock_stop_pct=None, time_stop_days=5, years=10, capital=1500)
            logger.info(f"{symbol:<8} ${symbol_data['price']:>7.2f} ${symbol_data['contract_cost']:>9.0f} {result['total_trades']:>8} {result['win_rate']:>7.1f}% {result['total_return']:>+9.2f}% ${result['final_capital']:>10,.2f}")
    
    logger.info("\n" + "="*80)


if __name__ == "__main__":
    main()
