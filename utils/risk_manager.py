"""
Risk Management Module for the Quant Options Trading System.

Based on the principles from the papers that built quant finance:
- Sharpe (1964): CAPM, systematic vs idiosyncratic risk
- Markowitz (1952): Portfolio diversification as the only free lunch
- Black-Scholes (1973): Risk-neutral pricing
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from api.tastytrade_client import TastyTradeClient
from config import Config

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics for a position or portfolio."""
    position_value: float
    delta_exposure: float
    gamma_exposure: float
    theta_exposure: float
    vega_exposure: float
    max_loss: float
    assignment_risk: float  # 0-1 probability
    concentration_pct: float  # % of portfolio
    margin_requirement: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'position_value': round(self.position_value, 2),
            'delta_exposure': round(self.delta_exposure, 4),
            'gamma_exposure': round(self.gamma_exposure, 4),
            'theta_exposure': round(self.theta_exposure, 2),
            'vega_exposure': round(self.vega_exposure, 2),
            'max_loss': round(self.max_loss, 2),
            'assignment_risk': round(self.assignment_risk, 2),
            'concentration_pct': round(self.concentration_pct, 4),
            'margin_requirement': round(self.margin_requirement, 2),
        }


class RiskManager:
    """
    Manages risk for the options trading system.
    
    Key principles:
    1. Position sizing: Max 20% per position (diversification)
    2. Delta management: Monitor directional exposure
    3. Assignment risk: Track probability of assignment
    4. Portfolio heat: Total capital at risk
    """
    
    def __init__(self, client: TastyTradeClient):
        """Initialize risk manager."""
        self.client = client
        self.max_position_pct = Config.MAX_POSITION_PCT  # 20%
        self.max_portfolio_delta = 2.0  # Max 200% net delta
        self.max_assignment_risk = 0.50  # Flag positions with >50% assignment risk
    
    def calculate_position_risk(
        self,
        symbol: str,
        shares: int = 0,
        option_contracts: int = 0,
        option_delta: float = 0,
        option_gamma: float = 0,
        option_theta: float = 0,
        option_vega: float = 0,
        option_strike: float = 0,
        current_price: float = 0,
    ) -> RiskMetrics:
        """Calculate risk metrics for a position."""
        
        # Get account balance for concentration calculation
        try:
            balance = self.client.get_account_balance()
            net_liquidating_value = balance.get('net_liquidating_value', 0)
        except:
            net_liquidating_value = 0
        
        # Stock position value and risk
        stock_value = shares * current_price
        stock_delta = shares  # 1 delta per share
        
        # Option position risk
        option_multiplier = 100
        option_value = option_contracts * option_multiplier * current_price
        option_delta_exposure = option_contracts * option_multiplier * option_delta
        
        # Greeks exposure (per contract)
        total_gamma = option_contracts * option_gamma * option_multiplier
        total_theta = option_contracts * option_theta * option_multiplier
        total_vega = option_contracts * option_vega * option_multiplier
        
        # Combined position
        total_delta = stock_delta + option_delta_exposure
        total_value = stock_value + option_value
        
        # Max loss calculation
        if option_contracts > 0 and option_strike > 0:
            if option_delta > 0:  # Short call
                max_loss_option = option_contracts * option_strike * option_multiplier
            else:  # Short put
                max_loss_option = option_contracts * option_strike * option_multiplier
        else:
            max_loss_option = 0
        
        max_loss = max_loss_option
        
        # Assignment risk (using delta as proxy)
        assignment_risk = abs(option_delta) if option_delta else 0
        
        # Concentration
        concentration = (total_value / net_liquidating_value) if net_liquidating_value > 0 else 0
        
        # Margin requirement (simplified)
        margin = option_contracts * option_strike * option_multiplier * 0.20  # 20% margin
        
        return RiskMetrics(
            position_value=total_value,
            delta_exposure=total_delta,
            gamma_exposure=total_gamma,
            theta_exposure=total_theta,
            vega_exposure=total_vega,
            max_loss=max_loss,
            assignment_risk=assignment_risk,
            concentration_pct=concentration,
            margin_requirement=margin
        )
    
    def check_position_limits(self, risk: RiskMetrics) -> List[str]:
        """Check if position exceeds risk limits."""
        warnings = []
        
        if risk.concentration_pct > self.max_position_pct:
            warnings.append(
                f"Concentration {risk.concentration_pct:.1%} exceeds limit of "
                f"{self.max_position_pct:.1%}"
            )
        
        if risk.assignment_risk > self.max_assignment_risk:
            warnings.append(
                f"High assignment risk: {risk.assignment_risk:.1%}"
            )
        
        if abs(risk.delta_exposure) > 500:  # Large directional bet
            warnings.append(
                f"Large delta exposure: {risk.delta_exposure:.0f} shares equivalent"
            )
        
        return warnings
    
    def calculate_portfolio_risk(self) -> Dict:
        """Calculate aggregate portfolio risk metrics."""
        try:
            positions = self.client.get_portfolio_positions()
            balance = self.client.get_account_balance()
            
            total_value = balance.get('net_liquidating_value', 0)
            
            # Aggregate metrics
            total_delta = 0
            total_theta = 0
            total_vega = 0
            max_loss_scenario = 0
            
            for pos in positions:
                if pos['instrument_type'] == 'Equity':
                    total_delta += pos['quantity']
                elif pos['instrument_type'] == 'Equity Option':
                    # Estimate delta from position
                    option_delta = 0.30  # Conservative estimate
                    total_delta += pos['quantity'] * 100 * option_delta
                    
                    # Theta is income for sellers
                    total_theta += 50  # Rough estimate per contract
            
            # Portfolio concentration
            position_values = [abs(p.get('market_price', 0) * p['quantity']) for p in positions]
            if position_values and total_value > 0:
                max_concentration = max(position_values) / total_value
            else:
                max_concentration = 0
            
            return {
                'total_portfolio_value': round(total_value, 2),
                'net_delta_exposure': round(total_delta, 2),
                'daily_theta_income': round(total_theta, 2),
                'total_vega_exposure': round(total_vega, 2),
                'max_concentration': round(max_concentration, 4),
                'diversification_score': round(1 - max_concentration, 4),
                'cash_percentage': round(
                    balance.get('cash_available', 0) / total_value * 100, 2
                ) if total_value > 0 else 0,
                'margin_utilization': round(
                    balance.get('maintenance_requirement', 0) / total_value * 100, 2
                ) if total_value > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk: {e}")
            return {}
    
    def recommend_position_size(
        self,
        symbol: str,
        strategy: str = 'conservative'
    ) -> int:
        """Recommend number of contracts based on risk parameters."""
        try:
            balance = self.client.get_account_balance()
            buying_power = balance.get('buying_power', 0)
            net_value = balance.get('net_liquidating_value', 0)
            
            # Get current quote
            quote = self.client.get_stock_quote(symbol)
            price = quote.get('last_price', 0) or quote.get('spot_price', 0)
            
            if price == 0:
                return 0
            
            # Base position sizing on strategy
            if strategy == 'conservative':
                max_position_value = net_value * 0.10  # 10% max
            elif strategy == 'moderate':
                max_position_value = net_value * 0.15  # 15% max
            else:  # aggressive
                max_position_value = net_value * 0.20  # 20% max
            
            # For cash-secured puts, cash required = strike * 100 per contract
            # Assume selling ATM or slightly OTM
            assumed_strike = price
            cash_per_contract = assumed_strike * 100
            
            max_contracts_by_value = int(max_position_value / cash_per_contract)
            max_contracts_by_cash = int(buying_power / cash_per_contract)
            
            # Take the minimum
            recommended = min(max_contracts_by_value, max_contracts_by_cash, 5)
            
            return max(0, recommended)
            
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 0
    
    def calculate_correlation_matrix(
        self,
        symbols: List[str],
        lookback_days: int = 30
    ) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix for portfolio symbols."""
        # This would require historical price data
        # Simplified version returns identity matrix
        matrix = {}
        for s1 in symbols:
            matrix[s1] = {}
            for s2 in symbols:
                matrix[s1][s2] = 1.0 if s1 == s2 else 0.0  # Placeholder
        
        return matrix
    
    def generate_risk_report(self) -> Dict:
        """Generate comprehensive risk report."""
        portfolio_risk = self.calculate_portfolio_risk()
        
        # Get open orders for pending risk
        try:
            open_orders = self.client.get_open_orders()
            pending_exposure = len(open_orders) * 100  # Rough estimate
        except:
            pending_exposure = 0
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_risk': portfolio_risk,
            'pending_order_exposure': pending_exposure,
            'risk_limits': {
                'max_position_pct': self.max_position_pct,
                'max_portfolio_delta': self.max_portfolio_delta,
                'max_assignment_risk': self.max_assignment_risk,
            },
            'risk_flags': self._check_risk_flags(portfolio_risk),
            'recommendations': self._generate_risk_recommendations(portfolio_risk)
        }
        
        return report
    
    def _check_risk_flags(self, portfolio_risk: Dict) -> List[str]:
        """Check for risk flags in portfolio."""
        flags = []
        
        if portfolio_risk.get('max_concentration', 0) > 0.25:
            flags.append("HIGH_CONCENTRATION")
        
        if abs(portfolio_risk.get('net_delta_exposure', 0)) > 1000:
            flags.append("LARGE_DIRECTIONAL_EXPOSURE")
        
        if portfolio_risk.get('cash_percentage', 100) < 5:
            flags.append("LOW_CASH_RESERVE")
        
        if portfolio_risk.get('margin_utilization', 0) > 50:
            flags.append("HIGH_MARGIN_USAGE")
        
        return flags
    
    def _generate_risk_recommendations(self, portfolio_risk: Dict) -> List[str]:
        """Generate risk-based recommendations."""
        recs = []
        
        if portfolio_risk.get('max_concentration', 0) > 0.20:
            recs.append("Consider reducing largest position to improve diversification")
        
        if portfolio_risk.get('diversification_score', 1) < 0.5:
            recs.append("Portfolio is concentrated - add more uncorrelated positions")
        
        if portfolio_risk.get('cash_percentage', 0) < 10:
            recs.append("Low cash reserve - reduce new position sizing")
        
        if not recs:
            recs.append("Risk metrics within acceptable limits")
        
        return recs
