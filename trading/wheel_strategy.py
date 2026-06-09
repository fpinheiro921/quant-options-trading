"""
Wheel Trading Strategy Implementation.

The Wheel Strategy:
1. Own stock → Sell covered calls
2. If assigned (stock sold) → Sell cash-secured puts
3. If assigned on put (stock bought) → Sell covered calls
4. Repeat in a cycle ("the wheel")

Based on the Quant Guild methodology and the papers that built quant finance:
- Black-Scholes (1973): Risk-neutral pricing and implied volatility
- Dupire (1994): Local volatility for the volatility surface
- Bachelier (1900): Brownian motion in finance
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from api.tastytrade_client import TastyTradeClient
from trading.strike_resolver import StrikeResolver, OptionCandidate
from config import TradingConfig, Config

logger = logging.getLogger(__name__)


class WheelState(Enum):
    """State of the wheel strategy for a symbol."""
    NO_POSITION = "no_position"
    OWN_STOCK = "own_stock"  # Ready to sell covered calls
    SHORT_CALL = "short_call"  # Have sold a call
    SHORT_PUT = "short_put"    # Have sold a put (no stock)
    BOTH_OPTIONS = "both_options"  # Rare: both call and put


@dataclass
class PositionAnalysis:
    """Analysis of a position for wheel strategy."""
    symbol: str
    state: WheelState
    shares_owned: int = 0
    cost_basis: float = 0.0
    current_price: float = 0.0
    stock_pnl: float = 0.0
    
    # Option position
    option_symbol: Optional[str] = None
    option_type: Optional[str] = None  # 'call' or 'put'
    option_strike: Optional[float] = None
    option_expiry: Optional[datetime] = None
    option_delta: Optional[float] = None
    option_premium: float = 0.0
    option_pnl: float = 0.0
    contracts: int = 0
    
    # Assignment analysis
    assignment_probability: float = 0.0
    assignment_pnl: float = 0.0  # P&L if assigned
    new_cost_basis_if_assigned: Optional[float] = None
    cash_obligation: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'state': self.state.value,
            'shares_owned': self.shares_owned,
            'cost_basis': round(self.cost_basis, 2),
            'current_price': round(self.current_price, 2),
            'stock_pnl': round(self.stock_pnl, 2),
            'option_symbol': self.option_symbol,
            'option_type': self.option_type,
            'option_strike': self.option_strike,
            'option_expiry': self.option_expiry.isoformat() if self.option_expiry else None,
            'option_delta': round(self.option_delta, 4) if self.option_delta else None,
            'option_premium': round(self.option_premium, 2),
            'option_pnl': round(self.option_pnl, 2),
            'contracts': self.contracts,
            'assignment_probability': round(self.assignment_probability, 2),
            'assignment_pnl': round(self.assignment_pnl, 2),
            'new_cost_basis_if_assigned': round(self.new_cost_basis_if_assigned, 2) if self.new_cost_basis_if_assigned else None,
            'cash_obligation': round(self.cash_obligation, 2),
        }


@dataclass
class TradeRecommendation:
    """A trade recommendation for the wheel strategy."""
    symbol: str
    action: str  # 'sell_call', 'sell_put', 'buy_stock', 'wait'
    candidate: OptionCandidate
    quantity: int
    expected_premium: float
    max_profit: float
    max_loss: float
    break_even: float
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'action': self.action,
            'option': self.candidate.to_dict(),
            'quantity': self.quantity,
            'expected_premium': round(self.expected_premium, 2),
            'max_profit': round(self.max_profit, 2),
            'max_loss': round(self.max_loss, 2),
            'break_even': round(self.break_even, 2),
            'reasoning': self.reasoning,
        }


class WheelStrategy:
    """
    Implements the Wheel Trading Strategy.
    
    Core principle from the five papers that built quant finance:
    1. Use delta to quantify assignment probability (Black-Scholes)
    2. Select strikes based on cost basis relationship
    3. Manage risk through diversification and position sizing
    """
    
    def __init__(
        self,
        client: TastyTradeClient,
        strike_resolver: StrikeResolver,
        target_delta: float = 0.30
    ):
        """Initialize wheel strategy."""
        self.client = client
        self.resolver = strike_resolver
        self.target_delta = target_delta
        self.config = TradingConfig()
    
    def analyze_position(self, symbol: str) -> PositionAnalysis:
        """
        Analyze current position state for a symbol.
        
        Determines where we are in the wheel cycle:
        - Do we own stock?
        - Do we have open option positions?
        - What should we do next?
        """
        analysis = PositionAnalysis(symbol=symbol, state=WheelState.NO_POSITION)
        
        # Get stock position
        stock_positions = self.client.get_stock_positions()
        stock_pos = next((p for p in stock_positions if p['symbol'] == symbol), None)
        
        if stock_pos:
            analysis.shares_owned = stock_pos['quantity']
            analysis.cost_basis = stock_pos['average_price']
            analysis.stock_pnl = stock_pos['unrealized_pnl']
        
        # Get option positions for this symbol
        option_positions = self.client.get_option_positions()
        symbol_options = [
            p for p in option_positions 
            if symbol in p['symbol'] or any(
                part in p['symbol'] for part in [symbol + ' ', symbol + str(datetime.now().year)[2:]]
            )
        ]
        
        # Get current price
        try:
            quote = self.client.get_stock_quote(symbol)
            analysis.current_price = quote.get('last_price') or quote.get('spot_price', 0)
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            analysis.current_price = analysis.cost_basis  # Fallback
        
        # Determine state
        if symbol_options:
            # Analyze option positions
            for opt in symbol_options:
                opt_symbol = opt['symbol']
                quantity = opt['quantity']
                
                # Determine if call or put
                # TastyTrade option symbols contain expiration info
                # Format is typically: SYMBOL YYMMDD C/P STRIKE
                if 'C' in opt_symbol.upper():
                    analysis.option_type = 'call'
                    analysis.state = WheelState.SHORT_CALL if quantity < 0 else WheelState.NO_POSITION
                elif 'P' in opt_symbol.upper():
                    analysis.option_type = 'put'
                    analysis.state = WheelState.SHORT_PUT if quantity < 0 else WheelState.NO_POSITION
                
                analysis.option_symbol = opt_symbol
                analysis.contracts = abs(quantity)
                analysis.option_pnl = opt['unrealized_pnl']
                
                # Extract strike from symbol (approximate)
                # Try to get from API if possible
                try:
                    option_details = self._parse_option_symbol(opt_symbol)
                    analysis.option_strike = option_details.get('strike')
                    analysis.option_expiry = option_details.get('expiration')
                except:
                    pass
        elif analysis.shares_owned > 0:
            analysis.state = WheelState.OWN_STOCK
        
        # Calculate assignment metrics if we have an option position
        if analysis.option_type and analysis.option_strike:
            self._calculate_assignment_metrics(analysis)
        
        return analysis
    
    def _parse_option_symbol(self, symbol: str) -> Dict[str, Any]:
        """Parse option symbol to extract details."""
        # TastyTrade format: SYMBOL YYMMDD C/P STRIKE
        parts = symbol.split()
        if len(parts) >= 3:
            try:
                exp_str = parts[1]
                year = 2000 + int(exp_str[:2])
                month = int(exp_str[2:4])
                day = int(exp_str[4:6])
                expiration = datetime(year, month, day)
                
                option_type = 'C' if 'C' in parts[2].upper() else 'P'
                strike = float(parts[-1]) if parts[-1].replace('.', '').isdigit() else 0
                
                return {
                    'expiration': expiration,
                    'option_type': option_type,
                    'strike': strike,
                    'underlying': parts[0]
                }
            except (ValueError, IndexError):
                pass
        
        return {}
    
    def _calculate_assignment_metrics(self, analysis: PositionAnalysis):
        """Calculate assignment probability and P&L."""
        if not analysis.option_strike:
            return
        
        # Use delta as proxy for assignment probability
        if analysis.option_delta:
            analysis.assignment_probability = abs(analysis.option_delta)
        
        # Calculate assignment P&L
        if analysis.option_type == 'call':
            # Call assignment: sell stock at strike
            if analysis.shares_owned > 0:
                stock_pnl = (analysis.option_strike - analysis.cost_basis) * analysis.shares_owned
                total_pnl = stock_pnl + analysis.option_premium * analysis.contracts * 100
                analysis.assignment_pnl = total_pnl
        
        elif analysis.option_type == 'put':
            # Put assignment: buy stock at strike
            cash_obligation = analysis.option_strike * analysis.contracts * 100
            analysis.cash_obligation = cash_obligation
            
            # Calculate new cost basis if assigned
            if analysis.contracts > 0:
                total_cost = cash_obligation - (analysis.option_premium * analysis.contracts * 100)
                new_shares = analysis.contracts * 100
                
                if analysis.shares_owned > 0:
                    # Blend with existing position
                    total_shares = analysis.shares_owned + new_shares
                    total_basis = (analysis.cost_basis * analysis.shares_owned + total_cost)
                    analysis.new_cost_basis_if_assigned = total_basis / total_shares
                else:
                    analysis.new_cost_basis_if_assigned = total_cost / new_shares
    
    def generate_recommendations(
        self,
        symbol: str,
        analysis: Optional[PositionAnalysis] = None
    ) -> List[TradeRecommendation]:
        """Generate trade recommendations based on current state."""
        if analysis is None:
            analysis = self.analyze_position(symbol)
        
        recommendations = []
        
        if analysis.state == WheelState.OWN_STOCK:
            # Look for covered calls above cost basis
            candidates = self.resolver.resolve_strikes(
                symbol=symbol,
                target_delta=self.target_delta,
                option_type='call',
                max_maturities=3,
                candidates_per_maturity=3,
                spot_price=analysis.current_price
            )
            
            # Filter for strikes above cost basis
            for expiry, options in candidates.items():
                for candidate in options['calls']:
                    if candidate.strike > analysis.cost_basis:
                        contracts = analysis.shares_owned // 100
                        if contracts > 0:
                            premium = (candidate.premium or 0) * contracts * 100
                            max_profit = (candidate.strike - analysis.cost_basis) * analysis.shares_owned + premium
                            
                            rec = TradeRecommendation(
                                symbol=symbol,
                                action='sell_call',
                                candidate=candidate,
                                quantity=contracts,
                                expected_premium=premium,
                                max_profit=max_profit,
                                max_loss=-analysis.stock_pnl,  # Worst case: stock drops
                                break_even=analysis.cost_basis - (candidate.premium or 0),
                                reasoning=f"Sell covered call above cost basis ({analysis.cost_basis:.2f})"
                            )
                            recommendations.append(rec)
        
        elif analysis.state == WheelState.SHORT_PUT:
            # Already short a put, waiting for potential assignment
            # Could recommend rolling or waiting
            pass
        
        elif analysis.state == WheelState.SHORT_CALL:
            # Already short a call, waiting for potential assignment
            # Could recommend rolling or waiting
            pass
        
        elif analysis.state == WheelState.NO_POSITION:
            # No position - recommend selling cash-secured puts
            candidates = self.resolver.resolve_strikes(
                symbol=symbol,
                target_delta=self.target_delta,
                option_type='put',
                max_maturities=3,
                candidates_per_maturity=3,
                spot_price=analysis.current_price
            )
            
            for expiry, options in candidates.items():
                for candidate in options['puts']:
                    contracts = 1  # Start with 1 contract
                    premium = (candidate.premium or 0) * contracts * 100
                    cash_required = candidate.strike * contracts * 100
                    
                    rec = TradeRecommendation(
                        symbol=symbol,
                        action='sell_put',
                        candidate=candidate,
                        quantity=contracts,
                        expected_premium=premium,
                        max_profit=premium,
                        max_loss=cash_required - premium,
                        break_even=candidate.strike - (candidate.premium or 0),
                        reasoning=f"Sell cash-secured put at strike {candidate.strike}"
                    )
                    recommendations.append(rec)
        
        # Sort by expected premium
        recommendations.sort(key=lambda r: r.expected_premium, reverse=True)
        return recommendations[:3]  # Top 3 recommendations
    
    def execute_trade(
        self,
        recommendation: TradeRecommendation,
        price_type: str = 'mid'
    ) -> Optional[str]:
        """Execute a trade recommendation."""
        candidate = recommendation.candidate
        
        # Determine price
        if price_type == 'bid':
            price = candidate.bid
        elif price_type == 'ask':
            price = candidate.ask
        else:
            price = candidate.mid_price
        
        # Determine action
        if recommendation.action == 'sell_call':
            action = 'SellToOpen'
        elif recommendation.action == 'sell_put':
            action = 'SellToOpen'
        else:
            raise ValueError(f"Unknown action: {recommendation.action}")
        
        try:
            order = self.client.place_option_order(
                option_symbol=candidate.symbol,
                quantity=recommendation.quantity,
                action=action,
                price=price
            )
            
            if order:
                logger.info(f"Order placed: {order.id} - {recommendation.action} {candidate.symbol}")
                return order.id
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            raise
        
        return None
    
    def get_wheel_status(self) -> Dict[str, Any]:
        """Get overall wheel strategy status across all positions."""
        stock_positions = self.client.get_stock_positions()
        option_positions = self.client.get_option_positions()
        
        symbols_with_positions = set()
        for p in stock_positions:
            symbols_with_positions.add(p['symbol'])
        for p in option_positions:
            # Extract underlying from option symbol
            # Simplified extraction
            symbol = p['symbol'].split()[0] if ' ' in p['symbol'] else p['symbol'][:4]
            symbols_with_positions.add(symbol)
        
        analyses = []
        for symbol in symbols_with_positions:
            try:
                analysis = self.analyze_position(symbol)
                analyses.append(analysis.to_dict())
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
        
        # Calculate portfolio metrics
        total_stock_pnl = sum(a['stock_pnl'] for a in analyses)
        total_option_pnl = sum(a['option_pnl'] for a in analyses)
        total_premium_collected = sum(
            a['option_premium'] for a in analyses if a['option_premium'] > 0
        )
        
        return {
            'positions': analyses,
            'summary': {
                'total_positions': len(analyses),
                'total_stock_pnl': round(total_stock_pnl, 2),
                'total_option_pnl': round(total_option_pnl, 2),
                'total_premium_collected': round(total_premium_collected, 2),
                'positions_by_state': self._count_by_state(analyses),
            }
        }
    
    def _count_by_state(self, analyses: List[Dict]) -> Dict[str, int]:
        """Count positions by wheel state."""
        counts = {}
        for a in analyses:
            state = a['state']
            counts[state] = counts.get(state, 0) + 1
        return counts
