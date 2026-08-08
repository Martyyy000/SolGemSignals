"""
formatter.py

Builds the Telegram signal message. High energy, professional tone, HTML
parse mode - but every line states something that is actually true about
the token. No fabricated "insider wallet activity" claims: that kind of
fake urgency is manipulative and isn't something this bot does.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config import TROJAN_AFFILIATE_LINK


def _fmt_usd(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.0f}"


def build_signal_message(token: dict[str, Any]) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    contract_address = token["contract_address"]
    name = _escape_html(token["name"])
    symbol = _escape_html(token["symbol"])
    volume_str = _fmt_usd(token["volume_usd"])
    if token.get("volume_is_estimate"):
        volume_str += " (est.)"
    liquidity_str = _fmt_usd(token["liquidity_usd"])
    market_cap_str = _fmt_usd(token["market_cap_usd"])

    dexscreener_url = f"https://dexscreener.com/solana/{contract_address}"

    message = (
        "🔥 <b>NEW PUMP.FUN GEM DETECTED!</b> 🔥\n"
        f"⏱ Timestamp: {now_utc}\n\n"
        f"📈 Token: <b>{name}</b> (${symbol})\n"
        f"📊 24h Volume: {volume_str}\n"
        f"💧 Liquidity: {liquidity_str}\n"
        f"🏦 Market Cap: {market_cap_str}\n\n"
        "⚠️ <i>High risk: this is a brand-new pump.fun token. Most new "
        "tokens lose most of their value quickly. Only risk what you can "
        "afford to lose and always verify the contract yourself.</i>\n\n"
        f"📝 CA: <code>{contract_address}</code>\n\n"
        f'🔗 <a href="{TROJAN_AFFILIATE_LINK}">Quick Buy via Trojan Bot</a> '
        "(affiliate link - we may earn a fee)\n"
        f'🔗 <a href="{dexscreener_url}">Analyze Chart on Dexscreener</a>'
    )
    return message


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
