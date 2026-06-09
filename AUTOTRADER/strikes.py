"""
Strike price calculation and OCC symbol builder.
OCC format: SNAP  260612C00006500
            AAPL  260612C00185000
            Symbol (6 chars padded) + YYMMDD + C/P + 8-digit strike (5 whole + 3 decimal)
"""
from datetime import date, timedelta
from decimal import Decimal


def calc_strike(stock_price: float, moneyness: str) -> Decimal:
    """
    Calculate option strike based on moneyness type.

    moneyness values:
      'otm10'      — 10% OTM call  (Phases 1-3)
      'atm'        — At the money  (Phase 4)
      'itm90delta' — ~88% of price, ITM (Phase 5 AAPL)
    """
    if moneyness == "otm10":
        raw = stock_price * 1.10
    elif moneyness == "atm":
        raw = stock_price
    elif moneyness == "itm90delta":
        raw = stock_price * 0.88
    else:
        raw = stock_price

    # Rounding increments
    if stock_price < 25:
        rounded = round(raw * 2) / 2     # $0.50 increments
    elif stock_price < 100:
        rounded = round(raw)             # $1 increments
    else:
        rounded = round(raw / 5) * 5    # $5 increments

    return Decimal(str(rounded))


def build_occ_symbol(symbol: str, exp_date: date, strike: Decimal, option_type: str = "C") -> str:
    """
    Build OCC option symbol.
    e.g. SNAP @ $6.50 call exp 2026-06-12 → 'SNAP  260612C00006500'
    """
    sym_padded  = symbol.ljust(6)
    date_str    = exp_date.strftime("%y%m%d")
    strike_int  = int(strike * 1000)
    strike_str  = str(strike_int).zfill(8)
    return f"{sym_padded}{date_str}{option_type}{strike_str}"


def find_best_expiration(expirations: list, dte_target: int = 30) -> dict:
    """Return the expiration closest to dte_target days."""
    return min(expirations, key=lambda e: abs(e["days-to-expiration"] - dte_target))


def find_nearest_strike_from_chain(strikes: list, target_strike: Decimal) -> dict:
    """From a chain strikes list, find the one closest to target_strike."""
    return min(strikes, key=lambda s: abs(Decimal(str(s["strike-price"])) - target_strike))
