"""
WEEKLY BREAKOUT STRATEGY - NASDAQ Portfolio
Entry: Break above previous week's high
Exit: +8% stock move, -70% option value, or Thursday before expiration
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NASDAQ Portfolio (19 symbols)
NASDAQ_SYMBOLS = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'NFLX',
    'AMD', 'ADBE', 'CRM', 'CSCO', 'INTC', 'PLTR', 'COIN', 'RBLX',
    'SNOW', 'CRWD', 'QQQ'
]


def load_daily_data(symbol: str, years: int = 10) -> pd.DataFrame:
    """Load daily data for weekly analysis, filtered to last N years."""
    cache_path = Path(f'h:/QUANT TRADING/data/massive_cache/stocks/{symbol}/1d_5y.csv')
    if not cache_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    
    # Filter to last N years
    cutoff_date = datetime.now() - timedelta(days=years * 365)
    df = df[df.index >= cutoff_date]
    
    return df


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly."""
    if df.empty:
        return df
    weekly = df.resample('W-FRI').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    return weekly


def get_option_expiration(entry_date: datetime, dte: int = 30) -> datetime:
    """Get expiration date ~30 DTE."""
    return entry_date + timedelta(days=dte)


def estimate_atm_premium(stock_price: float, days_to_exp: int = 30) -> float:
    """Estimate 30DTE ATM call premium."""
    # 30DTE ATM call: ~4-5% of stock price
    base_premium = stock_price * 0.045
    return base_premium


def calculate_option_value(
    entry_stock: float,
    current_stock: float,
    entry_premium: float,
    days_remaining: int,
    total_days: int = 30
) -> float:
    """
    Estimate 30DTE option value realistically.
    
    - Intrinsic: max(0, current - strike)
    - Time decay: loses ~40% of value by expiration
    - Delta: ~0.50 for ATM
    - Gamma effect modest (not explosive like weekly)
    """
    strike = entry_stock  # ATM
    price_move_pct = (current_stock - entry_stock) / entry_stock
    
    # Intrinsic value
    intrinsic = max(0, current_stock - strike)
    
    # Time decay: 30DTE options lose value more slowly
    time_decay_factor = days_remaining / total_days
    
    # Initial time value (what we paid minus intrinsic at entry)
    initial_time_value = max(0, entry_premium)
    remaining_time_value = initial_time_value * time_decay_factor
    
    # For winning moves: realistic option gain
    # Stock +8% in a week on 30DTE ATM call -> option +40-60%
    # Stock +8% over 3 weeks -> option +20-30% (more theta decay)
    if price_move_pct > 0:
        # Winner: capture intrinsic + partial time value
        # Realistic: +8% stock = ~+50% option gain for short hold
        gain_multiplier = 1.0 + min(price_move_pct * 6.0, 1.5)  # Cap at +150%
        option_value = entry_premium * gain_multiplier
    else:
        # Loser: time decay + delta loss
        # If stock flat/down, lose to theta
        loss_factor = max(0.10, 1.0 + price_move_pct * 2.0)  # Floor at 10% of entry
        option_value = entry_premium * loss_factor * time_decay_factor
    
    # Ensure intrinsic is at least captured if ITM
    if intrinsic > 0:
        option_value = max(option_value, intrinsic * 0.5)  # Can exercise for some value
    
    # Hard caps
    max_value = entry_premium * 2.5  # Best case: 2.5x (not 4x)
    option_value = min(option_value, max_value)
    
    # Floor
    return max(option_value, 0.01)


def find_weekly_setups(df_weekly: pd.DataFrame) -> List[Dict]:
    """
    Find weekly breakout setups.
    Entry: Current week breaks above previous week's high.
    """
    setups = []
    
    if len(df_weekly) < 3:
        return setups
    
    for i in range(1, len(df_weekly)):
        prev_week = df_weekly.iloc[i - 1]
        curr_week = df_weekly.iloc[i]
        
        # Breakout: Current week opens or trades above previous week's high
        # Signal fires when high of current week exceeds previous week's high
        if curr_week['high'] > prev_week['high']:
            # Entry at break above previous week's high
            entry_price = prev_week['high'] + 0.01
            
            # Profit target: +8% from entry
            target_price = entry_price * 1.08
            
            # Stop: Option down 70% (we'll track this dynamically)
            
            setups.append({
                'week_date': df_weekly.index[i],
                'entry_price': entry_price,
                'prev_week_high': prev_week['high'],
                'curr_week_high': curr_week['high'],
                'target_price': target_price,
                'week_open': curr_week['open'],
                'week_close': curr_week['close']
            })
    
    return setups


