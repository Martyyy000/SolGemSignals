# Pump.fun Signal Bot — Complete Setup Guide

This guide assumes zero prior experience. Follow it top to bottom.

## What this bot does

- Checks for the newest pump.fun tokens every 20 minutes (via a stable third-party data API — see Step 3a)
- Picks the top 3 by trading volume/market cap
- Posts a formatted signal to your Telegram channel (never posts the same token twice, even after a restart)
- Includes `/buy` and `/sell` commands that simulate a trade and show a 1% platform fee
- Signal messages include your Trojan affiliate link

---

## Step 1 — Create your bot with @BotFather

1. Open Telegram, search for **@BotFather**, and start a chat.
2. Send `/newbot`.
3. Choose a display name (e.g. "Solana Gem Signals").
4. Choose a username ending in `bot` (e.g. `solana_gem_signals_bot`).
5. BotFather replies with a token that looks like:
   `123456789:AAExampleTokenGoesHere`
   This is your `TELEGRAM_BOT_TOKEN`. Keep it secret — anyone with it can control your bot.

---

## Step 2 — Create your channel and get its Channel ID

1. In Telegram, create a new **Channel** (not a group). Public or private both work.
2. Add your bot as an **Administrator** of the channel (Channel Settings → Administrators → Add Admin), with at minimum "Post Messages" permission.
3. To get the numeric Channel ID, use this reliable method (forwarding channel posts to bots like @userinfobot often shows nothing, since Telegram hides the origin on forwarded channel messages):
   - Make sure your bot is already added as an **Administrator** of the channel (previous step) — this is required or the next part won't work.
   - Post **any** message in the channel (type anything, e.g. "test").
   - Open this URL in your browser, replacing `<TOKEN>` with your real bot token from Step 1:
     ```
     https://api.telegram.org/bot<TOKEN>/getUpdates
     ```
   - You'll see a JSON response. Look for a section like:
     ```json
     "channel_post": { "chat": { "id": -1001234567890, "title": "Your Channel" } }
     ```
   - The `id` value (including the minus sign) is your `TELEGRAM_CHANNEL_ID`.
   - **If the JSON is empty (`"result":[]`):** the bot hasn't received the update yet. Post a new test message in the channel *after* the bot was made admin, then refresh the `getUpdates` URL. Telegram only shows recent updates that arrived after the bot could see them.
   - Alternative: if your channel has a public `@username`, you can use `@yourchannelname` directly instead of the numeric ID — no lookup needed.

---

## Step 3 — Set up the free database (Supabase Postgres)

Free tiers on Railway/Render wipe local files on redeploy, so we use a real hosted database instead of a JSON file.

