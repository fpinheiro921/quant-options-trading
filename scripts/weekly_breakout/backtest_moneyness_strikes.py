"""
Backtest Weekly Breakout with Proper Black-Scholes Option Pricing
Test ATM, ITM (10%), and OTM (10%) strikes
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')
sys.path.insert(0, r'h:\QUANT TRADING\scripts')

import logging
import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime, timedelta
from pathlib import Path

from backtest_weekly_breakout import load_daily_data, resample_to_weekly, find_weekly_setups

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# BLACK-SCHOLES OPTION PRICING
# ============================================================================

def black_scholes_call(S, K, T, r, sigma):
    """
    Black-Scholes price for European call option.
    S: stock price
    K: strike price
    T: time to expiration in years
    r: risk-free rate
    sigma: implied volatility
    """
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return max(call_price, 0.01)


def calculate_greeks(S, K, T, r, sigma):
    """Calculate option Greeks."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    delta = norm.cdf(d1)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
    vega = S * norm.pdf(d1) * np.sqrt(T)
    
    return {'delta': delta, 'gamma': gamma, 'theta': theta / 365, 'vega': vega}


def estimate_historical_volatility(df, lookback=30):
    """Estimate annualized historical volatility from price data."""
    if len(df) < lookback:
        lookback = len(df)
    
    prices = df['close'].iloc[-lookback:]
    log_returns = np.log(prices / prices.shift(1)).dropna()
    
    if len(log_returns) < 5:
        return 0.30  # Default 30% if not enough data
    
    daily_vol = log_returns.std()
    annual_vol = daily_vol * np.sqrt(252)
    
    # Bound between 15% and 100%
    return max(0.15, min(annual_vol, 1.0))


def get_strike(stock_price, moneyness):
    """
    Get strike price based on moneyness.
    moneyness: 'ITM10' (10% ITM), 'ATM', 'OTM10' (10% OTM)
    """
    if moneyness == 'ITM10':
        return stock_price * 0.90
    elif moneyness == 'ATM':
        return stock_price
    elif moneyness == 'OTM10':
        return stock_price * 1.10
    else:
        return stock_price


def get_contract_premium(stock_price, strike, days_to_exp=30, vol=None, df=None):
    """Get proper option premium using Black-Scholes."""
    if vol is None and df is not None:
        vol = estimate_historical_volatility(df)
    elif vol is None:
        vol = 0.30
    
    T = days_to_exp / 365.0
    r = 0.045  # 4.5% risk-free rate
    
    premium = black_scholes_call(stock_price, strike, T, r, vol)
    return premium


def get_option_value_at_exit(entry_stock, exit_stock, strike, entry_premium, 
                              days_held, total_days=30, vol=None, df=None):
    """Re-price option at exit using Black-Scholes."""
    if vol is None and df is not None:
        vol = estimate_historical_volatility(df)
    elif vol is None:
        vol = 0.30
    
    days_remaining = max(0, total_days - days_held)
    T = days_remaining / 365.0
    r = 0.045
    
    exit_premium = black_scholes_call(exit_stock, strike, T, r, vol)
    
    # Hard floor and cap for realism
    max_value = entry_premium * 3.0
    exit_premium = min(exit_premium, max_value)
    exit_premium = max(exit_premium, 0.01)
    
    return exit_premium


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_backtest_symbol(symbol, moneyness='ATM', stock_stop_pct=-0.02, 
                        time_stop_days=5, years=10, capital=1500):
    """Run weekly breakout backtest for a single symbol with chosen strike."""
    df = load_daily_data(symbol, years=years)
    if df.empty:
        return [], capital, capital

    df_w = resample_to_weekly(df)
    if len(df_w) < 5:
        return [], capital, capital

    setups = find_weekly_setups(df_w)
    if not setups:
        return [], capital, capital

    # Estimate volatility once from full dataset
    base_vol = estimate_historical_volatility(df, lookback=60)
    
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
        
        # Get strike based on moneyness
        strike = get_strike(entry_stock, moneyness)
        
        time_stop_date = entry_date + timedelta(days=time_stop_days)
        
        # Get entry premium using Black-Scholes
        entry_premium = get_contract_premium(entry_stock, strike, 30, base_vol)
        
        # TRUE 10% risk
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
        
        # Re-price option at exit
        exit_premium = get_option_value_at_exit(
            entry_stock, exit_price, strike, entry_premium,
            days_held, 30, base_vol
        )
        
        pnl = (exit_premium - entry_premium) * contracts * 100

        # Calculate Greeks at entry for analysis
        greeks = calculate_greeks(entry_stock, strike, 30/365, 0.045, base_vol)

        trades.append({
            'symbol': symbol,
            'moneyness': moneyness,
            'strike': strike,
            'entry_date': entry_date,
            'exit_date': exit_date,
            'days_held': days_held,
            'entry_stock': entry_stock,
            'exit_stock': exit_price,
            'entry_premium': entry_premium,
            'exit_premium': exit_premium,
            'contracts': contracts,
            'cost': cost,
            'pnl': pnl,
            'pnl_pct': (pnl / cost) * 100,
            'stock_pct': ((exit_price - entry_stock) / entry_stock) * 100,
            'exit_reason': exit_reason,
            'delta': greeks['delta'],
            'theta': greeks['theta'],
            'iv': base_vol
        })

        current_capital += pnl
        next_available_date = time_stop_date + timedelta(days=1)

    return trades, total_capital, current_capital


