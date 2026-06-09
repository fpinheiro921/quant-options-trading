"""
Quant Options Trading System - Main Entry Point

A comprehensive options trading system implementing the Wheel Strategy
using the TastyTrade API.

Based on the papers that built quantitative finance:
- Bachelier (1900): Theory of Speculation - Brownian motion in finance
- Sharpe (1964): Capital Asset Pricing Model - Systematic vs idiosyncratic risk
- Black-Scholes (1973): Options pricing via risk-neutral replication
- Dupire (1994): Local volatility for the volatility surface
- Carr-Madan (1999): FFT for efficient option pricing

Features:
- Wheel Strategy implementation (covered calls → cash-secured puts)
- Delta-based strike selection
- Real-time market data visualization
- Risk management and position sizing
- Portfolio tracking and P&L analysis
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask dashboard."""
    from dashboard.app import init_clients, app, socketio
    
    # Display current trading mode
    mode = Config.TRADING_MODE
    mode_display = {
        TradingMode.PAPER: "📝 PAPER TRADING (Local Simulation)",
        TradingMode.SANDBOX: "🧪 SANDBOX (TastyTrade Test Environment)",
        TradingMode.LIVE: "🔴 LIVE TRADING (REAL MONEY)"
    }.get(mode, f"UNKNOWN MODE: {mode}")
    
    print("\n" + "=" * 70)
    print(f"  {mode_display}")
    print("=" * 70 + "\n")
    
    if mode == TradingMode.LIVE:
        print("⚠️  WARNING: Live trading mode active!")
        print("   Real money will be used for trades.\n")
    elif mode == TradingMode.SANDBOX:
        print("✅ Using TastyTrade sandbox environment")
        print("   Test money only - safe for strategy validation\n")
    else:
        print("✅ Paper trading mode - local simulation")
        print("   No real orders will be sent\n")
    
    logger.info(f"Starting Quant Options Trading Dashboard on {host}:{port}")
    
    # Initialize API clients
    init_clients()
    
    # Run the application
    socketio.run(app, host=host, port=port, debug=debug)


def run_cli():
    """Run CLI interface for command-line trading."""
    from api.tastytrade_client import TastyTradeClient
    from trading.strike_resolver import StrikeResolver
    from trading.wheel_strategy import WheelStrategy
    from config import Config, TradingConfig, TradingMode
    
    # Display current trading mode
    mode = Config.TRADING_MODE
    mode_display = {
        TradingMode.PAPER: "📝 PAPER TRADING",
        TradingMode.SANDBOX: "🧪 SANDBOX",
        TradingMode.LIVE: "🔴 LIVE TRADING"
    }.get(mode, f"UNKNOWN: {mode}")
    
    print("\n" + "="*60)
    print("  Quant Options Trading System - CLI")
    print(f"  Mode: {mode_display}")
    print("="*60 + "\n")
    
    if mode == TradingMode.LIVE:
        print("⚠️  LIVE MODE: Real money will be used!\n")
    
    # Initialize client
    client = TastyTradeClient(Config.TASTYTRADE_USERNAME, Config.TASTYTRADE_PASSWORD)
    
    if not client.authenticate(Config.TASTYTRADE_ACCOUNT_ID):
        print("❌ Authentication failed. Check your credentials.")
        sys.exit(1)
    
    print("✅ Authenticated successfully\n")
    
    # Initialize trading components
    resolver = StrikeResolver(client)
    strategy = WheelStrategy(client, resolver)
    
    # Show account info
    try:
        balance = client.get_account_balance()
        print(f"💰 Cash Available: ${balance['cash_available']:,.2f}")
        print(f"📊 Net Liquidating Value: ${balance['net_liquidating_value']:,.2f}")
        print(f"🛡️  Buying Power: ${balance['buying_power']:,.2f}\n")
    except Exception as e:
        logger.error(f"Failed to get account balance: {e}")
    
    # Show wheel status
    print("📈 Wheel Strategy Status:")
    print("-" * 40)
    
    try:
        status = strategy.get_wheel_status()
        
        if not status['positions']:
            print("No active positions. Ready to start the wheel!\n")
            print("To begin:")
            print("  1. Sell cash-secured puts on symbols you want to own")
            print("  2. If assigned, sell covered calls above cost basis")
            print("  3. If called away, return to step 1\n")
        else:
            print(f"Active positions: {status['summary']['total_positions']}")
            print(f"Total Stock P&L: ${status['summary']['total_stock_pnl']:,.2f}")
            print(f"Total Option P&L: ${status['summary']['total_option_pnl']:,.2f}")
            print(f"Premium Collected: ${status['summary']['total_premium_collected']:,.2f}\n")
            
            for pos in status['positions']:
                print(f"\n  {pos['symbol']}:")
                print(f"    State: {pos['state']}")
                print(f"    Shares: {pos['shares_owned']}")
                print(f"    Cost Basis: ${pos['cost_basis']:,.2f}")
                print(f"    Stock P&L: ${pos['stock_pnl']:,.2f}")
                if pos['option_symbol']:
                    print(f"    Option: {pos['option_symbol']}")
                    print(f"    Option Delta: {pos['option_delta']:.2%}")
    
    except Exception as e:
        logger.error(f"Failed to get wheel status: {e}")
    
    print("\n" + "="*60)
    print("Use the dashboard (run: python main.py --dashboard)")
    print("for visual trading interface.")
    print("="*60 + "\n")


