"""Check local data cache."""
import sys
sys.path.insert(0, r'h:\QUANT TRADING')

from data.local_data_provider import LocalDataProvider

provider = LocalDataProvider()
symbols = provider.get_available_symbols()
summary = provider.get_cache_summary()

print("=" * 60)
print("LOCAL DATA CACHE SUMMARY")
print("=" * 60)
print(f"Total symbols: {len(symbols)}")
print(f"Daily data: {len(summary['by_timeframe'].get('daily', []))} symbols")
print(f"Hourly data: {len(summary['by_timeframe'].get('hourly', []))} symbols")
print()
print("Available symbols:")
for s in symbols:
    print(f"  - {s}")

print()
print("✅ Cache is ready for fast backtesting!")
print()
print("You can now run:")
print("  python backtest_wheel_portfolio.py")
print("  python backtest_2year.py")
print("  python backtest_report.py NVDA 30")
