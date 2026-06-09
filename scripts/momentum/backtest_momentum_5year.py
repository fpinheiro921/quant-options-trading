"""
5-Year Momentum (Compra a Seco) Backtest

Runs Compra a Seco strategy independently on 2H charts.
Results will be combined with Wheel strategy results.
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np

from backtest.backtest_engine import MomentumBreakoutBacktester
from backtest.paper_trading import PaperTradingEnvironment, create_paper_environment
from api.alpaca_client import AlpacaClient
from config import Config
from models.technical_analysis import TechnicalAnalyzer, Candle

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_momentum_5year_backtest(symbol='NVDA', starting_capital=50000.0):
    """Run 5-year momentum backtest on 2H charts."""
    
    logger.info("=" * 80)
    logger.info(f"MOMENTUM (COMPRA A SECO) 5-YEAR BACKTEST - {symbol}")
    logger.info("=" * 80)
    
    client = AlpacaClient(Config.ALPACA_API_KEY, Config.ALPACA_API_SECRET, paper=True)
    client.authenticate()
    
    env = create_paper_environment(starting_capital)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1825)  # 5 years
    
    logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"Capital: ${starting_capital:,.2f}")
    
    # Fetch 2H data - use local cache if available
    logger.info(f"\nFetching 2H data for {symbol}...")
    
    try:
        # Try local cache first
        from pathlib import Path
        cache_path = Path(f'h:/QUANT TRADING/data/massive_cache/stocks/{symbol}/1h_2y.csv')
        
        if cache_path.exists():
            logger.info(f"  Loading from local cache: {cache_path}")
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            logger.info(f"  Loaded {len(df)} hourly candles from cache")
            
            # Resample to 2h (2 hour)
            df = df.resample('2h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            logger.info(f"  Resampled to {len(df)} 2H candles")
        else:
            # Fetch from API
            df = client.get_2h_candles(symbol, 2000)
            if df.empty:
                logger.error("No data returned")
                return None
            
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
        
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        logger.info(f"Total 2H candles: {len(df)}")
        if len(df) > 0:
            logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")
        else:
            logger.error("No data in date range")
            return None
        
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Convert to candles
    analyzer = TechnicalAnalyzer()
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
    
    logger.info(f"\nScanning for Compra a Seco setups...")
    setups = analyzer.find_compra_a_seco_setups(symbol, candles)
    logger.info(f"Found {len(setups)} setups")
    
    # Simulate trading on setups
    trades = []
    position = None
    capital = starting_capital
    
    for setup in setups:
        if position is not None:
            continue  # Wait for current position to close
        
        # Find entry candle (breakout)
        entry_idx = None
        for i, c in enumerate(candles):
            if c.timestamp > setup.detected_at and c.high > setup.breakout_price:
                entry_idx = i
                break
        
        if entry_idx is None:
            continue
        
        entry_candle = candles[entry_idx]
        entry_price = setup.entry_price
        
        # Position sizing (20% of capital)
        position_size = min(100, int((capital * 0.20) / entry_price))
        if position_size < 10:
            continue
        
        # Simulate trade
        capital -= entry_price * position_size
        
        # Find exit
        exit_price = None
        exit_reason = None
        
        for i in range(entry_idx + 1, min(entry_idx + setup.stop_time_bars + 1, len(candles))):
            c = candles[i]
            
            # Check target
            if c.high >= setup.target_price:
                exit_price = setup.target_price
                exit_reason = 'target'
                break
            
            # Check time stop
            if i >= entry_idx + setup.stop_time_bars:
                exit_price = c.close
                exit_reason = 'timeout'
                break
        
        if exit_price is None:
            # Use last available price
            exit_price = candles[min(entry_idx + setup.stop_time_bars, len(candles) - 1)].close
            exit_reason = 'end_of_data'
        
        # Close position
        capital += exit_price * position_size
        pnl = (exit_price - entry_price) * position_size
        
        trades.append({
            'entry_time': entry_candle.timestamp,
            'exit_time': candles[min(entry_idx + setup.stop_time_bars, len(candles) - 1)].timestamp,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'size': position_size,
            'pnl': pnl,
            'reason': exit_reason
        })
        
        logger.info(f"Trade: {entry_candle.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                   f"Entry: ${entry_price:.2f}, Exit: ${exit_price:.2f}, "
                   f"P&L: ${pnl:+.2f} ({exit_reason})")
    
    # Calculate results
    final_value = capital
    total_pnl = sum(t['pnl'] for t in trades)
    winning_trades = sum(1 for t in trades if t['pnl'] > 0)
    losing_trades = sum(1 for t in trades if t['pnl'] <= 0)
    
    logger.info("\n" + "=" * 80)
    logger.info("MOMENTUM BACKTEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Initial Capital: ${starting_capital:,.2f}")
    logger.info(f"Final Capital: ${final_value:,.2f}")
    logger.info(f"Total Return: {((final_value - starting_capital) / starting_capital * 100):+.2f}%")
    logger.info(f"Total Trades: {len(trades)}")
    logger.info(f"Winning: {winning_trades}, Losing: {losing_trades}")
    logger.info(f"Win Rate: {(winning_trades / len(trades) * 100) if trades else 0:.1f}%")
    logger.info(f"Total P&L: ${total_pnl:+.2f}")
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'momentum_{symbol}_5year_{timestamp}.md'
    
    md = f"""# Momentum (Compra a Seco) 5-Year Backtest Report

## Overview

**Strategy:** Compra a Seco (Momentum Breakout)
**Symbol:** {symbol}
**Period:** {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
**Initial Capital:** ${starting_capital:,.2f}

---

## Performance Summary

| Metric | Value |
|--------|-------|
| Final Capital | ${final_value:,.2f} |
| **Total Return** | **{((final_value - starting_capital) / starting_capital * 100):+.2f}%** |
| Total Trades | {len(trades)} |
| Winning Trades | {winning_trades} |
| Losing Trades | {losing_trades} |
| Win Rate | {(winning_trades / len(trades) * 100) if trades else 0:.1f}% |
| Total P&L | ${total_pnl:+.2f} |

---

## Trade List

| # | Entry | Exit | Entry $ | Exit $ | Size | P&L | Reason |
|---|-------|------|---------|--------|------|-----|--------|
"""
    
    for i, t in enumerate(trades, 1):
        md += f"| {i} | {t['entry_time'].strftime('%Y-%m-%d %H:%M')} | {t['exit_time'].strftime('%Y-%m-%d %H:%M')} | ${t['entry_price']:.2f} | ${t['exit_price']:.2f} | {t['size']} | ${t['pnl']:+.2f} | {t['reason']} |\n"
    
    md += f"""
---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Data source: 2-hour candles*
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    logger.info(f"\n✅ Report saved: {report_file}")
    
    client.close()
    
    return {
        'symbol': symbol,
        'initial_capital': starting_capital,
        'final_capital': final_value,
        'return_pct': ((final_value - starting_capital) / starting_capital) * 100,
        'trades': len(trades),
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'total_pnl': total_pnl,
        'trade_list': trades
    }


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'NVDA'
    run_momentum_5year_backtest(symbol)
