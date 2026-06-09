"""
Combined Strategy Backtest - Wheel + Compra a Seco (Momentum)

Both strategies run simultaneously with ONE position each:
- Wheel: 1 position (short put OR covered call)
- Momentum: 1 position (stock breakout trade)

Total: Up to 2 positions open at once (one per strategy)

Period: 5 years (1825 days)
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
import pandas as pd
import numpy as np

from backtest.backtest_engine import BacktestResult, WheelStrategyBacktester, MomentumBreakoutBacktester
from backtest.paper_trading import PaperTradingEnvironment, create_paper_environment, TradeAction
from backtest.enhanced_backtest import print_enhanced_report
from api.alpaca_client import AlpacaClient
from config import Config
from models.technical_analysis import TechnicalAnalyzer, Candle, CompraASecoSetup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Top 20 NASDAQ for Wheel
WHEEL_PORTFOLIO = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'TSLA',
    'NFLX', 'AMD', 'ADBE', 'CRM', 'CSCO', 'INTC',
    'PLTR', 'COIN', 'RBLX', 'SNOW', 'CRWD',
    'QQQ', 'NVDA'  # NVDA weighted
]

# Single symbol for Momentum (2H chart focused)
MOMENTUM_SYMBOL = 'NVDA'  # High volatility for momentum setups


class CombinedStrategyBacktester:
    """
    Backtester that runs Wheel + Momentum simultaneously.
    
    Each strategy maintains ONE position:
    - Wheel: Cash-secured put OR covered call
    - Momentum: Stock position from breakout
    """
    
    def __init__(
        self,
        client: AlpacaClient,
        wheel_env: PaperTradingEnvironment,
        momentum_env: PaperTradingEnvironment,
        wheel_portfolio: List[str],
        momentum_symbol: str,
        target_delta: float = 0.20,
        dte: int = 30
    ):
        self.client = client
        self.wheel_env = wheel_env
        self.momentum_env = momentum_env
        self.wheel_portfolio = wheel_portfolio
        self.momentum_symbol = momentum_symbol
        self.target_delta = target_delta
        self.dte = dte
        self.analyzer = TechnicalAnalyzer()
        
        # Strategy state
        self.wheel_symbol = None
        self.wheel_position_type = None  # 'short_put' or 'covered_call'
        self.wheel_cost_basis = 0.0
        self.wheel_put_strike = 0.0
        self.wheel_call_strike = 0.0
        
        self.momentum_position = None  # Current momentum trade
        
    def estimate_put_premium(self, stock_price: float, strike: float, days_to_expiry: int) -> float:
        """Estimate put premium."""
        distance_pct = (stock_price - strike) / stock_price
        if distance_pct < 0.05:
            return strike * 0.025
        elif distance_pct < 0.10:
            return strike * 0.015
        else:
            return strike * 0.008
    
    def estimate_call_premium(self, stock_price: float, strike: float, days_to_expiry: int) -> float:
        """Estimate call premium."""
        distance_pct = (strike - stock_price) / stock_price
        if distance_pct < 0:
            return strike * 0.03
        elif distance_pct < 0.05:
            return strike * 0.02
        else:
            return strike * 0.01
    
    def estimate_volatility(self, df: pd.DataFrame, window: int = 20) -> float:
        """Estimate annualized volatility."""
        if len(df) < window:
            return 0.40
        returns = df['close'].pct_change().dropna()
        vol = returns.std() * (252 ** 0.5)
        return max(0.20, min(vol, 0.80))
    
    def find_best_wheel_opportunity(self, current_date: datetime, data_dict: Dict) -> Optional[Tuple]:
        """Find best Wheel opportunity across portfolio."""
        best_opportunity = None
        best_score = -1.0
        
        for symbol in self.wheel_portfolio:
            if symbol not in data_dict:
                continue
            
            df = data_dict[symbol]
            idx = df.index.get_indexer([current_date], method='nearest')[0]
            if idx < 0 or idx >= len(df):
                continue
            
            current_price = df.iloc[idx]['close']
            put_strike = round(current_price * (1 - 0.06), 2)
            
            cash_needed = put_strike * 100
            if cash_needed > self.wheel_env.account.cash_balance * 0.30:
                continue
            
            vol = self.estimate_volatility(df.iloc[:idx+1])
            days_to_expiry = self.dte
            premium = self.estimate_put_premium(current_price, put_strike, days_to_expiry)
            
            # Calculate score
            premium_yield = (premium * 100) / cash_needed
            distance_score = 1.0 - abs(0.06 - 0.06) * 5
            vol_score = 1.0 - abs(vol - 0.40) * 2
            score = (premium_yield * 0.5) + (distance_score * 0.3) + (vol_score * 0.2)
            
            if score > best_score:
                best_score = score
                best_opportunity = (symbol, put_strike, premium, score)
        
        return best_opportunity
    
    def check_momentum_setups(self, current_date: datetime, candles: List[Candle]) -> Optional[CompraASecoSetup]:
        """Check for Compra a Seco momentum setups."""
        setups = self.analyzer.find_compra_a_seco_setups(self.momentum_symbol, candles)
        
        # Filter to current date
        for setup in setups:
            if abs((setup.detected_at - current_date).days) <= 1:
                return setup
        
        return None
    
    def run_combined_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        starting_capital: float = 100000.0
    ) -> Dict:
        """
        Run both strategies simultaneously over 5 years.
        
        Each strategy gets $50,000 (half of total capital)
        """
        logger.info("=" * 80)
        logger.info("COMBINED STRATEGY BACKTEST - Wheel + Compra a Seco")
        logger.info("=" * 80)
        logger.info(f"Wheel Portfolio: {len(self.wheel_portfolio)} stocks")
        logger.info(f"Momentum Symbol: {self.momentum_symbol}")
        logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Capital per strategy: ${starting_capital/2:,.2f}")
        
        # Split capital between strategies
        wheel_capital = starting_capital / 2
        momentum_capital = starting_capital / 2
        
        # Fetch data for all symbols
        logger.info("\nFetching historical data...")
        wheel_data = {}
        for symbol in self.wheel_portfolio:
            try:
                df = self.client.get_historical_candles(symbol, '1d', 2000, end_date)
                if not df.empty and len(df) > 100:
                    if df.index.tz is not None:
                        df.index = df.index.tz_localize(None)
                    df = df[(df.index >= start_date) & (df.index <= end_date)]
                    if len(df) >= 60:
                        wheel_data[symbol] = df
                        logger.info(f"  {symbol}: {len(df)} days")
            except Exception as e:
                logger.warning(f"  {symbol}: Failed to load - {e}")
        
        # Fetch 2H data for momentum
        logger.info(f"\nFetching 2H data for {self.momentum_symbol}...")
        try:
            mom_df = self.client.get_2h_candles(self.momentum_symbol, 2000)
            if not mom_df.empty:
                if mom_df.index.tz is not None:
                    mom_df.index = mom_df.index.tz_localize(None)
                mom_df = mom_df[(mom_df.index >= start_date) & (mom_df.index <= end_date)]
                logger.info(f"  {self.momentum_symbol}: {len(mom_df)} 2H candles")
        except Exception as e:
            logger.error(f"Failed to load momentum data: {e}")
            return {}
        
        # Track performance
        wheel_premiums = 0.0
        wheel_stock_pnl = 0.0
        momentum_pnl = 0.0
        momentum_trades = []
        
        wheel_trades = []
        equity_curve = []
        
        # Monthly cycle tracking
        current_date = start_date
        cycle_count = 0
        
        while current_date <= end_date:
            cycle_count += 1
            
            # Calculate expiry
            expiry_date = min(current_date + timedelta(days=self.dte), end_date)
            
            # =====================
            # WHEEL STRATEGY
            # =====================
            if self.wheel_position_type is None:
                # No position - find opportunity
                opportunity = self.find_best_wheel_opportunity(current_date, wheel_data)
                
                if opportunity:
                    symbol, put_strike, premium, score = opportunity
                    
                    # Sell put
                    put_trade = self.wheel_env.execute_option_trade(
                        symbol=symbol,
                        option_symbol=f"{symbol}_PUT_{put_strike}_{expiry_date.strftime('%Y%m%d')}",
                        quantity=1,
                        action=TradeAction.SELL_TO_OPEN,
                        market_price=premium,
                        strike=put_strike,
                        expiry=expiry_date,
                        option_type='put',
                        timestamp=current_date,
                        strategy='wheel'
                    )
                    
                    if put_trade:
                        wheel_trades.append(put_trade)
                        wheel_premiums += premium * 100
                        wheel_capital += premium * 100
                        
                        self.wheel_symbol = symbol
                        self.wheel_position_type = 'short_put'
                        self.wheel_put_strike = put_strike
                        
                        logger.info(f"\n[Cycle {cycle_count}] WHEEL: Sold {symbol} put @ ${put_strike:.2f}")
            
            else:
                # Have position - check outcome
                symbol = self.wheel_symbol
                
                if symbol in wheel_data:
                    df = wheel_data[symbol]
                    expiry_idx = df.index.get_indexer([expiry_date], method='nearest')[0]
                    expiry_price = df.iloc[expiry_idx]['close'] if expiry_idx < len(df) else df.iloc[-1]['close']
                    
                    if self.wheel_position_type == 'short_put':
                        if expiry_price < self.wheel_put_strike:
                            # ASSIGNED
                            stock_buy = self.wheel_env.execute_stock_trade(
                                symbol=symbol, quantity=100, action=TradeAction.BUY,
                                market_price=self.wheel_put_strike, timestamp=expiry_date, strategy='wheel'
                            )
                            wheel_capital -= self.wheel_put_strike * 100
                            self.wheel_cost_basis = self.wheel_put_strike
                            self.wheel_position_type = 'covered_call'
                            
                            # Sell call
                            call_strike = max(self.wheel_put_strike, expiry_price * 1.02)
                            call_strike = round(call_strike, 2)
                            call_premium = self.estimate_call_premium(expiry_price, call_strike, self.dte)
                            
                            call_trade = self.wheel_env.execute_option_trade(
                                symbol=symbol, option_symbol=f"{symbol}_CALL_{call_strike}_{expiry_date.strftime('%Y%m%d')}",
                                quantity=1, action=TradeAction.SELL_TO_OPEN, market_price=call_premium,
                                strike=call_strike, expiry=expiry_date + timedelta(days=self.dte),
                                option_type='call', timestamp=expiry_date, strategy='wheel'
                            )
                            
                            if call_trade:
                                wheel_trades.append(call_trade)
                                wheel_premiums += call_premium * 100
                                wheel_capital += call_premium * 100
                                self.wheel_call_strike = call_strike
                            
                            logger.info(f"[Cycle {cycle_count}] WHEEL: {symbol} ASSIGNED @ ${self.wheel_put_strike:.2f}")
                        else:
                            # Expired worthless
                            logger.info(f"[Cycle {cycle_count}] WHEEL: {symbol} put expired")
                            self.wheel_position_type = None
                            self.wheel_symbol = None
                    
                    elif self.wheel_position_type == 'covered_call':
                        if expiry_price > self.wheel_call_strike:
                            # CALLED AWAY
                            stock_sell = self.wheel_env.execute_stock_trade(
                                symbol=symbol, quantity=100, action=TradeAction.SELL,
                                market_price=self.wheel_call_strike, timestamp=expiry_date, strategy='wheel'
                            )
                            stock_pnl = (self.wheel_call_strike - self.wheel_cost_basis) * 100
                            wheel_stock_pnl += stock_pnl
                            wheel_capital += self.wheel_call_strike * 100
                            
                            logger.info(f"[Cycle {cycle_count}] WHEEL: {symbol} CALLED AWAY @ ${self.wheel_call_strike:.2f} (P&L: ${stock_pnl:+.2f})")
                            
                            self.wheel_position_type = None
                            self.wheel_symbol = None
                        else:
                            # Call expired - sell another
                            call_strike = max(self.wheel_cost_basis, expiry_price * 1.02)
                            call_strike = round(call_strike, 2)
                            call_premium = self.estimate_call_premium(expiry_price, call_strike, self.dte)
                            
                            call_trade = self.wheel_env.execute_option_trade(
                                symbol=symbol, option_symbol=f"{symbol}_CALL_{call_strike}_{expiry_date.strftime('%Y%m%d')}",
                                quantity=1, action=TradeAction.SELL_TO_OPEN, market_price=call_premium,
                                strike=call_strike, expiry=expiry_date + timedelta(days=self.dte),
                                option_type='call', timestamp=expiry_date, strategy='wheel'
                            )
                            
                            if call_trade:
                                wheel_trades.append(call_trade)
                                wheel_premiums += call_premium * 100
                                wheel_capital += call_premium * 100
                                self.wheel_call_strike = call_strike
            
            # =====================
            # MOMENTUM STRATEGY
            # =====================
            if self.momentum_position is None:
                # Check for setup
                # Get recent candles up to current date
                recent_df = mom_df[mom_df.index <= current_date].tail(100)
                if len(recent_df) > 20:
                    candles = []
                    for idx, row in recent_df.iterrows():
                        candles.append(Candle(
                            timestamp=idx,
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume']
                        ))
                    
                    setup = self.check_momentum_setups(current_date, candles)
                    
                    if setup:
                        # Check if we have breakout
                        current_idx = mom_df.index.get_indexer([current_date], method='nearest')[0]
                        if current_idx < len(mom_df):
                            current_price = mom_df.iloc[current_idx]['close']
                            
                            if current_price > setup.breakout_price:
                                # ENTER MOMENTUM TRADE
                                position_size = min(100, int((momentum_capital * 0.20) / current_price))
                                
                                if position_size > 0:
                                    mom_trade = self.momentum_env.execute_stock_trade(
                                        symbol=self.momentum_symbol,
                                        quantity=position_size,
                                        action=TradeAction.BUY,
                                        market_price=current_price,
                                        timestamp=current_date,
                                        strategy='momentum'
                                    )
                                    
                                    if mom_trade:
                                        self.momentum_position = {
                                            'entry_price': current_price,
                                            'quantity': position_size,
                                            'entry_time': current_date,
                                            'stop_loss': setup.stop_loss_price,
                                            'target': setup.target_price
                                        }
                                        momentum_capital -= current_price * position_size
                                        
                                        logger.info(f"[Cycle {cycle_count}] MOMENTUM: BUY {self.momentum_symbol} @ ${current_price:.2f} x {position_size}")
            
            else:
                # Check exit conditions
                current_idx = mom_df.index.get_indexer([current_date], method='nearest')[0]
                if current_idx < len(mom_df):
                    current_price = mom_df.iloc[current_idx]['close']
                    
                    exit_reason = None
                    if current_price >= self.momentum_position['target']:
                        exit_reason = 'target'
                    elif current_price <= self.momentum_position['stop_loss']:
                        exit_reason = 'stop_loss'
                    elif (current_date - self.momentum_position['entry_time']).days >= 5:
                        exit_reason = 'timeout'
                    
                    if exit_reason:
                        # EXIT MOMENTUM TRADE
                        mom_trade = self.momentum_env.execute_stock_trade(
                            symbol=self.momentum_symbol,
                            quantity=self.momentum_position['quantity'],
                            action=TradeAction.SELL,
                            market_price=current_price,
                            timestamp=current_date,
                            strategy='momentum'
                        )
                        
                        pnl = (current_price - self.momentum_position['entry_price']) * self.momentum_position['quantity']
                        momentum_pnl += pnl
                        momentum_capital += current_price * self.momentum_position['quantity']
                        momentum_trades.append({
                            'entry': self.momentum_position['entry_price'],
                            'exit': current_price,
                            'pnl': pnl,
                            'reason': exit_reason
                        })
                        
                        logger.info(f"[Cycle {cycle_count}] MOMENTUM: SELL {self.momentum_symbol} @ ${current_price:.2f} ({exit_reason}, P&L: ${pnl:+.2f})")
                        
                        self.momentum_position = None
            
            # Track equity curve
            wheel_position_value = 0
            if self.wheel_position_type == 'covered_call' and self.wheel_symbol in wheel_data:
                idx = wheel_data[self.wheel_symbol].index.get_indexer([expiry_date], method='nearest')[0]
                if idx < len(wheel_data[self.wheel_symbol]):
                    wheel_position_value = 100 * wheel_data[self.wheel_symbol].iloc[idx]['close']
            
            momentum_position_value = 0
            if self.momentum_position and self.momentum_symbol in mom_df:
                idx = mom_df.index.get_indexer([current_date], method='nearest')[0]
                if idx < len(mom_df):
                    momentum_position_value = self.momentum_position['quantity'] * mom_df.iloc[idx]['close']
            
            total_value = wheel_capital + wheel_position_value + momentum_capital + momentum_position_value
            
            equity_curve.append({
                'date': expiry_date.isoformat(),
                'wheel_capital': wheel_capital,
                'wheel_position': wheel_position_value,
                'momentum_capital': momentum_capital,
                'momentum_position': momentum_position_value,
                'total_value': total_value,
                'cycle': cycle_count
            })
            
            # Move to next month
            current_date = expiry_date + timedelta(days=1)
        
        # Calculate final results
        wheel_final = wheel_capital + (100 * wheel_data[self.wheel_symbol].iloc[-1]['close'] if self.wheel_position_type == 'covered_call' and self.wheel_symbol in wheel_data else 0)
        momentum_final = momentum_capital + (self.momentum_position['quantity'] * mom_df.iloc[-1]['close'] if self.momentum_position else 0)
        
        total_final = wheel_final + momentum_final
        
        logger.info("\n" + "=" * 80)
        logger.info("COMBINED BACKTEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"\nWHEEL STRATEGY:")
        logger.info(f"  Final Capital: ${wheel_final:.2f}")
        logger.info(f"  Premiums Collected: ${wheel_premiums:.2f}")
        logger.info(f"  Stock P&L: ${wheel_stock_pnl:.2f}")
        logger.info(f"  Trades: {len(wheel_trades)}")
        logger.info(f"  Return: {((wheel_final - starting_capital/2) / (starting_capital/2) * 100):+.2f}%")
        
        logger.info(f"\nMOMENTUM STRATEGY:")
        logger.info(f"  Final Capital: ${momentum_final:.2f}")
        logger.info(f"  Trade P&L: ${momentum_pnl:.2f}")
        logger.info(f"  Trades: {len(momentum_trades)}")
        logger.info(f"  Return: {((momentum_final - starting_capital/2) / (starting_capital/2) * 100):+.2f}%")
        
        logger.info(f"\nCOMBINED:")
        logger.info(f"  Initial: ${starting_capital:,.2f}")
        logger.info(f"  Final: ${total_final:,.2f}")
        logger.info(f"  Total Return: {((total_final - starting_capital) / starting_capital * 100):+.2f}%")
        logger.info(f"  Annualized: {((total_final / starting_capital) ** (365 / (end_date - start_date).days) - 1) * 100:+.2f}%")
        
        return {
            'wheel': {
                'final_capital': wheel_final,
                'premiums': wheel_premiums,
                'stock_pnl': wheel_stock_pnl,
                'trades': len(wheel_trades),
                'return_pct': ((wheel_final - starting_capital/2) / (starting_capital/2)) * 100
            },
            'momentum': {
                'final_capital': momentum_final,
                'trade_pnl': momentum_pnl,
                'trades': len(momentum_trades),
                'return_pct': ((momentum_final - starting_capital/2) / (starting_capital/2)) * 100
            },
            'combined': {
                'initial': starting_capital,
                'final': total_final,
                'return_pct': ((total_final - starting_capital) / starting_capital) * 100,
                'annualized_pct': ((total_final / starting_capital) ** (365 / (end_date - start_date).days) - 1) * 100
            },
            'equity_curve': equity_curve
        }


def run_combined_backtest():
    """Run the combined strategy backtest."""
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_API_SECRET,
        paper=True
    )
    client.authenticate()
    
    wheel_env = create_paper_environment(50000.0)  # $50K for Wheel
    momentum_env = create_paper_environment(50000.0)  # $50K for Momentum
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1825)  # 5 years
    
    backtester = CombinedStrategyBacktester(
        client=client,
        wheel_env=wheel_env,
        momentum_env=momentum_env,
        wheel_portfolio=WHEEL_PORTFOLIO,
        momentum_symbol=MOMENTUM_SYMBOL,
        target_delta=0.20,
        dte=30
    )
    
    results = backtester.run_combined_backtest(start_date, end_date, 100000.0)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'combined_strategies_5year_{timestamp}.md'
    
    md = f"""# Combined Strategies Backtest Report

