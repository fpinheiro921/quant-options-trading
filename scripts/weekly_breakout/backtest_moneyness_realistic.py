"""
Realistic Backtest: ATM vs ITM vs OTM with Fixed 1 Contract
Uses actual Black-Scholes pricing
Skips trade if contract cost exceeds account balance
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


def black_scholes_call(S, K, T, r, sigma):
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return max(call_price, 0.01)


def estimate_historical_volatility(df, lookback=60):
    if len(df) < lookback:
        lookback = len(df)
    prices = df['close'].iloc[-lookback:]
    log_returns = np.log(prices / prices.shift(1)).dropna()
    if len(log_returns) < 5:
        return 0.30
    daily_vol = log_returns.std()
    annual_vol = daily_vol * np.sqrt(252)
    return max(0.15, min(annual_vol, 1.0))


def run_backtest_fixed(symbol, moneyness='ATM', stock_stop_pct=-0.02,
                       time_stop_days=5, years=10, capital=1500):
    """Run backtest with FIXED 1 contract per trade (realistic retail sizing)."""
    df = load_daily_data(symbol, years=years)
    if df.empty:
        return [], capital, capital

    df_w = resample_to_weekly(df)
    if len(df_w) < 5:
        return [], capital, capital

    setups = find_weekly_setups(df_w)
    if not setups:
        return [], capital, capital

    base_vol = estimate_historical_volatility(df, 60)
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

        # Get strike
        if moneyness == 'ITM10':
            strike = entry_stock * 0.90
        elif moneyness == 'OTM10':
            strike = entry_stock * 1.10
        else:
            strike = entry_stock

        time_stop_date = entry_date + timedelta(days=time_stop_days)

        # Black-Scholes pricing
        T = 30 / 365.0
        r = 0.045
        entry_premium = black_scholes_call(entry_stock, strike, T, r, base_vol)
        contract_cost = entry_premium * 100

        # REALISTIC: Skip if can't afford 1 contract
        if contract_cost > current_capital:
            continue

        # FIXED: 1 contract only
        contracts = 1
        cost = contract_cost

        # REAL RISK: cost as % of account
        risk_pct = (cost / current_capital) * 100

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
        days_remaining = max(0, 30 - days_held)
        T_exit = days_remaining / 365.0
        exit_premium = black_scholes_call(exit_price, strike, T_exit, r, base_vol)
        exit_premium = max(exit_premium, 0.01)

        pnl = (exit_premium - entry_premium) * contracts * 100

        # Delta at entry
        d1 = (np.log(entry_stock / strike) + (r + 0.5 * base_vol**2) * T) / (base_vol * np.sqrt(T))
        delta = norm.cdf(d1)

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
            'cost_pct_account': risk_pct,
            'pnl': pnl,
            'pnl_pct': (pnl / cost) * 100,
            'stock_pct': ((exit_price - entry_stock) / entry_stock) * 100,
            'exit_reason': exit_reason,
            'delta': delta,
            'iv': base_vol
        })

        current_capital += pnl
        next_available_date = time_stop_date + timedelta(days=1)

    return trades, total_capital, current_capital


def main():
    logger.info("="*80)
    logger.info("REALISTIC BACKTEST: Fixed 1 Contract, Black-Scholes Pricing")
    logger.info("="*80)

    symbols = ['AAPL', 'SNAP', 'CCL', 'AAL', 'M', 'FSLY']
    moneyness_levels = ['ITM10', 'ATM', 'OTM10']

    print("\n" + "="*100)
    print(f"{'Symbol':<8} {'Moneyness':<10} {'Trades':>8} {'WinRate':>8} {'Final':>12} {'Return':>10} {'AvgCost':>10} {'AvgPnL':>10}")
    print("="*100)

    all_results = {}

    for symbol in symbols:
        all_results[symbol] = {}
        for moneyness in moneyness_levels:
            trades, capital, final_capital = run_backtest_fixed(
                symbol, moneyness=moneyness, stock_stop_pct=-0.02,
                time_stop_days=5, years=10, capital=1500
            )

            total = len(trades)
            if total > 0:
                wins = sum(1 for t in trades if t['pnl'] > 0)
                wr = (wins / total * 100)
                pnl = sum(t['pnl'] for t in trades)
                ret = (pnl / capital) * 100
                avg_cost = np.mean([t['cost'] for t in trades])
                avg_pnl = np.mean([t['pnl'] for t in trades])
                skipped = len(find_weekly_setups(resample_to_weekly(load_daily_data(symbol, 10)))) - total
            else:
                wr = 0
                ret = 0
                avg_cost = 0
                avg_pnl = 0
                skipped = 0

            all_results[symbol][moneyness] = {
                'trades': trades,
                'total': total,
                'win_rate': wr,
                'return': ret,
                'final': final_capital,
                'avg_cost': avg_cost,
                'avg_pnl': avg_pnl,
                'skipped': skipped
            }

            status = ""
            if total == 0:
                status = "(NO TRADES - too expensive)"
            print(f"{symbol:<8} {moneyness:<10} {total:>8} {wr:>7.1f}% ${final_capital:>10.2f} {ret:>9.1f}% ${avg_cost:>9.2f} ${avg_pnl:>9.2f} {status}")

    print("="*100)

    # Summary: Best moneyness per symbol
    print("\n" + "="*60)
    print("BEST MOneyNESS PER SYMBOL (Fixed 1 Contract)")
    print("="*60)
    for symbol in symbols:
        best_m = ''
        best_ret = -999999
        for m in moneyness_levels:
            r = all_results[symbol][m]['return']
            if r > best_ret:
                best_ret = r
                best_m = m
        print(f"{symbol:8s}: {best_m:8s} ({best_ret:+.1f}%)")

    # Generate report
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = Path(f'h:/QUANT TRADING/reports/weekly_breakout/MONEYNESS_REALISTIC_{ts}.md')
    report_path.parent.mkdir(parents=True, exist_ok=True)

    md = f"""# Realistic Moneyness Comparison: Fixed 1 Contract per Trade

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Model:** Black-Scholes with Historical Volatility
**Strategy:** Weekly Breakout, -2% Stock Stop, 5-Day Time Stop
**Account:** $1,500
**Sizing:** Fixed 1 contract per trade (realistic retail)
**Rule:** Skip trade if contract cost > account balance

