# AutoMoGuDing SaaS 后端

`server/` 是 AutoMoGuDing SaaS 的 FastAPI 后端，负责管理端 API、用户端 API、工学云接口调用、定时调度、批量任务队列、补卡、报告提交和运行时数据回写。

## 技术栈

- FastAPI
- SQLModel
- MySQL
- APScheduler
- Requests
- ONNX Runtime

## 启动命令

从项目根目录启动：

```bash
pip install -r server/requirements.txt
python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8147
```

启动后访问：

- API 文档：本地开发默认开启，生产需设置 `EXPOSE_API_DOCS=true` 后访问 `http://localhost:8147/docs`
- OpenAPI：本地开发默认开启，生产需设置 `EXPOSE_API_DOCS=true` 后访问 `http://localhost:8147/openapi.json`

## 环境变量

后端默认读取项目根目录 `.env`。

必填：

```env
DATABASE_URL=mysql+pymysql://user:password@127.0.0.1:3306/automoguding?charset=utf8mb4
```

常用可选项：

```env
APP_ENV=development
APP_SECRET=dev-only-random-secret-at-least-32-characters
USER_PASSWORD_KEY=dev-only-secret-encryption-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=dev-only-admin-password
APP_ROLE=all
RATE_LIMIT_BACKEND=memory
ALLOW_RUNTIME_SCHEMA_MIGRATIONS=true
APP_REGISTRATION_ENABLED=false
USER_PASSWORD_MIN_LENGTH=10
EXPOSE_API_DOCS=false
AUTH_COOKIE_SECURE=false
RETURN_AUTH_TOKEN=false
ALLOW_LEGACY_TOKENS=false
ROLE_PERMISSIONS_JSON=
FRONTEND_ORIGINS=
ALLOW_WILDCARD_CORS=false
TRUSTED_HOSTS=
ALLOW_MISSING_TRUSTED_HOSTS=false
MAX_REQUEST_BODY_BYTES=8388608
ENABLE_HSTS=false
DISABLE_CSP=false
CONTENT_SECURITY_POLICY=
ALLOW_AUDIT_LOG_PURGE=false
TASK_LOCK_TTL_SECONDS=1800
AI_ALLOWED_HOSTS=
AI_ALLOWED_MODELS=
ALLOW_PRIVATE_AI_ENDPOINTS=false
AI_REQUEST_MAX_TIMEOUT_SECONDS=60
AI_REQUEST_MAX_RETRIES=2
AI_MAX_OUTPUT_TOKENS=1200
AI_SUBMITTED_REPORT_HISTORY_LIMIT=8
AI_SUBMITTED_REPORT_HISTORY_CHARS=4000
AI_PROMPT_VERSION=2026-05-29.1
AI_TENANT_DAILY_LIMIT=1000
AI_USER_DAILY_LIMIT=50
AI_RATE_LIMIT_WINDOW_SECONDS=86400
METRICS_AUTH_TOKEN=
METRICS_CACHE_TTL_SECONDS=5
HTTP_METRIC_RETENTION_DAYS=14
HTTP_METRIC_PURGE_INTERVAL_SECONDS=3600
HTTP_METRIC_SAMPLE_RATE=1
HTTP_METRIC_EXCLUDE_PATH_PREFIXES=
RECENT_METRIC_WINDOW_SECONDS=300
CAPTCHA_MODEL_AUTO_DOWNLOAD=false
CAPTCHA_MODEL_REQUIRE_CHECKSUM=true
CAPTCHA_MODEL_SHA256_OCR_ONNX=
CAPTCHA_MODEL_SHA256_YOLOV5N_ONNX=
TRUST_PROXY_HEADERS=false
TRUSTED_PROXY_IPS=
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE_SECONDS=1800
DATABASE_POOL_TIMEOUT_SECONDS=30
SCHEDULER_TIMEZONE=Asia/Shanghai
SCHEDULER_LOAD_PAGE_SIZE=500
SCHEDULER_JITTER_SECONDS=600
SCHEDULER_REPORT_JITTER_SECONDS=0
CLOCKIN_MAKEUP_BATCH_DELAY_SECONDS=2
CLOCKIN_MAKEUP_RATE_LIMIT_RETRIES=3
CLOCKIN_MAKEUP_RATE_LIMIT_RETRY_SECONDS=10
CLOCKIN_MAKEUP_RATE_LIMIT_COOLDOWN_SECONDS=60
MOGUDING_IP_RESTRICT_COOLDOWN_SECONDS=600
BATCH_RUNNING_ITEM_TIMEOUT_SECONDS=1800
BATCH_JOB_MAX_USERS=200
BATCH_TENANT_MAX_ACTIVE_JOBS=5
IDEMPOTENCY_TTL_SECONDS=604800
MOGUDING_PROXY_API_URL=
MOGUDING_PROXY_ALLOWED_HOSTS=
ALLOW_PRIVATE_MOGUDING_PROXY_ENDPOINTS=false
MOGUDING_PROXY_TTL_SECONDS=55
MOGUDING_PROXY_API_TIMEOUT_SECONDS=10
MOGUDING_PROXY_URLS=
REPORT_MAKEUP_BATCH_DELAY_SECONDS=2
GEOCODE_SEARCH_PROVIDER=mapchaxun
GEOCODE_PROVIDER=osm
BAIDU_MAP_AK=your-baidu-map-ak
BAIDU_MAP_COORD_TYPE=gcj02ll
BAIDU_MAP_INPUT_COORD_TYPE=
BAIDU_MAP_OUTPUT_COORD_TYPE=
AMAP_KEY=your-amap-key
```

