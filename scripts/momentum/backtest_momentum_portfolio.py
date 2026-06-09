"""
Portfolio Momentum (Compra a Seco) Backtest

Runs Compra a Seco strategy on ALL symbols in a portfolio.
ONE position at a time - scan all, pick best setup.

Period: 5 years
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
from models.technical_analysis import TechnicalAnalyzer, Candle, CompraASecoSetup

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
        'SQ', 'SHOP', 'UPST', 'SOFI', 'LCID', 'RIVN', 'GME', 'AMC', 'MRNA',
        'ARKK', 'TQQQ', 'NET'
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


def run_momentum_portfolio_backtest(portfolio_name: str, symbols: List[str], starting_capital: float = 50000.0):
    """Run momentum strategy scanning all portfolio symbols."""
    
    logger.info("=" * 80)
    logger.info(f"PORTFOLIO MOMENTUM BACKTEST - {portfolio_name}")
    logger.info(f"Symbols: {len(symbols)}")
    logger.info("=" * 80)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1825)  # 5 years
    
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
    
    # Setup analyzer
    analyzer = TechnicalAnalyzer()
    
    # Trading state
    capital = starting_capital
    position = None  # Current trade
    trades = []
    
    # Get all unique timestamps across all symbols
    all_timestamps = set()
    for df in data.values():
        all_timestamps.update(df.index.tolist())
    all_timestamps = sorted(list(all_timestamps))
    
    logger.info(f"\nScanning {len(all_timestamps)} timestamps for setups...")
    
    # Scan through time
    for i, ts in enumerate(all_timestamps):
        if i % 1000 == 0:
            logger.info(f"  Progress: {i}/{len(all_timestamps)} timestamps ({i/len(all_timestamps)*100:.1f}%)")
        
        # If we have a position, check for exit
        if position is not None:
            symbol = position['symbol']
            if symbol in data:
                df = data[symbol]
                idx = df.index.get_indexer([ts], method='nearest')[0]
                if idx >= 0 and idx < len(df):
                    current_price = df.iloc[idx]['close']
                    
                    # Check exit conditions
                    exit_reason = None
                    if current_price >= position['target']:
                        exit_reason = 'target'
                        exit_price = position['target']
                    elif (ts - position['entry_time']).total_seconds() / 3600 >= position['max_hours']:
                        exit_reason = 'timeout'
                        exit_price = current_price
                    
                    if exit_reason:
                        # Close position
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
                        
                        logger.info(f"EXIT {symbol}: ${exit_price:.2f} ({exit_reason}, P&L: ${pnl:+.2f})")
                        position = None
        
        # If no position, scan for new setups
        if position is None:
            best_setup = None
            best_score = -1.0
            best_symbol = None
            
            for symbol, df in data.items():
                # Get recent candles up to current timestamp
                recent_df = df[df.index <= ts].tail(100)
                if len(recent_df) < 90:
                    continue
                
                # Convert to candles
                candles = []
                for idx, row in recent_df.iterrows():
                    candles.append(Candle(
                        timestamp=idx,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    ))
                
                # Find setups
                setups = analyzer.find_compra_a_seco_setups(symbol, candles)
                
                for setup in setups:
                    if abs((setup.detected_at - ts).total_seconds()) < 7200:  # Within 2 hours
                        # Calculate score based on setup quality
                        score = setup.propulsion_amplitude / recent_df['close'].iloc[-1]
                        
                        if score > best_score:
                            best_score = score
                            best_setup = setup
                            best_symbol = symbol
            
            # Enter best setup
            if best_setup and best_symbol:
                symbol = best_symbol
                df = data[symbol]
                idx = df.index.get_indexer([ts], method='nearest')[0]
                if idx >= 0 and idx < len(df):
                    current_price = df.iloc[idx]['close']
                    
                    # Check if we can afford
                    position_size = min(100, int((capital * 0.20) / current_price))
                    if position_size >= 10:
                        capital -= current_price * position_size
                        
                        position = {
                            'symbol': symbol,
                            'entry_price': current_price,
                            'entry_time': ts,
                            'size': position_size,
                            'target': best_setup.target_price,
                            'max_hours': best_setup.stop_time_bars * 2  # 2 hours per bar
                        }
                        
                        logger.info(f"ENTRY {symbol}: ${current_price:.2f} x {position_size} (target: ${best_setup.target_price:.2f})")
    
    # Close any open position at end
    if position is not None:
        symbol = position['symbol']
        if symbol in data:
            df = data[symbol]
            final_price = df.iloc[-1]['close']
            pnl = (final_price - position['entry_price']) * position['size']
            capital += final_price * position['size']
            
            trades.append({
                'symbol': symbol,
                'entry_time': position['entry_time'],
                'exit_time': df.index[-1],
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
    
    # Count unique symbols traded
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
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'momentum_portfolio_{portfolio_name}_{timestamp}.md'
    
    md = f"""# Portfolio Momentum (Compra a Seco) Backtest Report

## Overview

**Portfolio:** {portfolio_name}
**Symbols:** {', '.join(symbols)}
**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
**Initial Capital:** ${starting_capital:,.2f}

---

## Performance Summary

| Metric | Value |
|--------|-------|
| Final Capital | ${final_value:,.2f} |
| **Total Return** | **{((final_value - starting_capital) / starting_capital * 100):+.2f}%** |
| Total Trades | {len(trades)} |
| Symbols Traded | {symbols_traded} |
| Winning Trades | {winning_trades} |
| Losing Trades | {losing_trades} |
| Win Rate | {win_rate:.1f}% |
| Total P&L | ${total_pnl:+.2f} |

---

## Trade List

| # | Symbol | Entry | Exit | Entry $ | Exit $ | Size | P&L | Reason |
|---|--------|-------|------|---------|--------|------|-----|--------|
"""
    
    for i, t in enumerate(trades, 1):
        md += f"| {i} | {t['symbol']} | {t['entry_time'].strftime('%Y-%m-%d %H:%M')} | {t['exit_time'].strftime('%Y-%m-%d %H:%M')} | ${t['entry_price']:.2f} | ${t['exit_price']:.2f} | {t['size']} | ${t['pnl']:+.2f} | {t['reason']} |\n"
    
    md += f"""
---

## Setup Detection

- **Pattern:** Propulsion candle + Pin Bar + Breakout
- **EMA:** 8/80 divergence confirmation
- **Entry:** Above pin bar high
- **Target:** 1:1 risk/reward (propulsion amplitude)
- **Exit:** Target hit, timeout, or end of test
- **Position Size:** 20% of capital max

---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Data source: 2-hour cached candles*
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    logger.info(f"\n✅ Report saved: {report_file}")
    
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
    # Run for all portfolios
    results = {}
    
    for name, symbols in PORTFOLIOS.items():
        try:
            result = run_momentum_portfolio_backtest(name, symbols)
            if result:
                results[name] = result
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
