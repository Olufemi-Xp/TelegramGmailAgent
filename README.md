# Production-Ready Personal AI Assistant for Telegram

An autonomous, private, and secure personal AI assistant accessible through Telegram, built for production deployment on **Railway** with persistent PostgreSQL hybrid memory (pgvector), multi-provider research capabilities (Perplexity, Tavily, Google Search), Gmail integration (search, reading, reply drafting), durable reminders, document analysis, voice transcription, vision inspection, and downloadable report generation.

---

## Architecture Overview

```
                                 +-------------------------+
                                 | Telegram Messenger App  |
                                 +------------+------------+
                                              |  aiogram 3.x Long-Polling
                                              v
+-------------------------------------------------------------------------------------------------+
|                                    Personal AI Assistant Core                                   |
|                                                                                                 |
|  +--------------------+    +--------------------+    +--------------------+    +-------------+  |
|  | Security Middleware|--->| Context Builder    |--->| Agent Orchestrator |--->| Tool Registry|  |
|  | - User ID Allowlist|    | - Recent Turns     |    | - OpenRouter LLM   |    | - Validation|  |
|  | - Rate Limiter     |    | - Personal Facts   |    | - Reasoning Loop   |    | - Timeouts  |  |
|  | - Idempotency Check|    | - Semantic Chunks  |    | - Model Fallbacks  |    | - Audit Log |  |
|  +--------------------+    +--------------------+    +--------------------+    +------+------+  |
|                                                                                       |         |
|  +---------------------+  +--------------------+  +--------------------+              |         |
|  | Research Adapters   |  | Gmail OAuth2       |  | File Generator     |<-------------+         |
|  | - Perplexity Sonar  |  | - Read & Summarize |  | - TXT & Markdown    |                       |
|  | - Tavily Search     |  | - Reply Drafting   |  | - CSV Spreadsheets  |                       |
|  | - Google Search API |  | - (Sending Disabled)|  | - PDF & DOCX Reports|                       |
|  +---------------------+  +--------------------+  +--------------------+                        |
|                                                                                                 |
|  +-------------------------------------------------------------------------------------------+  |
|  | FastAPI Application Engine: /health/live, /health/ready, /oauth/google/callback           |  |
|  +-------------------------------------------------------------------------------------------+  |
|  | APScheduler / Durable Task Dispatcher: Periodic atomic reminder delivery to Telegram       |  |
|  +-------------------------------------------------------------------------------------------+  |
+-----------------------------------------------+-------------------------------------------------+
                                                |
                                                v
                   +---------------------------------------------------------+
                   | PostgreSQL 16 + pgvector (Managed Railway Database)     |
                   | - users, conversations, messages, summaries             |
                   | - personal_memories (facts & preferences)               |
                   | - documents & document_chunks (384-dim embeddings)      |
                   | - jobs (SHA-256 fingerprint deduplication)              |
                   | - reminders (atomic delivery claiming)                  |
                   | - oauth_credentials (AES-Fernet encrypted tokens)       |
                   | - tool_executions, telegram_updates, audit_events       |
                   +---------------------------------------------------------+
```

---

## Key Guarantees & Security Model

1. **Default-Deny Authentication:** Access is restricted strictly to numeric Telegram User IDs defined in `TELEGRAM_ALLOWED_USER_IDS`. Any unlisted user is rejected before tools or memory are loaded.
2. **Untrusted Data Boundaries:** Emails, web search results, external URLs, and uploaded files are wrapped in `<<<UNTRUSTED_CONTENT>>>` delimiters. External content cannot override system policies or expand tool permissions.
3. **No-Send Gmail Guarantee:** Sending emails (`messages/send`) is explicitly disabled in code. The assistant can only search, read, summarize, and prepare drafts (`/draft`).
4. **Encrypted Credentials at Rest:** Google OAuth refresh and access tokens are encrypted with symmetric AES-Fernet encryption (`ENCRYPTION_KEY`) before database persistence.
5. **SSRF & URL Protection:** URL reader blocks loopback (`127.0.0.1`), private RFC1918 subnets, link-local addresses, and cloud metadata hostnames (`169.254.169.254`, `metadata.google.internal`).
6. **Cost Controls:** Enforces sliding-window per-user rate limits and daily/monthly budget ceilings (`DAILY_MODEL_BUDGET`, `MONTHLY_MODEL_BUDGET`). Chain-of-thought `<think>` tags are stripped from user-facing answers.

