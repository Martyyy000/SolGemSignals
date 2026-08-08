"""
pumpfun_api.py

Talks directly to pump.fun's public frontend API to get the newest tokens -
no Dexscreener in the loop, so there's no extra indexing delay.

IMPORTANT: this is an unofficial, undocumented API that pump.fun's own
frontend uses. It can change shape or move without notice. If token fetching
starts failing, check the response of PUMPFUN_API_BASE + "/coins" in a
browser/Postman and adjust the field mapping in `_normalize_token` below.
"""

from __future__ import annotations

from typing import Any

import httpx

from config import PUMPFUN_API_BASE, logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SolanaSignalBot/1.0)",
    "Accept": "application/json",
}


async def fetch_latest_tokens(limit: int = 50) -> list[dict[str, Any]]:
    """
    Fetch the most recently created tokens on pump.fun, newest first.
    Returns a list of normalized token dicts. Never raises - returns []
    on any failure so a bad API response doesn't crash the scan loop.
    """
    url = f"{PUMPFUN_API_BASE}/coins/latest"
    params = {
        "offset": 0,
        "limit": limit,
        "sort": "created_timestamp",
        "order": "DESC",
        "includeNsfw": "false",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
            response = await client.get(url, params=params)
            if response.status_code == 401:
                logger.error(
                    "pump.fun API returned 401 Unauthorized. This endpoint may "
                    "now require an Authorization: Bearer <JWT> header. Check "
                    "https://github.com/BankkRoll/pumpfun-apis for the current "
                    "auth requirements and update HEADERS in pumpfun_api.py."
                )
                return []
            response.raise_for_status()
            raw_tokens = response.json()
    except httpx.HTTPError as exc:
        logger.error("pump.fun API request failed: %s", exc)
        return []
    except ValueError as exc:
        logger.error("pump.fun API returned invalid JSON: %s", exc)
        return []

    # The v3 endpoint may return a raw list or an object wrapping the list
    # (e.g. {"coins": [...]} / {"data": [...]}) - handle both defensively.
    if isinstance(raw_tokens, dict):
        for key in ("coins", "data", "results"):
            if isinstance(raw_tokens.get(key), list):
                raw_tokens = raw_tokens[key]
                break

    if not isinstance(raw_tokens, list):
        logger.error(
            "Unexpected pump.fun API response shape: %s. If this persists, "
            "inspect a live response and adjust _normalize_token/fetch_latest_tokens.",
            type(raw_tokens),
        )
        return []

    normalized = []
    for raw in raw_tokens:
        token = _normalize_token(raw)
        if token is not None:
            normalized.append(token)
    return normalized


def _normalize_token(raw: dict[str, Any]) -> dict[str, Any] | None:
    """
    Maps pump.fun's raw JSON fields onto a stable internal schema so the
    rest of the bot doesn't care about upstream field-name changes.
    """
    try:
        contract_address = raw.get("mint")
        if not contract_address:
            return None

        name = raw.get("name") or "Unknown"
        symbol = raw.get("symbol") or "???"

        # pump.fun exposes market cap directly; "volume" in the strict sense
        # isn't always present on the listing endpoint, so we fall back to
        # a reasonable proxy (real trade volume, if provided) and clearly
        # label it as an estimate downstream if we had to fall back.
        market_cap_usd = float(raw.get("usd_market_cap") or 0)
        volume_usd = raw.get("volume_24h_usd")
        volume_is_estimate = volume_usd is None
        if volume_usd is None:
            # Fallback proxy: rough activity signal from reserves delta if
            # the API doesn't expose true volume on this endpoint.
            volume_usd = float(raw.get("real_sol_reserves") or 0) * float(
                raw.get("usd_market_cap", 0) or 0
            ) / max(float(raw.get("virtual_sol_reserves") or 1), 1)

        liquidity_usd = float(raw.get("virtual_sol_reserves") or 0) * float(
            raw.get("sol_price_usd") or 0
        ) if raw.get("sol_price_usd") else market_cap_usd * 0.15  # rough fallback

        created_timestamp = raw.get("created_timestamp")

        return {
            "contract_address": contract_address,
            "name": name,
            "symbol": symbol,
            "market_cap_usd": market_cap_usd,
            "volume_usd": float(volume_usd or 0),
            "volume_is_estimate": volume_is_estimate,
            "liquidity_usd": float(liquidity_usd or 0),
            "created_timestamp": created_timestamp,
            "raw": raw,
        }
    except (TypeError, ValueError) as exc:
        logger.warning("Failed to normalize token payload: %s", exc)
        return None
