# FundMasterAI 团队协作指南

> 这份文档写给参与开发的队友，讲清楚三件事：**怎么加入、怎么改代码、怎么把改动部署到共享的云服务器**。
>
> 本地单机开发的环境配置与启动方式见 [README.zh-CN.md](README.zh-CN.md)，这里不重复。

---

## 一、一句话讲清协作模型

```text
你的电脑(Mac/Win) --写代码--> GitHub(dev 分支, 走 PR) --git pull--> 云服务器(统一运行环境)
```

- **GitHub 是代码的唯一来源**：所有改动都通过 git 进出，不在任何人电脑里"私藏"。
- **云服务器是统一的运行环境**：不管你本地是 Mac 还是 Windows，代码最终都跑在同一台 Linux 云上，所以不会出现"我这能跑、你那跑不起来"的线上差异。

> 小知识：环境其实分两层。**运行环境**（代码真正跑起来的地方）由云服务器统一；**开发环境**（你自己电脑上写代码、试跑）还是各自的系统。日常协作以云为准即可，不必追求本地完全一致。

---

## 二、第一次加入（每位队友只做一次）

### 0. 让负责人把你加进仓库

请仓库负责人在 GitHub → `Settings` → `Collaborators` 里把你的 GitHub 账号加进来，否则你无法把代码 push 上去。

### 1. 克隆仓库

```bash
git clone https://github.com/MrGood4U/FundMasterAI.git
cd FundMasterAI
git checkout dev
```

### 2. 申请云服务器登录权限（用 SSH 公钥，不用密码）

先在自己电脑生成密钥（如果以前生成过就跳过）：

```bash
ssh-keygen -t ed25519        # 一路回车即可
cat ~/.ssh/id_ed25519.pub    # 复制输出的这一整行
```

把输出的**公钥**发给项目负责人，由他加到服务器。之后你就能免密登录：

```bash
ssh root@<云服务器IP>         # 具体 IP 向项目负责人索取
```

> 安全约定：
> - **不要互相传服务器密码**，一人一把钥匙；某人离队时，负责人删掉对应公钥即可。
> - **服务器 IP、登录信息等敏感内容不写进仓库**，请单独向负责人索取。

---

## 三、日常开发流程

```bash
git checkout dev
git pull                          # 先同步最新代码
git checkout -b 你的名字/功能名    # 从 dev 切自己的分支，例如 lily/fix-news

# ... 在自己分支上改代码 ...

git add -A
git commit -m "用一句话说明你改了什么"
git push -u origin 你的名字/功能名
```

然后去 GitHub 上发起 **Pull Request（PR）** 合并到 `dev`，等 CI 自动检查通过、队友 review 后再合并。

> 为什么要走"分支 + PR"，而不是直接改 dev：
> - 避免多人同时改 `dev` 互相覆盖；
> - CI 会自动帮你跑测试，提前发现问题；
> - 每个改动都有记录，方便回溯。

---

## 四、把改动部署到云服务器

代码合并进 `dev` 后，登录云服务器，一条命令完成更新：

```bash
ssh root@<云服务器IP>
cd /root/FundMasterAI
./update.sh          # 自动：git pull + 装依赖 + 重启所有服务
```

> 约定：**谁合并了 PR，谁负责上云跑一次 `update.sh`**（或固定一人专门管部署），避免大家都以为别人会做。

---

## 五、云上服务一览

项目用 systemd 管理 5 个服务（开机自启、崩溃自动重启）：

| 服务 | 作用 | 端口 |
|---|---|---|
| `fundmaster-market` | 行情 / 基金数据 | 5001 |
| `fundmaster-news` | 新闻 / 公告 | 5010 |
| `fundmaster-portfolio` | 组合（连 MariaDB） | 5002 |
| `fundmaster-agent` | AI 多智能体分析引擎 | 5003 |
| `fundmaster-frontend` | 前端页面 + API 代理 | 8080 |

用户从浏览器**只访问 8080**；其它服务由 8080 内部转发，不直接对公网暴露（更安全）。

常用运维命令：

```bash
systemctl status fundmaster-agent       # 查看某个服务是否在运行
systemctl restart fundmaster-frontend   # 重启某个服务
journalctl -u fundmaster-agent -n 50    # 看最近 50 行日志（排错首选）
```

---

## 六、铁律与注意事项

- **绝不在云上直接改代码**：不要在服务器上用 `vim` 改 `.py` 文件。云上只负责 `git pull`。否则下次更新会冲突，而且改动没进 git 会丢失。
- **`.env`（含 API Key）不进 git**：已经在忽略名单里，各机器单独放一份，不要提交。
- **装了新依赖包**：记得同步更新依赖清单，让别人也能一键装上（见 README 的依赖说明）。
- 不确定的操作，先在自己分支里试，别直接动 `dev` 和云上生产环境。

---

## 七、出问题怎么排查

| 现象 | 先查什么 |
|---|---|
| 网页打不开 | `systemctl status fundmaster-frontend` 是否 `active` |
| AI 分析报错 / 一直转圈 | `journalctl -u fundmaster-agent -n 80` 看日志 |
| 数据拿不到 / 超时 | market、news 服务是否 `active`；也可能是外部数据源临时不稳定 |
| 改了代码没生效 | 是否 `git pull` 了，并重启了对应服务 |
| 浏览器报 502 | 多半是本机网络 / VPN / 缓存问题，关掉 VPN 后强制刷新（Ctrl+Shift+R）再试 |

---

## 八、本地开发

想在自己电脑上完整跑起来调试，见 [README.zh-CN.md](README.zh-CN.md) 的"环境要求 / 启动后端服务 / 启动 AI Agent / 启动前端"章节。

如果以后本地环境差异（依赖、路径等）变成经常性的麻烦，再考虑引入 Docker 把整套环境打包统一——目前阶段不必。
