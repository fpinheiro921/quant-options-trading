"""
Order executor — places entries and manages exits.
All orders are Limit at mid price for better fills.
"""
import logging
from datetime import datetime, date, timedelta
from tt_client import TastyClient
from state_manager import add_open_trade, close_trade, get_open_trade_for_symbol

logger = logging.getLogger(__name__)


def build_option_order(occ_symbol: str, limit_price: float) -> dict:
    """
    Build a Buy to Open limit order body for a single-leg equity option.
    Follows the exact tastytrade JSON structure from docs.
    """
    return {
        "time-in-force": "Day",
        "order-type":    "Limit",
        "price":         str(round(limit_price, 2)),
        "price-effect":  "Debit",
        "source":        "autotrader-v1",
        "legs": [
            {
                "action":          "Buy to Open",
                "symbol":          occ_symbol,
                "quantity":        1,
                "instrument-type": "Equity Option",
            }
        ],
    }


def build_close_order(occ_symbol: str, limit_price: float) -> dict:
    """Build a Sell to Close limit order."""
    return {
        "time-in-force": "Day",
        "order-type":    "Limit",
        "price":         str(round(limit_price, 2)),
        "price-effect":  "Credit",
        "source":        "autotrader-v1",
        "legs": [
            {
                "action":          "Sell to Close",
                "symbol":          occ_symbol,
                "quantity":        1,
                "instrument-type": "Equity Option",
            }
        ],
    }


def enter_trade(client: TastyClient, state: dict, signal: dict, dry_run: bool = False) -> bool:
    """
    Place a Buy to Open order for a breakout signal.
    Returns True if order was placed (or dry-run succeeded).
    """
    occ    = signal["occ_symbol"]
    price  = signal["mid"]
    symbol = signal["symbol"]

    logger.info(f"\n{'='*55}")
    logger.info(f"{'  DRY RUN — ' if dry_run else '  LIVE ORDER — '}ENTERING {symbol}")
    logger.info(f"  OCC Symbol:   {occ}")
    logger.info(f"  Limit Price:  ${price:.2f}")
    logger.info(f"  Cost:         ${price * 100:.2f}")
    logger.info(f"  Stop @ stock: ${signal['stop_price']:.2f}")
    logger.info(f"  Time stop:    {signal['time_stop']} trading days")
    logger.info(f"{'='*55}")

    order_body = build_option_order(occ, price)

    try:
        resp = client.place_order(order_body, dry_run=dry_run)
    except Exception as e:
        logger.error(f"Order failed: {e}")
        return False

    if dry_run:
        logger.info(f"DRY RUN response: {resp}")
        logger.info("  ✅ Order structure valid — would be submitted live")
        return True

    # Extract order ID from response
    order_data = resp.get("data", {}).get("order", {})
    order_id   = order_data.get("id")
    status     = order_data.get("status", "Unknown")
    logger.info(f"  Order ID: {order_id}  Status: {status}")

    # Record in state
    trade = {
        "symbol":          symbol,
        "occ_symbol":      occ,
        "order_id":        order_id,
        "entry_premium":   price,
        "entry_stock":     signal["stock_price"],
        "strike":          signal["strike"],
        "exp_date":        signal["exp_date"],
        "stop_price":      signal["stop_price"],
        "time_stop_date":  _add_trading_days(date.today(), signal["time_stop"]).isoformat(),
        "moneyness":       signal["moneyness"],
        "cost":            signal["cost"],
    }
    add_open_trade(state, trade)
    return True


def check_exits(client: TastyClient, state: dict, dry_run: bool = False):
    """
    Check all open trades for exit conditions:
      1. Stock stop loss (stock_price <= stop_price)
      2. Time stop (today >= time_stop_date)
      3. Profit target: option premium doubled (2x entry)
    """
    if not state["open_trades"]:
        return

    logger.info(f"\nChecking {len(state['open_trades'])} open trade(s) for exits...")

    trades_to_close = []

    for trade in list(state["open_trades"]):
        symbol     = trade["symbol"]
        occ        = trade["occ_symbol"]
        stop_price = trade["stop_price"]
        time_stop  = date.fromisoformat(trade["time_stop_date"])
        entry_prem = trade["entry_premium"]

        # Get current stock price
        try:
            current_stock = client.get_stock_price(symbol)
        except Exception as e:
            logger.error(f"Could not get price for {symbol}: {e}")
            continue

        # Get current option price
        try:
            quote       = client.get_option_quote(occ)
            bid         = float(quote.get("bid", 0))
            ask         = float(quote.get("ask", 0))
            current_opt = round((bid + ask) / 2, 2)
        except Exception as e:
            logger.error(f"Could not get option quote for {occ}: {e}")
            current_opt = entry_prem

        # Check exit conditions
        exit_reason = None

        if current_stock <= stop_price:
            exit_reason = f"STOCK_STOP (stock=${current_stock:.2f} <= stop=${stop_price:.2f})"

        elif date.today() >= time_stop:
            exit_reason = f"TIME_STOP ({date.today()} >= {time_stop})"

        elif current_opt >= entry_prem * 2:
            exit_reason = f"PROFIT_TARGET (opt=${current_opt:.2f} >= 2x entry=${entry_prem*2:.2f})"

        if exit_reason:
            pnl = (current_opt - entry_prem) * 100
            logger.info(f"  EXIT SIGNAL: {occ}")
            logger.info(f"    Reason:      {exit_reason}")
            logger.info(f"    Entry prem:  ${entry_prem:.2f}")
            logger.info(f"    Exit prem:   ${current_opt:.2f}")
            logger.info(f"    PnL:         ${pnl:+.2f}")
            trades_to_close.append((trade, current_opt, exit_reason))
        else:
            pnl_so_far = (current_opt - entry_prem) * 100
            logger.info(f"  HOLD: {occ}  stock=${current_stock:.2f}  "
                        f"opt=${current_opt:.2f}  pnl=${pnl_so_far:+.2f}")

    # Execute exits
    for trade, exit_price, reason in trades_to_close:
        _exit_trade(client, state, trade, exit_price, reason, dry_run)


def _exit_trade(client: TastyClient, state: dict, trade: dict,
                exit_price: float, reason: str, dry_run: bool):
    occ = trade["occ_symbol"]
    logger.info(f"\n  {'DRY RUN — ' if dry_run else ''}CLOSING {occ}  ({reason})")

    order_body = build_close_order(occ, exit_price)

    try:
        resp = client.place_order(order_body, dry_run=dry_run)
        if dry_run:
            logger.info(f"  DRY RUN: close order valid")
        else:
            order_id = resp.get("data", {}).get("order", {}).get("id")
            logger.info(f"  Close order placed: {order_id}")
    except Exception as e:
        logger.error(f"  Close order failed: {e}")
        return

    close_trade(state, occ, exit_price, reason)


def _add_trading_days(start: date, n: int) -> date:
    """Add N trading days (Mon-Fri) to a date."""
    current = start
    added   = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon=0, Fri=4
            added += 1
    return current
