# FundMasterAI Docker 运行说明

这套配置会一次启动完整项目：

- `frontend`：Nginx 静态前端和统一 API 反向代理；
- `market`：行情与基金数据后端；
- `news`：新闻后端；
- `portfolio`：投资组合后端；
- `agent`：AI Agent；
- `mysql`：Portfolio 所需数据库；
- `redis`：Market 指数排名等可恢复缓存。

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

第一次构建需要下载 Python、Nginx、MySQL 镜像和依赖，耗时会明显长于以后启动。Market/News 的财经数据仍来自真实外部数据源；默认 `mock` 的只是 LLM 文案，所以演示机器需要联网。

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

# 停止并删除容器，保留 MySQL 数据
docker compose down

# 重新构建某个服务
docker compose build agent
docker compose up -d agent frontend
```

只有明确要清空本地演示数据库时才运行：

```bash
docker compose down -v
```

`-v` 会删除 Compose 创建的 MySQL 数据卷。

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
启动；`-v` 会永久删除该 Compose 项目的数据库数据。

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
Portfolio Overview 中尚未接入本地 Agent 的旧 AI widget 不属于本次 Docker 接线范围。