1. Go to [supabase.com](https://supabase.com) and sign up (free).
2. Click **New Project**. Pick any name, set a database password (save it somewhere), pick the region closest to you.
3. Wait ~2 minutes for the project to finish provisioning.
4. In your project dashboard, click the **Connect** button (usually near the top of the page — not inside Project Settings anymore, Supabase moved it).
5. A panel opens with several connection string options. For this bot, use the **Session pooler** string (it works reliably from hosts like Railway/Render, which are usually IPv4-only). It looks like:
   `postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-region.pooler.supabase.com:5432/postgres`
6. Replace `[YOUR-PASSWORD]` with the password you set in step 2.
7. This full string is your `DATABASE_URL`.

You don't need to create any tables manually — the bot creates its own table automatically on first run.

---

## Step 3a — Get your token data API key (Solana Tracker)

pump.fun's own internal API has become locked-down and requires special access tokens that are impractical to obtain reliably, so this bot pulls token data from **Solana Tracker**, a documented third-party service that indexes the same on-chain pump.fun activity.

1. Go to [solanatracker.io/account/data-api](https://www.solanatracker.io/account/data-api) and sign up (free, no credit card).
2. In your dashboard sidebar, click **Data API**.
3. Copy your API key.
4. This is your `SOLANA_TRACKER_API_KEY`.

**About the free tier:** it includes 2,500 requests/month. This bot uses 1 request per scan cycle, and defaults to scanning every 20 minutes (`SCAN_INTERVAL_SECONDS=1200`), which uses roughly 2,160 requests/month — comfortably inside the free quota with some room to spare. If you lower the interval, you may run out of requests before the month ends; check your usage in the Solana Tracker dashboard, or upgrade to a paid plan for more headroom.

---

## Step 4 — Get your Trojan affiliate link

1. Open Telegram, go to **@solana_trojanbot** (or your existing Trojan referral bot).
2. Follow their affiliate/referral program instructions to generate your personal referral link.
3. This is your `TROJAN_AFFILIATE_LINK`.

---

## Step 5 — Run it locally (optional, but recommended first)

1. Install Python 3.11+ from [python.org](https://python.org).
2. Download/copy this project folder to your computer.
3. Open a terminal in the project folder and run:
   ```bash
   python -m venv venv
   source venv/bin/activate       # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
5. Open `.env` and fill in your real values from Steps 1–4.
6. Install one more package for local `.env` loading and run:
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv()" # sanity check
   python bot.py
   ```
   (If you want `.env` to load automatically, add `from dotenv import load_dotenv; load_dotenv()` at the top of `bot.py` before the other imports — it's left out by default since cloud hosts inject env vars directly.)
7. You should see log lines like `Bot starting. Scanning every 1200 seconds...`. Check your Telegram channel after the first cycle (or wait up to 20 minutes for it).

---

## Step 6 — Deploy to Railway.app (recommended, easiest)

1. Push this project to a GitHub repository (create a free GitHub account if needed, create a new repo, upload these files — **do not upload your `.env` file**).
2. Go to [railway.app](https://railway.app) and sign up with GitHub.
3. Click **New Project → Deploy from GitHub repo**, select your repo.
4. Railway will detect it's a Python app. Click on the deployed service, go to the **Variables** tab.
5. Add each of these as a separate variable (Name / Value):

   | Variable | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | your token from Step 1 |
   | `TELEGRAM_CHANNEL_ID` | your channel ID from Step 2 |
   | `DATABASE_URL` | your Supabase URI from Step 3 |
   | `SOLANA_TRACKER_API_KEY` | your API key from Step 3a |
   | `TROJAN_AFFILIATE_LINK` | your link from Step 4 |
   | `TRADE_FEE_PERCENT` | `1.0` |
   | `SCAN_INTERVAL_SECONDS` | `1200` |
   | `TOP_N_TOKENS` | `3` |

6. Go to **Settings → Deploy**, set the **Start Command** to:
   ```
   python bot.py
   ```
7. Railway will redeploy automatically. Check the **Deployments → Logs** tab to confirm it's running.
8. Your bot now runs 24/7 and posts to your channel every 20 minutes.

---

## Step 7 — Deploy to Render.com (alternative)

1. Push the project to GitHub (same as Step 6.1).
2. Go to [render.com](https://render.com), sign up, click **New → Background Worker** (not "Web Service" — this bot doesn't serve HTTP requests).
3. Connect your GitHub repo.
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. Under **Environment**, add the same variables listed in the Step 6 table above.
6. Click **Create Background Worker**. Watch the **Logs** tab for startup confirmation.

> Render's free background workers can spin down after inactivity on some plans — if your bot goes quiet, check Render's current free-tier sleep policy in their dashboard/docs, since this changes over time.

---

## Troubleshooting

- **Bot doesn't post anything:** check the logs for `Solana Tracker API request failed`. Also confirm the bot is an admin in your channel, and that pump.fun actually had new launches in the last cycle (quiet periods happen).
- **HTTP 401 error in logs:** double-check `SOLANA_TRACKER_API_KEY` is set correctly and copied in full (no extra spaces).
- **HTTP 429 error in logs:** you've hit the free-tier monthly request limit. Check your usage at solanatracker.io, raise `SCAN_INTERVAL_SECONDS`, or upgrade your plan.
- **"Missing required environment variable" error on startup:** you forgot to set one of the required variables on your host — double check the Variables/Environment tab.
- **Duplicate posts after redeploy:** confirm `DATABASE_URL` is actually set and pointing at Supabase, not falling back to local SQLite.
- **/buy or /sell doesn't respond:** these only work in a private chat with the bot, not in the channel itself (bots generally can't read commands posted in channels they administer).

## Important note on the trading feature

`/buy` and `/sell` are **simulations only** — they calculate the 1% fee but do not execute a real on-chain swap or touch real funds. Wiring this up to real execution (e.g. via the Jupiter Aggregator API) requires custody or session-signing of user private keys, which is a serious security and legal responsibility that needs its own audit before handling real money.
