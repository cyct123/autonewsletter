# 日志格式优化设计文档

**日期**：2026-03-18
**状态**：待实现

---

## 背景

当前日志存在三个痛点：

1. 开发时难读（structlog 输出纯 JSON，需手动解析）
2. 三种格式混杂（structlog JSON、APScheduler 纯文本、uvicorn 访问日志各自独立）
3. 缺少关键上下文字段（如耗时 `duration_ms`、pipeline 阶段 `stage`）

---

## 目标

- 开发环境：彩色、对齐、人类可读的 pretty 格式
- 生产环境：标准 JSON 格式，便于后续接入日志平台
- 统一三种日志来源，全部走 structlog 管道处理

---

## 架构

```
环境变量 LOG_FORMAT=pretty|json
         ↓
   logger.py 初始化
         ↓
   ┌─────────────────────────────┐
   │  structlog pipeline         │
   │  - 时间戳                   │
   │  - 日志级别                 │
   │  - logger 名称              │
   │  - 上下文字段               │
   │  ↓                         │
   │  pretty → ConsoleRenderer  │
   │  json   → JSONRenderer     │
   └─────────────────────────────┘
         ↑              ↑
   APScheduler      uvicorn
   (接管 stdlib     (接管 access
    logging)         log)
```

通过 `logging.basicConfig` 将 Python 标准库 logging 路由到 structlog，从而统一接管 APScheduler 和 uvicorn 的日志输出。

---

## 字段规范

### 基础字段（每条日志都有）

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | string | ISO 8601 时间戳 |
| `level` | string | debug/info/warning/error |
| `logger` | string | 模块名，如 `app.jobs.weekly_newsletter` |
| `event` | string | 事件名，snake_case，如 `pipeline_started` |

### 上下文字段（按场景附加）

| 字段 | 类型 | 说明 |
|------|------|------|
| `duration_ms` | int | 耗时（毫秒） |
| `stage` | string | pipeline 阶段名 |
| `url` | string | 相关 URL |
| `error` | string | 错误信息 |

---

## 输出示例

### pretty 模式（开发环境）

```
2026-03-18 09:00:01 [info     ] pipeline_started               [app.jobs]
2026-03-18 09:00:02 [info     ] transcription_starting         [app.jobs] url=https://...m4a
2026-03-18 09:00:45 [info     ] transcription_success          [app.jobs] url=https://...m4a duration_ms=43210
2026-03-18 09:00:46 [warning  ] content_skipped_no_text        [app.jobs] url=https://...
2026-03-18 09:01:00 [info     ] pipeline_done                  [app.jobs] duration_ms=59000 items=5
```

### json 模式（生产环境）

```json
{"timestamp":"2026-03-18T09:00:01Z","level":"info","logger":"app.jobs","event":"pipeline_started"}
{"timestamp":"2026-03-18T09:00:45Z","level":"info","logger":"app.jobs","event":"transcription_success","url":"https://...","duration_ms":43210}
```

---

## 改动范围

| 文件 | 改动内容 |
|------|---------|
| `app/utils/logger.py` | 添加环境感知双模式初始化，接管 stdlib logging |
| `app/jobs/weekly_newsletter.py` | pipeline 各阶段加入 `duration_ms` 和 `stage` 字段 |
| `app/config.py` | 添加 `log_format` 配置项（`pretty|json`，默认 `json`） |
| `.env.example` | 添加 `LOG_FORMAT=pretty` 示例注释 |

**不改动**：其他业务模块的 `logger.info/error` 调用保持不变。

---

## 配置方式

在 `.env` 中设置：

```bash
# 开发环境
LOG_FORMAT=pretty

# 生产环境（默认）
LOG_FORMAT=json
```
