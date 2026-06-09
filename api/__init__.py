"""API module for broker integration.

Supports Alpaca (primary) and TastyTrade (legacy).
"""
from .tastytrade_client import TastyTradeClient
from .alpaca_client import AlpacaClient, create_alpaca_client

__all__ = ['TastyTradeClient', 'AlpacaClient', 'create_alpaca_client', 'get_client']


def get_client():
    """Factory function to get the appropriate API client based on config.
    
    Returns:
        AlpacaClient or TastyTradeClient based on BROKER_API setting
    """
    from config import Config, BrokerAPI
    
    if Config.BROKER_API == BrokerAPI.ALPACA:
        creds = Config.get_alpaca_credentials()
        client = AlpacaClient(
            api_key=creds['api_key'],
            api_secret=creds['api_secret'],
            paper=creds['paper']
        )
        return client
    else:
        creds = Config.get_credentials()
        return TastyTradeClient(creds['username'], creds['password'])
