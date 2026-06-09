"""
Technical Analysis Module for Candlestick Patterns and Indicators.

Implements pattern recognition for the Compra a Seco strategy:
- EMA (Exponential Moving Average) for trend detection
- Candlestick body analysis
- Pin bar / Doji detection
- Propulsion candle identification
- Breakout detection
"""
import logging
from typing import List, Dict, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class CandlePattern(Enum):
    """Candlestick pattern types."""
    PROPULSION = "propulsion"  # Large momentum candle
    PIN_BAR = "pin_bar"        # Small indecision candle
    DOJI = "doji"             # Open ≈ Close
    NONE = "none"


@dataclass
class Candle:
    """Represents a single candlestick."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    
    @property
    def body(self) -> float:
        """Candle body size (absolute)."""
        return abs(self.close - self.open)
    
    @property
    def body_pct(self) -> float:
        """Body as percentage of range."""
        range_val = self.high - self.low
        return self.body / range_val if range_val > 0 else 0
    
    @property
    def is_bullish(self) -> bool:
        """True if bullish candle."""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """True if bearish candle."""
        return self.close < self.open
    
    @property
    def upper_shadow(self) -> float:
        """Upper shadow size."""
        top = max(self.open, self.close)
        return self.high - top
    
    @property
    def lower_shadow(self) -> float:
        """Lower shadow size."""
        bottom = min(self.open, self.close)
        return bottom - self.low
    
    @property
    def range(self) -> float:
        """Total range (high - low)."""
        return self.high - self.low
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'body': self.body,
            'is_bullish': self.is_bullish,
        }


@dataclass  
class EMADivergence:
    """EMA divergence status for trend detection."""
    ema_fast: float      # EMA 8
    ema_slow: float      # EMA 80
    divergence: float    # Distance between EMAs
    is_bull_run: bool    # EMA 8 > EMA 80 and diverging
    
    def to_dict(self) -> Dict:
        return {
            'ema_fast': round(self.ema_fast, 4),
            'ema_slow': round(self.ema_slow, 4),
            'divergence': round(self.divergence, 4),
            'is_bull_run': self.is_bull_run,
        }


@dataclass
class CompraASecoSetup:
    """Complete setup for Compra a Seco strategy."""
    symbol: str
    detected_at: datetime
    propulsion_candle: Candle
    pin_bar_candle: Candle
    breakout_price: float
    target_price: float
    stop_time_bars: int
    ema_status: EMADivergence
    
    # Calculated values
    propulsion_amplitude: float
    entry_price: float
    
    # Status
    is_active: bool = True
    bars_since_setup: int = 0
    was_triggered: bool = False
    was_completed: bool = False
    result: Optional[str] = None  # 'target', 'timeout', 'manual'
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'detected_at': self.detected_at.isoformat(),
            'propulsion_candle': self.propulsion_candle.to_dict(),
            'pin_bar_candle': self.pin_bar_candle.to_dict(),
            'breakout_price': round(self.breakout_price, 2),
            'target_price': round(self.target_price, 2),
            'propulsion_amplitude': round(self.propulsion_amplitude, 2),
            'entry_price': round(self.entry_price, 2),
            'ema_status': self.ema_status.to_dict(),
            'is_active': self.is_active,
            'bars_since_setup': self.bars_since_setup,
            'was_triggered': self.was_triggered,
            'was_completed': self.was_completed,
            'result': self.result,
        }


class TechnicalAnalyzer:
    """
    Technical analysis utilities for pattern recognition.
    """
    
    def __init__(self):
        """Initialize analyzer."""
        self.ema_fast_period = 8
        self.ema_slow_period = 80
        self.propulsion_multiplier = 2.0  # 2x average body
        self.pin_bar_max_body_pct = 0.20   # Max 20% of range
        self.breakout_max_bars = 3         # Must breakout within 3 bars
        self.target_multiplier = 2.0       # 2x propulsion amplitude
        self.time_stop_bars = 12           # 12-bar time stop
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return []
        
        # Convert to numpy for efficient calculation
        prices_arr = np.array(prices)
        
        # EMA formula: EMA_t = α * Price_t + (1-α) * EMA_{t-1}
        # where α = 2 / (period + 1)
        alpha = 2.0 / (period + 1)
        
        ema = np.zeros_like(prices_arr)
        ema[0] = prices_arr[0]  # Initialize with first price
        
        for i in range(1, len(prices_arr)):
            ema[i] = alpha * prices_arr[i] + (1 - alpha) * ema[i-1]
        
        return ema.tolist()
    
    def check_ema_divergence(
        self,
        candles: List[Candle],
        current_idx: int
    ) -> EMADivergence:
        """
        Check if EMA 8 is diverging from EMA 80 (bull run).
        
        Bull run = EMA 8 > EMA 80 and distance is increasing
        """
        if current_idx < self.ema_slow_period:
            return EMADivergence(0, 0, 0, False)
        
        # Get closing prices
        closes = [c.close for c in candles[:current_idx + 1]]
        
        # Calculate EMAs
        ema_fast = self.calculate_ema(closes, self.ema_fast_period)
        ema_slow = self.calculate_ema(closes, self.ema_slow_period)
        
        if not ema_fast or not ema_slow:
            return EMADivergence(0, 0, 0, False)
        
        current_fast = ema_fast[-1]
        current_slow = ema_slow[-1]
        
        # Calculate divergence
        divergence = current_fast - current_slow
        
        # Bull run: EMA 8 above EMA 80
        is_bull_run = current_fast > current_slow
        
        return EMADivergence(current_fast, current_slow, divergence, is_bull_run)
    
    def detect_propulsion_candle(
        self,
        candles: List[Candle],
        idx: int,
        lookback: int = 20
    ) -> Tuple[bool, float]:
        """
        Detect if candle at idx is a propulsion candle.
        
        Propulsion = Body size ≥ 2x average body size over lookback period
        
        Returns: (is_propulsion, average_body)
        """
        if idx < lookback or idx >= len(candles):
            return False, 0
        
        current_candle = candles[idx]
        
        # Calculate average body size over lookback period
        lookback_candles = candles[idx - lookback:idx]
        bodies = [c.body for c in lookback_candles]
        avg_body = np.mean(bodies)
        
        if avg_body == 0:
            return False, 0
        
        # Check if current body is ≥ 2x average
        is_propulsion = current_candle.body >= (avg_body * self.propulsion_multiplier)
        
        return is_propulsion, avg_body
    
    def detect_pin_bar(self, candle: Candle) -> bool:
        """
        Detect if a candle is a pin bar / tiny candle (indecision).
        
        Pin bar = Small body relative to range (≤20% of range)
        """
        if candle.range == 0:
            return False
        
        # Body is small relative to total range
        body_pct = candle.body / candle.range
        
        # Also check that it's relatively small in absolute terms
        # or has long shadows indicating indecision
        long_shadows = (candle.upper_shadow + candle.lower_shadow) > candle.body * 2
        
        return body_pct <= self.pin_bar_max_body_pct or long_shadows
    
    def detect_doji(self, candle: Candle, tolerance: float = 0.01) -> bool:
        """
        Detect doji pattern (open ≈ close).
        
        Args:
            candle: The candle to check
            tolerance: Maximum percentage difference between open and close
        """
        if candle.range == 0:
            return False
        
        body_pct = candle.body / candle.range
        return body_pct <= tolerance
    
    def find_compra_a_seco_setups(
        self,
        symbol: str,
        candles: List[Candle]
    ) -> List[CompraASecoSetup]:
        """
        Find all Compra a Seco setups in the candle series.
        
        Pattern:
        1. Bull run (EMA 8 > EMA 80)
        2. Propulsion candle (large body)
        3. Pin bar next (small body - indecision)
        4. Breakout above pin bar high within 3 candles
        """
        setups = []
        
        if len(candles) < self.ema_slow_period + 10:
            return setups
        
        for i in range(self.ema_slow_period, len(candles) - 4):
            # Step 1: Check EMA divergence (bull run)
            ema_status = self.check_ema_divergence(candles, i)
            
            if not ema_status.is_bull_run:
                continue
            
            # Step 2: Check for propulsion candle
            is_propulsion, avg_body = self.detect_propulsion_candle(candles, i)
            
            if not is_propulsion:
                continue
            
            propulsion_candle = candles[i]
            
            # Step 3: Check next candle for pin bar
            if i + 1 >= len(candles):
                continue
            
            next_candle = candles[i + 1]
            
            if not self.detect_pin_bar(next_candle):
                continue
            
            pin_bar_candle = next_candle
            
            # Step 4: Look for breakout in next 3 candles
            breakout_price = pin_bar_candle.high
            entry_price = breakout_price + 0.01  # Breakout + 1 cent
            
            # Calculate target based on propulsion candle amplitude
            # Amplitude = high - low of propulsion candle
            propulsion_amplitude = propulsion_candle.range
            target_price = entry_price + (propulsion_amplitude * self.target_multiplier)
            
            # Check if breakout occurs within 3 candles
            for j in range(i + 2, min(i + 2 + self.breakout_max_bars, len(candles))):
                if candles[j].high > breakout_price:
                    # Breakout detected - create setup
                    setup = CompraASecoSetup(
                        symbol=symbol,
                        detected_at=candles[i].timestamp,
                        propulsion_candle=propulsion_candle,
                        pin_bar_candle=pin_bar_candle,
                        breakout_price=breakout_price,
                        target_price=target_price,
                        stop_time_bars=self.time_stop_bars,
                        ema_status=ema_status,
                        propulsion_amplitude=propulsion_amplitude,
                        entry_price=entry_price,
                        is_active=True,
                    )
                    setups.append(setup)
                    break
        
        return setups
    
    def check_setup_status(
        self,
        setup: CompraASecoSetup,
        candles: List[Candle],
        from_idx: int
    ) -> CompraASecoSetup:
        """
        Update setup status based on subsequent price action.
        
        Returns updated setup with result status.
        """
        if not setup.is_active or setup.was_completed:
            return setup
        
        # Count bars since setup detection
        bars_since = 0
        
        for i in range(from_idx, min(from_idx + setup.stop_time_bars, len(candles))):
            candle = candles[i]
            bars_since += 1
            
            # Check if target hit
            if candle.high >= setup.target_price:
                setup.was_completed = True
                setup.result = 'target'
                setup.is_active = False
                return setup
            
            # Check time stop
            if bars_since >= setup.stop_time_bars:
                setup.was_completed = True
                setup.result = 'timeout'
                setup.is_active = False
                return setup
        
        setup.bars_since_setup = bars_since
        return setup
    
    def get_recent_candles_from_dataframe(
        self,
        df: pd.DataFrame,
        periods: int = 100
    ) -> List[Candle]:
        """Convert DataFrame to Candle objects."""
        candles = []
        
        for idx, row in df.tail(periods).iterrows():
            candle = Candle(
                timestamp=idx if isinstance(idx, datetime) else datetime.now(),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                close=float(row['close']),
                volume=int(row.get('volume', 0))
            )
            candles.append(candle)
        
        return candles


# Utility functions for pattern visualization
def format_candle_for_chart(candle: Candle) -> Dict:
    """Format candle for charting library."""
    return {
        'x': candle.timestamp.isoformat(),
        'open': candle.open,
        'high': candle.high,
        'low': candle.low,
        'close': candle.close,
        'volume': candle.volume,
    }


def calculate_pattern_statistics(setups: List[CompraASecoSetup]) -> Dict:
    """Calculate statistics from completed setups."""
    if not setups:
        return {}
    
    completed = [s for s in setups if s.was_completed]
    targets_hit = [s for s in completed if s.result == 'target']
    timeouts = [s for s in completed if s.result == 'timeout']
    
    win_rate = len(targets_hit) / len(completed) if completed else 0
    
    return {
        'total_setups': len(setups),
        'completed': len(completed),
        'targets_hit': len(targets_hit),
        'timeouts': len(timeouts),
        'win_rate': round(win_rate, 4),
        'avg_target_distance': round(
            np.mean([s.target_price - s.entry_price for s in setups]), 2
        ) if setups else 0,
    }
