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

# --- Scan behaviour ---
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "300"))  # 5 minutes
TOP_N_TOKENS = int(os.environ.get("TOP_N_TOKENS", "3"))

# --- pump.fun public frontend API ---
# NOTE: this is pump.fun's public (unofficial, undocumented) frontend API.
# It can change without notice - if the bot stops finding tokens, check
# whether the response shape/endpoint has changed and adjust pumpfun_api.py.
PUMPFUN_API_BASE = os.environ.get("PUMPFUN_API_BASE", "https://frontend-api.pump.fun")
