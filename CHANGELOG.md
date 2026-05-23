# 更新日志

本文档记录 AutoMoGuDing SaaS 的重要变更。版本号建议遵循 `v主版本.次版本.修订号` 格式。

## Unreleased

- 文档：补充 Demo 截图、部署说明、Release 流程、Roadmap 和贡献入口。
- 文档：新增后端说明、前端说明和当前功能速查。

## 2026-05-23

### 新增

- 新增日报 / 周报 / 月报分类型补交能力，每个报告类型都有独立的一键补全部待补周期入口。
- 新增一键补卡限流退避能力，遇到“请求过于频繁”、`429` 或 `rate limit` 时等待后重试当前日期。
- 新增工学云 IP 限制熔断能力，遇到“IP非法请求过多，已限制访问”后会暂停非代理工学云请求；手动补卡代理会切换新 IP 后重试。
- 新增工学云请求代理能力：支持 `MOGUDING_PROXY_API_URL` 动态获取 `ip:端口`，自动读取 `accessName` / `accessPassword` 拼接代理；也支持 `MOGUDING_PROXY_URLS` 静态代理池。
- 新增管理端 Web 全局代理配置入口，可在「系统设置」中维护工学云动态代理接口、缓存秒数、接口超时和静态代理列表。
- 调整工学云代理作用域：代理仅在手动补卡执行阶段启用，正常登录、定时打卡、报告提交和缺卡查询不使用代理。
- 调整报告手动执行限流边界：`立即执行日报 / 周报 / 月报` 不再触发本系统 `/run` 接口的 429 限流，打卡和默认手动运行仍保留限流。
- 调整报告待补周期获取边界：未开启的日报 / 周报 / 月报不会自动查询未提交周期，后端接口也会直接返回空列表。
- 新增补卡和报告补交流程的批量间隔配置：
  - `CLOCKIN_MAKEUP_BATCH_DELAY_SECONDS`
  - `CLOCKIN_MAKEUP_RATE_LIMIT_RETRIES`
  - `CLOCKIN_MAKEUP_RATE_LIMIT_RETRY_SECONDS`
  - `CLOCKIN_MAKEUP_RATE_LIMIT_COOLDOWN_SECONDS`
  - `REPORT_MAKEUP_BATCH_DELAY_SECONDS`
- 新增镜像日期标签说明，默认构建会同时推送 `latest`、分支标签、`YYYYMMDD`、`YYYYMMDD-HHMMSS` 和 `sha-*` 标签。

### 变更

- 修正任务执行边界：普通定时打卡不会自动触发补卡，补卡只通过管理端或用户端手动接口执行。
- 一键补卡保留日期间隔，并在限流后对当前日期重试；当前日期恢复后会降低后续日期请求速度，持续限流时会停止剩余日期，避免继续触发远端风控。
- 一键补交报告按 `daily`、`weekly`、`monthly` 分别处理，不会跨类型混在一起补交。
- 优化 `docker-compose.yml` 和 `docker-compose.image.yml`，透传补卡 / 补交报告的批量间隔和限流重试配置。
- 更新文档中关于 `latest` 的说明：远端 `latest` 被覆盖后，本地已拉取镜像不会自动显示可用更新，需要重新 `pull` 或指定新的日期 / sha 标签。

### 验证

- `python -m unittest discover -s tests`
- `python -m compileall server`
- `git diff --check`

## 2026-05-22

### 新增

- 新增缺卡记录筛选能力，支持从已打卡记录中识别待补日期。
- 新增按类型补卡能力：补卡前选择 `上班` 或 `下班`，一次只补一种类型。
- 新增「补选中」和「全部待补」两种补卡操作。
- 新增管理端补卡接口：
  - `GET /users/{user_id}/clock-in/missing-days`
  - `POST /users/{user_id}/clock-in/makeup`
  - `POST /users/{user_id}/clock-in/makeup-all`
- 新增用户端补卡接口：
  - `GET /app/clock-in/missing-days`
  - `POST /app/clock-in/makeup`
  - `POST /app/clock-in/makeup-all`
- 新增后端单元测试，覆盖打卡记录归一化、补卡请求构造、按类型补卡和批量补卡请求解析。

### 变更

- 学生补卡请求改为调用 `attendence/attendanceReplace/v4/save`。
- 补卡请求体使用 `attendanceType=REPLACE`，`attendenceTime=null`，`isReplace=null`。
- 管理端用户编辑页和用户端设置页的补卡日期改为多选，并按当前补卡类型过滤。
- README 更新到当前实现，补充补卡规则和验证命令。

### 验证

- `python -m unittest discover -s tests`
- `python -m compileall server`
- `npm run build`（在 `web/` 目录）
- `git diff --check`

## 2026-05-15

### 新增

- 管理端能力：后台登录、角色权限、用户管理、用户执行日志、审计日志、通知配置、SMTP 测试、AI 测试、地理编码搜索与逆地理解析。
- 用户端能力：`/u/login`、`/u/register`、`/u`、`/u/settings`。
- 用户自助流程：注册 / 登录、绑定工学云账号、读取自身配置、自动获取打卡地址、保存打卡与报告配置、手动执行任务、查看执行记录、生成日报和提交日报。
- 自动化任务：基于 APScheduler 注册上班打卡、下班打卡、日报、周报和月报任务。
- 批量任务：支持并发执行、失败重试、暂停、恢复、取消和进度查询。
- GitHub Actions 镜像构建流程：支持发布到 GHCR，可选同步到 Docker Hub。

### 变更

- 统一执行结果回写逻辑，将执行状态、日志、最近运行时间、远端登录态和实习计划信息同步回用户数据。
- 前端统一消息提示入口，修正 `createWebHistory()` 模式下的 `401` 未登录跳转。
- 支持本地前后端分离开发和 Docker Compose 一体化部署。
