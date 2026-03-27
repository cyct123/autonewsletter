# 管理后台设计文档

**日期**：2026-03-27
**状态**：待实现

---

## 背景

AutoNewsletter 当前所有配置均通过 `.env` 文件管理，无法在不重启容器的情况下修改内容源、订阅者、AI 模型选择和定时任务调度。`/trigger` 端点无任何保护。需要一个管理后台解决以下问题：

- 内容源、订阅者需手动操作数据库才能增删改
- 调度时间（weekly_cron）修改需重启容器
- `/trigger` 裸露，无身份验证

---

## 目标

- 提供 Web 管理界面，支持内容源、订阅者、AI 配置、定时任务、内容查看、发送日志的管理
- SQLAdmin AuthenticationBackend 保护 `/admin/*`，HTTP Basic Auth 保护 `/trigger`
- 运营配置支持后台实时修改并立即生效，无需重启

---

## 技术选型

**SQLAdmin**（推荐）：与现有 SQLAlchemy async 模型直接集成，自动生成 CRUD 界面，挂载到 `/admin`，支持自定义操作按钮。

**新增依赖**：`sqladmin>=0.16.0`（≥0.16 版本的 `AuthenticationBackend`、`on_model_change`、`after_model_change` 钩子签名与本规范一致）

---

## 架构

### 目录结构变更

```
app/
  admin/
    __init__.py            ← 空文件（包标记）
    auth.py                ← AdminAuth (AuthenticationBackend 实现)
    views/
      __init__.py          ← 空文件（包标记）
      source.py            ← SourceAdmin View
      subscriber.py        ← SubscriberAdmin View
      content.py           ← ContentAdmin View（只读+删除）
      send_log.py          ← SendLogAdmin View（只读）
      system_config.py     ← SystemConfigAdmin View（单行编辑）
  models/
    system_config.py       ← 新增：运营配置单行表
  repositories/
    system_config.py       ← 新增：get_system_config / get_or_create_system_config
  main.py                  ← Admin 在此构建（避免循环导入），挂载 Basic Auth middleware
requirements.txt           ← 新增 sqladmin>=0.16.0
environment.yml            ← 新增 sqladmin>=0.16.0
alembic/versions/          ← 新增迁移：FK 约束 + system_config 表
```

### 访问路径

| 路径 | 说明 |
|------|------|
| `/admin` | 管理后台首页 |
| `/admin/source` | 内容源 CRUD |
| `/admin/subscriber` | 订阅者 CRUD |
| `/admin/content` | 内容列表（只读+删除）|
| `/admin/sendlog` | 发送日志（只读）|
| `/admin/system-config` | 系统设置页 |
| `POST /trigger` | 手动触发（受 Basic Auth 保护）|

---

## 认证方案

两套保护机制，互不干涉：

- **`/admin/*`**：SQLAdmin `AuthenticationBackend`，session cookie 登录。访问 `/admin` 时重定向到登录表单页（非浏览器 Basic Auth 弹窗）。SQLAdmin 自动放行 `/admin/statics/` 静态资源，无需额外配置。
- **`POST /trigger`**：FastAPI `BaseHTTPMiddleware` 校验 HTTP Basic Auth header，仅拦截 `/trigger` 路径，其余路径直通。
- **公开接口**：`GET /health`、`GET /` 不受任何保护。

### app/admin/auth.py

```python
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.config import settings

class AdminAuth(AuthenticationBackend):
    async def authenticate(self, request: Request) -> bool:
        """Called by SQLAdmin on each /admin/* request. Return False → redirect to /admin/login."""
        return request.session.get("token") == "authenticated"

    async def login(self, request: Request) -> bool:
        form = await request.form()
        if form.get("username") == settings.admin_user and form.get("password") == settings.admin_pass:
            request.session["token"] = "authenticated"
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True
```

### Admin 构建位置：app/main.py

**避免循环导入**：`Admin(app, engine)` 需要 FastAPI `app` 实例，而 `app` 定义在 `main.py`。因此 Admin 实例在 `main.py` 中直接构建，而非在 `app/admin/__init__.py`（否则 `admin/__init__.py` 需导入 `main.py` 中的 `app`，造成循环导入）。

