# News Backend

新闻资讯后端，提供 A 股近期新闻和公募基金公告的查询接口，以及 Function Calling 函数定义供 LLM agent 发现和调用。

## 环境要求

- Python >= 3.11
- pip >= 3.11

## 安装依赖

```bash
pip3.11 install flask akshare pandas
```

## 配置文件

本后端无 `config.ini` 文件，仅通过环境变量配置（均有默认值，一般无需改动）。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `SECRET_KEY` | `a_very_secret_key_that_should_be_changed` | Flask 密钥 |
| `MYSQL_HOST` | `localhost` | MySQL 地址（预留） |
| `MYSQL_USER` | `root` | MySQL 用户名（预留） |
| `MYSQL_PASSWORD` | `password` | MySQL 密码（预留） |
| `MYSQL_DB` | `fundmaster_db` | MySQL 数据库名（预留） |
| `REDIS_HOST` | `localhost` | Redis 地址（预留） |
| `REDIS_PORT` | `6379` | Redis 端口（预留） |
| `REDIS_DB` | `0` | Redis 数据库编号（预留） |

> MySQL/Redis 配置项当前预留，本后端直接从 akshare 在线获取数据，不连接数据库。

## MySQL 数据库

不需要。本后端不连接数据库，数据直接通过 akshare 从网络获取，无需提前创建表。

## 端口

- 默认端口：**5000**（Flask 默认端口，当前不可通过环境变量配置）

## Function Calling 接口文档

启动后访问以下端点获取 LLM agent 可用的全部函数定义：

```
GET http://localhost:5000/api/news/functions
```

支持按类别筛选：

```
GET http://localhost:5000/api/news/functions?tag=stock   # A 股新闻
GET http://localhost:5000/api/news/functions?tag=fund    # 公募基金公告
```

函数定义源码位于 `utils/function_registry.py`，共 2 个函数：

| 函数名 | 说明 |
|---|---|
| `get_stock_recent_news` | 获取 A 股近期新闻 |
| `get_public_fund_announcement` | 获取公募基金公告 |

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

日志文件：`app.log`（位于 news_backend 目录下）

所有标准输出和标准错误均重定向到此文件。查看实时日志：

```bash
tail -f app.log
```

## 项目结构

```
news_backend/
├── app.py                  # 应用入口（Flask 工厂模式）
├── config.py               # 配置类（环境变量）
├── start.sh / stop.sh      # 启动/停止脚本
├── apis/
│   ├── akshare_news_api.py  # 新闻数据获取（akshare）
│   └── field_mapping.py     # 字段映射
├── views/
│   ├── news_view.py         # 新闻/公告接口
│   └── meta_view.py         # /api/news/functions 端点
├── services/
│   └── news_service.py
├── daos/
│   └── example_dao.py       # DAO 示例存根（未使用）
└── utils/
    └── function_registry.py  # Function Calling 函数定义
```
