# Admin Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SQLAdmin web UI at `/admin` for managing sources, subscribers, AI config, and the cron schedule, protected by session login; protect `/trigger` with HTTP Basic Auth; move four operational settings into a `system_config` DB table for live editing without restart.

**Architecture:** SQLAdmin is mounted directly in `main.py` (to avoid circular imports) with a custom `AuthenticationBackend` that validates credentials against `.env`-configured `ADMIN_USER`/`ADMIN_PASS` and stores a session cookie via Starlette `SessionMiddleware`. A new `system_config` single-row table holds `weekly_cron`, `ai_model`, `force_recent`, `default_max_items_per_run`; the pipeline reads from it at runtime rather than from `.env`. FK constraints tie `Content.source_id → sources.id` and `SendLog.subscriber_id → subscribers.id` with `RESTRICT` deletion policy.

**Tech Stack:** FastAPI, SQLAdmin ≥ 0.16.0, SQLAlchemy 2 async, APScheduler 3, Alembic, structlog, Starlette SessionMiddleware

---

## Pre-flight: check for orphaned data

Before any code changes, run these SQL queries in the live DB. If counts > 0, clean up before running migrations.

```bash
docker-compose exec db psql -U autonews -d autonews -c \
  "SELECT COUNT(*) FROM contents WHERE source_id NOT IN (SELECT id FROM sources);"
docker-compose exec db psql -U autonews -d autonews -c \
  "SELECT COUNT(*) FROM send_logs WHERE subscriber_id NOT IN (SELECT id FROM subscribers);"
```

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `requirements.txt` | Modify | Add `sqladmin>=0.16.0` |
| `environment.yml` | Modify | Add `sqladmin>=0.16.0` |
| `.env.example` | Modify | Add admin credential vars |
| `app/config.py` | Modify | Add `admin_user`, `admin_pass`, `admin_session_secret` |
| `app/models/system_config.py` | **Create** | `SystemConfig` ORM model (Integer PK) |
| `app/repositories/system_config.py` | **Create** | `get_system_config`, `get_or_create_system_config` |
| `app/models/source.py` | Modify | Add `contents` relationship |
| `app/models/content.py` | Modify | Add FK on `source_id`, add `source` relationship |
| `app/models/subscriber.py` | Modify | Add `send_logs` relationship |
| `app/models/send_log.py` | Modify | Add FK on `subscriber_id`, add `subscriber` relationship |
| `alembic/env.py` | Modify | Import `SystemConfig` so autogenerate sees it |
| `alembic/versions/<hash>_admin_backend.py` | **Create** | Migration: system_config table + two FK constraints |
| `app/modules/sources.py` | Modify | Add `init_sources_from_env`; remove `.env` runtime fallback |
| `app/services/ai.py` | Modify | Add `db` param to `summarize` and `translate_title`; read `ai_model` from DB |
| `app/modules/summarization.py` | Modify | Thread `db` through wrapper functions |
| `app/jobs/weekly_newsletter.py` | Modify | `setup_scheduler(weekly_cron)` signature; read system_config at pipeline start; remove dead guard |
| `app/admin/__init__.py` | **Create** | Empty package marker |
| `app/admin/auth.py` | **Create** | `AdminAuth` (session cookie login) |
| `app/admin/views/__init__.py` | **Create** | Empty package marker |
| `app/admin/views/source.py` | **Create** | `SourceAdmin` full CRUD |
| `app/admin/views/subscriber.py` | **Create** | `SubscriberAdmin` full CRUD |
| `app/admin/views/content.py` | **Create** | `ContentAdmin` read+delete only |
| `app/admin/views/send_log.py` | **Create** | `SendLogAdmin` read-only |
| `app/admin/views/system_config.py` | **Create** | `SystemConfigAdmin` edit-only + cron hot-reload |
| `app/main.py` | Modify | Mount Admin + middlewares; update lifespan init sequence |
| `tests/conftest.py` | **Create** | Shared pytest fixtures (PostgreSQL test DB) |
| `tests/test_trigger_auth.py` | **Create** | Smoke tests for `TriggerAuthMiddleware` (written in Task 8, requires main.py) |
| `tests/test_system_config_repo.py` | **Create** | Unit tests for `get_system_config` / `get_or_create_system_config` |
| `tests/test_sources_module.py` | **Create** | Unit tests for `init_sources_from_env` |
| `tests/test_admin_auth.py` | **Create** | Unit tests for `AdminAuth` |

---

## Task 1: Dependencies and Config

**Files:**
- Modify: `requirements.txt`
- Modify: `environment.yml`
- Modify: `.env.example`
- Modify: `app/config.py`
- Create: `tests/conftest.py`

- [ ] **Step 1.1: Add sqladmin and test dependencies to requirements.txt**

  Open `requirements.txt` and add after the `alembic` line:
  ```
  sqladmin>=0.16.0
  pytest==8.1.0
  pytest-asyncio==0.23.5
  ```

- [ ] **Step 1.2: Add sqladmin and test dependencies to environment.yml**

  Find the `pip:` section in `environment.yml` and add under it:
  ```yaml
    - sqladmin>=0.16.0
    - pytest==8.1.0
    - pytest-asyncio==0.23.5
  ```

- [ ] **Step 1.3: Add admin vars to .env.example**

  Append to `.env.example` (after the LOG_FORMAT section):
  ```
  # ============================================
  # Admin Backend
  # ============================================
  ADMIN_USER=admin
  ADMIN_PASS=change_me_strong_password
  ADMIN_SESSION_SECRET=change_me_random_secret_string

  # Test database (separate from production DB)
  TEST_DATABASE_URL=postgresql+asyncpg://autonews:autonews@db/autonews_test
  ```

- [ ] **Step 1.4: Add admin fields to Settings**

  In `app/config.py`, add three fields inside `class Settings` after `log_format`:
  ```python
  # Admin
  admin_user: str = "admin"
  admin_pass: str = ""
  admin_session_secret: str = ""
  ```