```python
# app/main.py
from sqladmin import Admin
from app.database import engine  # async engine，来自 app/database.py
from app.config import settings
from app.admin.auth import AdminAuth
from app.admin.views.source import SourceAdmin
from app.admin.views.subscriber import SubscriberAdmin
from app.admin.views.content import ContentAdmin
from app.admin.views.send_log import SendLogAdmin
from app.admin.views.system_config import SystemConfigAdmin
from starlette.middleware.sessions import SessionMiddleware

# ... FastAPI app 创建 ...

# SessionMiddleware 必须先添加（先加的后执行，提供 session 供后续中间件使用）
app.add_middleware(SessionMiddleware, secret_key=settings.admin_pass or "changeme-set-ADMIN_PASS")
# TriggerAuthMiddleware 后添加（后加的先执行，在 session 初始化前鉴权 /trigger）
app.add_middleware(TriggerAuthMiddleware)
# 运行时执行顺序：TriggerAuthMiddleware → SessionMiddleware → 路由处理

authentication_backend = AdminAuth(secret_key=settings.admin_pass or "changeme-set-ADMIN_PASS")
admin = Admin(app, engine, authentication_backend=authentication_backend)
admin.add_view(SourceAdmin)
admin.add_view(SubscriberAdmin)
admin.add_view(ContentAdmin)
admin.add_view(SendLogAdmin)
admin.add_view(SystemConfigAdmin)
```

### /trigger Basic Auth middleware（app/main.py）

```python
import base64
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class TriggerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/trigger" and request.method == "POST":
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Basic "):
                return Response("Unauthorized", status_code=401,
                                headers={"WWW-Authenticate": "Basic"})
            try:
                decoded = base64.b64decode(auth[6:]).decode()
                username, password = decoded.split(":", 1)
            except Exception:
                return Response("Unauthorized", status_code=401,
                                headers={"WWW-Authenticate": "Basic"})
            if username != settings.admin_user or password != settings.admin_pass:
                return Response("Unauthorized", status_code=401,
                                headers={"WWW-Authenticate": "Basic"})
        return await call_next(request)

app.add_middleware(TriggerAuthMiddleware)
```

### 配置（写入 .env）

```
ADMIN_USER=admin
ADMIN_PASS=your_strong_password
```

`app/config.py` 新增两个字段：
```python
admin_user: str = "admin"
admin_pass: str = ""
```

---

## 配置分层

### 原则

- **system_config 表**：运行时可安全修改且应立即生效的运营配置
- **.env**：基础设施、凭据、启动期参数、以及需重启才稳定生效的配置

### .env（保留）

| 变量 | 说明 |
|------|------|
| DATABASE_URL | 数据库连接 |
| REDIS_URL | Redis 连接 |
| DEEPSEEK_API_KEY / OPENAI_API_KEY | AI 密钥 |
| SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS | 邮件凭据 |
| LARK_WEBHOOK_URL | 飞书 Webhook |
| WECHAT_WEBHOOK_URLS | 微信 Webhook |
| PUSHPLUS_TOKENS | PushPlus Token |
| WHISPER_URL / WHISPER_MODEL / WHISPER_TIMEOUT | Whisper 配置 |
| ADMIN_USER / ADMIN_PASS | 管理员凭据 |
| RSS_FEEDS | 仅初始化导入用，不再作为运行时 fallback |
| IMMEDIATE_RUN | 启动期行为 |
| LOG_FORMAT / LOG_LEVEL | 日志配置（导入时初始化，不支持热更新）|
| WEEKLY_CRON | 保留，仅作 system_config 首次初始化的默认值；启动后以数据库值为准，不再直接读取 |
| FORCE_RECENT | 保留，仅作 system_config 首次初始化的默认值；启动后以数据库值为准 |

`app/config.py` 中的 `weekly_cron` 和 `force_recent` 字段**保留**（用于 `get_or_create_system_config` 的默认值），但 `setup_scheduler()` 和 pipeline 运行时不再直接读取。

### system_config 表（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，固定为 1 |
| weekly_cron | String | 调度表达式，默认 "0 9 * * 3" |
| ai_model | String | "deepseek" \| "openai"，默认 "deepseek" |
| default_max_items_per_run | Integer | 每次抓取默认条数，默认 5 |
| force_recent | Boolean | 是否跳过去重，默认 False |

**`force_recent` 优先级**：`system_config.force_recent` 优先于 `.env FORCE_RECENT`。`.env` 中的 `FORCE_RECENT` 仅作为首次 `get_or_create` 的初始默认值，运行时 pipeline 只读数据库值。

