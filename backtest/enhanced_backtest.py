"""
Enhanced Backtesting Engine with Professional Backtesting Standards.

Based on Backtest Wizard Flagship Course insights:
1. Market Type Filtering (Regime Detection)
2. Portfolio-Level Backtesting
3. Proper Position Sizing
4. Equity Curve Analysis
5. Monte Carlo Simulation
6. Walk-Forward Analysis
7. Statistical Significance Testing
"""
import logging
import random
from typing import List, Dict, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats

from backtest.paper_trading import PaperTradingEnvironment, PaperTrade, TradeAction, TradeType
from config import Config

logger = logging.getLogger(__name__)


class MarketType(Enum):
    """Market regime classification."""
    BULL_STRONG = "bull_strong"      # Strong uptrend
    BULL_WEAK = "bull_weak"          # Weak uptrend
    BEAR_STRONG = "bear_strong"      # Strong downtrend
    BEAR_WEAK = "bear_weak"          # Weak downtrend
    SIDEWAY_VOLATILE = "sideway_volatile"  # Sideways with volatility
    SIDEWAY_QUIET = "sideway_quiet"  # Sideways quiet


@dataclass
class MarketRegime:
    """Market regime detection for filtering trades."""
    date: datetime
    market_type: MarketType
    roc_20: float  # 20-day rate of change
    atr_14: float  # 14-day ATR
    atr_percent: float  # ATR as % of price
    bb_width: float  # Bollinger Band width
    trend_strength: float  # ADX or similar
    
    def is_bullish(self) -> bool:
        return self.market_type in [MarketType.BULL_STRONG, MarketType.BULL_WEAK]
    
    def is_bearish(self) -> bool:
        return self.market_type in [MarketType.BEAR_STRONG, MarketType.BEAR_WEAK]
    
    def is_trending(self) -> bool:
        return self.market_type in [MarketType.BULL_STRONG, MarketType.BEAR_STRONG]


@dataclass
class EnhancedBacktestResult:
    """Comprehensive backtest results with professional metrics."""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    
    # Capital & Returns
    initial_capital: float
    final_capital: float
    total_return_pct: float
    annualized_return_pct: float
    
    # Trade Statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_trade_return: float
    avg_winner: float
    avg_loser: float
    profit_factor: float
    payoff_ratio: float
    
    # Risk Metrics
    max_drawdown_pct: float
    max_drawdown_duration: int  # days
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    volatility_annual: float
    var_95: float  # Value at Risk
    
    # Equity Curve Analysis
    equity_curve: List[Dict[str, Any]]
    underwater_curve: List[float]  # Drawdown over time
    monthly_returns: List[float]
    
    # Market Regime Performance
    regime_performance: Dict[MarketType, Dict[str, float]]
    
    # Monte Carlo Results
    mc_median_return: float
    mc_worst_case: float
    mc_best_case: float
    mc_probability_of_profit: float
    
    # Walk-Forward Analysis
    wf_is_consistent: bool
    wf_in_sample_return: float
    wf_out_of_sample_return: float
    
    # Statistical Significance
    p_value: float
    is_statistically_significant: bool
    confidence_interval: Tuple[float, float]
    
    trades: List[PaperTrade]


