"""
One-time script to exchange refresh_token for an access token
and verify your Tastytrade credentials work.

STEP 1: Go to my.tastytrade.com
        → Manage tab → My Profile → API → OAuth Applications
        → Click "Manage" on fpinheiro921 Personal OAuth2 App
        → Click "Create Grant"
        → Copy the refresh_token shown

STEP 2: Set env vars in PowerShell:
        $env:TASTYTRADE_CLIENT_SECRET = "2dac589ad01010e82c14b33d432c87ef91ad25ae"
        $env:TASTYTRADE_REFRESH_TOKEN = "paste_your_refresh_token_here"

STEP 3: Run this script:
        python tastytrade_get_token.py
"""
import os
import requests

CLIENT_ID     = "4f6d10a7-01d5-47c3-ba5f-7ff812153205"
CLIENT_SECRET = os.getenv('TASTYTRADE_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('TASTYTRADE_REFRESH_TOKEN')

BASE_URL      = "https://api.tastyworks.com"


def get_access_token():
    """Exchange refresh_token for a 15-minute access token."""
    if not CLIENT_SECRET:
        print("ERROR: TASTYTRADE_CLIENT_SECRET not set")
        print('Run: $env:TASTYTRADE_CLIENT_SECRET = "2dac589ad01010e82c14b33d432c87ef91ad25ae"')
        return None
    if not REFRESH_TOKEN:
        print("ERROR: TASTYTRADE_REFRESH_TOKEN not set")
        print("Get it from: my.tastytrade.com → Manage → My Profile → API → OAuth Applications")
        print("             → Manage → Create Grant → copy the refresh_token")
        return None

    print("Requesting access token...")
    resp = requests.post(
        f"{BASE_URL}/oauth/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    if resp.status_code == 200:
        data = resp.json()
        access_token = data["access_token"]
        expires_in   = data.get("expires_in", 900)
        print(f"\n✅ Access token obtained! (expires in {expires_in}s / 15 min)")
        print(f"   Token: {access_token[:20]}...")
        return access_token
    else:
        print(f"\n❌ Failed: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return None


def verify_connection(access_token):
    """Use access token to fetch account info and confirm everything works."""
    print("\nVerifying connection...")
    resp = requests.get(
        f"{BASE_URL}/customers/me/accounts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
            "User-Agent":    "fpinheiro921-trading-bot/1.0"
        }
    )

    if resp.status_code == 200:
        data     = resp.json()
        accounts = data.get("data", {}).get("items", [])
        print(f"\n✅ Connected! Found {len(accounts)} account(s):")
        for acct in accounts:
            a = acct.get("account", {})
            print(f"   Account: {a.get('account-number')}  |  "
                  f"Type: {a.get('account-type-name')}  |  "
                  f"Nick: {a.get('nickname', 'N/A')}")
        return True
    else:
        print(f"\n❌ Verification failed: {resp.status_code}")
        print(f"   Response: {resp.text}")
        return False


if __name__ == "__main__":
    token = get_access_token()
    if token:
        verify_connection(token)
        print("\n🎉 Setup complete! You're ready to trade via API.")
        print("\nNext step:")
        print("  python tastytrade_connect.py --connect")
