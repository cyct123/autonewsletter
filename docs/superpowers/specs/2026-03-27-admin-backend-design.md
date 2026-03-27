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
- HTTP Basic Auth 保护所有管理入口
- 运营配置支持后台实时修改并立即生效，无需重启

---

## 技术选型

**SQLAdmin**（推荐）：与现有 SQLAlchemy async 模型直接集成，自动生成 CRUD 界面，挂载到 `/admin`，支持自定义操作按钮。

**新增依赖**：`sqladmin`

---

## 架构

### 目录结构变更

```
app/
  admin/
    __init__.py            ← 初始化 Admin 实例，注册所有 View
    views/
      source.py            ← 内容源管理
      subscriber.py        ← 订阅者管理
      content.py           ← 内容查看（只读+删除）
      send_log.py          ← 发送日志（只读）
      system_config.py     ← 系统设置页（自定义 BaseView）
  models/
    system_config.py       ← 新增：运营配置单行表
  main.py                  ← 挂载 Admin，加 Basic Auth，app.state.scheduler
requirements.txt           ← 新增 sqladmin
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

**HTTP Basic Auth**，通过 FastAPI middleware 实现，保护 `/admin/*` 和 `/trigger`。

```
保护范围：GET /admin/*、POST /trigger
公开接口：GET /health、GET /
```

**配置（写入 .env）：**
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

### system_config 表（新增）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，固定为 1 |
| weekly_cron | String | 调度表达式，默认 "0 9 * * 3" |
| ai_model | String | "deepseek" \| "openai"，默认 "deepseek" |
| default_max_items_per_run | Integer | 每次抓取默认条数，默认 5 |
| force_recent | Boolean | 是否跳过去重，默认 False |

**单行表约束**：
- 启动时 `get_or_create`，默认值来自当前 `settings.*`
- 后台禁止新增/删除，只允许编辑
- 保存 `weekly_cron` 后自动触发 scheduler 重载

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

### UUID 类型一致性

迁移后统一使用 `UUID(as_uuid=True)`，业务层不做字符串/UUID 手动转换。

---

## Scheduler 重载机制

### app.state.scheduler

`app/main.py` lifespan 中将 scheduler 实例挂载到 `app.state`：

```python
app.state.scheduler = scheduler
```

### 保存 weekly_cron 后重载

在 `SystemConfigAdmin` 的 `after_model_change` 钩子中执行：

```python
async def after_model_change(self, data, model, is_created, request):
    scheduler = request.app.state.scheduler
    if scheduler is None:
        return  # 兜底：scheduler 不存在时跳过热更新
    new_cron = model.weekly_cron
    try:
        trigger = CronTrigger.from_crontab(new_cron)
        scheduler.reschedule_job("weekly_newsletter", trigger=trigger)
    except Exception:
        pass  # cron 校验在保存前已完成，此处不应失败
```

### cron 表达式校验

保存前在 `on_model_change` 中校验：

```python
async def on_model_change(self, data, model, is_created, request):
    try:
        CronTrigger.from_crontab(data["weekly_cron"])
    except Exception:
        raise ValueError("cron 表达式格式无效")
```

校验失败时不写库、不动 scheduler。

### scheduler 不存在时的兜底

若 `app.state.scheduler` 为 `None`（如测试环境），跳过热更新，仅写库，并在日志中记录警告。

---

## RSS_FEEDS 初始化导入

### 执行时机

在 `app/main.py` lifespan 中，**scheduler.start() 之前**执行：

```
1. 检查 sources 表是否为空
2. 若为空且 settings.rss_feeds 非空，批量导入
3. 之后不再作为运行时 fallback
```

### 代码变更

- `app/modules/sources.py`：删除 `list_sources` 中的 `.env` 回退逻辑（当前第 24 行附近）
- `app/main.py`：lifespan 中新增 `init_sources_from_env()` 调用

---

## ai_model 配置优先级

当前 `app/services/ai.py` 以 API key 存在性决定使用哪个模型（`deepseek_api_key` 有值则用 DeepSeek）。

变更后：优先读取 `system_config.ai_model`，再 fallback 到 key 存在性检测。

```python
config = await get_system_config(db)
if config.ai_model == "openai" and settings.openai_api_key:
    # 使用 OpenAI
elif settings.deepseek_api_key:
    # 使用 DeepSeek（默认）
```

---

## Admin Views 权限设计

| View | 可操作 | 备注 |
|------|--------|------|
| SourceAdmin | 增/改/删/查 | 删除前检查是否有关联 Content（RESTRICT 会报错）|
| SubscriberAdmin | 增/改/删/查 | 删除前检查是否有关联 SendLog |
| ContentAdmin | 查/删 | 不允许手动创建/编辑，由 pipeline 生成 |
| SendLogAdmin | 查 | 只读，不允许任何写操作 |
| SystemConfigAdmin | 改 | 单行，禁止新增/删除，保存后触发 scheduler 重载 |

---

## 启动顺序

```
lifespan 启动：
1. init_sources_from_env()   ← RSS_FEEDS 初始化导入
2. get_or_create_system_config()  ← system_config 单行初始化
3. scheduler = setup_scheduler()  ← 读取 system_config.weekly_cron 建立 job
4. app.state.scheduler = scheduler
5. scheduler.start()
6. if settings.immediate_run: run_weekly_newsletter()
```

---

## 数据库迁移

新增一个 Alembic 迁移文件，包含：

1. `system_config` 表创建
2. `contents.source_id` 加 ForeignKey 约束（`RESTRICT`）
3. `send_logs.subscriber_id` 加 ForeignKey 约束（`RESTRICT`）

迁移前需执行孤立数据检查（见上文）。

---

## 改动文件清单

| 文件 | 改动 |
|------|------|
| `requirements.txt` | 新增 `sqladmin` |
| `app/config.py` | 新增 `admin_user`、`admin_pass` |
| `.env.example` | 新增 `ADMIN_USER`、`ADMIN_PASS` |
| `app/main.py` | 挂载 Admin、Basic Auth middleware、app.state.scheduler、init_sources_from_env |
| `app/models/source.py` | 新增 `relationship` |
| `app/models/content.py` | `source_id` 加 ForeignKey，新增 `relationship` |
| `app/models/subscriber.py` | 新增 `relationship` |
| `app/models/send_log.py` | `subscriber_id` 加 ForeignKey，新增 `relationship` |
| `app/models/system_config.py` | 新增文件：单行配置模型 |
| `app/modules/sources.py` | 删除运行时 `.env` fallback |
| `app/services/ai.py` | 改为读取 `system_config.ai_model` 决定模型选择 |
| `app/admin/__init__.py` | 新增：Admin 初始化 |
| `app/admin/views/source.py` | 新增：SourceAdmin View |
| `app/admin/views/subscriber.py` | 新增：SubscriberAdmin View |
| `app/admin/views/content.py` | 新增：ContentAdmin View（只读+删除）|
| `app/admin/views/send_log.py` | 新增：SendLogAdmin View（只读）|
| `app/admin/views/system_config.py` | 新增：SystemConfigAdmin（设置页，含 cron 重载）|
| `alembic/versions/` | 新增迁移：FK 约束 + system_config 表 |

---

## 验证方案

1. `docker-compose build app && docker-compose up -d app`
2. 访问 `http://localhost:8000/admin`，确认弹出 Basic Auth 对话框
3. 使用 `.env` 中的 `ADMIN_USER/ADMIN_PASS` 登录
4. 在内容源管理页添加一个新 RSS 源，确认数据库有记录
5. 在系统设置页修改 `weekly_cron`，确认 scheduler 日志显示 job 已重新调度
6. 执行 `curl -X POST -u admin:pass http://localhost:8000/trigger`，确认 Basic Auth 生效
7. 执行 `curl http://localhost:8000/health`，确认无需认证
