"""
Backtesting Engine for Wheel and Momentum Breakout Strategies.

Runs strategies on historical data to evaluate performance before live trading.
"""
import logging
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from backtest.paper_trading import PaperTradingEnvironment, PaperTrade, TradeAction
from models.technical_analysis import TechnicalAnalyzer, Candle, CompraASecoSetup
from trading.wheel_strategy import WheelStrategy, TradeRecommendation
from trading.momentum_breakout import CompraASecoStrategy
from api.tastytrade_client import TastyTradeClient

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_trade_return: float
    max_drawdown_pct: float
    sharpe_ratio: float
    
    # Detailed data
    equity_curve: List[Dict[str, Any]]  # Date + account value
    trades: List[PaperTrade]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': round(self.final_capital, 2),
            'total_return_pct': round(self.total_return_pct, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 4),
            'avg_trade_return': round(self.avg_trade_return, 4),
            'max_drawdown_pct': round(self.max_drawdown_pct, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
        }


class WheelStrategyBacktester:
    """
    Backtester for the Wheel Strategy based on professional options trading methodology.
    
    Proper Mechanics (from video):
    1. Sell 20 Delta cash-secured puts monthly (30-35 DTE)
    2. If assigned at strike X, sell covered calls at or ABOVE X
    3. If called away, return to step 1 (sell puts again)
    4. Track: Put premiums + Call premiums + Stock P&L
    5. Never sell calls below your cost basis
    
    Key Rules:
    - 20 Delta puts = ~80% probability of expiring worthless
    - Monthly expiration for consistent income
    - Only trade stocks you want to own long-term
    """
    
    def __init__(
        self,
        client: TastyTradeClient,
        paper_env: PaperTradingEnvironment,
        target_delta: float = 0.20,  # 20 Delta per video
        dte: int = 30,  # Monthly per video
        max_position_pct: float = 0.30  # 30% max allocation
    ):
        self.client = client
        self.paper = paper_env
        self.target_delta = target_delta  # 20 Delta = ~80% win rate
        self.dte = dte  # 30 days (monthly)
        self.max_position_pct = max_position_pct
    
    def _estimate_put_premium(self, stock_price: float, strike: float, 
                              days_to_expiry: int, volatility: float = 0.40) -> float:
        """Estimate put premium using simplified Black-Scholes."""
        # Simplified: 20 Delta put is roughly 2-4% OTM, premium ~1.5-2.5% of strike
        distance_pct = (stock_price - strike) / stock_price
        # Closer to ATM = higher premium
        if distance_pct < 0.05:  # < 5% OTM
            return strike * 0.025  # 2.5% premium
        elif distance_pct < 0.10:  # < 10% OTM
            return strike * 0.015  # 1.5% premium
        else:
            return strike * 0.008  # 0.8% premium
    
    def _estimate_call_premium(self, stock_price: float, strike: float,
                             days_to_expiry: int, volatility: float = 0.40) -> float:
        """Estimate call premium."""
        distance_pct = (strike - stock_price) / stock_price
        # ITM calls are more expensive
        if distance_pct < 0:  # ITM
            return strike * 0.03  # 3% premium
        elif distance_pct < 0.05:  # Slightly OTM
            return strike * 0.02  # 2% premium
        else:
            return strike * 0.01  # 1% premium
    
    def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        starting_capital: float = 100000.0
    ) -> BacktestResult:
        """
        Run proper Wheel strategy backtest.
        
        Strategy Flow:
        Month 1: Sell 20 Delta put → Collect premium
                 → If expires worthless: Repeat
                 → If assigned: Own shares at strike X
        Month 2+: If own shares: Sell call at or above X
                 → If called away: Sell shares at profit + call premium
                 → If expires: Keep shares, sell next month's call
        """
        logger.info(f"Starting PROPER Wheel backtest for {symbol}")
        logger.info(f"Parameters: {self.target_delta} Delta, {self.dte} DTE, monthly cycles")
        
        # Fetch historical stock data
        days_needed = (end_date - start_date).days + 60  # Extra for monthly cycles
        df = self.client.get_historical_candles(symbol, '1d', days_needed, end_date)
        
        if df.empty or len(df) < 30:
            logger.error(f"Insufficient data for {symbol}")
            return self._empty_result(symbol, start_date, end_date, starting_capital)
        
        # Handle timezone
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        # Filter to backtest period
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        if len(df) < 20:
            logger.error(f"Not enough data points for {symbol}")
            return self._empty_result(symbol, start_date, end_date, starting_capital)
        
        # Track state
        capital = starting_capital
        shares_owned = 0
        put_strike = 0.0  # Strike where we might get assigned
        call_strike = 0.0  # Strike where we'll sell calls
        total_premiums_collected = 0.0
        total_stock_pnl = 0.0
        monthly_returns = []
        
        # Process monthly cycles
        trades = []
        equity_curve = []
        
        # Start from first trading day
        current_date = df.index[0]
        end_backtest = df.index[-1]
        
        month_count = 0
        
        while current_date <= end_backtest:
            month_count += 1
            
            # Get current price
            current_idx = df.index.get_indexer([current_date], method='nearest')[0]
            if current_idx < 0 or current_idx >= len(df):
                break
                
            current_price = df.iloc[current_idx]['close']
            
            # Calculate expiry date (30 days out or end of backtest)
            expiry_date = min(current_date + timedelta(days=self.dte), end_backtest)
            
            # Find price at expiry
            expiry_idx = df.index.get_indexer([expiry_date], method='nearest')[0]
            if expiry_idx >= len(df):
                expiry_price = df.iloc[-1]['close']
            else:
                expiry_price = df.iloc[expiry_idx]['close']
            
            if shares_owned == 0:
                # === PHASE 1: SELL CASH-SECURED PUT ===
                
                # Calculate 20 Delta strike (roughly 5-8% OTM for typical volatility)
                # 20 Delta put is approximately: stock_price * (1 - 0.05 to 0.08)
                put_strike = current_price * (1 - 0.06)  # ~6% OTM = ~20 Delta
                put_strike = round(put_strike, 2)
                
                # Check cash requirement
                cash_needed = put_strike * 100
                if cash_needed > capital * self.max_position_pct:
                    logger.debug(f"Month {month_count}: Insufficient cash for put at {put_strike}")
                    # Move forward a month
                    current_date = expiry_date + timedelta(days=1)
                    continue
                
                # Calculate premium
                days_to_expiry = (expiry_date - current_date).days
                premium = self._estimate_put_premium(current_price, put_strike, days_to_expiry)
                
                # Sell put
                put_trade = self.paper.execute_option_trade(
                    symbol=symbol,
                    option_symbol=f"{symbol}_PUT_{put_strike}_{expiry_date.strftime('%Y%m%d')}",
                    quantity=1,
                    action=TradeAction.SELL_TO_OPEN,
                    market_price=premium,
                    strike=put_strike,
                    expiry=expiry_date,
                    option_type='put',
                    timestamp=current_date,
                    strategy='wheel_put'
                )
                
                if put_trade:
                    trades.append(put_trade)
                    total_premiums_collected += premium * 100
                    
                    logger.info(f"Month {month_count}: SOLD PUT {put_strike} @ ${premium:.2f} "
                              f"(Stock: ${current_price:.2f}, Expiry: {expiry_date.strftime('%Y-%m-%d')})")
                    
                    # Check assignment
                    if expiry_price < put_strike:
                        # ASSIGNED - Buy shares at put_strike
                        shares_owned = 100
                        call_strike = put_strike  # Sell calls AT or ABOVE assignment price
                        capital -= put_strike * 100
                        
                        logger.info(f"Month {month_count}: ASSIGNED at ${put_strike:.2f} "
                                  f"(Stock closed at ${expiry_price:.2f})")
                    else:
                        # Put expired worthless - keep premium, repeat next month
                        logger.info(f"Month {month_count}: Put expired worthless "
                                  f"(Stock: ${expiry_price:.2f}, Strike: ${put_strike:.2f})")
                
            else:
                # === PHASE 2: SELL COVERED CALL ===
                # CRITICAL: Never sell calls below cost basis (per video rules)
                
                # Use the put_strike as minimum call strike
                # Sell calls at or slightly above assignment price
                call_strike = max(put_strike, current_price * 1.02)  # At or 2% above
                call_strike = round(call_strike, 2)
                
                # Ensure call strike is >= cost basis
                cost_basis = put_strike  # What we paid for shares
                call_strike = max(call_strike, cost_basis)
                
                days_to_expiry = (expiry_date - current_date).days
                call_premium = self._estimate_call_premium(current_price, call_strike, days_to_expiry)
                
                # Sell covered call
                call_trade = self.paper.execute_option_trade(
                    symbol=symbol,
                    option_symbol=f"{symbol}_CALL_{call_strike}_{expiry_date.strftime('%Y%m%d')}",
                    quantity=1,
                    action=TradeAction.SELL_TO_OPEN,
                    market_price=call_premium,
                    strike=call_strike,
                    expiry=expiry_date,
                    option_type='call',
                    timestamp=current_date,
                    strategy='wheel_call'
                )
                
                if call_trade:
                    trades.append(call_trade)
                    total_premiums_collected += call_premium * 100
                    
                    logger.info(f"Month {month_count}: SOLD CALL {call_strike} @ ${call_premium:.2f} "
                              f"(Stock: ${current_price:.2f}, Cost Basis: ${cost_basis:.2f})")
                    
                    # Check if called away
                    if expiry_price > call_strike:
                        # CALLED AWAY - Sell shares at call_strike
                        stock_pnl = (call_strike - cost_basis) * 100
                        total_stock_pnl += stock_pnl
                        capital += call_strike * 100
                        
                        logger.info(f"Month {month_count}: CALLED AWAY at ${call_strike:.2f} "
                                  f"(Stock: ${expiry_price:.2f}, Stock P&L: ${stock_pnl:.2f})")
                        
                        shares_owned = 0
                        put_strike = 0
                        call_strike = 0
                    else:
                        # Call expired worthless - keep shares and premium
                        logger.info(f"Month {month_count}: Call expired worthless "
                                  f"(Stock: ${expiry_price:.2f}, Strike: ${call_strike:.2f})")
                        # Keep shares, will sell another call next month
            
            # Track equity curve
            position_value = shares_owned * expiry_price if shares_owned > 0 else 0
            total_value = capital + position_value
            
            equity_curve.append({
                'date': expiry_date.isoformat(),
                'capital': capital,
                'position_value': position_value,
                'total_value': total_value,
                'shares_owned': shares_owned,
                'price': expiry_price,
                'month': month_count,
                'premiums_collected': total_premiums_collected,
                'stock_pnl': total_stock_pnl
            })
            
            # Move to next month
            current_date = expiry_date + timedelta(days=1)
        
        # Calculate final value
        final_price = df.iloc[-1]['close']
        final_position_value = shares_owned * final_price if shares_owned > 0 else 0
        final_value = capital + final_position_value
        
        logger.info(f"\n=== WHEEL BACKTEST SUMMARY ===")
        logger.info(f"Total Months: {month_count}")
        logger.info(f"Total Trades: {len(trades)}")
        logger.info(f"Total Premiums Collected: ${total_premiums_collected:.2f}")
        logger.info(f"Total Stock P&L: ${total_stock_pnl:.2f}")
        logger.info(f"Final Capital: ${capital:.2f}")
        logger.info(f"Final Position Value: ${final_position_value:.2f}")
        logger.info(f"Final Total Value: ${final_value:.2f}")
        logger.info(f"Total Return: {((final_value - starting_capital) / starting_capital * 100):+.2f}%")
        
        # Calculate results
        final_value = capital + (shares_owned * df['close'].iloc[-1] if shares_owned > 0 else 0)
        
        # Get trades from paper environment
        all_trades = self.paper.account.trades
        closed_trades = [t for t in all_trades if not t.is_open]
        winners = sum(1 for t in closed_trades if t.realized_pnl > 0)
        
        return BacktestResult(
            strategy_name='Wheel',
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=starting_capital,
            final_capital=final_value,
            total_return_pct=((final_value - starting_capital) / starting_capital) * 100,
            total_trades=len(all_trades),
            winning_trades=winners,
            losing_trades=len(closed_trades) - winners,
            win_rate=winners / len(closed_trades) if closed_trades else 0,
            avg_trade_return=np.mean([t.realized_pnl for t in closed_trades]) if closed_trades else 0,
            max_drawdown_pct=self._calculate_max_drawdown(equity_curve),
            sharpe_ratio=0.0,  # Would need risk-free rate calc
            equity_curve=equity_curve,
            trades=all_trades
        )
    
    def _empty_result(self, symbol, start, end, capital) -> BacktestResult:
        """Create empty result for failed backtest."""
        return BacktestResult(
            strategy_name='Wheel',
            symbol=symbol,
            start_date=start,
            end_date=end,
            initial_capital=capital,
            final_capital=capital,
            total_return_pct=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            avg_trade_return=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            equity_curve=[],
            trades=[]
        )
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
        """Calculate maximum drawdown percentage."""
        if not equity_curve:
            return 0.0
        
        values = [point['total_value'] for point in equity_curve]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd * 100