说明：

- `DATABASE_URL` 必须使用 MySQL，且必须以 `mysql+pymysql://` 开头。
- 生产环境必须显式配置安全的 `APP_SECRET` 和管理员密码；示例值、默认值和过短值会导致启动失败。
- 生产环境必须配置 `USER_PASSWORD_KEY` 或 `FERNET_KEY`，否则后端会拒绝保存新的工学云密码、SMTP 授权码和代理接口密钥；本地开发未配置时仍兼容历史明文数据。
- `APP_ROLE=api` 只提供 Web / API；`APP_ROLE=worker` 启动 APScheduler 和批量队列；未配置时为本地开发兼容模式 `all`。
- `RATE_LIMIT_BACKEND` 支持 `memory` 和 `database`；生产多副本部署应使用 `database`。数据库后端按 bucket 聚合计数，避免登录或接口被扫时对限流表产生请求级写放大。
- `ALLOW_RUNTIME_SCHEMA_MIGRATIONS` 控制启动时是否允许应用进程自动建表、补列和建索引。生产环境默认关闭，发布前必须执行 Alembic 迁移；本地开发可设为 `true`。
- 登录态默认写入 HttpOnly Cookie，前端不再使用 `localStorage` 保存 token。生产环境默认启用 Secure Cookie，并通过 `csrf_token` Cookie + `X-CSRF-Token` 请求头做双提交 CSRF 校验；本地 HTTP 调试时才设置 `AUTH_COOKIE_SECURE=false`。跨域部署前端时必须配置 `FRONTEND_ORIGINS` 或 `CORS_ORIGINS`；生产环境默认拒绝 `*` 通配 CORS，除非显式设置 `ALLOW_WILDCARD_CORS=true`；需要兼容外部脚本取 Bearer token 时才打开 `RETURN_AUTH_TOKEN=true`。`ALLOW_LEGACY_TOKENS=true` 只用于短迁移窗口兼容旧版无版本 token，生产默认拒绝。
- 生产环境必须配置 `TRUSTED_HOSTS`，或通过 `FRONTEND_ORIGINS` / `CORS_ORIGINS` 自动推导 Host 白名单；如果三者都为空，后端会拒绝启动。只有明确接受 Host 校验缺失风险时才设置 `ALLOW_MISSING_TRUSTED_HOSTS=true`。`MAX_REQUEST_BODY_BYTES` 控制非 GET 请求体上限，生产默认 8 MiB，最高 10 MiB，包含无 `Content-Length` 的分块请求，避免异常大包长期占用 API worker。
- 停用租户会阻断管理端登录、用户端登录、现有 token 继续访问、定时调度加载、残留调度执行和批量队列执行。
- 租户管理接口只允许默认租户 `default` 的管理员访问；非默认租户管理员即使角色为 `admin`，也不会获得 `tenants:read` / `tenants:manage` 权限。需要做临时权限灰度或租户差异化时，可用 `ROLE_PERMISSIONS_JSON` 覆盖角色权限映射。
- `APP_REGISTRATION_ENABLED` 控制用户端自助注册，生产默认关闭；租户 `settings.registration_enabled=false` 也会禁用该租户自助注册。后端没有提供用户邀请入口。
- `USER_PASSWORD_MIN_LENGTH` 控制用户端密码最小长度，默认 10；管理端重置管理员密码按更高标准校验。
- `EXPOSE_API_DOCS` 控制 `/docs`、`/redoc` 和 `/openapi.json`，生产默认关闭，本地开发默认开启。接口契约快照放在 `docs/api/openapi-contract.json`，变更 API 路径、请求体或响应模型后必须运行 `python scripts/openapi_contract.py --write` 并让 `python scripts/openapi_contract.py` 通过。
- 默认启用安全响应头和 CSP，内置 `frame-src 'self' https://www.mapchaxun.cn` 以兼容经纬度核对页；生产环境默认启用 HSTS，只有显式设置 `ENABLE_HSTS=false` 才关闭。只有前端资源策略冲突时才临时关闭或覆盖 CSP。
- 审计日志默认不可清空。只有显式设置 `ALLOW_AUDIT_LOG_PURGE=true` 时清空接口才可用，并会追加 `audit.purge` 记录。
- 删除用户为软删除，会停用打卡和用户端绑定账号，但保留历史记录用于追溯和恢复。
- `TASK_LOCK_TTL_SECONDS` 控制定时任务分布式锁过期时间，用于防止多个 worker 重复执行同一任务。
- `BATCH_RUNNING_ITEM_TIMEOUT_SECONDS` 控制批量队列 running 项 lease 超时回收时间，默认 1800 秒。队列认领会写入 worker owner 和 lease token；超时后仍有重试次数的项目会重新排队，次数耗尽的项目会标记失败并推进批量任务进度，过期线程不能再覆盖新状态。
- `BATCH_JOB_MAX_USERS` 限制单个批量任务的用户数量，`BATCH_TENANT_MAX_ACTIVE_JOBS` 限制单租户同时处于 queued/running/paused 的批量任务数。批量运行接口支持 `Idempotency-Key` / `X-Idempotency-Key`，相同租户、操作者、用户列表和并发参数会回放同一 `job_id`；一键补卡、批量补卡、手动运行和批量补报告也会按同样的幂等键逻辑去重；批量任务详情支持失败项重试；`IDEMPOTENCY_TTL_SECONDS=604800` 控制记录保留窗口。
- `AI_ALLOWED_HOSTS` 可选限制正式 AI 生成链路 host。默认只允许解析到公网地址的 HTTPS 端点；本机、内网、链路本地和特殊地址会被拒绝，并会把已校验的 DNS 解析结果固定到本次请求，避免校验后解析漂移。确需接入内网模型服务时，必须同时设置 `ALLOW_PRIVATE_AI_ENDPOINTS=true` 和明确的 `AI_ALLOWED_HOSTS` 白名单。`AI_ALLOWED_MODELS` 可以锁定模型白名单，`AI_MAX_OUTPUT_TOKENS` 控制输出长度上限，`AI_PROMPT_VERSION` 记录提示词版本。`AI_TENANT_DAILY_LIMIT`、`AI_USER_DAILY_LIMIT` 和 `AI_RATE_LIMIT_WINDOW_SECONDS` 控制 AI 生成的租户级和用户级配额，避免循环任务或滥用把外部模型费用打穿。`AI_REQUEST_MAX_TIMEOUT_SECONDS`、`AI_REQUEST_MAX_RETRIES`、`AI_SUBMITTED_REPORT_HISTORY_LIMIT` 和 `AI_SUBMITTED_REPORT_HISTORY_CHARS` 控制 AI 请求超时、重试和历史报告注入规模。
- 生产环境访问 `/metrics` 和 `/metrics.prom` 需要配置 `METRICS_AUTH_TOKEN`，并通过 `X-Metrics-Token` 或 Bearer token 携带。指标包含认证失败、任务事件、批量队列、活动锁和 HTTP 状态 / 延迟；指标快照默认缓存 `METRICS_CACHE_TTL_SECONDS=5` 秒，并会在相关写入提交后失效，避免抓取端高频请求时每次重新扫业务库又不至于长期返回旧数据；HTTP 请求明细默认保留 14 天，并按小时节流清理；静态资源和健康检查默认不写入明细，可用 `HTTP_METRIC_SAMPLE_RATE` 与 `HTTP_METRIC_EXCLUDE_PATH_PREFIXES` 控制采样和排除前缀，`RECENT_METRIC_WINDOW_SECONDS=300` 控制最近窗口。Prometheus 告警规则放在 `monitoring/prometheus/alerts.yml`，排障步骤见 `docs/ops/runbook.md`。
- 备份导出支持 `--encryption-key` 或 `BACKUP_ENCRYPTION_KEY` 加密封装，导入加密备份时必须提供相同密钥；生产环境未提供密钥会拒绝导出，只有显式设置 `ALLOW_PLAINTEXT_BACKUP=true` 才允许明文 JSON。
- `CAPTCHA_MODEL_AUTO_DOWNLOAD` 控制启动时是否自动下载验证码 ONNX 模型。生产环境默认关闭，避免 API 启动被外网模型下载拖死；本地开发未配置时仍会自动检查下载。
- `CAPTCHA_MODEL_REQUIRE_CHECKSUM` 控制模型自动下载时是否强制校验 SHA256，生产默认要求。需要下载 `ocr.onnx` 和 `yolov5n.onnx` 时分别配置 `CAPTCHA_MODEL_SHA256_OCR_ONNX`、`CAPTCHA_MODEL_SHA256_YOLOV5N_ONNX`。
- 默认不信任 `X-Forwarded-For`。生产环境会忽略单独的 `TRUST_PROXY_HEADERS=true`，需要透过反向代理获取真实 IP 时，必须配置 `TRUSTED_PROXY_IPS` 为代理 IP 或 CIDR。
- MySQL 连接池通过 `DATABASE_POOL_SIZE`、`DATABASE_MAX_OVERFLOW`、`DATABASE_POOL_RECYCLE_SECONDS`、`DATABASE_POOL_TIMEOUT_SECONDS` 显式配置，生产环境不要继续靠 SQLAlchemy 默认值硬撑。
- `SCHEDULER_LOAD_PAGE_SIZE` 控制定时任务启动时分页加载用户的页大小；启动时只为开启打卡或报告任务的用户注册调度。
- `GEOCODE_SEARCH_PROVIDER=mapchaxun` 为默认地址搜索服务，无需地图 Key，只影响搜索框。
- `GEOCODE_PROVIDER` 控制搜索结果需要反查时的逆地理解析，默认 `osm`，可切换 `baidu` / `amap`。
- 使用百度 Web 服务时需要提供 `BAIDU_MAP_AK`；缺少 AK 时会返回明确错误。`BAIDU_MAP_COORD_TYPE` 默认 `gcj02ll`，也可用 `BAIDU_MAP_INPUT_COORD_TYPE`、`BAIDU_MAP_OUTPUT_COORD_TYPE` 分别控制百度逆地理输入坐标和返回坐标。
- `CLOCKIN_MAKEUP_BATCH_DELAY_SECONDS` 控制一键补卡每个日期之间的默认间隔。
- `CLOCKIN_MAKEUP_RATE_LIMIT_RETRIES` 控制补卡遇到频繁请求时的最大重试次数。
- `CLOCKIN_MAKEUP_RATE_LIMIT_RETRY_SECONDS` 控制补卡频繁请求重试的初始等待秒数，后续会递增退避。
- `CLOCKIN_MAKEUP_RATE_LIMIT_COOLDOWN_SECONDS` 控制触发 IP 频繁后的批量冷却间隔。当前日期重试成功后，后续日期会按该间隔降速；如果当前日期重试耗尽仍然频繁，会停止剩余日期。
- `MOGUDING_IP_RESTRICT_COOLDOWN_SECONDS` 控制普通网络被工学云返回“IP非法请求过多，已限制访问”后的非代理请求暂停时间，默认 `600` 秒。暂停期间不会继续向工学云发起普通网络请求；手动补卡启用代理后仍可获取/切换代理 IP 重试。
- `MOGUDING_PROXY_API_URL` 控制动态代理获取接口。接口响应需要包含 `ip:端口`，代理获取接口默认拒绝本机、内网和特殊地址；确需内网代理服务时，必须同时设置 `ALLOW_PRIVATE_MOGUDING_PROXY_ENDPOINTS=true` 和 `MOGUDING_PROXY_ALLOWED_HOSTS` 白名单。后端会从接口 URL 查询参数读取 `accessName` 和 `accessPassword`，并拼接成 `http://accessName:accessPassword@ip:端口`。
- `MOGUDING_PROXY_TTL_SECONDS` 控制动态代理缓存时长，默认 `55` 秒。
- `MOGUDING_PROXY_API_TIMEOUT_SECONDS` 控制动态代理接口请求超时。
- `MOGUDING_PROXY_URLS` 控制静态工学云补卡代理池，多个代理用逗号、分号或换行分隔。如果同时配置动态代理接口，会优先使用动态代理接口。代理只在手动补卡执行阶段启用；正常登录、定时打卡、报告提交和缺卡查询不会使用该代理。
- 补卡代理也可以在管理端 Web 的「系统设置」中按租户保存。环境变量中的代理配置优先级高于 Web 配置；非默认租户的 Web 配置不会覆盖 `default` 租户。
- `REPORT_MAKEUP_BATCH_DELAY_SECONDS` 控制日报 / 周报 / 月报一键补交的批量间隔，未配置时会回退到补卡间隔。
- Docker 容器内的 `127.0.0.1` 指向容器自身。容器连接宿主机 MySQL 时，请使用宿主机 IP 或 `host.docker.internal`。

