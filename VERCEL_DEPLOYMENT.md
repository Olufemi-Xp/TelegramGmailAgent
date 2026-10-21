# Deploying Telegram Personal AI Assistant on Vercel

This guide walks you through deploying your personal AI assistant to **Vercel** serverless infrastructure with **Telegram Webhooks**, **Vercel Cron** for reminders, and **Cloud PostgreSQL**.

---

## 1. Architectural Highlights on Vercel

1. **Serverless Execution**: Runs as a serverless ASGI application via `api/index.py` and `@vercel/python`.
2. **Telegram Webhooks**: Automatically switches from polling to webhooks (`/api/telegram/webhook`) so updates are pushed instantly to Vercel without continuous long-polling loops.
3. **Scheduled Reminders**: Scheduled via `vercel.json` Cron (`/api/cron/reminders`) executing every minute to process due reminders.
4. **Cloud Database**: Uses a managed PostgreSQL database (e.g., [Neon.tech](https://neon.tech/) or [Supabase](https://supabase.com/)) with vector extension support.

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Provision a Free PostgreSQL Database (Neon)

Vercel functions are stateless and ephemeral, requiring a persistent cloud database:

1. Sign up for free at **[neon.tech](https://neon.tech/)** (or Supabase).
2. Create a new project (e.g., `telegram-assistant`).
3. Under **Dashboard > Connection Details**, copy the **Direct connection string** (or pooled connection string):
   ```
   postgresql://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. For SQLAlchemy async, replace `postgresql://` with `postgresql+asyncpg://`:
   ```
   postgresql+asyncpg://user:password@ep-xyz.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

---

### Step 2: Import Your GitHub Repository to Vercel

1. Log in to **[Vercel Dashboard](https://vercel.com/dashboard)**.
2. Click **Add New... > Project**.
3. Under **Import Git Repository**, select `Olufemi-Xp/TelegramGmailAgent`.
4. Keep the default Framework Preset as **Other**.

---

### Step 3: Configure Vercel Environment Variables

In the **Environment Variables** section of the Vercel project setup, add the following variables:

| Variable Name | Example / Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-xyz.neon.tech/neondb?sslmode=require` | Your Neon or Supabase connection string |
| `TELEGRAM_BOT_TOKEN` | `8650420403:AA...` | Your Telegram Bot token from @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | `6400123091` | Your numeric Telegram user ID |
| `BOT_MODE` | `webhook` | Explicitly enables webhook mode |
| `TELEGRAM_WEBHOOK_URL` | `https://<your-project>.vercel.app` | Base URL of your deployed Vercel app |
| `TELEGRAM_WEBHOOK_SECRET` | *(Optional, e.g. 32-char random string)* | Secret for validating webhook authenticity |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b` | Primary reasoning model |
| `OPENROUTER_FALLBACK_MODEL` | `meta-llama/llama-3.3-70b-instruct` | Automatic fallback model |
| `ENCRYPTION_KEY` | `w_9w12M7O5E-8d_f1JzB4pA6kL3sV9tX2qY5mZ7nK1o=` | 32-byte Fernet key for token encryption |
| `GROQ_API_KEY` | `gsk_...` | Free Whisper transcription from Groq |
| `TRANSCRIPTION_PROVIDER` | `groq` | Set to `groq` for ultra-fast free voice transcription |
| `TAVILY_API_KEY` | `tvly-...` | Web search API key |
| `PERPLEXITY_API_KEY` | `pplx-...` | Deep research API key |
| `APP_ENV` | `production` | Production mode |
| `APP_TIMEZONE` | `Africa/Lagos` | Your local timezone |

*(If using Gmail integration)*:
- `GOOGLE_CLIENT_ID`: `your-google-client-id`
- `GOOGLE_CLIENT_SECRET`: `your-google-client-secret`
- `GOOGLE_REDIRECT_URI`: `https://<your-project>.vercel.app/oauth/google/callback`

Click **Deploy**.

---

### Step 4: Run Initial Database Migration

Once your Neon database connection string is ready, apply the database schema either:

**Option A (Locally with Alembic)**:
```powershell
# Set your Neon DATABASE_URL temporarily
$env:DATABASE_URL="postgresql+asyncpg://user:password@ep-xyz.neon.tech/neondb?sslmode=require"
python -m alembic upgrade head
```

**Option B (Automatic)**:
The application calls `await init_db()` automatically on its first cold start, creating all tables and the pgvector extension if it does not already exist.

---

### Step 5: Activate Telegram Webhook (One-Click)

After Vercel finishes deploying (e.g. `https://telegram-gmail-agent.vercel.app`), configure Telegram to send updates to your Vercel URL by opening this URL in your web browser:

```
https://<your-project>.vercel.app/api/telegram/set-webhook?url=https://<your-project>.vercel.app/api/telegram/webhook
```

You will receive an immediate confirmation:
```json
{
  "status": "success",
  "webhook_url": "https://<your-project>.vercel.app/api/telegram/webhook",
  "has_secret": false
}
```

To verify the webhook status at any time, open:
```
https://<your-project>.vercel.app/api/telegram/webhook-info
```

---

### Step 6: Verify Everything Live

1. Open your Telegram bot (`@xpgmailasst_bot`).
2. Send `/start` — the bot should greet you with interactive buttons.
3. Send a voice message — it will transcribe via Groq and answer back.
4. Send `/status` — to verify database connectivity, memory count, and budget diagnostics.
