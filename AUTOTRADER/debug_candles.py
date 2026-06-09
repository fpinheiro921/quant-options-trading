"""Debug script — prints raw DXLink messages to see actual COMPACT format."""
import json
import asyncio
import time
import websockets
import os
from pathlib import Path

env_file = Path(r'H:\QUANT TRADING\STRATEGY_COMBINATIONS\.env')
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

import requests
CLIENT_SECRET = os.getenv('TASTYTRADE_CLIENT_SECRET')
REFRESH_TOKEN = os.getenv('TASTYTRADE_REFRESH_TOKEN')

resp = requests.post('https://api.tastyworks.com/oauth/token',
    data={'grant_type': 'refresh_token', 'refresh_token': REFRESH_TOKEN, 'client_secret': CLIENT_SECRET},
    headers={'Content-Type': 'application/x-www-form-urlencoded'})
access_token = resp.json()['access_token']

resp2 = requests.get('https://api.tastyworks.com/api-quote-tokens',
    headers={'Authorization': f'Bearer {access_token}', 'User-Agent': 'debug/1.0'})
quote_token = resp2.json()['data']['token']
print(f"Quote token: {quote_token[:30]}...")

from datetime import datetime, timedelta, timezone
from_time_ms = int((datetime.now(timezone.utc) - timedelta(days=14)).timestamp() * 1000)
print(f"From time: {from_time_ms}  ({datetime.fromtimestamp(from_time_ms/1000)})")

async def debug():
    async with websockets.connect("wss://tasty-openapi-ws.dxfeed.com/realtime", ping_interval=20) as ws:
        await ws.send(json.dumps({"type":"SETUP","channel":0,"version":"0.1-DXF-JS/0.3.0","keepaliveTimeout":60,"acceptKeepaliveTimeout":60}))

        authorized = False
        channel_open = False
        msg_count = 0

        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3)
            except asyncio.TimeoutError:
                if channel_open:
                    print("\nNo more messages — done")
                    break
                continue

            msg = json.loads(raw)
            print(f"\n[MSG {msg_count}] type={msg.get('type')}  channel={msg.get('channel')}")

            if msg.get('type') == 'AUTH_STATE' and msg.get('state') == 'UNAUTHORIZED':
                await ws.send(json.dumps({"type":"AUTH","channel":0,"token": quote_token}))
                print("  -> Sent AUTH")

            elif msg.get('type') == 'AUTH_STATE' and msg.get('state') == 'AUTHORIZED':
                authorized = True
                print("  -> Authorized!")
                await ws.send(json.dumps({"type":"CHANNEL_REQUEST","channel":1,"service":"FEED","parameters":{"contract":"AUTO"}}))
                print("  -> Sent CHANNEL_REQUEST")

            elif msg.get('type') == 'CHANNEL_OPENED':
                channel_open = True
                print("  -> Channel opened!")
                await ws.send(json.dumps({"type":"FEED_SETUP","channel":1,"acceptAggregationPeriod":10,"acceptDataFormat":"COMPACT","acceptEventFields":{"Candle":["eventType","eventSymbol","time","openPrice","highPrice","lowPrice","closePrice","volume"]}}))
                print("  -> Sent FEED_SETUP")
                await ws.send(json.dumps({"type":"FEED_SUBSCRIPTION","channel":1,"reset":True,"add":[{"type":"Candle","symbol":"SNAP{=1d}","fromTime":from_time_ms}]}))
                print("  -> Sent FEED_SUBSCRIPTION for SNAP{=1d}")

            elif msg.get('type') == 'FEED_DATA':
                data = msg.get('data', [])
                print(f"  FEED_DATA len={len(data)}")
                print(f"  RAW DATA: {json.dumps(data)[:500]}")

            elif msg.get('type') == 'KEEPALIVE':
                await ws.send(json.dumps({"type":"KEEPALIVE","channel":0}))

            msg_count += 1
            if msg_count > 20:
                break

asyncio.run(debug())