## 启动流程

`server/main.py` 在启动时会执行以下动作：

1. 加载 `.env`。
2. 创建数据库连接。
3. 建表并补齐运行时字段。
4. 初始化管理员种子账号。
5. 按 `CAPTCHA_MODEL_AUTO_DOWNLOAD` 配置检查验证码识别所需 ONNX 模型。
6. 根据 `APP_ROLE` 决定是否启动 APScheduler。
7. 根据 `APP_ROLE` 决定是否启动批量任务 queue worker。
8. 如果 `web/dist` 存在，则托管前端静态资源并提供 SPA fallback。

数据库结构使用 Alembic 维护。生产环境默认不会在应用启动时自动建表、补列或建索引：

```bash
python -m alembic upgrade head
```

启动流程仍保留建表和补列逻辑，用于兼容旧部署，但生产发布应以迁移命令作为 schema 入口。

因此排查启动问题时，不要只看 API 是否启动，也要关注数据库连接、模型文件、调度线程和队列线程。

## 目录说明

```text
server/
├─ api.py                   # 管理端和用户端 API
├─ auth.py                  # Token 签发、校验和角色权限
├─ clockin_backfill.py      # 打卡记录归一化和待补卡日期筛选
├─ coreApi/
│  ├─ MainLogicApi.py       # 工学云接口客户端
│  └─ AiServiceClient.py    # AI 报告生成客户端
├─ database.py              # 数据库连接、建表和补列
├─ migrations/              # Alembic 数据库迁移
├─ models.py                # SQLModel 数据模型
├─ queue_worker.py          # 批量任务队列
├─ scheduler.py             # 用户定时任务注册
├─ task_runner.py           # 打卡、补卡、报告提交等任务执行
├─ user_runtime.py          # User 模型与运行配置之间的桥接
└─ util/                    # 加密、验证码、消息推送、配置工具
```

