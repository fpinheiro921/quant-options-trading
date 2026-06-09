"""
Compra a Seco Strategy - Momentum Breakout Trading System.

A technical analysis based strategy that identifies momentum breakouts
using candlestick patterns and EMA divergence.

Strategy Rules (120-minute timeframe):
1. Trend: Bull run (EMA 8 > EMA 80)
2. Setup: Propulsion candle (≥2x average body) followed by pin bar
3. Entry: Breakout above pin bar high within 3 candles
4. Target: 2x propulsion candle amplitude
5. Stop: Time-based exit after 12 bars if target not hit

American market focus, especially tech stocks.
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import pandas as pd

from api.tastytrade_client import TastyTradeClient
from models.technical_analysis import (
    TechnicalAnalyzer, Candle, CompraASecoSetup, EMADivergence
)
from config import Config

logger = logging.getLogger(__name__)


class StrategyState(Enum):
    """State of the Compra a Seco strategy."""
    SCANNING = "scanning"           # Looking for setup
    SETUP_DETECTED = "setup"        # Propulsion + pin bar found, waiting for breakout
    IN_POSITION = "in_position"     # Bought on breakout
    TARGET_HIT = "target"           # Reached profit target
    TIME_STOP = "timeout"           # Exited on time stop


@dataclass
class BreakoutTrade:
    """Represents a completed or active breakout trade."""
    symbol: str
    entry_time: datetime
    entry_price: float
    target_price: float
    setup_reference: CompraASecoSetup
    
    # Trade status
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    contracts: int = 1
    pnl: float = 0.0
    exit_reason: Optional[str] = None  # 'target', 'timeout', 'manual'
    
    @property
    def is_open(self) -> bool:
        return self.exit_price is None
    
    @property
    def target_distance_pct(self) -> float:
        if self.entry_price == 0:
            return 0
        return (self.target_price - self.entry_price) / self.entry_price
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'entry_time': self.entry_time.isoformat(),
            'entry_price': round(self.entry_price, 2),
            'target_price': round(self.target_price, 2),
            'exit_price': round(self.exit_price, 2) if self.exit_price else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'contracts': self.contracts,
            'pnl': round(self.pnl, 2),
            'exit_reason': self.exit_reason,
            'is_open': self.is_open,
            'target_distance_pct': round(self.target_distance_pct, 4),
        }


@dataclass
class StrategyPerformance:
    """Performance metrics for the strategy."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 4),
            'avg_profit': round(self.avg_profit, 2),
            'avg_loss': round(self.avg_loss, 2),
            'profit_factor': round(self.profit_factor, 2),
            'max_drawdown': round(self.max_drawdown, 2),
        }


