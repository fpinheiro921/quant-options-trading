# AutoTrader — Complete Guide

## Do I Need My PC On At All Times?

**Short answer: No — but it must be on at 14:40 Portugal time Monday–Friday.**

The bot runs once per day for ~30 seconds via Windows Task Scheduler.
It does NOT run continuously.

### Portugal Timezone Reference

| Season | Portugal | ET (New York) | Task time |
|--------|----------|---------------|-----------|
| Summer (Mar–Oct) | UTC+1 (WET) | UTC-4 (EDT) | **14:40 Portugal** |
| Winter (Nov–Mar) | UTC+0 (WET) | UTC-5 (EST) | **13:40 Portugal** |

US market opens 9:30 AM ET. Bot runs 10 min after open.
**The scheduler is set to 14:40 (summer). In November, update to 13:40.**

### Option A — PC at home (simplest)
- Turn on PC before **14:40 Portugal time** on trading days
- Or set PC to **wake from sleep** automatically (Power Options → Wake timers)
- The scheduled task runs, takes 30 seconds, then PC can sleep again

### Option B — Cloud VPS (~$5/month, fully hands-off)
If you want true 24/7 automation with zero PC dependency:

1. **Vultr / DigitalOcean** — $6/month, Windows Server
2. Upload this folder via FileZilla
3. Set up Task Scheduler on the VPS
4. Bot runs without your PC ever being on

**Recommended:** Start with Option A (free, works fine), move to VPS when you're
confident the bot is working correctly.

---

## System Architecture

```
main.py (runs daily at 9:40 AM)
  │
  ├── MONDAY: scanner.py → checks breakout conditions → trader.py → places entry
  │
  └── TUE–FRI: trader.py → checks exits (stop loss / time stop / profit target)
        │
        └── state_manager.py → saves all trade history to state/account_state.json
```

---

## Phase Journey

| Phase | Account | Strategy | Symbols |
|-------|---------|----------|---------|
| 1 | $0–$999 | SNAP OTM calls | SNAP |
| 2 | $400–$1499 | SNAP + AAL OTM | SNAP, AAL |
| 3 | $1000–$2999 | Top 5 OTM | SNAP, CCL, AAL, M, FSLY |
| 4 | $1500–$4999 | Top 5 ATM | SNAP, CCL, AAL, M, FSLY |
| 5 | $5000+ | AAPL 90-delta ITM | AAPL |

Phase transitions happen **automatically** — the bot detects your balance
and upgrades phase without you doing anything.

---

## Entry Rules (per the backtest strategy)

1. **Breakout signal**: Stock price > previous week's close by ≥1%
2. **Buy**: 1 call option, 10% OTM strike, ~30 DTE, limit at mid price
3. **No VIX filter yet** (too small account to matter at Phase 1)
4. Only **1 open trade per symbol** at a time

## Exit Rules

| Condition | Trigger | Action |
|-----------|---------|--------|
| Stock stop | Stock drops -1.5% from entry | Sell to Close at market mid |
| Time stop | 3 trading days elapsed | Sell to Close at market mid |
| Profit target | Option premium 2x entry | Sell to Close at market mid |

---

## Commands

```powershell
# Check account status
python "H:\QUANT TRADING\AUTOTRADER\main.py" --status

# Force a scan right now (test it)
python "H:\QUANT TRADING\AUTOTRADER\main.py" --scan --dry-run

# Force exit check right now
python "H:\QUANT TRADING\AUTOTRADER\main.py" --exits --dry-run

# Run live (no dry-run flag)
python "H:\QUANT TRADING\AUTOTRADER\main.py" --scan
```

## Setup (one time)

```powershell
# 1. Install Task Scheduler tasks (run as Administrator)
cd "H:\QUANT TRADING\AUTOTRADER"
.\setup_scheduler.ps1

# 2. Test dry-run to confirm everything works
python main.py --scan --dry-run
python main.py --exits --dry-run

# 3. Go live (remove --dry-run)
# The scheduler handles it from here
```

## Files

| File | Purpose |
|------|---------|
| `main.py` | Daily orchestrator |
| `config.py` | Phase definitions and parameters |
| `tt_client.py` | Tastytrade API wrapper |
| `scanner.py` | Weekly breakout detection |
| `trader.py` | Order entry and exit logic |
| `state_manager.py` | Persistent trade/phase state |
| `notifier.py` | Log + email notifications |
| `state/account_state.json` | Live state (auto-created) |
| `logs/autotrader_YYYYMMDD.log` | Daily log files |

## Email Alerts (optional)

Add to `STRATEGY_COMBINATIONS/.env`:
```
NOTIFY_EMAIL=your@gmail.com
NOTIFY_EMAIL_PASSWORD=your_gmail_app_password
NOTIFY_TO=your@gmail.com
```
Get app password: myaccount.google.com → Security → App Passwords