def backtest_weekly_breakout(
    symbol: str,
    capital: float = 50000.0,
    risk_per_trade: float = 0.10
) -> Dict:
    """
    Run weekly breakout backtest for a single symbol.
    
    Entry: Break above previous week's high
    Buy ATM Call (30 DTE)
    Exit: Stock +8% OR Thursday of expiration week
    Risk: 10% of capital per trade
    """
    df = load_daily_data(symbol)
    if df.empty:
        return None
    
    df_weekly = resample_to_weekly(df)
    if len(df_weekly) < 5:
        return None
    
    setups = find_weekly_setups(df_weekly)
    
    if not setups:
        return None
    
    trades = []
    current_capital = capital
    
    for setup in setups:
        entry_date = setup['week_date']
        entry_stock = setup['entry_price']
        target = setup['target_price']
        
        # Get expiration (30 DTE)
        expiration = get_option_expiration(entry_date, dte=30)
        thursday_exit = expiration - timedelta(days=1)
        
        # Estimate option premium at entry (30 DTE)
        days_to_exp = (expiration - entry_date).days
        entry_premium = estimate_atm_premium(entry_stock, days_to_exp)
        
        # Position sizing: risk 10% of capital per trade
        max_risk = capital * risk_per_trade
        contracts = int(max_risk / (entry_premium * 100))
        if contracts < 1:
            contracts = 1
        
        cost = entry_premium * contracts * 100
        if cost > current_capital:
            continue
        
        # Simulate trade day by day using daily data
        trade_days = df.loc[entry_date:thursday_exit]
        
        if len(trade_days) < 1:
            continue
        
        exit_price = None
        exit_date = None
        exit_reason = None
        
        for date, row in trade_days.iterrows():
            daily_high = row['high']
            daily_low = row['low']
            
            # Check profit target: stock up 8%
            if daily_high >= target:
                exit_price = target
                exit_date = date
                exit_reason = 'PROFIT_TARGET'
                break
            
            # Check time stop: Thursday of expiration week
            if date >= thursday_exit:
                exit_price = row['close']
                exit_date = date
                exit_reason = 'TIME_STOP'
                break
        
        # If no exit triggered, use last available day
        if exit_price is None:
            last_day = trade_days.iloc[-1]
            exit_price = last_day['close']
            exit_date = trade_days.index[-1]
            exit_reason = 'TIME_STOP'
        
        # Calculate P&L
        days_held = (exit_date - entry_date).days
        final_premium = calculate_option_value(
            entry_stock, exit_price, entry_premium, 
            max(0, (expiration - exit_date).days), days_to_exp
        )
        
        pnl = (final_premium - entry_premium) * contracts * 100
        pnl_pct = (pnl / cost) * 100
        stock_pct = ((exit_price - entry_stock) / entry_stock) * 100
        
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
            'pnl_pct': pnl_pct,
            'stock_pct': stock_pct,
            'exit_reason': exit_reason
        })
        
        current_capital += pnl
    
    if not trades:
        return None
    
    total_pnl = sum(t['pnl'] for t in trades)
    winners = sum(1 for t in trades if t['pnl'] > 0)
    losers = len(trades) - winners
    win_rate = (winners / len(trades)) * 100
    
    avg_winner = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winners > 0 else 0
    avg_loser = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if losers > 0 else 0
    
    # Profit factor
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    final_capital = capital + total_pnl
    total_return = ((final_capital - capital) / capital) * 100
    
    # Exit reason breakdown
    profit_exits = sum(1 for t in trades if t['exit_reason'] == 'PROFIT_TARGET')
    stop_exits = sum(1 for t in trades if t['exit_reason'] == 'OPTION_STOP')
    time_exits = sum(1 for t in trades if t['exit_reason'] == 'TIME_STOP')
    
    return {
        'symbol': symbol,
        'trades': len(trades),
        'winners': winners,
        'losers': losers,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_return': total_return,
        'final_capital': final_capital,
        'avg_winner': avg_winner,
        'avg_loser': avg_loser,
        'profit_factor': profit_factor,
        'profit_exits': profit_exits,
        'stop_exits': stop_exits,
        'time_exits': time_exits,
        'trade_list': trades
    }


