# 当前功能与接口速查

本文档记录当前代码实现中的核心功能、补卡规则、接口入口和验证命令。历史设计与计划文档位于 `docs/superpowers/`，不一定代表最新实现。

## 功能范围

AutoMoGuDing SaaS 当前包含两套 Web 界面：

- **管理端：** 用户管理、批量任务、审计日志查询、全局 AI 配置、通知基础配置、单用户推送配置、AI 测试、地理编码、缺卡查询和补卡。审计清空默认禁用，用户删除为软删除。
- **用户端：** 注册 / 登录、绑定工学云账号、个人打卡 / 报告 / 推送配置、手动执行、执行记录、日报生成 / 提交、缺卡查询和补卡。

后端任务执行链路集中在：

- `server/api.py`：管理端和用户端 API。
- `server/user_runtime.py`：数据库用户模型与任务运行配置之间的转换。
- `server/scheduler.py`：定时任务注册。
- `server/queue_worker.py`：批量任务队列。
- `server/task_runner.py`：打卡、补卡、报告提交等任务执行。
- `server/clockin_backfill.py`：打卡记录归一化和待补卡日期筛选。
- `server/coreApi/MainLogicApi.py`：工学云接口客户端。
- `server/execution_locks.py`：定时任务分布式锁。
- `server/observability.py`：任务事件记录与 `/metrics` 运行统计。

更多后端维护细节见 `server/README.md`，前端交互说明见 `web/README.md`。

## 地图与地理编码

管理端用户编辑页的打卡设置默认显示 `https://www.mapchaxun.cn/jingweidu`，用于人工核对经纬度。页面内的地址搜索仍走后端 `/geocode/search`，默认调用 `https://www.mapchaxun.cn/api/getSolidAdress`，会根据响应中的 `location` 和 `address_components` 自动回填经纬度、省市区和地址；如果搜索服务没有返回结构化地址，前端会继续调用 `/geocode/reverse` 反查地址。

后端地址搜索默认配置：

- `GEOCODE_SEARCH_PROVIDER=mapchaxun`

逆地理解析默认配置：

- `GEOCODE_PROVIDER=osm`

也可以把搜索或逆地理解析切换到百度 Web 服务：

- `GEOCODE_SEARCH_PROVIDER=baidu`
- `GEOCODE_PROVIDER=baidu`
- `BAIDU_MAP_AK=<百度地图 Web 服务 AK>`
- `BAIDU_MAP_COORD_TYPE=gcj02ll`
- `BAIDU_MAP_INPUT_COORD_TYPE=`：可选，百度逆地理输入坐标类型，默认跟随 `BAIDU_MAP_COORD_TYPE`
- `BAIDU_MAP_OUTPUT_COORD_TYPE=`：可选，百度地理编码返回坐标类型，默认跟随 `BAIDU_MAP_COORD_TYPE`

使用百度但未配置百度 AK 时会直接返回明确错误，不会静默切换到其他服务。历史高德分支仍保留兼容，可通过 `amap` 和 `AMAP_KEY` 启用。

## 打卡记录与缺卡筛选

打卡记录会先归一化为以下结构：

| 字段 | 说明 |
|------|------|
| `date` | 日期，格式为 `YYYY-MM-DD` |
| `time` | 打卡时间，格式为 `YYYY-MM-DD HH:mm:ss` |
| `type` | 打卡类型，`START` 或 `END` |
| `type_label` | 中文类型，上班或下班 |
| `address` | 记录中的地址 |

缺卡筛选规则：

- `START` 表示上班打卡。
- `END` 表示下班打卡。
- 同一天如果 `START` 和 `END` 都存在，则该日期不是待补日期。
- 同一天如果只缺一种类型，则只在该类型下展示。
- 待补日期会按用户配置的打卡周期过滤。

## 补卡规则

补卡一次只补一种类型：

- `target_type=START`：只补上班。
- `target_type=END`：只补下班。

即使某一天同时缺上班和下班，只要用户选择 `START`，系统也只提交上班补卡；选择 `END` 时也只提交下班补卡。

补卡只在手动接口中触发，定时任务不会自动执行补卡。批量补卡默认会保留日期间隔，并在遇到“请求过于频繁”、`429` 或“IP非法请求过多，已限制访问”时自动等待重试当前日期。

触发 IP 频繁后会进入批量冷却策略：当前日期重试成功后，后续日期之间会按冷却间隔降速；当前日期重试耗尽仍然频繁时，会停止剩余日期并标记为跳过，避免继续触发远端风控。

可通过 `MOGUDING_PROXY_API_URL` 配置动态代理获取接口。接口响应需要包含 `ip:端口`，后端会从接口 URL 查询参数读取 `accessName` 和 `accessPassword`，并拼接成 `http://accessName:accessPassword@ip:端口` 使用。动态代理默认缓存 `55` 秒；补卡请求遇到 IP 频繁或代理连接失败时，会重新获取新 IP 后重试。

