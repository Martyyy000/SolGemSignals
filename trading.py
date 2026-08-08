"""
trading.py

Modular, simulated in-bot trading feature. This does NOT execute real
on-chain swaps - it demonstrates the fee-calculation flow you'd wire up to
a real Solana swap (e.g. via Jupiter Aggregator API + a custodial or
session-based signer) in a production build. Keeping actual key custody
and transaction signing out of this bot is intentional: that's a
significant additional security surface (custody of user funds) that
needs its own dedicated audit and legal review before going live.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import TRADE_FEE_PERCENT


@dataclass
class TradeResult:
    side: str  # "buy" or "sell"
    contract_address: str
    gross_amount_usd: float
    fee_usd: float
    net_amount_usd: float
    fee_percent: float


def simulate_trade(side: str, contract_address: str, amount_usd: float) -> TradeResult:
    """
    Calculates the platform fee on a simulated trade.

    side: "buy" or "sell"
    amount_usd: gross trade volume in USD the user wants to trade
    """
    if amount_usd <= 0:
        raise ValueError("Trade amount must be greater than zero.")
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")

    fee_usd = round(amount_usd * (TRADE_FEE_PERCENT / 100), 4)
    net_amount_usd = round(amount_usd - fee_usd, 4)

    return TradeResult(
        side=side,
        contract_address=contract_address,
        gross_amount_usd=amount_usd,
        fee_usd=fee_usd,
        net_amount_usd=net_amount_usd,
        fee_percent=TRADE_FEE_PERCENT,
    )


def format_trade_confirmation(result: TradeResult) -> str:
    return (
        f"✅ <b>Simulated {result.side.upper()} order</b>\n"
        f"Contract: <code>{result.contract_address}</code>\n"
        f"Gross amount: ${result.gross_amount_usd:,.2f}\n"
        f"Platform fee ({result.fee_percent:.2f}%): ${result.fee_usd:,.2f}\n"
        f"Net amount: ${result.net_amount_usd:,.2f}\n\n"
        "<i>This is a simulation only - no real on-chain transaction was "
        "sent. Real execution requires a signing integration (e.g. Jupiter "
        "Aggregator + wallet custody), which is intentionally not included "
        "here.</i>"
    )
