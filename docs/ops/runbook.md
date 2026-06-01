# 运行手册

本文档用于排查线上运行、CI 安全扫描和批量任务异常。处理问题时优先保留日志、请求 ID 和任务 ID，避免只凭界面现象判断。

## 供应链审计失败

- 先看失败来源：`pip-audit`、`npm audit`、Trivy，还是 `python scripts/verify_supply_chain_policy.py`。
- Python 依赖问题优先检查 `server/requirements.txt`；前端依赖问题优先检查 `web/package.json` 和 `web/package-lock.json`。
- GitHub Actions 引用失败时检查 `.github/workflows/docker-publish.yml` 中的 `uses:`，外部 action 必须钉到完整 40 位 commit SHA。
- Docker 基础镜像扫描或策略失败时检查 `Dockerfile` 的 `FROM` 行，基础镜像必须使用 `@sha256:` digest。
- 修复后至少运行：

```bash
python -m unittest discover -s tests -p test_platform_foundations.py
python scripts/verify_supply_chain_policy.py
git diff --check
```

前端依赖变更还需要在 `web/` 下运行：

```bash
npm ci --dry-run --ignore-scripts
npm run lint
npm test
npm run build
```

## 认证失败告警

- 先看 `/audit` 最近的 `admin.login.fail` / `app.login.fail` 记录。
- 确认失败原因是密码错误、账号锁定、账号停用，还是限流误伤。
- 如果只影响单个账号，优先检查该账号状态、绑定信息和最近权限变更。
- 如果大量账号同时失败，先确认 `APP_SECRET`、Cookie 域、`FRONTEND_ORIGINS` 和 `TRUSTED_HOSTS` 是否在发布中被改坏。

## 5xx 告警

- 先看 `/metrics.prom` 和最近请求 ID。
- 再查 `HttpRequestMetric`、`TaskExecutionEvent`、`AuditLog` 是否集中在同一接口、同一账号或同一批量任务。
- 如果由批量任务引起，先暂停或取消对应任务，再处理失败项，避免 worker 继续扩散错误。
- 如果 5xx 集中在启动后，优先检查数据库连接、Alembic 版本、模型文件校验和环境变量安全校验。

## 批量任务卡住

- 查看 `/batch-jobs/{id}` 的 `running`、`queued`、`failed` 数量。
- 失败项先用 `retry-failed` 重新排队，再决定是否继续、暂停或取消任务。
- 如果 running 项长时间不动，检查 `BATCH_RUNNING_ITEM_TIMEOUT_SECONDS` 和 worker 日志。
- 如果活跃批量任务异常增多，检查兼容保留的 `BATCH_TENANT_MAX_ACTIVE_JOBS` 默认桶限制和幂等键是否被绕过。

## AI 生成失败

- 先确认管理端“系统设置 -> AI 设置”里的 API URL、API Key 和 Model 是否已保存；读取接口只返回 `hasApiKey`，看不到明文 Key 是预期行为。
- 再确认 `AI_ALLOWED_HOSTS`、`ALLOW_PRIVATE_AI_ENDPOINTS`、`AI_ALLOWED_MODELS` 和 `AI_MAX_OUTPUT_TOKENS` 配置。
- 再看 `/settings/ai/test` 是否仍能连通，以及目标模型是否被白名单拦截；`/ai/test` 仅作为兼容入口保留。
- 正式 AI 生成默认拒绝本机、内网、链路本地和特殊地址；确需内网模型时必须同时设置 `ALLOW_PRIVATE_AI_ENDPOINTS=true` 和明确的 `AI_ALLOWED_HOSTS`。
- 需要回放时核对 `AI_PROMPT_VERSION`，否则提示词版本不一致，结果没有可比性。

## 权限灰度

- `ROLE_PERMISSIONS_JSON` 只适合短期灰度和紧急修补。
- 灰度结束后必须清空配置，回到内置权限策略。
- 任何权限变更都要同步检查管理员、批量任务、审计日志、系统设置和用户端接口的可访问面。