## Overview

**Strategies:** Wheel (Portfolio) + Compra a Seco (Momentum)
**Period:** 5 Years (1825 days)
**Initial Capital:** $100,000 ($50K per strategy)

---

## Wheel Strategy Results

| Metric | Value |
|--------|-------|
| Final Capital | ${results['wheel']['final_capital']:.2f} |
| Return | {results['wheel']['return_pct']:+.2f}% |
| Premiums Collected | ${results['wheel']['premiums']:.2f} |
| Stock P&L | ${results['wheel']['stock_pnl']:.2f} |
| Total Trades | {results['wheel']['trades']} |

---

## Momentum Strategy Results

| Metric | Value |
|--------|-------|
| Final Capital | ${results['momentum']['final_capital']:.2f} |
| Return | {results['momentum']['return_pct']:+.2f}% |
| Trade P&L | ${results['momentum']['trade_pnl']:.2f} |
| Total Trades | {results['momentum']['trades']} |

---

## Combined Results

| Metric | Value |
|--------|-------|
| Initial Capital | ${results['combined']['initial']:,.2f} |
| Final Capital | ${results['combined']['final']:,.2f} |
| **Total Return** | **{results['combined']['return_pct']:+.2f}%** |
| **Annualized** | **{results['combined']['annualized_pct']:+.2f}%** |

---

*Both strategies run simultaneously with ONE position each*
*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md)
    
    print(f"\n✅ Report saved: {report_file}")
    
    client.close()
    return results


if __name__ == "__main__":
    run_combined_backtest()