- [ ] **Step 1.5: Create tests/conftest.py**

  The project models use PostgreSQL-specific types (UUID, ARRAY, JSONB) that are not
  supported by SQLite. Tests must run against a real PostgreSQL instance.
  Run tests inside the app container: `docker-compose exec app pytest`

  ```python
  # tests/conftest.py
  import os
  import pytest
  import pytest_asyncio
  from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
  from app.database import Base
  from app.config import settings

  # Import existing models so Base.metadata includes them.
  # SystemConfig is added to this file in Task 2 Step 2.3a (after the model is created).
  from app.models.source import Source
  from app.models.content import Content
  from app.models.subscriber import Subscriber
  from app.models.send_log import SendLog

  # Derive test DB URL: use TEST_DATABASE_URL env var if set,
  # otherwise append "_test" to the production database name.
  _prod_url = settings.database_url
  TEST_DB_URL = os.environ.get(
      "TEST_DATABASE_URL",
      _prod_url.rsplit("/", 1)[0] + "/" + _prod_url.rsplit("/", 1)[1] + "_test",
  )


  @pytest_asyncio.fixture
  async def db():
      """Async DB session backed by a real PostgreSQL test database.
      Creates all tables before each test, drops them after — no persistent state.
      Requires TEST_DATABASE_URL to point to an existing (empty) PostgreSQL database.
      """
      engine = create_async_engine(TEST_DB_URL, echo=False)
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.create_all)
      session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
      async with session_factory() as session:
          yield session
      async with engine.begin() as conn:
          await conn.run_sync(Base.metadata.drop_all)
      await engine.dispose()
  ```

- [ ] **Step 1.6: Create test database on the PostgreSQL server**

  The test database must exist before pytest can connect. Run once:
  ```bash
  docker-compose exec db psql -U autonews -c "CREATE DATABASE autonews_test;"
  ```
  Expected: `CREATE DATABASE`

  Add `TEST_DATABASE_URL` to your local `.env` file (copy the value from `.env.example`).

- [ ] **Step 1.7: Install deps and verify config loads**

  ```bash
  pip install "sqladmin>=0.16.0" pytest==8.1.0 pytest-asyncio==0.23.5
  python -c "from app.config import settings; print(settings.admin_user)"
  ```
  Expected output: `admin`

- [ ] **Step 1.8: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add requirements.txt environment.yml .env.example app/config.py tests/conftest.py
  git commit -m "feat(admin): add sqladmin dep, admin config fields, and test infrastructure"
  ```

---

## Task 2: SystemConfig Model and Repository

**Files:**
- Create: `app/models/system_config.py`
- Create: `app/repositories/system_config.py`
- Create: `tests/test_system_config_repo.py`

- [ ] **Step 2.1: Write failing tests**

  Create `tests/test_system_config_repo.py`:
  ```python
  # tests/test_system_config_repo.py
  import pytest
  import pytest_asyncio
  from app.repositories.system_config import get_system_config, get_or_create_system_config

  pytestmark = pytest.mark.asyncio


  async def test_get_or_create_creates_row(db):
      # Patch settings so the test doesn't depend on the real .env value
      from unittest.mock import patch
      with patch("app.repositories.system_config.settings") as mock_settings:
          mock_settings.weekly_cron = "0 9 * * 3"
          mock_settings.force_recent = False
          config = await get_or_create_system_config(db)
      assert config.id == 1
      assert config.weekly_cron == "0 9 * * 3"
      assert config.ai_model == "deepseek"
      assert config.default_max_items_per_run == 5
      assert config.force_recent is False


  async def test_get_or_create_idempotent(db):
      first = await get_or_create_system_config(db)
      second = await get_or_create_system_config(db)
      assert first.id == second.id


  async def test_get_system_config_after_create(db):
      await get_or_create_system_config(db)
      config = await get_system_config(db)
      assert config.id == 1


  async def test_get_system_config_fallback_creates(db):
      # get_system_config with no existing row should auto-create
      config = await get_system_config(db)
      assert config.id == 1
  ```

- [ ] **Step 2.2: Run tests to confirm they fail**

  ```bash
  pytest tests/test_system_config_repo.py -v
  ```
  Expected: `ModuleNotFoundError` or `ImportError` — model and repo don't exist yet.

- [ ] **Step 2.3: Create app/models/system_config.py**

  ```python
  # app/models/system_config.py
  from sqlalchemy import Column, Integer, String, Boolean
  from app.database import Base


  class SystemConfig(Base):
      __tablename__ = "system_config"

      id = Column(Integer, primary_key=True, default=1)
      weekly_cron = Column(String, nullable=False, default="0 9 * * 3")
      ai_model = Column(String, nullable=False, default="deepseek")
      default_max_items_per_run = Column(Integer, nullable=False, default=5)
      force_recent = Column(Boolean, nullable=False, default=False)
  ```

  Note: primary key is `Integer`, not UUID — this is a single-row config table.

- [ ] **Step 2.3a: Update tests/conftest.py — add SystemConfig import**

  Now that `app/models/system_config.py` exists, make the import explicit. Add one line to
  `tests/conftest.py`, after the `SendLog` import:
  ```python
  from app.models.system_config import SystemConfig
  ```
  This ensures `SystemConfig` is registered with `Base.metadata` before `create_all` runs,
  regardless of test file import order.

- [ ] **Step 2.4: Create app/repositories/system_config.py**

  ```python
  # app/repositories/system_config.py
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select
  from app.models.system_config import SystemConfig
  from app.config import settings


  async def get_system_config(db: AsyncSession) -> SystemConfig:
      """Get system_config row. Falls back to get_or_create if row missing (defensive)."""
      result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
      config = result.scalar_one_or_none()
      if config is None:
          return await get_or_create_system_config(db)
      return config


  async def get_or_create_system_config(db: AsyncSession) -> SystemConfig:
      """Called at startup — guarantees the id=1 row exists and returns it."""
      result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
      config = result.scalar_one_or_none()
      if config is None:
          config = SystemConfig(
              id=1,
              weekly_cron=settings.weekly_cron,
              ai_model="deepseek",
              default_max_items_per_run=5,
              force_recent=settings.force_recent,
          )
          db.add(config)
          await db.commit()
          await db.refresh(config)
      return config
  ```

- [ ] **Step 2.5: Run tests to confirm they pass**

  ```bash
  pytest tests/test_system_config_repo.py -v
  ```
  Expected: all 4 tests PASS.

- [ ] **Step 2.6: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/models/system_config.py app/repositories/system_config.py tests/test_system_config_repo.py
  git commit -m "feat(admin): add SystemConfig model and repository"
  ```

