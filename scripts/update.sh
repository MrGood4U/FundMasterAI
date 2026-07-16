#!/bin/bash
# 云服务器一键更新脚本：拉取最新代码 -> 更新 agent 依赖 -> 重启全部 systemd 服务。
# 仅用于已按 systemd 方式部署的云服务器（见 CONTRIBUTING.zh-CN.md）。
# 本地开发请按 README.zh-CN.md 的方式各自启动，不要在本地跑这个脚本。
set -e

# 切到仓库根目录(脚本在 scripts/ 下，往上一级即为根)，无论克隆在什么路径都能正确运行
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/3] 拉取最新代码..."
git pull

echo "[2/3] 更新 agent 依赖(如有变化)..."
python3.11 -m pip install -e "ai_agent/fund_llm_engine[backend]" -q 2>/dev/null || true

echo "[3/3] 重启所有服务..."
systemctl restart fundmaster-market fundmaster-news fundmaster-portfolio fundmaster-agent fundmaster-frontend
sleep 6

echo "服务状态:"
# 注意：systemctl is-active 在服务未处于 active 时返回非零码；配合顶部 set -e，
# 曾经导致某个服务刚好还在 activating/failed 时脚本直接中断，后面的服务状态
# 就不会被打印出来，容易误判"部署失败"或掩盖真正失败的服务。这里用 `|| true`
# 保证每个服务的状态都能完整打印，方便一眼看出到底是哪个服务没起来。
for s in market news portfolio agent frontend; do
  echo -n "  fundmaster-$s: "
  systemctl is-active "fundmaster-$s" || true
done
