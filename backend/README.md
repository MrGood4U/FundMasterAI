# FundMasterAI Backend

FundMasterAI 后端由三个独立的 Flask 微服务组成：Market Backend（行情）、News Backend（资讯）、Portfolio Backend（投资组合管理）。三个服务可独立启动，也可通过 `start_all.sh` 一键全部启动。

## 环境要求

- Python >= 3.11
- pip >= 3.11
- MySQL（仅 portfolio_backend 需要）
- Redis（可有, market_backend可以配置缓存加快请求速度）

## 三个后端概览

| 后端 | 端口 | 功能 | 需要 MySQL | 需要 Redis | Function Calling |
|---|---|---|---|---|
| [market_backend](market_backend/) | **5001** | A 股 / 公募基金 / 加密货币 实时行情、历史数据、K 线、技术指标 | 否 | 可选 | `GET /api/market/functions` |
| [news_backend](news_backend/) | **5000** | A 股近期新闻、公募基金公告查询 | 否 | 否 | `GET /api/news/functions` |
| [portfolio_backend](portfolio_backend/) | **5002** | 交易记录、持仓管理、价格告警、自选关注 | **是** | 否 | `GET /api/portfolio/functions` |

详细说明请参见各后端目录下的 `README.md`。

## 安装依赖

```bash
# market_backend
pip3.11 install flask flask-openapi3 akshare pandas numpy efinance okx forex-python
pip3.11 install -U "flask-openapi3[swagger,redoc]"

# news_backend
pip3.11 install flask akshare pandas

# portfolio_backend
pip3.11 install flask pymysql requests
```

## 配置文件

各后端配置文件位置：

| 后端 | 配置文件 | 说明 |
|---|---|---|
| market_backend | `apis/config.ini` | OKX API 密钥（使用加密货币接口时必须填写） |
| news_backend | 无 | 仅通过环境变量配置（均有默认值） |
| portfolio_backend | `config.ini` | MySQL 连接信息 + market_backend 地址（必须填写） |

所有后端均支持通过同名环境变量覆盖配置文件中的值（环境变量优先级最高）。

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

不需要进行初始化, 修改market_backend下的config.ini配置redis即可.

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
