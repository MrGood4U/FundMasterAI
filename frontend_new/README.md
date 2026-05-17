# FundMaster 前端

静态展示站点：按 Figma 文件 `B1cuHJoXlJTr7e1ADVhH2P` 中多帧界面，用 **HTML5 + CSS**（无框架）实现；共享侧栏/顶栏，每页独立内容与样式扩展。

## 页面与 Figma 节点对照

| 本地文件 | Figma 节点 | 说明 |
|----------|------------|------|
| `index.html` | `11:336` | Market Intelligence / News Feed（默认入口） |
| `fund-deep-dive.html` | `11:2` | Fund Deep Dive（Analytics 高亮） |
| `market-hub.html` | `11:626` | Market Hub |
| `market-flow.html` | `11:1391` | Market Liquidity & Flow（侧栏与 Market Hub 同属 Markets，高亮「Markets」） |
| `ai-insights.html` | `11:1030` | AI Insights |
| `global-investment.html` | `11:2106` | Global Investment |
| `equity-funds.html` | `11:1703` | Equity Funds（侧栏高亮「Portfolio」） |
| `debt-funds.html` | `11:2610` | Debt Funds（侧栏高亮「Portfolio」） |
| `portfolio-overview.html` | `11:2408`、`42:2` | Portfolio Overview（两节点内容一致，共用一个页面） |
| `settings.html` | `14:3184` | Settings |

## 样式结构

| 路径 | 用途 |
|------|------|
| `css/shell.css` | 全局变量、侧栏、顶栏、主滚动区、通用标题与 FAB、响应式基线 |
| `css/page-news.css` | 仅 `index.html` 使用的快讯双栏与日历等 |
| `css/dashboard-widgets.css` | 多页共用的 KPI 卡片、表格、条形图等 |
| `css/page-*.css` | 各专题页布局与装饰 |
| `styles.css` | 兼容旧引用：`@import` shell + page-news |

从 `index.html` 以外的页面进入时，侧栏链接已在各 HTML 中写死为上述文件名。

## 重新生成专题页 HTML（可选）

侧栏结构由脚本统一生成，修改导航时请编辑 `scripts/generate-pages.py` 后执行：

```bash
cd "/Users/liuzhaoxuan/Fundmaster 前端" && python3 scripts/generate-pages.py
```

`index.html` 不在脚本内，需手动维护。

## 本地预览

```bash
cd "/Users/liuzhaoxuan/Fundmaster 前端" && python3 -m http.server 8080
```

浏览器访问 `http://127.0.0.1:8080`，再点开各 HTML 或从侧栏切换。

## 字体与资源

- 标题与品牌：Space Grotesk；正文：Inter；等宽数据：JetBrains Mono。
- **图标**：侧栏与顶栏使用 `assets/icons/` 内 PNG。替换时用同名文件覆盖即可。三个顶栏导出默认映射为：`header-search.png`（搜索框）、`header-bell.png`（通知）、`header-help.png`（帮助）；若与设计顺序不一致，可在该文件夹内互换文件名。

## 浏览器支持

现代浏览器；`backdrop-filter` 与 `:has()` 在极旧版本上可能降级（毛玻璃或 Market Hub 背景装饰略弱）。
