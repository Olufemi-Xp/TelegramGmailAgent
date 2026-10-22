# Deploying Telegram Personal AI Assistant on Vercel

This guide provides everything needed to deploy and run your personal AI assistant on **Vercel** serverless infrastructure using **Neon PostgreSQL** (or Supabase), **Telegram Webhooks**, and **Vercel Cron**.

---

## 1. Why Did the Previous Deployment Fail?

1. **Vercel Hobby Cron Frequency Restriction**:
   Vercel Free (Hobby) accounts **strictly forbid** minute-by-minute or hourly cron expressions (`* * * * *` or `0 * * * *`). Deploying a project with a cron schedule faster than once a day causes Vercel to abort the deployment with a build error:
   ```
   Error: A Hobby plan is limited to running Cron Jobs once a day
   ```
   **Fix implemented:** `vercel.json` has been updated to use the Hobby-compliant daily schedule (`"schedule": "0 8 * * *"`).
2. **Serverless Database Drivers & Connection Pooling**:
   Standard Postgres connection strings from Neon (`postgresql://...` or `postgres://...`) look for synchronous drivers (`psycopg2`).
   **Fix implemented:** `app/config.py` now automatically normalizes incoming URLs to `postgresql+asyncpg://` and switches connection pooling to `NullPool` on serverless instances to prevent connection leaks.
3. **Trimmed Production Dependencies**:
   `pytest` and development dependencies have been separated into `requirements-dev.txt`, reducing build duration and serverless bundle size.

---

## 2. Architecture & Secrets Design

