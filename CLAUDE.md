# CLAUDE.md

This file provides guidance to Claude Code when working with AutoNewsletter.

## Project Overview

AutoNewsletter is an automated newsletter system using FastAPI, SQLAlchemy, and APScheduler for RSS content aggregation, AI summarization, and multi-channel distribution.

## Windows Development Environment

**Recommended**: Use WSL2 for the best development experience. See [docs/WSL2-SETUP.md](docs/WSL2-SETUP.md) for detailed setup instructions.

**Alternative**: Windows users can use Git Bash terminal to run project scripts:

1. Install Git for Windows: https://git-scm.com/download/win
2. Open Git Bash terminal (not PowerShell or CMD)
3. Execute all `.sh` scripts in Git Bash

All command examples in documentation use Bash syntax and can be run directly in Git Bash or WSL2.

## Development Commands

### Conda Environment (Recommended)

```bash
# Create and activate conda environment
./conda-setup.sh
conda activate autonewsletter

# Development mode with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Update environment
conda env update -f environment.yml --prune

# Deactivate environment
conda deactivate
```

### Pip (Alternative)

```bash
# Install dependencies
pip install -r requirements.txt

# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Common Commands

```bash
# Force immediate newsletter run
IMMEDIATE_RUN=1 uvicorn app.main:app

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Architecture

### Core Pipeline Flow

The system runs on APScheduler with cron schedule (default: Wednesdays at 9 AM).

**Pipeline stages** (in `app/jobs/weekly_newsletter.py`):

1. **Source Loading**: Fetch active sources from DB or fallback to `RSS_FEEDS` env var
2. **Content Collection**: For each source, fetch RSS items
3. **Transcription**: Extract text from URLs (Whisper service placeholder)
4. **Summarization**: Use DeepSeek/OpenAI for Chinese summaries with quality scores
5. **Title Translation**: Auto-translate English titles to Chinese
6. **Content Selection**: Rank by quality score, select top N items
7. **Distribution**: Send to active subscribers via their preferred channel

### Module Structure

- **`app/models/`**: SQLAlchemy ORM models
  - `source.py`: RSS/podcast sources
  - `content.py`: Processed content with summaries
  - `subscriber.py`: Multi-channel subscribers
  - `send_log.py`: Delivery audit trail

- **`app/repositories/`**: Data access layer
  - `source.py`: Source CRUD operations
  - `content.py`: Content CRUD operations

- **`app/services/`**: External service integrations
  - `ai.py`: DeepSeek/OpenAI for summarization and translation
  - `rss.py`: RSS feed parsing with feedparser
  - `whisper.py`: Audio transcription placeholder
  - `wechat.py`, `pushplus.py`: Channel-specific delivery

- **`app/modules/`**: Business logic
  - `sources.py`: Source management
  - `transcription.py`: Transcription orchestration
  - `summarization.py`: Summarization orchestration
  - `content.py`: Content selection and filtering
  - `subscribers.py`: Subscriber management
  - `distribution.py`: Multi-channel delivery orchestration

- **`app/jobs/`**: Scheduled tasks
  - `weekly_newsletter.py`: Main newsletter generation pipeline

- **`app/utils/`**: Utilities
  - `logger.py`: Structured logging with structlog
  - `newsletter_template.py`: HTML template generation

### Key Design Patterns

**Async/Await**: All I/O operations use asyncio for high performance

**Dependency Injection**: FastAPI's dependency injection for database sessions

**Repository Pattern**: Separate data access from business logic

**Service Layer**: External integrations isolated in services

**Structured Logging**: JSON logs with structlog for better observability

## Environment Variables

Required:
- `DATABASE_URL`: PostgreSQL connection string (must use `postgresql+asyncpg://` for async)
- AI API Key (choose one):
  - `DEEPSEEK_API_KEY`: DeepSeek API key (recommended, cost-effective)
  - `OPENAI_API_KEY`: OpenAI API key (fallback)

