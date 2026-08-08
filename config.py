"""
config.py
Loads all configuration strictly from environment variables.
Never hardcode secrets in this file.
"""

import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pumpfun-bot")


def _require(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in your .env file (local) or in your host's "
            f"Environment Variables panel (Railway/Render)."
        )
    return value


# --- Telegram ---
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = _require("TELEGRAM_CHANNEL_ID")  # e.g. -1001234567890 or @yourchannel

# --- Monetization ---
TROJAN_AFFILIATE_LINK = os.environ.get(
    "TROJAN_AFFILIATE_LINK", "https://t.me/solana_trojanbot?start=r-yourcode"
)
TRADE_FEE_PERCENT = float(os.environ.get("TRADE_FEE_PERCENT", "1.0"))  # 1% default

# --- Database ---
# If DATABASE_URL is set and starts with postgres(ql)://, we use Postgres
# (e.g. free Supabase project). Otherwise we fall back to a local SQLite file.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH = os.environ.get("SQLITE_PATH", "pumpfun_bot.db")

# --- Solana Tracker Data API (stable, documented replacement for pump.fun's
# own increasingly locked-down internal API) ---
SOLANA_TRACKER_API_KEY = _require("SOLANA_TRACKER_API_KEY")
SOLANA_TRACKER_API_BASE = os.environ.get(
    "SOLANA_TRACKER_API_BASE", "https://data.solanatracker.io"
)

# --- Scan behaviour ---
# The Solana Tracker free tier allows 2,500 requests/month. At 1 request per
# scan, staying under that budget needs an interval of at least ~18 minutes
# (2500 / 30 days ≈ 83/day ≈ 1 every 17.3 min). Default is set with margin;
# lower it only if you're on a paid plan or accept possible overage.
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "1200"))  # 20 min
TOP_N_TOKENS = int(os.environ.get("TOP_N_TOKENS", "3"))
