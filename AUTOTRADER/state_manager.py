"""
Persistent state manager — tracks open trades, phase, and account history.
Saves to JSON file so state survives restarts.
"""
import json
import logging
from datetime import date, datetime
from pathlib import Path
from config import STATE_FILE

logger = logging.getLogger(__name__)

DEFAULT_STATE = {
    "phase":           1,
    "cash_balance":    0.0,
    "last_updated":    None,
    "open_trades":     [],   # list of active trade dicts
    "trade_history":   [],   # completed trades
    "phase_history":   [],   # phase transition log
}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as e:
            logger.warning(f"Could not load state: {e}. Using default.")
    return dict(DEFAULT_STATE)


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    logger.debug(f"State saved → {STATE_FILE}")


def add_open_trade(state: dict, trade: dict):
    """Record a new open trade."""
    trade["opened_at"] = datetime.now().isoformat()
    state["open_trades"].append(trade)
    save_state(state)
    logger.info(f"Trade recorded: {trade['symbol']} {trade['occ_symbol']} @ ${trade['entry_premium']:.2f}")


def close_trade(state: dict, occ_symbol: str, exit_premium: float, exit_reason: str):
    """Move a trade from open → history with exit info."""
    for trade in state["open_trades"]:
        if trade["occ_symbol"] == occ_symbol:
            trade["exit_premium"]  = exit_premium
            trade["exit_reason"]   = exit_reason
            trade["closed_at"]     = datetime.now().isoformat()
            trade["pnl"]           = (exit_premium - trade["entry_premium"]) * 100
            trade["pnl_pct"]       = trade["pnl"] / (trade["entry_premium"] * 100) * 100
            state["trade_history"].append(trade)
            state["open_trades"].remove(trade)
            save_state(state)
            logger.info(f"Trade closed: {occ_symbol}  PnL=${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%)  Reason={exit_reason}")
            return trade
    logger.warning(f"Could not find open trade: {occ_symbol}")
    return None


def update_balance(state: dict, new_balance: float):
    state["cash_balance"] = new_balance
    save_state(state)


def log_phase_transition(state: dict, old_phase: int, new_phase: int, balance: float):
    state["phase_history"].append({
        "from_phase": old_phase,
        "to_phase":   new_phase,
        "balance":    balance,
        "date":       date.today().isoformat(),
    })
    state["phase"] = new_phase
    save_state(state)
    logger.info(f"PHASE TRANSITION: Phase {old_phase} → Phase {new_phase}  (balance=${balance:.2f})")


def get_open_trade_for_symbol(state: dict, symbol: str) -> dict | None:
    """Return open trade for a symbol if one exists."""
    for trade in state["open_trades"]:
        if trade["symbol"] == symbol:
            return trade
    return None


def print_summary(state: dict):
    history = state["trade_history"]
    wins    = [t for t in history if t.get("pnl", 0) > 0]
    losses  = [t for t in history if t.get("pnl", 0) <= 0]
    total_pnl = sum(t.get("pnl", 0) for t in history)

    print(f"\n{'='*55}")
    print(f"  AUTOTRADER SUMMARY")
    print(f"{'='*55}")
    print(f"  Phase:         {state['phase']}")
    print(f"  Cash Balance:  ${state['cash_balance']:,.2f}")
    print(f"  Open Trades:   {len(state['open_trades'])}")
    print(f"  Total Trades:  {len(history)}")
    print(f"  Wins:          {len(wins)}  |  Losses: {len(losses)}")
    if history:
        wr = len(wins) / len(history) * 100
        print(f"  Win Rate:      {wr:.1f}%")
        print(f"  Total PnL:     ${total_pnl:.2f}")
    if state["open_trades"]:
        print(f"\n  Open Positions:")
        for t in state["open_trades"]:
            print(f"    {t['occ_symbol']:30s}  entry=${t['entry_premium']:.2f}  opened={t['opened_at'][:10]}")
    print(f"{'='*55}\n")