### A. 100% Environment-Variable Driven (No Local Files)
- **No `credentials.json` or `token.json` files are ever used or required.**
- All Gmail OAuth client credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`) are read directly from environment variables.
- You can optionally set `GMAIL_REFRESH_TOKEN` directly in Vercel environment variables to authenticate Gmail without ever going through browser login!

### B. Hosted Database on Vercel (Neon Postgres)
- SQLite cannot persist across serverless invocations on Vercel.
- **Neon PostgreSQL** (or Supabase) is used for:
  - **Conversational Memory**: Stored in `personal_memories` with semantic vector indexing.
  - **Processed Email Tracking**: Stored in `processed_emails` to ensure you are never notified twice about the same email.
  - **Draft Storage**: Stored in `email_drafts` and synchronized with Gmail.
  - **Reminders & Audits**: Stored in `reminders` and `audit_events`.

### C. Telegram Webhooks vs. Polling
- Long-polling is disabled on Vercel because serverless lambdas terminate after handling an HTTP request.
- Telegram communicates with Vercel via **Webhooks** (`POST /api/telegram/webhook`).
- A 1-click webhook registration endpoint is available at `/api/telegram/set-webhook`.

---

## 3. Environment Variables for Vercel Dashboard

In the **Vercel Dashboard > Project Settings > Environment Variables**, add the following:

| Variable Name | Required | Example / Value | Purpose |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | **Yes** | `postgresql+asyncpg://user:pass@ep-xyz.us-east-2.aws.neon.tech/neondb?ssl=require` | Hosted Neon PostgreSQL connection string. |
| `TELEGRAM_BOT_TOKEN` | **Yes** | `8650420403:AAGY...` | Bot API token from [@BotFather](https://t.me/BotFather). |
| `TELEGRAM_ALLOWED_USER_IDS` | **Yes** | `6400123091` | Your numeric Telegram User ID. Blocks unauthorized strangers. |
| `BOT_MODE` | **Yes** | `webhook` | Tells the assistant to operate in serverless webhook mode. |
| `TELEGRAM_WEBHOOK_URL` | **Yes** | `https://your-project.vercel.app` | Your deployed Vercel domain. |
| `TELEGRAM_WEBHOOK_SECRET` | *Optional* | `random_secret_string_32_chars` | Secret token to authenticate Telegram webhook payloads. |
| `OPENROUTER_API_KEY` | **Yes** | `sk-or-v1-...` | LLM reasoning API key from [OpenRouter](https://openrouter.ai/keys). |
| `OPENROUTER_MODEL` | *Optional* | `openai/gpt-oss-120b` | Primary reasoning model. |
| `OPENROUTER_FALLBACK_MODEL`| *Optional* | `meta-llama/llama-3.3-70b-instruct`| Fallback model for failover. |
| `GROQ_API_KEY` | **Yes** | `gsk_...` | Free Whisper transcription from [console.groq.com](https://console.groq.com). |
| `TRANSCRIPTION_PROVIDER` | **Yes** | `groq` | Directs voice note transcription to Groq Whisper. |
| `ENCRYPTION_KEY` | **Yes** | `w_9w12M7O5E-8d_f1JzB4pA6kL3sV9tX2qY5mZ7nK1o=` | 32-byte Fernet key for encrypting sensitive credentials. |
| `APP_ENV` | **Yes** | `production` | Set to production. |
| `APP_TIMEZONE` | *Optional* | `Africa/Lagos` | Default user timezone. |

#### Gmail Integration (Optional):
| Variable Name | Required | Description |
| :--- | :--- | :--- |
| `GOOGLE_CLIENT_ID` | Optional | OAuth 2.0 Client ID from Google Cloud Console. |
| `GOOGLE_CLIENT_SECRET` | Optional | OAuth 2.0 Client Secret from Google Cloud Console. |
| `GOOGLE_REDIRECT_URI` | Optional | `https://your-project.vercel.app/oauth/google/callback` |
| `GMAIL_REFRESH_TOKEN` | Optional | Pre-generated refresh token to skip OAuth browser flow entirely. |

#### Research Search Providers (Optional):
- `PERPLEXITY_API_KEY`: Perplexity AI API Key.
- `TAVILY_API_KEY`: Tavily Search API Key.

---

## 4. Step-by-Step Deployment Guide

### Step 1: Create Free Neon PostgreSQL Database
1. Go to **[neon.tech](https://neon.tech/)** and sign up for free.
2. Click **Create Project** (e.g. `telegram-assistant`).
3. Under **Dashboard > Connection Details**, copy the connection string.
4. Replace `postgresql://` with `postgresql+asyncpg://`:
   ```
   postgresql+asyncpg://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?ssl=require
   ```

### Step 2: Push to GitHub & Deploy to Vercel
1. Your repository is already linked to GitHub:
   ```powershell
   git push origin main
   ```
2. In **[Vercel Dashboard](https://vercel.com/dashboard)**, click **Add New... > Project** and import `Olufemi-Xp/TelegramGmailAgent`.
3. Add the Environment Variables listed in Section 3 above.
4. Click **Deploy**.

### Step 3: Activate Telegram Webhook (1-Click)
Once Vercel finishes deploying, open this URL in your web browser:
```
https://<your-project>.vercel.app/api/telegram/set-webhook?url=https://<your-project>.vercel.app/api/telegram/webhook
```
You will receive an instant JSON confirmation:
```json
{
  "status": "success",
  "webhook_url": "https://<your-project>.vercel.app/api/telegram/webhook",
  "has_secret": false
}
```

---

## 5. Cron Jobs & Inbox Monitoring on Vercel Free Plan

### Built-in Vercel Cron
`vercel.json` is pre-configured with a daily morning cron:
```json
"crons": [
  {
    "path": "/api/cron/inbox",
    "schedule": "0 8 * * *"
  }
]
```
Every day at 8:00 AM UTC, Vercel triggers `/api/cron/inbox`, which:
1. Checks for unread Gmail emails.
2. Deduplicates against `processed_emails` in Neon Postgres.
3. Sends new email summaries to your Telegram bot.
4. Delivers any due reminders.

### Want Inbox Checks Every 10 or 15 Minutes for Free?
Because Vercel limits the Hobby plan scheduler to once a day, you can get frequent automated checks completely free without upgrading to Vercel Pro:
1. Go to **[cron-job.org](https://cron-job.org/)** (100% free web cron service).
2. Create a new cron job:
   - **URL**: `https://<your-project>.vercel.app/api/cron/inbox`
   - **Schedule**: Every 10 or 15 minutes.
3. Save. Your Vercel assistant will now monitor your Gmail inbox throughout the day!
