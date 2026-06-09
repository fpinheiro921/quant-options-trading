"""
Portfolio Momentum (Compra a Seco) Backtest - Fixed Real-Time Scanner

Properly scans all portfolio symbols for momentum patterns in real-time.
ONE position at a time - scan all, pick best setup.
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import pandas as pd
import numpy as np

from api.alpaca_client import AlpacaClient
from config import Config
from models.technical_analysis import TechnicalAnalyzer, Candle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Portfolio configurations (same as Wheel)
PORTFOLIOS = {
    'NASDAQ': [
        'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA',
        'NFLX', 'AMD', 'ADBE', 'CRM', 'CSCO', 'INTC',
        'PLTR', 'COIN', 'RBLX', 'SNOW', 'CRWD', 'QQQ', 'NVDA'
    ],
    'SP500': [
        'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'JPM', 'JNJ', 'V', 'PG', 'UNH',
        'HD', 'MA', 'BAC', 'ABBV', 'PFE', 'KO', 'PEP', 'WMT', 'DIS', 'SPY', 'XOM'
    ],
    'HIGH_VOL': [
        'TSLA', 'NVDA', 'PLTR', 'COIN', 'RBLX', 'SNOW', 'CRWD', 'AMD',
        'SHOP', 'UPST', 'SOFI', 'LCID', 'RIVN', 'GME', 'AMC', 'MRNA',
        'ARKK', 'TQQQ', 'NET', 'DKNG'
    ],
    'DIVIDEND': [
        'JNJ', 'PG', 'KO', 'PEP', 'WMT', 'MCD', 'TGT', 'COST', 'LOW', 'HD',
        'VZ', 'T', 'XOM', 'CVX', 'BMY', 'ABBV', 'MSFT', 'AAPL', 'CSCO', 'INTC'
    ],
    'SECTOR': [
        'NVDA', 'MSFT', 'AAPL', 'JPM', 'V', 'BLK', 'JNJ', 'UNH', 'ABBV',
        'AMZN', 'WMT', 'KO', 'XOM', 'CVX', 'CAT', 'GE', 'GOOGL', 'VZ', 'LIN', 'AMT'
    ],
    'SMALL_CAP': [
        'AVAV', 'DKNG', 'HOOD', 'AFRM', 'TOST', 'BILL', 'ASAN', 'MDB', 'TWLO',
        'OKTA', 'ZI', 'HUBS', 'FSLY', 'ESTC', 'SPLK', 'DOCU', 'PD', 'S', 'CYBR', 'IWM'
    ]
}


def load_cached_2h_data(symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
    """Load 2H data from local cache."""
    from pathlib import Path
    cache_path = Path(f'h:/QUANT TRADING/data/massive_cache/stocks/{symbol}/1h_2y.csv')
    
    if not cache_path.exists():
        return None
    
    try:
        df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        # Resample to 2h
        df = df.resample('2h').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        return df
    except Exception as e:
        logger.warning(f"Failed to load {symbol}: {e}")
        return None


def detect_pattern_realtime(candles: List[Candle], current_idx: int) -> Optional[Dict]:
    """
    Detect Compra a Seco pattern in real-time at current index.
    
    Looks for:
    1. Bull run (price above rising EMAs)
    2. Propulsion candle (large body)
    3. Pin bar next (small body, indecision)
    4. Current candle breaking above pin bar high
    
    Returns setup dict if pattern complete and breaking out now.
    """
    if current_idx < 10 or current_idx >= len(candles):
        return None
    
    # Need at least 3 candles: propulsion, pin bar, breakout
    if current_idx < 2:
        return None
    
    # Check recent candles for pattern
    # Look back up to 10 candles for the propulsion + pin bar sequence
    lookback_start = max(0, current_idx - 10)
    
    for i in range(lookback_start, current_idx - 1):
        # Candle i = potential propulsion
        # Candle i+1 = potential pin bar
        # Current candle = potential breakout
        
        propulsion = candles[i]
        pin_bar = candles[i + 1]
        breakout_candle = candles[current_idx]
        
        # Check 1: Propulsion candle (large body, > 1.5x average of last 20)
        recent_bodies = [c.body for c in candles[max(0, i-20):i]]
        if not recent_bodies:
            continue
        avg_body = sum(recent_bodies) / len(recent_bodies)
        
        if propulsion.body < avg_body * 1.5:
            continue
        
        # Check 2: Pin bar (small body, < 30% of range)
        if pin_bar.range == 0:
            continue
        pin_body_pct = pin_bar.body / pin_bar.range
        if pin_body_pct > 0.30:
            continue
        
        # Check 3: Bull run context (price generally rising)
        if current_idx >= 5:
            price_5_ago = candles[current_idx - 5].close
            if breakout_candle.close <= price_5_ago:
                continue  # Not in uptrend
        
        # Check 4: Breakout above pin bar high
        if breakout_candle.high > pin_bar.high:
            # Pattern confirmed! Calculate targets
            propulsion_amplitude = propulsion.range
            entry_price = pin_bar.high + 0.01
            target_price = entry_price + propulsion_amplitude
            
            return {
                'propulsion_idx': i,
                'pin_bar_idx': i + 1,
                'breakout_idx': current_idx,
                'propulsion_candle': propulsion,
                'pin_bar_candle': pin_bar,
                'entry_price': entry_price,
                'target_price': target_price,
                'propulsion_amplitude': propulsion_amplitude,
                'detected_at': breakout_candle.timestamp
            }
    
    return None


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """Calculate EMA for a list of prices."""
    if len(prices) < period:
        return None
    
    multiplier = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period  # SMA start
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    
    return ema


def run_momentum_portfolio_backtest(portfolio_name: str, symbols: List[str], starting_capital: float = 50000.0):
    """Run momentum strategy scanning all portfolio symbols in real-time."""
    
    logger.info("=" * 80)
    logger.info(f"PORTFOLIO MOMENTUM BACKTEST - {portfolio_name}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info("=" * 80)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years (cache limit)
    
    logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Capital: ${starting_capital:,.2f}")
    
    # Load data for all symbols
    logger.info("\nLoading 2H data for all symbols...")
    data = {}
    for symbol in symbols:
        df = load_cached_2h_data(symbol, start_date, end_date)
        if df is not None and len(df) > 100:
            data[symbol] = df
            logger.info(f"  {symbol}: {len(df)} 2H candles ({df.index[0].date()} to {df.index[-1].date()})")
        else:
            logger.warning(f"  {symbol}: No data available")
    
    if not data:
        logger.error("No data loaded for any symbol!")
        return None
    
    # Convert all data to candles
    symbol_candles = {}
    for symbol, df in data.items():
        candles = []
        for idx, row in df.iterrows():
            candles.append(Candle(
                timestamp=idx,
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            ))
        symbol_candles[symbol] = candles
    
    # Get all unique timestamps
    all_timestamps = set()
    for candles in symbol_candles.values():
        all_timestamps.update([c.timestamp for c in candles])
    all_timestamps = sorted(list(all_timestamps))
    
    logger.info(f"\nScanning {len(all_timestamps)} timestamps across {len(data)} symbols...")
    
    # Trading state
    capital = starting_capital
    position = None
    trades = []
    traded_patterns = set()  # Track (symbol, propulsion_idx, pin_bar_idx) to avoid duplicates
    
    # Scan through time
    for t_idx, ts in enumerate(all_timestamps):
        if t_idx % 500 == 0:
            logger.info(f"  Progress: {t_idx}/{len(all_timestamps)} ({t_idx/len(all_timestamps)*100:.1f}%)")
        
        # If we have a position, check for exit
        if position is not None:
            symbol = position['symbol']
            candles = symbol_candles[symbol]
            
            # Find current candle index
            current_idx = None
            for i, c in enumerate(candles):
                if c.timestamp == ts:
                    current_idx = i
                    break
            
            if current_idx is not None:
                current_price = candles[current_idx].close
                
                # Check exit conditions
                exit_reason = None
                exit_price = current_price
                
                if current_price >= position['target']:
                    exit_reason = 'target'
                    exit_price = position['target']
                elif (ts - position['entry_time']).total_seconds() / 3600 >= position['max_hours']:
                    exit_reason = 'timeout'
                
                if exit_reason:
                    pnl = (exit_price - position['entry_price']) * position['size']
                    capital += exit_price * position['size']
                    
                    trades.append({
                        'symbol': symbol,
                        'entry_time': position['entry_time'],
                        'exit_time': ts,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'size': position['size'],
                        'pnl': pnl,
                        'reason': exit_reason
                    })
                    
                    logger.info(f"EXIT {symbol}: ${exit_price:.2f} ({exit_reason}, P&L: ${pnl:+.2f}) - Capital: ${capital:.2f}")
                    position = None
        
        # If no position, scan for new setups
        if position is None:
            best_setup = None
            best_score = -1.0
            best_symbol = None
            
            for symbol, candles in symbol_candles.items():
                # Find current index
                current_idx = None
                for i, c in enumerate(candles):
                    if c.timestamp == ts:
                        current_idx = i
                        break
                
                if current_idx is None or current_idx < 20:
                    continue
                
                # Detect pattern in real-time
                setup = detect_pattern_realtime(candles, current_idx)
                
                if setup:
                    # Check if this pattern was already traded
                    pattern_key = (symbol, setup['propulsion_idx'], setup['pin_bar_idx'])
                    if pattern_key in traded_patterns:
                        continue
                    
                    # Score based on propulsion amplitude / price
                    score = setup['propulsion_amplitude'] / candles[current_idx].close
                    
                    if score > best_score:
                        best_score = score
                        best_setup = setup
                        best_symbol = symbol
            
            # Enter best setup
            if best_setup and best_symbol:
                entry_price = best_setup['entry_price']
                target_price = best_setup['target_price']
                
                # Mark pattern as traded
                pattern_key = (best_symbol, best_setup['propulsion_idx'], best_setup['pin_bar_idx'])
                traded_patterns.add(pattern_key)
                
                # Position sizing (20% of capital)
                position_size = min(100, int((capital * 0.20) / entry_price))
                if position_size >= 10:
                    capital -= entry_price * position_size
                    
                    position = {
                        'symbol': best_symbol,
                        'entry_price': entry_price,
                        'entry_time': ts,
                        'size': position_size,
                        'target': target_price,
                        'max_hours': 30  # ~5 days of 6-hour trading sessions
                    }
                    
                    logger.info(f"ENTRY {best_symbol}: ${entry_price:.2f} x {position_size} (target: ${target_price:.2f}) - Capital: ${capital:.2f}")
    
    # Close any open position at end
    if position is not None:
        symbol = position['symbol']
        candles = symbol_candles[symbol]
        final_price = candles[-1].close
        pnl = (final_price - position['entry_price']) * position['size']
        capital += final_price * position['size']
        
        trades.append({
            'symbol': symbol,
            'entry_time': position['entry_time'],
            'exit_time': candles[-1].timestamp,
            'entry_price': position['entry_price'],
            'exit_price': final_price,
            'size': position['size'],
            'pnl': pnl,
            'reason': 'end_of_test'
        })
        
        logger.info(f"CLOSE {symbol}: ${final_price:.2f} (end of test, P&L: ${pnl:+.2f})")
    
    # Calculate results
    final_value = capital
    total_pnl = sum(t['pnl'] for t in trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    losing_trades = sum(1 for t in trades if t['pnl'] <= 0)
    win_rate = (winning_trades / len(trades) * 100) if trades else 0
    symbols_traded = len(set(t['symbol'] for t in trades))
    
    logger.info("\n" + "=" * 80)
    logger.info("PORTFOLIO MOMENTUM BACKTEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Portfolio: {portfolio_name}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info(f"Symbols Traded: {symbols_traded}")
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
        'symbols_traded': symbols_traded,
        'trade_list': trades
    }


if __name__ == "__main__":
    # Run for all portfolios
    results = {}
    
    for name, symbols in PORTFOLIOS.items():
        try:
            result = run_momentum_portfolio_backtest(name, symbols)
            if result:
                results[name] = result
                
                # Save individual report
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_file = f'momentum_portfolio_{name}_{timestamp}.md'
                
                md = f"""# Momentum Portfolio Backtest Report - {name}

## Overview

**Portfolio:** {name}
**Symbols:** {', '.join(symbols)}
**Period:** 2 Years (Cached Data)
**Initial Capital:** ${result['initial']:,.2f}

---

## Performance Summary

| Metric | Value |
|--------|-------|
| Final Capital | ${result['final']:,.2f} |
| **Total Return** | **{result['return_pct']:+.2f}%** |
| Total Trades | {result['trades']} |
| Symbols Traded | {result['symbols_traded']} |
| Winning Trades | {result['winning']} |
| Losing Trades | {result['losing']} |
| Win Rate | {result['win_rate']:.1f}% |

---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Scanner: Real-time Compra a Seco pattern detection*
"""
                
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(md)
                
                logger.info(f"✅ Report saved: {report_file}")
        except Exception as e:
            logger.error(f"Failed to run {name}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("ALL PORTFOLIOS COMPLETE")
    logger.info("=" * 80)
    
    for name, result in results.items():
        logger.info(f"{name}: {result['return_pct']:+.2f}% ({result['trades']} trades, {result['symbols_traded']} symbols)")
