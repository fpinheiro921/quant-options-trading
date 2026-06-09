# Tastytrade Trading Guide: Weekly Breakout Strategy

**Account:** fpinheiro921 Personal OAuth2 App  
**Strategy:** Weekly Breakout with 10% OTM Calls  
**Starting Capital:** $150  

---

## Step 1: Verify Account Setup

### Checklist Before Trading
- [ ] Account created and funded ($150 minimum)
- [ ] Options Level 2 (Standard Cash) approved
- [ ] OAuth2 credentials created (✅ Done)
- [ ] Paper trading configured (for practice)

### Your OAuth2 Credentials
```bash
# Save these as environment variables
export TASTYTRADE_CLIENT_ID="your_client_id"
export TASTYTRADE_CLIENT_SECRET="your_client_secret"
export TASTYTRADE_REDIRECT_URI="http://localhost:3000/callback"
```

---

## Step 2: Paper Trading (Phase 0)

### Enable Paper Trading in Tastytrade
```
Mobile App: Profile → Trading Preferences → Paper Trading ON
Desktop:  Settings → Trading → Paper Trading Mode
```

### Practice Order Entry (Do This 20+ Times)

#### Example: SNAP Weekly Breakout

**Scenario:** SNAP breaks above previous week's high at $15.00

**Step 1: Calculate 10% OTM Strike**
```
Stock Price: $15.00
Calculation: $15.00 × 1.10 = $16.50
Strike to Buy: $16.50 Call
```

**Step 2: Find Option in Tastytrade**
```
1. Search "SNAP"
2. Click "Trade" → "Options"
3. Select expiration: ~30 DTE (e.g., Jun 21 if today is May 22)
4. Find $16.50 strike in the chain
5. Click the Call (C) side
```

**Step 3: Preview Order**
```
Action: BUY TO OPEN
Quantity: 1
Order Type: LIMIT (recommended)
Price: Mid between bid/ask (e.g., if bid=$0.45, ask=$0.50, enter $0.48)
Time-in-Force: DAY
```

**Step 4: Set Stops (Critical!)**
- Stock stop: -1.5% from entry ($15.00 → stop at $14.78)
- Time stop: 3 days (exit by Thursday of entry week)
- Profit target: Stock +8% ($15.00 → target at $16.20)

---

## Step 3: Phase Transition Guide

| Phase | Account | Symbol | Strike | Position | Stop |
|-------|---------|--------|--------|----------|------|
| **0. Paper** | $0 | SNAP | 10% OTM | 1 contract | -1.5% |
| **1. SNAP OTM** | $400+ | SNAP | 10% OTM | 1 contract | -1.5% |
| **2. SNAP+AAL** | $1,000+ | SNAP/AAL | 10% OTM | 1 each | -1.5% |
| **3. Top 5 OTM** | $1,500+ | SNAP/CCL/AAL/M/FSLY | 10% OTM | 1 each | -1.5% |
| **4. Top 5 ATM** | $3,000+ | Top 5 | ATM (100%) | 1 each | -1.5% |
| **5. AAPL ATM** | $5,000+ | AAPL | 90-delta ITM | 0.5 size | -1.5% |

---

## Step 4: Order Entry Templates

### Template 1: SNAP OTM Buy
```
Symbol: SNAP
Option: CALL
Strike: [Stock Price × 1.10]
Expiration: 30-35 DTE
Action: BUY TO OPEN
Quantity: 1
Order Type: LIMIT (mid price)
TIF: DAY

Exit Rules:
- Stock Stop: -1.5% from entry
- Time Stop: 3 days (Thursday)
- Profit Target: +8% stock move
```

### Template 2: AAPL ITM Buy (Phase 5)
```
Symbol: AAPL
Option: CALL
Strike: [Stock Price × 0.88] (90-delta)
Expiration: 30-35 DTE
Action: BUY TO OPEN
Quantity: 1 (50% of normal size)
Order Type: LIMIT (mid price)
TIF: DAY

Exit Rules:
- Stock Stop: -1.5% from entry
- Time Stop: 3 days
- VIX Filter: Only if VIX < 20
```

---

## Step 5: Risk Management Rules

### Maximum Risk Per Trade
```
Account < $1,000: Risk $40-50 per trade (10-12%)
Account $1,000-$5,000: Risk $100-150 per trade (3-5%)
Account > $5,000: Risk $250-500 per trade (2-5%)
```

