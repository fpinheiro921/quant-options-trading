"""
Tastytrade API Connection
SDK:     pip install tastytrade  (already installed v12.4.1)
Docs:    H:\\QUANT TRADING\\tastytrade-llms-txt-docs\\llms.txt
GitHub:  https://github.com/tastyware/tastytrade

─────────────────────────────────────────────────────────────
HOW AUTHENTICATION WORKS (from official docs)
─────────────────────────────────────────────────────────────
For a PERSONAL app (your own account only):

  1. Go to my.tastytrade.com → Settings → API (or Developer Portal)
  2. Create an OAuth2 app → get client_id and client_secret
  3. Generate a PERSONAL GRANT (refresh_token) directly on that page
     (No browser flow needed for personal apps!)
  4. Access tokens last 15 minutes
     → SDK auto-refreshes using: Session(client_secret, refresh_token)

Base URL (production): https://api.tastyworks.com
Base URL (sandbox):    https://api.cert.tastyworks.com

─────────────────────────────────────────────────────────────
SETUP
─────────────────────────────────────────────────────────────
Set these environment variables (PowerShell):

  $env:TASTYTRADE_CLIENT_SECRET = "your_client_secret"
  $env:TASTYTRADE_REFRESH_TOKEN = "your_refresh_token_from_personal_grant"

Then run:
  python tastytrade_connect.py --connect      # verify connection
  python tastytrade_connect.py --test-order   # dry-run SNAP OTM order
"""
import sys
import os
import asyncio
import logging
from decimal import Decimal
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# CREDENTIALS — load from .env file, fallback to env vars
# ─────────────────────────────────────────────────────────────
def _load_env():
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

CLIENT_SECRET  = os.getenv('TASTYTRADE_CLIENT_SECRET')
REFRESH_TOKEN  = os.getenv('TASTYTRADE_REFRESH_TOKEN')
ACCOUNT_NUMBER = os.getenv('TASTYTRADE_ACCOUNT')


def check_credentials():
    missing = []
    if not CLIENT_SECRET:
        missing.append("TASTYTRADE_CLIENT_SECRET")
    if not REFRESH_TOKEN:
        missing.append("TASTYTRADE_REFRESH_TOKEN")
    if missing:
        for m in missing:
            logger.error(f"Missing env var: {m}")
        logger.error("Set them in PowerShell:")
        logger.error('  $env:TASTYTRADE_CLIENT_SECRET = "..."')
        logger.error('  $env:TASTYTRADE_REFRESH_TOKEN = "..."')
        logger.error("\nGet refresh_token from: my.tastytrade.com → Settings → API → Personal Grant")
        return False
    return True


# ─────────────────────────────────────────────────────────────
# CONNECTION TEST
# ─────────────────────────────────────────────────────────────
async def connect_and_show():
    """Connect to Tastytrade, print account balance and positions."""
    from tastytrade import Session, Account

    if not check_credentials():
        return None, None

    logger.info("Authenticating with Tastytrade...")
    # Session(client_secret, refresh_token) — auto-handles 15-min token refresh
    session = Session(CLIENT_SECRET, REFRESH_TOKEN)
    logger.info("Connected!")

    accounts = await Account.get(session)
    account  = accounts[0]
    logger.info(f"Account number: {account.account_number}")

    balances  = await account.get_balances(session)
    positions = await account.get_positions(session)

    print(f"\n{'='*50}")
    print(f"ACCOUNT: {account.account_number}")
    print(f"  Cash Balance:        ${balances.cash_balance:,.2f}")
    print(f"  Net Liquidating Val: ${balances.net_liquidating_value:,.2f}")
    print(f"  Buying Power:        ${balances.equity_buying_power:,.2f}")
    print(f"  Open Positions:      {len(positions)}")
    if positions:
        print(f"\n  Positions:")
        for p in positions:
            print(f"    {p.symbol:30s}  qty={p.quantity}  avg={p.average_open_price}")
    print(f"{'='*50}\n")

    return session, account


