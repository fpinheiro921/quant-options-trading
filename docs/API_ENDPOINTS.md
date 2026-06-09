# Quant Trading System - API Endpoints

Complete reference for all REST API endpoints available in the dashboard.

## Base URL
```
http://localhost:5000
```

---

## 📊 Account & Status

### Get System Status
```http
GET /api/status
```
Returns authentication status and system health.

**Response:**
```json
{
  "authenticated": true,
  "timestamp": "2026-05-10T16:30:00"
}
```

---

## 💰 Paper Trading

### Get Paper Trading Status
```http
GET /api/paper/status
```
Returns paper trading account summary and mode information.

**Response:**
```json
{
  "cash_balance": 100000.00,
  "total_pnl": 0.00,
  "total_trades": 0,
  "win_rate": 0.0,
  "open_positions": [],
  "recent_trades": [],
  "trading_mode": "paper",
  "is_paper": true,
  "is_sandbox": false,
  "is_live": false
}
```

### Reset Paper Account
```http
POST /api/paper/reset
```
Resets paper trading account to starting balance ($100,000).

**Response:**
```json
{
  "success": true,
  "message": "Account reset to $100,000.00",
  "cash_balance": 100000.00
}
```

### Get Paper Trading History
```http
GET /api/paper/trades
```
Returns all paper trading trades.

**Response:**
```json
{
  "trades": [
    {
      "id": "uuid",
      "timestamp": "2026-05-10T14:30:00",
      "symbol": "NVDA",
      "action": "buy",
      "quantity": 100,
      "price": 150.00,
      "realized_pnl": 0.00,
      "is_open": false,
      "strategy": "momentum_breakout"
    }
  ],
  "total_count": 1
}
```

### Get Paper Trading Positions
```http
GET /api/paper/positions
```
Returns current open positions in paper account.

**Response:**
```json
{
  "positions": [
    {
      "symbol": "NVDA",
      "quantity": 100,
      "trade_type": "stock",
      "entry_price": 150.00,
      "current_price": 155.00,
      "unrealized_pnl": 500.00
    }
  ],
  "count": 1
}
```

---

## 📈 Backtesting

### Run Backtest
```http
POST /api/backtest/run
Content-Type: application/json

{
  "symbol": "NVDA",
  "days": 30,
  "strategy": "momentum"
}
```

Runs a backtest for the specified symbol and strategy.

**Parameters:**
- `symbol` (required): Stock symbol (e.g., "NVDA")
- `days` (optional): Lookback period in days (default: 30)
- `strategy` (optional): "wheel" or "momentum" (default: "momentum")

**Response:**
```json
{
  "success": true,
  "strategy": "Compra a Seco (Momentum Breakout)",
  "symbol": "NVDA",
  "period": {
    "start": "2026-04-10T00:00:00",
    "end": "2026-05-10T00:00:00",
    "days": 30
  },
  "performance": {
    "initial_capital": 100000.00,
    "final_capital": 105000.00,
    "total_return_pct": 5.00,
    "total_trades": 10,
    "winning_trades": 6,
    "losing_trades": 4,
    "win_rate": 0.60,
    "avg_trade_return": 500.00,
    "max_drawdown_pct": 2.50,
    "sharpe_ratio": 1.50
  },
  "trades": [
    {
      "timestamp": "2026-04-15T10:00:00",
      "symbol": "NVDA",
      "action": "buy",
      "quantity": 100,
      "price": 150.00,
      "realized_pnl": 0.00,
      "strategy": "momentum_breakout"
    }
  ]
}
```

### Get Backtest History
```http
GET /api/backtest/history
```
Returns list of recent backtests (currently not persisted).

**Response:**
```json
{
  "backtests": [],
  "message": "Backtest history persistence not yet implemented"
}
```

---

## 🎯 Wheel Strategy

### Get Wheel Strategy Status
```http
GET /api/wheel/status
```
Returns current wheel strategy state and recommendations.

**Response:**
```json
{
  "has_uncovered_positions": false,
  "covered_calls": [],
  "cash_secured_puts": [],
  "recommendations": [
    {
      "symbol": "NVDA",
      "action": "sell_cash_secured_put",
      "strike": 140.00,
      "premium": 2.50,
      "dte": 7,
      "delta": 0.30
    }
  ]
}
```

### Get Symbol Analysis
```http
GET /api/wheel/analyze/<symbol>
```
Returns detailed analysis for a symbol including option chain.

**Example:** `GET /api/wheel/analyze/NVDA`

**Response:**
```json
{
  "symbol": "NVDA",
  "price": 150.00,
  "option_chain": {
    "expirations": ["2026-05-17", "2026-05-24"],
    "strikes": [140, 145, 150, 155, 160]
  },
  "recommendations": []
}
```

### Get Risk Analysis
```http
GET /api/wheel/risk
```
Returns portfolio risk metrics.

**Response:**
```json
{
  "portfolio_value": 100000.00,
  "total_delta_exposure": 0.00,
  "cash_needed_for_assignments": 0.00,
  "margin_utilization": 0.00,
  "max_position_size_pct": 20.00
}
```

