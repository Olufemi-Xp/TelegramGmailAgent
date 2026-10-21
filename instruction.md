# Step-by-Step Setup & Run Guide: Personal AI Assistant

This guide covers everything required to obtain all API keys, install dependencies, configure environment variables, and run the assistant locally or in production on Railway.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Obtaining All API Keys & Credentials](#2-obtaining-all-api-keys--credentials)
   - [A. Telegram Bot Token & Numeric User ID](#a-telegram-bot-token--numeric-user-id-required)
   - [B. OpenRouter LLM API Key](#b-openrouter-llm-api-key-required)
   - [C. Fernet Encryption Key](#c-fernet-encryption-key-required)
   - [D. Web Search Providers (Tavily, Perplexity, Google)](#d-web-search-providers-at-least-one-recommended)
   - [E. Google Cloud Gmail OAuth 2.0](#e-google-cloud-gmail-oauth-20-optional-for-email)
3. [Environment Configuration (`.env`)](#3-environment-configuration-env)
4. [Local Installation & Run Instructions](#4-local-installation--run-instructions)
   - [Option A: Python Virtual Environment](#option-a-run-with-python-virtualenv)
   - [Option B: Docker Compose (PostgreSQL + pgvector)](#option-b-run-with-docker-compose-recommended)
5. [Database Migrations (Alembic)](#5-database-migrations-alembic)
6. [Testing the Application](#6-testing-the-application)
7. [Railway Deployment Guide](#7-railway-deployment-guide)
8. [Telegram Commands Cheat Sheet](#8-telegram-commands-cheat-sheet)

---

## 1. Prerequisites

Before starting, ensure you have:
- **Python 3.12+** (tested and compatible with Python 3.12 - 3.14)
- **Git**
- *(Optional but recommended)* **Docker & Docker Compose** for local PostgreSQL with `pgvector`
- A **Telegram** account

---

## 2. Obtaining All API Keys & Credentials

### A. Telegram Bot Token & Numeric User ID *(REQUIRED)*

#### 1. Create Bot & Get Bot Token
1. Open your Telegram app and search for **[@BotFather](https://t.me/BotFather)** (verified with blue checkmark).
2. Click **Start** or send `/start`.
3. Send `/newbot`.
4. Enter a display name for your bot (e.g., `My Private Assistant`).
5. Enter a username ending in `bot` (e.g., `my_private_personal_ai_bot`).
6. BotFather will return your **HTTP API Token**:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```
   Copy this value into `TELEGRAM_BOT_TOKEN`.

#### 2. Get Your Numeric Telegram User ID (Whitelist Security)
Because this is a private bot with access to your emails and personal memory, **default-deny security** blocks everyone whose numeric user ID is not in the whitelist:
1. In Telegram, search for **[@userinfobot](https://t.me/userinfobot)** or **[@raw_data_bot](https://t.me/raw_data_bot)**.
2. Send `/start`.
3. The bot will reply with your profile information. Copy the numeric **Id** (e.g., `123456789`).
4. Set this in `TELEGRAM_ALLOWED_USER_IDS=123456789` (separate multiple IDs with commas if needed).

---

### B. OpenRouter LLM API Key *(REQUIRED)*

OpenRouter acts as the central LLM provider for the reasoning agent.

1. Go to [https://openrouter.ai/](https://openrouter.ai/) and sign up or log in.
2. Navigate to **Keys** ([https://openrouter.ai/keys](https://openrouter.ai/keys)).
3. Click **Create Key**, give it a name (e.g. `telegram-assistant`), and copy the key:
   ```
   sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
4. Verify your models in `.env`:
   - Primary model: `OPENROUTER_MODEL=openai/gpt-oss-120b`
   - Fallback model: `OPENROUTER_FALLBACK_MODEL=meta-llama/llama-3.3-70b-instruct`

---

### C. Fernet Encryption Key *(REQUIRED)*

This key encrypts your Gmail OAuth refresh and access tokens in the database using 256-bit AES-Fernet encryption.

Generate a secure key in your terminal with Python:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Example output:
```
w_9w12M7O5E-8d_f1JzB4pA6kL3sV9tX2qY5mZ7nK1o=
```
Copy this value to `ENCRYPTION_KEY` in `.env`.

---

### D. Web Search Providers *(At least one recommended)*

The assistant can search the web for news, jobs, and research. You can configure any or all of the following:

#### Option 1: Tavily Search (Recommended)
1. Go to [https://tavily.com/](https://tavily.com/) and create a free account.
2. Copy your API Key from the dashboard:
   ```
   tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. Set `TAVILY_API_KEY=tvly-...` in `.env`.

#### Option 2: Perplexity API
1. Go to [https://www.perplexity.ai/settings/api](https://www.perplexity.ai/settings/api).
2. Generate an API Key.
3. Set:
   ```ini
   PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   PERPLEXITY_MODEL=sonar
   ```

#### Option 3: Google Custom Search JSON API
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Custom Search API**.
3. Create an API Key in **Credentials** (`GOOGLE_SEARCH_API_KEY`).
4. Go to [Google Programmable Search Engine](https://programmablesearchengine.google.com/).
5. Create a search engine that searches the entire web and copy the **Search Engine ID** (`GOOGLE_SEARCH_ENGINE_ID`).

---

### E. Google Cloud Gmail OAuth 2.0 *(Optional - for Email)*

To enable Gmail reading, summarization, and draft replies:

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `Personal-AI-Assistant`).
3. In **APIs & Services > Library**, search for **Gmail API** and click **Enable**.
4. In **APIs & Services > OAuth consent screen**:
   - User Type: **External**
   - App Name: `Personal AI Assistant`
   - User support email: your email
   - Under **Scopes**, add:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.compose`
   - Under **Test users**, add your personal Gmail address.
5. In **APIs & Services > Credentials**:
   - Click **Create Credentials** > **OAuth client ID**.
   - Application type: **Web application**.
   - Name: `Telegram Assistant Webhook`.
   - **Authorized redirect URIs**:
     - For local development: `http://localhost:8000/oauth/google/callback`
     - For Railway production: `https://<your-railway-domain>.railway.app/oauth/google/callback`
   - Click **Create** and copy:
     - **Client ID** (`GOOGLE_CLIENT_ID`)
     - **Client Secret** (`GOOGLE_CLIENT_SECRET`)
6. In `.env`, set:
   ```ini
   GOOGLE_CLIENT_ID=xxxxxxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
   GOOGLE_REDIRECT_URI=http://localhost:8000/oauth/google/callback
   ```

> 🔒 **Security Guarantee:** The code strictly forbids sending emails. Only searching, reading, summarizing, and draft creation are supported.

---

## 3. Environment Configuration (`.env`)

1. In the project directory (`TelegramGmailAgent`), copy the example file:
   ```bash
   cp .env.example .env
   ```
   *(On Windows PowerShell: `Copy-Item .env.example .env`)*

2. Open `.env` and fill in your keys:

```ini
# ==========================================
# Telegram Bot Configuration
# ==========================================
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USER_IDS=123456789

# ==========================================
# Database Connection
# ==========================================
# For Docker Compose / Railway PostgreSQL:
DATABASE_URL=postgresql+asyncpg://assistant:secretpassword123@localhost:5432/personal_assistant
# For simple local testing without Postgres:
# DATABASE_URL=sqlite+aiosqlite:///storage/agent.db

# ==========================================
# OpenRouter LLM Gateway
# ==========================================
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=openai/gpt-oss-120b
OPENROUTER_FALLBACK_MODEL=meta-llama/llama-3.3-70b-instruct
OPENROUTER_SITE_URL=https://github.com/personal-ai-assistant
OPENROUTER_APP_NAME=Personal AI Assistant

# ==========================================
# Secret Encryption Key
# ==========================================
ENCRYPTION_KEY=w_9w12M7O5E-8d_f1JzB4pA6kL3sV9tX2qY5mZ7nK1o=

# ==========================================
# Search Providers
# ==========================================
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PERPLEXITY_API_KEY=
PERPLEXITY_MODEL=sonar
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_ENGINE_ID=

# ==========================================
# Google / Gmail OAuth 2.0
# ==========================================
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/oauth/google/callback

# ==========================================
# Operational Settings
# ==========================================
APP_ENV=development
APP_TIMEZONE=Africa/Lagos
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=20
MAX_TOOL_ITERATIONS=6
REQUEST_TIMEOUT_SECONDS=60.0
DAILY_MODEL_BUDGET=5.0
MONTHLY_MODEL_BUDGET=50.0

HOST=0.0.0.0
PORT=8000
STORAGE_DIR=./storage
```

---

## 4. Local Installation & Run Instructions

Navigate to the project folder first:
```bash
cd c:\Users\user\Documents\XpAut\TelegramGmailAgent
```

### Option A: Run with Python Virtualenv

#### 1. Create & Activate Virtual Environment
```bash
# On Windows PowerShell:
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# On macOS/Linux:
python3 -m venv .venv
source .venv/bin/activate
```

#### 2. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Run Database Migrations
```bash
python -m alembic upgrade head
```

#### 4. Start the Application & Bot
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

### Option B: Run with Docker Compose *(Recommended)*

Docker Compose launches both the PostgreSQL 16 container with `pgvector` and the assistant application.

```bash
docker compose up --build
```

To run in the background (detached mode):
```bash
docker compose up -d
```

To inspect logs:
```bash
docker compose logs -f app
```

To stop:
```bash
docker compose down
```

---

## 5. Database Migrations (Alembic)

The project uses Alembic to manage database schemas.

- **Apply all migrations:**
  ```bash
  python -m alembic upgrade head
  ```
- **Check current revision:**
  ```bash
  python -m alembic current
  ```
- **Create a new migration (after modifying `app/database/models.py`):**
  ```bash
  python -m alembic revision --autogenerate -m "describe_changes"
  ```

---

## 6. Testing the Application

Run the automated test suite with pytest:

```bash
python -m pytest -v
```

To run a specific test file:
```bash
# Run security tests
python -m pytest tests/test_security.py -v

# Run end-to-end multi-turn flows
python -m pytest tests/test_e2e_flows.py -v
```

All 34 tests execute within ~10 seconds using an isolated in-memory test database.

---

## 7. Railway Deployment Guide

Railway provides zero-maintenance cloud hosting with managed PostgreSQL.

### Step 1: Create a Railway Project
1. Log in to [Railway.app](https://railway.app/).
2. Click **New Project** > **Provision PostgreSQL**.
3. Under the PostgreSQL service settings, note the connection variables.

### Step 2: Deploy Application from GitHub
1. In the same project, click **New Service** > **GitHub Repo**.
2. Select your repository containing the `TelegramGmailAgent` code.
3. Railway will automatically detect `Dockerfile` and `railway.json`.

### Step 3: Configure Railway Environment Variables
Go to your application service > **Variables** tab, and add:
- `DATABASE_URL`: `${{Postgres.DATABASE_URL}}` *(automatically links to your Railway Postgres database)*
- `TELEGRAM_BOT_TOKEN`: `your-bot-token`
- `TELEGRAM_ALLOWED_USER_IDS`: `your-numeric-id`
- `OPENROUTER_API_KEY`: `your-openrouter-key`
- `OPENROUTER_MODEL`: `openai/gpt-oss-120b`
- `OPENROUTER_FALLBACK_MODEL`: `meta-llama/llama-3.3-70b-instruct`
- `ENCRYPTION_KEY`: `your-fernet-key`
- `TAVILY_API_KEY`: `your-tavily-key`
- `PERPLEXITY_API_KEY`: `your-perplexity-key`
- `APP_ENV`: `production`
- `APP_TIMEZONE`: `Africa/Lagos`

*(If using Gmail)*:
- `GOOGLE_CLIENT_ID`: `your-google-client-id`
- `GOOGLE_CLIENT_SECRET`: `your-google-client-secret`
- `GOOGLE_REDIRECT_URI`: `https://<your-railway-app>.railway.app/oauth/google/callback`

### Step 4: Generate Public Domain
1. In the application service, go to **Settings > Networking > Generate Domain**.
2. Copy your public domain (e.g., `https://assistant-production-xxxx.up.railway.app`).
3. If using Gmail, paste `https://<domain>/oauth/google/callback` into Google Cloud Console under **Authorized redirect URIs**.

### Step 5: Verify Deployment
- Open `https://<domain>/health/live` in your browser (should return `{"status": "live"}`).
- Open `https://<domain>/health/ready` (should return `{"status": "ready", "database": "connected"}`).
- Open your Telegram bot and send `/start`.

---

## 8. Telegram Commands Cheat Sheet

| Command | Usage Example |
| :--- | :--- |
| `/start` | Welcome and quick action buttons |
| `/help` | List of all commands and usage notes |
| `/status` | Check system diagnostics, budget usage, and integration health |
| `/search` | `/search latest news on AI agents` |
| `/remember` | `/remember I have 5 years experience with FastAPI and PostgreSQL` |
| `/memory` | Inspect facts, categories, and uploaded documents |
| `/forget` | `/forget <memory-id>` to permanently delete a fact |
| `/upload` | Instructions for uploading CVs or PDFs for semantic search |
| `/jobs` | `/jobs Senior Python AI Engineer remote` |
| `/gmail` | Summarize unread emails in inbox |
| `/draft` | `/draft recruiter@company.com \| Interview Acceptance \| Thank you for the offer...` |
| `/remind` | `/remind 2026-10-22T09:00:00Z \| Follow up on contract` |
| `/tasks` | View all active and scheduled reminders |
| `/cancel` | `/cancel <reminder-id>` |

You can also send documents directly (PDF/DOCX/TXT/CSV), send voice notes to transcribe and process, send photos to analyze, or ask questions in ordinary conversational language.