def monte_carlo(trades, capital=1500, n=1000):
    np.random.seed(42)
    returns = []
    
    for _ in range(n):
        indices = np.random.choice(len(trades), size=len(trades), replace=True)
        sim = [trades[i] for i in indices]
        eq = capital
        for t in sim:
            eq += t['pnl']
        returns.append((eq - capital) / capital)
    
    return {
        'mean': np.mean(returns) * 100,
        'median': np.median(returns) * 100,
        'worst': np.percentile(returns, 5) * 100,
        'best': np.percentile(returns, 95) * 100,
        'prob': np.mean([r > 0 for r in returns]) * 100
    }


def generate_comparison_report(results, report_path):
    """Generate report comparing ATM, ITM, OTM for all symbols."""
    md = f"""# Moneyness Comparison: ATM vs ITM vs OTM

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Model:** Black-Scholes with Historical Volatility
**Strategy:** Weekly Breakout, -2% Stock Stop, 5-Day Time Stop
**Account:** $1,500

---

## Option Model Details

| Parameter | Value |
|-----------|-------|
| Pricing Model | Black-Scholes |
| Volatility | Historical (30-60 day lookback) |
| Risk-Free Rate | 4.5% |
| Days to Expiration | 30 |
| **ITM Strike** | 90% of stock price |
| **ATM Strike** | 100% of stock price |
| **OTM Strike** | 110% of stock price |

---

## Summary Results

| Symbol | Moneyness | Strike | Avg Delta | Trades | Win Rate | Total Return | Profit Factor | MC Prob |
|--------|-----------|--------|-----------|--------|----------|--------------|---------------|---------|
"""

    for symbol in sorted(results.keys()):
        for moneyness in ['ITM10', 'ATM', 'OTM10']:
            data = results[symbol][moneyness]
            trades = data['trades']
            if len(trades) == 0:
                md += f"| {symbol} | {moneyness} | - | - | 0 | - | - | - | - |\n"
                continue
            
            wins = sum(1 for t in trades if t['pnl'] > 0)
            wr = (wins / len(trades) * 100)
            pnl = sum(t['pnl'] for t in trades)
            ret = (pnl / 1500) * 100
            
            winning = [t['pnl'] for t in trades if t['pnl'] > 0]
            losing = [t['pnl'] for t in trades if t['pnl'] <= 0]
            gp = sum(winning) if winning else 0
            gl = abs(sum(losing)) if losing else 0
            pf = gp / gl if gl > 0 else 0
            
            avg_delta = np.mean([t['delta'] for t in trades])
            mc = data['mc']
            
            md += f"| {symbol} | {moneyness} | {get_strike(100, moneyness):.0f}% | {avg_delta:.2f} | {len(trades)} | {wr:.1f}% | {ret:+.1f}% | {pf:.2f} | {mc['prob']:.0f}% |\n"

    md += """
---

## Detailed Analysis by Symbol

"""

    for symbol in sorted(results.keys()):
        md += f"### {symbol}\n\n"
        
        for moneyness in ['ITM10', 'ATM', 'OTM10']:
            data = results[symbol][moneyness]
            trades = data['trades']
            if len(trades) == 0:
                md += f"**{moneyness}:** No trades\n\n"
                continue
            
            wins = sum(1 for t in trades if t['pnl'] > 0)
            wr = (wins / len(trades) * 100)
            pnl = sum(t['pnl'] for t in trades)
            ret = (pnl / 1500) * 100
            
            avg_premium = np.mean([t['entry_premium'] for t in trades])
            avg_delta = np.mean([t['delta'] for t in trades])
            avg_contract_cost = avg_premium * 100
            
            md += f"**{moneyness}:** Return {ret:+.1f}% | {len(trades)} trades | {wr:.1f}% WR | Avg Delta: {avg_delta:.2f} | Avg Contract: ${avg_contract_cost:.2f}\n\n"
        
        md += "\n---\n\n"

    md += """## Key Insights

### ITM (10% In-The-Money)
- **Higher delta** (~0.70-0.80): Moves more with stock
- **More expensive** contracts: Less leverage
- **Lower time decay risk**: More intrinsic value
- **Better for trending stocks**: Captures more of the move

### ATM (At-The-Money)
- **Delta ~0.50**: Balanced stock sensitivity
- **Moderate cost**: Good leverage
- **Higher theta decay**: Pure time value
- **Best risk/reward**: Balanced approach

### OTM (10% Out-of-The-Money)
- **Lower delta** (~0.30-0.40): Less stock sensitivity
- **Cheaper contracts**: More leverage
- **High time decay**: All time value
- **Need bigger moves**: Must hit +8% target to profit

---

## Conclusions

- **ITM** may perform better with the -2% stop (higher delta = more directional)
- **ATM** is the balanced baseline
- **OTM** may underperform due to theta decay on 5-day holds
- Results depend heavily on stock's realized volatility vs implied volatility

---
*Backtest with proper Black-Scholes pricing*
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)
    
    logger.info(f"\n✅ Report saved: {report_path}")


def main():
    logger.info("="*80)
    logger.info("BACKTEST: ATM vs ITM vs OTM with Black-Scholes Pricing")
    logger.info("="*80)

    symbols = ['AAPL', 'SNAP', 'CCL', 'AAL', 'M', 'FSLY']
    moneyness_levels = ['ITM10', 'ATM', 'OTM10']
    
    all_results = {}

    for symbol in symbols:
        logger.info(f"\n{'='*60}")
        logger.info(f"SYMBOL: {symbol}")
        logger.info(f"{'='*60}")
        
        all_results[symbol] = {}
        
        for moneyness in moneyness_levels:
            logger.info(f"\n  [{moneyness}]")
            trades, capital, final_capital = run_backtest_symbol(
                symbol, moneyness=moneyness, stock_stop_pct=-0.02,
                time_stop_days=5, years=10, capital=1500
            )
            
            logger.info(f"    Trades: {len(trades)} | Final: ${final_capital:,.2f}")
            
            if len(trades) > 0:
                mc = monte_carlo(trades, capital=capital)
                logger.info(f"    MC Mean: {mc['mean']:+.1f}% | Prob Profit: {mc['prob']:.1f}%")
            else:
                mc = {'mean': 0, 'median': 0, 'worst': 0, 'best': 0, 'prob': 0}
            
            all_results[symbol][moneyness] = {
                'trades': trades,
                'capital': capital,
                'final_capital': final_capital,
                'mc': mc
            }

    # Generate report
    logger.info("\n" + "="*80)
    logger.info("GENERATING COMPARISON REPORT")
    logger.info("="*80)
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(f'h:/QUANT TRADING/reports/weekly_breakout/MONEYNESS_COMPARISON_{ts}.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_comparison_report(all_results, report_path)

    # Print summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY - BEST MOneyNESS PER SYMBOL")
    logger.info("="*80)
    
    for symbol in symbols:
        best_return = -999999
        best_m = ''
        for moneyness in moneyness_levels:
            trades = all_results[symbol][moneyness]['trades']
            if len(trades) > 0:
                ret = (sum(t['pnl'] for t in trades) / 1500) * 100
                if ret > best_return:
                    best_return = ret
                    best_m = moneyness
        
        logger.info(f"{symbol}: Best = {best_m} ({best_return:+.1f}%)")
    
    logger.info("="*80)


if __name__ == "__main__":
    main()
