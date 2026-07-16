# Market Backend

市场行情后端，提供 A 股、公募基金、加密货币的实时行情、历史数据、K 线、技术指标等数据接口，以及 Function Calling 函数定义供 LLM agent 发现和调用。

## 环境要求

- Python >= 3.11
- pip >= 3.11

## 安装依赖

在仓库根目录使用与 Docker 镜像相同的锁定依赖：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r docker/requirements/market.txt
openbb-build
```

`docker/requirements/market.txt` 是当前依赖清单的权威来源，其中包含 AkShare、Redis、
OpenBB、YFinance 和 `pysqlite3`。不要在 README 里另维护一份容易过期的手写包列表。
部分云服务器的 Python 缺少 `_sqlite3`；当前 `app.py` 会把已安装的 `pysqlite3`
注册为兼容实现。

## 配置文件

### `apis/config.ini`（主配置文件）

原生运行时的持久化配置集中在 `apis/config.ini`，无需环境变量也可启动。Docker 构建
会刻意排除本机的该文件，并用 `docker/market-config.container` 作为容器配置，避免
把本地密钥复制进镜像。文件分为以下段：

#### `[okx]` — OKX API 密钥（使用加密货币接口时才需要）

```ini
[okx]
api_key = 你的_api_key
api_secret = 你的_api_secret
api_pass = 你的_api_passphrase
```

#### `[tick_flow]` — TickFlow API 密钥（个股资金流向接口）

```ini
[tick_flow]
api_key = 你的_api_key
```

#### `[openbb]` — OpenBB FMP API 密钥（全球指数/汇率/宏观矩阵）

```ini
[openbb]
fmp_api_key = 你的_fmp_api_key
```

OpenBB/FMP 是例外：`FMP_API_KEY` 环境变量优先，其次是兼容变量
`OPENBB_FMP_API_KEY`，最后才读取这里的 `fmp_api_key`。Docker 用户应把
`FMP_API_KEY` 写在根目录由 Git 忽略的 `.env` 中，以便重建容器后继续生效。

#### `[redis]` — Redis 连接（缓存层依赖）

```ini
[redis]
redis_host = localhost
redis_port = 6379
redis_db = 0
redis_password =
```

> **优先级**：`config.ini` > 环境变量 > 默认值。即如果 `config.ini` 有值就用它，否则查环境变量（`REDIS_HOST` / `REDIS_PORT` / `REDIS_DB`），都没有才用默认值。
>
> **启动行为**：启动时自动探测 Redis。如果 Redis 不可达，整个缓存层静默禁用 —— 不会重复尝试连接，不会打印重复日志，直接走实时 API 请求。

#### `[cache]` — 缓存开关与间隔

每个数据源可独立开启/关闭，并配置刷新间隔（秒）。禁用的数据源不会被预热，也不会被周期性刷新。

```ini
[cache]
# ---- A 股行情 ----
stock_spot_em_enabled = true     # 东方财富 A 股实时行情
stock_spot_em_interval = 600     # 刷新间隔（秒，下同）
stock_spot_sina_enabled = true   # 新浪 A 股实时行情
stock_spot_sina_interval = 600

# ---- 公募基金（东方财富）----
fund_etf_spot_em_enabled = true  # ETF 实时行情
fund_etf_spot_em_interval = 600
fund_lof_spot_em_enabled = false # LOF 实时行情
fund_lof_spot_em_interval = 30

# ---- 公募基金（同花顺）----
fund_ths_spot_enabled = true     # 基金分类行情（全量，约 10000 条）
fund_ths_spot_interval = 600

# ---- 其他缓存 ----
fund_name_list_enabled = false   # 基金名称列表（约 20000 条）
fund_name_list_interval = 3600
fund_rank_enabled = false        # 基金排行榜
fund_rank_interval = 300
fund_value_est_enabled = false   # 基金估值
fund_value_est_interval = 30
fund_info_index_enabled = false  # 指数基金信息
fund_info_index_interval = 60

# ---- 全球指数 ----
global_index_rank_enabled = true  # 全球指数排行（YFinance）
global_index_rank_interval = 300

