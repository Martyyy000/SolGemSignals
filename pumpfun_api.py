"""
pumpfun_api.py

Fetches the newest Solana tokens via the Solana Tracker Data API
(https://docs.solanatracker.io) and filters down to pump.fun launches.

Why not call pump.fun's own frontend API directly? pump.fun has tightened
their internal API: the public frontend-api.pump.fun domain was retired,
its replacement (frontend-api-v3.pump.fun) now requires an authenticated
JWT for most endpoints, and getting that token means reverse-engineering
their login/anti-bot flow - not something worth building a bot around.
Solana Tracker indexes the same on-chain pump.fun activity and exposes it
through a stable, documented, free-tier API instead.

Get a free API key at https://www.solanatracker.io/account/data-api
(2,500 requests/month on the free tier - see README for scan-interval
guidance so you stay within that budget).
"""

from __future__ import annotations

from typing import Any

import httpx

from config import SOLANA_TRACKER_API_KEY, SOLANA_TRACKER_API_BASE, logger

HEADERS = {
    "x-api-key": SOLANA_TRACKER_API_KEY,
    "Accept": "application/json",
}


async def fetch_latest_tokens(limit: int = 50) -> list[dict[str, Any]]:
    """
    Fetch the most recently created tokens across Solana Tracker's indexed
    DEXes, then filter down to pump.fun launches only.
    Returns a list of normalized token dicts. Never raises - returns []
    on any failure so a bad API response doesn't crash the scan loop.
    """
    url = f"{SOLANA_TRACKER_API_BASE}/tokens/latest"

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
            response = await client.get(url, params={"page": 1})
            if response.status_code == 401:
                logger.error(
                    "Solana Tracker API returned 401 Unauthorized. Check that "
                    "SOLANA_TRACKER_API_KEY is set correctly in your environment."
                )
                return []
            if response.status_code == 429:
                logger.warning(
                    "Solana Tracker API rate limit hit (429). Consider "
                    "increasing SCAN_INTERVAL_SECONDS or upgrading your plan."
                )
                return []
            response.raise_for_status()
            raw_tokens = response.json()
    except httpx.HTTPError as exc:
        logger.error("Solana Tracker API request failed: %s", exc)
        return []
    except ValueError as exc:
        logger.error("Solana Tracker API returned invalid JSON: %s", exc)
        return []

    if not isinstance(raw_tokens, list):
        logger.error(
            "Unexpected Solana Tracker API response shape: %s", type(raw_tokens)
        )
        return []

    normalized = []
    for raw in raw_tokens[:limit]:
        token = _normalize_token(raw)
        if token is not None:
            normalized.append(token)
    return normalized


def _normalize_token(raw: dict[str, Any]) -> dict[str, Any] | None:
    """
    Maps a Solana Tracker TokenInfo object onto our internal schema, and
    filters out anything that isn't actually a pump.fun launch (the Data
    API covers Raydium, Meteora, Orca, etc. too).
    """
    try:
        token_info = raw.get("token") or {}
        pools = raw.get("pools") or []

        contract_address = token_info.get("mint")
        if not contract_address or not pools:
            return None

        # Only keep pools whose market is pump.fun - the same token dict
        # can list multiple pools, so pick the pump.fun one if present.
        pumpfun_pool = next(
            (p for p in pools if str(p.get("market", "")).lower() == "pumpfun"),
            None,
        )
        if pumpfun_pool is None:
            return None

        name = token_info.get("name") or "Unknown"
        symbol = token_info.get("symbol") or "???"

        market_cap_usd = float((pumpfun_pool.get("marketCap") or {}).get("usd") or 0)
        liquidity_usd = float((pumpfun_pool.get("liquidity") or {}).get("usd") or 0)

        txns = pumpfun_pool.get("txns") or {}
        volume_usd = txns.get("volume24h", txns.get("volume"))
        volume_is_estimate = volume_usd is None
        volume_usd = float(volume_usd or 0)

        created_timestamp = (token_info.get("creation") or {}).get("created_time")

        return {
            "contract_address": contract_address,
            "name": name,
            "symbol": symbol,
            "market_cap_usd": market_cap_usd,
            "volume_usd": volume_usd,
            "volume_is_estimate": volume_is_estimate,
            "liquidity_usd": liquidity_usd,
            "created_timestamp": created_timestamp,
            "raw": raw,
        }
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to normalize token payload: %s", exc)
        return None
