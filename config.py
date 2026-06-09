"""
Configuration module for the Quant Options Trading System.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class TradingMode:
    """Trading mode constants."""
    PAPER = 'paper'      # Paper trading simulation
    LIVE = 'live'        # Real money trading


class BrokerAPI:
    """Broker API selection constants."""
    ALPACA = 'alpaca'
    TASTYTRADE = 'tastytrade'


class Config:
    """Application configuration."""
    
    # Trading Mode - CRITICAL: Set to 'paper' for backtesting until ready
    TRADING_MODE = os.getenv('TRADING_MODE', TradingMode.PAPER)
    
    # Broker API Selection
    BROKER_API = os.getenv('BROKER_API', BrokerAPI.ALPACA)
    
    # ==========================================
    # ALPACA API CONFIGURATION (PRIMARY)
    # ==========================================
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_API_SECRET = os.getenv('ALPACA_API_SECRET')
    ALPACA_PAPER = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
    
    # Live trading keys (separate from paper)
    ALPACA_LIVE_API_KEY = os.getenv('ALPACA_LIVE_API_KEY')
    ALPACA_LIVE_API_SECRET = os.getenv('ALPACA_LIVE_API_SECRET')
    
    @staticmethod
    def get_alpaca_credentials():
        """Get Alpaca API credentials based on trading mode."""
        if Config.TRADING_MODE == TradingMode.LIVE:
            return {
                'api_key': Config.ALPACA_LIVE_API_KEY or Config.ALPACA_API_KEY,
                'api_secret': Config.ALPACA_LIVE_API_SECRET or Config.ALPACA_API_SECRET,
                'paper': False
            }
        else:
            return {
                'api_key': Config.ALPACA_API_KEY,
                'api_secret': Config.ALPACA_API_SECRET,
                'paper': True
            }
    
    # TastyTrade API - Credentials based on mode
    @staticmethod
    def get_credentials():
        """Get credentials based on trading mode."""
        mode = Config.TRADING_MODE
        if mode == TradingMode.SANDBOX:
            return {
                'username': os.getenv('TASTYTRADE_SANDBOX_USERNAME') or os.getenv('TASTYTRADE_USERNAME'),
                'password': os.getenv('TASTYTRADE_SANDBOX_PASSWORD') or os.getenv('TASTYTRADE_PASSWORD'),
                'account_id': os.getenv('TASTYTRADE_SANDBOX_ACCOUNT_ID') or os.getenv('TASTYTRADE_ACCOUNT_ID')
            }
        else:
            return {
                'username': os.getenv('TASTYTRADE_USERNAME'),
                'password': os.getenv('TASTYTRADE_PASSWORD'),
                'account_id': os.getenv('TASTYTRADE_ACCOUNT_ID')
            }
    
    @staticmethod
    def get_api_url():
        """Get API URL based on trading mode."""
        mode = Config.TRADING_MODE
        # Use tastyworks.com (not tastytrade.com) per official API docs
        if mode == TradingMode.SANDBOX:
            return os.getenv('TASTYTRADE_SANDBOX_URL', 'https://api.cert.tastyworks.com')
        return os.getenv('TASTYTRADE_API_URL', 'https://api.tastyworks.com')
    
    @staticmethod
    def get_user_agent():
        """Get User-Agent header (required by TastyTrade API)."""
        return os.getenv('API_USER_AGENT', 'QuantOptionsBot/1.0')
    
    # Legacy direct access (for backward compatibility)
    TASTYTRADE_USERNAME = os.getenv('TASTYTRADE_USERNAME')
    TASTYTRADE_PASSWORD = os.getenv('TASTYTRADE_PASSWORD')
    TASTYTRADE_ACCOUNT_ID = os.getenv('TASTYTRADE_ACCOUNT_ID')
    # FIXED: Use tastyworks.com per official API documentation
    TASTYTRADE_API_URL = os.getenv('TASTYTRADE_API_URL', 'https://api.tastyworks.com')
    TASTYTRADE_SANDBOX_URL = os.getenv('TASTYTRADE_SANDBOX_URL', 'https://api.cert.tastyworks.com')
    TASTYTRADE_DXFEED_URL = os.getenv('TASTYTRADE_DXFEED_URL', 'wss://tasty-open-api-ws.dxfeed.com/realtime')
    API_USER_AGENT = os.getenv('API_USER_AGENT', 'QuantOptionsBot/1.0')
    
    # Paper Trading Settings (for local simulation mode)
    PAPER_STARTING_BALANCE = float(os.getenv('PAPER_STARTING_BALANCE', '100000.0'))
    PAPER_SAVE_FILE = os.getenv('PAPER_SAVE_FILE', 'paper_account.pkl')
    
    # Trading Parameters
    DEFAULT_DELTA_THRESHOLD = float(os.getenv('DEFAULT_DELTA_THRESHOLD', '0.30'))
    MIN_PREMIUM_THRESHOLD = float(os.getenv('MIN_PREMIUM_THRESHOLD', '0.50'))
    MAX_POSITION_PCT = float(os.getenv('MAX_POSITION_PCT', '0.20'))
    RISK_FREE_RATE = float(os.getenv('RISK_FREE_RATE', '0.045'))
    
    # Option Chain Parameters
    STRIKE_RANGE_PCT = 0.20  # +/- 20% from spot for strike search
    MAX_MATURITIES = 5
    MIN_VOLUME = 10
    
    # UI Parameters
    CHART_RANGE_PCT = 0.20
    REFRESH_INTERVAL = 1000  # milliseconds
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class TradingConfig:
    """Trading strategy configuration."""
    
    # Wheel Strategy Parameters
    TARGET_DELTA_CALL = 0.30  # Delta for covered calls
    TARGET_DELTA_PUT = 0.30   # Delta for cash-secured puts
    DEFAULT_DTE = 7  # Days to expiration
    MIN_DTE = 0
    MAX_DTE = 45
    
    # Position Management
    LOT_SIZE = 100  # Shares per option contract
    MAX_LOTS_PER_SYMBOL = 5
    
    # Assignment Handling
    AUTO_ROLL = True  # Auto-roll positions on assignment
    ROLL_DAYS_BEFORE_EXPIRY = 1