# ---- 压缩 ----
compression_threshold = 1048576  # 大于此字节数（1 MiB）的 JSON 才 gzip 压缩
compression = false              # 是否启用 gzip（true/false）
```

> **设计说明**：数据量较大的源（如 `fund_ths_spot` 约 10000 条、股票行情约 5000 条）建议开启缓存，前端请求将直接从 Redis 读取（毫秒级），而非每次等待 akshare 实时拉取（秒级）。个人投资分析场景不需要高频数据，600 秒（10 分钟）刷新一次即可。

### `apis/config.py`（API 密钥读取器）

从 `config.ini` 读取 OKX、TickFlow、OpenBB 的 API 密钥，提供 `get_okx_api_key()`、
`get_tickflow_api_key()`、`get_openbb_fmp_api_key()` 等函数供各 API 模块调用；其中
FMP 读取顺序为 `FMP_API_KEY` > `OPENBB_FMP_API_KEY` > `config.ini`。

### `config.py`（应用配置类）

Flask 应用的全局配置（`Config` 类），从 `apis/config.ini` 的 `[cache]` 和 `[redis]` 段读取所有配置项，同时兼容环境变量覆盖。缓存开关/间隔、Redis 连接、MySQL 连接、HTTP 端口等配置均集中在此。

### 环境变量

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `MARKET_HTTP_PORT` | `5001` | 后端监听端口 |
| `MYSQL_HOST` | `localhost` | MySQL 地址 |
| `MYSQL_USER` | `root` | MySQL 用户名 |
| `MYSQL_PASSWORD` | `password` | MySQL 密码 |
| `MYSQL_DB` | `fundmaster_db` | MySQL 数据库名 |
| `REDIS_HOST` | `localhost` | Redis 地址（`config.ini` 优先） |
| `REDIS_PORT` | `6379` | Redis 端口（`config.ini` 优先） |
| `REDIS_DB` | `0` | Redis 数据库编号（`config.ini` 优先） |
| `FMP_API_KEY` | 空 | OpenBB/FMP 密钥（最高优先级；Docker 推荐） |
| `OPENBB_FMP_API_KEY` | 空 | FMP 兼容变量，仅在 `FMP_API_KEY` 为空时使用 |

> MySQL 配置项当前预留，实际 DAO 层为内存 mock 实现，不连接数据库。

## MySQL 数据库

不需要。本后端无需提前创建数据库表。

## 端口

- 默认端口：**5001**
- 可通过环境变量 `MARKET_HTTP_PORT` 修改

## 基金目录、排行与持仓

- `GET /api/market/fund_public/fund_name_list` 返回真实基金目录；前端会把成功结果在
  浏览器缓存 24 小时，不再提供硬编码的假基金兜底。
- `POST /api/market/fund_public/rank` 的上游收益字段可能缺失；Fund Rankings 和 QDII
  排行所用的前端请求路径会把响应中的非有限数值按缺失值解析。
- `POST /api/market/fund_public/portfolio_hold_stock` 和
  `POST /api/market/fund_public/portfolio_hold_bond` 接收 `code`、可选 `year`，并返回
  该年份响应中的最新季度。当前 AkShare `1.18.64` 对应的东方财富请求缺少必要
  Referer，因此代码使用隔离的直连适配器分别请求股票和债券持仓；没有数据时返回
  空列表，不生成演示持仓。

这些持仓仍是基金披露数据，只能支持已披露证券和占净值比例；它们不会自动补出久期、
信用评级、发行人分类或完整底层穿透。

## Function Calling 接口文档

启动后访问以下端点获取 LLM agent 可用的全部函数定义：

```
GET http://localhost:5001/api/market/functions
```

支持按类别筛选：

```
GET http://localhost:5001/api/market/functions?tag=stock    # 仅股票
GET http://localhost:5001/api/market/functions?tag=fund     # 仅基金
GET http://localhost:5001/api/market/functions?tag=crypto   # 仅加密货币
```

函数定义源码位于 `utils/function_registry.py`。当前 registry 有 56 个函数，覆盖 A 股、
公募基金、可转债、加密货币、全球指数/汇率、宏观数据和资金流等类别。数量会随接口
扩展而变化；运行时以 `GET /api/market/functions` 的返回为准。

## 启动与停止

```bash
# 启动（后台运行，日志写入 app.log）
bash start.sh

# 停止
bash stop.sh
```

启动后 PID 写入 `app.pid`，可通过 `cat app.pid` 查看进程 ID。

## 日志

日志文件：`app.log`（位于 market_backend 目录下）

所有标准输出和标准错误均重定向到此文件。查看实时日志：

```bash
tail -f app.log
```

## 项目结构

```
market_backend/
├── app.py                       # 应用入口（Flask + flask-openapi3）
├── config.py                    # 应用配置类（[cache]/[redis] → Flask Config）
├── start.sh / stop.sh           # 启动/停止脚本
├── apis/
│   ├── config.ini               # 主配置文件（缓存/Redis/OKX/TickFlow/OpenBB）
│   ├── config.py                # API 密钥读取器（OKX / TickFlow / OpenBB）
│   ├── akshare_stock_api.py     # A 股数据（akshare）
│   ├── akshare_public_fund_api.py # 公募基金数据（akshare）
│   ├── akshare_bond_api.py      # 可转债数据（akshare）
│   ├── akshare_macro_api.py     # 宏观经济数据（akshare）
│   ├── efinance_api.py          # 基金历史净值（efinance）
│   ├── okx_api.py               # 加密货币行情（OKX）
│   ├── finshare_stock_api.py    # A 股数据（FinShare）
│   ├── yfinance_api.py          # 全球指数排行（YFinance）
│   ├── forex_api.py             # 汇率数据（CurrencyConverter）
│   ├── openbb_api.py            # 全球指数/宏观矩阵（OpenBB）
│   └── field_mapping.py         # 字段映射
├── views/
│   ├── stock_view.py            # A 股接口
│   ├── public_fund_view.py      # 公募基金接口
│   ├── crypto_view.py           # 加密货币接口
│   ├── bond_view.py             # 可转债接口
│   ├── macro_view.py            # 宏观经济接口
│   ├── global_view.py           # 全球指数/汇率接口
│   └── meta_view.py             # /api/market/functions 端点（Function Calling）
├── services/
│   ├── stock_service.py         # A 股业务逻辑（缓存 + fallback）
│   ├── public_fund_service.py   # 公募基金业务逻辑
│   ├── crypto_service.py        # 加密货币业务逻辑
│   ├── bond_service.py          # 可转债业务逻辑
│   ├── macro_service.py         # 宏观经济业务逻辑
│   └── global_service.py        # 全球市场业务逻辑
├── daos/
│   ├── cache_dao.py             # Redis 缓存 DAO（JSON + gzip，含 DataFrame 支持）
│   └── market_dao.py            # 内存 mock DAO（预留）
├── utils/
│   ├── function_registry.py     # Function Calling 函数定义（运行时以 registry 为准）
│   ├── kline_generator.py       # K 线生成工具
│   └── cache_scheduler.py       # 缓存预热与周期性刷新调度（ThreadPoolExecutor）
└── tests/                       # pytest 测试（API / Service / View 层）
```
