"""
database.py

Persistence layer for the bot. Prevents duplicate signal posts even across
redeploys/restarts on free hosting tiers.

Two backends are supported behind one async interface:

1. Postgres (recommended for Railway/Render free tiers, since their local
   disk is ephemeral). Point DATABASE_URL at a free Supabase Postgres
   instance and every restart/redeploy will still remember posted tokens.

2. SQLite (aiosqlite). Only safe on hosts that give you a persistent volume
   (e.g. a Railway volume mounted at a fixed path). On Render/Railway's
   plain free web-service tier, local disk is wiped on redeploy - so this
   mode is provided mainly for local development/testing.
"""

from __future__ import annotations

import time
from typing import Optional

from config import DATABASE_URL, SQLITE_PATH, logger

_IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith(
    "postgresql://"
)


class Database:
    def __init__(self):
        self._pg_pool = None
        self._sqlite_conn = None

    async def connect(self):
        if _IS_POSTGRES:
            import asyncpg

            # Supabase (and most managed PG providers) require SSL.
            dsn = DATABASE_URL
            self._pg_pool = await asyncpg.create_pool(dsn=dsn, ssl="require", min_size=1, max_size=5)
            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS posted_tokens (
                        contract_address TEXT PRIMARY KEY,
                        symbol TEXT,
                        name TEXT,
                        posted_at DOUBLE PRECISION
                    );
                    """
                )
            logger.info("Connected to Postgres database.")
        else:
            import aiosqlite

            self._sqlite_conn = await aiosqlite.connect(SQLITE_PATH)
            await self._sqlite_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posted_tokens (
                    contract_address TEXT PRIMARY KEY,
                    symbol TEXT,
                    name TEXT,
                    posted_at REAL
                );
                """
            )
            await self._sqlite_conn.commit()
            logger.warning(
                "Using local SQLite file (%s). On Render/Railway free web "
                "services this file is wiped on every redeploy/restart unless "
                "you attach a persistent volume. For guaranteed persistence, "
                "set DATABASE_URL to a free Supabase Postgres instance instead.",
                SQLITE_PATH,
            )

    async def close(self):
        if self._pg_pool:
            await self._pg_pool.close()
        if self._sqlite_conn:
            await self._sqlite_conn.close()

    async def is_already_posted(self, contract_address: str) -> bool:
        if self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT 1 FROM posted_tokens WHERE contract_address = $1",
                    contract_address,
                )
                return row is not None
        else:
            cursor = await self._sqlite_conn.execute(
                "SELECT 1 FROM posted_tokens WHERE contract_address = ?",
                (contract_address,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def mark_posted(self, contract_address: str, symbol: str, name: str):
        now = time.time()
        if self._pg_pool:
            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO posted_tokens (contract_address, symbol, name, posted_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (contract_address) DO NOTHING;
                    """,
                    contract_address,
                    symbol,
                    name,
                    now,
                )
        else:
            await self._sqlite_conn.execute(
                """
                INSERT OR IGNORE INTO posted_tokens (contract_address, symbol, name, posted_at)
                VALUES (?, ?, ?, ?);
                """,
                (contract_address, symbol, name, now),
            )
            await self._sqlite_conn.commit()


db = Database()
