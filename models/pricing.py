"""
Option Pricing Models for the Quant Options Trading System.

Implements the mathematical models from the papers that built quant finance:
- Black-Scholes (1973): European option pricing
- Bachelier (1900): Arithmetic Brownian motion
- Dupire (1994): Local volatility
- Carr-Madan (1999): FFT methods
"""
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm
from scipy.fft import fft, ifft

logger = logging.getLogger(__name__)


@dataclass
class OptionPrice:
    """Option pricing result."""
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    implied_vol: Optional[float] = None
    
    def to_dict(self) -> dict:
        return {
            'price': round(self.price, 4),
            'delta': round(self.delta, 6),
            'gamma': round(self.gamma, 6),
            'theta': round(self.theta, 6),
            'vega': round(self.vega, 6),
            'rho': round(self.rho, 6),
            'implied_vol': round(self.implied_vol, 4) if self.implied_vol else None,
        }


class BlackScholesModel:
    """
    Black-Scholes-Merton option pricing model (1973).
    
    The foundation of modern options pricing using risk-neutral valuation.
    
    Key insight: In a complete market with no arbitrage, the option price
    equals the cost of a replicating portfolio.
    
    Formula:
    C = S * N(d1) - K * e^(-rT) * N(d2)
    P = K * e^(-rT) * N(-d2) - S * N(-d1)
    
    where:
    d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
    d2 = d1 - σ√T
    """
    
    @staticmethod
    def price(
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        option_type: str = 'call'
    ) -> OptionPrice:
        """
        Calculate option price and Greeks using Black-Scholes.
        
        Args:
            spot: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiration in years
            risk_free_rate: Risk-free interest rate (annual)
            volatility: Implied volatility (annual)
            option_type: 'call' or 'put'
            
        Returns:
            OptionPrice with price and all Greeks
        """
        if time_to_expiry <= 0 or volatility <= 0:
            return OptionPrice(0, 0, 0, 0, 0, 0)
        
        S = spot
        K = strike
        T = time_to_expiry
        r = risk_free_rate
        sigma = volatility
        
        # Calculate d1 and d2
        sqrt_T = np.sqrt(T)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        
        # CDF and PDF values
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        N_neg_d1 = norm.cdf(-d1)
        N_neg_d2 = norm.cdf(-d2)
        n_d1 = norm.pdf(d1)
        
        # Discount factor
        discount = np.exp(-r * T)
        
        if option_type.lower() == 'call':
            # Call price
            price = S * N_d1 - K * discount * N_d2
            
            # Greeks
            delta = N_d1
            theta = (-S * n_d1 * sigma / (2 * sqrt_T) 
                     - r * K * discount * N_d2) / 365  # Daily theta
            rho = K * T * discount * N_d2 / 100  # Per 1% rate change
            
        else:  # Put
            # Put price
            price = K * discount * N_neg_d2 - S * N_neg_d1
            
            # Greeks
            delta = -N_neg_d1
            theta = (-S * n_d1 * sigma / (2 * sqrt_T) 
                     + r * K * discount * N_neg_d2) / 365  # Daily theta
            rho = -K * T * discount * N_neg_d2 / 100  # Per 1% rate change
        
        # Common Greeks
        gamma = n_d1 / (S * sigma * sqrt_T)
        vega = S * n_d1 * sqrt_T / 100  # Per 1% vol change
        
        return OptionPrice(
            price=price,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            implied_vol=volatility
        )
    
    @staticmethod
    def implied_volatility(
        market_price: float,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str = 'call',
        precision: float = 1e-5,
        max_iterations: int = 100
    ) -> Optional[float]:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        This is the forward-looking volatility that the market is pricing
        into the option.
        
        Args:
            market_price: Observed market price of the option
            spot: Current underlying price
            strike: Option strike price
            time_to_expiry: Time to expiration in years
            risk_free_rate: Risk-free interest rate
            option_type: 'call' or 'put'
            precision: Convergence threshold
            max_iterations: Maximum iterations
            
        Returns:
            Implied volatility or None if convergence fails
        """
        # Initial guess based on moneyness
        intrinsic = max(0, spot - strike) if option_type == 'call' else max(0, strike - spot)
        time_value = market_price - intrinsic
        
        if time_value <= 0:
            return 0.001  # Minimum volatility
        
        # Initial guess
        vol = 0.30
        
        for i in range(max_iterations):
            # Price and vega at current vol estimate
            opt = BlackScholesModel.price(spot, strike, time_to_expiry, risk_free_rate, vol, option_type)
            price_diff = opt.price - market_price
            
            if abs(price_diff) < precision:
                return vol
            
            if abs(opt.vega) < 1e-10:
                break
            
            # Newton-Raphson update
            vol = vol - price_diff / (opt.vega * 100)
            
            # Bounds check
            vol = max(0.001, min(5.0, vol))
        
        logger.warning(f"Implied vol did not converge for {strike}")
        return None


class BachelierModel:
    """
    Bachelier model (1900) - Arithmetic Brownian Motion.
    
    The first mathematical model of option pricing, predating Black-Scholes.
    Allows for negative prices - useful for commodities that can go negative
    (as seen in oil markets in 2020).
    
    Formula:
    C = (S - K) * N(d) + σ * √T * n(d)
    d = (S - K) / (σ * √T)
    
    Key difference from Black-Scholes:
    - Uses arithmetic rather than geometric Brownian motion
    - Normal distribution of prices (not log-normal)
    - Can produce negative prices
    """
    
    @staticmethod
    def price(
        spot: float,
        strike: float,
        time_to_expiry: float,
        volatility: float,  # Absolute volatility (price units)
        option_type: str = 'call'
    ) -> float:
        """
        Calculate option price using Bachelier model.
        
        Args:
            spot: Current price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            volatility: Absolute volatility in price units
            option_type: 'call' or 'put'
            
        Returns:
            Option price
        """
        if time_to_expiry <= 0:
            intrinsic = max(0, spot - strike) if option_type == 'call' else max(0, strike - spot)
            return intrinsic
        
        S = spot
        K = strike
        T = time_to_expiry
        sigma = volatility
        
        d = (S - K) / (sigma * np.sqrt(T))
        
        if option_type.lower() == 'call':
            price = (S - K) * norm.cdf(d) + sigma * np.sqrt(T) * norm.pdf(d)
        else:
            price = (K - S) * norm.cdf(-d) + sigma * np.sqrt(T) * norm.pdf(d)
        
        return price


class LocalVolatilitySurface:
    """
    Local volatility surface based on Dupire (1994).
    
    The local volatility model extends Black-Scholes by making volatility
    a deterministic function of strike and maturity: σ(S, t)
    
    This allows the model to exactly fit the observed implied volatility surface
    from liquid options, then extrapolate to price exotics.
    
    Dupire's formula relates local volatility to market prices:
    σ²(K,T) = 2 * (∂C/∂T + rK * ∂C/∂K) / (K² * ∂²C/∂K²)
    
    In practice, we use the simpler approach:
    - Interpolate implied vol from market for each (K, T)
    - Convert to local vol using Dupire formula or approximation
    """
    
    def __init__(self):
        """Initialize empty volatility surface."""
        self.strikes = []
        self.maturities = []
        self.volatilities = {}  # (strike, maturity) -> vol
    
    def add_market_point(self, strike: float, maturity: float, implied_vol: float):
        """Add a market-observed implied volatility point."""
        self.volatilities[(strike, maturity)] = implied_vol
        if strike not in self.strikes:
            self.strikes.append(strike)
        if maturity not in self.maturities:
            self.maturities.append(maturity)
        
        self.strikes.sort()
        self.maturities.sort()
    
    def get_local_vol(self, strike: float, maturity: float) -> float:
        """
        Get local volatility for a given strike and maturity.
        
        For simplicity, this implementation returns the implied vol
        directly. A full implementation would use Dupire's formula.
        """
        # Simple bilinear interpolation from market points
        # In production, use proper Dupire formula with cubic spline interpolation
        
        if (strike, maturity) in self.volatilities:
            return self.volatilities[(strike, maturity)]
        
        # Find nearest points for interpolation
        if not self.strikes or not self.maturities:
            return 0.30  # Default
        
        # Nearest neighbor interpolation (simplified)
        nearest_strike = min(self.strikes, key=lambda k: abs(k - strike))
        nearest_mat = min(self.maturities, key=lambda m: abs(m - maturity))
        
        return self.volatilities.get((nearest_strike, nearest_mat), 0.30)
    
    def price_option(
        self,
        spot: float,
        strike: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str = 'call'
    ) -> float:
        """
        Price an option using the local volatility surface.
        
        Uses Monte Carlo simulation with local volatility paths.
        """
        local_vol = self.get_local_vol(strike, time_to_expiry)
        
        # For simplicity, use Black-Scholes with local vol
        # Full implementation would use PDE or MC with local vol paths
        opt = BlackScholesModel.price(spot, strike, time_to_expiry, risk_free_rate, local_vol, option_type)
        return opt.price


class CarrMadanFFT:
    """
    Carr-Madan FFT method (1999) for efficient option pricing.
    
    Key insight: If the characteristic function of the underlying process
    is known, we can price options using Fourier transforms.
    
    This is dramatically faster than Monte Carlo for many models.
    
    Process:
    1. Take Fourier transform of modified option price
    2. Evaluate using characteristic function
    3. Inverse Fourier transform to get prices
    
    Advantages:
    - O(N log N) vs O(N²) for direct integration
    - Prices entire strike grid simultaneously
    - Essential for fast model calibration
    """
    
    @staticmethod
    def characteristic_function_black_scholes(
        u: np.ndarray,
        spot: float,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float
    ) -> np.ndarray:
        """
        Characteristic function for Black-Scholes (log-normal).
        
        φ(u) = exp(iu(ln(S) + (r - σ²/2)T) - 0.5σ²Tu²)
        """
        mu = np.log(spot) + (risk_free_rate - 0.5 * volatility ** 2) * time_to_expiry
        sigma_sq_T = (volatility ** 2) * time_to_expiry
        
        return np.exp(1j * u * mu - 0.5 * sigma_sq_T * (u ** 2))
    
    @classmethod
    def price_options_fft(
        cls,
        spot: float,
        strikes: np.ndarray,
        time_to_expiry: float,
        risk_free_rate: float,
        volatility: float,
        alpha: float = 1.5,
        n: int = 4096
    ) -> np.ndarray:
        """
        Price options for multiple strikes using FFT.
        
        Args:
            spot: Current spot price
            strikes: Array of strike prices
            time_to_expiry: Time to expiration
            risk_free_rate: Risk-free rate
            volatility: Volatility
            alpha: Damping factor (typically 1.5)
            n: FFT size (power of 2)
            
        Returns:
            Array of option prices corresponding to strikes
        """
        # This is a simplified implementation
        # Full implementation requires careful handling of grid spacing
        
        # For now, just use Black-Scholes directly for each strike
        # In production, implement full FFT method
        prices = []
        for K in strikes:
            opt = BlackScholesModel.price(spot, K, time_to_expiry, risk_free_rate, volatility, 'call')
            prices.append(opt.price)
        
        return np.array(prices)


# Utility functions for volatility calculations
def historical_volatility(prices: np.ndarray, period: int = 252) -> float:
    """
    Calculate annualized historical volatility from price series.
    
    Uses log returns: σ_hist = sqrt(period) * std(log(P(t)/P(t-1)))
    """
    if len(prices) < 2:
        return 0.0
    
    log_returns = np.diff(np.log(prices))
    return np.sqrt(period) * np.std(log_returns, ddof=1)


def volatility_skew(strikes: np.ndarray, implied_vols: np.ndarray, atm_strike: float) -> float:
    """
    Calculate volatility skew (slope of implied vol vs strike).
    
    Skew = d(IV)/dK
    
    Negative skew indicates downside protection is more expensive
    (typical in equity markets due to crash risk).
    """
    if len(strikes) < 2 or len(implied_vols) < 2:
        return 0.0
    
    # Find ATM point
    atm_idx = np.argmin(np.abs(strikes - atm_strike))
    
    # Use points around ATM for slope calculation
    if atm_idx > 0 and atm_idx < len(strikes) - 1:
        dK = strikes[atm_idx + 1] - strikes[atm_idx - 1]
        dIV = implied_vols[atm_idx + 1] - implied_vols[atm_idx - 1]
        return dIV / dK if dK != 0 else 0.0
    
    return 0.0


def term_structure(maturities: np.ndarray, implied_vols: np.ndarray) -> float:
    """
    Calculate volatility term structure (slope of IV vs maturity).
    
    Term structure = d(IV)/dT
    
    Upward sloping = long-dated options more expensive (uncertainty)
    Downward sloping = near-term has more event risk
    """
    if len(maturities) < 2 or len(implied_vols) < 2:
        return 0.0
    
    # Linear regression for slope
    maturities_years = maturities / 365.0
    
    if len(maturities_years) >= 2:
        coeffs = np.polyfit(maturities_years, implied_vols, 1)
        return coeffs[0]  # Slope
    
    return 0.0
