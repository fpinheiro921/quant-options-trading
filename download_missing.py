"""Download missing symbols for portfolio momentum backtest."""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from scripts.download_portfolio_data import download_portfolio

MISSING_SYMBOLS = [
    'SQ', 'SHOP', 'UPST', 'SOFI', 'LCID', 'RIVN', 'GME', 'AMC', 'MRNA', 'ARKK', 'TQQQ', 'NET',
    'MCD', 'TGT', 'COST', 'LOW', 'T', 'BMY', 'ABBV', 'BLK', 'CAT', 'GE', 'LIN', 'AMT',
    'AVAV', 'DKNG', 'HOOD', 'AFRM', 'TOST', 'BILL', 'ASAN', 'MDB', 'TWLO',
    'OKTA', 'ZI', 'HUBS', 'FSLY', 'ESTC', 'SPLK', 'DOCU', 'PD', 'S', 'CYBR', 'BRK-B'
]

print(f"Downloading {len(MISSING_SYMBOLS)} missing symbols...")
print("Symbols:", ', '.join(MISSING_SYMBOLS))
print()

download_portfolio(MISSING_SYMBOLS, years=3)