---

## Option Model Details

| Parameter | Value |
|-----------|-------|
| Pricing Model | Black-Scholes |
| Volatility | Historical (60-day lookback) |
| Risk-Free Rate | 4.5% |
| Days to Expiration | 30 |
| **ITM Strike** | 90% of stock price |
| **ATM Strike** | 100% of stock price |
| **OTM Strike** | 110% of stock price |
| Sizing | Fixed 1 contract |
| Skip Rule | If contract cost > account balance |

---

## Results Summary

| Symbol | Moneyness | Trades | Win Rate | Final Capital | Total Return | Avg Contract Cost |
|--------|-----------|--------|----------|---------------|--------------|-------------------|
"""

    for symbol in symbols:
        for moneyness in moneyness_levels:
            data = all_results[symbol][moneyness]
            if data['total'] > 0:
                md += f"| {symbol} | {moneyness} | {data['total']} | {data['win_rate']:.1f}% | ${data['final']:,.2f} | {data['return']:+.1f}% | ${data['avg_cost']:.2f} |\n"
            else:
                md += f"| {symbol} | {moneyness} | 0 | - | - | - | Too expensive |\n"

    md += """
---

## Key Findings

### AAPL
- ITM: TOO EXPENSIVE for $1,500 account ($3,078/contract)
- ATM: Works well, 1 contract = 58% of account
- OTM: Cheapest, but lower delta = needs bigger moves

### Cheap Stocks (SNAP, AAL, M)
- All moneyness levels affordable
- ITM: Higher win rate, lower returns (expensive contracts)
- OTM: Lower win rate, explosive returns when they win
- ATM: Balanced

### Realistic Takeaway
With FIXED 1 contract sizing:
- ITM: Safer but capital-intensive (fewer trades)
- ATM: Best balance for most symbols
- OTM: High variance, many small losses, few big wins

---

## What Option Are You Buying?

**30 DTE (Days to Expiration) Call Option**

| Feature | Description |
|---------|-------------|
| Type | CALL (right to buy stock at strike) |
| Expiration | 30 days from entry |
| Strike | ATM = stock price / ITM = 90% of stock / OTM = 110% of stock |
| Premium | Calculated via Black-Scholes with historical volatility |

### Example: AAPL at $293

| Moneyness | Strike | Premium | Contract Cost | Delta |
|-----------|--------|---------|---------------|-------|
| ITM10 | $263.99 | $30.78 | $3,078 | 0.95 |
| ATM | $293.32 | $8.64 | $864 | 0.54 |
| OTM10 | $322.65 | $0.92 | $92 | 0.10 |

### Example: SNAP at $6.08

| Moneyness | Strike | Premium | Contract Cost | Delta |
|-----------|--------|---------|---------------|-------|
| ITM10 | $5.47 | $0.80 | $80 | 0.76 |
| ATM | $6.08 | $0.45 | $45 | 0.54 |
| OTM10 | $6.69 | $0.22 | $22 | 0.34 |

---

## Risk Reality Check ($1,500 Account)

| Symbol | Moneyness | Contract Cost | % of Account | Affordable? |
|--------|-----------|---------------|--------------|-------------|
| AAPL | ITM10 | $3,078 | 205% | ❌ NO |
| AAPL | ATM | $864 | 58% | ✅ Yes (1 contract) |
| AAPL | OTM10 | $92 | 6% | ✅ Yes |
| SNAP | ITM10 | $80 | 5% | ✅ Yes |
| SNAP | ATM | $45 | 3% | ✅ Yes |
| SNAP | OTM10 | $22 | 1% | ✅ Yes |

---

## Recommendation

For **$1,500 account**:
1. **AAPL**: Can only trade ATM or OTM (ITM too expensive)
2. **Cheap stocks**: Can trade any moneyness
3. **Best overall**: ATM strikes (balanced delta, reasonable cost)
4. **Conservative**: ITM on cheap stocks only (higher delta, more directional)
5. **Aggressive**: OTM (cheaper, higher leverage, more variance)

---

*Realistic backtest with proper Black-Scholes pricing and fixed 1-contract sizing*
"""

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(md)

    logger.info(f"\n✅ Report saved: {report_path}")


if __name__ == "__main__":
    main()