def run_portfolio_backtest(portfolio_name: str = 'NASDAQ', symbols: List[str] = None):
    """Run weekly breakout backtest with ONE open trade at a time across portfolio."""
    if symbols is None:
        symbols = NASDAQ_SYMBOLS
    
    logger.info(f"\n{'='*80}")
    logger.info(f"WEEKLY BREAKOUT BACKTEST: {portfolio_name}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Rule: ONE open trade at a time across entire portfolio")
    logger.info(f"Strategy: Break above prev week high, 30DTE ATM Call, +8% target OR 10-day exit")
    logger.info(f"Risk: 10% per trade | No option stop - 10d tight time stop")
    logger.info(f"{'='*80}\n")
    
    # Load all data first
    all_data = {}
    all_weekly = {}
    for symbol in symbols:
        df = load_daily_data(symbol)
        if not df.empty:
            df_w = resample_to_weekly(df)
            if len(df_w) >= 5:
                all_data[symbol] = df
                all_weekly[symbol] = df_w
    
    if not all_data:
        logger.warning("No data found for any symbols")
        return
    
    logger.info(f"Loaded data for {len(all_data)} symbols")
    
    # Build unified timeline of all weekly breakout setups across all symbols
    # Each entry: (week_date, symbol, setup_data)
    all_setups = []
    for symbol, df_w in all_weekly.items():
        setups = find_weekly_setups(df_w)
        for s in setups:
            all_setups.append({
                'week_date': s['week_date'],
                'symbol': symbol,
                'entry_price': s['entry_price'],
                'target_price': s['target_price'],
                'df': all_data[symbol]  # reference to daily data
            })
    
    # Sort chronologically
    all_setups.sort(key=lambda x: x['week_date'])
    logger.info(f"Total setups found across all symbols: {len(all_setups)}")
    
    # Run simulation with ONE position at a time
    total_capital = 50000.0
    current_capital = total_capital
    
    trades = []
    next_available_date = None  # Can't enter new trade before this date
    
    for setup in all_setups:
        entry_date = setup['week_date']
        
        # Skip if this setup occurs while we're still in a trade
        if next_available_date is not None and entry_date < next_available_date:
            continue
        
        symbol = setup['symbol']
        entry_stock = setup['entry_price']
        target = setup['target_price']
        df = setup['df']
        
        # Time stop: 5 days (minimum)
        time_stop_days = 5
        time_stop_date = entry_date + timedelta(days=time_stop_days)
        
        # Estimate option premium at entry (30 DTE)
        entry_premium = estimate_atm_premium(entry_stock, days_to_exp=30)
        
        # Position sizing: risk 10% of current capital
        max_risk = current_capital * 0.10
        contracts = int(max_risk / (entry_premium * 100))
        if contracts < 1:
            contracts = 1
        
        cost = entry_premium * contracts * 100
        if cost > current_capital:
            continue
        
        # Simulate trade day by day
        trade_days = df.loc[entry_date:time_stop_date]
        
        if len(trade_days) < 1:
            continue
        
        exit_price = None
        exit_date = None
        exit_reason = None
        
        for date, row in trade_days.iterrows():
            daily_high = row['high']
            daily_low = row['low']
            
            # Check profit target: stock up 8%
            if daily_high >= target:
                exit_price = target
                exit_date = date
                exit_reason = 'PROFIT_TARGET'
                break
            
            # Check time stop: 20 days (average to hit profit target)
            if date >= time_stop_date:
                exit_price = row['close']
                exit_date = date
                exit_reason = 'TIME_STOP'
                break
        
        # If no exit triggered, use last available day
        if exit_price is None:
            last_day = trade_days.iloc[-1]
            exit_price = last_day['close']
            exit_date = trade_days.index[-1]
            exit_reason = 'TIME_STOP'
        
        # Calculate P&L
        days_held = (exit_date - entry_date).days
        final_premium = calculate_option_value(
            entry_stock, exit_price, entry_premium, 
            max(0, (30 - days_held)), 30
        )
        
        pnl = (final_premium - entry_premium) * contracts * 100
        pnl_pct = (pnl / cost) * 100
        stock_pct = ((exit_price - entry_stock) / entry_stock) * 100
        
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
            'pnl_pct': pnl_pct,
            'stock_pct': stock_pct,
            'exit_reason': exit_reason
        })
        
        current_capital += pnl
        
        # Block new entries until this trade is closed
        next_available_date = time_stop_date + timedelta(days=1)
    
    if not trades:
        logger.warning("No trades executed")
        return
    
    # Calculate metrics
    total_trades = len(trades)
    total_winners = sum(1 for t in trades if t['pnl'] > 0)
    total_losers = total_trades - total_winners
    win_rate = (total_winners / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = sum(t['pnl'] for t in trades)
    final_capital = total_capital + total_pnl
    total_return = ((final_capital - total_capital) / total_capital) * 100
    
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    profit_exits = sum(1 for t in trades if t['exit_reason'] == 'PROFIT_TARGET')
    stop_exits = sum(1 for t in trades if t['exit_reason'] == 'OPTION_STOP')
    time_exits = sum(1 for t in trades if t['exit_reason'] == 'TIME_STOP')
    
    # Symbol breakdown
    symbol_stats = {}
    for t in trades:
        sym = t['symbol']
        if sym not in symbol_stats:
            symbol_stats[sym] = {'trades': 0, 'wins': 0, 'pnl': 0}
        symbol_stats[sym]['trades'] += 1
        symbol_stats[sym]['wins'] += 1 if t['pnl'] > 0 else 0
        symbol_stats[sym]['pnl'] += t['pnl']
    
    logger.info(f"\n{'='*80}")
    logger.info(f"PORTFOLIO SUMMARY: {portfolio_name} (ONE POSITION AT A TIME)")
    logger.info(f"{'='*80}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Winners: {total_winners} | Losers: {total_losers}")
    logger.info(f"Win Rate: {win_rate:.1f}%")
    logger.info(f"Total Return: {total_return:+.2f}%")
    logger.info(f"Profit Factor: {profit_factor:.2f}")
    logger.info(f"Final Capital: ${final_capital:,.2f}")
    logger.info(f"Exit Breakdown: Profit={profit_exits}, Stop={stop_exits}, Time={time_exits}")
    logger.info(f"{'='*80}")
    
    # Generate report
    generate_report_v2(trades, symbol_stats, portfolio_name, total_capital, final_capital, 
                        total_trades, total_winners, total_losers, win_rate, 
                        total_return, profit_factor, profit_exits, stop_exits, time_exits)


def generate_report_v2(trades, symbol_stats, portfolio_name, initial, final, total_trades, 
                       wins, losses, win_rate, total_return, pf, profit_exits, stop_exits, time_exits):
    """Generate Markdown report for unified portfolio backtest."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(f'h:/QUANT TRADING/reports/NASDAQ/WEEKLY_BREAKOUT_{portfolio_name}_{timestamp}.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    md = f"""# Weekly Breakout Strategy - {portfolio_name} Backtest
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
| **Initial Capital** | ${initial:,.2f} |

## Performance Summary

| Metric | Value |
|--------|-------|
| **Total Return** | **{total_return:+.2f}%** |
| Final Capital | ${final:,.2f} |
| Total Trades | {total_trades} |
| Winners | {wins} |
| Losers | {losses} |
| Win Rate | {win_rate:.1f}% |
| Profit Factor | {pf:.2f} |

## Exit Analysis

| Exit Type | Count | Percentage |
|-----------|-------|------------|
| Profit Target (+8%) | {profit_exits} | {(profit_exits/total_trades*100) if total_trades > 0 else 0:.1f}% |
| Option Stop (-70%) | {stop_exits} | {(stop_exits/total_trades*100) if total_trades > 0 else 0:.1f}% |
| Time Stop (Thursday) | {time_exits} | {(time_exits/total_trades*100) if total_trades > 0 else 0:.1f}% |

## Symbol Breakdown (All {len(NASDAQ_SYMBOLS)} NASDAQ Symbols)

| Symbol | Trades | Win Rate | Avg P&L/Trade | Total P&L |
|--------|--------|----------|---------------|-----------|
"""
    
    # Show all symbols, even those with no trades
    for sym in NASDAQ_SYMBOLS:
        if sym in symbol_stats:
            data = symbol_stats[sym]
            wr = (data['wins'] / data['trades'] * 100) if data['trades'] > 0 else 0
            avg_pnl = data['pnl'] / data['trades'] if data['trades'] > 0 else 0
            md += f"| {sym} | {data['trades']} | {wr:.1f}% | ${avg_pnl:,.2f} | ${data['pnl']:,.2f} |\n"
        else:
            md += f"| {sym} | 0 | - | - | Skipped (one-at-a-time) |\n"
    
    md += f"""
## Recent Trades

| Symbol | Entry | Exit | Days | Stock % | P&L | Reason |
|--------|-------|------|------|---------|-----|--------|
"""
    
    # Show first 15 trades
    for t in trades[:15]:
        md += (f"| {t['symbol']} | ${t['entry_stock']:.2f} | ${t['exit_stock']:.2f} | "
               f"{t['days_held']}d | {t['stock_pct']:+.1f}% | ${t['pnl']:,.2f} | {t['exit_reason']} |\n")
    
    md += f"""
---
*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Strategy: Weekly Breakout + ATM Call*
*Rule: ONE open position at a time across portfolio*
"""
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    logger.info(f"\n✅ Report saved: {report_path}")


if __name__ == "__main__":
    # FULL NASDAQ - Weekly Breakout Strategy with 5-day time stop
    run_portfolio_backtest(portfolio_name='NASDAQ', symbols=NASDAQ_SYMBOLS)
