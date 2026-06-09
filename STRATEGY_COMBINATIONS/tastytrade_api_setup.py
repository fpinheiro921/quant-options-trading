"""
Tastytrade API Integration
Uses OAuth2 credentials for automated trading
"""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TastytradeClient:
    """
    Tastytrade API client using OAuth2.
    
    To use:
    1. Get credentials from Tastytrade Developer Portal
    2. Set environment variables or pass directly
    3. Call authenticate() before trading
    """
    
    BASE_URL = "https://api.tastytrade.com"
    
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        """
        Initialize Tastytrade client.
        
        Args:
            client_id: OAuth2 client ID from Tastytrade
            client_secret: OAuth2 client secret from Tastytrade
            redirect_uri: Registered redirect URI
        """
        self.client_id = client_id or os.getenv('TASTYTRADE_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('TASTYTRADE_CLIENT_SECRET')
        self.redirect_uri = redirect_uri or os.getenv('TASTYTRADE_REDIRECT_URI', 'http://localhost:3000/callback')
        
        self.access_token = None
        self.refresh_token = None
        self.account_number = None
        self.session_token = None
        
    def authenticate(self):
        """
        Authenticate with Tastytrade OAuth2.
        
        NOTE: This is a simplified flow. Full OAuth2 requires:
        1. Redirect user to authorization URL
        2. User logs in and authorizes
        3. Tastytrade redirects to your URI with code
        4. Exchange code for access token
        
        For automated trading, you may need to:
        - Use device code flow, or
        - Store and refresh tokens, or
        - Use API key if available
        """
        logger.info("Authenticating with Tastytrade...")
        
        # Check if we have stored tokens
        token_file = Path.home() / '.tastytrade_tokens.json'
        if token_file.exists():
            with open(token_file, 'r') as f:
                tokens = json.load(f)
                self.access_token = tokens.get('access_token')
                self.refresh_token = tokens.get('refresh_token')
                
            if self.refresh_token:
                logger.info("Found existing tokens, attempting refresh...")
                return self._refresh_token()
        
        # If no stored tokens, need to do OAuth2 flow
        logger.info("No stored tokens found. Starting OAuth2 flow...")
        logger.info("Please visit the authorization URL and grant access.")
        
        auth_url = f"{self.BASE_URL}/oauth2/authorize"
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'trade read'
        }
        
        logger.info(f"Authorization URL: {auth_url}")
        logger.info(f"Params: {params}")
        
        # In practice, you would:
        # 1. Open browser with this URL
        # 2. User logs in and authorizes
        # 3. Catch the redirect with the code
        # 4. Exchange code for tokens
        
        return False
    
    def _refresh_token(self):
        """Refresh access token using refresh token."""
        try:
            response = requests.post(
                f"{self.BASE_URL}/oauth2/token",
                data={
                    'grant_type': 'refresh_token',
                    'refresh_token': self.refresh_token,
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
            )
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens['access_token']
                self.refresh_token = tokens.get('refresh_token', self.refresh_token)
                
                # Save tokens
                self._save_tokens()
                
                logger.info("Token refreshed successfully!")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
    
    def _save_tokens(self):
        """Save tokens to file for reuse."""
        token_file = Path.home() / '.tastytrade_tokens.json'
        with open(token_file, 'w') as f:
            json.dump({
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'timestamp': datetime.now().isoformat()
            }, f)
    
    def get_accounts(self):
        """Get list of accounts."""
        if not self.access_token:
            logger.error("Not authenticated")
            return []
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/accounts",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            
            if response.status_code == 200:
                accounts = response.json().get('data', [])
                logger.info(f"Found {len(accounts)} accounts")
                return accounts
            else:
                logger.error(f"Failed to get accounts: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []
    
    def get_account_balance(self, account_number=None):
        """Get account balance."""
        account = account_number or self.account_number
        if not account:
            logger.error("No account number set")
            return None
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/accounts/{account}/balances",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            
            if response.status_code == 200:
                balance = response.json().get('data', {})
                logger.info(f"Account balance: ${balance.get('cash-available-to-withdraw', 0)}")
                return balance
            else:
                logger.error(f"Failed to get balance: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
    
    def get_option_chain(self, symbol):
        """Get option chain for a symbol."""
        if not self.access_token:
            logger.error("Not authenticated")
            return None
        
        try:
            # Get expiration dates first
            response = requests.get(
                f"{self.BASE_URL}/option-chains/{symbol}/nested",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            
            if response.status_code == 200:
                chain = response.json().get('data', {})
                return chain
            else:
                logger.error(f"Failed to get option chain: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting option chain: {e}")
            return None
    
    def place_order(self, order_spec, account_number=None):
        """
        Place an order.
        
        Args:
            order_spec: Dictionary with order details
                {
                    'symbol': 'SNAP',
                    'strike': 16.5,
                    'expiration': '2026-06-19',
                    'option_type': 'Call',
                    'quantity': 1,
                    'action': 'Buy to Open',
                    'price': 'Market'  # or limit price
                }
        """
        account = account_number or self.account_number
        if not account:
            logger.error("No account number set")
            return False
        
        try:
            # Build order payload (simplified)
            payload = {
                'source': 'tastytrade-api',
                'order-type': 'Market',  # or 'Limit'
                'price': order_spec.get('price', ''),
                'time-in-force': 'Day',
                'legs': [{
                    'instrument-type': 'Equity Option',
                    'symbol': f"{order_spec['symbol']} {order_spec['expiration']} {order_spec['option_type']} {order_spec['strike']}",
                    'quantity': order_spec['quantity'],
                    'action': order_spec['action']
                }]
            }
            
            response = requests.post(
                f"{self.BASE_URL}/accounts/{account}/orders",
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                },
                json=payload
            )
            
            if response.status_code == 201:
                order = response.json()
                logger.info(f"Order placed successfully: {order}")
                return True
            else:
                logger.error(f"Failed to place order: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return False
    
    def preview_order(self, order_spec, account_number=None):
        """Preview an order without placing it (for verification)."""
        account = account_number or self.account_number
        if not account:
            logger.error("No account number set")
            return False
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/accounts/{account}/orders/preview",
                headers={
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                },
                json=order_spec
            )
            
            if response.status_code == 200:
                preview = response.json()
                logger.info(f"Order preview: {preview}")
                return preview
            else:
                logger.error(f"Preview failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error previewing order: {e}")
            return None


def calculate_otm_strike(stock_price, otm_percent=0.10):
    """Calculate 10% OTM strike price."""
    strike = stock_price * (1 + otm_percent)
    
    # Round to nearest available strike increment
    if stock_price < 25:
        # $0.50 or $1 increments
        strike = round(strike * 2) / 2
    else:
        # $1 or $2.50 increments
        strike = round(strike)
    
    return strike


def main():
    """Example usage of Tastytrade client."""
    logger.info("="*60)
    logger.info("TASTYTRADE API SETUP")
    logger.info("="*60)
    
    # Initialize client
    client = TastytradeClient()
    
    # Check credentials
    if not client.client_id or not client.client_secret:
        logger.error("Missing credentials!")
        logger.error("Set environment variables:")
        logger.error("  TASTYTRADE_CLIENT_ID")
        logger.error("  TASTYTRADE_CLIENT_SECRET")
        return
    
    logger.info("Client initialized with credentials")
    logger.info(f"Client ID: {client.client_id[:10]}...")
    
    # Authenticate
    if client.authenticate():
        logger.info("Authentication successful!")
        
        # Get accounts
        accounts = client.get_accounts()
        if accounts:
            client.account_number = accounts[0]['account-number']
            logger.info(f"Using account: {client.account_number}")
            
            # Get balance
            client.get_account_balance()
    else:
        logger.info("Please complete OAuth2 flow manually:")
        logger.info("1. Visit the authorization URL above")
        logger.info("2. Log in and authorize")
        logger.info("3. Copy the authorization code")
        logger.info("4. Run exchange_code_for_token(code)")


if __name__ == "__main__":
    main()
