"""
Command-line interface for the Quant Options Trading System.

Provides quick access to common trading operations without the web dashboard.
"""
import sys
import argparse
import logging
from typing import List, Optional, Union
from datetime import datetime

from api import get_client, AlpacaClient
from trading.strike_resolver import StrikeResolver
from trading.wheel_strategy import WheelStrategy
from trading.momentum_breakout import CompraASecoStrategy, create_default_watchlist
from backtest.paper_trading import PaperTradingEnvironment, create_paper_environment
from backtest.backtest_engine import (
    WheelStrategyBacktester,
    MomentumBreakoutBacktester,
    print_backtest_summary
)
from utils.risk_manager import RiskManager
from models.pricing import BlackScholesModel
from config import Config, TradingMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Print section header."""
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print("─" * 70)


def cmd_status(client):  # Accepts AlpacaClient or TastyTradeClient
    """Show account and position status."""
    print_header("ACCOUNT STATUS")
    
    # Account balance
    try:
        balance = client.get_account_balance()
        print(f"\n💰 Cash Available:       ${balance['cash_available']:>12,.2f}")
        print(f"📊 Net Liquidating:      ${balance['net_liquidating_value']:>12,.2f}")
        print(f"🛡️  Buying Power:         ${balance['buying_power']:>12,.2f}")
        print(f"⚠️  Maintenance Req:      ${balance['maintenance_requirement']:>12,.2f}")
    except Exception as e:
        print(f"\n❌ Failed to get account balance: {e}")
    
    # Positions
    try:
        positions = client.get_portfolio_positions()
        print_section("PORTFOLIO POSITIONS")
        
        if not positions:
            print("\nNo active positions.")
        else:
            print(f"\n{'Symbol':<10} {'Type':<15} {'Qty':>8} {'Avg Price':>12} {'P&L':>12}")
            print("-" * 70)
            for pos in positions:
                symbol = pos['symbol']
                pnl = pos['unrealized_pnl']
                pnl_str = f"${pnl:,.2f}"
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                
                print(f"{symbol:<10} {pos['instrument_type']:<15} {pos['quantity']:>8} "
                      f"${pos['average_price']:>10,.2f} {pnl_color} {pnl_str:>10}")
    except Exception as e:
        print(f"\n❌ Failed to get positions: {e}")


def cmd_wheel(client):  # Accepts AlpacaClient or TastyTradeClient
    """Show wheel strategy status."""
    print_header("WHEEL STRATEGY STATUS")
    
    resolver = StrikeResolver(client)
    strategy = WheelStrategy(client, resolver)
    
    try:
        status = strategy.get_wheel_status()
        
        print_section("SUMMARY")
        print(f"\nTotal Positions:        {status['summary']['total_positions']}")
        print(f"Total Stock P&L:         ${status['summary']['total_stock_pnl']:,.2f}")
        print(f"Total Option P&L:        ${status['summary']['total_option_pnl']:,.2f}")
        print(f"Premium Collected:       ${status['summary']['total_premium_collected']:,.2f}")
        
        if status['positions']:
            print_section("POSITION DETAILS")
            
            for pos in status['positions']:
                print(f"\n📈 {pos['symbol']} [{pos['state'].upper().replace('_', ' ')}]")
                print(f"   Shares:      {pos['shares_owned']}")
                print(f"   Cost Basis:    ${pos['cost_basis']:,.2f}")
                print(f"   Current:       ${pos['current_price']:,.2f}")
                print(f"   Stock P&L:     ${pos['stock_pnl']:,.2f}")
                
                if pos['option_symbol']:
                    print(f"\n   Option:        {pos['option_symbol']}")
                    print(f"   Strike:        ${pos['option_strike']}")
                    print(f"   Delta:         {pos['option_delta']:.2%}")
                    print(f"   Premium:       ${pos['option_premium']:,.2f}")
                    print(f"   Assignment:    {pos['assignment_probability']:.1%}")
                    
                    if pos['option_type'] == 'call':
                        print(f"   Call P&L:      ${pos['assignment_pnl']:,.2f}")
                    else:
                        print(f"   New Cost:      ${pos['new_cost_basis_if_assigned']:,.2f}")
                        print(f"   Cash Req:      ${pos['cash_obligation']:,.2f}")
        else:
            print("\n🎯 Ready to start the wheel!")
            print("\n   Next steps:")
            print("   1. Select a symbol you want to own")
            print("   2. Sell cash-secured puts at your target entry price")
            print("   3. If assigned, sell covered calls above cost basis")
            print("   4. If called away, return to step 2")
    
    except Exception as e:
        print(f"\n❌ Failed to get wheel status: {e}")


def cmd_analyze(client, symbol: str):
    """Analyze a symbol for wheel strategy."""
    print_header(f"ANALYZING {symbol.upper()}")
    
    resolver = StrikeResolver(client)
    
    # Get quote
    try:
        quote = client.get_stock_quote(symbol.upper())
        spot = quote.get('last_price') or quote.get('spot_price', 0)
        print(f"\n📊 Current Price: ${spot:.2f}")
        print(f"   Bid: ${quote.get('bid', 0):.2f} | Ask: ${quote.get('ask', 0):.2f}")
    except Exception as e:
        print(f"\n❌ Failed to get quote: {e}")
        return
    
    # Analyze wheel state
    strategy = WheelStrategy(client, resolver)
    analysis = strategy.analyze_position(symbol.upper())
    
    print_section("POSITION STATE")
    print(f"\nState: {analysis.state.value.upper().replace('_', ' ')}")
    print(f"Shares Owned:    {analysis.shares_owned}")
    print(f"Cost Basis:      ${analysis.cost_basis:.2f}")
    print(f"Stock P&L:       ${analysis.stock_pnl:.2f}")
    
    # Get recommendations
    print_section("TRADE RECOMMENDATIONS")
    
    recs = strategy.generate_recommendations(symbol.upper(), analysis)
    
    if recs:
        for i, rec in enumerate(recs, 1):
            action_icon = "🟢" if "call" in rec.action else "🔴"
            print(f"\n{i}. {action_icon} {rec.action.upper().replace('_', ' ')}")
            print(f"   Strike:        ${rec.candidate.strike:.2f}")
            print(f"   Expiration:    {rec.candidate.expiration.strftime('%Y-%m-%d')}")
            print(f"   Delta:         {rec.candidate.delta:.2%}")
            print(f"   Premium:       ${rec.expected_premium:.2f}")
            print(f"   Max Profit:    ${rec.max_profit:.2f}")
            print(f"   Reason:        {rec.reasoning}")
    else:
        print("\nNo recommendations at this time.")
    
    # Show option chain
    print_section("OPTION CHAIN (Target Delta: 0.30)")
    
    try:
        results = resolver.resolve_strikes(
            symbol=symbol.upper(),
            target_delta=0.30,
            option_type='both',
            max_maturities=3,
            spot_price=spot
        )
        
        for expiry, options in results.items():
            print(f"\n📅 {expiry.strftime('%Y-%m-%d')}:")
            
            print(f"\n   CALLS:")
            print(f"   {'Strike':>10} {'Delta':>10} {'Bid':>10} {'Ask':>10} {'Vol':>8}")
            print(f"   {'-'*54}")
            for c in options['calls'][:3]:
                print(f"   {c.strike:>10.2f} {c.delta:>9.2%} ${c.bid:>9.2f} ${c.ask:>9.2f} {c.volume:>8}")
            
            print(f"\n   PUTS:")
            print(f"   {'Strike':>10} {'Delta':>10} {'Bid':>10} {'Ask':>10} {'Vol':>8}")
            print(f"   {'-'*54}")
            for p in options['puts'][:3]:
                print(f"   {p.strike:>10.2f} {abs(p.delta):>9.2%} ${p.bid:>9.2f} ${p.ask:>9.2f} {p.volume:>8}")
    
    except Exception as e:
        print(f"\n❌ Failed to resolve options: {e}")


def cmd_risk(client):
    """Show risk analysis."""
    print_header("RISK ANALYSIS")
    
    risk_manager = RiskManager(client)
    
    try:
        report = risk_manager.generate_risk_report()
        
        print_section("PORTFOLIO RISK METRICS")
        
        portfolio = report['portfolio_risk']
        print(f"\nPortfolio Value:        ${portfolio.get('total_portfolio_value', 0):,.2f}")
        print(f"Net Delta Exposure:     {portfolio.get('net_delta_exposure', 0):,.0f}")
        print(f"Daily Theta Income:     ${portfolio.get('daily_theta_income', 0):,.2f}")
        print(f"Max Concentration:      {portfolio.get('max_concentration', 0):.1%}")
        print(f"Diversification Score:  {portfolio.get('diversification_score', 0):.2f}")
        print(f"Cash Percentage:        {portfolio.get('cash_percentage', 0):.1f}%")
        print(f"Margin Utilization:     {portfolio.get('margin_utilization', 0):.1f}%")
        
        if report['risk_flags']:
            print_section("⚠️  RISK FLAGS")
            for flag in report['risk_flags']:
                print(f"   🔴 {flag}")
        
        if report['recommendations']:
            print_section("💡 RECOMMENDATIONS")
            for rec in report['recommendations']:
                print(f"   💭 {rec}")
    
    except Exception as e:
        print(f"\n❌ Failed to generate risk report: {e}")


def cmd_recommend(client, symbols: List[str]):
    """Get trade recommendations for symbols."""
    print_header("TRADE RECOMMENDATIONS")
    
    resolver = StrikeResolver(client)
    strategy = WheelStrategy(client, resolver)
    
    for symbol in symbols:
        symbol = symbol.upper().strip()
        print(f"\n{'─' * 70}")
        print(f"  {symbol}")
        print(f"{'─' * 70}")
        
        try:
            analysis = strategy.analyze_position(symbol)
            recs = strategy.generate_recommendations(symbol, analysis)
            
            if recs:
                best = recs[0]
                action = "Sell Call" if "call" in best.action else "Sell Put"
                print(f"\n🎯 RECOMMENDED: {action}")
                print(f"   Strike:     ${best.candidate.strike:.2f}")
                print(f"   Expiry:     {best.candidate.expiration.strftime('%Y-%m-%d')}")
                print(f"   Delta:      {best.candidate.delta:.2%}")
                print(f"   Premium:    ${best.expected_premium:.2f}")
                print(f"   Max Profit: ${best.max_profit:.2f}")
            else:
                print(f"\n⏳ No recommendation at this time")
                print(f"   State: {analysis.state.value.replace('_', ' ')}")
                
                if analysis.state.value == 'short_call':
                    print(f"   Waiting for call assignment or expiration")
                elif analysis.state.value == 'short_put':
                    print(f"   Waiting for put assignment or expiration")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")


def cmd_momentum(client, symbol: Optional[str] = None):
    """Show Compra a Seco momentum breakout strategy status."""
    print_header("COMPRA A SECO (MOMENTUM BREAKOUT)")
    
    momentum = CompraASecoStrategy(client)
    momentum.add_to_watchlist(create_default_watchlist())
    
    print_section("STRATEGY PARAMETERS")
    print(f"\nTimeframe:          120-minute (2-hour) candles")
    print(f"Propulsion Candle:  ≥2x average body size")
    print(f"Pin Bar:            Small body (≤20% of range)")
    print(f"Breakout Window:    Within 3 candles")
    print(f"Target:             2x propulsion candle amplitude")
    print(f"Time Stop:          12 bars")
    
    print_section("WATCHLIST (Tech Stocks)")
    for sym in momentum.watchlist:
        print(f"  📊 {sym}")
    
    # If a symbol is provided, scan for setups
    if symbol:
        symbol = symbol.upper().strip()
        print_section(f"SCANNING {symbol} FOR SETUPS")
        
        try:
            setups = momentum.scan_symbol(symbol, lookback_days=30)
            
            if setups:
                print(f"\n🎯 Found {len(setups)} potential setups:")
                for i, setup in enumerate(setups[-3:], 1):  # Show last 3
                    print(f"\n  Setup {i}:")
                    print(f"    Detected:        {setup.detected_at.strftime('%Y-%m-%d %H:%M')}")
                    print(f"    Propulsion:      ${setup.propulsion_candle.close:.2f}")
                    print(f"    Pin Bar:         ${setup.pin_bar_candle.close:.2f}")
                    print(f"    Entry (breakout): ${setup.entry_price:.2f}")
                    print(f"    Target:          ${setup.target_price:.2f}")
                    print(f"    EMA Status:      {'✅ Bull Run' if setup.ema_status.is_bull_run else '❌ No Trend'}")
            else:
                print(f"\n⏳ No setups found for {symbol} in the last 30 days")
                print(f"   The pattern requires:")
                print(f"   • EMA 8 > EMA 80 (bull run)")
                print(f"   • Large propulsion candle")
                print(f"   • Small pin bar consolidation")
                
        except Exception as e:
            print(f"\n❌ Error scanning {symbol}: {e}")
    
    print_section("PERFORMANCE")
    perf = momentum.calculate_performance()
    
    if perf.total_trades == 0:
        print("\nNo trades yet. Waiting for setups...")
    else:
        print(f"\nTotal Trades:       {perf.total_trades}")
        print(f"Win Rate:           {perf.win_rate:.1%}")
        print(f"Avg Profit:         ${perf.avg_profit:.2f}")
        print(f"Avg Loss:           ${perf.avg_loss:.2f}")
        print(f"Profit Factor:      {perf.profit_factor:.2f}")
        print(f"Max Drawdown:       ${perf.max_drawdown:.2f}")
    
    print("\n💡 To use this strategy:")
    print("   1. Run: python cli.py momentum NVDA")
    print("   2. Monitor 120-min charts for propulsion + pin bar patterns")
    print("   3. Enter on breakout above pin bar high")
    print("   4. Target 2x the propulsion candle range")
    print("   5. Exit if target not hit within 12 bars")


def cmd_paper(client, action: str = None):
    """Paper trading command."""
    from config import TradingMode
    
    print("\n" + "=" * 70)
    print("  📝 PAPER TRADING ACCOUNT")
    print("=" * 70)
    
    # Check current mode
    if Config.TRADING_MODE == TradingMode.PAPER:
        print("\n✅ Mode: PAPER (Local Simulation)")
        print("   No real orders will be sent to TastyTrade")
    elif Config.TRADING_MODE == TradingMode.SANDBOX:
        print("\n✅ Mode: SANDBOX (TastyTrade Test Environment)")
        print("   Test money - 15-min delayed quotes")
    else:
        print("\n⚠️  WARNING: Not in paper/sandbox mode!")
        print(f"   Current mode: {Config.TRADING_MODE}")
        print("   Use TRADING_MODE=paper in .env for safe testing")
    
    # Handle reset action
    if action and action.lower() == 'reset':
        confirm = input("\n⚠️  Reset paper account to $100,000? (yes/no): ")
        if confirm.lower() == 'yes':
            paper = create_paper_environment(Config.PAPER_STARTING_BALANCE)
            paper.reset_account()
            paper.save_account()
            print("\n✅ Paper account reset to $100,000")
        else:
            print("\nCancelled")
        return
    
    # Load or create paper environment
    paper = create_paper_environment(Config.PAPER_STARTING_BALANCE)
    
    # Display account summary
    summary = paper.get_account_summary()
    
    print_section("ACCOUNT SUMMARY")
    print(f"\nCash Balance:       ${summary['cash_balance']:,.2f}")
    print(f"Total P&L:            ${summary['total_pnl']:,.2f}")
    print(f"Total Trades:         {summary['total_trades']}")
    print(f"Win Rate:             {summary['win_rate']:.1%}")
    print(f"Open Positions:       {len(summary['open_positions'])}")
    
    # Display positions
    if summary['open_positions']:
        print_section("OPEN POSITIONS")
        for pos in summary['open_positions']:
            pnl_icon = "🟢" if pos['unrealized_pnl'] >= 0 else "🔴"
            print(f"\n  {pos['symbol']}: {pos['quantity']} {pos['trade_type']}")
            print(f"    Entry: ${pos['entry_price']:.2f} | Current: ${pos['current_price']:.2f}")
            print(f"    P&L: {pnl_icon} ${pos['unrealized_pnl']:.2f}")
    
    # Display recent trades
    if summary['recent_trades']:
        print_section("RECENT TRADES")
        for trade in summary['recent_trades'][:5]:
            pnl_str = ""
            if trade['realized_pnl'] != 0:
                icon = "🟢" if trade['realized_pnl'] > 0 else "🔴"
                pnl_str = f" | {icon} ${trade['realized_pnl']:.2f}"
            
            print(f"  {trade['timestamp'][:10]}: {trade['action']} {trade['symbol']} "
                  f"@{trade['price']:.2f}{pnl_str}")
    
    print("\n" + "-" * 70)
    print("Commands:")
    print("  python cli.py paper         # Show status")
    print("  python cli.py paper reset   # Reset account")
    print("  python cli.py backtest NVDA 30  # Backtest strategy")
    print("=" * 70)


def cmd_backtest(client, symbol: str = None, days: str = "30"):
    """Backtest command."""
    from datetime import timedelta
    
    print("\n" + "=" * 70)
    print("  📊 STRATEGY BACKTEST")
    print("=" * 70)
    
    if not symbol:
        print("\n❌ Error: Symbol required")
        print("   Usage: python cli.py backtest NVDA 60")
        return
    
    symbol = symbol.upper().strip()
    
    # Parse days
    try:
        lookback_days = int(days)
    except ValueError:
        lookback_days = 30
    
    print(f"\nSymbol:        {symbol}")
    print(f"Lookback:      {lookback_days} days")
    print(f"Starting Cap:  $100,000")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    # Ask which strategy
    print("\nSelect strategy:")
    print("  1. Wheel (Cash-secured puts → Covered calls)")
    print("  2. Compra a Seco (Momentum breakout)")
    
    choice = input("\nEnter choice (1 or 2): ").strip() or "2"
    
    try:
        if choice == "1":
            print_section("WHEEL STRATEGY BACKTEST")
            print("\n⚠️  Note: Wheel backtest requires historical option chains")
            print("   This is a simplified simulation using estimated premiums")
            
            paper = PaperTradingEnvironment(Config.PAPER_STARTING_BALANCE)
            backtester = WheelStrategyBacktester(client, paper)
            result = backtester.run_backtest(symbol, start_date, end_date)
            
        else:
            print_section("COMPRA A SECO (MOMENTUM) BACKTEST")
            print("\nℹ️  Using actual 2-hour historical data")
            
            paper = PaperTradingEnvironment(Config.PAPER_STARTING_BALANCE)
            backtester = MomentumBreakoutBacktester(client, paper)
            result = backtester.run_backtest(symbol, start_date, end_date)
        
        # Display results
        print("\n" + "=" * 70)
        print("  BACKTEST RESULTS")
        print("=" * 70)
        
        print(f"\nStrategy:       {result.strategy_name}")
        print(f"Period:         {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        print(f"Initial:        ${result.initial_capital:,.2f}")
        print(f"Final:          ${result.final_capital:,.2f}")
        
        return_pct = ((result.final_capital - result.initial_capital) / result.initial_capital) * 100
        icon = "🟢" if return_pct >= 0 else "🔴"
        print(f"Return:         {icon} {return_pct:+.2f}%")
        
        print(f"\nTotal Trades:   {result.total_trades}")
        if result.total_trades > 0:
            print(f"Win Rate:       {result.win_rate:.1%}")
            print(f"Winners:        {result.winning_trades}")
            print(f"Losers:         {result.losing_trades}")
            print(f"Avg Trade:      ${result.avg_trade_return:.2f}")
        
        print(f"\nMax Drawdown:   {result.max_drawdown_pct:.2f}%")
        print(f"Sharpe Ratio:   {result.sharpe_ratio:.2f}")
        
        # Show trade list if any
        if result.trades:
            print_section("TRADE LIST")
            for trade in result.trades[:10]:  # Show first 10
                pnl_str = ""
                if trade.realized_pnl != 0:
                    icon = "🟢" if trade.realized_pnl > 0 else "🔴"
                    pnl_str = f" | {icon} ${trade.realized_pnl:.2f}"
                
                date_str = trade.timestamp.strftime('%Y-%m-%d') if hasattr(trade.timestamp, 'strftime') else str(trade.timestamp)[:10]
                price = trade.entry_price if hasattr(trade, 'entry_price') else trade.price
                print(f"  {date_str}: {trade.action.value} {trade.symbol} "
                      f"@{price:.2f}{pnl_str}")
        
        print("\n" + "=" * 70)
        
        # Auto-save report (non-interactive for reliability)
        try:
            filename = f"backtest_{symbol}_{lookback_days}d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            import json
            report_data = result.to_dict() if hasattr(result, 'to_dict') else {
                'strategy': result.strategy_name,
                'symbol': result.symbol,
                'period': {'start': result.start_date.isoformat(), 'end': result.end_date.isoformat()},
                'performance': {
                    'initial_capital': result.initial_capital,
                    'final_capital': result.final_capital,
                    'total_return_pct': result.total_return_pct,
                    'total_trades': result.total_trades,
                    'win_rate': result.win_rate,
                    'max_drawdown_pct': result.max_drawdown_pct,
                    'sharpe_ratio': result.sharpe_ratio
                }
            }
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            print(f"\n✅ Report saved to: {filename}")
        except Exception as save_error:
            print(f"\n⚠️  Could not save report: {save_error}")
        
    except Exception as e:
        print(f"\n❌ Backtest error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Quant Options Trading System - CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py status                  # Show account status
  python cli.py wheel                   # Show wheel strategy status
  python cli.py analyze NVDA            # Analyze NVDA
  python cli.py risk                    # Show risk analysis
  python cli.py recommend NVDA SPY GDX  # Get recommendations
  python cli.py momentum                # Show momentum breakout info
  python cli.py momentum NVDA           # Scan NVDA for setups
  python cli.py paper                   # Show paper trading status
  python cli.py paper reset             # Reset paper account
  python cli.py backtest NVDA 30        # Backtest NVDA for 30 days
        """
    )
    
    parser.add_argument('command', choices=[
        'status', 'wheel', 'analyze', 'risk', 'recommend', 'momentum', 'backtest', 'paper'
    ], help='Command to execute')
    
    parser.add_argument('args', nargs='*', help='Additional arguments')
    
    args = parser.parse_args()
    
    # Initialize broker client
    client = get_client()
    
    if not client.authenticate():
        print("❌ Error: Authentication failed")
        print("   Check your API credentials in .env file")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'status':
            cmd_status(client)
        elif args.command == 'wheel':
            cmd_wheel(client)
        elif args.command == 'analyze':
            if not args.args:
                print("❌ Error: Symbol required (e.g., python cli.py analyze NVDA)")
                sys.exit(1)
            cmd_analyze(client, args.args[0])
        elif args.command == 'risk':
            cmd_risk(client)
        elif args.command == 'recommend':
            if not args.args:
                print("❌ Error: Symbols required (e.g., python cli.py recommend NVDA SPY)")
                sys.exit(1)
            cmd_recommend(client, args.args)
        elif args.command == 'momentum':
            # Optional symbol argument for scanning
            momentum_symbol = args.args[0] if args.args else None
            cmd_momentum(client, momentum_symbol)
        
        elif args.command == 'paper':
            # Optional action argument (reset)
            paper_action = args.args[0] if args.args else None
            cmd_paper(client, paper_action)
        
        elif args.command == 'backtest':
            # Required symbol, optional days
            if not args.args:
                print("❌ Error: Symbol required for backtest")
                print("   Usage: python cli.py backtest NVDA [days]")
                sys.exit(1)
            
            backtest_symbol = args.args[0]
            backtest_days = args.args[1] if len(args.args) > 1 else "30"
            cmd_backtest(client, backtest_symbol, backtest_days)
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    
    finally:
        client.close()


if __name__ == '__main__':
    main()
