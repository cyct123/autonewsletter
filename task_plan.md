# Task Plan: 日志格式优化

**目标**：实现环境感知双模式日志（pretty/json），统一三种日志来源，加入耗时字段
**设计文档**：`docs/superpowers/specs/2026-03-18-log-format-design.md`
**创建时间**：2026-03-18

---

## 阶段

### Phase 1: 配置层 `complete`
- [x] `app/config.py` 添加 `log_format: str = "json"` 字段
- [x] `.env.example` 添加 `LOG_FORMAT=pretty` 注释示例

### Phase 2: 日志核心 `complete`
- [x] 重写 `app/utils/logger.py`
  - 根据 `settings.log_format` 选择 `ConsoleRenderer`（pretty）或 `JSONRenderer`（json）
  - 通过 `logging.basicConfig` 接管 stdlib logging（覆盖 APScheduler、uvicorn）
  - 统一字段顺序：timestamp → level → logger → event �� 上下文字段

### Phase 3: Pipeline 耗时字段 `complete`
- [x] `app/jobs/weekly_newsletter.py` 各阶段加入 `duration_ms` 和 `stage` 字段
  - pipeline 整体耗时
  - 转录阶段耗时
  - 摘要阶段耗时

### Phase 4: 验证 `complete`
- [x] 重新构建容器：`docker-compose build app && docker-compose up -d app`
- [x] 触发 pipeline：`curl -X POST http://localhost:8000/trigger`
- [x] 确认日志格式符合设计文档预期（pretty 彩色格式正常，json 格式正常）

### Phase 5: 提交 `complete`
- [x] git commit: `feat(logging): add dual-mode log format with pipeline metrics`

---

## 错误记录

| 错误 | 尝试 | 解决 |
|------|------|------|
| - | - | - |
