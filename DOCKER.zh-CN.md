# FundMasterAI Docker 运行说明

这套配置会一次启动完整项目：

- `frontend`：Nginx 静态前端和统一 API 反向代理；
- `market`：行情与基金数据后端；
- `news`：新闻后端；
- `portfolio`：投资组合后端；
- `agent`：AI Agent；
- `mysql`：Portfolio 所需数据库；
- `redis`：Market 指数排名、基金目录等已启用数据源的可恢复缓存。

默认只把前端端口暴露给宿主机，其他服务都留在 Compose 内部网络。

## 1. 启动

要求安装 Docker Desktop（含 Docker Compose v2）。在仓库根目录执行：

```bash
docker compose up --build --wait
```

浏览器打开：

```text
http://localhost:8080/ai-insights.html
```

如果 `8080` 已占用：

```bash
APP_PORT=8088 docker compose up --build --wait
```

然后打开 `http://localhost:8088/ai-insights.html`。

`APP_PORT=8088` 是这次 Compose 配置的一部分。后续执行 `run`、`up` 等 Compose
命令时要继续传入同一个值，或者把 `APP_PORT=8088` 写进根目录的本地 `.env`。例如：

```bash
APP_PORT=8088 docker compose run --rm smoke
```

如果后续命令漏掉该变量，Compose 可能把前端重新创建到默认 `8080`，并在端口已被
占用时报错。

第一次构建需要下载 Python、Nginx、MySQL、Redis 镜像和依赖，耗时会明显长于以后
启动。Market/News 的财经数据仍来自真实外部数据源；默认 `mock` 的只是 LLM 文案，
所以演示机器需要联网。

老师或新成员从干净 clone 开始时，不需要先创建 `.env`、安装 Python 依赖或初始化
MySQL。Compose 会使用仓库内的安全演示默认值并自动创建数据库表。建议先确认配置
可以被解析，再启动：

```bash
docker compose config --quiet
docker compose up --build --wait
```

## 2. 一键验收

服务全部健康后执行：

```bash
docker compose run --rm smoke
```

该测试会从 Nginx 的同源入口依次检查：

1. Overview、Equity、Debt、Analytics、Markets、News、AI Insights、Settings 等 10 个主要页面；
2. Market、News、Portfolio 的 function registry；
3. Agent function registry 和模型目录；
4. `000001` 的真实后端数据 + mock LLM 分析，并校验 NAV 与 Agent 输出。

smoke 是提交前的最低验收，不等同于页面视觉验收。通过后还应至少在浏览器打开
`ai-insights.html`，等待真实数据加载完成，并切换一次侧栏页面确认没有一直停留在
Loading 状态。

指定其他演示基金：

```bash
SMOKE_FUND_CODE=000171 docker compose run --rm smoke
```

页面手工演示可依次输入：`000001`、`003358`、`161725`、`000171`。

## 3. 常用维护命令

```bash
# 查看状态
docker compose ps

# 查看全部日志
docker compose logs -f

# 只看某个服务
docker compose logs -f agent

# 停止并删除容器，保留 MySQL 数据和 Redis 缓存
docker compose down

# 重新构建某个服务
docker compose build agent
docker compose up -d agent frontend
```

只有明确要同时清空本地演示数据库和 Market 缓存时才运行：

```bash
docker compose down -v
```

`-v` 会删除 Compose 创建的 `mysql_data` 和 `redis_data` 数据卷。

## 4. 配置与真实 LLM

默认账号仅用于本地课堂演示，宿主机端口也只绑定到 `127.0.0.1`。如果只需要
自定义端口或数据库配置，请在**第一次启动前**执行：

```bash
cp .env.docker.example .env
```

编辑根目录 `.env` 后启动容器。原先把 LLM 配置也放在根目录 `.env` 的方式仍然兼容，
但新环境推荐统一使用 Agent 自己的 `.env`：

```bash
cp ai_agent/fund_llm_engine/.env.example ai_agent/fund_llm_engine/.env
```

