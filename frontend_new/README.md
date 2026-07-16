# FundMaster 前端

`frontend_new/` 是 FundMasterAI 当前使用的静态前端。页面以 HTML/CSS/JavaScript
实现，不依赖前端框架；完整项目运行时由 Nginx 提供静态文件，并把同源
`/api/market`、`/api/news`、`/api/portfolio`、`/api/ai` 请求转发到对应服务。

## 推荐预览方式

从仓库根目录启动完整项目：

```bash
docker compose up --build --wait
docker compose run --rm smoke
```

打开 `http://localhost:8080/ai-insights.html`，再通过左侧导航检查其他页面。这样
页面使用的 API 路由与最终部署一致。

只看静态布局时，也可以从仓库根目录运行：

```bash
python3 -m http.server 8080 --directory frontend_new
```

然后打开 `http://127.0.0.1:8080/`。这种方式没有 Nginx API 代理；需要后端数据的
区域可能显示加载失败，因此不能代替完整联调验收。

## 主要页面

| 文件 | 页面 |
|---|---|
| `portfolio-overview.html` | Portfolio Overview |
| `equity-funds.html` | Equity Funds |
| `debt-funds.html` | Debt Funds |
| `global-investment.html` | Global Investment |
| `fund-deep-dive.html` | Fund Deep Dive |
| `market-hub.html` | Market Hub |
| `market-flow.html` | ETF Capital Flow |
| `index.html` | Market Intelligence / News |
| `ai-insights.html` | AI Insights |
| `settings.html` | Settings |

这些页面最初对应 Figma 文件 `B1cuHJoXlJTr7e1ADVhH2P` 的多个 frame，但当前运行
语义应以页面代码、API 契约和实际浏览器结果为准，而不是以旧设计稿中的占位数据为准。

## 样式与脚本

| 路径 | 用途 |
|---|---|
| `css/shell.css` | 侧栏、顶栏、主题变量和响应式基线 |
| `css/dashboard-widgets.css` | 多页共用的 KPI、表格和图表组件 |
| `css/page-*.css` | 各页面布局与扩展样式 |
| `scripts/`、`js/` | 页面取数、缓存、交互和 AI Insights 逻辑 |
| `assets/icons/` | 侧栏和顶栏图标 |

## 基金搜索与浏览器缓存

顶部搜索和 Portfolio Overview 的“添加基金”都使用 Market 后端的真实基金目录
`GET /api/market/fund_public/fund_name_list`，不再使用硬编码的演示基金兜底。首次冷
请求允许最长 120 秒；成功后会把精简目录写入浏览器 `localStorage`，缓存键为
`fundmaster:fund-directory:v1`，有效期 24 小时。过期缓存可以先用于搜索，同时在
后台刷新；网络失败时页面会明确显示暂时不可用，不会把任意输入伪装成真实基金。

搜索支持基金代码、名称和拼音缩写，按前缀优先排序并做 250 ms 防抖。Portfolio
Overview 只有在用户从搜索结果中选中真实基金后才允许保存持仓。Fund Rankings 和
QDII 排行所用的请求路径如果收到上游 `NaN` / `Infinity`，会把这些非有限值作为
缺失值处理，避免整页 JSON 解析失败。

## 导航页生成

专题页的共享导航由 `scripts/generate-pages.py` 维护。修改生成模板后，在仓库根目录
执行：

```bash
python3 frontend_new/scripts/generate-pages.py
```

`index.html` 不在生成脚本内，需要单独维护。执行生成脚本后必须检查 Git diff，避免
覆盖页面上的手工联调修改。

## 验收

自动 smoke 会检查 10 个主要页面和四类后端/Agent 接口：

```bash
docker compose run --rm smoke
```

自动检查只能证明页面和主链路可访问；提交前仍应在真实浏览器里确认数据加载后的
布局、空状态、页面切换和缓存行为。

## 浏览器支持

使用当前版本的 Chrome、Edge、Safari 或 Firefox。`backdrop-filter` 和 `:has()` 在
较旧浏览器中可能降级，但不应影响核心数据与导航。
