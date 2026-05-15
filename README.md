# AutoMoGuDing SaaS（工学云打卡管理平台）

AutoMoGuDing SaaS 是一个面向多用户托管的工学云自动化平台，提供管理端与用户端两套 Web 界面，支持自动打卡、日报 / 周报 / 月报提交、批量执行，以及 AI 生成报告内容。

## 功能概览

- **管理端：** 管理用户、查看审计日志、配置通知、批量执行任务、测试 AI 与地理编码能力。
- **用户端：** 通过 `/u` 入口注册 / 登录、绑定工学云账号、修改个人打卡与报告配置、手动执行任务、生成并提交日报。
- **自动调度：** 基于 APScheduler 为每个用户注册上下班打卡和报告任务。
- **批量执行：** 通过队列 worker 并发处理批量任务，支持暂停、取消与失败重试。
- **运行时同步：** 将工学云登录态、计划信息、执行结果等运行时数据回写到数据库 JSON 字段。

## 更新日志

### 当前版本（2026-05-15）

- **管理端能力完成：** 支持后台登录、角色权限、用户管理、用户执行日志、审计日志、通知配置、SMTP 测试、AI 测试、地理编码搜索与逆地理解析。
- **用户端能力完成：** 恢复 `/u/login`、`/u/register`、`/u`、`/u/settings` 四个入口，用户端拥有独立认证状态和请求入口，不再与后台管理端登录态混用。
- **用户自助流程完成：** 支持用户注册 / 登录、绑定工学云账号、读取自身配置、自动获取打卡地址、保存打卡与报告配置、手动执行任务、查看执行记录、生成日报和提交日报。
- **自动化任务完成：** 基于 APScheduler 为单个用户注册上班打卡、下班打卡、日报、周报和月报任务，并在配置变更后重建对应 job。
- **批量任务完成：** 管理端可发起批量运行，后端队列 worker 支持并发执行、失败重试、暂停、恢复、取消和进度查询。
- **运行时回写完成：** 抽取统一的执行结果回写逻辑，将执行状态、日志、最近运行时间、远端登录态和实习计划信息同步回用户数据。
- **安全与配置完成：** 支持 MySQL 数据库、JWT 登录态、角色校验、基础限流、敏感字段加密存储，并通过 `.env` 管理生产配置。
- **前端一致性完成：** 统一前端消息提示入口，修正 `createWebHistory()` 模式下的 `401` 未登录跳转，并清理 Vue 模板残留文件。
- **部署与工程维护完成：** 支持本地前后端分离开发、Docker Compose 一体化部署、FastAPI 托管 `web/dist` 静态资源，并补齐 `.gitignore` 以忽略环境变量、运行数据、模型文件、依赖目录和本地工具缓存。
- **镜像发布流程完成：** 新增 GitHub Actions 工作流 `.github/workflows/docker-publish.yml`，支持推送 `main` / `master`、发布 `v*` 标签或手动触发时自动构建 Docker 镜像，并发布到 GitHub Container Registry (GHCR)；配置 Docker Hub 密钥后可同步推送到 Docker Hub。

## 技术栈

- **后端：** FastAPI + SQLModel + MySQL
- **前端：** Vue 3 + Vite + Pinia + Vue Router + Element Plus
- **任务调度：** APScheduler
- **部署方式：** 本地前后端分离开发，或 Docker Compose 一体化部署

## 架构说明

### 1. 后端启动流程

`server/main.py` 是后端入口。应用启动时不只会拉起 API，还会执行以下初始化动作：

- 建表并补齐运行时列
- 初始化管理员种子账号
- 检查并下载验证码识别所需的 ONNX 模型
- 启动 APScheduler 定时调度器
- 启动批量任务 queue worker
- 在 `web/dist` 存在时直接托管前端静态资源，并处理 SPA fallback

### 2. 双 API 面

`server/api.py` 同时承载两套接口：

- **管理端 API：** 面向 `admin`、`operator`、`viewer` 等角色
- **用户端 API：** 统一挂在 `/app/*`，面向终端用户

用户端当前已接回以下典型能力：

- `/app/auth/register`
- `/app/auth/login`
- `/app/me`
- `/app/bind`
- `/app/run`
- `/app/execution`
- `/app/reports/daily/generate`
- `/app/reports/daily/submit`

### 3. 任务执行链路

项目的执行链路集中在以下几个模块：

- `server/user_runtime.py`：负责在数据库模型和任务运行配置之间做桥接
- `server/scheduler.py`：为单用户注册定时打卡 / 报告任务
- `server/queue_worker.py`：执行批量任务队列
- `server/task_runner.py`：真正协调工学云接口、AI 报告生成、图片上传和消息推送

无论是**定时执行**、**批量执行**还是**用户手动执行**，最终都会汇总到 `server/task_runner.py`。

### 4. 前端结构

前端位于 `web/`，主要由两套入口构成：

- **管理端：** `/login` 进入后台，使用 `web/src/stores/auth.js` 和 `web/src/api/http.js`
- **用户端：** `/u/login`、`/u/register`、`/u`、`/u/settings`，使用 `web/src/stores/userAuth.js` 和 `web/src/api/userHttp.js`

`web/src/router/index.js` 负责两套认证流和路由守卫的分流。

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+（建议）
- MySQL 8+

## 本地开发

### 1. 准备 `.env`