---

## Verified Model Identifiers (OpenRouter)

- **Primary Reasoning Model:** `openai/gpt-oss-120b` (Open-weight 117B MoE reasoning model on OpenRouter).
- **Fallback Model:** `meta-llama/llama-3.3-70b-instruct` or `openai/gpt-4o-mini`.
- **Vision Model:** `openai/gpt-4o-mini` (multimodal image analysis).
- **Embedding Model:** `all-MiniLM-L6-v2` (384-dimensional dense vectors with deterministic local fallback).

---

## Telegram Commands

| Command | Description |
| :--- | :--- |
| `/start` | Welcome overview, capabilities, and quick navigation keyboard |
| `/help` | Complete assistant command reference |
| `/status` | Live health diagnostics and active integrations (secrets redacted) |
| `/search <query>` | Live web research with verified citations and URLs |
| `/memory` | Inspect stored personal facts and document counts |
| `/remember <fact>` | Explicitly save a personal preference or career detail |
| `/forget <id>` | Permanently delete a personal memory record |
| `/upload` | Instructions for uploading CVs, PDFs, and documents |
| `/jobs <query>` | Discover remote jobs or freelance gigs with SHA-256 deduplication |
| `/gmail` | Summarize recent unread emails or connect Google Account |
| `/draft <details>` | Prepare an email draft in Gmail without sending |
| `/remind <time> \| <task>` | Schedule a persistent reminder (ISO 8601 UTC) |
| `/tasks` | List pending reminders and scheduled tasks |
| `/cancel <id>` | Cancel an active reminder |

*Natural language requests (e.g. "Find AI engineer jobs", "What is my background according to my CV?", "Generate a PDF report on clean energy") work seamlessly.*

---

## Project Structure

