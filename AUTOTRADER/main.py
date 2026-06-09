"""
AutoTrader Main Orchestrator
────────────────────────────
Runs in two modes depending on the day/time:

  MONDAY morning (9:40 AM ET):
    → scan for weekly breakout setups
    → place entry orders for signals found

  TUESDAY–FRIDAY morning (9:40 AM ET):
    → check open positions for exit conditions
    → close positions that hit stop loss, time stop, or profit target

Usage:
  python main.py                 # auto-detect mode from day of week
  python main.py --scan          # force scan + entry
  python main.py --exits         # force exit check
  python main.py --status        # print account status only
  python main.py --dry-run       # run full logic but don't place real orders

Scheduling (Task Scheduler):
  Run daily Mon–Fri at 9:40 AM Eastern time
  Command: python "H:\\QUANT TRADING\\AUTOTRADER\\main.py"
"""
import sys
import logging
from datetime import date, datetime

from notifier import setup_logging, notify, notify_entry, notify_exit, notify_phase_change
from tt_client import TastyClient
from state_manager import (
    load_state, save_state, update_balance, log_phase_transition,
    get_open_trade_for_symbol, print_summary
)
from config import get_current_phase
from scanner import scan_phase
from trader import enter_trade, check_exits

logger = logging.getLogger(__name__)


def run(dry_run: bool = False, force_scan: bool = False, force_exits: bool = False):
    setup_logging("autotrader")
    logger.info(f"\n{'='*55}")
    logger.info(f"  AUTOTRADER  —  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"{'='*55}")

    client = TastyClient()
    state  = load_state()

    # ── 1. Refresh balance and detect phase ───────────────────
    try:
        balance_data = client.get_balance()
        cash = float(balance_data.get("cash-balance", state["cash_balance"]))
    except Exception as e:
        logger.error(f"Could not fetch balance: {e}")
        cash = state["cash_balance"]

    update_balance(state, cash)
    logger.info(f"Cash balance: ${cash:,.2f}")

    # ── 2. Phase transition check ─────────────────────────────
    new_phase_num, phase_cfg = get_current_phase(cash)
    old_phase_num = state.get("phase", 1)

    if new_phase_num != old_phase_num:
        notify_phase_change(old_phase_num, new_phase_num, cash)
        log_phase_transition(state, old_phase_num, new_phase_num, cash)
    else:
        state["phase"] = new_phase_num
        save_state(state)

    logger.info(f"Active phase: {new_phase_num} — {phase_cfg['name']}")

    # ── 3. Determine run mode ─────────────────────────────────
    today     = date.today()
    weekday   = today.weekday()  # 0=Mon, 4=Fri
    is_monday = weekday == 0

    do_scan  = force_scan or is_monday
    do_exits = force_exits or (not is_monday)

    # --- 4. EXIT CHECK (Tue–Fri or forced) ---------------------
    if do_exits:
        logger.info("\n--- EXIT CHECK ---")
        check_exits(client, state, dry_run=dry_run)

    # --- 5. ENTRY SCAN (Monday or forced) ----------------------
    if do_scan:
        logger.info("\n--- ENTRY SCAN ---")

        # Don't enter new trades if we already have one per symbol
        symbols_with_open_trade = {t["symbol"] for t in state["open_trades"]}
        available_symbols = [
            s for s in phase_cfg["symbols"]
            if s not in symbols_with_open_trade
        ]

        if not available_symbols:
            logger.info("All symbols already have open trades — skipping scan")
        else:
            # Temporarily filter phase config to available symbols
            filtered_cfg = {**phase_cfg, "symbols": available_symbols}
            signals = scan_phase(client, filtered_cfg, cash)

            if not signals:
                logger.info("No breakout signals found this week")
                notify("AutoTrader: No signals", f"Scanned {phase_cfg['name']} — no breakouts found for {today}")
            else:
                for signal in signals:
                    success = enter_trade(client, state, signal, dry_run=dry_run)
                    if success and not dry_run:
                        notify_entry(signal)

    # ── 6. Print summary ─────────────────────────────────────
    print_summary(state)


if __name__ == "__main__":
    dry_run     = "--dry-run" in sys.argv
    force_scan  = "--scan"    in sys.argv
    force_exits = "--exits"   in sys.argv

    if "--status" in sys.argv:
        setup_logging("status")
        state = load_state()
        print_summary(state)
        # Also show live balance
        try:
            client = TastyClient()
            bal    = client.get_balance()
            cash   = float(bal.get("cash-balance", 0))
            print(f"Live balance from API: ${cash:,.2f}")
        except Exception as e:
            print(f"Could not fetch live balance: {e}")
    else:
        run(dry_run=dry_run, force_scan=force_scan, force_exits=force_exits)
