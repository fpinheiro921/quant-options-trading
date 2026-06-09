"""
Verify Option Pricing Model
Show actual Black-Scholes prices for ATM, ITM, OTM across all symbols
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')
sys.path.insert(0, r'h:\QUANT TRADING\scripts')

import numpy as np
from scipy.stats import norm
from backtest_weekly_breakout import load_daily_data


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


def calculate_greeks(S, K, T, r, sigma):
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {'delta': 0, 'theta': 0}
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    delta = norm.cdf(d1)
    theta = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
    return {'delta': delta, 'theta': theta / 365}


symbols = ['AAPL', 'SNAP', 'CCL', 'AAL', 'M', 'FSLY']

print("="*90)
print("OPTION PRICING VERIFICATION - Black-Scholes Model")
print("="*90)
print(f"\n{'Symbol':<8} {'Price':>8} {'IV':>6} {'Strike':>8} {'Type':>8} {'Premium':>10} {'Contract$':>10} {'Delta':>6} {'Theta/d':>8}")
print("-"*90)

for symbol in symbols:
    df = load_daily_data(symbol, years=1)
    if df.empty:
        continue
    
    price = df['close'].iloc[-1]
    iv = estimate_historical_volatility(df, 60)
    T = 30 / 365
    r = 0.045
    
    for moneyness, pct in [('ITM10', 0.90), ('ATM', 1.00), ('OTM10', 1.10)]:
        strike = price * pct
        premium = black_scholes_call(price, strike, T, r, iv)
        contract_cost = premium * 100
        greeks = calculate_greeks(price, strike, T, r, iv)
        
        print(f"{symbol:<8} ${price:>6.2f} {iv*100:>5.1f}% ${strike:>6.2f} {moneyness:>8} ${premium:>8.2f} ${contract_cost:>8.0f} {greeks['delta']:>6.2f} ${greeks['theta']:>7.2f}")
    
    print("-"*90)

print("\n" + "="*90)
print("ANALYSIS")
print("="*90)

print("""
ITM10  = 90% of stock price (10% In-The-Money)
ATM    = 100% of stock price (At-The-Money)
OTM10  = 110% of stock price (10% Out-of-The-Money)

KEY OBSERVATIONS:
- ITM options have higher delta (move more with stock) but cost more
- ATM options have delta ~0.50 (balanced)
- OTM options have lower delta (need bigger stock moves) but cost less
- Theta decay is most severe for ATM options
""")
