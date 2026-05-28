# Portfolio Backend

投资组合管理后端，提供交易记录、持仓管理、价格告警、自选关注等 CRUD 接口，以及 Function Calling 函数定义供 LLM agent 发现和调用。启动后自动运行后台告警检查线程，按可配置的时间间隔扫描价格告警并触发通知。

## 环境要求

- Python >= 3.11
- pip >= 3.11

## 安装依赖

```bash
pip3.11 install flask pymysql requests
```

## 配置文件

### `config.ini`（必须手动配置）

位于项目根目录下，已有的默认值如下，请根据实际环境修改：

```ini
[mysql]
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=fundmaster_user
MYSQL_PASSWORD=fundmaster_pass
MYSQL_DB=fundmaster_db

[market_backend]
MARKET_BACKEND_URL=http://localhost:5001
```

可选的 `[app]` 段（控制端口和告警检查间隔）和 `[redis]` 段（预留）：

```ini
[app]
PORTFOLIO_HTTP_PORT=5002
ALERT_CHECK_INTERVAL_MINUTES=5

[redis]
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

目前并不需要配置redis, 配置mysql即可

### 环境变量（可选，优先级高于 config.ini）

所有 `config.ini` 中的配置项均可通过同名环境变量覆盖。例如：

```bash
export PORTFOLIO_HTTP_PORT=5002
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=你的密码
export MYSQL_DB=fundmaster_db
export MARKET_BACKEND_URL=http://localhost:5001
export ALERT_CHECK_INTERVAL_MINUTES=5
```

配置优先级：**环境变量 > config.ini > 代码硬编码默认值**。

## MySQL 数据库

**必须先创建数据库和表再启动服务。**

在 MySQL 中运行 `init.sql`：

```bash
mysql -u root -p fundmaster_db < init.sql
```

`init.sql` 会创建以下 4 张表：

| 表名 | 说明 |
|---|---|
| `user_profile` | 用户资料（手机号、邮箱及验证状态） |
| `transactions` | 交易记录（买卖明细） |
| `price_alert` | 价格告警（支持价格/百分比两种触发模式） |
| `watchlist` | 自选关注列表 |

所有表使用 InnoDB 引擎，utf8mb4 字符集。

## 端口

- 默认端口：**5002**
- 可通过环境变量 `PORTFOLIO_HTTP_PORT` 或 `config.ini` 中 `[app]` 段的 `PORTFOLIO_HTTP_PORT` 修改

## 后台告警检查

服务启动后自动启动一个后台守护线程，每 **`ALERT_CHECK_INTERVAL_MINUTES`** 分钟（默认 5 分钟）执行一次：

1. 查询所有 `is_enabled=1` 的价格告警
2. 调用 Market Backend 获取实时价格
3. 判断是否触发告警条件（price 模式比较绝对价，pct 模式比较持仓成本变化百分比）
4. 触发后：发送电话/邮件通知（当前为日志模拟），并将该告警 `is_enabled` 设为 0

告警触发逻辑详见 `alert_checker.py`。

## Function Calling 接口文档

启动后访问以下端点获取 LLM agent 可用的全部函数定义：

```
GET http://localhost:5002/api/portfolio/functions
```

支持按类别筛选：

```
GET http://localhost:5002/api/portfolio/functions?tag=transaction   # 交易记录
GET http://localhost:5002/api/portfolio/functions?tag=holding       # 持仓管理
GET http://localhost:5002/api/portfolio/functions?tag=alert         # 价格告警
GET http://localhost:5002/api/portfolio/functions?tag=watchlist     # 自选关注
```

函数定义源码位于 `utils/function_registry.py`，共 15 个函数，涵盖交易的 CRUD/列表、持仓汇总/明细（含实时行情和盈亏计算）、告警的 CRUD/列表（含价格/百分比两种模式）、自选的添加/移除/列表（含实时行情）。

## 启动与停止

```bash
# 启动（后台运行，日志写入 app.log）
bash start.sh

# 停止
bash stop.sh
```

启动后 PID 写入 `app.pid`，可通过 `cat app.pid` 查看进程 ID。

也可使用项目根 `backend/` 目录下的批量脚本同时操作所有后端：

```bash
bash ../start_all.sh   # 启动所有后端
bash ../stop_all.sh    # 停止所有后端
```

## 日志

日志文件：`app.log`（位于 portfolio_backend 目录下）

所有标准输出和标准错误均重定向到此文件。查看实时日志：

```bash
tail -f app.log
```

## 项目结构

```
portfolio_backend/
├── app.py                  # 应用入口（Flask 工厂模式 + 启动后台告警线程）
├── config.py               # 配置类（env > config.ini > 默认值 三层回退）
├── config.ini              # 配置文件（需手动编辑）
├── init.sql                # 数据库建表脚本（启动前必须执行）
├── alert_checker.py        # 后台告警检查线程
├── start.sh / stop.sh      # 启动/停止脚本
├── apis/
│   └── market_client.py    # HTTP 客户端，调用 market_backend 获取实时行情
├── views/
│   ├── transaction_view.py  # 交易记录接口
│   ├── holding_view.py      # 持仓管理接口
│   ├── alert_view.py        # 价格告警接口
│   ├── watchlist_view.py    # 自选关注接口
│   └── meta_view.py         # /api/portfolio/functions 端点
├── services/
│   ├── transaction_service.py
│   ├── holding_service.py
│   ├── alert_service.py
│   └── watchlist_service.py
├── daos/
│   ├── base_dao.py          # pymysql 连接工厂
│   ├── transaction_dao.py
│   ├── alert_dao.py
│   ├── user_profile_dao.py
│   └── watchlist_dao.py
├── utils/
│   ├── function_registry.py # Function Calling 函数定义
│   └── notification.py      # 电话/邮件通知（当前为日志模拟）
└── tests/                   # pytest 测试（67 个）
```
