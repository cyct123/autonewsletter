# AutoNewsletter

自动化新闻简报系统，基于 FastAPI + SQLAlchemy + APScheduler。

## 技术栈

- **FastAPI**: 现代异步 Web 框架
- **SQLAlchemy 2.0**: 异步 ORM
- **APScheduler**: 定时任务调度
- **PostgreSQL**: 数据存储
- **Redis**: 缓存和去重
- **OpenAI/DeepSeek**: AI 摘要和翻译

## 快速开始

> **Windows 用户注意**: 本项目的脚本文件（`.sh`）需要在 Bash 环境中运行。
> - **推荐方式**: 使用 WSL2 获得完整的 Linux 开发体验，详见 [WSL2 配置指南](docs/WSL2-SETUP.md) 🚀
> - **快速方式**: 使用 Git Bash 终端运行脚本。如果尚未安装，请访问 [git-scm.com](https://git-scm.com/download/win) 下载安装。

### 1. 环境准备

#### 选项 A: 使用 Conda（推荐）

```bash
# 创建 conda 环境
./conda-setup.sh

# 激活环境
conda activate autonewsletter

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

#### 选项 B: 使用 pip

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

### 2. 数据库初始化

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d db redis

# 运行数据库迁移
alembic upgrade head
```

### 3. 运行应用

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 立即运行一次（不等待定时任务）
IMMEDIATE_RUN=1 uvicorn app.main:app
```

### 4. Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f app

# 停止服务
docker-compose down
```

## API 端点

- `GET /`: 服务信息
- `GET /health`: 健康检查
- `POST /trigger`: 手动触发 newsletter 生成

## 环境变量

### 必需配置

- `DATABASE_URL`: PostgreSQL 连接字符串（格式：`postgresql+asyncpg://user:pass@host:port/db`）
- `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`: AI 服务密钥

### 可选配置

- `REDIS_URL`: Redis 连接字符串（默认：`redis://localhost:6379`）
- `RSS_FEEDS`: RSS 源列表（逗号分隔）
- `WEEKLY_CRON`: 定时任务表达式（默认：`0 9 * * 3` = 每周三 9:00）
- `IMMEDIATE_RUN`: 启动时立即运行（`1` 启用，`0` 禁用）
- `FORCE_RECENT`: 强制处理最近内容，跳过去重（`1` 启用）
- `LOG_LEVEL`: 日志级别（`debug`/`info`/`warning`/`error`）

### 推送渠道配置

- `PUSHPLUS_TOKENS`: PushPlus 令牌（逗号分隔）
- `WECHAT_WEBHOOK_URLS`: 企业微信 Webhook（逗号分隔）
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`: 邮件配置

## 项目结构

```
app/
├── models/          # SQLAlchemy 数据模型
├── repositories/    # 数据访问层
├── services/        # 外部服务集成（RSS、AI、推送）
├── modules/         # 业务逻辑模块
├── jobs/            # 定时任务
├── utils/           # 工具函数
├── api/             # API 路由
├── config.py        # 配置管理
├── database.py      # 数据库连接
└── main.py          # 应用入口
```

## 开发指南

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

### 测试

```bash
# 手动触发 newsletter 生成
curl -X POST http://localhost:8000/trigger

# 检查健康状态
curl http://localhost:8000/health
```

## 特性

- **自动化内容收集**: 从 RSS 源自动抓取内容
- **AI 智能摘要**: 使用 DeepSeek/OpenAI 生成中文摘要和关键要点
- **质量评分**: 自动评估内容质量并排序
- **多渠道分发**: 支持 PushPlus、企业微信、邮件、飞书
- **定时调度**: 基于 cron 表达式的灵活调度
- **异步高性能**: 全异步架构，高效处理并发请求

## 许可证

MIT