class MomentumBreakoutBacktester:
    """
    Backtester for Compra a Seco (Momentum Breakout) Strategy.
    
    Runs on historical 2-hour candle data to detect patterns and
    simulate trades with the exact strategy rules.
    """
    
    def __init__(
        self,
        client: TastyTradeClient,
        paper_env: PaperTradingEnvironment
    ):
        self.client = client
        self.paper = paper_env
        self.analyzer = TechnicalAnalyzer()
    
    def run_backtest(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        starting_capital: float = 100000.0,
        risk_per_trade: float = 0.02  # Risk 2% per trade
    ) -> BacktestResult:
        """
        Run momentum breakout backtest.
        
        This uses actual historical 2-hour data from TastyTrade API.
        """
        logger.info(f"Starting Momentum Breakout backtest for {symbol}")
        
        # Fetch 2-hour historical data
        df = self.client.get_2h_candles(
            symbol, 
            lookback_days=(end_date - start_date).days + 30  # Extra for pattern detection
        )
        
        if df.empty:
            logger.error(f"No historical 2H data for {symbol}")
            return self._empty_result(symbol, start_date, end_date, starting_capital)
        
        # Handle timezone-aware dates from yfinance by stripping timezone
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        
        # Ensure start_date and end_date are tz-naive
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)
        
        # Convert ALL data to candles for pattern detection (need enough history for EMAs)
        all_candles = self._df_to_candles(df)
        
        # Detect all setups in historical data
        all_setups = self.analyzer.find_compra_a_seco_setups(symbol, all_candles)
        
        # Filter setups to backtest period
        setups = [s for s in all_setups if start_date <= s.detected_at <= end_date]
        
        # Also filter candles to backtest period for trade simulation
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        candles = self._df_to_candles(df)
        
        logger.info(f"Found {len(setups)} setups in backtest period")
        
        # Simulate trades
        trades = []
        equity_curve = []
        capital = starting_capital
        
        for setup in setups:
            # Check if breakout occurred within window
            entry_idx = None
            pin_bar_idx = None
            
            # Find pin bar index by timestamp
            for i, candle in enumerate(candles):
                if candle.timestamp == setup.pin_bar_candle.timestamp:
                    pin_bar_idx = i
                    break
            
            if pin_bar_idx is None:
                continue  # Pin bar not found in candles
            
            for i, candle in enumerate(candles):
                if candle.timestamp > setup.detected_at:
                    # Check if we broke above pin bar high
                    if candle.high > setup.breakout_price:
                        entry_idx = i
                        break
                    # Check if window expired (3 candles after pin bar)
                    if i > pin_bar_idx + 3:
                        break
            
            if entry_idx is None:
                continue  # No breakout, skip this setup
            
            # Calculate position size (risk 2% of capital)
            risk_amount = capital * risk_per_trade
            stop_distance = setup.entry_price - setup.propulsion_candle.low
            
            if stop_distance <= 0:
                continue
            
            position_size = int(risk_amount / stop_distance)
            position_size = max(0, min(position_size, int(capital * 0.20 / setup.entry_price)))  # Max 20%
            
            if position_size == 0:
                continue
            
            # Execute entry
            entry_trade = self.paper.execute_stock_trade(
                symbol=symbol,
                quantity=position_size,
                action=TradeAction.BUY,
                market_price=setup.entry_price,
                timestamp=candles[entry_idx].timestamp,
                strategy='momentum_breakout'
            )
            
            if not entry_trade:
                continue
            
            trades.append(entry_trade)
            capital -= position_size * setup.entry_price
            
            # Simulate exit (target hit or time stop)
            exit_idx = None
            exit_price = None
            exit_reason = None
            
            for i in range(entry_idx + 1, min(entry_idx + 13, len(candles))):  # Max 12 bars
                candle = candles[i]
                
                # Check target hit
                if candle.high >= setup.target_price:
                    exit_idx = i
                    exit_price = setup.target_price
                    exit_reason = 'target'
                    break
                
                # Time stop
                if i >= entry_idx + 12:
                    exit_idx = i
                    exit_price = candle.close
                    exit_reason = 'timeout'
                    break
            
            if exit_idx:
                # Execute exit
                exit_trade = self.paper.execute_stock_trade(
                    symbol=symbol,
                    quantity=position_size,
                    action=TradeAction.SELL,
                    market_price=exit_price,
                    timestamp=candles[exit_idx].timestamp,
                    strategy='momentum_breakout'
                )
                
                if exit_trade:
                    trades.append(exit_trade)
                    capital += position_size * exit_price
                    
                    # Update trade with exit info
                    entry_trade.exit_price = exit_price
                    entry_trade.exit_timestamp = candles[exit_idx].timestamp
                    entry_trade.realized_pnl = position_size * (exit_price - setup.entry_price)
                    entry_trade.notes = f"Exit: {exit_reason}"
            
            # Track equity
            equity_curve.append({
                'date': candles[entry_idx].timestamp.isoformat(),
                'capital': capital,
                'trades_open': len([t for t in trades if t.is_open])
            })
        
        # Calculate results
        final_value = capital + self.paper.account.cash_balance
        
        # Get all trades from paper environment
        all_trades = self.paper.account.trades
        closed_trades = [t for t in all_trades if not t.is_open]
        winners = sum(1 for t in closed_trades if t.realized_pnl > 0)
        
        return BacktestResult(
            strategy_name='Compra a Seco (Momentum Breakout)',
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=starting_capital,
            final_capital=final_value,
            total_return_pct=((final_value - starting_capital) / starting_capital) * 100,
            total_trades=len(all_trades),
            winning_trades=winners,
            losing_trades=len(closed_trades) - winners,
            win_rate=winners / len(closed_trades) if closed_trades else 0,
            avg_trade_return=np.mean([t.realized_pnl for t in closed_trades]) if closed_trades else 0,
            max_drawdown_pct=self._calculate_max_drawdown(equity_curve),
            sharpe_ratio=0.0,
            equity_curve=equity_curve,
            trades=all_trades
        )
    
    def _df_to_candles(self, df: pd.DataFrame) -> List[Candle]:
        """Convert DataFrame to Candle objects."""
        candles = []
        for idx, row in df.iterrows():
            candles.append(Candle(
                timestamp=idx if isinstance(idx, datetime) else datetime.now(),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row.get('volume', 0))
            ))
        return candles
    
    def _empty_result(self, symbol, start, end, capital) -> BacktestResult:
        """Create empty result for failed backtest."""
        return BacktestResult(
            strategy_name='Compra a Seco',
            symbol=symbol,
            start_date=start,
            end_date=end,
            initial_capital=capital,
            final_capital=capital,
            total_return_pct=0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0,
            avg_trade_return=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            equity_curve=[],
            trades=[]
        )
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> float:
        """Calculate maximum drawdown."""
        if not equity_curve:
            return 0.0
        
        values = [point['capital'] for point in equity_curve]
        peak = values[0]
        max_dd = 0.0
        
        for value in values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        return max_dd * 100