```
├── app/
│   ├── main.py                     # FastAPI lifespan, bot polling runner, and HTTP entry
│   ├── config.py                   # Pydantic v2 BaseSettings configuration
│   ├── logging_config.py           # Structured logging with secret redaction
│   ├── api/
│   │   ├── health.py               # /health/live and /health/ready endpoints
│   │   └── oauth.py                # /oauth/google/callback Google OAuth flow
│   ├── bot/
│   │   ├── bot.py                  # Bot & Dispatcher factory
│   │   ├── formatting.py           # Safe Telegram message chunking (<4096 chars)
│   │   ├── keyboards.py            # Inline keyboards
│   │   ├── middleware.py           # Security allowlist & update idempotency
│   │   └── handlers/               # Command & message handlers
│   ├── agent/
│   │   ├── orchestrator.py         # Multi-turn reasoning loop & bounded context
│   │   ├── tool_registry.py        # Central tool registry with execution audit
│   │   ├── schemas.py              # Pydantic schemas for all tool inputs
│   │   └── prompts.py              # System prompt and security barriers
│   ├── providers/
│   │   ├── llm/openrouter.py       # OpenRouter client with backoff & fallbacks
│   │   ├── search/                 # Perplexity, Tavily, Google Search adapters
│   │   ├── embeddings/provider.py  # Embedding service (remote + local fallback)
│   │   ├── transcription/          # Audio / voice note transcription
│   │   └── vision/provider.py      # Multimodal image analysis
│   ├── tools/
│   │   ├── web_search.py           # Multi-provider search with TTL cache
│   │   └── url_reader.py           # SSRF-protected article extractor
│   ├── memory/
│   │   ├── service.py              # Personal facts & document memory coordinator
│   │   ├── indexing.py             # PDF/DOCX/TXT/CSV parser & chunker
│   │   ├── retrieval.py            # Semantic vector & keyword retrieval
│   │   └── summarization.py        # Rolling conversation summarizer
│   ├── database/
│   │   ├── models.py               # 14 SQLAlchemy ORM models
│   │   ├── session.py              # Async engine & pgvector initialization
│   │   └── repositories/           # Repositories for all entities
│   ├── scheduler/
│   │   ├── service.py              # Background scheduler loop
│   │   └── jobs.py                 # Atomic claiming & Telegram reminder delivery
│   ├── security/
│   │   ├── authentication.py       # Telegram numeric user ID allowlist
│   │   ├── encryption.py           # AES-Fernet token encryption
│   │   ├── rate_limits.py          # Sliding-window rate limiter & budget tracker
│   │   └── url_safety.py           # SSRF & IP range validation
│   └── services/
│       ├── file_service.py         # TXT, CSV, PDF, DOCX generation
│       ├── gmail_service.py        # Gmail API OAuth2 & drafting (no-send)
│       └── job_service.py          # Opportunity discovery & deduplication
├── alembic/                        # Database migration scripts
├── tests/                          # 34 Automated unit, integration, and E2E tests
├── Dockerfile                      # Production Docker container
├── docker-compose.yml              # Local Docker setup with pgvector PostgreSQL
├── railway.json                    # Railway deployment manifest
├── requirements.txt                # Pinned production dependencies
└── .env.example                    # Documented configuration template
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+ (or Docker & Docker Compose)
- A Telegram account and Bot Token from [@BotFather](https://t.me/BotFather)
- An OpenRouter API Key ([openrouter.ai](https://openrouter.ai))

### 2. Configure Environment
```bash
cp .env.example .env
```
Edit `.env` and fill in:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALLOWED_USER_IDS` (your numeric Telegram ID from `@userinfobot`)
- `OPENROUTER_API_KEY`
- Search keys (`PERPLEXITY_API_KEY` or `TAVILY_API_KEY`)

### 3. Run with Docker Compose (Recommended)
```bash
docker compose up --build
```
This starts:
- PostgreSQL 16 with pgvector extension on port `5432`.
- FastAPI web server and Telegram bot polling on port `8000`.

### 4. Run Directly with Python
```bash
pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. Run the Automated Test Suite
```bash
python -m pytest -v
```

---

## Railway Production Deployment

### 1. Create Project on Railway
1. Go to [Railway.app](https://railway.app) and create a **New Project**.
2. Add a **PostgreSQL** database service.
3. In PostgreSQL service settings or query tab, verify pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 2. Deploy the Assistant
1. Connect this repository to your Railway project.
2. Railway detects `Dockerfile` and `railway.json` automatically.
3. Add the environment variables from your `.env` under the **Variables** tab:
   - `DATABASE_URL`: `${{Postgres.DATABASE_URL}}` (Railway reference)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_ALLOWED_USER_IDS`
   - `OPENROUTER_API_KEY`
   - `OPENROUTER_MODEL`: `openai/gpt-oss-120b`
   - `OPENROUTER_FALLBACK_MODEL`: `meta-llama/llama-3.3-70b-instruct`
   - `ENCRYPTION_KEY`: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (if Gmail enabled)
   - `GOOGLE_REDIRECT_URI`: `https://<your-railway-domain>.railway.app/oauth/google/callback`
   - `TAVILY_API_KEY` / `PERPLEXITY_API_KEY`
4. Deploy the service. Railway will automatically run health checks on `/health/live`.

---

## Verification & Status Checks

- Health liveness: `GET /health/live` (Returns HTTP 200 `{"status": "live"}`)
- Health readiness: `GET /health/ready` (Returns HTTP 200 `{"status": "ready", "database": "connected"}`)
- In Telegram: Send `/status` to view active integrations, database status, and daily budget consumption.
