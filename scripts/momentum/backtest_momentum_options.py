"""
Momentum (Compra a Seco) Options Backtest - Fixed Real-Time Scanner

Uses CALL OPTIONS instead of stocks:
- Entry: Buy ATM Call (30 DTE) when breakout detected
- Stop: Sell if stock hits propulsion candle low
- Target: Sell if stock hits 2x risk (2x propulsion amplitude)
- Time Stop: Sell on Thursday of expiration week
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
import logging
import pandas as pd
import numpy as np

from models.technical_analysis import Candle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


PORTFOLIOS = {
    'NASDAQ': ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA', 'NFLX', 'AMD', 'ADBE', 'CRM', 'CSCO', 'INTC', 'PLTR', 'COIN', 'RBLX', 'SNOW', 'CRWD', 'QQQ', 'NVDA'],
    'SP500': ['AAPL', 'MSFT', 'AMZN', 'GOOGL', 'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'BAC', 'ABBV', 'PFE', 'KO', 'PEP', 'WMT', 'DIS', 'SPY', 'XOM'],
    'HIGH_VOL': ['TSLA', 'NVDA', 'PLTR', 'COIN', 'RBLX', 'SNOW', 'CRWD', 'AMD', 'SQ', 'SHOP', 'UPST', 'SOFI', 'LCID', 'RIVN', 'GME', 'AMC', 'MRNA', 'ARKK', 'TQQQ', 'NET'],
    'DIVIDEND': ['JNJ', 'PG', 'KO', 'PEP', 'WMT', 'MCD', 'TGT', 'COST', 'LOW', 'HD', 'VZ', 'T', 'XOM', 'CVX', 'BMY', 'ABBV', 'MSFT', 'AAPL', 'CSCO', 'INTC'],
    'SECTOR': ['NVDA', 'MSFT', 'AAPL', 'JPM', 'V', 'BLK', 'JNJ', 'UNH', 'ABBV', 'AMZN', 'WMT', 'KO', 'XOM', 'CVX', 'CAT', 'GE', 'GOOGL', 'VZ', 'LIN', 'AMT'],
    'SMALL_CAP': ['AVAV', 'DKNG', 'HOOD', 'AFRM', 'TOST', 'BILL', 'ASAN', 'MDB', 'TWLO', 'OKTA', 'ZI', 'HUBS', 'FSLY', 'ESTC', 'SPLK', 'DOCU', 'PD', 'S', 'CYBR', 'IWM']
}


def load_cached_2h_data(symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
    from pathlib import Path
    cache_path = Path(f'h:/QUANT TRADING/data/massive_cache/stocks/{symbol}/1h_2y.csv')
    if not cache_path.exists():
        return None
    try:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df.resample('2h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        return df
    except Exception as e:
        logger.warning(f"Failed to load {symbol}: {e}")
        return None


def estimate_option_value(stock_entry: float, stock_current: float, days_remaining: int, is_call: bool = True) -> float:
    """
    Estimate option value using delta approximation.
    
    ATM Call:
    - Entry: ~4% of stock price (time value)
    - If stock up $1: option +$0.50 (delta)
    - If stock down $1: option -$0.50
    - Time decay: loses ~10% per week
    """
    # Base entry premium for ATM call (~4% of stock price)
    entry_premium = stock_entry * 0.04
    
    # Intrinsic value
    intrinsic = max(0, stock_current - stock_entry) if is_call else max(0, stock_entry - stock_current)
    
    # Delta effect: ATM call delta ≈ 0.5
    delta = 0.50
    price_move = stock_current - stock_entry
    delta_pnl = price_move * delta
    
    # Time decay (theta): loses ~30% of time value by expiration
    # Linear decay for simplicity
    time_decay_pct = 1.0 - (days_remaining / 30) * 0.30
    time_value = max(0, (entry_premium - intrinsic) * time_decay_pct) if intrinsic > 0 else entry_premium * time_decay_pct
    
    # Final value
    option_value = intrinsic + max(0, time_value + delta_pnl * 0.5)
    
    # Floor at $0.05 (options rarely go to absolute zero)
    return max(option_value, 0.05)


def get_expiration_thursday(entry_date: datetime) -> datetime:
    """Get the Thursday of expiration week (3rd Friday - 1 day)."""
    # Find 3rd Friday of the month ~30 days out
    target_month = entry_date.month + 1 if entry_date.day > 15 else entry_date.month
    target_year = entry_date.year
    if target_month > 12:
        target_month = 1
        target_year += 1
    
    # Find 3rd Friday
    first_day = datetime(target_year, target_month, 1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
    third_friday = first_friday + timedelta(days=14)
    
    # Thursday before expiration
    return third_friday - timedelta(days=1)


def detect_pattern_realtime(candles: List[Candle], current_idx: int) -> Optional[Dict]:
    if current_idx < 10 or current_idx >= len(candles) or current_idx < 2:
        return None
    
    lookback_start = max(0, current_idx - 10)
    
    for i in range(lookback_start, current_idx - 1):
        propulsion = candles[i]
        pin_bar = candles[i + 1]
        breakout_candle = candles[current_idx]
        
        recent_bodies = [c.body for c in candles[max(0, i-20):i]]
        if not recent_bodies:
            continue
        avg_body = sum(recent_bodies) / len(recent_bodies)
        
        # Check: Propulsion candle must be strongly bullish (close near high)
        if propulsion.range == 0:
            continue
        propulsion_bullishness = (propulsion.close - propulsion.open) / propulsion.range
        if propulsion_bullishness < 0.70:  # Must be at least 70% bullish
            continue
        
        if propulsion.body < avg_body * 1.5:
            continue
        
        if pin_bar.range == 0:
            continue
        pin_body_pct = pin_bar.body / pin_bar.range
        if pin_body_pct > 0.30:
            continue
        
        if current_idx >= 5:
            price_5_ago = candles[current_idx - 5].close
            if breakout_candle.close <= price_5_ago:
                continue
        
        if breakout_candle.high > pin_bar.high:
            propulsion_amplitude = propulsion.range
            entry_price = pin_bar.high + 0.01
            target_price = entry_price + (propulsion_amplitude * 2)  # 2x risk
            # Looser stop: use pin bar low instead of propulsion low
            stop_price = pin_bar.low - 0.01  # Pin bar low minus 1 cent
            
            return {
                'propulsion_idx': i,
                'pin_bar_idx': i + 1,
                'breakout_idx': current_idx,
                'propulsion_candle': propulsion,
                'pin_bar_candle': pin_bar,
                'entry_price': entry_price,
                'target_price': target_price,
                'stop_price': stop_price,
                'propulsion_amplitude': propulsion_amplitude,
                'detected_at': breakout_candle.timestamp
            }
    return None


def run_momentum_options_backtest(portfolio_name: str, symbols: List[str], starting_capital: float = 50000.0):
    logger.info("=" * 80)
    logger.info(f"OPTIONS MOMENTUM BACKTEST - {portfolio_name}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info("=" * 80)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Capital: ${starting_capital:,.2f}")
    
    logger.info("\nLoading 2H data for all symbols...")
    data = {}
    for symbol in symbols:
        df = load_cached_2h_data(symbol, start_date, end_date)
        if df is not None and len(df) > 100:
            data[symbol] = df
            logger.info(f"  {symbol}: {len(df)} 2H candles")
        else:
            logger.warning(f"  {symbol}: No data")
    
    if not data:
        logger.error("No data loaded!")
        return None
    
    symbol_candles = {}
    for symbol, df in data.items():
        candles = []
        for idx, row in df.iterrows():
            candles.append(Candle(timestamp=idx, open=row['open'], high=row['high'], low=row['low'], close=row['close'], volume=row['volume']))
        symbol_candles[symbol] = candles
    
    all_timestamps = set()
    for candles in symbol_candles.values():
        all_timestamps.update([c.timestamp for c in candles])
    all_timestamps = sorted(list(all_timestamps))
    
    logger.info(f"\nScanning {len(all_timestamps)} timestamps...")
    
    capital = starting_capital
    position = None
    trades = []
    traded_patterns = set()
    
    for t_idx, ts in enumerate(all_timestamps):
        if t_idx % 500 == 0:
            logger.info(f"  Progress: {t_idx}/{len(all_timestamps)} ({t_idx/len(all_timestamps)*100:.1f}%)")
        
        # Check existing position
        if position is not None:
            symbol = position['symbol']
            candles = symbol_candles[symbol]
            current_idx = None
            for i, c in enumerate(candles):
                if c.timestamp == ts:
                    current_idx = i
                    break
            
            if current_idx is not None:
                current_price = candles[current_idx].close
                current_low = candles[current_idx].low
                
                exit_reason = None
                exit_price = current_price
                
                # Check stop loss: stock hits propulsion candle low
                if current_low <= position['stop_price']:
                    exit_reason = 'stop_loss'
                    exit_price = position['stop_price']
                # Check target: 2x propulsion amplitude
                elif current_price >= position['target']:
                    exit_reason = 'target'
                    exit_price = position['target']
                # Check time stop: Thursday of expiration week
                elif ts.date() >= position['expiration_thursday'].date():
                    exit_reason = 'expiration'
                    exit_price = current_price
                
                if exit_reason:
                    # Sell the call option - calculate realistic value
                    days_held = max(1, (ts - position['entry_time']).days)
                    days_remaining = max(1, 30 - days_held)
                    option_value = estimate_option_value(position['entry_stock_price'], exit_price, days_remaining)
                    pnl = (option_value - position['entry_premium']) * position['contracts'] * 100
                    capital += option_value * position['contracts'] * 100
                    
                    trades.append({
                        'symbol': symbol,
                        'entry_time': position['entry_time'],
                        'exit_time': ts,
                        'entry_stock': position['entry_stock_price'],
                        'exit_stock': exit_price,
                        'entry_premium': position['entry_premium'],
                        'exit_premium': option_value,
                        'contracts': position['contracts'],
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    
                    logger.info(f"EXIT {symbol}: Stock ${exit_price:.2f} ({exit_reason}, Option P&L: ${pnl:+.2f}) - Capital: ${capital:.2f}")
                    position = None
        
        # Look for new setups
        if position is None:
            best_setup = None
            best_score = -1.0
            best_symbol = None
            
            for symbol, candles in symbol_candles.items():
                current_idx = None
                for i, c in enumerate(candles):
                    if c.timestamp == ts:
                        current_idx = i
                        break
                
                if current_idx is None or current_idx < 20:
                    continue
                
                setup = detect_pattern_realtime(candles, current_idx)
                
                if setup:
                    pattern_key = (symbol, setup['propulsion_idx'], setup['pin_bar_idx'])
                    if pattern_key in traded_patterns:
                        continue
                    
                    score = setup['propulsion_amplitude'] / candles[current_idx].close
                    if score > best_score:
                        best_score = score
                        best_setup = setup
                        best_symbol = symbol
            
            if best_setup and best_symbol:
                stock_price = best_setup['entry_price']
                
                # Buy ATM Call (30 DTE)
                option_premium = estimate_option_value(stock_price, stock_price, 30)  # Entry value
                expiration_thursday = get_expiration_thursday(ts)
                
                # Position sizing: Fixed risk per trade (2% of initial capital = $1,000)
                # Risk = premium paid (max loss on long call)
                risk_per_trade = starting_capital * 0.02  # $1,000 fixed risk
                contracts = int(risk_per_trade / (option_premium * 100))
                if contracts < 1:
                    contracts = 1
                
                cost = option_premium * contracts * 100
                if cost > capital:  # Can't spend more than available
                    continue
                
                capital -= cost
                
                position = {
                    'symbol': best_symbol,
                    'entry_stock_price': stock_price,
                    'entry_premium': option_premium,
                    'entry_time': ts,
                    'contracts': contracts,
                    'target': best_setup['target_price'],
                    'stop_price': best_setup['stop_price'],
                    'expiration_thursday': expiration_thursday
                }
                
                pattern_key = (best_symbol, best_setup['propulsion_idx'], best_setup['pin_bar_idx'])
                traded_patterns.add(pattern_key)
                
                logger.info(f"BUY CALL {best_symbol}: Stock ${stock_price:.2f}, Premium ${option_premium:.2f} x {contracts} contracts, Target: ${best_setup['target_price']:.2f}, Stop: ${best_setup['stop_price']:.2f}, Exp: {expiration_thursday.date()} - Capital: ${capital:.2f}")
    
    # Close any open position
    if position is not None:
        symbol = position['symbol']
        candles = symbol_candles[symbol]
        final_price = candles[-1].close
        days_held = max(1, (candles[-1].timestamp - position['entry_time']).days)
        days_remaining = max(1, 30 - days_held)
        option_value = estimate_option_value(position['entry_stock_price'], final_price, days_remaining)
        pnl = (option_value - position['entry_premium']) * position['contracts'] * 100
        capital += option_value * position['contracts'] * 100
        
        trades.append({
            'symbol': symbol,
            'entry_time': position['entry_time'],
            'exit_time': candles[-1].timestamp,
            'entry_stock': position['entry_stock_price'],
            'exit_stock': final_price,
            'entry_premium': position['entry_premium'],
            'exit_premium': option_value,
            'contracts': position['contracts'],
            'pnl': pnl,
            'reason': 'end_of_test'
        })
    
    final_value = capital
    total_pnl = sum(t['pnl'] for t in trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    losing_trades = sum(1 for t in trades if t['pnl'] <= 0)
    win_rate = (winning_trades / len(trades) * 100) if trades else 0
    symbols_traded = len(set(t['symbol'] for t in trades))
    
    logger.info("\n" + "=" * 80)
    logger.info("OPTIONS MOMENTUM BACKTEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Portfolio: {portfolio_name}")
    logger.info(f"Initial Capital: ${starting_capital:,.2f}")
    logger.info(f"Final Capital: ${final_value:,.2f}")
    logger.info(f"Total Return: {((final_value - starting_capital) / starting_capital * 100):+.2f}%")
    logger.info(f"Total Trades: {len(trades)}")
    logger.info(f"Winning: {winning_trades}, Losing: {losing_trades}")
    logger.info(f"Win Rate: {win_rate:.1f}%")
    logger.info(f"Total P&L: ${total_pnl:+.2f}")
    
    return {
        'portfolio': portfolio_name,
        'initial': starting_capital,
        'final': final_value,
        'return_pct': ((final_value - starting_capital) / starting_capital) * 100,
        'trades': len(trades),
        'winning': winning_trades,
        'losing': losing_trades,
        'win_rate': win_rate,
        'symbols_traded': symbols_traded
    }


if __name__ == "__main__":
    results = {}
    for name, symbols in PORTFOLIOS.items():
        try:
            result = run_momentum_options_backtest(name, symbols)
            if result:
                results[name] = result
        except Exception as e:
            logger.error(f"Failed {name}: {e}")
    
    logger.info("\n" + "=" * 80)
    logger.info("ALL PORTFOLIOS COMPLETE")
    logger.info("=" * 80)
    for name, result in results.items():
        logger.info(f"{name}: {result['return_pct']:+.2f}% ({result['trades']} trades)")