普通登录、定时打卡、报告提交、缺卡查询等非补卡请求如果命中“IP非法请求过多，已限制访问”，会按 `MOGUDING_IP_RESTRICT_COOLDOWN_SECONDS` 进入普通网络熔断窗口，暂停继续向工学云发起非代理请求；手动补卡启用代理后仍可获取或切换代理 IP 重试。

也可以通过 `MOGUDING_PROXY_URLS` 配置静态工学云补卡代理池。多个代理用逗号、分号或换行分隔；如果同时配置动态代理接口，会优先使用动态代理接口。

代理只在手动补卡执行阶段启用。正常登录、缺卡查询、定时打卡和报告提交不会使用工学云代理。

管理端 Web 的「系统设置」提供全局工学云补卡代理配置。环境变量中的代理配置优先于 Web 全局配置。

补卡时间来自用户配置：

- 上班补卡使用 `config.clockIn.schedule.startTime`，默认 `07:30`。
- 下班补卡使用 `config.clockIn.schedule.endTime`，默认 `18:00`。

学生补卡请求使用：

```text
attendence/attendanceReplace/v4/save
```

关键请求字段：

| 字段 | 值 |
|------|----|
| `attendanceType` | `REPLACE` |
| `type` | `START` 或 `END` |
| `createTime` | 目标日期 + 对应上班 / 下班时间 |
| `attendenceTime` | `null` |
| `isReplace` | `null` |

## 用户端补卡接口

### 获取缺卡日期

```http
GET /app/clock-in/missing-days
```

返回中的 `options` 用于前端日期下拉。每个选项包含：

```json
{
  "value": "2026-05-06",
  "label": "2026-05-06（缺上班）",
  "missing_types": ["START"],
  "existing_types": ["END"]
}
```

### 补选中日期

```http
POST /app/clock-in/makeup
Content-Type: application/json
```

```json
{
  "target_dates": ["2026-05-06", "2026-05-07"],
  "target_type": "START"
}
```

兼容单日期请求：

```json
{
  "target_date": "2026-05-06",
  "target_type": "END"
}
```

### 补全部待补日期

```http
POST /app/clock-in/makeup-all
Content-Type: application/json
```

```json
{
  "target_type": "END"
}
```

该接口会先重新获取缺卡列表，再只补当前 `target_type` 下仍缺卡的日期。

## 管理端补卡接口

管理端接口与用户端语义一致，只是路径包含用户 ID：

```http
GET /users/{user_id}/clock-in/missing-days
POST /users/{user_id}/clock-in/makeup
POST /users/{user_id}/clock-in/makeup-all
```

## 前端补卡交互

管理端用户编辑页和用户端设置页采用同一交互模型：

1. 点击「刷新缺卡」。
2. 选择补卡类型：上班或下班。
3. 日期下拉只展示当前类型仍缺的日期。
4. 点击「补选中」补多选日期。
5. 点击「全部待补」补当前类型下全部待补日期。

页面会显示：

- 已获取打卡记录数
- 当前类型待补天数
- 已选择天数

## 报告补交

日报、周报、月报都支持按周期筛选未提交记录：

- 日报按日期筛选。
- 周报按自然周筛选。
- 月报按月份筛选。

管理端和用户端设置页均支持选择未提交周期、AI 生成内容和立即提交；日报、周报、月报分别提供独立的「补全部日报 / 补全部周报 / 补全部月报」入口，只会补当前类型的待补周期。

未开启的报告类型不会自动获取未提交周期。前端会禁用该类型的刷新、生成、提交和立即执行入口；后端缺失周期接口也会直接返回空列表，不会登录工学云查询远端报告记录。

「立即执行日报 / 周报 / 月报」属于报告类手动任务，不触发本系统 `/run` 接口的 429 限流。打卡和默认手动运行仍保留内部限流。

## 认证、AI 与运行观测