class MarketRegimeDetector:
    """
    Detects market regimes using ROC (Rate of Change) and ATR (Average True Range).
    
    Based on Backtest Wizard Lesson 10: Quantify Market Type using ROC & ATR
    """
    
    def __init__(
        self,
        roc_lookback: int = 20,
        atr_lookback: int = 14,
        bb_lookback: int = 20
    ):
        self.roc_lookback = roc_lookback
        self.atr_lookback = atr_lookback
        self.bb_lookback = bb_lookback
    
    def calculate_roc(self, prices: pd.Series) -> pd.Series:
        """Calculate Rate of Change."""
        return prices.pct_change(self.roc_lookback) * 100
    
    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_lookback).mean()
        
        return atr
    
    def calculate_bb_width(self, prices: pd.Series) -> pd.Series:
        """Calculate Bollinger Band width."""
        sma = prices.rolling(window=self.bb_lookback).mean()
        std = prices.rolling(window=self.bb_lookback).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        bb_width = (upper - lower) / sma * 100
        return bb_width
    
    def classify_market(
        self,
        roc: float,
        atr_percent: float,
        bb_width: float
    ) -> MarketType:
        """
        Classify market type based on ROC and ATR%.
        
        Rules from Backtest Wizard methodology:
        - ROC > 5%: Bullish
        - ROC < -5%: Bearish
        - ATR% > 3%: Volatile
        - ATR% < 1.5%: Quiet
        """
        is_volatile = atr_percent > 3.0
        is_quiet = atr_percent < 1.5
        
        if roc > 5:
            return MarketType.BULL_STRONG if not is_volatile else MarketType.BULL_WEAK
        elif roc < -5:
            return MarketType.BEAR_STRONG if not is_volatile else MarketType.BEAR_WEAK
        else:
            # Sideways market
            if is_volatile:
                return MarketType.SIDEWAY_VOLATILE
            else:
                return MarketType.SIDEWAY_QUIET
    
    def detect_regimes(self, df: pd.DataFrame) -> List[MarketRegime]:
        """Detect market regimes for all dates in dataframe."""
        regimes = []
        
        prices = df['close']
        roc = self.calculate_roc(prices)
        atr = self.calculate_atr(df)
        bb_width = self.calculate_bb_width(prices)
        
        for idx, row in df.iterrows():
            if pd.isna(roc.loc[idx]) or pd.isna(atr.loc[idx]):
                continue
            
            price = row['close']
            atr_percent = (atr.loc[idx] / price) * 100 if price > 0 else 0
            
            regime = MarketRegime(
                date=idx if isinstance(idx, datetime) else datetime.now(),
                market_type=self.classify_market(
                    roc.loc[idx],
                    atr_percent,
                    bb_width.loc[idx] if not pd.isna(bb_width.loc[idx]) else 0
                ),
                roc_20=roc.loc[idx],
                atr_14=atr.loc[idx],
                atr_percent=atr_percent,
                bb_width=bb_width.loc[idx] if not pd.isna(bb_width.loc[idx]) else 0,
                trend_strength=abs(roc.loc[idx])  # Simplified
            )
            regimes.append(regime)
        
        return regimes


class PositionSizer:
    """
    Professional position sizing methods.
    
    Based on Backtest Wizard Lesson 06: Useful SetOptions
    """
    
    @staticmethod
    def fixed_fractional(
        capital: float,
        risk_per_trade: float = 0.02,
        stop_loss_pct: float = 0.05
    ) -> int:
        """
        Fixed fractional position sizing.
        Risk 2% of capital per trade with 5% stop loss.
        """
        risk_amount = capital * risk_per_trade
        position_size = risk_amount / stop_loss_pct
        return int(position_size)
    
    @staticmethod
    def fixed_ratio(
        capital: float,
        delta: float = 10000,  # Profit required to increase size
        initial_units: int = 1
    ) -> int:
        """
        Fixed ratio position sizing (Ryan Jones method).
        Increase size after accumulating delta profits.
        """
        profit = capital - 100000  # Assuming $100k starting
        if profit < 0:
            return initial_units
        
        additional_units = int(profit / delta)
        return initial_units + additional_units
    
    @staticmethod
    def kelly_criterion(
        win_rate: float,
        avg_winner: float,
        avg_loser: float
    ) -> float:
        """
        Kelly Criterion for optimal position size.
        f* = (p * b - q) / b
        where p = win rate, q = loss rate, b = win/loss ratio
        """
        if avg_loser == 0:
            return 0
        
        b = avg_winner / avg_loser  # Odds
        p = win_rate
        q = 1 - p
        
        kelly = (p * b - q) / b if b > 0 else 0
        
        # Use half-Kelly for safety
        return max(0, min(kelly * 0.5, 0.25))  # Cap at 25%
    
    @staticmethod
    def volatility_based(
        capital: float,
        atr: float,
        risk_per_trade: float = 0.01,
        atr_multiplier: float = 2.0
    ) -> int:
        """
        ATR-based position sizing.
        Position size = (Capital * Risk%) / (ATR * Multiplier)
        """
        risk_amount = capital * risk_per_trade
        stop_distance = atr * atr_multiplier
        
        if stop_distance <= 0:
            return 0
        
        position_size = risk_amount / stop_distance
        return int(position_size)


