# FundMasterAI 中文说明

FundMasterAI 是一个集成式课堂演示项目，包含基金与市场数据、投资组合工具、
新闻/行情看板，以及带解释链路的多智能体分析服务。

英文说明见 [README.md](README.md)。

## 一键启动

最终提交和课堂演示优先使用 Docker Compose。它会一次启动前端、Market/News/
Portfolio 三个后端、AI Agent、MySQL 和 Redis。

需要：

- 已安装包含 Docker Compose v2 的 Docker Desktop；
- 能访问公开行情和基金数据源的网络；
- 默认 mock 文案模式不需要 LLM API Key。

在仓库根目录执行：

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

然后打开：

```text
http://localhost:8080/portfolio-overview.html
```

第一次构建需要下载镜像和 Python 依赖，明显慢于后续启动属于正常现象。验收成功
时，最后会看到：

```text
FundMasterAI Docker smoke test passed.
```

如果 `8080` 被占用：

```bash
APP_PORT=8088 docker compose up --build --wait
APP_PORT=8088 docker compose run --rm smoke
```

然后打开 `http://localhost:8088/portfolio-overview.html`。配置、日志、真实 LLM 和故障排查
见 [DOCKER.md](DOCKER.md)。

## 实际运行链路

```text
frontend_new（Nginx 静态站点 + 同源 API 网关）
  -> Market 后端（行情、基金、宏观、全球市场、资金流；Redis 缓存）
  -> News 后端（个股新闻、基金公告）
  -> Portfolio 后端（MySQL 投资组合 CRUD）
  -> AI Agent 服务
       -> 后端 function registry
       -> 确定性特征和基金类型路由
       -> 专业 Agent
       -> Chief 汇总和 analysis_trace 解释链路
```

Docker 默认使用真实公开后端数据，但 LLM 文案使用确定性 mock。这样即使没有 API
Key，也能稳定演示真实服务和取数链路；只有需要展示真实模型生成时才配置
OpenAI-compatible provider。

## 主要目录

| 路径 | 用途 |
|---|---|
| [`frontend_new/`](frontend_new/README.md) | 静态看板和浏览器端联调逻辑 |
| [`backend/`](backend/README.md) | Market、News、Portfolio 三个 Flask 服务 |
| [`ai_agent/fund_llm_engine/`](ai_agent/fund_llm_engine/README.md) | 多智能体基金分析服务 |
| [`docker/`](docker/) | 容器构建、Nginx 路由和端到端 smoke 测试 |

## 文档入口

不要再把所有历史记录都当成当前操作说明；按下面的任务选择权威入口：

| 需求 | 当前应看的文档 |
|---|---|
| 启动完整项目 | [DOCKER.md](DOCKER.md) |
| 理解或单独预览前端 | [frontend_new/README.md](frontend_new/README.md) |
| 不用 Docker 启动后端 | [backend/README.md](backend/README.md) |
| 开发或测试 AI Agent | [ai_agent/fund_llm_engine/README.md](ai_agent/fund_llm_engine/README.md) |
| 查找 AI Agent 中文文档 | [AI Agent 中文索引](ai_agent/fund_llm_engine/docs/README.zh-CN.md) |
| 查看稳定 AI API 字段 | [AI Agent 中文契约](ai_agent/fund_llm_engine/docs/contracts.md) |
| 参与团队协作 | [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md) |

旧周末联调和共享 systemd 云服务器不再属于当前启动链路；Windows 原生 Agent 调试、
旧设计、迁移、handoff 和 benchmark 仍保留作参考。

## 验证项目

完整链路：

```bash
docker compose config --quiet
docker compose up --build --wait
docker compose run --rm smoke
```

## 真实 LLM 模式

干净 clone 默认使用 mock 文案。需要真实 OpenAI-compatible 模型时：

```bash
cp ai_agent/fund_llm_engine/.env.example ai_agent/fund_llm_engine/.env
```

填写 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 后重建 Agent 和前端：

```bash
docker compose up -d --build --wait agent frontend
```

本地 `.env` 已被 Git 忽略，不能提交。Provider 和模型目录说明见
[provider_setup.md](ai_agent/fund_llm_engine/docs/provider_setup.md)。

## 已知边界

- 公开数据源可能变慢或临时不可用；冷启动和 smoke 需要联网，偶尔会比本地单测慢。
- AI 评分是可解释的启发式分析 demo，不是经过统计校准的收益预测或自动交易系统。
- 债券分析深度受上游真实提供的久期、期限、发行人和信用评级字段限制。
- 部分安全和账户控件会明确标记为浏览器本地演示，不等同于生产身份系统。

## 停止

```bash
docker compose down
```

该命令会同时保留 MySQL 数据卷和 Redis 缓存卷。只有明确允许永久删除本地演示
数据库和可恢复的 Market 缓存时，才执行 `docker compose down -v`。