---

## Task 3: Model Relationships and Migration

**Files:**
- Modify: `app/models/source.py` (add `contents` relationship)
- Modify: `app/models/content.py` (add FK + `source` relationship)
- Modify: `app/models/subscriber.py` (add `send_logs` relationship)
- Modify: `app/models/send_log.py` (add FK + `subscriber` relationship)
- Modify: `alembic/env.py` (import SystemConfig)
- Create: `alembic/versions/<hash>_admin_backend.py`

- [ ] **Step 3.1: Update app/models/source.py — add relationship**

  Add at the top of the file after existing imports:
  ```python
  from sqlalchemy.orm import relationship
  ```

  Add after the `updated_at` column inside `class Source`:
  ```python
  contents = relationship("Content", back_populates="source")
  ```

- [ ] **Step 3.2: Update app/models/content.py — add FK and relationship**

  Replace the existing import block and `source_id` line. The full updated file:
  ```python
  # app/models/content.py
  from sqlalchemy import Column, String, Text, Float, DateTime, ARRAY, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import relationship
  from datetime import datetime
  import uuid
  from app.database import Base


  class Content(Base):
      __tablename__ = "contents"

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
      title = Column(Text, nullable=False)
      original_url = Column(Text, nullable=False, unique=True, index=True)
      transcript = Column(Text)
      summary = Column(Text)
      key_points = Column(ARRAY(Text))
      quality_score = Column(Float, default=0.0)
      processed_at = Column(DateTime, default=datetime.utcnow)
      status = Column(String, default="pending")
      created_at = Column(DateTime, default=datetime.utcnow)

      source = relationship("Source", back_populates="contents")
  ```

- [ ] **Step 3.3: Update app/models/subscriber.py — add relationship**

  Add import at top:
  ```python
  from sqlalchemy.orm import relationship
  ```

  Add after `updated_at` column inside `class Subscriber`:
  ```python
  send_logs = relationship("SendLog", back_populates="subscriber")
  ```

- [ ] **Step 3.4: Update app/models/send_log.py — add FK and relationship**

  Full updated file:
  ```python
  # app/models/send_log.py
  from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
  from sqlalchemy.dialects.postgresql import UUID
  from sqlalchemy.orm import relationship
  from datetime import datetime
  import uuid
  from app.database import Base


  class SendLog(Base):
      __tablename__ = "send_logs"

      id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
      subscriber_id = Column(UUID(as_uuid=True), ForeignKey("subscribers.id", ondelete="RESTRICT"), nullable=False)
      channel_type = Column(String, nullable=False)
      success = Column(Boolean, default=False)
      error_message = Column(Text)
      sent_at = Column(DateTime, default=datetime.utcnow)

      subscriber = relationship("Subscriber", back_populates="send_logs")
  ```

- [ ] **Step 3.5: Update alembic/env.py — import SystemConfig**

  After line 12 (`from app.models.send_log import SendLog`), add:
  ```python
  from app.models.system_config import SystemConfig
  ```

- [ ] **Step 3.6: Verify model imports are error-free**

  ```bash
  python -c "from app.models.system_config import SystemConfig; from app.models.content import Content; from app.models.send_log import SendLog; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 3.7: Create Alembic migration**

  ```bash
  docker-compose exec app python -m alembic revision --autogenerate -m "add_system_config_and_fk_constraints"
  ```

  Open the generated file in `alembic/versions/`. Verify it contains:
  - `op.create_table('system_config', ...)` with 5 columns
  - `op.create_foreign_key(...)` from `contents.source_id` → `sources.id`
  - `op.create_foreign_key(...)` from `send_logs.subscriber_id` → `subscribers.id`

  If autogenerate missed any of these, add them manually. Reference structure:

  ```python
  def upgrade() -> None:
      op.create_table(
          'system_config',
          sa.Column('id', sa.Integer(), nullable=False),
          sa.Column('weekly_cron', sa.String(), nullable=False),
          sa.Column('ai_model', sa.String(), nullable=False),
          sa.Column('default_max_items_per_run', sa.Integer(), nullable=False),
          sa.Column('force_recent', sa.Boolean(), nullable=False),
          sa.PrimaryKeyConstraint('id'),
      )
      op.create_foreign_key(
          'fk_contents_source_id',
          'contents', 'sources',
          ['source_id'], ['id'],
          ondelete='RESTRICT'
      )
      op.create_foreign_key(
          'fk_send_logs_subscriber_id',
          'send_logs', 'subscribers',
          ['subscriber_id'], ['id'],
          ondelete='RESTRICT'
      )

  def downgrade() -> None:
      op.drop_constraint('fk_send_logs_subscriber_id', 'send_logs', type_='foreignkey')
      op.drop_constraint('fk_contents_source_id', 'contents', type_='foreignkey')
      op.drop_table('system_config')
  ```

- [ ] **Step 3.8: Apply migration**

  ```bash
  docker-compose exec app python -m alembic upgrade head
  ```
  Expected: migration completes with no errors.

- [ ] **Step 3.9: Verify DB state**

  ```bash
  docker-compose exec db psql -U autonews -d autonews -c "\d system_config"
  docker-compose exec db psql -U autonews -d autonews -c "\d+ contents" | grep source_id
  docker-compose exec db psql -U autonews -d autonews -c "\d+ send_logs" | grep subscriber_id
  ```
  Each should show the constraint.

- [ ] **Step 3.10: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/models/ alembic/
  git commit -m "feat(admin): add FK constraints and model relationships"
  ```

---

## Task 4: sources.py — init_sources_from_env + remove fallback

**Files:**
- Modify: `app/modules/sources.py`
- Create: `tests/test_sources_module.py`