class MonteCarloSimulator:
    """
    Monte Carlo simulation for backtest robustness testing.
    
    Based on professional backtesting standards.
    """
    
    def __init__(self, num_simulations: int = 1000):
        self.num_simulations = num_simulations
    
    def simulate(
        self,
        trades: List[PaperTrade],
        initial_capital: float
    ) -> Dict[str, float]:
        """
        Run Monte Carlo simulations using bootstrapping with replacement.
        
        Samples trades with replacement to create different trade sequences,
        then applies compounding with fixed fractional position sizing.
        """
        results = []
        
        # Extract percentage returns
        trade_returns_pct = []
        for trade in trades:
            if trade.realized_pnl != 0 and trade.entry_price > 0 and trade.quantity > 0:
                capital_at_risk = trade.entry_price * trade.quantity
                ret_pct = trade.realized_pnl / capital_at_risk
                trade_returns_pct.append(ret_pct)
        
        if not trade_returns_pct:
            return {
                'median_return': 0,
                'worst_case': 0,
                'best_case': 0,
                'probability_of_profit': 0
            }
        
        n_trades = len(trade_returns_pct)
        
        for _ in range(self.num_simulations):
            # Bootstrap: sample trades WITH replacement
            # This creates different win/loss ratios across simulations
            sampled = [random.choice(trade_returns_pct) for _ in range(n_trades)]
            
            # Calculate equity curve with compounding
            capital = initial_capital
            risk_fraction = 0.05  # 5% risk per trade for realistic compounding
            
            for ret_pct in sampled:
                position_size = capital * risk_fraction
                pnl = ret_pct * position_size
                capital += pnl
                
                if capital <= 0:
                    capital = 0
                    break
            
            final_return = ((capital - initial_capital) / initial_capital) * 100
            results.append(final_return)
        
        results.sort()
        
        return {
            'median_return': np.median(results),
            'worst_case': np.percentile(results, 5),
            'best_case': np.percentile(results, 95),
            'probability_of_profit': sum(1 for r in results if r > 0) / len(results)
        }


