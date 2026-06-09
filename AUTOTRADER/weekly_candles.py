"""
Weekly candle fetcher via DXLink WebSocket.
Pulls 3 weeks of daily candles (AAPL{=1d}) and aggregates to weekly OHLC.

Breakout condition (correct strategy definition):
  Current week's close > Previous week's HIGH

This replaces the prev_close proxy used in scanner.py.
"""
import json
import time
import asyncio
import logging
import websockets
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

DXLINK_URL = "wss://tasty-openapi-ws.dxfeed.com/realtime"


async def fetch_daily_candles(symbol: str, quote_token: str, days_back: int = 21) -> list[dict]:
    """
    Fetch daily candles for a symbol via DXLink WebSocket.
    Returns list of dicts: {date, open, high, low, close}
    sorted oldest → newest.
    """
    from_time_ms = int((datetime.now(timezone.utc) - timedelta(days=days_back)).timestamp() * 1000)
    candle_symbol = f"{symbol}{{=1d}}"
    candles = {}

    async with websockets.connect(DXLINK_URL, ping_interval=20) as ws:
        # 1. SETUP
        await ws.send(json.dumps({
            "type": "SETUP", "channel": 0,
            "version": "0.1-DXF-JS/0.3.0",
            "keepaliveTimeout": 60,
            "acceptKeepaliveTimeout": 60
        }))

        # 2. Wait for AUTH_STATE UNAUTHORIZED then send token
        deadline = time.time() + 15
        while time.time() < deadline:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            if msg.get("type") == "AUTH_STATE" and msg.get("state") == "UNAUTHORIZED":
                await ws.send(json.dumps({
                    "type": "AUTH", "channel": 0, "token": quote_token
                }))
            elif msg.get("type") == "AUTH_STATE" and msg.get("state") == "AUTHORIZED":
                break

        # 3. CHANNEL_REQUEST
        await ws.send(json.dumps({
            "type": "CHANNEL_REQUEST", "channel": 1,
            "service": "FEED",
            "parameters": {"contract": "AUTO"}
        }))

        # wait for CHANNEL_OPENED
        deadline = time.time() + 10
        while time.time() < deadline:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            if msg.get("type") == "CHANNEL_OPENED":
                break

        # 4. FEED_SETUP — request Candle fields
        # Field names confirmed from live DXLink response: open/high/low/close (not openPrice etc)
        await ws.send(json.dumps({
            "type": "FEED_SETUP", "channel": 1,
            "acceptAggregationPeriod": 10,
            "acceptDataFormat": "COMPACT",
            "acceptEventFields": {
                "Candle": ["eventSymbol", "time", "open", "high", "low", "close", "volume"]
            }
        }))

        # 5. FEED_SUBSCRIPTION — candle events
        await ws.send(json.dumps({
            "type": "FEED_SUBSCRIPTION", "channel": 1,
            "reset": True,
            "add": [{"type": "Candle", "symbol": candle_symbol, "fromTime": from_time_ms}]
        }))

        # 6. Collect candle events until stream quiets (2s silence = done)
        #
        # Actual COMPACT format from DXLink (observed):
        # data = ["Candle", [flat_array]]
        # flat_array = ["Candle", symbol, time, open, high, low, close, vol,
        #               "Candle", symbol, time, open, high, low, close, vol, ...]
        # i.e. "Candle" string is repeated as a type marker inside the flat array.
        # Fields after each "Candle" marker (excluding eventType itself):
        #   eventSymbol, time, openPrice, highPrice, lowPrice, closePrice, volume  → 7 values
        # BUT DXLink may only return fields it has data for; we parse by marker.

        deadline = time.time() + 20

        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                break

            msg = json.loads(raw)

            if msg.get("type") in ("FEED_CONFIG", "SETUP"):
                continue

            if msg.get("type") == "FEED_DATA" and msg.get("channel") == 1:
                data = msg.get("data", [])
                # Format: ["Candle", [sym, time, o, h, l, c, vol, sym, time, o, h, l, c, vol, ...]]
                # 7 values per record, no inner type marker — just the flat sequence
                if len(data) == 2 and data[0] == "Candle" and isinstance(data[1], list):
                    flat = data[1]
                    N = 7  # eventSymbol, time, open, high, low, close, volume
                    i = 0
                    while i + N <= len(flat):
                        chunk = flat[i:i + N]
                        try:
                            ts = chunk[1]
                            o  = chunk[2]
                            h  = chunk[3]
                            l  = chunk[4]
                            cl = chunk[5]
                            if (ts and ts > 0
                                    and cl not in (None, "NaN")
                                    and float(cl) > 0):
                                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).date()
                                candles[dt] = {
                                    "date":  dt,
                                    "open":  float(o  or 0),
                                    "high":  float(h  or 0),
                                    "low":   float(l  or 0),
                                    "close": float(cl),
                                }
                        except Exception:
                            pass
                        i += N

            if msg.get("type") == "KEEPALIVE":
                await ws.send(json.dumps({"type": "KEEPALIVE", "channel": 0}))

    result = sorted(candles.values(), key=lambda x: x["date"])
    logger.debug(f"  {symbol}: fetched {len(result)} daily candles")
    return result