## API 面

后端同时承载两套 API。

### 管理端

管理端接口面向 `admin`、`operator`、`viewer` 等角色，负责：

- 用户管理
- 租户管理
- 批量执行
- 审计日志查询和清空
- 通知配置
- AI 测试
- 地理编码
- 缺卡查询和补卡
- 报告生成和提交

补卡相关接口：

```http
GET /users/{user_id}/clock-in/missing-days
POST /users/{user_id}/clock-in/makeup
POST /users/{user_id}/clock-in/makeup-all
```

### 用户端

用户端接口统一挂在 `/app/*`，面向终端用户，负责：

- 注册 / 登录
- 绑定工学云账号
- 读取和保存自身配置
- 手动执行任务
- 查看执行记录
- 缺卡查询和补卡
- 日报、周报、月报生成和提交，以及当前类型下一键补全部待补周期

补卡相关接口：

```http
GET /app/clock-in/missing-days
POST /app/clock-in/makeup
POST /app/clock-in/makeup-all
```

报告补交接口：

```http
GET /app/reports/{report_key}/missing-periods
POST /app/reports/{report_key}/generate
POST /app/reports/{report_key}/submit
POST /app/reports/{report_key}/makeup-all
```

## 补卡执行链路

补卡相关代码分布：

- `server/api.py`：接收 `target_dates` 和 `target_type`，校验参数并写审计日志。
- `server/clockin_backfill.py`：归一化远端打卡记录，生成缺卡日期选项。
- `server/task_runner.py`：根据日期、类型和配置时间执行补卡。
- `server/coreApi/MainLogicApi.py`：构造工学云补卡请求并调用远端接口。

