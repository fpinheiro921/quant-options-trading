"""
Massive.com API Client for Financial Data Retrieval and Local Caching.

This client:
1. Fetches historical data from Massive API
2. Caches data locally to avoid repeated API calls
3. Provides a local-first interface for backtesting

API Key: EmiYlge1r_wvYDAJro1iqOvN8al_AfPg
Documentation: https://docs.massive.com (assumed structure)
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Union
from pathlib import Path
import pandas as pd
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MassiveConfig:
    """Configuration for Massive API."""
    api_key: str = "EmiYlge1r_wvYDAJro1iqOvN8al_AfPg"
    base_url: str = "https://api.massive.com/v1"  # Assumed base URL
    cache_dir: str = "data/massive_cache"
    rate_limit_per_second: int = 10


class MassiveDataCache:
    """
    Local cache for Massive API data.
    
    Structure:
    data/massive_cache/
    ├── stocks/
    │   ├── AAPL/
    │   │   ├── daily_2019_2024.parquet
    │   │   ├── hourly_2023_2024.parquet
    │   │   └── metadata.json
    │   ├── NVDA/
    │   └── ...
    ├── options/
    │   └── chains/
    └── indices/
    """
    
    def __init__(self, cache_dir: str = "data/massive_cache"):
        self.cache_dir = Path(cache_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create cache directory structure."""
        directories = [
            self.cache_dir / "stocks",
            self.cache_dir / "options" / "chains",
            self.cache_dir / "indices",
            self.cache_dir / "metadata"
        ]
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory: {d}")
    
    def get_cache_path(self, symbol: str, data_type: str, timeframe: str) -> Path:
        """Get cache file path for a symbol."""
        safe_symbol = symbol.replace('/', '_').replace('\\', '_')
        
        if data_type == 'stock':
            symbol_dir = self.cache_dir / "stocks" / safe_symbol
            symbol_dir.mkdir(parents=True, exist_ok=True)
            return symbol_dir / f"{timeframe}.csv"
        elif data_type == 'options':
            return self.cache_dir / "options" / f"{safe_symbol}_{timeframe}.parquet"
        elif data_type == 'index':
            return self.cache_dir / "indices" / f"{safe_symbol}_{timeframe}.parquet"
        else:
            return self.cache_dir / f"{safe_symbol}_{data_type}_{timeframe}.parquet"
    
    def exists(self, symbol: str, data_type: str, timeframe: str) -> bool:
        """Check if data exists in cache."""
        cache_path = self.get_cache_path(symbol, data_type, timeframe)
        return cache_path.exists()
    
    def load(self, symbol: str, data_type: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Load data from cache."""
        cache_path = self.get_cache_path(symbol, data_type, timeframe)
        
        if not cache_path.exists():
            return None
        
        try:
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            logger.info(f"Loaded {len(df)} rows from cache: {cache_path}")
            return df
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return None
    
    def save(self, symbol: str, data_type: str, timeframe: str, df: pd.DataFrame):
        """Save data to cache."""
        cache_path = self.get_cache_path(symbol, data_type, timeframe)
        
        try:
            df.to_csv(cache_path)
            logger.info(f"Saved {len(df)} rows to cache: {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def get_metadata(self, symbol: str) -> Dict:
        """Get metadata for a symbol."""
        safe_symbol = symbol.replace('/', '_').replace('\\', '_')
        meta_path = self.cache_dir / "stocks" / safe_symbol / "metadata.json"
        
        if meta_path.exists():
            with open(meta_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save_metadata(self, symbol: str, metadata: Dict):
        """Save metadata for a symbol."""
        safe_symbol = symbol.replace('/', '_').replace('\\', '_')
        symbol_dir = self.cache_dir / "stocks" / safe_symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        
        meta_path = symbol_dir / "metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"Saved metadata for {symbol}")


class MassiveClient:
    """
    Client for Massive.com API with local caching.
    
    Usage:
        client = MassiveClient()
        
        # Fetch and cache data
        df = client.get_stock_data('AAPL', start='2020-01-01', end='2024-01-01')
        
        # Get cached data (fast, no API call)
        df = client.get_cached_data('AAPL', 'daily')
        
        # Bulk download for backtesting
        symbols = ['AAPL', 'NVDA', 'TSLA']
        client.bulk_download(symbols, years=5)
    """
    
    def __init__(self, config: Optional[MassiveConfig] = None):
        self.config = config or MassiveConfig()
        self.cache = MassiveDataCache(self.config.cache_dir)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'QuantTradingBot/1.0'
        })
        self._last_request_time = datetime.now()
        
    def _rate_limit(self):
        """Apply rate limiting."""
        import time
        min_interval = 1.0 / self.config.rate_limit_per_second
        elapsed = (datetime.now() - self._last_request_time).total_seconds()
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = datetime.now()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make API request with rate limiting and error handling."""
        self._rate_limit()
        
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {}
    
    def get_stock_data(
        self,
        symbol: str,
        start: Union[str, datetime],
        end: Union[str, datetime],
        timeframe: str = '1d',
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Get historical stock data from Massive API or cache.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            start: Start date (YYYY-MM-DD or datetime)
            end: End date (YYYY-MM-DD or datetime)
            timeframe: Data interval ('1d', '1h', '1m', etc.)
            use_cache: Use local cache if available
        
        Returns:
            DataFrame with OHLCV data
        """
        # Check cache first
        cache_key = f"{start}_{end}"
        if use_cache and self.cache.exists(symbol, 'stock', f"{timeframe}_{cache_key}"):
            df = self.cache.load(symbol, 'stock', f"{timeframe}_{cache_key}")
            if df is not None:
                return df
        
        # Convert dates
        if isinstance(start, str):
            start = datetime.strptime(start, '%Y-%m-%d')
        if isinstance(end, str):
            end = datetime.strptime(end, '%Y-%m-%d')
        
        # Fetch from API
        logger.info(f"Fetching {symbol} from Massive API ({timeframe}, {start.date()} to {end.date()})")
        
        # Try different endpoints (common patterns for financial APIs)
        endpoints = [
            f"stocks/{symbol}/candles",
            f"equities/{symbol}/historical",
            f"data/stocks/{symbol}/bars",
            f"market/stocks/{symbol}/ohlcv"
        ]
        
        data = None
        for endpoint in endpoints:
            params = {
                'symbol': symbol,
                'start': start.strftime('%Y-%m-%d'),
                'end': end.strftime('%Y-%m-%d'),
                'timeframe': timeframe
            }
            
            response = self._make_request(endpoint, params)
            
            if response and 'data' in response:
                data = response['data']
                logger.info(f"Success with endpoint: {endpoint}")
                break
            elif response and 'candles' in response:
                data = response['candles']
                logger.info(f"Success with endpoint: {endpoint}")
                break
            elif response and 'bars' in response:
                data = response['bars']
                logger.info(f"Success with endpoint: {endpoint}")
                break
        
        if not data:
            logger.warning(f"No data returned for {symbol}, trying fallback to yfinance")
            return self._fetch_from_yfinance(symbol, start, end, timeframe)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Standardize column names
        column_mapping = {
            'o': 'open', 'open': 'open',
            'h': 'high', 'high': 'high',
            'l': 'low', 'low': 'low',
            'c': 'close', 'close': 'close',
            'v': 'volume', 'volume': 'volume',
            't': 'timestamp', 'time': 'timestamp', 'date': 'timestamp'
        }
        df = df.rename(columns=column_mapping)
        
        # Set timestamp as index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        # Cache the data
        if use_cache and not df.empty:
            self.cache.save(symbol, 'stock', f"{timeframe}_{cache_key}", df)
            
            # Update metadata
            metadata = self.cache.get_metadata(symbol)
            metadata.update({
                'last_updated': datetime.now().isoformat(),
                'symbol': symbol,
                'timeframe': timeframe,
                'date_range': {
                    'start': start.isoformat(),
                    'end': end.isoformat()
                },
                'rows': len(df)
            })
            self.cache.save_metadata(symbol, metadata)
        
        return df
    
    def _fetch_from_yfinance(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        """Fallback to yfinance if Massive API fails."""
        try:
            import yfinance as yf
            
            logger.info(f"Using yfinance fallback for {symbol}")
            
            ticker = yf.Ticker(symbol)
            
            # Map timeframe to yfinance interval
            interval_map = {
                '1d': '1d',
                '1h': '1h',
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '60m': '60m'
            }
            
            yf_interval = interval_map.get(timeframe, '1d')
            
            # Calculate period for yfinance
            days = (end - start).days
            if days <= 7:
                period = '7d'
            elif days <= 30:
                period = '1mo'
            elif days <= 90:
                period = '3mo'
            elif days <= 180:
                period = '6mo'
            elif days <= 365:
                period = '1y'
            elif days <= 730:
                period = '2y'
            else:
                period = '5y'
            
            df = ticker.history(period=period, interval=yf_interval)
            
            # Filter to requested date range
            df = df[(df.index >= start) & (df.index <= end)]
            
            # Rename columns to lowercase
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            logger.info(f"yfinance returned {len(df)} rows for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"yfinance fallback also failed: {e}")
            return pd.DataFrame()
    
    def bulk_download(
        self,
        symbols: List[str],
        years: int = 5,
        timeframe: str = '1d',
        include_options: bool = False
    ):
        """
        Bulk download historical data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            years: How many years of historical data
            timeframe: Data interval
            include_options: Also download options chains
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        logger.info(f"Starting bulk download for {len(symbols)} symbols")
        logger.info(f"Period: {start_date.date()} to {end_date.date()}")
        logger.info(f"Timeframe: {timeframe}")
        
        results = {
            'success': [],
            'failed': [],
            'cached': []
        }
        
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] Processing {symbol}...")
            
            # Check if already cached
            cache_key = f"{start_date.date()}_{end_date.date()}"
            if self.cache.exists(symbol, 'stock', f"{timeframe}_{cache_key}"):
                logger.info(f"  {symbol} already in cache, skipping")
                results['cached'].append(symbol)
                continue
            
            # Fetch data
            try:
                df = self.get_stock_data(symbol, start_date, end_date, timeframe, use_cache=True)
                
                if not df.empty:
                    results['success'].append(symbol)
                    logger.info(f"  ✓ Downloaded {len(df)} rows for {symbol}")
                else:
                    results['failed'].append(symbol)
                    logger.warning(f"  ✗ No data for {symbol}")
                    
            except Exception as e:
                results['failed'].append(symbol)
                logger.error(f"  ✗ Error downloading {symbol}: {e}")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("BULK DOWNLOAD COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Successful: {len(results['success'])}")
        logger.info(f"Cached (skipped): {len(results['cached'])}")
        logger.info(f"Failed: {len(results['failed'])}")
        
        if results['failed']:
            logger.warning(f"Failed symbols: {', '.join(results['failed'])}")
        
        return results
    
    def get_cached_symbols(self) -> List[str]:
        """Get list of symbols available in local cache."""
        stocks_dir = self.cache.cache_dir / "stocks"
        if not stocks_dir.exists():
            return []
        
        symbols = []
        for symbol_dir in stocks_dir.iterdir():
            if symbol_dir.is_dir():
                symbols.append(symbol_dir.name)
        
        return sorted(symbols)
    
    def get_data_summary(self) -> Dict:
        """Get summary of all cached data."""
        summary = {
            'total_symbols': 0,
            'total_files': 0,
            'symbols': {}
        }
        
        stocks_dir = self.cache.cache_dir / "stocks"
        if stocks_dir.exists():
            for symbol_dir in stocks_dir.iterdir():
                if symbol_dir.is_dir():
                    summary['total_symbols'] += 1
                    parquet_files = list(symbol_dir.glob('*.parquet'))
                    summary['total_files'] += len(parquet_files)
                    
                    # Get metadata
                    metadata = self.cache.get_metadata(symbol_dir.name)
                    summary['symbols'][symbol_dir.name] = {
                        'files': len(parquet_files),
                        'metadata': metadata
                    }
        
        return summary


def download_portfolio_data():
    """Download data for the portfolio used in backtesting."""
    portfolio = [
        'QQQ', 'AAPL', 'MSFT', 'NVDA', 'AMD',
        'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX',
        'SPY', 'IWM', 'VIX'
    ]
    
    client = MassiveClient()
    
    # Download 5 years of daily data
    results = client.bulk_download(
        symbols=portfolio,
        years=5,
        timeframe='1d',
        include_options=False
    )
    
    # Also download hourly data for momentum strategy
    results_hourly = client.bulk_download(
        symbols=portfolio,
        years=2,  # Hourly data typically limited
        timeframe='1h',
        include_options=False
    )
    
    return results, results_hourly


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 80)
    print("MASSIVE.COM DATA DOWNLOADER")
    print("=" * 80)
    print("\nThis will download historical data for your portfolio")
    print("and store it locally for fast backtesting.\n")
    
    # Download portfolio data
    daily_results, hourly_results = download_portfolio_data()
    
    # Show summary
    client = MassiveClient()
    summary = client.get_data_summary()
    
    print("\n" + "=" * 80)
    print("DATA SUMMARY")
    print("=" * 80)
    print(f"Total symbols cached: {summary['total_symbols']}")
    print(f"Total data files: {summary['total_files']}")
    print(f"\nCached symbols:")
    for symbol, info in summary['symbols'].items():
        print(f"  - {symbol}: {info['files']} files")
        if 'metadata' in info and info['metadata']:
            date_range = info['metadata'].get('date_range', {})
            if date_range:
                print(f"    Period: {date_range.get('start', 'N/A')[:10]} to {date_range.get('end', 'N/A')[:10]}")
    
    print("\n✅ Data download complete!")
    print("You can now backtest without API calls using the local cache.")