class CompraASecoStrategy:
    """
    Implements the Compra a Seco (Momentum Breakout) Strategy.
    
    This strategy trades momentum breakouts using candlestick patterns
    on the 120-minute timeframe, targeting tech stocks in the American market.
    """
    
    def __init__(self, client: TastyTradeClient):
        """Initialize the strategy."""
        self.client = client
        self.analyzer = TechnicalAnalyzer()
        
        # Configuration
        self.timeframe = 120  # 2-hour candles
        self.propulsion_multiplier = 2.0
        self.target_multiplier = 2.0
        self.breakout_max_bars = 3
        self.time_stop_bars = 12
        
        # State tracking
        self.active_setups: Dict[str, CompraASecoSetup] = {}
        self.active_trades: Dict[str, BreakoutTrade] = {}
        self.trade_history: List[BreakoutTrade] = []
        self.watchlist: List[str] = []
        
        logger.info("Compra a Seco strategy initialized (120-min timeframe)")
    
    def add_to_watchlist(self, symbols: List[str]):
        """Add symbols to the watchlist for monitoring."""
        for symbol in symbols:
            if symbol.upper() not in self.watchlist:
                self.watchlist.append(symbol.upper())
        logger.info(f"Watchlist: {self.watchlist}")
    
    def fetch_historical_data(
        self,
        symbol: str,
        lookback_days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data for analysis from TastyTrade API.
        
        Gets 120-minute (2-hour) candles for the Compra a Seco strategy.
        """
        try:
            # Use the TastyTrade client to get 2-hour candles
            df = self.client.get_2h_candles(symbol, lookback_days)
            
            if df.empty:
                logger.warning(f"No historical data returned for {symbol}")
                return None
            
            logger.info(f"Fetched {len(df)} 2H candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return None
    
    def scan_for_setups(self, symbol: str, candles: List[Candle]) -> List[CompraASecoSetup]:
        """
        Scan for Compra a Seco setups in historical data.
        
        Args:
            symbol: Stock symbol
            candles: List of Candle objects (120-min timeframe)
            
        Returns:
            List of detected setups
        """
        setups = self.analyzer.find_compra_a_seco_setups(symbol, candles)
        
        logger.info(f"Found {len(setups)} setups for {symbol}")
        
        # Update active setups
        for setup in setups:
            key = f"{symbol}_{setup.detected_at.timestamp()}"
            if key not in self.active_setups:
                self.active_setups[key] = setup
        
        return setups
    
    def scan_symbol(self, symbol: str, lookback_days: int = 30) -> List[CompraASecoSetup]:
        """
        Scan a symbol for Compra a Seco setups using TastyTrade API data.
        
        This is the main entry point for the dashboard/API.
        
        Args:
            symbol: Stock symbol to scan
            lookback_days: Days of historical data to fetch
            
        Returns:
            List of detected setups
        """
        # Fetch historical data from TastyTrade API
        df = self.fetch_historical_data(symbol, lookback_days)
        
        if df is None or df.empty:
            logger.warning(f"No data available for {symbol}")
            return []
        
        # Convert DataFrame to Candle objects
        candles = self.analyzer.get_recent_candles_from_dataframe(df, len(df))
        
        # Scan for setups
        setups = self.scan_for_setups(symbol, candles)
        
        return setups
    
    def check_active_setups(self, symbol: str, current_candle: Candle) -> List[str]:
        """
        Check if any active setups have triggered (breakout occurred).
        
        Returns list of triggered setup keys that resulted in trades.
        """
        triggered = []
        
        for key, setup in list(self.active_setups.items()):
            if not setup.symbol == symbol:
                continue
            
            if not setup.is_active or setup.was_triggered:
                continue
            
            # Check for breakout
            if current_candle.high > setup.breakout_price:
                # Entry triggered - create trade
                trade = BreakoutTrade(
                    symbol=symbol,
                    entry_time=current_candle.timestamp,
                    entry_price=setup.entry_price,
                    target_price=setup.target_price,
                    setup_reference=setup,
                    contracts=1,  # Fixed size for now
                )
                
                trade_key = f"{symbol}_{current_candle.timestamp.timestamp()}"
                self.active_trades[trade_key] = trade
                
                setup.was_triggered = True
                triggered.append(trade_key)
                
                logger.info(f"Breakout triggered for {symbol} at {setup.entry_price:.2f}")
        
        return triggered
    
    def check_active_trades(
        self,
        symbol: str,
        current_price: float,
        current_time: datetime
    ) -> List[str]:
        """
        Check active trades for target hit or time stop.
        
        Returns list of closed trade keys.
        """
        closed = []
        
        for key, trade in list(self.active_trades.items()):
            if not trade.symbol == symbol:
                continue
            
            if not trade.is_open:
                continue
            
            bars_elapsed = self._calculate_bars_elapsed(
                trade.entry_time, current_time
            )
            
            # Check target hit
            if current_price >= trade.target_price:
                trade.exit_price = trade.target_price
                trade.exit_time = current_time
                trade.pnl = (trade.target_price - trade.entry_price) * trade.contracts * 100
                trade.exit_reason = 'target'
                
                self.trade_history.append(trade)
                closed.append(key)
                
                logger.info(f"Target hit for {symbol}: ${trade.pnl:.2f}")
            
            # Check time stop
            elif bars_elapsed >= self.time_stop_bars:
                trade.exit_price = current_price
                trade.exit_time = current_time
                trade.pnl = (current_price - trade.entry_price) * trade.contracts * 100
                trade.exit_reason = 'timeout'
                
                self.trade_history.append(trade)
                closed.append(key)
                
                logger.info(f"Time stop for {symbol}: ${trade.pnl:.2f}")
        
        return closed
    
    def _calculate_bars_elapsed(self, start: datetime, end: datetime) -> int:
        """Calculate number of 120-minute bars elapsed."""
        diff = end - start
        minutes = diff.total_seconds() / 60
        bars = int(minutes / self.timeframe)
        return max(0, bars)
    
    def get_active_setups_summary(self) -> List[Dict]:
        """Get summary of all active setups."""
        return [setup.to_dict() for setup in self.active_setups.values() if setup.is_active]
    
    def get_active_trades_summary(self) -> List[Dict]:
        """Get summary of all active trades."""
        return [trade.to_dict() for trade in self.active_trades.values() if trade.is_open]
    
    def get_trade_history_summary(self) -> List[Dict]:
        """Get trade history."""
        return [trade.to_dict() for trade in self.trade_history]
    
    def calculate_performance(self) -> StrategyPerformance:
        """Calculate strategy performance metrics."""
        if not self.trade_history:
            return StrategyPerformance(0, 0, 0, 0, 0, 0, 0, 0)
        
        closed_trades = [t for t in self.trade_history if not t.is_open]
        
        if not closed_trades:
            return StrategyPerformance(0, 0, 0, 0, 0, 0, 0, 0)
        
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        
        avg_profit = (
            sum(t.pnl for t in winning_trades) / len(winning_trades)
            if winning_trades else 0
        )
        
        avg_loss = (
            sum(t.pnl for t in losing_trades) / len(losing_trades)
            if losing_trades else 0
        )
        
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Calculate max drawdown (simplified)
        cumulative = 0
        max_dd = 0
        peak = 0
        for trade in closed_trades:
            cumulative += trade.pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        
        return StrategyPerformance(
            total_trades=len(closed_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            max_drawdown=max_dd
        )
    
    def manual_entry(self, symbol: str, entry_price: float, current_time: datetime) -> Optional[str]:
        """Manual entry for testing or when setup is detected externally."""
        # Create synthetic setup
        setup = CompraASecoSetup(
            symbol=symbol,
            detected_at=current_time,
            propulsion_candle=Candle(current_time, entry_price * 0.98, entry_price * 1.02, 
                                      entry_price * 0.97, entry_price, 0),
            pin_bar_candle=Candle(current_time, entry_price * 0.995, entry_price * 1.005,
                                   entry_price * 0.994, entry_price * 0.995, 0),
            breakout_price=entry_price,
            target_price=entry_price * 1.02,  # 2% target as placeholder
            stop_time_bars=self.time_stop_bars,
            ema_status=EMADivergence(entry_price, entry_price * 0.99, entry_price * 0.01, True),
            propulsion_amplitude=entry_price * 0.02,
            entry_price=entry_price,
            was_triggered=True,
        )
        
        trade = BreakoutTrade(
            symbol=symbol,
            entry_time=current_time,
            entry_price=entry_price,
            target_price=setup.target_price,
            setup_reference=setup,
            contracts=1,
        )
        
        key = f"{symbol}_{current_time.timestamp()}_manual"
        self.active_trades[key] = trade
        
        logger.info(f"Manual entry for {symbol} at {entry_price:.2f}")
        return key
    
    def manual_exit(self, trade_key: str, exit_price: float, current_time: datetime, reason: str = 'manual'):
        """Manual exit for a trade."""
        if trade_key not in self.active_trades:
            logger.error(f"Trade {trade_key} not found")
            return False
        
        trade = self.active_trades[trade_key]
        
        if not trade.is_open:
            logger.warning(f"Trade {trade_key} already closed")
            return False
        
        trade.exit_price = exit_price
        trade.exit_time = current_time
        trade.pnl = (exit_price - trade.entry_price) * trade.contracts * 100
        trade.exit_reason = reason
        
        self.trade_history.append(trade)
        
        logger.info(f"Manual exit for {trade.symbol}: ${trade.pnl:.2f}")
        return True
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get complete strategy status."""
        performance = self.calculate_performance()
        
        return {
            'watchlist': self.watchlist,
            'timeframe': self.timeframe,
            'active_setups_count': len([s for s in self.active_setups.values() if s.is_active]),
            'active_trades_count': len([t for t in self.active_trades.values() if t.is_open]),
            'total_trades_history': len(self.trade_history),
            'performance': performance.to_dict(),
            'active_setups': self.get_active_setups_summary(),
            'active_trades': self.get_active_trades_summary(),
        }


def create_default_watchlist() -> List[str]:
    """Create default watchlist for tech stocks."""
    return [
        'NVDA',  # NVIDIA
        'AAPL',  # Apple
        'MSFT',  # Microsoft
        'GOOGL', # Alphabet
        'AMZN',  # Amazon
        'META',  # Meta
        'TSLA',  # Tesla
        'AMD',   # AMD
        'CRM',   # Salesforce
        'NFLX',  # Netflix
    ]