def run_backtest_suite(
    client: TastyTradeClient,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    strategies: List[str] = ['wheel', 'momentum']
) -> Dict[str, List[BacktestResult]]:
    """
    Run backtest suite for multiple symbols and strategies.
    
    Args:
        client: TastyTrade API client
        symbols: List of symbols to test
        start_date: Backtest start date
        end_date: Backtest end date
        strategies: List of strategies to test ('wheel', 'momentum')
        
    Returns:
        Dictionary mapping strategy names to lists of results
    """
    results = {'wheel': [], 'momentum': []}
    
    for symbol in symbols:
        symbol = symbol.upper()
        
        if 'wheel' in strategies:
            logger.info(f"Backtesting Wheel on {symbol}")
            paper = PaperTradingEnvironment(starting_balance=100000.0)
            backtester = WheelStrategyBacktester(client, paper)
            result = backtester.run_backtest(symbol, start_date, end_date)
            results['wheel'].append(result)
        
        if 'momentum' in strategies:
            logger.info(f"Backtesting Momentum Breakout on {symbol}")
            paper = PaperTradingEnvironment(starting_balance=100000.0)
            backtester = MomentumBreakoutBacktester(client, paper)
            result = backtester.run_backtest(symbol, start_date, end_date)
            results['momentum'].append(result)
    
    return results


def print_backtest_summary(results: Dict[str, List[BacktestResult]]):
    """Print formatted backtest summary."""
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 80)
    
    for strategy_name, strategy_results in results.items():
        print(f"\n{strategy_name.upper()} STRATEGY")
        print("-" * 80)
        
        for result in strategy_results:
            print(f"\n{result.symbol}:")
            print(f"  Period:         {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
            print(f"  Initial:        ${result.initial_capital:,.2f}")
            print(f"  Final:          ${result.final_capital:,.2f}")
            print(f"  Return:         {result.total_return_pct:+.2f}%")
            print(f"  Trades:         {result.total_trades}")
            print(f"  Win Rate:       {result.win_rate:.1%}")
            print(f"  Max Drawdown:   {result.max_drawdown_pct:.2f}%")
    
    print("\n" + "=" * 80)


def export_backtest_report(results: Dict[str, List[BacktestResult]], filename: str):
    """Export backtest results to JSON file."""
    export_data = {
        'generated_at': datetime.now().isoformat(),
        'results': {
            strategy: [r.to_dict() for r in results_list]
            for strategy, results_list in results.items()
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    logger.info(f"Backtest report exported to {filename}")