---

## 🚀 Momentum Breakout (Compra a Seco)

### Get Momentum Strategy Status
```http
GET /api/momentum/status
```
Returns momentum strategy status and parameters.

**Response:**
```json
{
  "state": "scanning",
  "watchlist": ["NVDA", "AAPL", "TSLA", "MSFT", "AMD"],
  "active_setups": 0,
  "active_trades": 0
}
```

### Get Watchlist
```http
GET /api/momentum/watchlist
```
Returns current watchlist.

**Response:**
```json
{
  "watchlist": ["NVDA", "AAPL", "TSLA", "MSFT", "AMD"],
  "default": ["NVDA", "AAPL", "TSLA", "MSFT", "AMD", "META", "GOOGL", "AMZN"]
}
```

### Update Watchlist
```http
POST /api/momentum/watchlist
Content-Type: application/json

{
  "symbols": ["NVDA", "AAPL", "TSLA"]
}
```

**Response:**
```json
{
  "success": true,
  "watchlist": ["NVDA", "AAPL", "TSLA"]
}
```

### Scan Symbol for Setups
```http
GET /api/momentum/setups/<symbol>
```
Scans a symbol for Compra a Seco setups using historical data.

**Example:** `GET /api/momentum/setups/NVDA`

**Response:**
```json
{
  "symbol": "NVDA",
  "setups_found": 2,
  "setups": [
    {
      "symbol": "NVDA",
      "propulsion_candle": {
        "open": 148.00,
        "high": 152.00,
        "low": 147.50,
        "close": 151.00,
        "timestamp": "2026-05-10T10:00:00"
      },
      "pin_bar_candle": {
        "open": 151.00,
        "high": 151.50,
        "low": 150.50,
        "close": 151.20,
        "timestamp": "2026-05-10T12:00:00"
      },
      "entry_price": 151.50,
      "target_price": 159.50,
      "breakout_price": 151.50,
      "detected_at": "2026-05-10T12:00:00",
      "ema_status": {
        "is_bull_run": true,
        "ema8": 148.50,
        "ema80": 140.00
      }
    }
  ],
  "active_setups": []
}
```

### Get Performance Metrics
```http
GET /api/momentum/performance
```
Returns strategy performance metrics.

**Response:**
```json
{
  "total_trades": 0,
  "win_rate": 0.0,
  "avg_profit": 0.0,
  "avg_loss": 0.0,
  "profit_factor": 0.0,
  "max_drawdown": 0.0
}
```

### Get Trades
```http
GET /api/momentum/trades
```
Returns active and historical trades.

**Response:**
```json
{
  "active_trades": [],
  "trade_history": []
}
```

---

## 🔌 WebSocket Events

### Connection Events
- `connect` - Client connected
- `disconnect` - Client disconnected

### Quote Streaming
```javascript
// Subscribe to quotes
socket.emit('subscribe_quotes', { symbols: ['NVDA', 'AAPL'] });

// Receive updates
socket.on('quote_update', (data) => {
  console.log(data); // { symbol: 'NVDA', price: 150.00, ... }
});
```

### Account Updates
```javascript
// Subscribe to account updates
socket.emit('subscribe_account');

// Receive updates
socket.on('account_update', (data) => {
  console.log(data); // Account balance, positions, etc.
});
```

---

## 📋 Trading Modes

The system supports 3 trading modes configured via `TRADING_MODE` in `.env`:

| Mode | API Endpoint | Description |
|------|--------------|-------------|
| `paper` | `/api/paper/*` | Local simulation, no real orders |
| `sandbox` | `/api/paper/*` | TastyTrade test environment, 15-min delayed quotes |
| `live` | Live API | Real money trading |

**Check current mode:**
```http
GET /api/paper/status
```

**Response:**
```json
{
  "trading_mode": "paper",
  "is_paper": true,
  "is_sandbox": false,
  "is_live": false
}
```

---

## 🧪 Testing Examples

### Test Paper Trading
```bash
# Check paper account
curl http://localhost:5000/api/paper/status

# Reset account
curl -X POST http://localhost:5000/api/paper/reset

# View trades
curl http://localhost:5000/api/paper/trades

# View positions
curl http://localhost:5000/api/paper/positions
```

### Run Backtest
```bash
curl -X POST http://localhost:5000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NVDA", "days": 30, "strategy": "momentum"}'
```

### Scan for Setups
```bash
curl http://localhost:5000/api/momentum/setups/NVDA
```

---

## ⚠️ Error Responses

All errors return appropriate HTTP status codes:

```json
{
  "error": "Description of the error"
}
```

**Common Status Codes:**
- `400` - Bad Request (missing parameters)
- `401` - Unauthorized (not authenticated)
- `500` - Internal Server Error

---

## 📚 Additional Resources

- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing & backtesting guide
- [TASTYTRADE_API_INFO.md](TASTYTRADE_API_INFO.md) - Official API documentation
- [README.md](README.md) - System overview

---

**Last Updated:** May 2026
**Version:** 1.0