补卡请求只补一种类型：

- `target_type=START`：只补上班。
- `target_type=END`：只补下班。

即使某一天同时缺上班和下班，选择 `START` 时也只补上班；选择 `END` 时只补下班。

批量补卡默认按 `CLOCKIN_MAKEUP_BATCH_DELAY_SECONDS` 间隔逐个日期执行。如果远端返回“请求过于频繁”、`429`、`rate limit` 或“IP非法请求过多，已限制访问”，后端会等待后重试当前日期，而不是直接进入下一个日期。重试次数和初始等待时间由 `CLOCKIN_MAKEUP_RATE_LIMIT_RETRIES`、`CLOCKIN_MAKEUP_RATE_LIMIT_RETRY_SECONDS` 控制。

触发 IP 频繁后，批量任务会进入冷却策略：

- 当前日期按指数退避重试。
- 当前日期重试成功后，后续日期之间的间隔提升到 `CLOCKIN_MAKEUP_RATE_LIMIT_COOLDOWN_SECONDS`。
- 当前日期重试耗尽仍然频繁时，后续日期会被标记为跳过并停止继续请求，避免扩大远端限流。

只有手动补卡会启用工学云代理。正常登录、缺卡查询、定时打卡和报告提交会继续直连工学云，不会使用这里配置的代理。

