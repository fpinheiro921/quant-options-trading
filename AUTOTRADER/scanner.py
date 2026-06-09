"""
Weekly breakout scanner.
Runs Monday morning — detects if a symbol broke above its previous week's HIGH.

Breakout condition (correct strategy definition):
  Current price > Previous week's HIGH candle

Uses DXLink WebSocket for real daily candles aggregated to weekly OHLC.
Falls back to prev_close proxy if WebSocket unavailable.
"""
import asyncio
import logging
from datetime import date, timedelta
from decimal import Decimal
from tt_client import TastyClient
from strikes import calc_strike, find_best_expiration, find_nearest_strike_from_chain
from config import PHASE_CONFIG

logger = logging.getLogger(__name__)


def is_weekly_breakout(client: TastyClient, symbol: str) -> tuple[bool, dict]:
    """
    Check if symbol has a valid weekly breakout setup.
    Uses proper weekly OHLC candles via DXLink (falls back to REST proxy).

    Returns (is_breakout, info_dict)
    """
    # ── Try proper DXLink candle breakout ────────────────────
    try:
        from weekly_candles import get_weekly_breakout_signal
        import websockets  # noqa — just check it's installed

        quote_token = client.get_quote_token()
        is_breakout, info = asyncio.run(
            get_weekly_breakout_signal(symbol, quote_token)
        )
        current = info.get("current_close", 0)
        return is_breakout, {"close": current, **info}

    except Exception as e:
        logger.warning(f"  DXLink candle fetch failed ({e}) — falling back to REST proxy")

    # ── Fallback: REST prev_close proxy ──────────────────────
    candles = client.get_weekly_candles(symbol)
    if not candles:
        return False, {}

    d          = candles[0]
    current    = d["close"]
    prev_close = d["prev_close"]

    if prev_close <= 0:
        return False, d

    pct_move    = (current - prev_close) / prev_close * 100
    is_breakout = pct_move >= 1.0

    flag = "[BREAKOUT]" if is_breakout else "[no signal]"
    logger.info(f"  {symbol}: ${current:.2f}  prev_close=${prev_close:.2f}  "
                f"move={pct_move:+.1f}%  {flag} [REST fallback]")

    return is_breakout, {**d, "pct_move": pct_move}


def find_option_to_buy(
    client: TastyClient,
    symbol: str,
    stock_price: float,
    moneyness: str,
    dte_target: int = 30,
    max_cost: float = None,
) -> dict | None:
    """
    Find the best option contract to buy for a breakout signal.

    Returns a dict with all order details, or None if no suitable option found.
    """
    try:
        expirations = client.get_option_chain(symbol)
    except Exception as e:
        logger.error(f"Could not get option chain for {symbol}: {e}")
        return None

    # Find best expiration
    best_exp    = find_best_expiration(expirations, dte_target)
    exp_date_str = best_exp["expiration-date"]
    dte          = best_exp["days-to-expiration"]
    exp_date     = date.fromisoformat(exp_date_str)

    # Calculate target strike
    target_strike = calc_strike(stock_price, moneyness)

    # Find nearest strike in chain
    strikes = best_exp["strikes"]
    nearest = find_nearest_strike_from_chain(strikes, target_strike)
    occ_symbol   = nearest["call"]
    actual_strike = Decimal(str(nearest["strike-price"]))

    # Get quote
    quote = client.get_option_quote(occ_symbol)
    if not quote:
        logger.warning(f"No quote for {occ_symbol}")
        return None

    bid = float(quote.get("bid", 0))
    ask = float(quote.get("ask", 0))
    mid = round((bid + ask) / 2, 2)

    if mid <= 0:
        logger.warning(f"Zero mid price for {occ_symbol}")
        return None

    cost = mid * 100

    # Respect max cost guardrail
    if max_cost and cost > max_cost:
        logger.warning(f"{occ_symbol}: cost ${cost:.2f} > max allowed ${max_cost:.2f} — skipping")
        return None

    result = {
        "symbol":         symbol,
        "occ_symbol":     occ_symbol,
        "stock_price":    stock_price,
        "strike":         float(actual_strike),
        "target_strike":  float(target_strike),
        "exp_date":       exp_date_str,
        "dte":            dte,
        "bid":            bid,
        "ask":            ask,
        "mid":            mid,
        "cost":           cost,
        "moneyness":      moneyness,
    }

    logger.info(f"  Option found: {occ_symbol}  bid={bid}  ask={ask}  mid={mid}  "
                f"cost=${cost:.2f}  DTE={dte}")
    return result


def scan_phase(client: TastyClient, phase_cfg: dict, cash_balance: float) -> list:
    """
    Scan all symbols in a phase for breakout setups.
    Returns list of actionable option candidates.
    """
    signals = []
    max_risk_pct  = phase_cfg["max_risk_pct"]
    max_cost      = cash_balance * max_risk_pct
    moneyness     = phase_cfg["moneyness"]
    dte_target    = phase_cfg["dte_target"]
    vix_max       = phase_cfg["vix_max"]

    logger.info(f"\nScanning {len(phase_cfg['symbols'])} symbols | "
                f"max_cost=${max_cost:.2f} ({max_risk_pct*100:.0f}% of ${cash_balance:.2f})")

    for symbol in phase_cfg["symbols"]:
        # Skip if already have open trade for this symbol
        breakout, mkt = is_weekly_breakout(client, symbol)
        if not breakout:
            continue

        stock_price = mkt["close"]
        option = find_option_to_buy(
            client, symbol, stock_price, moneyness, dte_target, max_cost
        )
        if option:
            option["stop_price"]   = round(stock_price * (1 + phase_cfg["stop_pct"]), 2)
            option["time_stop"]    = phase_cfg["time_stop_days"]
            signals.append(option)

    logger.info(f"Scan complete: {len(signals)} signal(s) found")
    return signals
