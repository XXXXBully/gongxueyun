# 运行手册

本文档用于排查线上运行、CI 安全扫描和批量任务异常。处理问题时优先保留日志、请求 ID、任务 ID、批量任务 ID 和后端版本，避免只凭界面现象判断。

## 告警总览

| 告警 / 现象 | 先看哪里 | 最常见原因 | 完成标准 |
|-------------|----------|------------|----------|
| 供应链审计失败 | CI 失败步骤、依赖审计、容器扫描、固定策略结果 | 依赖漏洞、外部 action 未固定、基础镜像未固定 | 审计和策略结果恢复正常 |
| 认证失败激增 | `/audit`、登录接口响应、限流指标 | 密码错误、账号停用、Cookie / Origin / Host 配置变更 | 单账号问题被定位，或全局配置恢复 |
| 5xx 告警 | `/metrics.prom`、请求 ID、后端日志 | 数据库、迁移版本、配置校验、外部依赖失败 | 5xx 回落，请求 ID 可追溯 |
| 批量任务卡住 | `/batch-jobs/{id}`、worker 日志 | running lease 未回收、远端限流、worker 停止 | queued / running / failed 状态恢复可解释 |
| AI 生成失败 | 系统设置、`/settings/ai/test`、AI 安全配置 | Key 缺失、host 白名单、内网端点被拒、模型不在白名单 | 测试接口和正式生成链路均可解释 |
| 权限异常 | 当前用户权限、`ROLE_PERMISSIONS_JSON`、审计日志 | 灰度配置残留、角色权限映射错误 | 权限矩阵符合预期，灰度配置清理 |

## 供应链审计失败

| 检查项 | 命令 / 文件 | 处理 |
|--------|-------------|------|
| Python 依赖 | `server/requirements.txt` | 升级受影响包并做回归确认 |
| 前端依赖 | `web/package.json`、`web/package-lock.json` | 升级依赖锁定文件，必要时调整依赖声明 |
| GitHub Actions | `.github/workflows/docker-publish.yml` | 外部 action 的 `uses:` 必须钉到完整 40 位 commit SHA |
| Docker 基础镜像 | `Dockerfile` | `FROM` 必须使用 `@sha256:` digest |
| 策略结果 | CI 输出中的固定策略检查 | 修复 action 和基础镜像固定策略 |

## 认证失败告警

| 现象 | 检查 | 处理 |
|------|------|------|
| 单个管理员失败 | `/audit` 中 `admin.login.fail`、账号状态、密码重置记录 | 区分密码错误、账号停用、权限变更 |
| 单个用户失败 | `/audit` 中 `app.login.fail`、用户端账号、绑定工学云信息 | 确认是用户端密码还是工学云账号密码 |
| 大量账号同时失败 | `APP_SECRET`、Cookie 域、`FRONTEND_ORIGINS`、`TRUSTED_HOSTS` | 回滚错误配置或补齐白名单 |
| 浏览器有 Cookie 但请求 401 | CSRF token、Origin / Referer、HTTPS / `AUTH_COOKIE_SECURE` | 按部署方式修正前端地址和 Cookie 安全属性 |
| 登录接口 429 | 限流 bucket、IP、账号维度 | 判断是否撞库、代理配置错误或测试脚本过快 |

## 5xx 告警

| 排查顺序 | 证据 | 判断 |
|----------|------|------|
| 1 | `/metrics.prom` 状态码分布和最近请求 ID | 是否集中在单接口 |
| 2 | `HttpRequestMetric` | 是否集中在同一账号、路径或时间窗口 |
| 3 | `TaskExecutionEvent` | 是否由定时任务、补卡或报告任务触发 |
| 4 | `AuditLog` | 是否紧跟配置变更、权限变更或批量操作 |
| 5 | 后端启动日志 | 数据库连接、Alembic 版本、模型校验、环境变量安全校验 |

| 原因 | 处理 |
|------|------|
| 批量任务引起 | 先暂停或取消对应任务，再处理失败项，避免 worker 扩散错误 |
| 迁移版本不一致 | 执行 `python -m alembic current` 和 `python -m alembic upgrade head` |
| 数据库连接失败 | 检查 `DATABASE_URL`、MySQL 网络、账号权限和连接池配置 |
| 请求体过大 | 检查 `MAX_REQUEST_BODY_BYTES` 和客户端上传内容 |
| 外部依赖失败 | 区分工学云、AI、地图、SMTP、代理接口 |

## 批量任务卡住

| 检查项 | 看什么 | 处理 |
|--------|--------|------|
| 任务状态 | `/batch-jobs/{id}` 的 `queued`、`running`、`failed` | 判断是未认领、执行中还是失败堆积 |
| running 长时间不动 | `BATCH_RUNNING_ITEM_TIMEOUT_SECONDS`、worker 日志 | 等待 lease 回收或重启 worker 后观察 |
| failed 增多 | 失败原因、远端返回、代理切换次数 | 先 `retry-failed`，再决定继续 / 暂停 / 取消 |
| queued 不减少 | worker 是否运行、`APP_ROLE=worker`、数据库连接 | 恢复 worker 或修正角色配置 |
| 活跃任务过多 | `BATCH_JOB_MAX_USERS`、`BATCH_TENANT_MAX_ACTIVE_JOBS`、幂等键 | 调整容量或清理重复提交 |

## AI 生成失败

| 检查项 | 预期 |
|--------|------|
| 系统设置 | 管理端“系统设置 -> AI 设置”已保存 API URL、API Key、Model |
| Key 回显 | 读取接口只返回 `hasApiKey`，看不到明文 Key 是预期行为 |
| 测试接口 | `/settings/ai/test` 能连通；`/ai/test` 只是兼容入口 |
| Host 白名单 | `AI_ALLOWED_HOSTS` 覆盖目标 host |
| 内网模型 | 必须同时设置 `ALLOW_PRIVATE_AI_ENDPOINTS=true` 和明确的 `AI_ALLOWED_HOSTS` |
| 模型白名单 | `AI_ALLOWED_MODELS` 包含目标模型 |
| 输出长度 | `AI_MAX_OUTPUT_TOKENS` 足够但不过大 |
| 回放对比 | `AI_PROMPT_VERSION` 一致 |

正式 AI 生成默认拒绝本机、内网、链路本地和特殊地址，并会固定已校验 DNS 解析结果，避免校验后解析漂移。

## 权限灰度

| 操作 | 要求 |
|------|------|
| 临时灰度 | 只使用 `ROLE_PERMISSIONS_JSON` 做短期覆盖 |
| 验证范围 | 管理员、用户、批量任务、审计日志、系统设置、用户端接口 |
| 结束灰度 | 清空 `ROLE_PERMISSIONS_JSON`，回到内置权限策略 |
| 事故回滚 | 保留审计日志和变更记录，不要只改前端隐藏菜单 |
