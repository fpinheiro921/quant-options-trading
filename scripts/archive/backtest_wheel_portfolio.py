"""
Portfolio Wheel Strategy Backtester

Strategy: Run Wheel on a portfolio of stocks, but only ONE position at a time.
This is the professional approach - scan multiple stocks, pick the best opportunity.

Portfolio Rules:
1. Each month, scan all symbols for best 20 Delta put opportunity
2. Only ONE open position at any time (either short put or covered call)
3. When position closes, scan again for next best opportunity
4. Rotate through portfolio based on opportunity, not fixed allocation

Key Principles (from video):
- Only trade stocks you want to own long-term
- 20 Delta puts = ~80% probability of success
- If assigned, sell calls AT or ABOVE cost basis
- Never take realized losses on shares
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging
import pandas as pd

from backtest.backtest_engine import BacktestResult, WheelStrategyBacktester
from backtest.paper_trading import PaperTradingEnvironment, create_paper_environment, TradeAction
from backtest.enhanced_backtest import print_enhanced_report
from api.alpaca_client import AlpacaClient
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# PORTFOLIO CONFIGURATIONS
# Choose your portfolio by setting DEFAULT_PORTFOLIO below
# =============================================================================

# Portfolio 1: TOP 20 NASDAQ (High Growth, High Volatility)
# Best for: Higher premiums, more assignments, growth-oriented
NASDAQ_PORTFOLIO = [
    # Magnificent 7 (Best of NASDAQ)
    'AAPL',   # Apple - largest cap, most liquid
    'MSFT',   # Microsoft - stable, dividend
    'NVDA',   # NVIDIA - high volatility, great premiums
    'AMZN',   # Amazon - large cap
    'META',   # Meta - volatile
    'GOOGL',  # Google - stable
    'TSLA',   # Tesla - very volatile, highest premiums
    
    # Top NASDAQ Tech (High Premiums)
    'NFLX',   # Netflix - volatile
    'AMD',    # AMD - volatile
    'ADBE',   # Adobe - stable growth
    'CRM',    # Salesforce - volatile
    'CSCO',   # Cisco - stable, dividend
    'INTC',   # Intel - value play
    
    # High Volatility Growth (Best for Wheel)
    'PLTR',   # Palantir - very volatile
    'COIN',   # Coinbase - crypto volatility
    'RBLX',   # Roblox - growth
    'SNOW',   # Snowflake - growth
    'CRWD',   # CrowdStrike - cybersecurity
    
    # Diversification
    'QQQ',    # NASDAQ 100 ETF
    'NVDA',   # NVIDIA weighted (best premium generator)
]

# Portfolio 2: TOP 20 S&P 500 (Blue Chip, Stable, Dividend)
# Best for: Conservative income, lower volatility, dividend stocks
SP500_PORTFOLIO = [
    # Mega Cap Blue Chips
    'AAPL',   # Apple
    'MSFT',   # Microsoft
    'AMZN',   # Amazon
    'GOOGL',  # Google
    'BRK-B',  # Berkshire Hathaway
    'JPM',    # JPMorgan Chase
    'JNJ',    # Johnson & Johnson
    'V',      # Visa
    'PG',     # Procter & Gamble
    
    # Dividend Aristocrats
    'UNH',    # UnitedHealth
    'HD',     # Home Depot
    'MA',     # Mastercard
    'BAC',    # Bank of America
    'ABBV',   # AbbVie
    'PFE',    # Pfizer
    'KO',     # Coca-Cola
    'PEP',    # PepsiCo
    'WMT',    # Walmart
    'DIS',    # Disney
    
    # Diversified
    'SPY',    # S&P 500 ETF
    'XOM',    # ExxonMobil (energy)
]

# Portfolio 3: HIGH VOLATILITY (Maximum Premiums)
# Best for: Aggressive income, frequent assignments, experienced traders
HIGH_VOL_PORTFOLIO = [
    # Very High Volatility (10-15% monthly swings)
    'TSLA',   # Tesla - EV leader, extreme volatility
    'NVDA',   # NVIDIA - AI chip boom
    'PLTR',   # Palantir - government AI contracts
    'COIN',   # Coinbase - crypto proxy
    'RBLX',   # Roblox - metaverse/gaming
    'SNOW',   # Snowflake - cloud data
    'CRWD',   # CrowdStrike - cybersecurity
    'NET',    # Cloudflare - internet infrastructure
    'DDOG',   # Datadog - cloud monitoring
    'ZM',     # Zoom - video communications
    
    # High Volatility Growth
    'AMD',    # AMD - semiconductor
    'SQ',     # Block (Square) - fintech
    'SHOP',   # Shopify - e-commerce
    'UPST',   # Upstart - AI lending
    'SOFI',   # SoFi - fintech bank
    'LCID',   # Lucid - EV luxury
    'RIVN',   # Rivian - EV trucks
    'GME',    # GameStop - meme volatility
    'AMC',    # AMC - meme volatility
    'MRNA',   # Moderna - biotech
    
    # Diversified
    'ARKK',   # ARK Innovation ETF
    'TQQQ',   # 3x Leveraged NASDAQ (extreme)
]

# Portfolio 4: DIVIDEND FOCUS (Income + Stability)
# Best for: Conservative investors, dividend income, lower risk
DIVIDEND_PORTFOLIO = [
    # Dividend Aristocrats (25+ years of increases)
    'JNJ',    # Johnson & Johnson (2.9% yield)
    'PG',     # Procter & Gamble (2.5% yield)
    'KO',     # Coca-Cola (3.1% yield)
    'PEP',    # PepsiCo (3.0% yield)
    'WMT',    # Walmart (1.5% yield)
    'MCD',    # McDonald's (2.4% yield)
    'TGT',    # Target (3.2% yield)
    'COST',   # Costco (0.7% yield)
    'LOW',    # Lowe's (2.1% yield)
    'HD',     # Home Depot (2.5% yield)
    
    # High Dividend Yield (4%+)
    'VZ',     # Verizon (6.8% yield)
    'T',      # AT&T (6.5% yield)
    'XOM',    # ExxonMobil (5.4% yield)
    'CVX',    # Chevron (5.2% yield)
    'BMY',    # Bristol Myers (4.8% yield)
    'ABBV',   # AbbVie (4.3% yield)
    
    # Tech Dividends
    'MSFT',   # Microsoft (0.8% yield)
    'AAPL',   # Apple (0.5% yield)
    'CSCO',   # Cisco (3.2% yield)
    'INTC',   # Intel (1.2% yield)
    
    # Diversified
    'SCHD',   # Schwab US Dividend ETF
    'VYM',    # Vanguard High Dividend Yield
]

# Portfolio 5: SECTOR ROTATION (Diversified by Industry)
# Best for: Sector rotation strategy, balanced exposure
SECTOR_PORTFOLIO = [
    # Technology (3)
    'NVDA',   # Semiconductors
    'MSFT',   # Software
    'AAPL',   # Hardware
    
    # Financials (3)
    'JPM',    # Banks
    'V',      # Payments
    'BLK',    # Asset Management
    
    # Healthcare (3)
    'JNJ',    # Pharmaceuticals
    'UNH',    # Health Insurance
    'ABBV',   # Biotech
    
    # Consumer (3)
    'AMZN',   # E-commerce
    'WMT',    # Retail
    'KO',     # Beverages
    
    # Energy (2)
    'XOM',    # Oil
    'CVX',    # Oil
    
    # Industrial (2)
    'CAT',    # Machinery
    'GE',     # Aerospace/Industrial
    
    # Communications (2)
    'GOOGL',  # Internet
    'VZ',     # Telecom
    
    # Materials (1)
    'LIN',    # Chemicals
    
    # Real Estate (1)
    'AMT',    # REITs
    
    # Diversified
    'SPY',    # S&P 500 ETF
    'QQQ',    # NASDAQ ETF
]

# Portfolio 6: SMALL CAP GROWTH (Higher Risk/Reward)
# Best for: Aggressive growth, higher volatility than large caps
SMALL_CAP_PORTFOLIO = [
    # Russell 2000 Components (High Growth)
    'IWM',    # Russell 2000 ETF (benchmark)
    'AVAV',   # AeroVironment - drones
    'DKNG',   # DraftKings - sports betting
    'HOOD',   # Robinhood - fintech
    'AFRM',   # Affirm - buy now pay later
    'TOST',   # Toast - restaurant tech
    'BILL',   # Bill.com - payments
    'ASAN',   # Asana - productivity
    'MDB',    # MongoDB - database
    'TWLO',   # Twilio - communications
    
    # Small Cap Tech
    'OKTA',   # Identity management
    'ZI',     # ZoomInfo - sales intel
    'HUBS',   # HubSpot - marketing
    'FSLY',   # Fastly - edge cloud
    'ESTC',   # Elastic - search
    'SPLK',   # Splunk - data
    'DOCU',   # DocuSign - e-signature
    'PD',     # PagerDuty - ops
    'S',      # SentinelOne - security
    'CYBR',   # CyberArk - security
    
    # Diversified
    'VTWO',   # Vanguard Russell 2000
    'IWM',    # (reiterated)
]

# =============================================================================
# SELECT YOUR PORTFOLIO HERE
# =============================================================================

# DEFAULT_PORTFOLIO = NASDAQ_PORTFOLIO      # High growth, tech-focused
# DEFAULT_PORTFOLIO = SP500_PORTFOLIO       # Blue chip, stable dividends
# DEFAULT_PORTFOLIO = HIGH_VOL_PORTFOLIO    # Maximum premiums, high risk
# DEFAULT_PORTFOLIO = DIVIDEND_PORTFOLIO    # Conservative income focus
# DEFAULT_PORTFOLIO = SECTOR_PORTFOLIO      # Balanced sector exposure
# DEFAULT_PORTFOLIO = SMALL_CAP_PORTFOLIO   # Aggressive growth

DEFAULT_PORTFOLIO = NASDAQ_PORTFOLIO  # Default: Top 20 NASDAQ


def calculate_opportunity_score(
    stock_price: float,
    put_strike: float,
    premium: float,
    volatility: float,
    stock_symbol: str
) -> float:
    """
    Calculate opportunity score for a potential Wheel trade.
    
    Higher score = better opportunity
    
    Factors:
    - Premium yield (higher = better)
    - Distance from current price (further = safer)
    - Volatility (moderate = better than too low or too high)
    """
    # Premium yield as % of capital required
    capital_required = put_strike * 100
    premium_yield = (premium * 100) / capital_required
    
    # Distance score (20 Delta is ~6% OTM, which is ideal)
    distance_pct = (stock_price - put_strike) / stock_price
    distance_score = 1.0 - abs(distance_pct - 0.06) * 5  # Peak at 6% OTM
    
    # Volatility score (30-50% is ideal for Wheel)
    vol_score = 1.0 - abs(volatility - 0.40) * 2  # Peak at 40% vol
    
    # Combined score (weighted)
    score = (premium_yield * 0.5) + (distance_score * 0.3) + (vol_score * 0.2)
    
    return score


class PortfolioWheelBacktester:
    """
    Wheel strategy backtester that manages a portfolio with ONE open position.
    """
    
    def __init__(
        self,
        client: AlpacaClient,
        paper_env: PaperTradingEnvironment,
        symbols: List[str],
        target_delta: float = 0.20,
        dte: int = 30,
        max_position_pct: float = 0.30
    ):
        self.client = client
        self.paper = paper_env
        self.symbols = symbols
        self.target_delta = target_delta
        self.dte = dte
        self.max_position_pct = max_position_pct
        
        # State tracking
        self.historical_data = {}
        self.current_symbol = None
        self.position_type = None  # 'short_put' or 'covered_call'
        self.cost_basis = 0.0
        self.put_strike = 0.0
        self.call_strike = 0.0
        
    def fetch_portfolio_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical data for all symbols in portfolio."""
        data = {}
        days_needed = (end_date - start_date).days + 60
        
        logger.info(f"Fetching data for {len(self.symbols)} symbols...")
        
        for symbol in self.symbols:
            try:
                df = self.client.get_historical_candles(symbol, '1d', days_needed, end_date)
                if not df.empty and len(df) > 30:
                    # Handle timezone
                    if df.index.tz is not None:
                        df.index = df.index.tz_localize(None)
                    
                    # Filter to backtest period
                    df = df[(df.index >= start_date) & (df.index <= end_date)]
                    
                    if len(df) >= 20:
                        data[symbol] = df
                        logger.info(f"  ✅ {symbol}: {len(df)} days (${df.iloc[-1]['close']:.2f})")
                    else:
                        logger.warning(f"  ⚠️  {symbol}: Only {len(df)} days, skipping")
                else:
                    logger.warning(f"  ❌ {symbol}: No data")
            except Exception as e:
                logger.error(f"  ❌ {symbol}: Error fetching - {e}")
        
        logger.info(f"Successfully loaded {len(data)} symbols")
        return data
    
    def estimate_volatility(self, df: pd.DataFrame, window: int = 20) -> float:
        """Estimate annualized volatility from historical data."""
        if len(df) < window:
            return 0.40  # Default 40%
        
        returns = df['close'].pct_change().dropna()
        vol = returns.std() * (252 ** 0.5)  # Annualized
        return max(0.20, min(vol, 0.80))  # Clamp between 20-80%
    
    def find_best_opportunity(
        self,
        current_date: datetime,
        available_symbols: List[str]
    ) -> Optional[Tuple[str, float, float, float]]:
        """
        Find the best Wheel opportunity across portfolio.
        
        Returns: (symbol, put_strike, premium, score) or None
        """
        best_opportunity = None
        best_score = -1.0
        
        for symbol in available_symbols:
            if symbol not in self.historical_data:
                continue
            
            df = self.historical_data[symbol]
            
            # Get current price
            idx = df.index.get_indexer([current_date], method='nearest')[0]
            if idx < 0 or idx >= len(df):
                continue
            
            current_price = df.iloc[idx]['close']
            
            # Calculate 20 Delta put strike (~6% OTM)
            put_strike = round(current_price * (1 - 0.06), 2)
            
            # Estimate volatility
            vol = self.estimate_volatility(df.iloc[:idx+1])
            
            # Calculate premium (simplified Black-Scholes estimation)
            # 20 Delta put ~ 2-3% of strike for 30 DTE with moderate vol
            premium = put_strike * 0.025 * (vol / 0.40)  # Scale by vol
            
            # Check if we have enough capital
            capital_needed = put_strike * 100
            available_capital = self.paper.account.cash_balance
            
            if capital_needed > available_capital * self.max_position_pct:
                continue  # Can't afford this position
            
            # Calculate opportunity score
            score = calculate_opportunity_score(
                current_price, put_strike, premium, vol, symbol
            )
            
            if score > best_score:
                best_score = score
                best_opportunity = (symbol, put_strike, premium, score)
        
        return best_opportunity
    
    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        starting_capital: float = 100000.0
    ) -> BacktestResult:
        """
        Run portfolio Wheel backtest with ONE open position at a time.
        """
        logger.info("=" * 80)
        logger.info("PORTFOLIO WHEEL BACKTEST")
        logger.info("=" * 80)
        logger.info(f"Symbols: {', '.join(self.symbols)}")
        logger.info(f"Strategy: ONE open position at a time")
        logger.info(f"Capital: ${starting_capital:,.2f}")
        logger.info(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Fetch data for all symbols
        self.historical_data = self.fetch_portfolio_data(start_date, end_date)
        
        if not self.historical_data:
            logger.error("No data available for any symbols")
            return self._empty_result(start_date, end_date, starting_capital)
        
        # Track performance
        capital = starting_capital
        total_premiums = 0.0
        total_stock_pnl = 0.0
        trades = []
        equity_curve = []
        cycle_count = 0
        
        # Generate monthly dates for trading
        current_date = start_date
        available_symbols = list(self.historical_data.keys())
        
        while current_date <= end_date:
            cycle_count += 1
            
            # Calculate expiry (30 days or end of backtest)
            expiry_date = min(current_date + timedelta(days=self.dte), end_date)
            
            # Check if current position is still open
            if self.position_type is None:
                # NO OPEN POSITION - Find best opportunity
                opportunity = self.find_best_opportunity(current_date, available_symbols)
                
                if opportunity:
                    symbol, put_strike, premium, score = opportunity
                    
                    # SELL CASH-SECURED PUT
                    logger.info(f"\n📅 {current_date.strftime('%Y-%m-%d')} - Cycle {cycle_count}")
                    logger.info(f"🎯 Best Opportunity: {symbol} (Score: {score:.3f})")
                    logger.info(f"   Stock: ${self.historical_data[symbol].iloc[
                        self.historical_data[symbol].index.get_indexer([current_date], method='nearest')[0]
                    ]['close']:.2f}")
                    logger.info(f"   Put Strike: ${put_strike:.2f}")
                    logger.info(f"   Premium: ${premium:.2f} (${premium*100:.0f} total)")
                    
                    trade = self.paper.execute_option_trade(
                        symbol=symbol,
                        option_symbol=f"{symbol}_PUT_{put_strike}_{expiry_date.strftime('%Y%m%d')}",
                        quantity=1,
                        action=TradeAction.SELL_TO_OPEN,
                        market_price=premium,
                        strike=put_strike,
                        expiry=expiry_date,
                        option_type='put',
                        timestamp=current_date,
                        strategy='portfolio_wheel'
                    )
                    
                    if trade:
                        trades.append(trade)
                        premium_amount = premium * 100
                        total_premiums += premium_amount
                        capital += premium_amount  # Add premium to capital
                        
                        # Set state
                        self.current_symbol = symbol
                        self.position_type = 'short_put'
                        self.put_strike = put_strike
                        
                        logger.info(f"   ✅ SOLD PUT on {symbol}")
                        logger.info(f"   💰 Collected premium: ${premium_amount:.2f}")
                else:
                    logger.debug(f"Cycle {cycle_count}: No viable opportunity found")
            
            else:
                # HAVE OPEN POSITION - Check outcome
                symbol = self.current_symbol
                
                if symbol not in self.historical_data:
                    # Symbol no longer available, close position
                    self.position_type = None
                    self.current_symbol = None
                else:
                    df = self.historical_data[symbol]
                    
                    # Get expiry price
                    expiry_idx = df.index.get_indexer([expiry_date], method='nearest')[0]
                    if expiry_idx >= len(df):
                        expiry_price = df.iloc[-1]['close']
                    else:
                        expiry_price = df.iloc[expiry_idx]['close']
                    
                    if self.position_type == 'short_put':
                        # Check put assignment
                        if expiry_price < self.put_strike:
                            # ASSIGNED - Buy shares via stock trade first
                            stock_buy = self.paper.execute_stock_trade(
                                symbol=symbol,
                                quantity=100,
                                action=TradeAction.BUY,
                                market_price=self.put_strike,
                                timestamp=expiry_date,
                                strategy='portfolio_wheel'
                            )
                            
                            capital -= self.put_strike * 100
                            self.cost_basis = self.put_strike
                            self.position_type = 'covered_call'
                            
                            logger.info(f"\n📅 {expiry_date.strftime('%Y-%m-%d')} - Cycle {cycle_count}")
                            logger.info(f"🔴 ASSIGNED on {symbol}")
                            logger.info(f"   Bought 100 shares @ ${self.put_strike:.2f}")
                            logger.info(f"   Stock closed @ ${expiry_price:.2f}")
                            
                            # Sell call at or above cost basis
                            call_strike = max(self.put_strike, expiry_price * 1.02)
                            call_strike = round(call_strike, 2)
                            
                            # Calculate call premium
                            vol = self.estimate_volatility(df.iloc[:expiry_idx+1])
                            call_premium = call_strike * 0.02 * (vol / 0.40)
                            
                            call_trade = self.paper.execute_option_trade(
                                symbol=symbol,
                                option_symbol=f"{symbol}_CALL_{call_strike}_{expiry_date.strftime('%Y%m%d')}",
                                quantity=1,
                                action=TradeAction.SELL_TO_OPEN,
                                market_price=call_premium,
                                strike=call_strike,
                                expiry=expiry_date + timedelta(days=self.dte),
                                option_type='call',
                                timestamp=expiry_date,
                                strategy='portfolio_wheel'
                            )
                            
                            if call_trade:
                                trades.append(call_trade)
                                call_premium_amount = call_premium * 100
                                total_premiums += call_premium_amount
                                capital += call_premium_amount  # Add premium to capital
                                self.call_strike = call_strike
                                logger.info(f"   ✅ SOLD CALL ${call_strike:.2f} @ ${call_premium:.2f}")
                                logger.info(f"   💰 Collected call premium: ${call_premium_amount:.2f}")
                        else:
                            # Put expired worthless - position closed
                            logger.info(f"\n📅 {expiry_date.strftime('%Y-%m-%d')} - Cycle {cycle_count}")
                            logger.info(f"🟢 {symbol} PUT expired worthless")
                            logger.info(f"   Stock: ${expiry_price:.2f}, Strike: ${self.put_strike:.2f}")
                            
                            # Close position, ready for next opportunity
                            self.position_type = None
                            self.current_symbol = None
                    
                    elif self.position_type == 'covered_call':
                        # Check call assignment
                        if expiry_price > self.call_strike:
                            # CALLED AWAY - Sell shares at call strike
                            stock_sell = self.paper.execute_stock_trade(
                                symbol=symbol,
                                quantity=100,
                                action=TradeAction.SELL,
                                market_price=self.call_strike,
                                timestamp=expiry_date,
                                strategy='portfolio_wheel'
                            )
                            
                            stock_pnl = (self.call_strike - self.cost_basis) * 100
                            total_stock_pnl += stock_pnl
                            capital += self.call_strike * 100
                            
                            logger.info(f"\n📅 {expiry_date.strftime('%Y-%m-%d')} - Cycle {cycle_count}")
                            logger.info(f"💰 CALLED AWAY on {symbol}")
                            logger.info(f"   Sold 100 shares @ ${self.call_strike:.2f}")
                            logger.info(f"   Cost basis: ${self.cost_basis:.2f}")
                            logger.info(f"   Stock P&L: ${stock_pnl:+.2f}")
                            
                            # Close position, ready for next opportunity
                            self.position_type = None
                            self.current_symbol = None
                        else:
                            # Call expired worthless - keep shares, sell another call
                            logger.info(f"\n📅 {expiry_date.strftime('%Y-%m-%d')} - Cycle {cycle_count}")
                            logger.info(f"🟡 {symbol} CALL expired worthless")
                            logger.info(f"   Still holding shares, will sell next month's call")
                            
                            # Sell next month's call at or above cost basis
                            call_strike = max(self.put_strike, expiry_price * 1.02)
                            call_strike = round(call_strike, 2)
                            
                            vol = self.estimate_volatility(df.iloc[:expiry_idx+1])
                            call_premium = call_strike * 0.02 * (vol / 0.40)
                            
                            call_trade = self.paper.execute_option_trade(
                                symbol=symbol,
                                option_symbol=f"{symbol}_CALL_{call_strike}_{expiry_date.strftime('%Y%m%d')}",
                                quantity=1,
                                action=TradeAction.SELL_TO_OPEN,
                                market_price=call_premium,
                                strike=call_strike,
                                expiry=expiry_date + timedelta(days=self.dte),
                                option_type='call',
                                timestamp=expiry_date,
                                strategy='portfolio_wheel'
                            )
                            
                            if call_trade:
                                trades.append(call_trade)
                                call_premium_amount = call_premium * 100
                                total_premiums += call_premium_amount
                                capital += call_premium_amount  # Add premium to capital
                                self.call_strike = call_strike
                                logger.info(f"   💰 Collected roll premium: ${call_premium_amount:.2f}")
            
            # Track equity curve
            position_value = 0
            if self.position_type == 'covered_call' and self.current_symbol:
                symbol = self.current_symbol
                if symbol in self.historical_data:
                    df = self.historical_data[symbol]
                    idx = df.index.get_indexer([expiry_date], method='nearest')[0]
                    if idx < len(df):
                        position_value = 100 * df.iloc[idx]['close']
            
            total_value = capital + position_value
            
            equity_curve.append({
                'date': expiry_date.isoformat(),
                'capital': capital,
                'position_value': position_value,
                'total_value': total_value,
                'current_symbol': self.current_symbol,
                'position_type': self.position_type,
                'cycle': cycle_count,
                'premiums': total_premiums,
                'stock_pnl': total_stock_pnl
            })
            
            # Move to next month
            current_date = expiry_date + timedelta(days=1)
        
        # Calculate final results
        final_value = capital
        if self.position_type == 'covered_call' and self.current_symbol:
            symbol = self.current_symbol
            if symbol in self.historical_data:
                final_price = self.historical_data[symbol].iloc[-1]['close']
                final_value += 100 * final_price
        
        logger.info("\n" + "=" * 80)
        logger.info("PORTFOLIO WHEEL BACKTEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Cycles: {cycle_count}")
        logger.info(f"Total Trades: {len(trades)}")
        logger.info(f"Total Premiums: ${total_premiums:.2f}")
        logger.info(f"Total Stock P&L: ${total_stock_pnl:.2f}")
        logger.info(f"Final Capital: ${capital:.2f}")
        logger.info(f"Final Value: ${final_value:.2f}")
        logger.info(f"Total Return: {((final_value - starting_capital) / starting_capital * 100):+.2f}%")
        logger.info(f"Annualized Return: {((final_value / starting_capital) ** (365 / (end_date - start_date).days) - 1) * 100:+.2f}%")
        
        return BacktestResult(
            strategy_name='Portfolio Wheel',
            symbol=f"Portfolio ({len(self.symbols)} stocks)",
            start_date=start_date,
            end_date=end_date,
            initial_capital=starting_capital,
            final_capital=final_value,
            total_return_pct=((final_value - starting_capital) / starting_capital) * 100,
            total_trades=len(trades),
            winning_trades=sum(1 for t in trades if t.realized_pnl > 0),
            losing_trades=sum(1 for t in trades if t.realized_pnl < 0),
            win_rate=0,  # Calculate properly
            avg_trade_return=0,
            max_drawdown_pct=0,
            sharpe_ratio=0,
            equity_curve=equity_curve,
            trades=trades
        )
    
    def _empty_result(self, start, end, capital) -> BacktestResult:
        """Create empty result for failed backtest."""
        return BacktestResult(
            strategy_name='Portfolio Wheel',
            symbol="Portfolio",
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


def generate_portfolio_report(result: BacktestResult, symbols: List[str], days: int) -> str:
    """Generate markdown report for portfolio Wheel backtest."""
    
    md = f"""# 📊 Portfolio Wheel Strategy Report

## Overview

**Strategy:** Wheel on Portfolio (ONE position at a time)
**Portfolio:** {', '.join(symbols)}
**Period:** {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}
**Duration:** {days} days

## Performance Summary

| Metric | Value |
|--------|-------|
| Initial Capital | ${result.initial_capital:,.2f} |
| Final Capital | ${result.final_capital:,.2f} |
| Total Return | {result.total_return_pct:+.2f}% |
| Total Trades | {result.total_trades} |
| Symbols Traded | {len(symbols)} |

## Trade Log

| # | Symbol | Action | Strike | Premium | Date |
|---|--------|--------|--------|---------|------|
"""
    
    for i, trade in enumerate(result.trades[:30], 1):
        date_str = trade.timestamp.strftime('%Y-%m-%d') if hasattr(trade.timestamp, 'strftime') else str(trade.timestamp)[:10]
        strike = trade.option_strike if hasattr(trade, 'option_strike') else 0
        premium = trade.entry_price if hasattr(trade, 'entry_price') else 0
        
        md += f"| {i} | {trade.symbol} | {trade.action.value} | ${strike:.2f} | ${premium:.2f} | {date_str} |\n"
    
    if len(result.trades) > 30:
        md += f"\n*... and {len(result.trades) - 30} more trades*\n"
    
    md += f"""

## Key Insights

### Strategy Rules Applied
- ✅ **20 Delta Puts**: ~6% OTM, ~80% probability of success
- ✅ **Monthly Cycles**: 30 DTE for consistent income
- ✅ **Portfolio Approach**: Scan {len(symbols)} symbols, pick best opportunity
- ✅ **Single Position**: Only ONE trade open at any time
- ✅ **Never Sell Calls Below Cost Basis**: Protects against realized losses

### Performance Analysis
- **Return:** {result.total_return_pct:+.2f}% over {days} days
- **Annualized:** {(result.total_return_pct * 365 / days):+.2f}%
- **Trade Frequency:** {len(result.trades)} trades in {days // 30} months
- **Capital Efficiency:** 30% max allocation per position

### Recommendations

1. **{'✅ Strategy is viable' if result.total_return_pct > 5 else '⚠️ Mixed results - test longer'}
2. **Portfolio diversification** reduces single-stock risk
3. **Opportunity scanning** finds best premium/yield each month
4. **Consider adding more volatile stocks** (TSLA, NVDA) for higher premiums

---

*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Backtest period: {days} days*
"""
    
    return md


def run_portfolio_backtest(symbols: List[str] = None, days: int = 730):
    """Run portfolio Wheel backtest."""
    
    if symbols is None:
        symbols = DEFAULT_PORTFOLIO
    
    print("=" * 80)
    print("  PORTFOLIO WHEEL STRATEGY BACKTEST")
    print("=" * 80)
    print(f"\nPortfolio: {', '.join(symbols)}")
    print(f"Duration: {days} days (~2 years)")
    print(f"Approach: ONE open position at a time, scan all symbols monthly")
    
    # Initialize
    client = AlpacaClient(
        Config.ALPACA_API_KEY,
        Config.ALPACA_API_SECRET,
        paper=True
    )
    client.authenticate()
    
    paper = create_paper_environment(100000.0)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Run backtest
    backtester = PortfolioWheelBacktester(
        client=client,
        paper_env=paper,
        symbols=symbols,
        target_delta=0.20,
        dte=30
    )
    
    result = backtester.run_backtest(start_date, end_date, 100000.0)
    
    # Generate report
    report = generate_portfolio_report(result, symbols, days)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'portfolio_wheel_{timestamp}.md'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n" + "=" * 80)
    print("  REPORT SAVED")
    print("=" * 80)
    print(f"\n✅ Report: {filename}")
    
    client.close()
    
    return result


if __name__ == "__main__":
    # Allow custom symbols from command line
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
    else:
        symbols = DEFAULT_PORTFOLIO
    
    days = 1825  # 5 years
    run_portfolio_backtest(symbols, days)
