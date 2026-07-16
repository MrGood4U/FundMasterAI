# FundMasterAI Backend

FundMasterAI 后端由三个独立的 Flask 微服务组成：Market Backend（行情）、News
Backend（资讯）、Portfolio Backend（投资组合管理）。完整演示优先按仓库根目录
[`DOCKER.md`](../DOCKER.md) 启动；本文件用于不使用 Docker 的后端开发和调试。

## 环境要求

- Python >= 3.11
- pip >= 3.11
- MySQL（仅 portfolio_backend 需要）
- Redis（可选；market_backend 可用它持久化和复用已启用的数据缓存）

## 三个后端概览

| 后端 | 端口 | 功能 | 需要 MySQL | 需要 Redis | Function Calling |
|---|---|---|---|---|
| [market_backend](market_backend/) | **5001** | A 股 / 公募基金 / 加密货币 实时行情、历史数据、K 线、技术指标 | 否 | 可选 | `GET /api/market/functions` |
| [news_backend](news_backend/) | **5000** | A 股近期新闻、公募基金公告查询 | 否 | 否 | `GET /api/news/functions` |
| [portfolio_backend](portfolio_backend/) | **5002** | 交易记录、持仓管理、价格告警、自选关注 | **是** | 否 | `GET /api/portfolio/functions` |

详细说明请参见各后端目录下的 `README.md`。

## 安装依赖（原生运行）

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r ../docker/requirements/market.txt
python -m pip install -r ../docker/requirements/news.txt
python -m pip install -r ../docker/requirements/portfolio.txt
openbb-build
```

上面的 requirements 与 Docker 镜像使用同一份版本清单，避免 README 中手写的包名
再次落后于实际部署。Market 的 OpenBB 依赖安装后还需要运行一次 `openbb-build`。

## 配置文件

各后端配置文件位置：

| 后端 | 配置文件 | 说明 |
|---|---|---|
| market_backend | `apis/config.ini` | 原生运行的 API 密钥、缓存与 Redis 配置 |
| news_backend | 无 | 仅通过环境变量配置（均有默认值） |
| portfolio_backend | `config.ini` | MySQL 连接信息 + market_backend 地址（必须填写） |

配置优先级并不完全相同：Portfolio 是环境变量 > `config.ini` > 默认值；News 只读
环境变量；Market 的缓存/Redis 当前以 `apis/config.ini` 为主，HTTP 端口读环境变量，
OpenBB/FMP 密钥则是环境变量优先。Docker 不会复制本机的 `apis/config.ini`，而是
使用 `docker/market-config.container` 和根目录中由 Git 忽略的 `.env`。具体字段以
各服务 README 和 `config.py` 为准。

## MySQL 数据库初始化

**只有 portfolio_backend 需要 MySQL**，其他两个后端不需要。

在启动 portfolio_backend 之前，必须先在 MySQL 中创建数据库并运行建表脚本：

```bash
# 在 portfolio_backend 目录下执行
mysql -u root -p fundmaster_db < init.sql
```

`init.sql` 会创建 `user_profile`、`transactions`、`price_alert`、`watchlist` 四张表。

## Redis 数据库初始化

**只有 market_backend 可选需要 Redis**，其他两个后端不需要。

不需要建表或预写数据；原生运行时在 `market_backend/apis/config.ini` 中配置 Redis
即可。Docker Compose 会自动启动 Redis，并把缓存保存在 `redis_data` 数据卷中。

## Function Calling 接口

LLM agent 可通过以下端点自动发现各后端的功能接口：

- Market Backend: `GET http://localhost:5001/api/market/functions`
- News Backend: `GET http://localhost:5000/api/news/functions`
- Portfolio Backend: `GET http://localhost:5002/api/portfolio/functions`

各端点均支持 `?tag=xxx` 参数按类别筛选，具体 tag 值见各后端 README。

## 启动与停止

### 逐个启动

```bash
# 进入各后端目录，后台启动（日志写入各自目录下的 app.log）
cd market_backend && bash start.sh
cd news_backend && bash start.sh
cd portfolio_backend && bash start.sh

# 停止
cd market_backend && bash stop.sh
cd news_backend && bash stop.sh
cd portfolio_backend && bash stop.sh
```

### 一键启动/停止

```bash
# 在 backend/ 目录下执行
bash start_all.sh   # 按 market → news → portfolio 顺序启动
bash stop_all.sh    # 按相同顺序停止
```

`start_all.sh` 不负责启动 MySQL；原生启动 Portfolio 前，必须先完成上面的数据库
初始化。只调试 Market/News 或基金分析取数时，可以只启动需要的服务。

启动后各后端 PID 写入各自的 `app.pid` 文件，可通过 `cat market_backend/app.pid` 等方式查看。

## 日志

各后端日志分别写入各自目录下的 `app.log`：

- `market_backend/app.log`
- `news_backend/app.log`
- `portfolio_backend/app.log`

查看实时日志：

```bash
tail -f market_backend/app.log
tail -f news_backend/app.log
tail -f portfolio_backend/app.log
```

## 端口规划

```
5000 — news_backend
5001 — market_backend
5002 — portfolio_backend
```

建议确保以上端口未被其他进程占用。`news_backend` 的端口当前硬编码为 5000，其余后端可通过环境变量修改。

## 目录结构

```
backend/
├── start_all.sh              # 一键启动所有后端
├── stop_all.sh               # 一键停止所有后端
├── market_backend/            # 市场行情后端 (5001)
│   ├── README.md
│   ├── app.py
│   ├── config.py
│   ├── start.sh / stop.sh
│   ├── apis/
│   ├── views/
│   ├── services/
│   ├── daos/
│   ├── utils/
│   └── tests/
├── news_backend/             # 新闻资讯后端 (5000)
│   ├── README.md
│   ├── app.py
│   ├── config.py
│   ├── start.sh / stop.sh
│   ├── apis/
│   ├── views/
│   ├── services/
│   ├── daos/
│   └── utils/
└── portfolio_backend/        # 投资组合管理后端 (5002)
    ├── README.md
    ├── app.py
    ├── config.py
    ├── config.ini
    ├── init.sql
    ├── alert_checker.py
    ├── start.sh / stop.sh
    ├── apis/
    ├── views/
    ├── services/
    ├── daos/
    ├── utils/
    └── tests/
```
