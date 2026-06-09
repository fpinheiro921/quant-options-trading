"""Trading module for options strategies."""
from .strike_resolver import StrikeResolver, OptionCandidate
from .wheel_strategy import WheelStrategy, WheelState, PositionAnalysis, TradeRecommendation
from .momentum_breakout import (
    CompraASecoStrategy, 
    CompraASecoSetup, 
    BreakoutTrade,
    StrategyState,
    create_default_watchlist
)

__all__ = [
    'StrikeResolver', 
    'OptionCandidate',
    'WheelStrategy',
    'WheelState',
    'PositionAnalysis',
    'TradeRecommendation',
    'CompraASecoStrategy',
    'CompraASecoSetup',
    'BreakoutTrade',
    'StrategyState',
    'create_default_watchlist',
]