# ─────────────────────────────────────────────────────────────
# STRIKE HELPERS
# ─────────────────────────────────────────────────────────────
def otm_strike(stock_price: float, pct: float = 0.10) -> Decimal:
    """
    10% OTM call strike.  Formula: price * 1.10, rounded to nearest increment.

    Phase 1-4 (SNAP, CCL, AAL, M, FSLY): pct=0.10  (OTM)
    Phase 4 (Top 5 ATM):                  pct=0.00  (ATM)
    Phase 5 (AAPL 90-delta):              pct=-0.12 (ITM, use itm_strike_aapl)
    """
    raw = stock_price * (1 + pct)
    if stock_price < 25:
        rounded = round(raw * 2) / 2    # $0.50 increments
    elif stock_price < 100:
        rounded = round(raw)            # $1 increments
    else:
        rounded = round(raw / 5) * 5   # $5 increments
    return Decimal(str(rounded))


def itm_strike_aapl(stock_price: float) -> Decimal:
    """90-delta ITM strike for AAPL (Phase 5). ~88% of price, $5 increments."""
    raw = stock_price * 0.88
    return Decimal(str(round(raw / 5) * 5))


# ─────────────────────────────────────────────────────────────
# PLACE ORDER  (Buy to Open 10% OTM Call)
# ─────────────────────────────────────────────────────────────
async def buy_otm_call(
    symbol: str,
    stock_price: float,
    expiration: date,
    limit_price: float,
    dry_run: bool = True,
    phase: str = 'otm'
):
    """
    Buy 1 call option for the weekly breakout strategy.

    Args:
        symbol:       e.g. 'SNAP'
        stock_price:  price at breakout entry
        expiration:   option expiration date (aim for ~30 DTE)
        limit_price:  limit price in dollars (use mid of bid/ask)
        dry_run:      True = preview, False = real order
        phase:        'otm' (10% OTM), 'atm' (ATM), 'aapl' (90-delta ITM)
    """
    from tastytrade import Session, Account
    from tastytrade.instruments import NestedOptionChain, Option
    from tastytrade.order import NewOrder, OrderAction, OrderTimeInForce, OrderType

    if not check_credentials():
        return

    if phase == 'aapl':
        strike = itm_strike_aapl(stock_price)
    elif phase == 'atm':
        strike = otm_strike(stock_price, pct=0.00)
    else:
        strike = otm_strike(stock_price, pct=0.10)

    logger.info(f"\n{'='*50}")
    logger.info(f"  {'DRY RUN' if dry_run else 'LIVE'} ORDER: {symbol} CALL")
    logger.info(f"  Stock:      ${stock_price:.2f}")
    logger.info(f"  Strike:     ${strike}")
    logger.info(f"  Expiry:     {expiration}")
    logger.info(f"  Limit:      ${limit_price:.2f}")
    logger.info(f"  Phase:      {phase.upper()}")
    logger.info(f"{'='*50}")

    session  = Session(CLIENT_SECRET, REFRESH_TOKEN)
    accounts = await Account.get(session)
    account  = accounts[0]

    # Fetch option instrument using OCC symbol format
    # OCC format: SNAP  260619C00016500
    option = await Option.get_option(
        session,
        symbol=symbol,
        expiration_date=expiration,
        strike_price=strike,
        option_type='C'
    )

    leg = option.build_leg(Decimal('1'), OrderAction.BUY_TO_OPEN)

    order = NewOrder(
        time_in_force=OrderTimeInForce.DAY,
        order_type=OrderType.LIMIT,
        legs=[leg],
        price=Decimal(str(limit_price)),
        price_effect='Debit'
    )

    response = await account.place_order(session, order, dry_run=dry_run)
    logger.info(f"Response: {response}")

    if dry_run:
        logger.info("\nDRY RUN only. Change dry_run=False to place real order.")

    return response


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--connect" in sys.argv:
        asyncio.run(connect_and_show())

    elif "--test-order" in sys.argv:
        # Dry-run: buy SNAP 10% OTM call, ~30 DTE, limit $0.48
        asyncio.run(buy_otm_call(
            symbol='SNAP',
            stock_price=15.00,
            expiration=date(2026, 6, 19),
            limit_price=0.48,
            dry_run=True,
            phase='otm'
        ))

    else:
        print(__doc__)
        print("\nUsage:")
        print("  python tastytrade_connect.py --connect      # verify connection + show balance")
        print("  python tastytrade_connect.py --test-order   # dry-run SNAP OTM order")
