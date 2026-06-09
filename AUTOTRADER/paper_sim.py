"""
Paper Trading Simulation
────────────────────────
Replays the last N weeks of real SNAP daily candles through the exact
same strategy logic the live bot uses:

  - Detects weekly breakouts (current week close > prev week HIGH)
  - Looks up what the real option would have cost that Monday
  - Simulates exits: stock stop -1.5%, time stop 3 days, profit target 2x
  - Prints a full trade log and P&L summary
  - Sends results to Discord

Usage:
  python paper_sim.py            # simulate last 12 weeks
  python paper_sim.py --weeks 26 # simulate last 26 weeks
"""
import os
import sys
import asyncio
import logging
import requests
import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from decimal import Decimal

# ── Setup ─────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

env_file = Path(r'H:\QUANT TRADING\STRATEGY_COMBINATIONS\.env')
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

logging.basicConfig(level=logging.WARNING)  # suppress noise during sim
logger = logging.getLogger(__name__)

from tt_client import TastyClient
from weekly_candles import fetch_daily_candles, aggregate_to_weekly
from strikes import calc_strike
from notifier import _try_send_discord

# ── Black-Scholes for option pricing ─────────────────────────
import math

def black_scholes_call(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    from scipy.stats import norm
    return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)

def estimate_vol(daily_candles: list, window: int = 20) -> float:
    closes = [c["close"] for c in daily_candles if c["close"] > 0]
    if len(closes) < window + 1:
        return 0.60  # default high vol for small caps
    returns = [math.log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
    recent  = returns[-window:]
    mean    = sum(recent) / len(recent)
    var     = sum((r - mean) ** 2 for r in recent) / len(recent)
    return math.sqrt(var * 252)


def run_simulation(weeks_back: int = 12):
    client = TastyClient()
    symbol = "SNAP"
    moneyness = "otm10"
    stop_pct  = -0.015
    time_stop_days = 3
    starting_capital = 146.23
    max_risk_pct = 0.50

    print(f"\n{'='*60}")
    print(f"  PAPER TRADING SIMULATION — {symbol} OTM Phase 1")
    print(f"  Last {weeks_back} weeks of real market data")
    print(f"  Starting capital: ${starting_capital:.2f}")
    print(f"{'='*60}\n")

    # ── Fetch real daily candles ──────────────────────────────
    print("Fetching real SNAP candles from DXLink...")
    quote_token = client.get_quote_token()
    daily = asyncio.run(fetch_daily_candles(symbol, quote_token, days_back=weeks_back * 7 + 10))

    if len(daily) < 10:
        print(f"Not enough candle data ({len(daily)} days). Try fewer weeks.")
        return

    print(f"Got {len(daily)} daily candles ({daily[0]['date']} → {daily[-1]['date']})\n")

    weekly = aggregate_to_weekly(daily)
    vol    = estimate_vol(daily)
    print(f"Estimated annualized volatility: {vol*100:.1f}%\n")

    # ── Simulate week by week ─────────────────────────────────
    capital = starting_capital
    trades  = []
    r       = 0.045

    for i in range(1, len(weekly) - 1):  # need prev week + current + next
        prev_week    = weekly[i - 1]
        entry_week   = weekly[i]
        next_week    = weekly[i + 1] if i + 1 < len(weekly) else None

        prev_high    = prev_week["high"]
        entry_close  = entry_week["close"]
        entry_date   = entry_week["week_start"]

        # Skip if no breakout
        if entry_close <= prev_high:
            continue

        pct_above = (entry_close - prev_high) / prev_high * 100

        # Calculate OTM strike
        strike = float(calc_strike(entry_close, moneyness))
        T_entry = 30 / 365.0
        entry_prem = black_scholes_call(entry_close, strike, T_entry, r, vol)
        contract_cost = entry_prem * 100

        # Check affordability
        max_cost = capital * max_risk_pct
        if contract_cost > max_cost:
            print(f"  {entry_date}  SKIP — cost ${contract_cost:.2f} > max ${max_cost:.2f}")
            continue

        # Simulate exit using next week's daily candles
        stop_price = entry_close * (1 + stop_pct)

        # Get daily candles for this week
        week_days = [c for c in daily
                     if entry_date <= c["date"] < entry_date + timedelta(days=7)]

        exit_price   = None
        exit_reason  = None
        exit_premium = entry_prem  # fallback

        for day_num, day in enumerate(week_days[:time_stop_days]):
            if day["low"] <= stop_price:
                exit_price  = stop_price
                exit_reason = "STOCK_STOP"
                days_held   = day_num + 1
                break
            if day_num == time_stop_days - 1:
                exit_price  = day["close"]
                exit_reason = "TIME_STOP"
                days_held   = time_stop_days
                break

        if exit_price is None:
            exit_price  = week_days[-1]["close"] if week_days else entry_close
            exit_reason = "TIME_STOP"
            days_held   = len(week_days)

        days_remaining = max(0, 30 - days_held)
        T_exit = days_remaining / 365.0
        exit_premium = black_scholes_call(exit_price, strike, T_exit, r, vol)

        # Profit target check
        if exit_premium >= entry_prem * 2:
            exit_reason  = "PROFIT_TARGET"

        exit_premium = max(exit_premium, 0.01)
        pnl = (exit_premium - entry_prem) * 100
        capital += pnl
        capital  = max(capital, 10)

        result = "WIN " if pnl > 0 else "LOSS"
        trades.append({
            "date":         entry_date,
            "entry_stock":  entry_close,
            "strike":       strike,
            "entry_prem":   entry_prem,
            "exit_prem":    exit_premium,
            "exit_reason":  exit_reason,
            "pnl":          pnl,
            "capital":      capital,
        })

        print(f"  {entry_date}  {result}  "
              f"stock=${entry_close:.2f}(+{pct_above:.1f}% above prev high=${prev_high:.2f})  "
              f"strike=${strike:.2f}  entry=${entry_prem:.2f}  exit=${exit_premium:.2f}  "
              f"pnl=${pnl:+.2f}  [{exit_reason}]  capital=${capital:.2f}")

    # ── Summary ───────────────────────────────────────────────
    if not trades:
        print("\nNo breakout signals found in this period.")
        return

    wins   = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl = sum(t["pnl"] for t in trades)
    wr = len(wins) / len(trades) * 100
    avg_win  = sum(t["pnl"] for t in wins)  / len(wins)  if wins   else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0

    print(f"\n{'='*60}")
    print(f"  SIMULATION RESULTS ({weeks_back} weeks)")
    print(f"{'='*60}")
    print(f"  Trades:        {len(trades)}  ({len(wins)} wins / {len(losses)} losses)")
    print(f"  Win rate:      {wr:.1f}%")
    print(f"  Total P&L:     ${total_pnl:+.2f}")
    print(f"  Avg win:       ${avg_win:+.2f}")
    print(f"  Avg loss:      ${avg_loss:+.2f}")
    print(f"  Start capital: ${starting_capital:.2f}")
    print(f"  End capital:   ${capital:.2f}")
    print(f"  Return:        {(capital - starting_capital) / starting_capital * 100:+.1f}%")
    print(f"{'='*60}\n")

    # ── Discord summary ───────────────────────────────────────
    discord_body = (
        f"Period:      Last {weeks_back} weeks\n"
        f"Trades:      {len(trades)}  ({len(wins)}W / {len(losses)}L)\n"
        f"Win rate:    {wr:.1f}%\n"
        f"Total P&L:   ${total_pnl:+.2f}\n"
        f"Start:       ${starting_capital:.2f}\n"
        f"End:         ${capital:.2f}\n"
        f"Return:      {(capital - starting_capital) / starting_capital * 100:+.1f}%"
    )
    color = 0x2ecc71 if total_pnl > 0 else 0xe74c3c
    _try_send_discord(
        subject=f"[Paper Sim] SNAP OTM — {weeks_back}wk backtest",
        body=discord_body,
        color=color
    )
    print("Results sent to Discord.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", type=int, default=12)
    args = parser.parse_args()

    try:
        from scipy.stats import norm
    except ImportError:
        print("Installing scipy...")
        import subprocess
        subprocess.check_call(["pip", "install", "scipy", "-q"])

    run_simulation(weeks_back=args.weeks)