**单行表约束**：
- 启动时 `get_or_create`（id=1），`weekly_cron` 默认值取 `settings.weekly_cron`，`force_recent` 默认值取 `settings.force_recent`，其余字段使用硬编码默认值
- 后台禁止新增/删除，只允许编辑
- 保存 `weekly_cron` 后自动触发 scheduler 重载

---

## system_config 模型与仓储层

### app/models/system_config.py（新增）

```python
from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base  # 与其他模型使用相同的 Base

class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, default=1)
    weekly_cron = Column(String, nullable=False, default="0 9 * * 3")
    ai_model = Column(String, nullable=False, default="deepseek")
    default_max_items_per_run = Column(Integer, nullable=False, default=5)
    force_recent = Column(Boolean, nullable=False, default=False)
```

注：主键使用 `Integer`（非 UUID），与其他模型不同，因为这是单行配置表，固定 id=1。

### app/repositories/system_config.py（新增）

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.system_config import SystemConfig
from app.config import settings

async def get_system_config(db: AsyncSession) -> SystemConfig:
    """获取 system_config 行。调用前须确保 lifespan 已执行 get_or_create_system_config。"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.id == 1))
    config = result.scalar_one_or_none()
    if config is None:
        # 兜底：正常情况下 lifespan 已保证行存在；此处防御性处理避免 NoResultFound
        return await get_or_create_system_config(db)
    return config

async def get_or_create_system_config(db: AsyncSession) -> SystemConfig:
    """启动时调用，保证 id=1 行存在并返回。"""
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

---

## 模型关系补全

当前 `Content.source_id` 和 `SendLog.subscriber_id` 为裸 UUID，需补全外键和关联关系。

### 变更内容

**app/models/content.py**
```python
source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
source = relationship("Source", back_populates="contents")
```

**app/models/source.py**
```python
contents = relationship("Content", back_populates="source")
```

**app/models/send_log.py**
```python
subscriber_id = Column(UUID(as_uuid=True), ForeignKey("subscribers.id", ondelete="RESTRICT"), nullable=False)
subscriber = relationship("Subscriber", back_populates="send_logs")
```

**app/models/subscriber.py**
```python
send_logs = relationship("SendLog", back_populates="subscriber")
```

### 删除策略

`RESTRICT`：禁止删除有关联数据的父记录，避免误删历史数据。

### 迁移前置检查

加外键前需确认无脏数据：
```sql
-- 检查 contents 中的孤立 source_id
SELECT COUNT(*) FROM contents WHERE source_id NOT IN (SELECT id FROM sources);

-- 检查 send_logs 中的孤立 subscriber_id
SELECT COUNT(*) FROM send_logs WHERE subscriber_id NOT IN (SELECT id FROM subscribers);
```

若有脏数据，需先清理再执行迁移。

**部署顺序**：必须先执行 `alembic upgrade head` 完成迁移，再启动应用。

### UUID 类型一致性

迁移后统一使用 `UUID(as_uuid=True)`，业务层不做字符串/UUID 手动转换。

---

## Scheduler 重载机制

### setup_scheduler() 签名变更

**文件**：`app/jobs/weekly_newsletter.py`

当前函数内部读取 `settings.weekly_cron`（约第 164 行）。变更后：

```python
def setup_scheduler(weekly_cron: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_weekly_newsletter,
        CronTrigger.from_crontab(weekly_cron),  # 使用传入参数，不再读 settings.weekly_cron
        id="weekly_newsletter",                  # 保持 id 不变，供 reschedule_job 引用
        name="Weekly Newsletter Generation",     # 保持 name 不变
        misfire_grace_time=3600,                 # 新增：容忍 1 小时内的错过触发
    )
    return scheduler
```

**必须删除**函数体内对 `settings.weekly_cron` 的引用。`misfire_grace_time=3600` 是新增参数（当前代码无此参数），意为：若 job 因系统暂停错过触发时间，1 小时内仍可补运行。

**保留 `insert_content` 的 try/except**：`contents.source_id` 加 FK 约束后，若 pipeline 运行�� source 被管理员删除，`insert_content` 会触发 FK violation。pipeline 现有的 try/except 包裹（约第 113 行）已能捕获此异常并记录 `content_insert_failed`，**不得在清理死代码时删除该保护**。

### 保存 weekly_cron 后重载

在 `SystemConfigAdmin`（`app/admin/views/system_config.py`）的 `after_model_change` 钩子中执行。文件顶部需引入：

```python
from apscheduler.triggers.cron import CronTrigger
from sqladmin.exceptions import FormValidationError
from app.utils.logger import get_logger
logger = get_logger(__name__)
```

```python
async def after_model_change(self, data, model, is_created, request):
    scheduler = request.app.state.scheduler
    if scheduler is None:
        logger.warning("scheduler_not_found", reason="app.state.scheduler is None, skipping hot-reload")
        return
    new_cron = data["weekly_cron"]  # 使用 form data dict，避免 ORM 对象 detached 问题
    try:
        trigger = CronTrigger.from_crontab(new_cron)
        scheduler.reschedule_job("weekly_newsletter", trigger=trigger)
        logger.info("scheduler_reloaded", weekly_cron=new_cron)
    except Exception as e:
        logger.error("scheduler_reload_failed", error=str(e))
```

### cron 表达式校验

保存前在 `on_model_change` 中校验。**必须使用 `FormValidationError`**（`sqladmin.exceptions.FormValidationError`），普通 `ValueError` 不会中止保存，会导致 500：

```python
from sqladmin.exceptions import FormValidationError

async def on_model_change(self, data, model, is_created, request):
    try:
        CronTrigger.from_crontab(data["weekly_cron"])
    except Exception:
        raise FormValidationError({"weekly_cron": "cron expression is invalid"})
```

---

## RSS_FEEDS 初始化导入

### 函数定义位置

**`app/modules/sources.py`** 新增 `init_sources_from_env(db: AsyncSession)` 函数：

```python
async def init_sources_from_env(db: AsyncSession) -> None:
    """仅在 sources 表为空时，从 settings.rss_feeds 批量导入初始数据源。"""
    if not settings.rss_feeds:
        return
    count = await db.scalar(select(func.count()).select_from(Source))
    if count > 0:
        return
    for url in settings.rss_feeds.split(","):
        url = url.strip()
        if url:
            # create_source 签名：(db, name: str, url: str, ...)，name 暂用 url
            await create_source(db, name=url, url=url)
```

### 代码变更

- `app/modules/sources.py`：
  - 新增 `init_sources_from_env(db)` 函数（见上）
  - 删除 `list_sources` 中的 `.env` 回退逻辑（当前第 24 行附近）
  - 同步更新函数 docstring，移除对 `.env` fallback 的描述
  - 删除因 fallback 移除而不再使用的 `settings` 导入（若无其他引用）
- `app/jobs/weekly_newsletter.py`：删除 `if source.get("id"):` 空值保护（fallback 移除后 `list_sources` 不再返回无 id 的记录）

  **部署约束**：`if source.get("id"):` guard 的删除和 FK 迁移必须同时部署——先迁移后部署代码，或迁移与代码同一次部署。迁移完成后 `source_id` 有 NOT NULL + FK 约束，此时 `list_sources` 只返回 DB 中的真实记录（均有有效 id），guard 删除安全。
- `app/main.py`：lifespan 中调用 `await init_sources_from_env(db)`

---

## ai_model 配置优先级

当前 `app/services/ai.py` 以 API key 存在性决定使用哪个模型。

变更后：优先读取 `system_config.ai_model`，再 fallback 到 key 存在性检测。

### db 参数传递

`ai.py` 中的 `summarize()` 和 `translate_title()`（注意：函数名为 `translate_title`，非 `translate`）均需新增 `db: AsyncSession` 参数：

```python
# app/services/ai.py
from app.repositories.system_config import get_system_config

async def summarize(text: str, db: AsyncSession) -> dict:
    config = await get_system_config(db)
    if config.ai_model == "openai" and settings.openai_api_key:
        # 使用 OpenAI
    elif settings.deepseek_api_key:
        # 使用 DeepSeek（默认）
        # 注意：若 ai_model="openai" 但 OPENAI_API_KEY 未配置，会 fallback 到 DeepSeek
        # 此时必须 logger.warning("ai_model_fallback", configured="openai", reason="key_missing")
    else:
        return {}  # 无可用 key：保持与当前代码一致的兜底行为

async def translate_title(title: str, db: AsyncSession) -> str:
    config = await get_system_config(db)
    if config.ai_model == "openai" and settings.openai_api_key:
        # 使用 OpenAI
    elif settings.deepseek_api_key:
        # 使用 DeepSeek（默认）
        # 注意：同上，fallback 时记录 warning
    else:
        return title  # 无可用 key：返回原标题

### 调用链变更

- `app/modules/summarization.py`：`summarize_transcript()`、`translate_title_to_chinese()` 等包装函数新增并透传 `db: AsyncSession` 参数
- `app/jobs/weekly_newsletter.py`：pipeline 的 per-item 循环中（约第 75 行调用 `summarize_transcript`，约第 87 行调用 `translate_title_to_chinese`），将当前 `db` 传入：
  ```python
  summary = await summarize_transcript(transcript, db=db)
  title_zh = await translate_title_to_chinese(item["title"], db=db)
  ```

---

## default_max_items_per_run 与 force_recent 管道接入

当前 pipeline（`app/jobs/weekly_newsletter.py`）：
- 通过 `source.get("max_items_per_run", 5)` 获取每源抓取上限，硬编码默认值 5
- 通过 `settings.force_recent`（约第 50 行）决定是否跳过去重

变更后，pipeline 的 `async with AsyncSessionLocal() as db:` 块内，**在 source 循环之前**，一次性读取 `system_config`：

```python
async def run_weekly_newsletter():
    async with AsyncSessionLocal() as db:
        config = await get_system_config(db)           # ← 在循环前，session 内
        default_max = config.default_max_items_per_run
        force_recent = config.force_recent             # 替换原来约第 50 行的 settings.force_recent

        sources = await list_sources(db)
        for source in sources:
            max_items = source.get("max_items_per_run") if source.get("max_items_per_run") is not None else default_max
            # 使用 is not None 而非 or，允许 per-source 设置为 0 表示"使用默认值"
            # （实际上 0 在语义上等同于默认值；若将来需要"不抓取"语义，应使用负数或单独字段）
            ...
            summary = await summarize_transcript(transcript, db=db)
            title_zh = await translate_title_to_chinese(item["title"], db=db)
```

`get_system_config` 必须在 `async with AsyncSessionLocal() as db:` 块内调用，不可移到块外。

---

## Admin Views 权限设计

### 权限矩阵

| View | can_create | can_edit | can_delete | 备注 |
|------|-----------|---------|-----------|------|
| SourceAdmin | True | True | True | 删除前 DB 层 RESTRICT 报错 |
| SubscriberAdmin | True | True | True | 删除前 DB 层 RESTRICT 报错 |
| ContentAdmin | **False** | **False** | True | 由 pipeline 生成，禁止手动创建/编辑 |
| SendLogAdmin | **False** | **False** | **False** | 完全只读；当前无 content_id 字段，无法关联内容（已知限制）|
| SystemConfigAdmin | **False** | True | **False** | 单行，禁止新增/删除，保存后触发 scheduler 重载 |

`ContentAdmin` 和 `SendLogAdmin` 必须显式设置 `can_create = False`、`can_edit = False`（以及 `can_delete = False` 对 SendLog）。SQLAdmin 默认允许所有操作，不会自动推断。

---

## 启动顺序

以下为 `app/main.py` lifespan 的关键结构（须逐行对照当前代码完成修改）：

```python
# app/main.py lifespan
async with AsyncSessionLocal() as db:
    try:
        await init_sources_from_env(db)                      # 1. RSS_FEEDS 初始化导入
    except Exception:
        logger.warning("init_sources_failed")                # 失败不阻塞启动，继续执行
    config = await get_or_create_system_config(db)           # 2. system_config 单行初始化
# db session 在此关闭。config.weekly_cron 可安全访问——database.py 中
# AsyncSessionLocal 使用 expire_on_commit=False，commit 后属性不失效。

scheduler = setup_scheduler(weekly_cron=config.weekly_cron)  # 3. 用 DB 中的 cron 建立 job
# ↑ 原有无参数调用 setup_scheduler() 必须更新为此形式

app.state.scheduler = scheduler              # 4. 挂载到 app.state（admin 热重载依赖此赋值）
scheduler.start()                            # 5. 启动调度器
if settings.immediate_run:
    await run_weekly_newsletter()            # 6. 立即执行一次（可选）
```

注：`init_sources_from_env` 和 `get_or_create_system_config` 各自在内部 `db.commit()`，共用同一 session 无冲突（均为独立事务）。

---

## 数据库迁移

新增一个 Alembic 迁移文件，包含：

1. `system_config` 表创建
2. `contents.source_id` 加 ForeignKey 约束（`RESTRICT`）
3. `send_logs.subscriber_id` 加 ForeignKey 约束（`RESTRICT`）

迁移前需执行孤立数据检查（见上文）。**应用启动前必须先执行 `alembic upgrade head`**，否则 relationship 查询报错。

---

## 改动文件清单

| 文件 | 改动 |
|------|------|
| `requirements.txt` | 新增 `sqladmin>=0.16.0` |
| `environment.yml` | 新增 `sqladmin>=0.16.0`（conda 环境依赖）|
| `app/config.py` | 新增 `admin_user`、`admin_pass`；`weekly_cron`/`force_recent` 保留但仅供初始化用 |
| `.env.example` | 新增 `ADMIN_USER`、`ADMIN_PASS`（检查是否已存在，避免重复）|
| `app/main.py` | Admin 实例构建（`Admin(app, engine, ...)`）；注册所有 View；`TriggerAuthMiddleware`；`SessionMiddleware`（顺序：SessionMiddleware → TriggerAuthMiddleware → Admin）；lifespan 初始化序列；`app.state.scheduler` |
| `app/models/source.py` | 新增 `relationship` |
| `app/models/content.py` | `source_id` 加 ForeignKey，新增 `relationship` |
| `app/models/subscriber.py` | 新增 `relationship` |
| `app/models/send_log.py` | `subscriber_id` 加 ForeignKey，新增 `relationship` |
| `app/models/system_config.py` | **新增文件**：`SystemConfig` 模型（Integer 主键，非 UUID）|
| `app/repositories/system_config.py` | **新增文件**：`get_system_config` / `get_or_create_system_config` |
| `app/modules/sources.py` | 新增 `init_sources_from_env(db)`；删除运行时 `.env` fallback；更新 docstring；删除死代码导入 |
| `app/services/ai.py` | `summarize()`/`translate_title()` 新增 `db` 参数；从 `system_config.ai_model` 决定模型选择 |
| `app/modules/summarization.py` | 包装函数新增并透传 `db` 参数 |
| `app/jobs/weekly_newsletter.py` | `setup_scheduler(weekly_cron: str)` 签名变更，删除内部 `settings.weekly_cron` 引用；透传 `db` 到 summarization 调用；从 `system_config` 读取 `force_recent`（替换约第 50 行的 `settings.force_recent`）和 `default_max_items_per_run`；删除死代码 `if source.get("id"):` |
| `app/admin/__init__.py` | **新增文件**：空文件（包标记）|
| `app/admin/auth.py` | **新增文件**：`AdminAuth`（`AuthenticationBackend` 实现）|
| `app/admin/views/__init__.py` | **新增文件**：空文件（包标记）|
| `app/admin/views/source.py` | **新增文件**：`SourceAdmin`（增/改/删/查）|
| `app/admin/views/subscriber.py` | **新增文件**：`SubscriberAdmin`（增/改/删/查）|
| `app/admin/views/content.py` | **新增文件**：`ContentAdmin`（`can_create=False, can_edit=False`）|
| `app/admin/views/send_log.py` | **新增文件**：`SendLogAdmin`（`can_create=False, can_edit=False, can_delete=False`）|
| `app/admin/views/system_config.py` | **新增文件**：`SystemConfigAdmin`（`can_create=False, can_delete=False`，含 cron 重载，使用 `FormValidationError`）|
| `alembic/env.py` | 新增 `from app.models.system_config import SystemConfig` 导入（当前文件已显式导入 Source/Content/Subscriber/SendLog，确认后再添加，无需重复）|
| `alembic/versions/` | 新增迁移：FK 约束 + system_config 表 |

---

## 验证方案

1. `alembic upgrade head`（必须先于应用启动）
2. `docker-compose build app && docker-compose up -d app`
3. 访问 `http://localhost:8000/admin`，确认跳转到登录表单页（非 Basic Auth 弹窗）
4. 使用 `.env` 中的 `ADMIN_USER/ADMIN_PASS` 填写登录表单，确认进入管理后台首页
5. 在内容源管理页添加一个新 RSS 源，确认数据库有记录
6. 在系统设置页修改 `weekly_cron` 为无效值，确认前端显示表单校验错误（非 500）
7. 修改 `weekly_cron` 为有效值（如 `0 10 * * 3`），确认 scheduler 日志显示 job 已重新调度
8. 执行 `curl -X POST -u admin:pass http://localhost:8000/trigger`，确认 Basic Auth 生效
9. 执行 `curl http://localhost:8000/health`，确认无需认证