def aggregate_to_weekly(daily_candles: list[dict]) -> list[dict]:
    """
    Aggregate daily OHLC candles into weekly candles (Mon–Fri weeks).
    Returns list of weekly dicts: {week_start, open, high, low, close}
    sorted oldest → newest.
    """
    from collections import defaultdict

    weeks = defaultdict(list)
    for c in daily_candles:
        # ISO week Monday as key
        d = c["date"]
        week_start = d - timedelta(days=d.weekday())
        weeks[week_start].append(c)

    weekly = []
    for week_start, days in sorted(weeks.items()):
        days_sorted = sorted(days, key=lambda x: x["date"])
        weekly.append({
            "week_start": week_start,
            "open":       days_sorted[0]["open"],
            "high":       max(d["high"]  for d in days_sorted),
            "low":        min(d["low"]   for d in days_sorted),
            "close":      days_sorted[-1]["close"],
        })

    return weekly


def is_weekly_breakout_proper(weekly_candles: list[dict]) -> tuple[bool, dict]:
    """
    TRUE breakout condition:
      This week's price > PREVIOUS week's HIGH

    Requires at least 2 complete weeks of data.
    Returns (is_breakout, info_dict)
    """
    if len(weekly_candles) < 2:
        return False, {}

    # Last full week = second to last (last may be current incomplete week)
    prev_week    = weekly_candles[-2]
    current_week = weekly_candles[-1]

    prev_high     = prev_week["high"]
    current_close = current_week["close"]
    pct_above     = (current_close - prev_high) / prev_high * 100

    is_breakout = current_close > prev_high

    info = {
        "prev_week_high":  prev_high,
        "prev_week_start": str(prev_week["week_start"]),
        "current_close":   current_close,
        "pct_above_high":  pct_above,
    }

    flag = "[BREAKOUT above prev week HIGH]" if is_breakout else "[no signal]"
    logger.info(
        f"  Breakout check: current=${current_close:.2f}  "
        f"prev_week_high=${prev_high:.2f}  "
        f"diff={pct_above:+.1f}%  {flag}"
    )

    return is_breakout, info


async def get_weekly_breakout_signal(symbol: str, quote_token: str) -> tuple[bool, dict]:
    """
    Full pipeline: fetch candles → aggregate weekly → check breakout.
    Returns (is_breakout, info_dict)
    """
    daily   = await fetch_daily_candles(symbol, quote_token, days_back=21)
    if len(daily) < 5:
        logger.warning(f"  {symbol}: not enough candle data ({len(daily)} days)")
        return False, {}

    weekly  = aggregate_to_weekly(daily)
    return is_weekly_breakout_proper(weekly)
