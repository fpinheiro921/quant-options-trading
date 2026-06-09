"""
Tastytrade API client — handles auth, token refresh, all API calls.
"""
import os
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from config import ENV_FILE, TASTYTRADE_BASE

logger = logging.getLogger(__name__)


def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()


class TastyClient:
    """Lightweight Tastytrade REST client with auto token refresh."""

    def __init__(self):
        self.client_secret  = os.getenv('TASTYTRADE_CLIENT_SECRET')
        self.refresh_token  = os.getenv('TASTYTRADE_REFRESH_TOKEN')
        self.account_number = os.getenv('TASTYTRADE_ACCOUNT', '5WI61022')
        self._access_token  = None
        self._token_expiry  = None

    def _get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        now = datetime.utcnow()
        if self._access_token and self._token_expiry and now < self._token_expiry:
            return self._access_token

        resp = requests.post(
            f"{TASTYTRADE_BASE}/oauth/token",
            data={
                "grant_type":    "refresh_token",
                "refresh_token": self.refresh_token,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expiry = now + timedelta(seconds=data.get("expires_in", 900) - 30)
        logger.debug("Token refreshed, expires in ~15 min")
        return self._access_token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type":  "application/json",
            "User-Agent":    "fpinheiro921-autotrader/1.0",
        }

    def get(self, path: str, params: dict = None) -> dict:
        resp = requests.get(f"{TASTYTRADE_BASE}{path}", headers=self._headers(),
                            params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def post(self, path: str, body: dict) -> dict:
        resp = requests.post(f"{TASTYTRADE_BASE}{path}", headers=self._headers(),
                             json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def delete(self, path: str) -> dict:
        resp = requests.delete(f"{TASTYTRADE_BASE}{path}", headers=self._headers(),
                               timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── Account ───────────────────────────────────────────────
    def get_balance(self) -> dict:
        data = self.get(f"/accounts/{self.account_number}/balances/USD")
        return data["data"]

    def get_positions(self) -> list:
        data = self.get(f"/accounts/{self.account_number}/positions")
        return data["data"]["items"]

    def get_live_orders(self) -> list:
        data = self.get(f"/accounts/{self.account_number}/orders/live")
        return data["data"]["items"]

    # ── Market data ───────────────────────────────────────────
    def get_stock_price(self, symbol: str) -> float:
        data = self.get("/market-data/by-type", params={"equity": symbol})
        items = data["data"]["items"]
        if not items:
            raise ValueError(f"No market data for {symbol}")
        return float(items[0]["mark"])

    def get_option_quote(self, occ_symbol: str) -> dict:
        data = self.get("/market-data/by-type", params={"equity-option": occ_symbol})
        items = data["data"]["items"]
        if not items:
            return {}
        return items[0]

    def get_quote_token(self) -> str:
        """Get a DXLink streaming quote token (valid 24h)."""
        data = self.get("/api-quote-tokens")
        return data["data"]["token"]

    def get_option_chain(self, symbol: str) -> list:
        data = self.get(f"/option-chains/{symbol}/nested")
        return data["data"]["items"][0]["expirations"]

    def get_weekly_candles(self, symbol: str, n_weeks: int = 3) -> list:
        """Get last N weekly OHLC candles via market data."""
        data = self.get("/market-data/by-type", params={"equity": symbol})
        items = data["data"]["items"]
        if not items:
            return []
        d = items[0]
        return [{
            "symbol":    symbol,
            "open":      float(d.get("open", 0)),
            "high":      float(d.get("day-high-price", 0)),
            "low":       float(d.get("day-low-price", 0)),
            "close":     float(d.get("mark", 0)),
            "prev_close": float(d.get("prev-close", 0)),
            "year_high":  float(d.get("year-high-price", 0)),
        }]

    # ── Orders ────────────────────────────────────────────────
    def place_order(self, order_body: dict, dry_run: bool = False) -> dict:
        path = f"/accounts/{self.account_number}/orders"
        if dry_run:
            path += "/dry-run"
        return self.post(path, order_body)

    def cancel_order(self, order_id: str) -> dict:
        return self.delete(f"/accounts/{self.account_number}/orders/{order_id}")