- [ ] **Step 4.1: Write failing tests**

  Create `tests/test_sources_module.py`:
  ```python
  # tests/test_sources_module.py
  import pytest
  from unittest.mock import patch, AsyncMock
  from app.modules.sources import list_sources, init_sources_from_env

  pytestmark = pytest.mark.asyncio


  async def test_list_sources_returns_db_rows(db):
      """list_sources returns DB rows; no fallback to .env"""
      from app.repositories.source import create_source
      await create_source(db, name="Test Feed", url="https://example.com/feed.xml")

      sources = await list_sources(db)
      assert len(sources) == 1
      assert sources[0]["url"] == "https://example.com/feed.xml"


  async def test_list_sources_empty_returns_empty_not_env(db):
      """When DB is empty, list_sources returns [] — never falls back to .env"""
      with patch("app.modules.sources.settings") as mock_settings:
          mock_settings.rss_feeds = "https://should-not-appear.com/feed"
          sources = await list_sources(db)
      assert sources == []


  async def test_init_sources_from_env_imports_when_empty(db):
      """init_sources_from_env populates DB from RSS_FEEDS when sources table is empty"""
      with patch("app.modules.sources.settings") as mock_settings:
          mock_settings.rss_feeds = "https://feed1.com/rss,https://feed2.com/rss"
          await init_sources_from_env(db)

      sources = await list_sources(db)
      assert len(sources) == 2


  async def test_init_sources_from_env_noop_when_not_empty(db):
      """init_sources_from_env does nothing when DB already has sources"""
      from app.repositories.source import create_source
      await create_source(db, name="Existing", url="https://existing.com/feed")

      with patch("app.modules.sources.settings") as mock_settings:
          mock_settings.rss_feeds = "https://new-feed.com/rss"
          await init_sources_from_env(db)

      sources = await list_sources(db)
      assert len(sources) == 1  # still only 1, no new imports


  async def test_init_sources_from_env_noop_when_no_env_feeds(db):
      """init_sources_from_env does nothing when RSS_FEEDS is empty"""
      with patch("app.modules.sources.settings") as mock_settings:
          mock_settings.rss_feeds = ""
          await init_sources_from_env(db)

      sources = await list_sources(db)
      assert sources == []
  ```