后端默认从项目根目录读取 `.env`。当前数据库**只支持 MySQL**，必须配置 `DATABASE_URL`。

最小示例：

```env
DATABASE_URL=mysql+pymysql://automoguding:automoguding123@127.0.0.1:3306/automoguding?charset=utf8mb4
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123456
SCHEDULER_TIMEZONE=Asia/Shanghai
GEOCODE_PROVIDER=osm
```

可选配置：

```env
APP_SECRET=please-change-me-in-production
SCHEDULER_JITTER_SECONDS=600
SCHEDULER_REPORT_JITTER_SECONDS=0
AMAP_KEY=your-amap-key
```

说明：

- `DATABASE_URL` 必填，且必须以 `mysql+pymysql://` 开头。
- 生产环境应显式配置 `APP_SECRET`。
- 如果使用高德地理编码，请设置 `GEOCODE_PROVIDER=amap` 并提供 `AMAP_KEY`。

### 2. 启动后端

```bash
pip install -r server/requirements.txt
python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8147
```

启动后可访问：

- API 文档：`http://localhost:8147/docs`
- OpenAPI：`http://localhost:8147/openapi.json`

### 3. 启动前端

```bash
cd web
npm install
npm run dev
```

启动后访问：

- 前端页面：`http://localhost:5173`

Vite 开发服务器会将 `/api` 代理到本地后端 `http://127.0.0.1:8147`。

### 4. 构建前端

```bash
cd web
npm run build
npm run preview
```

## Docker 部署

项目支持通过 Docker Compose 一体化启动：

```bash
docker compose up -d --build
```

当前 `docker-compose.yml` 会：

- 构建应用镜像
- 暴露 `8147` 端口
- 将 `./data/images` 挂载到容器内图片目录
- 通过环境变量把 `DATABASE_URL`、调度时区、管理员账号等配置注入应用

访问入口：

- 应用首页：`http://localhost:8147`
- API 文档：`http://localhost:8147/docs`

### GitHub 自动构建镜像

仓库已提供 `.github/workflows/docker-publish.yml`，用于在 GitHub Actions 中自动构建并发布镜像到 GHCR，也可以同步推送到 Docker Hub。

触发方式：

- 推送到 `main` 或 `master` 分支：构建并推送分支镜像，同时默认分支会更新 `latest` 标签。
- 推送 `v*` 标签：构建并推送对应版本镜像，例如 `v1.0.0`。
- Pull Request：只执行构建验证，不推送镜像。
- 手动触发：可在 GitHub Actions 页面运行 `Docker Publish` 工作流。

镜像地址格式：

```text
ghcr.io/<owner>/<repo>:latest
```

Docker Hub 同步发布需要在 GitHub 仓库的 `Settings` → `Secrets and variables` → `Actions` 中配置以下 Secrets：

```text
DOCKERHUB_USERNAME=你的 Docker Hub 用户名
DOCKERHUB_TOKEN=你的 Docker Hub Access Token
DOCKERHUB_REPOSITORY=你的 Docker Hub 镜像名，可选，例如 username/automoguding-saas
```

如果不配置 `DOCKERHUB_REPOSITORY`，工作流会默认使用 `DOCKERHUB_USERNAME/<repo>` 作为 Docker Hub 镜像名。

如果仓库是私有仓库，需要在 GitHub 的 Package 设置中确认 GHCR 镜像可见性和拉取权限。GHCR 发布默认使用 GitHub 自动注入的 `GITHUB_TOKEN`。

## 常用入口

### 管理端

- 登录页：`/login`
- 默认首页：`/`

### 用户端

- 登录页：`/u/login`
- 注册页：`/u/register`
- 用户工作台：`/u`
- 用户设置页：`/u/settings`

## 目录结构

```text
automoguding-saas/
├─ server/                  # FastAPI 后端、调度器、任务执行与数据模型
├─ web/                     # Vue 3 前端
├─ docs/                    # 设计 / 计划等项目文档
├─ docker-compose.yml       # 容器编排配置
├─ Dockerfile               # 前端构建 + 后端运行镜像
└─ CLAUDE.md                # 面向 Claude Code 的仓库工作说明
```

## 关键配置与运行行为

- 应用启动时会自动建表、补列、种子管理员、检查模型、启动调度器和队列线程，因此排查启动问题时要把这些副作用一起考虑。
- 用户配置变更后，接口层通常会先移除旧 job，再按新配置重新注册 job。
- 容器部署时由 FastAPI 直接提供构建后的 `web/dist`；本地开发则通常使用 `5173` 前端 + `8147` 后端。
- 工学云账号密码、SMTP 密码等敏感信息为加密存储。
- `/ai/test` 默认只允许公网 HTTPS 地址，不允许本机或内网地址。

## 开发说明

### 当前可用命令

后端：

```bash
pip install -r server/requirements.txt
python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8147
```

前端：

```bash
cd web
npm install
npm run dev
npm run build
npm run preview
```

### 关于 lint / test

当前仓库**没有统一的标准化 lint 或测试脚本**。`web/package.json` 仅提供 `dev`、`build`、`preview` 三个脚本，因此不要假设仓库内已经存在 `npm test`、`npm run lint` 等命令。

## 补充说明

仓库当前以 `README.md` 作为唯一主文档。

如果文档与当前实现存在差异，请以本 README、`CLAUDE.md` 和实际代码为准。
