"""
Alpaca API Client for stocks and options trading.

Uses Alpaca's official API for market data and trading.
Documentation: https://alpaca.markets/docs/
"""
import logging
import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import time

from config import Config

logger = logging.getLogger(__name__)


class AlpacaClient:
    """Client for Alpaca API interactions."""
    
    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        """Initialize Alpaca client.
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            paper: Use paper trading (True) or live (False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper = paper
        
        # Set base URL
        if paper:
            self.base_url = "https://paper-api.alpaca.markets/v2"
            self.data_url = "https://data.alpaca.markets/v2"
        else:
            self.base_url = "https://api.alpaca.markets/v2"
            self.data_url = "https://data.alpaca.markets/v2"
        
        self.session = requests.Session()
        self.session.headers.update({
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret
        })
        
        self.account: Optional[Dict] = None
        self.authenticated = False
        
    def authenticate(self) -> bool:
        """Authenticate with Alpaca API."""
        try:
            response = self.session.get(f"{self.base_url}/account")
            response.raise_for_status()
            self.account = response.json()
            self.authenticated = True
            
            logger.info(f"Authenticated with Alpaca ({'paper' if self.paper else 'live'})")
            logger.info(f"Account: {self.account.get('account_number')}")
            logger.info(f"Buying Power: ${self.account.get('buying_power', 0)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Alpaca authentication failed: {e}")
            self.authenticated = False
            return False
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get account balance information."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            response = self.session.get(f"{self.base_url}/account")
            response.raise_for_status()
            account = response.json()
            
            return {
                'cash_available': float(account.get('cash', 0)),
                'cash': float(account.get('cash', 0)),
                'buying_power': float(account.get('buying_power', 0)),
                'net_liquidating_value': float(account.get('portfolio_value', 0)),
                'portfolio_value': float(account.get('portfolio_value', 0)),
                'equity': float(account.get('equity', 0)),
                'maintenance_requirement': float(account.get('maintenance_margin', 0)),
            }
            
        except Exception as e:
            logger.error(f"Failed to get account balance: {e}")
            raise
    
    def get_portfolio_positions(self) -> List[Dict[str, Any]]:
        """Get current portfolio positions."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            response = self.session.get(f"{self.base_url}/positions")
            response.raise_for_status()
            positions = response.json()
            
            formatted_positions = []
            for pos in positions:
                formatted_positions.append({
                    'symbol': pos.get('symbol'),
                    'quantity': int(float(pos.get('qty', 0))),
                    'average_price': float(pos.get('avg_entry_price', 0)),
                    'market_price': float(pos.get('current_price', 0)),
                    'market_value': float(pos.get('market_value', 0)),
                    'unrealized_pnl': float(pos.get('unrealized_pl', 0)),
                    'realized_pnl': float(pos.get('realized_pl', 0)),
                    'instrument_type': self._get_instrument_type(pos.get('symbol')),
                })
            
            return formatted_positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    def get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time stock quote."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            # Get latest trade
            response = self.session.get(
                f"{self.data_url}/stocks/{symbol}/trades/latest",
                headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret}
            )
            
            if response.status_code == 200:
                trade_data = response.json().get('trade', {})
                
                # Get quote data
                quote_response = self.session.get(
                    f"{self.data_url}/stocks/{symbol}/quotes/latest",
                    headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret}
                )
                
                quote_data = {}
                if quote_response.status_code == 200:
                    quote_data = quote_response.json().get('quote', {})
                
                return {
                    'symbol': symbol,
                    'last_price': float(trade_data.get('p', 0)),  # price
                    'bid': float(quote_data.get('bp', 0)),  # bid price
                    'ask': float(quote_data.get('ap', 0)),  # ask price
                    'bid_size': int(quote_data.get('bs', 0)),
                    'ask_size': int(quote_data.get('as', 0)),
                    'volume': int(trade_data.get('v', 0)),  # volume
                    'timestamp': trade_data.get('t'),  # timestamp
                }
            else:
                logger.warning(f"Could not get quote for {symbol}: {response.status_code}")
                return {'symbol': symbol, 'last_price': 0, 'bid': 0, 'ask': 0}
                
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return {'symbol': symbol, 'last_price': 0, 'bid': 0, 'ask': 0}
    
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = '1Day',
        limit: int = 100,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Get historical price candles.
        
        Note: Alpaca free tier (IEX) has limited historical data.
        For longer history, we fall back to yfinance.
        """
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            # First try Alpaca
            params = {
                'timeframe': timeframe,
                'limit': min(limit, 1000),  # Alpaca max is 1000
                'feed': 'iex',
                'adjustment': 'split'  # Adjust for splits
            }
            
            # Calculate start date
            if end_date:
                params['end'] = end_date.strftime('%Y-%m-%d')
                start_date = end_date - timedelta(days=limit * 2)
                params['start'] = start_date.strftime('%Y-%m-%d')
            else:
                start_date = datetime.now() - timedelta(days=limit * 2)
                params['start'] = start_date.strftime('%Y-%m-%d')
            
            url = f"{self.data_url}/stocks/{symbol}/bars"
            
            response = self.session.get(
                url,
                params=params,
                headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret}
            )
            
            if response.status_code == 200:
                data = response.json()
                bars = data.get('bars', [])
                
                if bars and len(bars) > 10:
                    df = pd.DataFrame(bars)
                    df['t'] = pd.to_datetime(df['t'])
                    df = df.rename(columns={
                        't': 'timestamp',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume',
                        'vw': 'vwap'
                    })
                    df.set_index('timestamp', inplace=True)
                    
                    return df
                else:
                    # Insufficient data, fall back to yfinance
                    logger.info(f"Alpaca returned only {len(bars)} bars, using yfinance")
                    return self._get_yfinance_data(symbol, timeframe, limit, end_date)
            else:
                logger.warning(f"Alpaca error {response.status_code}, using yfinance fallback")
                return self._get_yfinance_data(symbol, timeframe, limit, end_date)
                
        except Exception as e:
            logger.error(f"Alpaca failed for {symbol}: {e}, using yfinance fallback")
            return self._get_yfinance_data(symbol, timeframe, limit, end_date)
    
    def get_2h_candles(self, symbol: str, lookback_days: int = 30) -> pd.DataFrame:
        """Get 2-hour candles by resampling 1-hour data from yfinance.
        
        Note: Alpaca free tier has very limited intraday data.
        We use yfinance 1h data and resample to 2h for proper backtesting.
        """
        logger.info(f"Fetching 2H data for {symbol} ({lookback_days} days)")
        
        # Use yfinance directly for 1-hour data (max 60 days for 1h)
        max_1h_days = min(lookback_days, 60)  # yfinance limits 1h data to ~60 days
        
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            
            # For longer periods, we need to use daily data
            if lookback_days > 60:
                logger.info(f"Using daily data for {symbol} ({lookback_days} days) - yfinance 1H limit is 60 days")
                df = ticker.history(period=f"{min(lookback_days, 365)}d", interval='1d')
                if not df.empty:
                    logger.info(f"yfinance returned {len(df)} daily bars for {symbol}")
                    # Rename columns
                    df = df.rename(columns={
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    })
                    df['vwap'] = df['close']
                    df.index = df.index.tz_localize(None)
                return df
            
            # Get 1-hour data for shorter periods
            df = ticker.history(period=f"{max_1h_days}d", interval='1h')
            
            if df.empty:
                logger.warning(f"No 1H data for {symbol}, trying daily")
                return self.get_historical_candles(symbol, '1Day', lookback_days)
            
            # Standardize column names
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Remove timezone info for consistency
            df.index = df.index.tz_localize(None)
            
            # Resample to 2-hour candles
            df_2h = df.resample('2h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            df_2h['vwap'] = df_2h['close']  # Simplified VWAP
            
            logger.info(f"yfinance returned {len(df_2h)} 2H bars for {symbol}")
            return df_2h
            
        except Exception as e:
            logger.error(f"Failed to get 2H data for {symbol}: {e}")
            # Fallback to daily
            return self.get_historical_candles(symbol, '1Day', lookback_days)
    
    def _get_yfinance_data(
        self,
        symbol: str,
        timeframe: str = '1Day',
        limit: int = 100,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Fallback to yfinance for historical data."""
        try:
            import yfinance as yf
            
            # Map timeframe to yfinance interval
            interval_map = {
                '1Min': '1m',
                '5Min': '5m',
                '15Min': '15m',
                '1Hour': '1h',
                '1Day': '1d',
                '1Week': '1wk',
                '1Month': '1mo'
            }
            
            yf_interval = interval_map.get(timeframe, '1d')
            
            # Calculate period
            if limit <= 5:
                period = '5d'
            elif limit <= 30:
                period = '1mo'
            elif limit <= 90:
                period = '3mo'
            elif limit <= 180:
                period = '6mo'
            elif limit <= 365:
                period = '1y'
            else:
                period = '2y'
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=yf_interval)
            
            if df.empty:
                logger.warning(f"yfinance returned no data for {symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Add VWAP approximation
            df['vwap'] = df['close']  # Simplified
            
            logger.info(f"yfinance returned {len(df)} bars for {symbol}")
            return df
            
        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"yfinance failed for {symbol}: {e}")
            return pd.DataFrame()
    
    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,  # 'buy' or 'sell'
        order_type: str = 'market',  # 'market', 'limit', 'stop', 'stop_limit'
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = 'day'  # 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'
    ) -> Optional[Dict]:
        """Place a stock order.
        
        Note: Alpaca paper trading has limited hours (9:30 AM - 4:00 PM ET).
        """
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            order_data = {
                'symbol': symbol,
                'qty': qty,
                'side': side.lower(),
                'type': order_type.lower(),
                'time_in_force': time_in_force.lower()
            }
            
            if limit_price and order_type.lower() in ['limit', 'stop_limit']:
                order_data['limit_price'] = str(limit_price)
            
            if stop_price and order_type.lower() in ['stop', 'stop_limit']:
                order_data['stop_price'] = str(stop_price)
            
            response = self.session.post(
                f"{self.base_url}/orders",
                json=order_data
            )
            
            if response.status_code == 200:
                order = response.json()
                logger.info(f"Order placed: {order.get('id')} - {side} {qty} {symbol}")
                return order
            else:
                logger.error(f"Order failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
    
    def get_option_chain(self, symbol: str, expiration_date: Optional[str] = None) -> List[Dict]:
        """Get option chain for a symbol.
        
        Note: Alpaca's options API is newer and may have limited availability.
        """
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            # Alpaca options endpoint
            params = {'underlying_symbol': symbol}
            if expiration_date:
                params['expiration_date'] = expiration_date
            
            response = self.session.get(
                f"{self.data_url}/options/snapshots",
                params=params,
                headers={"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Format response
                options = []
                for snapshot in data.get('snapshots', []):
                    options.append({
                        'symbol': snapshot.get('symbol'),
                        'strike': float(snapshot.get('strike_price', 0)),
                        'expiration': snapshot.get('expiration_date'),
                        'type': 'call' if 'C' in snapshot.get('symbol', '') else 'put',
                        'bid': float(snapshot.get('bid_price', 0)),
                        'ask': float(snapshot.get('ask_price', 0)),
                        'last': float(snapshot.get('close_price', 0)),
                        'volume': int(snapshot.get('volume', 0)),
                        'open_interest': int(snapshot.get('open_interest', 0)),
                    })
                return options
            else:
                logger.warning(f"Could not get option chain: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get option chain for {symbol}: {e}")
            return []
    
    def get_open_orders(self) -> List[Dict]:
        """Get list of open orders."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            response = self.session.get(f"{self.base_url}/orders?status=open")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if not self.authenticated:
            raise RuntimeError("Not authenticated")
        
        try:
            response = self.session.delete(f"{self.base_url}/orders/{order_id}")
            if response.status_code == 200:
                logger.info(f"Order cancelled: {order_id}")
                return True
            else:
                logger.error(f"Failed to cancel order: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def close(self):
        """Close API connection."""
        if self.session:
            self.session.close()
        logger.info("Alpaca client closed")
    
    def _get_instrument_type(self, symbol: str) -> str:
        """Determine instrument type from symbol."""
        # Options symbols contain digits and specific patterns
        if any(char.isdigit() for char in symbol) and len(symbol) > 15:
            return 'Equity Option'
        return 'Equity'


def create_alpaca_client(paper: bool = True) -> AlpacaClient:
    """Factory function to create Alpaca client from config."""
    from config import Config
    
    api_key = Config.ALPACA_API_KEY
    api_secret = Config.ALPACA_API_SECRET
    
    if not api_key or not api_secret:
        raise ValueError("Alpaca API credentials not configured")
    
    return AlpacaClient(api_key, api_secret, paper=paper)