- 浏览器登录态默认写入 HttpOnly Cookie，前端不再把 token 放进 `localStorage`。非安全方法的 Cookie 请求会校验 `Origin` / `Referer`，跨域前端需要配置 `FRONTEND_ORIGINS` 或 `CORS_ORIGINS`；外部脚本客户端如需响应体 token，需要显式配置 `RETURN_AUTH_TOKEN=true`。
- 默认响应安全头和 CSP；生产环境默认启用 HSTS。
- 审计日志默认不可清空；用户删除为软删除，会停用打卡和用户端绑定账号并保留历史记录。
- 生产环境必须配置 `USER_PASSWORD_KEY` 或 `FERNET_KEY` 才允许保存新的工学云密码、SMTP 授权码和代理接口密钥；本地开发保留历史明文兼容。
- 前端按单租户产品运行，不再展示租户输入、租户菜单和租户管理页。核心表中保留 `tenant_id` / 默认值 `default` 只是为了兼容旧库、迁移和已有索引。
- 管理端权限从纯角色判断推进到权限点依赖，用户、任务、批量、设置和审计接口按动作权限校验。
- AI URL / API Key / Model 由全局系统设置统一管理，接口为 `/settings/ai` 和 `/settings/ai/test`；用户编辑页和用户端设置页不再保存用户级 AI 参数。读取全局设置时只返回 `hasApiKey`，不会回显 API Key。`/settings/ai/test` 和兼容保留的 `/ai/test` 默认只允许公网 HTTPS 地址；正式 AI 生成链路默认也拒绝本机、内网和特殊地址，确需接入内网模型服务时必须同时配置 `ALLOW_PRIVATE_AI_ENDPOINTS=true` 和 `AI_ALLOWED_HOSTS`。AI 生成还受 `AI_TENANT_DAILY_LIMIT`、`AI_USER_DAILY_LIMIT` 和 `AI_RATE_LIMIT_WINDOW_SECONDS` 控制，避免循环任务或滥用打穿模型费用。
- 定时任务使用数据库锁避免重复执行，锁 TTL 由 `TASK_LOCK_TTL_SECONDS` 控制。
- 批量队列认领会把 queued 项原子更新为 running，并写入 worker owner、lease token 和 lease 到期时间，降低多 worker 或多线程重复执行风险；running 项超过 `BATCH_RUNNING_ITEM_TIMEOUT_SECONDS` 后会回收，过期线程不能再覆盖新状态。
- 数据库限流后端按 bucket 聚合计数，登录和注册同时按 IP 与账号维度限流，避免低速撞库绕过单 IP 限制。
- `/metrics` 返回任务事件、批量任务、批量项、活动锁、HTTP 请求状态分布、延迟统计和最近请求 ID；`/metrics.prom` 返回 Prometheus 文本格式。生产环境默认不裸露 metrics，需要配置 `METRICS_AUTH_TOKEN` 并通过 `X-Metrics-Token` 或 Bearer token 访问。指标快照默认缓存 `METRICS_CACHE_TTL_SECONDS=5` 秒，并会在相关写入提交后失效，避免抓取端高频请求时每次重新扫业务库又不至于长期返回旧数据。HTTP 请求明细默认保留 14 天，并按小时节流清理；静态资源和健康检查默认不落库，避免指标表被无价值请求刷爆。
- AI、通知 SMTP 和工学云补卡代理 Web 配置按默认全局配置保存；单用户推送配置保存在用户记录中，管理员可在用户编辑页维护，绑定用户也可在 `/u/settings` 自助维护；QQ 邮箱 SMTP 的发件账号仍由管理员统一配置。
- 生产环境默认不在启动时自动下载验证码 ONNX 模型，避免外网下载失败影响 API 启动；需要自动拉取时配置 `CAPTCHA_MODEL_AUTO_DOWNLOAD=true`。
- 数据库 schema 使用 Alembic 维护，生产环境默认不做运行时 schema 写操作，发布前执行 `python -m alembic upgrade head`；运行时迁移关闭时，后端启动会校验数据库 `alembic_version` 是否处于 head，不一致会直接拒绝启动。需要保留开发期自动初始化时设置 `ALLOW_RUNTIME_SCHEMA_MIGRATIONS=true`。
- 数据库备份/恢复可使用 `python -m server.backup_cli export backup.json` 和 `python -m server.backup_cli import backup.json --replace-existing`，导出包包含 manifest、表行数和表校验和，导入前会校验篡改。生产环境导出默认要求 `BACKUP_ENCRYPTION_KEY` 或 `--encryption-key`，除非显式设置 `ALLOW_PLAINTEXT_BACKUP=true`。
- CI 质量门禁会运行 `python scripts/quality_gate.py` 和 `python scripts/verify_supply_chain_policy.py`，检查 UTC 时间、前端敏感登录态存储、服务器端 `print`、裸 `except/pass`、不带内部隔离上下文的用户读取回归、GitHub Actions 钉死和 Docker 基础镜像 digest 钉死；发布流程还会跑 `pip-audit`、`npm audit` 与 Trivy 扫描。

## 验证命令

后端测试：

```bash
python -m unittest discover -s tests
python -m alembic upgrade head
python scripts/quality_gate.py
```

后端语法编译：

```bash
python -m compileall server
```

前端构建：

```bash
cd web
npm run build
```

空白字符检查：

```bash
git diff --check
```

当前前端已经提供 `npm run lint`、`npm test` 和 `npm run test:static`，其中 `npm test` 当前委托到静态质量门禁。
