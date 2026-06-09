"""
Strike Resolver - Finds optimal option strikes based on delta thresholds.
Based on the Quant Guild methodology for delta-based option selection.
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from scipy.stats import norm

from api.tastytrade_client import TastyTradeClient
from config import TradingConfig, Config

logger = logging.getLogger(__name__)


@dataclass
class OptionCandidate:
    """Represents an option candidate with its properties."""
    symbol: str
    underlying: str
    strike: float
    expiration: datetime
    option_type: str  # 'C' or 'P'
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_vol: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: int = 0
    open_interest: int = 0
    
    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last
    
    @property
    def premium(self) -> Optional[float]:
        """Get premium (use bid for conservative estimate)."""
        return self.bid if self.bid is not None else self.mid_price
    
    def distance_to_delta(self, target_delta: float) -> float:
        """Calculate distance to target delta."""
        if self.delta is None:
            return float('inf')
        
        # Adjust for puts (convert to absolute for comparison)
        if self.option_type == 'P':
            delta = abs(self.delta)
        else:
            delta = abs(self.delta)
            
        return abs(delta - target_delta)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'underlying': self.underlying,
            'strike': self.strike,
            'expiration': self.expiration.isoformat() if self.expiration else None,
            'option_type': 'Call' if self.option_type == 'C' else 'Put',
            'delta': round(self.delta, 4) if self.delta else None,
            'gamma': round(self.gamma, 4) if self.gamma else None,
            'theta': round(self.theta, 4) if self.theta else None,
            'vega': round(self.vega, 4) if self.vega else None,
            'implied_vol': round(self.implied_vol, 4) if self.implied_vol else None,
            'bid': self.bid,
            'ask': self.ask,
            'mid': self.mid_price,
            'last': self.last,
            'volume': self.volume,
            'open_interest': self.open_interest,
            'premium': self.premium,
        }


class StrikeResolver:
    """Resolves optimal option strikes based on delta and volume criteria."""
    
    def __init__(self, client: TastyTradeClient):
        """Initialize with TastyTrade client."""
        self.client = client
        self._chain_cache: Dict[str, Dict[datetime, List]] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def _get_cache_key(self, symbol: str) -> str:
        """Generate cache key for symbol."""
        return symbol.upper()
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid."""
        key = self._get_cache_key(symbol)
        if key not in self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp[key] < self._cache_ttl
    
    def _get_cached_chain(self, symbol: str) -> Optional[Dict[datetime, List]]:
        """Get cached option chain if valid."""
        if self._is_cache_valid(symbol):
            return self._chain_cache.get(self._get_cache_key(symbol))
        return None
    
    def _cache_chain(self, symbol: str, chain: Dict[datetime, List]):
        """Cache option chain."""
        key = self._get_cache_key(symbol)
        self._chain_cache[key] = chain
        self._cache_timestamp[key] = datetime.now()
    
    def _calculate_black_scholes_delta(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float,
        option_type: str
    ) -> float:
        """Calculate delta using Black-Scholes."""
        if time_to_expiry <= 0 or volatility <= 0:
            return 0.0
            
        d1 = (np.log(spot / strike) + 
              (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / \
             (volatility * np.sqrt(time_to_expiry))
        
        if option_type == 'C':
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
    
    def _filter_strikes_by_moneyness(
        self,
        strikes: List[float],
        spot: float,
        option_type: str,
        range_pct: float = 0.15
    ) -> List[float]:
        """Filter strikes by moneyness (OTM options only)."""
        if option_type == 'C':  # Calls - OTM is above spot
            return [s for s in strikes if s >= spot and s <= spot * (1 + range_pct)]
        else:  # Puts - OTM is below spot
            return [s for s in strikes if s <= spot and s >= spot * (1 - range_pct)]
    
    def _rank_by_volume_and_delta(
        self,
        candidates: List[OptionCandidate],
        target_delta: float,
        top_n: int = 3
    ) -> List[OptionCandidate]:
        """Rank candidates by volume and delta proximity."""
        if not candidates:
            return []
        
        # Calculate scores
        scored = []
        for c in candidates:
            delta_distance = c.distance_to_delta(target_delta)
            volume_score = min(c.volume / 1000, 1.0)  # Normalize volume, cap at 1
            
            # Combined score: prefer lower delta distance but weight by volume
            # Lower score is better
            score = delta_distance * (1.1 - volume_score * 0.1)
            scored.append((score, c))
        
        # Sort by score and return top N
        scored.sort(key=lambda x: x[0])
        return [c for _, c in scored[:top_n]]
    
    def resolve_strikes(
        self,
        symbol: str,
        target_delta: float = 0.30,
        option_type: str = 'both',  # 'call', 'put', or 'both'
        max_maturities: int = 3,
        candidates_per_maturity: int = 3,
        min_dte: int = 0,
        max_dte: int = 45,
        spot_price: Optional[float] = None
    ) -> Dict[datetime, Dict[str, List[OptionCandidate]]]:
        """
        Resolve optimal option strikes for given parameters.
        
        Returns a dictionary mapping expiration dates to call/put candidates.
        """
        logger.info(f"Resolving strikes for {symbol} with target delta {target_delta}")
        
        # Get option chain
        chain = self._get_cached_chain(symbol)
        if chain is None:
            chain = self.client.get_option_chain(symbol)
            self._cache_chain(symbol, chain)
        
        # Get spot price if not provided
        if spot_price is None:
            quote = self.client.get_stock_quote(symbol)
            spot_price = quote.get('last_price') or quote.get('spot_price')
        
        if not spot_price:
            raise ValueError(f"Could not determine spot price for {symbol}")
        
        # Filter maturities
        now = datetime.now()
        valid_maturities = []
        for exp in chain.keys():
            dte = (exp - now).days
            if min_dte <= dte <= max_dte:
                valid_maturities.append(exp)
        
        valid_maturities.sort()
        selected_maturities = valid_maturities[:max_maturities]
        
        logger.info(f"Found {len(selected_maturities)} valid maturities")
        
        results = {}
        
        for maturity in selected_maturities:
            results[maturity] = {'calls': [], 'puts': []}
            
            options = chain[maturity]
            dte = (maturity - now).days
            time_to_expiry = dte / 365.0
            
            # Get all strikes
            all_strikes = sorted(set([opt.strike for opt in options]))
            
            # Filter OTM strikes
            call_strikes = self._filter_strikes_by_moneyness(
                all_strikes, spot_price, 'C', Config.STRIKE_RANGE_PCT
            )
            put_strikes = self._filter_strikes_by_moneyness(
                all_strikes, spot_price, 'P', Config.STRIKE_RANGE_PCT
            )
            
            # Create strike to option mapping
            strike_to_option = {opt.strike: opt for opt in options}
            
            # Process calls
            if option_type in ['call', 'both', 'C']:
                call_candidates = []
                for strike in call_strikes:
                    opt = strike_to_option.get(strike)
                    if opt:
                        # Try to get Greeks from option data, otherwise estimate
                        delta = getattr(opt, 'delta', None)
                        
                        candidate = OptionCandidate(
                            symbol=opt.symbol,
                            underlying=symbol,
                            strike=strike,
                            expiration=maturity,
                            option_type='C',
                            delta=delta,
                            bid=getattr(opt, 'bid_price', None),
                            ask=getattr(opt, 'ask_price', None),
                            last=getattr(opt, 'last_price', None),
                            volume=getattr(opt, 'volume', 0) or 0,
                            open_interest=getattr(opt, 'open_interest', 0) or 0,
                        )
                        call_candidates.append(candidate)
                
                # Rank and select top candidates
                results[maturity]['calls'] = self._rank_by_volume_and_delta(
                    call_candidates, target_delta, candidates_per_maturity
                )
            
            # Process puts
            if option_type in ['put', 'both', 'P']:
                put_candidates = []
                for strike in put_strikes:
                    opt = strike_to_option.get(strike)
                    if opt:
                        delta = getattr(opt, 'delta', None)
                        
                        candidate = OptionCandidate(
                            symbol=opt.symbol,
                            underlying=symbol,
                            strike=strike,
                            expiration=maturity,
                            option_type='P',
                            delta=delta,
                            bid=getattr(opt, 'bid_price', None),
                            ask=getattr(opt, 'ask_price', None),
                            last=getattr(opt, 'last_price', None),
                            volume=getattr(opt, 'volume', 0) or 0,
                            open_interest=getattr(opt, 'open_interest', 0) or 0,
                        )
                        put_candidates.append(candidate)
                
                results[maturity]['puts'] = self._rank_by_volume_and_delta(
                    put_candidates, target_delta, candidates_per_maturity
                )
        
        return results
    
    def find_strike_by_delta(
        self,
        symbol: str,
        target_delta: float,
        expiration: datetime,
        option_type: str,
        tolerance: float = 0.05,
        spot_price: Optional[float] = None
    ) -> Optional[OptionCandidate]:
        """Find a specific strike closest to target delta for given expiration."""
        results = self.resolve_strikes(
            symbol=symbol,
            target_delta=target_delta,
            option_type=option_type,
            max_maturities=1,
            candidates_per_maturity=1,
            spot_price=spot_price
        )
        
        if expiration in results:
            key = 'calls' if option_type == 'C' else 'puts'
            candidates = results[expiration].get(key, [])
            if candidates:
                return candidates[0]
        
        return None
    
    def clear_cache(self):
        """Clear option chain cache."""
        self._chain_cache.clear()
        self._cache_timestamp.clear()
        logger.info("Strike resolver cache cleared")
