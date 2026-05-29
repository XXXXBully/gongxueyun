# 运行手册

## 认证失败告警

- 先看 `/audit` 最近的 `admin.login.fail` / `app.login.fail` 记录。
- 确认是否是密码撞库、MFA 配置错误、租户停用，还是限流误伤。
- 如果是单租户异常，优先检查该租户的管理员锁定状态和最近的权限变更。

## 5xx 告警

- 先看 `/metrics.prom` 和最近请求 ID。
- 再查 `HttpRequestMetric`、`TaskExecutionEvent`、`AuditLog` 是否集中在同一接口或同一租户。
- 如果是批量任务引起的，先暂停任务，再处理失败项，不要让 worker 继续扩散错误。

## 批量任务卡住

- 查看 `/batch-jobs/{id}` 的 `running`、`queued`、`failed`。
- 失败项先用 `retry-failed` 重新排队，再决定是否继续暂停或取消。
- 如果同一个租户的活跃任务数异常增多，先查 `BATCH_TENANT_MAX_ACTIVE_JOBS` 和重复提交。

## AI 生成失败

- 先确认 `AI_ALLOWED_HOSTS`、`ALLOW_PRIVATE_AI_ENDPOINTS`、`AI_ALLOWED_MODELS` 和 `AI_MAX_OUTPUT_TOKENS` 配置。
- 再看 `/ai/test` 是否还能连通，以及目标模型是否被白名单拦截。
- 需要回放时，核对 `AI_PROMPT_VERSION`，否则提示词版本不一致，结果没有可比性。

## 权限灰度

- `ROLE_PERMISSIONS_JSON` 只适合短期灰度和紧急修补。
- 灰度结束后必须清空，回到内置策略。
- 任何权限变更都要同步检查管理员、批量和审计接口的可访问面。
