"""
Notification system — logs to file + Discord webhook + optional email.

To enable Discord alerts:
  Set in .env:
    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy

To enable email alerts (optional, Discord preferred):
  Set in .env:
    NOTIFY_EMAIL=your_email@gmail.com
    NOTIFY_EMAIL_PASSWORD=your_gmail_app_password
    NOTIFY_TO=your_email@gmail.com
"""
import os
import smtplib
import logging
import requests
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from config import LOG_DIR, ENV_FILE

logger = logging.getLogger(__name__)


def _load_notify_config():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_notify_config()


def setup_logging(run_name: str = "autotrader"):
    """Set up file + console logging."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{run_name}_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ]
    )
    logger.info(f"Logging to {log_file}")
    return log_file


def notify(subject: str, body: str):
    """Log notification, send Discord message, and optionally send email."""
    logger.info(f"NOTIFY: {subject}\n{body}")
    _try_send_discord(subject, body)
    _try_send_email(subject, body)


def notify_entry(signal: dict):
    subject = f"[AutoTrader] ENTRY: {signal['symbol']} {signal['occ_symbol']}"
    body = (
        f"Phase entry signal executed.\n\n"
        f"Symbol:      {signal['symbol']}\n"
        f"OCC:         {signal['occ_symbol']}\n"
        f"Strike:      ${signal['strike']:.2f}\n"
        f"Expiry:      {signal['exp_date']}\n"
        f"Entry price: ${signal['mid']:.2f}\n"
        f"Total cost:  ${signal['cost']:.2f}\n"
        f"Stock stop:  ${signal['stop_price']:.2f}\n"
        f"Time stop:   {signal['time_stop']} trading days\n"
    )
    notify(subject, body)


def notify_exit(occ_symbol: str, entry_prem: float, exit_prem: float, reason: str):
    pnl = (exit_prem - entry_prem) * 100
    result = "WIN" if pnl > 0 else "LOSS"
    subject = f"[AutoTrader] EXIT {result}: {occ_symbol}  PnL=${pnl:+.2f}"
    body = (
        f"Position closed.\n\n"
        f"OCC:         {occ_symbol}\n"
        f"Entry:       ${entry_prem:.2f}\n"
        f"Exit:        ${exit_prem:.2f}\n"
        f"PnL:         ${pnl:+.2f}\n"
        f"Reason:      {reason}\n"
    )
    notify(subject, body)


def notify_phase_change(old_phase: int, new_phase: int, balance: float):
    subject = f"[AutoTrader] PHASE CHANGE: Phase {old_phase} → Phase {new_phase}"
    body = (
        f"Account has grown to a new phase!\n\n"
        f"From Phase:  {old_phase}\n"
        f"To Phase:    {new_phase}\n"
        f"Balance:     ${balance:,.2f}\n"
    )
    notify(subject, body)


def _try_send_discord(subject: str, body: str, color: int = None):
    """Send a Discord embed message via webhook."""
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return

    # Auto-pick color from subject keywords
    if color is None:
        low = subject.lower()
        if "entry" in low or "phase change" in low:
            color = 0x00b4d8   # blue
        elif "win" in low or "profit" in low:
            color = 0x2ecc71   # green
        elif "loss" in low or "stop" in low:
            color = 0xe74c3c   # red
        elif "no signal" in low:
            color = 0x95a5a6   # grey
        else:
            color = 0xf39c12   # orange

    payload = {
        "embeds": [{
            "title":       subject,
            "description": f"```\n{body}\n```",
            "color":       color,
            "footer":      {"text": "AutoTrader | Tastytrade"},
            "timestamp":   datetime.utcnow().isoformat(),
        }]
    }

    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code not in (200, 204):
            logger.warning(f"Discord webhook returned {resp.status_code}: {resp.text}")
        else:
            logger.debug("Discord notification sent")
    except Exception as e:
        logger.warning(f"Discord notification failed (non-critical): {e}")


def _try_send_email(subject: str, body: str):
    from_addr = os.getenv("NOTIFY_EMAIL")
    password  = os.getenv("NOTIFY_EMAIL_PASSWORD")
    to_addr   = os.getenv("NOTIFY_TO")

    if not all([from_addr, password, to_addr]):
        return  # Email not configured — skip silently

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(from_addr, password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        logger.info(f"Email sent to {to_addr}")
    except Exception as e:
        logger.warning(f"Email failed (non-critical): {e}")