如果 Market Hub 需要通过 OpenBB/FMP 获取全球指数，请把密钥只写入根目录中由 Git
忽略的 `.env`：

```text
FMP_API_KEY=你的密钥
```

Market 容器会在每次创建或重建时从该环境变量读取密钥；密钥不会复制进镜像，也不应
写入 `docker/market-config.container`、`compose.yaml` 或任何提交到 Git 的文件。

MySQL 用户、密码和数据库只会在数据卷首次初始化时创建。如果 `mysql_data`
已经存在，之后再改 `FM_MYSQL_*` 不会自动迁移旧账号。此时应手工修改 MySQL
账号，或者在确认不需要现有演示数据后执行 `docker compose down -v`，再按新配置
启动；`-v` 会永久删除该 Compose 项目的数据库数据，并同时清空 Redis 缓存。

在 `ai_agent/fund_llm_engine/.env` 中，真实 LLM 至少配置：

```text
LLM_MOCK_MODE=false
LLM_API_KEY=你的密钥
LLM_BASE_URL=OpenAI-compatible API 地址
LLM_MODEL=模型名
```

如果已经在 Agent 目录维护了本地 `.env`，不需要复制、移动或额外传
`--env-file`。Compose 会在启动 Agent 容器时自动只读加载：

```text
ai_agent/fund_llm_engine/.env
```

配置优先级为：安全的 `.env.docker.example` mock 默认值 < 可选的根目录 `.env`
（兼容原 Docker 用法）< Agent 目录 `.env`（最高）。因此直接执行普通启动命令即可：

```bash
docker compose up -d --build --wait
```

没有任何本地 `.env` 的干净 clone 会继续使用 mock 模式；存在 Agent `.env` 时会
自动使用其中的 `LLM_MOCK_MODE`、key、base URL 和模型。Compose 不会修改这些文件，
它们也继续由 Git 忽略，因此每位团队成员可以保留自己的配置。

根目录 `.env`、Agent 自己的 `.env`、本机 `config.ini`、虚拟环境、日志和 PID 文件都被 `.dockerignore` 排除，不会复制进镜像。不要把真实密钥写入 `compose.yaml` 或提交到 Git。

## 5. 服务端口

| 服务 | 容器内端口 | 默认宿主机端口 |
|---|---:|---:|
| Frontend / API gateway | 80 | 8080 |
| Market | 5001 | 不暴露 |
| News | 5000 | 不暴露 |
| Portfolio | 5002 | 不暴露 |
| Agent | 5003 | 不暴露 |
| MySQL | 3306 | 不暴露 |
| Redis | 6379 | 不暴露 |

AI Insights 主链路通过同源路径访问 `/api/market/*`、`/api/news/*`、
`/api/portfolio/*` 和 `/api/ai/*`，因此不需要改现有 AI Insights 页面代码。
Portfolio Overview 已通过同源 `/api/ai/portfolio/analyze` 接入 Agent；完整 Compose
启动会同时提供它需要的 Portfolio 后端、MySQL 和 Agent 服务。

## 6. 常见问题

### 构建很慢

第一次构建会下载基础镜像、编译部分依赖并生成 OpenBB 资源。只要日志仍在下载或
安装依赖，就不代表卡死。后续没有依赖变化时会复用 Docker layer cache。

### 服务健康但页面数据暂时为空

健康检查只证明服务可访问；行情和基金数据仍依赖公开上游。先查看：

```bash
docker compose logs --tail=200 market news agent
```

如果是上游临时超时，可稍后重试 smoke。不要为了让页面“有数据”而把假数据写进
真实数据字段。

### 端口占用

只需要修改宿主机前端端口，容器内端口不变：

```bash
APP_PORT=8088 docker compose up -d --wait
```

### 如何确认真正启动成功

以下三项都满足才算完整启动：

1. `docker compose ps` 中长期服务均为 healthy；
2. `docker compose run --rm smoke` 最终通过；
3. 浏览器实际打开页面并看到数据加载后的界面。
