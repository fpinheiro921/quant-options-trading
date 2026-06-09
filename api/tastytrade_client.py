"""
TastyTrade API Client for options trading.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import pandas as pd

from tastytrade import Session, DXLinkStreamer
from tastytrade.dxfeed import Event, Quote, Greeks, Trade
from tastytrade.instruments import Option, Equity, get_option_chain
from tastytrade.account import Account
from tastytrade.order import (
    OrderType, OrderTimeInForce, OrderStatus,
    NewOrder, OrderAction, Leg, PlacedOrder
)
from tastytrade.utils import get_tasty_monthly

from config import Config

logger = logging.getLogger(__name__)


class TastyTradeClient:
    """Client for TastyTrade API interactions."""
    
    def __init__(self, username: str, password: str):
        """Initialize TastyTrade client."""
        self.username = username
        self.password = password
        self.session: Optional[Session] = None
        self.account: Optional[Account] = None
        self.streamer: Optional[DXLinkStreamer] = None
        self._market_data_callbacks: Dict[str, List[callable]] = {}
        
    def authenticate(self, account_id: Optional[str] = None) -> bool:
        """Authenticate with TastyTrade API."""
        try:
            self.session = Session(self.username, self.password)
            
            # Set account
            if account_id:
                self.account = Account.get_account(self.session, account_id)
            else:
                accounts = Account.get_accounts(self.session)
                if accounts:
                    self.account = accounts[0]
                    
            logger.info(f"Authenticated as {self.username}")
            logger.info(f"Using account: {self.account.account_number if self.account else 'None'}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def connect_streamer(self):
        """Connect to DXFeed streaming API."""
        if not self.session:
            raise RuntimeError("Must authenticate before connecting streamer")
            
        try:
            self.streamer = await DXLinkStreamer.create(self.session)
            self.streamer.add_event_listener(self._on_market_data)
            logger.info("Connected to DXFeed streamer")
        except Exception as e:
            logger.error(f"Failed to connect streamer: {e}")
            raise
    
    def _on_market_data(self, event: Event):
        """Handle incoming market data."""
        symbol = getattr(event, 'symbol', None)
        if symbol and symbol in self._market_data_callbacks:
            for callback in self._market_data_callbacks[symbol]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in market data callback: {e}")
    
    def subscribe_quotes(self, symbols: List[str], callback: callable):
        """Subscribe to real-time quotes."""
        if not self.streamer:
            raise RuntimeError("Streamer not connected")
            
        for symbol in symbols:
            if symbol not in self._market_data_callbacks:
                self._market_data_callbacks[symbol] = []
            self._market_data_callbacks[symbol].append(callback)
            
        self.streamer.subscribe(Quote, symbols)
        logger.info(f"Subscribed to quotes for {symbols}")
    
    def subscribe_greeks(self, option_symbols: List[str], callback: callable):
        """Subscribe to real-time Greeks."""
        if not self.streamer:
            raise RuntimeError("Streamer not connected")
            
        for symbol in option_symbols:
            if symbol not in self._market_data_callbacks:
                self._market_data_callbacks[symbol] = []
            self._market_data_callbacks[symbol].append(callback)
            
        self.streamer.subscribe(Greeks, option_symbols)
        logger.info(f"Subscribed to Greeks for {len(option_symbols)} options")
    
    def get_option_chain(self, symbol: str) -> Dict[datetime, List[Option]]:
        """Get option chain for a symbol."""
        if not self.session:
            raise RuntimeError("Not authenticated")
            
        try:
            equity = Equity.get_equity(self.session, symbol)
            chain = get_option_chain(self.session, equity)
            return chain
        except Exception as e:
            logger.error(f"Failed to get option chain for {symbol}: {e}")
            raise
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get current stock quote."""
        if not self.session:
            raise RuntimeError("Not authenticated")
            
        try:
            equity = Equity.get_equity(self.session, symbol)
            return {
                'symbol': symbol,
                'spot_price': equity.close_price if hasattr(equity, 'close_price') else None,
                'last_price': equity.last_price if hasattr(equity, 'last_price') else None,
                'bid': equity.bid_price if hasattr(equity, 'bid_price') else None,
                'ask': equity.ask_price if hasattr(equity, 'ask_price') else None,
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            raise
    
    def get_portfolio_positions(self) -> List[Dict[str, Any]]:
        """Get current portfolio positions."""
        if not self.session or not self.account:
            raise RuntimeError("Not authenticated or no account")
            
        try:
            positions = self.account.get_positions(self.session)
            result = []
            for pos in positions:
                result.append({
                    'symbol': pos.symbol,
                    'quantity': pos.quantity,
                    'average_price': pos.average_open_price,
                    'market_price': pos.mark_price,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'instrument_type': pos.instrument_type,
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get portfolio positions: {e}")
            raise
    
    def get_option_positions(self) -> List[Dict[str, Any]]:
        """Get current option positions."""
        positions = self.get_portfolio_positions()
        return [p for p in positions if p['instrument_type'] == 'Equity Option']
    
    def get_stock_positions(self) -> List[Dict[str, Any]]:
        """Get current stock positions."""
        positions = self.get_portfolio_positions()
        return [p for p in positions if p['instrument_type'] == 'Equity']
    
    def place_order(self, order: NewOrder) -> Optional[PlacedOrder]:
        """Place an order."""
        if not self.session or not self.account:
            raise RuntimeError("Not authenticated or no account")
            
        try:
            placed = self.account.place_order(self.session, order)
            logger.info(f"Order placed: {placed.id}")
            return placed
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def place_option_order(
        self,
        option_symbol: str,
        quantity: int,
        action: str,  # 'BuyToOpen', 'SellToOpen', 'BuyToClose', 'SellToClose'
        order_type: OrderType = OrderType.LIMIT,
        price: Optional[float] = None,
        time_in_force: OrderTimeInForce = OrderTimeInForce.DAY
    ) -> Optional[PlacedOrder]:
        """Place an option order."""
        
        # Map action string to OrderAction
        action_map = {
            'BuyToOpen': OrderAction.BUY_TO_OPEN,
            'SellToOpen': OrderAction.SELL_TO_OPEN,
            'BuyToClose': OrderAction.BUY_TO_CLOSE,
            'SellToClose': OrderAction.SELL_TO_CLOSE,
        }
        
        leg = Leg(
            instrument_type=Option,
            symbol=option_symbol,
            quantity=abs(quantity),
            action=action_map.get(action, OrderAction.SELL_TO_OPEN)
        )
        
        order = NewOrder(
            time_in_force=time_in_force,
            order_type=order_type,
            legs=[leg],
            price=price
        )
        
        return self.place_order(order)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self.session or not self.account:
            raise RuntimeError("Not authenticated or no account")
            
        try:
            self.account.delete_order(self.session, order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get account balance information."""
        if not self.session or not self.account:
            raise RuntimeError("Not authenticated or no account")
            
        try:
            balances = self.account.get_balances(self.session)
            return {
                'cash_available': balances.cash_available,
                'net_liquidating_value': balances.net_liquidating_value,
                'maintenance_requirement': balances.maintenance_requirement,
                'buying_power': balances.buying_power,
            }
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            raise
    
    def get_open_orders(self) -> List[PlacedOrder]:
        """Get list of open orders."""
        if not self.session or not self.account:
            raise RuntimeError("Not authenticated or no account")
            
        try:
            orders = self.account.get_live_orders(self.session)
            return [o for o in orders if o.status in [OrderStatus.LIVE, OrderStatus.RECEIVED]]
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
    
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = '1h',
        lookback_days: int = 30,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get historical candlestick data for technical analysis.
        
        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe ('1m', '5m', '15m', '1h', '2h', '1d')
            lookback_days: Number of days to look back
            end_date: End date (default: now)
            
        Returns:
            DataFrame with OHLCV data
        """
        if not self.session:
            raise RuntimeError("Not authenticated")
        
        try:
            # Get equity object
            equity = Equity.get_equity(self.session, symbol)
            
            # Calculate date range
            if end_date is None:
                end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            # Get candles from TastyTrade API
            # Note: The tastytrade library's get_candles method takes timeframe as string
            candles = equity.get_candles(
                self.session,
                timeframe=timeframe,
                start=start_date,
                end=end_date
            )
            
            # Convert to DataFrame
            data = []
            for candle in candles:
                data.append({
                    'timestamp': candle.datetime,
                    'open': float(candle.open_price),
                    'high': float(candle.high_price),
                    'low': float(candle.low_price),
                    'close': float(candle.close_price),
                    'volume': int(candle.volume) if hasattr(candle, 'volume') else 0
                })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
            
            logger.info(f"Fetched {len(df)} candles for {symbol} ({timeframe})")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            # Return empty DataFrame on error
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
    
    def get_2h_candles(
        self,
        symbol: str,
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """
        Get 120-minute (2-hour) candles for Compra a Seco strategy.
        
        This aggregates 1-hour candles into 2-hour candles.
        """
        # First get 1-hour data
        df_1h = self.get_historical_candles(symbol, '1h', lookback_days)
        
        if df_1h.empty:
            return df_1h
        
        # Resample to 2-hour candles
        df_2h = df_1h.resample('2H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        # Only keep candles within market hours if needed
        # For now, return all
        return df_2h
    
    def get_option_greeks(self, option_symbol: str) -> Optional[Dict[str, float]]:
        """
        Get Greeks for a specific option.
        
        Args:
            option_symbol: Option symbol string
            
        Returns:
            Dictionary with delta, gamma, theta, vega, or None if unavailable
        """
        if not self.session:
            raise RuntimeError("Not authenticated")
        
        try:
            # Get option object
            option = Option.get_option(self.session, option_symbol)
            
            return {
                'delta': float(option.delta) if hasattr(option, 'delta') else None,
                'gamma': float(option.gamma) if hasattr(option, 'gamma') else None,
                'theta': float(option.theta) if hasattr(option, 'theta') else None,
                'vega': float(option.vega) if hasattr(option, 'vega') else None,
                'implied_volatility': float(option.implied_volatility) if hasattr(option, 'implied_volatility') else None,
            }
        except Exception as e:
            logger.error(f"Failed to get Greeks for {option_symbol}: {e}")
            return None
    
    def close(self):
        """Close all connections."""
        if self.streamer:
            # Note: DXLinkStreamer cleanup is handled by async context
            pass
        if self.session:
            # Session cleanup
            pass
        logger.info("TastyTrade client closed")