class WalkForwardAnalyzer:
    """
    Walk-forward analysis for strategy robustness.
    
    Splits data into in-sample (optimization) and out-of-sample (testing) periods.
    """
    
    def __init__(self, in_sample_pct: float = 0.7):
        self.in_sample_pct = in_sample_pct
    
    def analyze(
        self,
        equity_curve: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform walk-forward analysis."""
        if not equity_curve:
            return {
                'is_consistent': False,
                'in_sample_return': 0,
                'out_of_sample_return': 0
            }
        
        n = len(equity_curve)
        split_idx = int(n * self.in_sample_pct)
        
        in_sample = equity_curve[:split_idx]
        out_of_sample = equity_curve[split_idx:]
        
        if not in_sample or not out_of_sample:
            return {
                'is_consistent': False,
                'in_sample_return': 0,
                'out_of_sample_return': 0
            }
        
        # Calculate returns
        is_start = in_sample[0].get('total_value', 100000)
        is_end = in_sample[-1].get('total_value', 100000)
        is_return = ((is_end - is_start) / is_start) * 100 if is_start > 0 else 0
        
        oos_start = out_of_sample[0].get('total_value', 100000)
        oos_end = out_of_sample[-1].get('total_value', 100000)
        oos_return = ((oos_end - oos_start) / oos_start) * 100 if oos_start > 0 else 0
        
        # Check consistency (out-of-sample should be positive if in-sample was)
        is_consistent = (is_return > 0 and oos_return > 0) or \
                       (is_return < 0 and oos_return < 0) or \
                       abs(oos_return) > abs(is_return) * 0.5
        
        return {
            'is_consistent': is_consistent,
            'in_sample_return': is_return,
            'out_of_sample_return': oos_return
        }


class EnhancedBacktester:
    """
    Enhanced backtesting engine with professional features.
    
    Key improvements over basic backtester:
    1. Market regime filtering
    2. Proper position sizing
    3. Monte Carlo simulation
    4. Walk-forward analysis
    5. Statistical significance testing
    """
    
    def __init__(
        self,
        paper_env: PaperTradingEnvironment,
        use_regime_filter: bool = True,
        allowed_regimes: Optional[List[MarketType]] = None
    ):
        self.paper = paper_env
        self.use_regime_filter = use_regime_filter
        self.allowed_regimes = allowed_regimes or [
            MarketType.BULL_STRONG,
            MarketType.BULL_WEAK
        ]
        
        self.regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        self.mc_simulator = MonteCarloSimulator()
        self.wf_analyzer = WalkForwardAnalyzer()
    
    def calculate_advanced_metrics(
        self,
        equity_curve: List[Dict[str, Any]],
        trades: List[PaperTrade]
    ) -> Dict[str, float]:
        """Calculate professional backtest metrics."""
        
        # Extract daily returns
        daily_returns = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i-1].get('total_value', 100000)
            curr = equity_curve[i].get('total_value', 100000)
            if prev > 0:
                daily_returns.append((curr - prev) / prev)
        
        if not daily_returns:
            return {}
        
        # Sharpe Ratio (assuming 0% risk-free rate for simplicity)
        returns = np.array(daily_returns)
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        # Sortino Ratio (downside deviation only)
        downside_returns = returns[returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        sortino = np.mean(returns) / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Annualized volatility
        vol_annual = np.std(returns) * np.sqrt(252) * 100
        
        # VaR 95%
        var_95 = np.percentile(returns, 5) * 100
        
        return {
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'volatility_annual': vol_annual,
            'var_95': var_95
        }
    
    def calculate_regime_performance(
        self,
        trades: List[PaperTrade],
        regimes: List[MarketRegime]
    ) -> Dict[MarketType, Dict[str, float]]:
        """Calculate strategy performance by market regime."""
        
        # Create regime lookup
        regime_map = {r.date: r for r in regimes}
        
        # Group trades by regime
        regime_trades = {rt: [] for rt in MarketType}
        
        for trade in trades:
            # Find regime for trade date
            regime = regime_map.get(trade.timestamp.date() if hasattr(trade.timestamp, 'date') else trade.timestamp)
            if regime:
                regime_trades[regime.market_type].append(trade)
        
        # Calculate metrics per regime
        results = {}
        for regime_type, trades_list in regime_trades.items():
            if not trades_list:
                continue
            
            winners = sum(1 for t in trades_list if t.realized_pnl > 0)
            total_pnl = sum(t.realized_pnl for t in trades_list)
            
            results[regime_type] = {
                'trades': len(trades_list),
                'win_rate': winners / len(trades_list) if trades_list else 0,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / len(trades_list) if trades_list else 0
            }
        
        return results
    
    def statistical_test(
        self,
        trades: List[PaperTrade]
    ) -> Dict[str, Any]:
        """
        Perform statistical significance test on trade returns.
        
        Uses one-sample t-test against zero mean.
        """
        returns = [t.realized_pnl for t in trades if t.realized_pnl != 0]
        
        if len(returns) < 10:
            return {
                'p_value': 1.0,
                'is_significant': False,
                'confidence_interval': (0, 0)
            }
        
        # One-sample t-test
        t_stat, p_value = stats.ttest_1samp(returns, 0)
        
        # Confidence interval
        mean = np.mean(returns)
        std_err = stats.sem(returns)
        ci = stats.t.interval(0.95, len(returns)-1, loc=mean, scale=std_err)
        
        return {
            'p_value': p_value,
            'is_significant': p_value < 0.05,
            'confidence_interval': ci,
            't_statistic': t_stat
        }
    
    def calculate_drawdown_curve(
        self,
        equity_curve: List[Dict[str, Any]]
    ) -> Tuple[List[float], int, int]:
        """
        Calculate drawdown curve and max drawdown duration.
        
        Returns:
            (underwater_curve, max_dd_pct, max_dd_duration_days)
        """
        if not equity_curve:
            return [], 0, 0
        
        values = [p.get('total_value', 0) for p in equity_curve]
        
        peak = values[0]
        max_dd = 0
        dd_start = 0
        max_dd_duration = 0
        current_dd_start = 0
        
        underwater = []
        
        for i, value in enumerate(values):
            if value > peak:
                peak = value
                current_dd_start = i
            
            dd = (peak - value) / peak if peak > 0 else 0
            underwater.append(dd * 100)
            
            if dd > max_dd:
                max_dd = dd
                dd_start = current_dd_start
                max_dd_duration = i - current_dd_start
        
        return underwater, max_dd * 100, max_dd_duration


class EnhancedMomentumBacktester(EnhancedBacktester):
    """
    Enhanced backtester specifically for Compra a Seco (Momentum) strategy.
    
    Implements proper regime filtering - only trade in bullish regimes.
    """
    
    def run_backtest(
        self,
        symbol: str,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
        risk_per_trade: float = 0.02
    ) -> EnhancedBacktestResult:
        """
        Run enhanced backtest with regime filtering and proper position sizing.
        """
        logger.info(f"Running enhanced momentum backtest for {symbol}")
        
        # Detect market regimes
        regimes = self.regime_detector.detect_regimes(df)
        regime_map = {r.date: r for r in regimes}
        
        # Convert to candles for strategy
        from models.technical_analysis import TechnicalAnalyzer, Candle
        analyzer = TechnicalAnalyzer()
        
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
        
        # Find setups
        setups = analyzer.find_compra_a_seco_setups(symbol, candles)
        
        # Simulate trades with regime filtering
        trades = []
        equity_curve = []
        capital = initial_capital
        
        for setup in setups:
            # Check regime - only trade in allowed regimes
            regime = regime_map.get(setup.detected_at.date() if hasattr(setup.detected_at, 'date') else setup.detected_at)
            
            if self.use_regime_filter and regime:
                if regime.market_type not in self.allowed_regimes:
                    logger.debug(f"Skipping setup due to regime: {regime.market_type}")
                    continue
            
            # Calculate position size using ATR-based sizing
            atr = regime.atr_14 if regime else setup.propulsion_candle.close * 0.02
            position_size = self.position_sizer.volatility_based(
                capital, atr, risk_per_trade
            )
            
            # Simulate entry
            entry_price = setup.entry_price
            entry_value = position_size * entry_price
            
            if entry_value > capital * 0.20:  # Max 20% allocation
                position_size = int(capital * 0.20 / entry_price)
            
            if position_size == 0:
                continue
            
            # Simulate exit (target or time stop)
            stop_loss = entry_price - (atr * 2)
            
            # Find exit in historical data
            exit_price = None
            exit_reason = None
            
            # Look for target hit or time stop in subsequent candles
            entry_idx = None
            for i, candle in enumerate(candles):
                if candle.timestamp >= setup.detected_at:
                    entry_idx = i
                    break
            
            if entry_idx:
                for i in range(entry_idx + 1, min(entry_idx + 13, len(candles))):
                    candle = candles[i]
                    
                    # Check stop loss first
                    if candle.low <= stop_loss:
                        exit_price = stop_loss
                        exit_reason = 'stop_loss'
                        break
                    
                    # Check target
                    if candle.high >= setup.target_price:
                        exit_price = setup.target_price
                        exit_reason = 'target'
                        break
                    
                    # Time stop
                    if i >= entry_idx + 12:
                        exit_price = candle.close
                        exit_reason = 'timeout'
                        break
            
            if exit_price:
                pnl = position_size * (exit_price - entry_price)
                capital += pnl
                
                trade = PaperTrade(
                    trade_id=str(len(trades)),
                    timestamp=setup.detected_at,
                    symbol=symbol,
                    action=TradeAction.BUY,
                    quantity=position_size,
                    entry_price=entry_price,
                    trade_type=TradeType.STOCK,
                    exit_price=exit_price,
                    exit_timestamp=candles[entry_idx + 1].timestamp if entry_idx else setup.detected_at,
                    realized_pnl=pnl,
                    strategy='enhanced_momentum',
                    notes=f"Exit: {exit_reason}, Regime: {regime.market_type.value if regime else 'unknown'}"
                )
                trades.append(trade)
            
            # Track equity
            equity_curve.append({
                'date': setup.detected_at.isoformat() if hasattr(setup.detected_at, 'isoformat') else str(setup.detected_at),
                'capital': capital,
                'total_value': capital
            })
        
        # Calculate metrics
        final_capital = capital
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        
        closed_trades = [t for t in trades if not t.is_open]
        winners = sum(1 for t in closed_trades if t.realized_pnl > 0)
        
        avg_winner = np.mean([t.realized_pnl for t in closed_trades if t.realized_pnl > 0]) if winners > 0 else 0
        avg_loser = np.mean([t.realized_pnl for t in closed_trades if t.realized_pnl <= 0]) if len(closed_trades) > winners else 1
        
        # Advanced metrics
        advanced = self.calculate_advanced_metrics(equity_curve, trades)
        
        # Drawdown analysis
        underwater, max_dd, max_dd_duration = self.calculate_drawdown_curve(equity_curve)
        
        # Monte Carlo
        mc_results = self.mc_simulator.simulate(trades, initial_capital)
        
        # Walk-forward
        wf_results = self.wf_analyzer.analyze(equity_curve)
        
        # Regime performance
        regime_perf = self.calculate_regime_performance(trades, regimes)
        
        # Statistical test
        stats_results = self.statistical_test(trades)
        
        # Calmar ratio
        calmar = total_return / max_dd if max_dd > 0 else 0
        
        return EnhancedBacktestResult(
            strategy_name='Enhanced Compra a Seco (Momentum Breakout)',
            symbol=symbol,
            start_date=df.index[0] if not df.empty else datetime.now(),
            end_date=df.index[-1] if not df.empty else datetime.now(),
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return_pct=total_return,
            annualized_return_pct=total_return * (252 / len(df)) if len(df) > 0 else 0,
            total_trades=len(closed_trades),
            winning_trades=winners,
            losing_trades=len(closed_trades) - winners,
            win_rate=winners / len(closed_trades) if closed_trades else 0,
            avg_trade_return=np.mean([t.realized_pnl for t in closed_trades]) if closed_trades else 0,
            avg_winner=avg_winner,
            avg_loser=avg_loser,
            profit_factor=abs(sum(t.realized_pnl for t in closed_trades if t.realized_pnl > 0)) / abs(sum(t.realized_pnl for t in closed_trades if t.realized_pnl < 0)) if any(t.realized_pnl < 0 for t in closed_trades) else float('inf'),
            payoff_ratio=abs(avg_winner / avg_loser) if avg_loser != 0 else 0,
            max_drawdown_pct=max_dd,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=advanced.get('sharpe_ratio', 0),
            sortino_ratio=advanced.get('sortino_ratio', 0),
            calmar_ratio=calmar,
            volatility_annual=advanced.get('volatility_annual', 0),
            var_95=advanced.get('var_95', 0),
            equity_curve=equity_curve,
            underwater_curve=underwater,
            monthly_returns=[],  # Would need daily aggregation
            regime_performance=regime_perf,
            mc_median_return=mc_results['median_return'],
            mc_worst_case=mc_results['worst_case'],
            mc_best_case=mc_results['best_case'],
            mc_probability_of_profit=mc_results['probability_of_profit'],
            wf_is_consistent=wf_results['is_consistent'],
            wf_in_sample_return=wf_results['in_sample_return'],
            wf_out_of_sample_return=wf_results['out_of_sample_return'],
            p_value=stats_results['p_value'],
            is_statistically_significant=stats_results['is_significant'],
            confidence_interval=stats_results['confidence_interval'],
            trades=trades
        )


def print_enhanced_report(result: EnhancedBacktestResult):
    """Print comprehensive backtest report."""
    print("\n" + "=" * 80)
    print("  ENHANCED BACKTEST REPORT")
    print("=" * 80)
    
    print(f"\nStrategy:     {result.strategy_name}")
    print(f"Symbol:       {result.symbol}")
    print(f"Period:       {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
    
    print("\n" + "─" * 80)
    print("  CAPITAL & RETURNS")
    print("─" * 80)
    print(f"Initial Capital:      ${result.initial_capital:,.2f}")
    print(f"Final Capital:        ${result.final_capital:,.2f}")
    icon = "🟢" if result.total_return_pct >= 0 else "🔴"
    print(f"Total Return:         {icon} {result.total_return_pct:+.2f}%")
    print(f"Annualized Return:    {result.annualized_return_pct:+.2f}%")
    
    print("\n" + "─" * 80)
    print("  TRADE STATISTICS")
    print("─" * 80)
    print(f"Total Trades:         {result.total_trades}")
    print(f"Winning Trades:       {result.winning_trades}")
    print(f"Losing Trades:        {result.losing_trades}")
    print(f"Win Rate:             {result.win_rate:.1%}")
    print(f"Avg Trade Return:     ${result.avg_trade_return:.2f}")
    print(f"Avg Winner:           ${result.avg_winner:.2f}")
    print(f"Avg Loser:            ${result.avg_loser:.2f}")
    print(f"Profit Factor:        {result.profit_factor:.2f}")
    print(f"Payoff Ratio:         {result.payoff_ratio:.2f}")
    
    print("\n" + "─" * 80)
    print("  RISK METRICS")
    print("─" * 80)
    print(f"Max Drawdown:         {result.max_drawdown_pct:.2f}%")
    print(f"Max DD Duration:      {result.max_drawdown_duration} days")
    print(f"Sharpe Ratio:         {result.sharpe_ratio:.2f}")
    print(f"Sortino Ratio:        {result.sortino_ratio:.2f}")
    print(f"Calmar Ratio:         {result.calmar_ratio:.2f}")
    print(f"Annual Volatility:    {result.volatility_annual:.2f}%")
    print(f"VaR 95%:              {result.var_95:.2f}%")
    
    print("\n" + "─" * 80)
    print("  MONTE CARLO SIMULATION (1000 runs)")
    print("─" * 80)
    print(f"Median Return:        {result.mc_median_return:+.2f}%")
    print(f"Worst Case (5%):      {result.mc_worst_case:+.2f}%")
    print(f"Best Case (95%):      {result.mc_best_case:+.2f}%")
    print(f"Probability Profit:   {result.mc_probability_of_profit:.1%}")
    
    print("\n" + "─" * 80)
    print("  WALK-FORWARD ANALYSIS")
    print("─" * 80)
    print(f"Consistent:           {'✅ Yes' if result.wf_is_consistent else '❌ No'}")
    print(f"In-Sample Return:     {result.wf_in_sample_return:+.2f}%")
    print(f"Out-of-Sample Return: {result.wf_out_of_sample_return:+.2f}%")
    
    print("\n" + "─" * 80)
    print("  STATISTICAL SIGNIFICANCE")
    print("─" * 80)
    sig_icon = "✅" if result.is_statistically_significant else "❌"
    print(f"P-Value:              {result.p_value:.4f}")
    print(f"Significant (p<0.05): {sig_icon} {result.is_statistically_significant}")
    print(f"Confidence Interval:  [{result.confidence_interval[0]:.2f}, {result.confidence_interval[1]:.2f}]")
    
    if result.regime_performance:
        print("\n" + "─" * 80)
        print("  PERFORMANCE BY MARKET REGIME")
        print("─" * 80)
        for regime, metrics in result.regime_performance.items():
            print(f"\n{regime.value}:")
            print(f"  Trades:     {metrics['trades']}")
            print(f"  Win Rate:   {metrics['win_rate']:.1%}")
            print(f"  Total P&L:  ${metrics['total_pnl']:,.2f}")
    
    print("\n" + "=" * 80)
