# Market Backend

市场行情后端，提供 A 股、公募基金、加密货币的实时行情、历史数据、K 线、技术指标等数据接口，以及 Function Calling 函数定义供 LLM agent 发现和调用。

## 环境要求

- Python >= 3.11
- pip >= 3.11

## 安装依赖

```bash
pip3.11 install flask flask-openapi3 akshare pandas numpy efinance okx redis
pip3.11 install -U "flask-openapi3[swagger,redoc]"

# 全球指数/汇率/宏观矩阵、个股资金流向与龙虎榜（新增于 2026-06）
pip3.11 install yfinance pysqlite3-binary forex-python CurrencyConverter finshare openbb
```

> `pysqlite3-binary` 是必须的：`yfinance` 依赖标准库 `sqlite3`，但部分云服务器上的
> Python 编译时未带 `_sqlite3` 模块，`app.py` 里用 `pysqlite3` 做了兼容替换
> （`sys.modules["sqlite3"] = pysqlite3`）。少装这一个包会导致 `fundmaster-market`
> 启动即崩溃、被 systemd 无限重启。

## 配置文件

### `apis/config.ini`（主配置文件）

所有持久化配置集中在 `apis/config.ini`，无需环境变量即可运行。文件分为以下段：

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

从 `config.ini` 读取 OKX、TickFlow、OpenBB 的 API 密钥，提供 `get_okx_api_key()`、`get_tickflow_api_key()`、`get_openbb_fmp_api_key()` 等函数供各 API 模块调用。

### `config.py`（应用配置类）

Flask 应用的全局配置（`Config` 类），从 `apis/config.ini` 的 `[cache]` 和 `[redis]` 段读取所有配置项，同时兼容环境变量覆盖。缓存开关/间隔、Redis 连接、MySQL 连接、HTTP 端口等配置均集中在此。

### 环境变量（可选，config.ini 有值时优先）

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

> MySQL 配置项当前预留，实际 DAO 层为内存 mock 实现，不连接数据库。

## MySQL 数据库

不需要。本后端无需提前创建数据库表。

## 端口

- 默认端口：**5001**
- 可通过环境变量 `MARKET_HTTP_PORT` 修改

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

函数定义源码位于 `utils/function_registry.py`，约 25 个函数，涵盖 A 股行情、公募基金净值/排行/分析、加密货币行情/K 线/均线等。

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
│   ├── function_registry.py     # Function Calling 函数定义（约 25 个函数）
│   ├── kline_generator.py       # K 线生成工具
│   └── cache_scheduler.py       # 缓存预热与周期性刷新调度（ThreadPoolExecutor）
└── tests/                       # pytest 测试（API / Service / View 层）
```