### Position Sizing
```
1. Check option premium (e.g., $0.50 = $50 per contract)
2. Ensure total cost < 15% of account
3. Example: $400 account → max $60 per trade
```

### Daily Checklist
- [ ] Check VIX (skip if > 25, or > 20 for AAPL)
- [ ] Check for weekly setups (break above previous week high)
- [ ] Calculate OTM strike (stock × 1.10)
- [ ] Verify option price is affordable (< 15% account)
- [ ] Set stock stop at -1.5%
- [ ] Set calendar reminder for 3-day exit

---

## Step 6: Automating with API

### Python Script Setup
```bash
# Install dependencies
pip install requests

# Set credentials
set TASTYTRADE_CLIENT_ID=your_id
set TASTYTRADE_CLIENT_SECRET=your_secret
```

### Run Authentication
```bash
python tastytrade_api_setup.py
```

### API Order Example
```python
from tastytrade_api_setup import TastytradeClient

client = TastytradeClient()
client.authenticate()

# Buy SNAP 10% OTM call
order = {
    'symbol': 'SNAP',
    'strike': 16.50,
    'expiration': '2026-06-21',
    'option_type': 'Call',
    'quantity': 1,
    'action': 'Buy to Open',
    'price': 'Market'
}

client.place_order(order)
```

---

## Step 7: Weekly Routine

### Sunday Evening (Prepare for Week)
1. Scan charts for all symbols
2. Mark previous week's high
3. Note which stocks are close to breakout

### Monday-Friday (Trading Days)
**Morning (9:30 AM ET):**
- Check if any stock gapped above previous week's high
- If yes → Calculate 10% OTM strike
- Preview order in Tastytrade
- Buy if setup is valid and VIX OK

**Afternoon (3:00 PM ET):**
- Check existing positions
- If stock hit -1.5% stop → Exit immediately
- If approaching 3-day limit → Evaluate for exit

### Friday Evening (Week Review)
- Log all trades in journal
- Note what worked/didn't
- Update account balance tracking

---

## Step 8: Phase Transition Checklist

### Paper → SNAP OTM ($150 → $400)
- [ ] Paper traded 20+ times
- [ ] Consistently following -1.5% stops
- [ ] Account reaches $400 (savings)
- [ ] Deposit $400 to live account

### SNAP OTM → SNAP+AAL ($400 → $1,000)
- [ ] 5+ trades completed
- [ ] Comfortable with order entry
- [ ] Account reaches $1,000
- [ ] Add AAL to watchlist

### Continue through all phases...

---

## Important Notes

### Tastytrade Specific
- **$0 commissions** on options closing (great for small accounts)
- **No assignment fees** (unlike other brokers)
- **Desktop app** has better charting than mobile
- **Watchlists** help track multiple symbols

### Account Safety
- Start with **paper trading**
- Only risk what you can afford to lose
- **Never** skip the -1.5% stop loss
- **Never** hold past 3 days without a plan

### When to Skip a Trade
- VIX > 25 (or > 20 for AAPL)
- Earnings within 5 days
- Major news event for the stock
- Account balance too low (< $400)

---

## Quick Reference Card

| Element | Value | Notes |
|---------|-------|-------|
| Entry | Break above prev week high | Confirmed on weekly chart |
| OTM Calc | Stock × 1.10 | Round to nearest strike |
| Stop Loss | -1.5% on stock | Monitor stock price, not option |
| Time Stop | 3 days | Exit by Thursday |
| Profit Target | +8% on stock | Optional, can hold to time stop |
| Max Risk | 10-15% account | Never more |
| DTE | 30-35 days | Avoid weeklies |
| VIX Max | 25 (20 for AAPL) | Skip if higher |

---

## Need Help?

### Tastytrade Resources
- **Support:** support@tastytrade.com
- **Documentation:** developer.tastytrade.com
- **Community:** r/tastytrade (Reddit)

### Strategy Questions
- Review reports in `reports/strategy_combinations/`
- Check `OPTIMIZED_STRATEGY_20260511_141903.md` for parameters
- Run backtests with `enhanced_individual_phases.py`

---

**Ready to start? Begin with paper trading for 1 month, then go live at $400.**
