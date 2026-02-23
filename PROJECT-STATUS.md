# AutoNewsletter - 项目状态

## 当前版本

**纯 Python 实现** - 基于 FastAPI + SQLAlchemy + APScheduler

## 快速开始

> **Windows 用户**: 请使用 Git Bash 终端运行以下命令。

```bash
# 1. Conda 快速设置（推荐）
./conda-setup.sh
conda activate autonewsletter

# 2. 或使用 pip
pip install -r requirements.txt

# 3. 启动数据库
docker-compose up -d db redis
alembic upgrade head

# 4. 运行应用
uvicorn app.main:app --reload

# 5. 验证
curl http://localhost:8000/health
```

## 项目统计

- **33 个 Python 文件** (~900 行代码)
- **4 个数据模型** (Source, Content, Subscriber, SendLog)
- **7 个服务集成** (RSS, AI, Whisper, PushPlus, WeChat, Email, Lark)
- **7 个业务模块** (Sources, Content, Transcription, Summarization, Subscribers, Distribution)
- **1 个定时任务** (Weekly Newsletter)

## 核心功能

✅ RSS 内容自动抓取
✅ AI 智能摘要（DeepSeek/OpenAI）
✅ 质���评分和排序
✅ 多渠道分发（PushPlus、微信、邮件、飞书）
✅ 定时调度（Cron）
✅ REST API（健康检查、手动触发）
✅ 异步高性能架构
✅ 数据库迁移（Alembic）
✅ 结构化日志（structlog）
✅ Docker 部署

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 14 |
| 缓存 | Redis 6 |
| 调度器 | APScheduler |
| HTTP 客户端 | httpx |
| RSS 解析 | feedparser |
| AI SDK | OpenAI |
| 日志 | structlog |
| 配置 | pydantic-settings |
| 迁移 | Alembic |

## 文档

- `README.md` - 用户指南
- `CLAUDE.md` - 开发者文档
- `docs/TYPESCRIPT-REMOVAL.md` - TypeScript 移除记录
- `docs/archive/` - 实现文档归档

## API 端点

- `GET /` - 服务信息
- `GET /health` - 健康检查
- `POST /trigger` - 手动触发 newsletter

## 环境变量

### 必需
- `DATABASE_URL` - PostgreSQL 连接（格式：`postgresql+asyncpg://...`）
- `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` - AI 服务密钥

### 可选
- `REDIS_URL` - Redis 连接
- `RSS_FEEDS` - RSS 源列表
- `PUSHPLUS_TOKENS` - PushPlus 令牌
- `WECHAT_WEBHOOK_URLS` - 微信 Webhook
- `SMTP_*` - 邮件配置
- `WEEKLY_CRON` - 调度表达式
- `IMMEDIATE_RUN` - 立即运行
- `FORCE_RECENT` - 强制处理最近内容

## 开发命令

```bash
# 开发模式
uvicorn app.main:app --reload

# 生产模式
uvicorn app.main:app --workers 4

# Docker 部署
docker-compose up -d

# 数据库迁移
alembic upgrade head
alembic revision --autogenerate -m "description"

# 测试
python test_setup.py
curl -X POST http://localhost:8000/trigger
```

## 项目结构

```
autonewsletter/
├── app/                # Python 应用
│   ├── models/        # 数据模型
│   ├── repositories/  # 数据访问
│   ├── services/      # 外部服务
│   ├── modules/       # 业务逻辑
│   ├── jobs/          # 定时任务
│   ├── utils/         # 工具函数
│   └── main.py        # 应用入口
├── alembic/           # 数据库迁移
├── docs/              # 文档
├── scripts/           # 脚本
├── requirements.txt   # Python 依赖
├── Dockerfile         # Docker 镜像
└── docker-compose.yml # Docker Compose
```

## 状态

✅ **生产就绪** - 所有核心功能已实现并测试

## 下一步

1. 配置 `.env` 文件
2. 运行 `./quickstart.sh`
3. 添加 RSS 源到数据库
4. 添加订阅者到数据库
5. 测试手动触发：`curl -X POST http://localhost:8000/trigger`

## 许可证

MIT