如果配置了 `MOGUDING_PROXY_API_URL`，补卡请求会在提交前获取动态代理。动态代理默认缓存 `MOGUDING_PROXY_TTL_SECONDS` 秒；遇到 IP 频繁或代理连接失败时，会重新调用代理接口获取新 IP 后继续重试。补卡批量结果会记录 `代理切换次数`。

普通登录、定时打卡、报告提交、缺卡查询等非补卡请求如果命中“IP非法请求过多，已限制访问”，会进入普通网络熔断窗口并停止后续工学云请求，避免在已封 IP 的情况下继续扩大限制。

动态代理接口示例：

```env
MOGUDING_PROXY_API_URL=http://capi.51daili.com/traffic/getip?linePoolIndex=1&packid=12&time=2&qty=1&port=1&format=txt&dt=2&ct=1&dtc=5&usertype=17&uid=54638&accessName=your-name&accessPassword=your-pass
```

接口返回 `1.2.3.4:8080` 时，实际使用的代理会变成 `http://your-name:your-pass@1.2.3.4:8080`。也可以使用 `MOGUDING_PROXY_URLS` 配置静态代理池。

管理端 Web 提供「系统设置」→「工学云代理」入口，可配置补卡代理的启用状态、动态代理接口、缓存秒数、接口超时秒数和静态代理列表。

