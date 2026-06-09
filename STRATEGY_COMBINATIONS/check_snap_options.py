"""Check SNAP current price and 10% OTM option costs for ~30 DTE."""
import os, requests
from pathlib import Path

env_file = Path(r'h:\QUANT TRADING\STRATEGY_COMBINATIONS\.env')
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

CLIENT_SECRET = os.getenv('TASTYTRADE_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('TASTYTRADE_REFRESH_TOKEN')
BASE = "https://api.tastyworks.com"

resp = requests.post(f'{BASE}/oauth/token',
    data={'grant_type': 'refresh_token', 'refresh_token': REFRESH_TOKEN, 'client_secret': CLIENT_SECRET},
    headers={'Content-Type': 'application/x-www-form-urlencoded'})
token = resp.json()['access_token']
H = {'Authorization': f'Bearer {token}', 'User-Agent': 'fpinheiro921/1.0'}

# ── SNAP current price ────────────────────────────────────────
resp = requests.get(f'{BASE}/market-data/by-type?equity=SNAP', headers=H)
snap = resp.json()['data']['items'][0]
price = float(snap['mark'])
print(f"\nSNAP current price: ${price:.2f}")
print(f"10% OTM strike:     ${round(price * 1.10 * 2) / 2:.2f}")
print(f"Account balance:    $146.23")

# ── Option chain - find ~30 DTE expiration ───────────────────
resp = requests.get(f'{BASE}/option-chains/SNAP/nested', headers=H)
expirations = resp.json()['data']['items'][0]['expirations']

print(f"\nAvailable expirations (~30 DTE target):")
for e in expirations[:10]:
    dte = e['days-to-expiration']
    print(f"  {e['expiration-date']}  DTE={dte}")

# Find closest to 30 DTE
target_exp = min(expirations, key=lambda e: abs(e['days-to-expiration'] - 30))
exp_date = target_exp['expiration-date']
print(f"\nBest expiration: {exp_date}  (DTE={target_exp['days-to-expiration']})")

# ── Find 10% OTM call price ───────────────────────────────────
otm_strike = round(price * 1.10 * 2) / 2
print(f"\nLooking for ${otm_strike:.2f} call on {exp_date}...")

strikes = target_exp['strikes']
# Find nearest strike to our target
nearest = min(strikes, key=lambda s: abs(float(s['strike-price']) - otm_strike))
call_symbol = nearest['call']
print(f"OCC Symbol: {call_symbol}")

# Get option market data
resp = requests.get(f'{BASE}/market-data/by-type?equity-option={call_symbol}', headers=H)
if resp.status_code == 200:
    items = resp.json()['data']['items']
    if items:
        opt = items[0]
        bid = float(opt.get('bid', 0))
        ask = float(opt.get('ask', 0))
        mid = (bid + ask) / 2
        cost = mid * 100
        pct_of_account = cost / 146.23 * 100
        print(f"\n{'='*50}")
        print(f"OPTION QUOTE: {call_symbol}")
        print(f"  Bid:         ${bid:.2f}")
        print(f"  Ask:         ${ask:.2f}")
        print(f"  Mid:         ${mid:.2f}")
        print(f"  Cost (1 contract): ${cost:.2f}")
        print(f"  % of $146.23 account: {pct_of_account:.1f}%")
        print(f"  AFFORDABLE? {'✅ YES' if cost < 146.23 else '❌ NO - not enough cash'}")
        print(f"{'='*50}")
    else:
        print("No market data for this option")
else:
    print(f"Market data error: {resp.status_code} {resp.text}")

# Also check strikes around target
print(f"\nAll strikes near ${otm_strike:.2f} for {exp_date}:")
for s in strikes:
    sp = float(s['strike-price'])
    if abs(sp - otm_strike) <= 1.0:
        print(f"  Strike ${sp:.2f}  |  call={s['call']}")