Optional:
- `REDIS_URL`: Redis connection string (default: redis://localhost:6379)
- `RSS_FEEDS`: Comma-separated RSS feed URLs
- `WEEKLY_CRON`: Cron expression (default: `0 9 * * 3`)
- `IMMEDIATE_RUN`: Set to `1` to run immediately on startup
- `FORCE_RECENT`: Set to `1` to bypass URL deduplication
- `PG_POOL_SIZE`: PostgreSQL connection pool size (default: 10)
- `LOG_LEVEL`: Logging level (debug/info/warning/error)

Channel-specific:
- `PUSHPLUS_TOKENS`: Comma-separated PushPlus tokens
- `WECHAT_WEBHOOK_URLS`: Comma-separated WeChat webhooks
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`: Email configuration

## Database Schema

Four main tables:
- `sources`: RSS/podcast sources
- `contents`: Processed content with summaries
- `subscribers`: Multi-channel subscribers
- `send_logs`: Delivery audit trail

Use Alembic for migrations:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Testing & Debugging

```bash
# Start services
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Manual trigger
curl -X POST http://localhost:8000/trigger

# View logs
docker-compose logs -f app

# Check database
docker-compose exec db psql -U autonews -d autonews -c "SELECT title, quality_score FROM contents ORDER BY processed_at DESC LIMIT 5;"
```

## API Endpoints

- `GET /`: Service information
- `GET /health`: Health check
- `POST /trigger`: Manually trigger newsletter generation

## Key Features

1. **Unified Stack**: Pure Python, no additional runtimes required
2. **Async Performance**: asyncio + asyncpg for high-performance async I/O
3. **AI Integration**: Native Python AI ecosystem with OpenAI SDK
4. **Simple Deployment**: Single runtime environment
5. **Type Safety**: Pydantic for runtime validation
6. **Structured Logging**: structlog for JSON logs

## Common Tasks

### Add a subscriber

**Method 1: Interactive Python script (Recommended)**

```bash
# In WSL2 with conda environment activated
python add_subscriber.py
```

The script will:
- Show available channels based on your .env configuration
- List existing subscribers
- Guide you through adding a new subscriber interactively

**Method 2: Direct SQL**

Edit `add_subscriber.sql` with your subscriber details, then run:

```bash
docker-compose exec db psql -U autonews -d autonews -f add_subscriber.sql
```

**Method 3: Direct database insert**

```bash
# PushPlus example
docker-compose exec db psql -U autonews -d autonews -c "
INSERT INTO subscribers (id, identifier, channel_type, active, preferences, created_at, updated_at)
VALUES (gen_random_uuid(), 'your_pushplus_token', 'pushplus', true, '{\"maxItemsPerNewsletter\": 10}'::jsonb, NOW(), NOW())
ON CONFLICT (identifier) DO NOTHING;
"

# List subscribers
docker-compose exec db psql -U autonews -d autonews -c "SELECT identifier, channel_type, active FROM subscribers;"
```

**Supported channels:**
- `pushplus`: Requires PUSHPLUS_TOKENS in .env
- `wechat`: Requires WECHAT_WEBHOOK_URLS in .env
- `email`: Requires SMTP configuration in .env
- `lark`: Requires Lark webhook URL

### Add a new RSS source
```python
from app.repositories.source import create_source
from app.database import AsyncSessionLocal

async with AsyncSessionLocal() as db:
    await create_source(db, "Source Name", "https://example.com/feed.xml")
```

### Add a new push channel
1. Create service in `app/services/new_channel.py`
2. Add channel logic to `app/modules/distribution.py`
3. Update subscriber model if needed

### Modify summarization prompt
Edit `app/services/ai.py` - the `summarize()` function contains the prompt.

### Change newsletter template
Edit `app/utils/newsletter_template.py` - the `build_newsletter_html()` function.