def run_analysis(symbol: str):
    """Run analysis on a specific symbol."""
    from api.tastytrade_client import TastyTradeClient
    from trading.strike_resolver import StrikeResolver
    from config import Config
    
    print(f"\n🔍 Analyzing {symbol}...\n")
    
    client = TastyTradeClient(Config.TASTYTRADE_USERNAME, Config.TASTYTRADE_PASSWORD)
    
    if not client.authenticate(Config.TASTYTRADE_ACCOUNT_ID):
        print("❌ Authentication failed")
        sys.exit(1)
    
    resolver = StrikeResolver(client)
    
    # Get stock quote
    try:
        quote = client.get_stock_quote(symbol)
        spot = quote.get('last_price') or quote.get('spot_price', 0)
        print(f"Current Price: ${spot:.2f}\n")
    except Exception as e:
        print(f"Failed to get quote: {e}")
        sys.exit(1)
    
    # Resolve options
    print("📊 Resolved Options (Target Delta: 0.30):\n")
    
    try:
        results = resolver.resolve_strikes(
            symbol=symbol,
            target_delta=0.30,
            option_type='both',
            max_maturities=3,
            spot_price=spot
        )
        
        for expiry, options in results.items():
            exp_str = expiry.strftime('%Y-%m-%d')
            print(f"  Expiration: {exp_str}")
            
            print(f"    Calls:")
            for c in options['calls'][:3]:
                print(f"      Strike: ${c.strike:.2f} | Delta: {c.delta:.2%} | Premium: ${c.premium:.2f} | Volume: {c.volume}")
            
            print(f"    Puts:")
            for p in options['puts'][:3]:
                print(f"      Strike: ${p.strike:.2f} | Delta: {abs(p.delta):.2%} | Premium: ${p.premium:.2f} | Volume: {p.volume}")
            print()
    
    except Exception as e:
        print(f"Failed to resolve options: {e}")
    
    print("\nUse the dashboard for detailed analysis and trading.\n")


def check_setup():
    """Check if the system is properly configured."""
    from config import TradingMode
    
    print("\n🔧 System Configuration Check\n")
    print("-" * 40)
    
    # Check trading mode
    mode = Config.TRADING_MODE
    mode_warnings = {
        TradingMode.PAPER: "✅ PAPER MODE - Safe for testing (local simulation)",
        TradingMode.SANDBOX: "✅ SANDBOX MODE - Safe for testing (TastyTrade sandbox)",
        TradingMode.LIVE: "⚠️  LIVE MODE - Real money will be used!"
    }
    print(mode_warnings.get(mode, f"❌ UNKNOWN MODE: {mode}"))
    print(f"\nCurrent Mode: {mode.upper()}")
    
    # Check environment variables
    required_vars = [
        'TASTYTRADE_USERNAME',
        'TASTYTRADE_PASSWORD',
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = value[:3] + '*' * (len(value) - 6) + value[-3:] if len(value) > 6 else '***'
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NOT SET")
            missing.append(var)
    
    # Optional variables
    optional_vars = ['TASTYTRADE_ACCOUNT_ID', 'DEFAULT_DELTA_THRESHOLD']
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: NOT SET (will use default)")
    
    print("-" * 40)
    
    if missing:
        print(f"\n❌ Missing required configuration: {', '.join(missing)}")
        print("\nPlease set these in your .env file:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your TastyTrade credentials")
        print("  3. Restart the application\n")
        return False
    else:
        print("\n✅ All required configuration is set!\n")
        return True


def main():
    """Main entry point."""
    from config import TradingMode
    
    parser = argparse.ArgumentParser(
        description='Quant Options Trading System - Wheel Strategy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --check               # Check configuration
  python main.py --dashboard           # Run web dashboard
  python main.py --cli                 # Run CLI interface
  python main.py --analyze NVDA        # Analyze specific symbol
  python main.py --dashboard --port 8080  # Run dashboard on port 8080
  
Trading Mode Progression:
  1. TRADING_MODE=paper     (Local simulation - safe)
  2. TRADING_MODE=sandbox   (TastyTrade sandbox - realistic)
  3. TRADING_MODE=live      (Real money - only after good results)
        """
    )
    
    parser.add_argument('--dashboard', action='store_true',
                        help='Run the web dashboard')
    parser.add_argument('--cli', action='store_true',
                        help='Run CLI interface')
    parser.add_argument('--check', action='store_true',
                        help='Check system configuration')
    parser.add_argument('--analyze', type=str, metavar='SYMBOL',
                        help='Analyze a specific symbol')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Dashboard host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Dashboard port (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    parser.add_argument('--mode', type=str, choices=['paper', 'sandbox', 'live'],
                        help='Override trading mode for this session')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Override mode if specified
    if args.mode:
        Config.TRADING_MODE = args.mode
        os.environ['TRADING_MODE'] = args.mode
    
    # Check configuration first
    if args.check:
        check_setup()
        return
    
    # Always check setup unless explicitly skipping
    if not check_setup():
        sys.exit(1)
    
    # Confirm live trading
    if Config.TRADING_MODE == TradingMode.LIVE:
        print("\n" + "⚠️ " * 20)
        print("\nLIVE TRADING MODE ACTIVE")
        print("REAL MONEY WILL BE USED FOR TRADES\n")
        response = input("Are you sure you want to continue? (type 'LIVE' to confirm): ")
        if response != 'LIVE':
            print("\nCancelled. Set TRADING_MODE=paper or TRADING_MODE=sandbox in .env\n")
            sys.exit(0)
    
    # Run appropriate mode
    if args.dashboard:
        run_dashboard(args.host, args.port, args.debug)
    elif args.cli:
        run_cli()
    elif args.analyze:
        run_analysis(args.analyze.upper())
    else:
        # Default to dashboard
        run_dashboard(args.host, args.port, args.debug)


if __name__ == '__main__':
    main()
