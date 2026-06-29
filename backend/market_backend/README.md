# Market Backend

市场行情后端，提供 A 股、公募基金、加密货币的实时行情、历史数据、K 线、技术指标等数据接口，以及 Function Calling 函数定义供 LLM agent 发现和调用。

## 环境要求

- Python >= 3.11
- pip >= 3.11

## 安装依赖

```bash
pip3.11 install flask flask-openapi3 akshare pandas numpy efinance okx
pip3.11 install -U "flask-openapi3[swagger,redoc]"
```

## 配置文件

### API 密钥 — `apis/config.ini`（必须手动配置）

如需使用加密货币行情接口（OKX），请编辑 `apis/config.ini` 填入你的 OKX API 密钥：

```ini
[okx]
API_KEY = 你的_api_key
API_SECRET = 你的_api_secret
API_PASS = 你的_api_passphrase
```

> 注意：`[tick_flow]` 部分尚未实现，调用 TickFlow 相关功能会报错。

### 环境变量（可选，有默认值）

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `MARKET_HTTP_PORT` | `5001` | 后端监听端口 |
| `MYSQL_HOST` | `localhost` | MySQL 地址 |
| `MYSQL_USER` | `root` | MySQL 用户名 |
| `MYSQL_PASSWORD` | `password` | MySQL 密码 |
| `MYSQL_DB` | `fundmaster_db` | MySQL 数据库名 |
| `REDIS_HOST` | `localhost` | Redis 地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_DB` | `0` | Redis 数据库编号 |

> MySQL/Redis 配置项当前预留，实际 DAO 层为内存 mock 实现，不连接数据库。

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
├── app.py                  # 应用入口（Flask + flask-openapi3）
├── config.py               # 配置类（环境变量）
├── start.sh / stop.sh      # 启动/停止脚本
├── apis/
│   ├── config.ini           # OKX API 密钥（需手动配置）
│   ├── config.py            # API 密钥读取
│   ├── akshare_stock_api.py      # A 股数据（akshare）
│   ├── akshare_public_fund_api.py # 公募基金数据（akshare）
│   ├── efinance_api.py           # 基金历史净值（efinance）
│   ├── okx_api.py                # 加密货币行情（OKX）
│   └── field_mapping.py          # 字段映射
├── views/
│   ├── stock_view.py        # A 股接口
│   ├── public_fund_view.py  # 公募基金接口
│   ├── crypto_view.py       # 加密货币接口
│   └── meta_view.py         # /api/market/functions 端点
├── services/
│   ├── stock_service.py
│   ├── public_fund_service.py
│   └── crypto_service.py
├── daos/
│   └── market_dao.py        # 内存 mock DAO
├── utils/
│   ├── function_registry.py # Function Calling 函数定义
│   └── kline_generator.py   # K 线生成工具
└── tests/                   # pytest 测试
```
