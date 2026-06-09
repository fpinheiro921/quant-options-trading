"""
Central configuration for all trading phases.
Edit PHASE_CONFIG to adjust parameters per phase.
"""
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────
BASE_DIR   = Path(r"H:\02 - TRADING\OPTIONS TRADING\AUTOTRADER")
STATE_FILE = BASE_DIR / "state" / "account_state.json"
LOG_DIR    = BASE_DIR / "logs"
ENV_FILE   = BASE_DIR / ".env"

# ── API ───────────────────────────────────────────────────────
TASTYTRADE_BASE = "https://api.tastyworks.com"

# ── Phase definitions ─────────────────────────────────────────
# account_min: minimum cash balance to be IN this phase
# account_max: graduate to next phase above this
# symbols:     symbols to scan for weekly breakouts
# moneyness:   'otm10' / 'atm' / 'itm90delta'
# vix_max:     skip trade if realized-vol proxy > this
# stop_pct:    stock stop loss (negative)
# time_stop_days: exit after N trading days
# position_size: fraction of 1 contract (1.0 = full, 0.5 = half)
# max_risk_pct:  max % of account per trade (guardrail)

PHASE_CONFIG = {
    1: {
        "name":             "SNAP OTM",
        "account_min":      0,
        "account_max":      999,
        "symbols":          ["SNAP"],
        "moneyness":        "otm10",
        "vix_max":          25,
        "stop_pct":         -0.015,
        "time_stop_days":   3,
        "position_size":    1.0,
        "max_risk_pct":     0.50,   # up to 50% for tiny account
        "dte_target":       30,
    },
    2: {
        "name":             "SNAP + AAL OTM",
        "account_min":      400,
        "account_max":      1499,
        "symbols":          ["SNAP", "AAL"],
        "moneyness":        "otm10",
        "vix_max":          25,
        "stop_pct":         -0.015,
        "time_stop_days":   3,
        "position_size":    1.0,
        "max_risk_pct":     0.25,
        "dte_target":       30,
    },
    3: {
        "name":             "Top 5 OTM",
        "account_min":      1000,
        "account_max":      2999,
        "symbols":          ["SNAP", "CCL", "AAL", "M", "FSLY"],
        "moneyness":        "otm10",
        "vix_max":          25,
        "stop_pct":         -0.015,
        "time_stop_days":   3,
        "position_size":    1.0,
        "max_risk_pct":     0.20,
        "dte_target":       30,
    },
    4: {
        "name":             "Top 5 ATM",
        "account_min":      1500,
        "account_max":      4999,
        "symbols":          ["SNAP", "CCL", "AAL", "M", "FSLY"],
        "moneyness":        "atm",
        "vix_max":          25,
        "stop_pct":         -0.015,
        "time_stop_days":   3,
        "position_size":    1.0,
        "max_risk_pct":     0.15,
        "dte_target":       30,
    },
    5: {
        "name":             "AAPL ITM 90-delta",
        "account_min":      5000,
        "account_max":      999999,
        "symbols":          ["AAPL"],
        "moneyness":        "itm90delta",
        "vix_max":          20,
        "stop_pct":         -0.015,
        "time_stop_days":   3,
        "position_size":    0.5,
        "max_risk_pct":     0.10,
        "dte_target":       30,
    },
}


def get_current_phase(cash_balance: float) -> dict:
    """Return the phase config for the given account balance."""
    for phase_num in sorted(PHASE_CONFIG.keys(), reverse=True):
        if cash_balance >= PHASE_CONFIG[phase_num]["account_min"]:
            return phase_num, PHASE_CONFIG[phase_num]
    return 1, PHASE_CONFIG[1]