- [ ] **Step 4.2: Run tests to confirm they fail**

  ```bash
  pytest tests/test_sources_module.py -v
  ```
  Expected: `test_list_sources_empty_returns_empty_not_env` will PASS (fallback exists but shouldn't) or FAIL — and `init_sources_from_env` will fail with ImportError.

- [ ] **Step 4.3: Rewrite app/modules/sources.py**

  Full replacement:
  ```python
  # app/modules/sources.py
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select, func
  from app.repositories.source import list_sources as repo_list_sources, create_source
  from app.models.source import Source
  from app.config import settings
  from typing import List


  async def list_sources(db: AsyncSession) -> List[dict]:
      """Get active sources from DB. Returns empty list if no sources configured.
      RSS_FEEDS env var is only used at startup for initial import (see init_sources_from_env).
      """
      sources = await repo_list_sources(db)
      return [
          {
              "id": str(source.id),
              "name": source.name,
              "url": source.url,
              "type": source.type,
              "active": source.active,
              "max_items_per_run": source.max_items_per_run,
          }
          for source in sources
      ]


  async def init_sources_from_env(db: AsyncSession) -> None:
      """One-time import: populate sources table from RSS_FEEDS env var if table is empty.
      Called once at application startup before scheduler starts.
      """
      if not settings.rss_feeds:
          return
      count = await db.scalar(select(func.count()).select_from(Source))
      if count > 0:
          return
      for url in settings.rss_feeds.split(","):
          url = url.strip()
          if url:
              await create_source(db, name=url, url=url)
  ```

- [ ] **Step 4.4: Run tests to confirm they pass**

  ```bash
  pytest tests/test_sources_module.py -v
  ```
  Expected: all 5 tests PASS.

- [ ] **Step 4.5: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/modules/sources.py tests/test_sources_module.py
  git commit -m "feat(admin): add init_sources_from_env, remove .env runtime fallback"
  ```

---

## Task 5: ai.py + summarization.py — thread db parameter

**Files:**
- Modify: `app/services/ai.py`
- Modify: `app/modules/summarization.py`

- [ ] **Step 5.1: Update app/services/ai.py — add db param to both functions**

  Replace the entire `app/services/ai.py` file with:

  ```python
  # app/services/ai.py
  import json
  from sqlalchemy.ext.asyncio import AsyncSession
  from openai import AsyncOpenAI
  from app.config import settings
  from app.repositories.system_config import get_system_config
  from app.utils.logger import logger


  async def summarize(text: str, db: AsyncSession) -> dict:
      """Generate Chinese summary with key points and quality score"""
      config = await get_system_config(db)

      if config.ai_model == "openai" and settings.openai_api_key:
          api_key = settings.openai_api_key
          base_url = None
          model = "gpt-4o-mini"
      elif settings.deepseek_api_key:
          if config.ai_model == "openai":
              logger.warning("ai_model_fallback", configured="openai", reason="OPENAI_API_KEY not set, using DeepSeek")
          api_key = settings.deepseek_api_key
          base_url = "https://api.deepseek.com"
          model = "deepseek-chat"
      else:
          logger.warning("no_api_key_configured", message="Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY is set")
          return {
              "summary": text[:300],
              "sentences": [],
              "boldIndices": [],
              "keyPoints": [],
              "qualityScore": 0,
          }

      logger.info("summarize_called", text_length=len(text))
      client = AsyncOpenAI(api_key=api_key, base_url=base_url)

      prompt = """你是中文资讯编辑，按以下标准生成中文内容:
  1) 用中文输出;
  2) 生成3-6句高信息密度的正文，覆盖"发生了什么+背景+影响/所以怎样(so what)";
  3) 至少标记两句为关键判断(boldIndices)，其中一条必须是"so what";
  4) 同时提取3个关键要点;
  5) 给出0-1之间的质量分数;
  结果以以下JSON格式返回: { "sentences": string[], "boldIndices": number[], "keyPoints": string[], "qualityScore": number }
  原文内容: """ + text[:6000]

      logger.info("ai_request_starting", model=model, prompt_length=len(prompt))

      try:
          response = await client.chat.completions.create(
              model=model,
              messages=[{"role": "user", "content": prompt}],
              temperature=0.3
          )

          output = response.choices[0].message.content
          logger.info("ai_response_received", model=model, output_length=len(output), output_preview=output[:200])

          parsed = json.loads(output)
          result = {
              "summary": "".join(parsed.get("sentences", [])),
              "sentences": parsed.get("sentences", []),
              "boldIndices": parsed.get("boldIndices", []),
              "keyPoints": parsed.get("keyPoints", []),
              "qualityScore": float(parsed.get("qualityScore", 0))
          }
          logger.info("ai_summarization_success", model=model, quality_score=result["qualityScore"], key_points_count=len(result["keyPoints"]))
          return result
      except json.JSONDecodeError as e:
          logger.error("ai_json_parse_failed", error=str(e), output=output[:500] if 'output' in locals() else "N/A")
          return {
              "summary": text[:300],
              "sentences": [],
              "boldIndices": [],
              "keyPoints": [],
              "qualityScore": 0.5
          }
      except Exception as e:
          logger.error("ai_summarization_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
          return {
              "summary": text[:300],
              "sentences": [],
              "boldIndices": [],
              "keyPoints": [],
              "qualityScore": 0.5
          }


  async def translate_title(title: str, db: AsyncSession) -> str:
      """Translate English title to Chinese"""
      ascii_count = sum(1 for c in title if ord(c) < 128)
      ascii_ratio = ascii_count / max(len(title), 1)

      logger.info("translate_title_called", title=title[:100], ascii_ratio=ascii_ratio)

      if ascii_ratio < 0.6:
          logger.info("translation_skipped", reason="already_chinese", ascii_ratio=ascii_ratio)
          return title

      config = await get_system_config(db)

      if config.ai_model == "openai" and settings.openai_api_key:
          api_key = settings.openai_api_key
          base_url = None
          model = "gpt-4o-mini"
      elif settings.deepseek_api_key:
          if config.ai_model == "openai":
              logger.warning("ai_model_fallback", configured="openai", reason="OPENAI_API_KEY not set, using DeepSeek")
          api_key = settings.deepseek_api_key
          base_url = "https://api.deepseek.com"
          model = "deepseek-chat"
      else:
          logger.warning("translation_skipped_no_api_key")
          return title

      client = AsyncOpenAI(api_key=api_key, base_url=base_url)
      prompt = f"将以下标题精准翻译为中文标题，保持简洁凝练: {title[:200]}"

      try:
          logger.info("translation_request_starting", model=model)
          response = await client.chat.completions.create(
              model=model,
              messages=[{"role": "user", "content": prompt}],
              temperature=0
          )

          translated = response.choices[0].message.content.strip()
          logger.info("translation_success", original=title, translated=translated)
          return translated or title
      except Exception as e:
          logger.error("title_translation_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
          return title
  ```

- [ ] **Step 5.2: Update app/modules/summarization.py — thread db through wrappers**

  Full replacement:
  ```python
  # app/modules/summarization.py
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.services.ai import summarize, translate_title


  async def summarize_transcript(text: str, db: AsyncSession) -> dict:
      """Generate summary from transcript"""
      return await summarize(text, db)


  async def translate_title_to_chinese(title: str, db: AsyncSession) -> str:
      """Translate title to Chinese if needed"""
      return await translate_title(title, db)
  ```

- [ ] **Step 5.3: Verify import chain is error-free**

  ```bash
  python -c "from app.modules.summarization import summarize_transcript, translate_title_to_chinese; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 5.4: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/services/ai.py app/modules/summarization.py
  git commit -m "feat(admin): thread db through summarize/translate_title for system_config ai_model"
  ```

---

## Task 6: weekly_newsletter.py — pipeline updates

**Files:**
- Modify: `app/jobs/weekly_newsletter.py`

Changes: `setup_scheduler` signature, read `system_config` at pipeline start, pass `db` to summarization calls, remove dead `if source.get("id"):` guard.

- [ ] **Step 6.1: Update setup_scheduler signature**

  Find `def setup_scheduler():` (near end of file). Replace the entire function:
  ```python
  def setup_scheduler(weekly_cron: str) -> AsyncIOScheduler:
      """Configure APScheduler for weekly newsletter.
      weekly_cron is read from system_config at startup — not from settings directly.
      """
      scheduler = AsyncIOScheduler()
      trigger = CronTrigger.from_crontab(weekly_cron)
      scheduler.add_job(
          run_weekly_newsletter,
          trigger,
          id="weekly_newsletter",
          name="Weekly Newsletter Generation",
          misfire_grace_time=3600,
      )
      logger.info("scheduler_configured", cron=weekly_cron)
      return scheduler
  ```

- [ ] **Step 6.2: Add system_config import to weekly_newsletter.py**

  Add after the existing imports:
  ```python
  from app.repositories.system_config import get_system_config
  ```

- [ ] **Step 6.3: Update run_weekly_newsletter — read system_config, replace settings refs**

  Inside `async with AsyncSessionLocal() as db:`, add these lines immediately after the `try:` statement (before `sources = await list_sources(db)`):
  ```python
  config = await get_system_config(db)
  default_max = config.default_max_items_per_run
  force_recent = config.force_recent
  ```

  Then:
  - Replace `source.get("max_items_per_run", 5)` with:
    ```python
    source.get("max_items_per_run") if source.get("max_items_per_run") is not None else default_max
    ```
  - Replace `settings.force_recent` (line ~50) with `force_recent`
  - Replace `await summarize_transcript(text)` with `await summarize_transcript(text, db=db)`
  - Replace `await translate_title_to_chinese(item["title"])` with `await translate_title_to_chinese(item["title"], db=db)`

- [ ] **Step 6.4: Remove dead if source.get("id"): guard**

  Find the block around line 113:
  ```python
  # Insert into database
  if source.get("id"):
      try:
          await insert_content(db, content)
  ```

  The `if source.get("id"):` guard is dead code after the fallback removal — list_sources now always returns DB sources with valid UUIDs. Remove the outer `if` and keep the `try/except`:
  ```python
  # Insert into database — keep try/except: FK violation possible if source deleted mid-run
  try:
      await insert_content(db, content)
      logger.info("content_inserted_to_db", url=item["url"])
  except Exception as e:
      logger.error("content_insert_failed", url=item["url"], error=str(e), exc_info=True)
  ```

- [ ] **Step 6.5: Verify the file parses without error**

  ```bash
  python -c "from app.jobs.weekly_newsletter import setup_scheduler, run_weekly_newsletter; print('OK')"
  ```
  Expected: `OK`

- [ ] **Step 6.6: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/jobs/weekly_newsletter.py
  git commit -m "feat(admin): update pipeline to read system_config; fix setup_scheduler signature"
  ```

---

## Task 7: Admin Package — Auth and Views

**Files:**
- Create: `app/admin/__init__.py`
- Create: `app/admin/auth.py`
- Create: `app/admin/views/__init__.py`
- Create: `app/admin/views/source.py`
- Create: `app/admin/views/subscriber.py`
- Create: `app/admin/views/content.py`
- Create: `app/admin/views/send_log.py`
- Create: `app/admin/views/system_config.py`
- Create: `tests/test_admin_auth.py`

- [ ] **Step 7.1: Write failing tests for AdminAuth**

  Create `tests/test_admin_auth.py`:
  ```python
  # tests/test_admin_auth.py
  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch
  from app.admin.auth import AdminAuth

  pytestmark = pytest.mark.asyncio


  async def test_authenticate_returns_true_when_token_set():
      auth = AdminAuth(secret_key="test")
      request = MagicMock()
      request.session = {"token": "authenticated"}
      assert await auth.authenticate(request) is True


  async def test_authenticate_returns_false_when_no_token():
      auth = AdminAuth(secret_key="test")
      request = MagicMock()
      request.session = {}
      assert await auth.authenticate(request) is False


  async def test_login_succeeds_with_correct_credentials():
      auth = AdminAuth(secret_key="test")
      request = AsyncMock()
      request.session = {}
      form_data = {"username": "admin", "password": "secret"}
      request.form = AsyncMock(return_value=form_data)

      with patch("app.admin.auth.settings") as mock_settings:
          mock_settings.admin_user = "admin"
          mock_settings.admin_pass = "secret"
          result = await auth.login(request)

      assert result is True
      assert request.session["token"] == "authenticated"


  async def test_login_fails_with_wrong_password():
      auth = AdminAuth(secret_key="test")
      request = AsyncMock()
      request.session = {}
      form_data = {"username": "admin", "password": "wrong"}
      request.form = AsyncMock(return_value=form_data)

      with patch("app.admin.auth.settings") as mock_settings:
          mock_settings.admin_user = "admin"
          mock_settings.admin_pass = "secret"
          result = await auth.login(request)

      assert result is False
      assert "token" not in request.session


  async def test_logout_clears_session():
      auth = AdminAuth(secret_key="test")
      request = MagicMock()
      request.session = {"token": "authenticated"}
      await auth.logout(request)
      assert request.session == {}
  ```

- [ ] **Step 7.2: Run tests to confirm they fail**

  ```bash
  pytest tests/test_admin_auth.py -v
  ```
  Expected: `ImportError` — `app.admin.auth` doesn't exist yet.

- [ ] **Step 7.3: Create app/admin/__init__.py**

  ```python
  # app/admin/__init__.py
  ```
  (empty file — package marker only)

- [ ] **Step 7.4: Create app/admin/auth.py**

  ```python
  # app/admin/auth.py
  from sqladmin.authentication import AuthenticationBackend
  from starlette.requests import Request
  from app.config import settings


  class AdminAuth(AuthenticationBackend):
      async def authenticate(self, request: Request) -> bool:
          """Called by SQLAdmin on each /admin/* request. Return False → redirect to /admin/login."""
          return request.session.get("token") == "authenticated"

      async def login(self, request: Request) -> bool:
          form = await request.form()
          if (form.get("username") == settings.admin_user
                  and form.get("password") == settings.admin_pass):
              request.session["token"] = "authenticated"
              return True
          return False

      async def logout(self, request: Request) -> bool:
          request.session.clear()
          return True
  ```

- [ ] **Step 7.5: Run auth tests to confirm they pass**

  ```bash
  pytest tests/test_admin_auth.py -v
  ```
  Expected: all 5 PASS.

- [ ] **Step 7.6: Create app/admin/views/__init__.py**

  ```python
  # app/admin/views/__init__.py
  ```
  (empty)

- [ ] **Step 7.7: Create app/admin/views/source.py**

  ```python
  # app/admin/views/source.py
  from sqladmin import ModelView
  from app.models.source import Source


  class SourceAdmin(ModelView, model=Source):
      name = "Source"
      name_plural = "Sources"
      icon = "fa-solid fa-rss"

      column_list = [Source.id, Source.name, Source.url, Source.type, Source.active, Source.max_items_per_run]
      column_searchable_list = [Source.name, Source.url]
      column_sortable_list = [Source.name, Source.active]
      column_default_sort = [(Source.name, False)]

      can_create = True
      can_edit = True
      can_delete = True
      can_view_details = True
  ```

- [ ] **Step 7.8: Create app/admin/views/subscriber.py**

  ```python
  # app/admin/views/subscriber.py
  from sqladmin import ModelView
  from app.models.subscriber import Subscriber


  class SubscriberAdmin(ModelView, model=Subscriber):
      name = "Subscriber"
      name_plural = "Subscribers"
      icon = "fa-solid fa-users"

      column_list = [Subscriber.id, Subscriber.identifier, Subscriber.channel_type, Subscriber.active, Subscriber.created_at]
      column_searchable_list = [Subscriber.identifier, Subscriber.channel_type]
      column_sortable_list = [Subscriber.channel_type, Subscriber.active, Subscriber.created_at]
      column_default_sort = [(Subscriber.created_at, True)]

      can_create = True
      can_edit = True
      can_delete = True
      can_view_details = True
  ```

- [ ] **Step 7.9: Create app/admin/views/content.py**

  ```python
  # app/admin/views/content.py
  from sqladmin import ModelView
  from app.models.content import Content


  class ContentAdmin(ModelView, model=Content):
      name = "Content"
      name_plural = "Contents"
      icon = "fa-solid fa-newspaper"

      column_list = [Content.id, Content.title, Content.quality_score, Content.status, Content.processed_at]
      column_searchable_list = [Content.title]
      column_sortable_list = [Content.quality_score, Content.processed_at]
      column_default_sort = [(Content.processed_at, True)]

      # Pipeline generates content — no manual creation or editing
      can_create = False
      can_edit = False
      can_delete = True
      can_view_details = True
  ```

- [ ] **Step 7.10: Create app/admin/views/send_log.py**

  ```python
  # app/admin/views/send_log.py
  from sqladmin import ModelView
  from app.models.send_log import SendLog


  class SendLogAdmin(ModelView, model=SendLog):
      name = "Send Log"
      name_plural = "Send Logs"
      icon = "fa-solid fa-paper-plane"

      column_list = [SendLog.id, SendLog.subscriber_id, SendLog.channel_type, SendLog.success, SendLog.sent_at]
      column_sortable_list = [SendLog.success, SendLog.sent_at]
      column_default_sort = [(SendLog.sent_at, True)]

      # Audit log — fully read-only
      can_create = False
      can_edit = False
      can_delete = False
      can_view_details = True
  ```

- [ ] **Step 7.11: Create app/admin/views/system_config.py**

  ```python
  # app/admin/views/system_config.py
  import structlog
  from sqladmin import ModelView
  from sqladmin.exceptions import FormValidationError
  from apscheduler.triggers.cron import CronTrigger
  from app.models.system_config import SystemConfig

  logger = structlog.get_logger()


  class SystemConfigAdmin(ModelView, model=SystemConfig):
      name = "System Config"
      name_plural = "System Config"
      icon = "fa-solid fa-gear"

      column_list = [
          SystemConfig.weekly_cron,
          SystemConfig.ai_model,
          SystemConfig.default_max_items_per_run,
          SystemConfig.force_recent,
      ]

      # Single-row config — no creation or deletion
      can_create = False
      can_edit = True
      can_delete = False
      can_view_details = True

      async def on_model_change(self, data, model, is_created, request):
          """Validate cron expression before saving. Raises FormValidationError on invalid input."""
          try:
              CronTrigger.from_crontab(data["weekly_cron"])
          except Exception:
              raise FormValidationError({"weekly_cron": "cron expression is invalid"})

      async def after_model_change(self, data, model, is_created, request):
          """Hot-reload the APScheduler job after weekly_cron is saved."""
          scheduler = getattr(request.app.state, "scheduler", None)
          if scheduler is None:
              logger.warning("scheduler_not_found",
                             reason="app.state.scheduler not set, skipping hot-reload")
              return
          new_cron = data["weekly_cron"]
          try:
              trigger = CronTrigger.from_crontab(new_cron)
              scheduler.reschedule_job("weekly_newsletter", trigger=trigger)
              logger.info("scheduler_reloaded", weekly_cron=new_cron)
          except Exception as e:
              logger.error("scheduler_reload_failed", error=str(e))
  ```

- [ ] **Step 7.12: Verify all view imports are error-free**

  ```bash
  python -c "
  from app.admin.auth import AdminAuth
  from app.admin.views.source import SourceAdmin
  from app.admin.views.subscriber import SubscriberAdmin
  from app.admin.views.content import ContentAdmin
  from app.admin.views.send_log import SendLogAdmin
  from app.admin.views.system_config import SystemConfigAdmin
  print('OK')
  "
  ```
  Expected: `OK`

- [ ] **Step 7.13: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/admin/ tests/test_admin_auth.py
  git commit -m "feat(admin): add admin package — auth and all model views"
  ```

---

## Task 8: main.py — wire everything together

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_trigger_auth.py`

This is the final integration step. The tests are written FIRST (TDD), but since `TriggerAuthMiddleware` is defined inside `main.py`, they run after the implementation in Step 8.2.

- [ ] **Step 8.1: Write tests/test_trigger_auth.py**

  Create `tests/test_trigger_auth.py`:
  ```python
  # tests/test_trigger_auth.py
  import pytest
  import base64
  from unittest.mock import patch, AsyncMock


  def make_auth_header(user, password):
      token = base64.b64encode(f"{user}:{password}".encode()).decode()
      return {"Authorization": f"Basic {token}"}


  def test_trigger_requires_auth():
      with patch("app.main.settings") as mock_settings:
          mock_settings.admin_user = "admin"
          mock_settings.admin_pass = "secret"
          mock_settings.admin_session_secret = "test"
          from fastapi.testclient import TestClient
          from app.main import app
          client = TestClient(app, raise_server_exceptions=False)
          response = client.post("/trigger")
          assert response.status_code == 401


  def test_trigger_accepts_correct_credentials():
      with patch("app.main.settings") as mock_settings, \
           patch("app.main.run_weekly_newsletter", new_callable=AsyncMock) as mock_run:
          mock_settings.admin_user = "admin"
          mock_settings.admin_pass = "secret"
          mock_settings.admin_session_secret = "test"
          from fastapi.testclient import TestClient
          from app.main import app
          client = TestClient(app, raise_server_exceptions=False)
          response = client.post("/trigger", headers=make_auth_header("admin", "secret"))
          assert response.status_code == 200
          mock_run.assert_called_once()


  def test_health_no_auth_required():
      from fastapi.testclient import TestClient
      from app.main import app
      client = TestClient(app, raise_server_exceptions=False)
      response = client.get("/health")
      assert response.status_code == 200
  ```

- [ ] **Step 8.2: Rewrite app/main.py**

  ```python
  # app/main.py
  import base64
  from contextlib import asynccontextmanager
  from fastapi import FastAPI
  from sqladmin import Admin
  from starlette.middleware.base import BaseHTTPMiddleware
  from starlette.middleware.sessions import SessionMiddleware
  from starlette.responses import Response

  from app.config import settings
  from app.database import engine, AsyncSessionLocal
  from app.jobs.weekly_newsletter import setup_scheduler, run_weekly_newsletter
  from app.modules.sources import init_sources_from_env
  from app.repositories.system_config import get_or_create_system_config
  from app.utils.logger import logger

  from app.admin.auth import AdminAuth
  from app.admin.views.source import SourceAdmin
  from app.admin.views.subscriber import SubscriberAdmin
  from app.admin.views.content import ContentAdmin
  from app.admin.views.send_log import SendLogAdmin
  from app.admin.views.system_config import SystemConfigAdmin


  class TriggerAuthMiddleware(BaseHTTPMiddleware):
      """HTTP Basic Auth protection for POST /trigger only."""

      async def dispatch(self, request, call_next):
          if request.url.path == "/trigger" and request.method == "POST":
              auth = request.headers.get("Authorization", "")
              if not auth.startswith("Basic "):
                  return Response(
                      "Unauthorized", status_code=401,
                      headers={"WWW-Authenticate": "Basic"},
                  )
              try:
                  decoded = base64.b64decode(auth[6:]).decode()
                  username, password = decoded.split(":", 1)
              except Exception:
                  return Response(
                      "Unauthorized", status_code=401,
                      headers={"WWW-Authenticate": "Basic"},
                  )
              if username != settings.admin_user or password != settings.admin_pass:
                  return Response(
                      "Unauthorized", status_code=401,
                      headers={"WWW-Authenticate": "Basic"},
                  )
          return await call_next(request)


  @asynccontextmanager
  async def lifespan(app: FastAPI):
      """Application lifespan management"""
      logger.info("autonewsletter_starting")

      async with AsyncSessionLocal() as db:
          try:
              await init_sources_from_env(db)
          except Exception:
              logger.warning("init_sources_failed")
          config = await get_or_create_system_config(db)

      scheduler = setup_scheduler(weekly_cron=config.weekly_cron)
      app.state.scheduler = scheduler
      scheduler.start()

      if settings.immediate_run:
          logger.info("immediate_run_triggered")
          await run_weekly_newsletter()

      logger.info("scheduler_ready")

      yield

      scheduler.shutdown()
      logger.info("scheduler_stopped")


  app = FastAPI(
      title="AutoNewsletter",
      description="Automated newsletter system with RSS, AI summarization, and multi-channel distribution",
      version="2.0.0",
      lifespan=lifespan,
  )

  # Middleware registration order matters in Starlette (last added = first executed at runtime)
  # SessionMiddleware added first → executes second (provides session for AdminAuth)
  app.add_middleware(
      SessionMiddleware,
      secret_key=settings.admin_session_secret or "changeme-set-ADMIN_SESSION_SECRET",
  )
  # TriggerAuthMiddleware added second → executes first (gates /trigger before session runs)
  app.add_middleware(TriggerAuthMiddleware)

  # Admin — constructed here in main.py to avoid circular import
  authentication_backend = AdminAuth(
      secret_key=settings.admin_session_secret or "changeme-set-ADMIN_SESSION_SECRET"
  )
  admin = Admin(app, engine, authentication_backend=authentication_backend)
  admin.add_view(SourceAdmin)
  admin.add_view(SubscriberAdmin)
  admin.add_view(ContentAdmin)
  admin.add_view(SendLogAdmin)
  admin.add_view(SystemConfigAdmin)


  @app.get("/health")
  async def health_check():
      """Health check endpoint — no auth required"""
      return {"status": "ok", "service": "autonewsletter"}


  @app.post("/trigger")
  async def trigger_newsletter():
      """Manually trigger newsletter generation — requires Basic Auth"""
      logger.info("manual_trigger_requested")
      await run_weekly_newsletter()
      return {"status": "triggered", "message": "Newsletter generation started"}


  @app.get("/")
  async def root():
      return {
          "service": "AutoNewsletter",
          "version": "2.0.0",
          "endpoints": {
              "health": "/health",
              "trigger": "/trigger (POST, requires Basic Auth)",
              "admin": "/admin",
          },
      }
  ```

- [ ] **Step 8.3: Verify main.py imports cleanly**

  ```bash
  python -c "from app.main import app; print('OK')"
  ```
  Expected: `OK` (no ImportError)

- [ ] **Step 8.4: Run TriggerAuthMiddleware tests**

  ```bash
  pytest tests/test_trigger_auth.py -v
  ```
  Expected: all 3 tests PASS.

- [ ] **Step 8.5: Checkpoint (optional — commit if pausing here)**

  ```bash
  git add app/main.py tests/test_trigger_auth.py
  git commit -m "feat(admin): wire Admin, middlewares, and updated lifespan in main.py"
  ```

---

## Task 9: End-to-end verification

- [ ] **Step 9.1: Rebuild and restart**

  ```bash
  docker-compose build app && docker-compose up -d app
  docker-compose logs -f app
  ```
  Watch for: `autonewsletter_starting`, no `ImportError`, `scheduler_ready`.



- [ ] **Step 9.2: Verify /admin redirects to login form**

  ```bash
  curl -v http://localhost:8000/admin
  ```
  Expected: `302` redirect to `/admin/login` (not a `WWW-Authenticate: Basic` 401 header).

- [ ] **Step 9.3: Verify /health is public**

  ```bash
  curl http://localhost:8000/health
  ```
  Expected: `{"status":"ok","service":"autonewsletter"}`

- [ ] **Step 9.4: Verify /trigger requires auth**

  ```bash
  curl -X POST http://localhost:8000/trigger
  ```
  Expected: `401 Unauthorized`

  ```bash
  curl -X POST -u admin:your_strong_password http://localhost:8000/trigger
  ```
  Expected: `{"status":"triggered",...}` (or error from pipeline, but not 401)

- [ ] **Step 9.5: Log in to admin and exercise views**

  Open `http://localhost:8000/admin` in a browser. Log in with `.env` credentials.
  - Add a new RSS source in Sources view — confirm DB record created
  - Open System Config — edit `weekly_cron` to an invalid value, confirm form shows error
  - Edit `weekly_cron` to `0 10 * * 3`, save — check app logs for `scheduler_reloaded`

- [ ] **Step 9.6: Run all tests**

  ```bash
  pytest tests/ -v
  ```
  Expected: all tests pass.

- [ ] **Step 9.7: Checkpoint (optional — final commit)**

  ```bash
  git add .
  git commit -m "feat(admin): complete admin backend implementation"
  ```
