"""
bot.py

Main entrypoint. Polls pump.fun every SCAN_INTERVAL_SECONDS, ranks new
tokens, posts the top N to the Telegram channel (skipping duplicates via
the persistent database), and exposes /buy and /sell commands that run
the simulated 1%-fee trade flow.

Run: python bot.py
"""

from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    SCAN_INTERVAL_SECONDS,
    TOP_N_TOKENS,
    logger,
)
from database import db
from pumpfun_api import fetch_latest_tokens
from formatter import build_signal_message
from trading import simulate_trade, format_trade_confirmation


# ----------------------------------------------------------------------
# Core scan job
# ----------------------------------------------------------------------

async def scan_and_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runs every SCAN_INTERVAL_SECONDS. Fetches, ranks, dedupes, posts."""
    logger.info("Running scan cycle...")

    tokens = await fetch_latest_tokens(limit=50)
    if not tokens:
        logger.info("No tokens returned this cycle.")
        return

    # Filter out noise: require some minimal signs of real activity so we
    # don't post tokens with literally zero trading behind them.
    active_tokens = [t for t in tokens if t["market_cap_usd"] > 0]

    # Rank by volume first, market cap as tiebreaker/fallback.
    ranked = sorted(
        active_tokens,
        key=lambda t: (t["volume_usd"], t["market_cap_usd"]),
        reverse=True,
    )

    top_candidates = ranked[: TOP_N_TOKENS * 3]  # headroom in case of dupes

    posted_count = 0
    for token in top_candidates:
        if posted_count >= TOP_N_TOKENS:
            break

        contract_address = token["contract_address"]
        if await db.is_already_posted(contract_address):
            continue

        message = build_signal_message(token)
        try:
            await context.bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            await db.mark_posted(contract_address, token["symbol"], token["name"])
            posted_count += 1
            logger.info("Posted token %s (%s)", token["symbol"], contract_address)
        except Exception as exc:
            logger.error("Failed to send message for %s: %s", contract_address, exc)

    logger.info("Scan cycle complete. Posted %d new token(s).", posted_count)


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome. This bot scans pump.fun in real time and posts the "
        "hottest new tokens to the signal channel every 5 minutes.\n\n"
        "Try:\n"
        "/buy <contract_address> <usd_amount> - simulate a buy with fee calc\n"
        "/sell <contract_address> <usd_amount> - simulate a sell with fee calc"
    )


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_trade_command(update, context, side="buy")


async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_trade_command(update, context, side="sell")


async def _handle_trade_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, side: str
) -> None:
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            f"Usage: /{side} <contract_address> <usd_amount>\n"
            f"Example: /{side} 7xKX...pump 100"
        )
        return

    contract_address, amount_str = args
    try:
        amount_usd = float(amount_str)
    except ValueError:
        await update.message.reply_text("Amount must be a number, e.g. 100")
        return

    try:
        result = simulate_trade(side, contract_address, amount_usd)
    except ValueError as exc:
        await update.message.reply_text(f"⚠️ {exc}")
        return

    await update.message.reply_text(
        format_trade_confirmation(result),
        parse_mode=ParseMode.HTML,
    )


# ----------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------

async def post_init(application: Application) -> None:
    await db.connect()
    logger.info("Database connected. Bot starting up.")


async def post_shutdown(application: Application) -> None:
    await db.close()
    logger.info("Database connection closed. Bot shutting down.")


def main() -> None:
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("sell", sell_command))

    # Kick off first scan shortly after startup, then repeat every interval.
    application.job_queue.run_repeating(
        scan_and_post,
        interval=SCAN_INTERVAL_SECONDS,
        first=10,
        name="pumpfun_scan",
    )

    logger.info(
        "Bot starting. Scanning every %s seconds, posting top %s tokens.",
        SCAN_INTERVAL_SECONDS,
        TOP_N_TOKENS,
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
