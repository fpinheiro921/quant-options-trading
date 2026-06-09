"""
Flask Dashboard for the Quant Options Trading System.
Provides real-time visualization of positions and the Wheel Strategy.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

from api.tastytrade_client import TastyTradeClient
from trading.strike_resolver import StrikeResolver
from trading.wheel_strategy import WheelStrategy
from trading.momentum_breakout import CompraASecoStrategy, create_default_watchlist
from backtest.paper_trading import PaperTradingEnvironment, create_paper_environment
from backtest.backtest_engine import (
    WheelStrategyBacktester,
    MomentumBreakoutBacktester,
    BacktestResult
)
from config import Config, TradingConfig, TradingMode

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'quant-wheel-strategy-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global clients
client: TastyTradeClient = None
resolver: StrikeResolver = None
wheel_strategy: WheelStrategy = None
momentum_strategy: CompraASecoStrategy = None
paper_env: PaperTradingEnvironment = None


def init_clients():
    """Initialize API clients."""
    global client, resolver, wheel_strategy, momentum_strategy
    
    if Config.TASTYTRADE_USERNAME and Config.TASTYTRADE_PASSWORD:
        client = TastyTradeClient(
            Config.TASTYTRADE_USERNAME,
            Config.TASTYTRADE_PASSWORD
        )
        
        if client.authenticate(Config.TASTYTRADE_ACCOUNT_ID):
            resolver = StrikeResolver(client)
            wheel_strategy = WheelStrategy(client, resolver)
            momentum_strategy = CompraASecoStrategy(client)
            
            # Initialize paper trading environment
            global paper_env
            paper_env = create_paper_environment(Config.PAPER_STARTING_BALANCE)
            logger.info("Paper trading environment initialized")
            # Add default tech stock watchlist
            momentum_strategy.add_to_watchlist(create_default_watchlist())
            logger.info("Clients initialized successfully")
        else:
            logger.error("Authentication failed")
    else:
        logger.warning("No credentials configured")


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/account')
def get_account_info():
    """Get account information."""
    if not client:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        balance = client.get_account_balance()
        return jsonify(balance)
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/positions')
def get_positions():
    """Get all portfolio positions."""
    if not client:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        positions = client.get_portfolio_positions()
        return jsonify({'positions': positions})
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wheel/status')
def get_wheel_status():
    """Get wheel strategy status."""
    if not wheel_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        status = wheel_strategy.get_wheel_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting wheel status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wheel/analyze/<symbol>')
def analyze_symbol(symbol):
    """Analyze a specific symbol for wheel strategy."""
    if not wheel_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        analysis = wheel_strategy.analyze_position(symbol)
        return jsonify(analysis.to_dict())
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wheel/recommendations/<symbol>')
def get_recommendations(symbol):
    """Get trade recommendations for a symbol."""
    if not wheel_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        recommendations = wheel_strategy.generate_recommendations(symbol)
        return jsonify({
            'symbol': symbol,
            'recommendations': [r.to_dict() for r in recommendations]
        })
    except Exception as e:
        logger.error(f"Error getting recommendations for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/options/chain/<symbol>')
def get_option_chain(symbol):
    """Get option chain for a symbol."""
    if not resolver:
        return jsonify({'error': 'Resolver not initialized'}), 401
    
    target_delta = float(request.args.get('delta', Config.DEFAULT_DELTA_THRESHOLD))
    max_maturities = int(request.args.get('maturities', 3))
    option_type = request.args.get('type', 'both')
    
    try:
        results = resolver.resolve_strikes(
            symbol=symbol,
            target_delta=target_delta,
            option_type=option_type,
            max_maturities=max_maturities
        )
        
        # Convert to serializable format
        serializable = {}
        for expiry, data in results.items():
            key = expiry.strftime('%Y-%m-%d')
            serializable[key] = {
                'calls': [c.to_dict() for c in data['calls']],
                'puts': [c.to_dict() for c in data['puts']]
            }
        
        return jsonify(serializable)
    except Exception as e:
        logger.error(f"Error getting option chain for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/quote/<symbol>')
def get_quote(symbol):
    """Get real-time quote for a symbol."""
    if not client:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        quote = client.get_stock_quote(symbol)
        return jsonify(quote)
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/trade/execute', methods=['POST'])
def execute_trade():
    """Execute a trade."""
    if not strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    data = request.get_json()
    symbol = data.get('symbol')
    action = data.get('action')
    option_symbol = data.get('option_symbol')
    quantity = data.get('quantity', 1)
    price = data.get('price')
    
    try:
        # This is a simplified execution - in production, use full TradeRecommendation
        order = client.place_option_order(
            option_symbol=option_symbol,
            quantity=quantity,
            action=action,
            price=price
        )
        
        return jsonify({
            'success': True,
            'order_id': order.id if order else None
        })
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/orders')
def get_orders():
    """Get open orders."""
    if not client:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        orders = client.get_open_orders()
        return jsonify({
            'orders': [
                {
                    'id': o.id,
                    'status': o.status.value if hasattr(o.status, 'value') else str(o.status),
                    'type': o.order_type.value if hasattr(o.order_type, 'value') else str(o.order_type),
                }
                for o in orders
            ]
        })
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500


# Momentum Breakout (Compra a Seco) API Endpoints
@app.route('/api/momentum/status')
def get_momentum_status():
    """Get Compra a Seco momentum breakout strategy status."""
    if not momentum_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        status = momentum_strategy.get_strategy_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting momentum status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/momentum/watchlist', methods=['GET', 'POST'])
def momentum_watchlist():
    """Get or update momentum strategy watchlist."""
    if not momentum_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    if request.method == 'POST':
        data = request.get_json()
        symbols = data.get('symbols', [])
        if symbols:
            momentum_strategy.add_to_watchlist(symbols)
            return jsonify({'success': True, 'watchlist': momentum_strategy.watchlist})
    
    return jsonify({
        'watchlist': momentum_strategy.watchlist,
        'default': create_default_watchlist()
    })


@app.route('/api/momentum/setups/<symbol>')
def get_momentum_setups(symbol):
    """Get detected setups for a symbol using TastyTrade API."""
    if not momentum_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        # Scan for setups using TastyTrade API historical data
        setups = momentum_strategy.scan_symbol(symbol.upper(), lookback_days=30)
        
        return jsonify({
            'symbol': symbol.upper(),
            'setups_found': len(setups),
            'setups': [setup.to_dict() for setup in setups],
            'active_setups': momentum_strategy.get_active_setups_summary()
        })
    except Exception as e:
        logger.error(f"Error getting setups for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/momentum/performance')
def get_momentum_performance():
    """Get strategy performance metrics."""
    if not momentum_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        performance = momentum_strategy.calculate_performance()
        return jsonify(performance.to_dict())
    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/momentum/trades')
def get_momentum_trades():
    """Get active and historical trades."""
    if not momentum_strategy:
        return jsonify({'error': 'Strategy not initialized'}), 401
    
    try:
        return jsonify({
            'active_trades': momentum_strategy.get_active_trades_summary(),
            'trade_history': momentum_strategy.get_trade_history_summary()
        })
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'error': str(e)}), 500


# WebSocket events for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info('Client connected')
    emit('connected', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info('Client disconnected')


# Paper Trading API Endpoints
@app.route('/api/paper/status')
def get_paper_status():
    """Get paper trading account status."""
    global paper_env
    
    if not paper_env:
        paper_env = create_paper_environment(Config.PAPER_STARTING_BALANCE)
    
    try:
        summary = paper_env.get_account_summary()
        summary['trading_mode'] = Config.TRADING_MODE
        summary['is_paper'] = Config.TRADING_MODE == TradingMode.PAPER
        summary['is_sandbox'] = Config.TRADING_MODE == TradingMode.SANDBOX
        summary['is_live'] = Config.TRADING_MODE == TradingMode.LIVE
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting paper status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper/reset', methods=['POST'])
def reset_paper_account():
    """Reset paper trading account to starting balance."""
    global paper_env
    
    try:
        paper_env = create_paper_environment(Config.PAPER_STARTING_BALANCE)
        paper_env.save_account()
        return jsonify({
            'success': True,
            'message': f'Account reset to ${Config.PAPER_STARTING_BALANCE:,.2f}',
            'cash_balance': paper_env.account.cash_balance
        })
    except Exception as e:
        logger.error(f"Error resetting paper account: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper/trades')
def get_paper_trades():
    """Get paper trading trade history."""
    global paper_env
    
    if not paper_env:
        paper_env = create_paper_environment(Config.PAPER_STARTING_BALANCE)
    
    try:
        trades = []
        for trade in paper_env.account.trades:
            trades.append({
                'id': trade.id,
                'timestamp': trade.timestamp.isoformat() if hasattr(trade.timestamp, 'isoformat') else str(trade.timestamp),
                'symbol': trade.symbol,
                'action': trade.action.value,
                'quantity': trade.quantity,
                'price': trade.price,
                'realized_pnl': trade.realized_pnl,
                'is_open': trade.is_open,
                'strategy': trade.strategy
            })
        
        return jsonify({
            'trades': trades,
            'total_count': len(trades)
        })
    except Exception as e:
        logger.error(f"Error getting paper trades: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/paper/positions')
def get_paper_positions():
    """Get paper trading open positions."""
    global paper_env
    
    if not paper_env:
        paper_env = create_paper_environment(Config.PAPER_STARTING_BALANCE)
    
    try:
        positions = paper_env.get_positions()
        return jsonify({
            'positions': positions,
            'count': len(positions)
        })
    except Exception as e:
        logger.error(f"Error getting paper positions: {e}")
        return jsonify({'error': str(e)}), 500


# Backtest API Endpoints
@app.route('/api/backtest/run', methods=['POST'])
def run_backtest():
    """Run a backtest for a symbol and strategy."""
    global client, paper_env
    
    if not client:
        return jsonify({'error': 'API client not initialized'}), 401
    
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        days = int(data.get('days', 30))
        strategy_type = data.get('strategy', 'momentum')  # 'wheel' or 'momentum'
        
        if not symbol:
            return jsonify({'error': 'Symbol required'}), 400
        
        # Initialize paper environment
        if not paper_env:
            paper_env = create_paper_environment(Config.PAPER_STARTING_BALANCE)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Run backtest
        if strategy_type == 'wheel':
            backtester = WheelStrategyBacktester(client, paper_env)
            result = backtester.run_backtest(symbol, start_date, end_date)
        else:
            backtester = MomentumBreakoutBacktester(client, paper_env)
            result = backtester.run_backtest(symbol, start_date, end_date)
        
        # Convert result to JSON-serializable format
        response = {
            'success': True,
            'strategy': result.strategy_name,
            'symbol': result.symbol,
            'period': {
                'start': result.start_date.isoformat(),
                'end': result.end_date.isoformat(),
                'days': days
            },
            'performance': {
                'initial_capital': result.initial_capital,
                'final_capital': result.final_capital,
                'total_return_pct': result.total_return_pct,
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': result.win_rate,
                'avg_trade_return': result.avg_trade_return,
                'max_drawdown_pct': result.max_drawdown_pct,
                'sharpe_ratio': result.sharpe_ratio
            },
            'trades': [
                {
                    'timestamp': t.timestamp.isoformat() if hasattr(t.timestamp, 'isoformat') else str(t.timestamp),
                    'symbol': t.symbol,
                    'action': t.action.value,
                    'quantity': t.quantity,
                    'price': t.price,
                    'realized_pnl': t.realized_pnl,
                    'strategy': t.strategy
                } for t in result.trades[:50]  # Limit to first 50 trades
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/backtest/history')
def get_backtest_history():
    """Get list of recent backtests (stored in memory)."""
    # For now, return empty list - could be enhanced to persist backtest results
    return jsonify({
        'backtests': [],
        'message': 'Backtest history persistence not yet implemented'
    })


@socketio.on('subscribe_quotes')
def handle_subscribe_quotes(data):
    """Subscribe to real-time quotes."""
    symbols = data.get('symbols', [])
    logger.info(f'Subscribing to quotes for: {symbols}')
    # Note: In production, this would set up actual streaming
    emit('subscribed', {'symbols': symbols})


def create_app():
    """Application factory."""
    init_clients()
    return app


if __name__ == '__main__':
    init_clients()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
