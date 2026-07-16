# FundMasterAI 团队协作指南

`dev` 是团队日常开发分支，`master` 是整理后的提交和演示稳定分支。日常修改应从
`dev` 新建短期功能分支，通过 Pull Request 合并回 `dev`；只有完成验证的发布状态才
进入 `master`。

## 日常流程

```bash
git switch dev
git pull --ff-only
git switch -c 你的名字/简短主题
```

完成一项范围清楚的修改后：

```bash
git add <本次文件>
git commit -m "说明本次改动"
git push -u origin 你的名字/简短主题
```

然后向 `dev` 发 Pull Request。真实密钥、本地 `.env`、日志、PID 文件和个人 IDE
状态都不能提交到 Git。

准备提交时，再从已经验收的发布状态向 `master` 发范围清楚的 release PR。不要把
`master` 当作日常联调分支，也不要把本地 QA 产物带进主分支。

## 合并前验证

涉及完整项目、前端、后端、Docker 或文档入口时，在仓库根目录执行：

```bash
docker compose config --quiet
docker compose up --build --wait
docker compose run --rm smoke
```

随后用真实浏览器打开 `http://localhost:8080/ai-insights.html`，等待数据加载完成，
再检查本次受影响的页面和交互。smoke 通过不能代替视觉验收。

只修改 AI Agent 时还应执行：

```bash
cd ai_agent/fund_llm_engine
python -m unittest discover -s tests
python scripts/run_golden_suite.py --mode mock
```

## Pull Request 要求

- 说明用户可见行为或接口契约发生了什么变化；
- 写明实际执行过的验证命令；
- 区分前端、后端和 Agent 的责任边界；
- 文档入口或启动方式变化时，同时更新对应的英文和中文入口；
- 不把健康检查或 smoke 当成页面已经完成真实浏览器验收。

`master` 不再维护共享 systemd 云服务器工作流。本地开发、课堂演示和提交验收统一
使用 Docker Compose；如果以后重新支持独立部署环境，应在部署方式真正稳定后再加入
对应 runbook。
