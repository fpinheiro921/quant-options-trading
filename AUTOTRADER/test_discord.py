"""Quick test — sends a sample message to your Discord channel."""
import os, sys
from pathlib import Path

env_file = Path(r'H:\QUANT TRADING\STRATEGY_COMBINATIONS\.env')
for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(Path(__file__).parent))
from notifier import _try_send_discord

_try_send_discord(
    subject="[AutoTrader] Test — Connection OK",
    body=(
        "AutoTrader Discord notifications are working!\n\n"
        "You will receive alerts for:\n"
        "  ENTRY  — when a trade is placed\n"
        "  EXIT   — when a trade closes (WIN/LOSS + PnL)\n"
        "  PHASE  — when account grows to next phase\n"
        "  SCAN   — Monday scan results (signal or no signal)\n"
    ),
    color=0x2ecc71
)
print("Test message sent. Check your Discord channel.")