学生补卡使用工学云接口：

```text
attendence/attendanceReplace/v4/save
```

补卡请求关键字段：

| 字段 | 值 |
|------|----|
| `attendanceType` | `REPLACE` |
| `type` | `START` 或 `END` |
| `createTime` | 目标日期 + 上班 / 下班配置时间 |
| `attendenceTime` | `null` |
| `isReplace` | `null` |

## 任务执行链路

执行入口主要有 3 类：

- 定时任务：`scheduler.py` 注册后由 APScheduler 触发。
- 批量任务：`queue_worker.py` 从队列中取任务执行。
- 手动任务：管理端或用户端 API 直接触发。

最终都会进入 `server/task_runner.py`：

- `perform_clock_in`：普通打卡。
- `perform_clock_in_makeup`：补单个日期的一种类型。
- `perform_clock_in_makeup_many`：补多个日期的一种类型。
- `submit_daily_report`：日报提交。
- `submit_weekly_report`：周报提交。
- `submit_monthly_report`：月报提交。

其中补卡只属于手动任务，不会被普通定时打卡任务自动触发。定时打卡只执行 `perform_clock_in`，报告定时任务只执行对应的日报、周报或月报提交。

执行结果会通过 `server/user_runtime.py` 回写到用户记录，包括最近运行时间、状态、日志、登录态和计划信息。

定时任务执行前会写入 `TaskExecutionLock`，同一个用户、同一种定时任务在锁过期前不会被多个 worker 重复执行。批量队列认领使用数据库状态更新，避免同一队列项被重复提交给线程池。运行事件记录在 `TaskExecutionEvent`，HTTP 请求统计记录在 `HttpRequestMetric`，并会携带请求 ID 方便串联入口、任务和告警链路；`/metrics` 和 `/metrics.prom` 会返回任务、批量、锁、请求状态码分布和延迟统计，并通过短 TTL 快照缓存降低重复抓取的数据库压力。

核心业务表已带 `tenant_id`，默认租户为 `default`。管理端用户读写、补卡和报告接口会按登录租户过滤，历史数据迁移时会自动补列并按默认租户兼容 `NULL` 旧值。租户列表、创建和停用属于默认租户平台管理员能力，不对非默认租户管理员开放。

数据库 JSON 备份工具：

```bash
python -m server.backup_cli export backup.json
python -m server.backup_cli import backup.json --replace-existing
```

导出包会附带 manifest 和表校验和，导入前会做完整性校验，避免静默吞掉篡改或不一致的备份数据。生产环境导出默认要求加密密钥；明文导出只应在受控排障场景临时设置 `ALLOW_PLAINTEXT_BACKUP=true`。

## 测试与验证

当前后端单元测试使用 Python 标准库 `unittest`。

```bash
python -m unittest discover -s tests
python -m alembic upgrade head
python scripts/quality_gate.py
```

语法编译检查：

```bash
python -m compileall server
```

空白字符检查：

```bash
git diff --check
```

当前项目已提供轻量质量门禁 `scripts/quality_gate.py`，用于防止重新引入 `utcnow()`、前端 token localStorage 存储、服务器端 `print`、裸 `except/pass`、不带租户上下文的用户读取和用户邀请入口。前端构建验证见 `web/README.md`。
