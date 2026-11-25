W15 离线原 Bow-tie 核心：现成服务 Python 下官方脚本通过（固定验收 8d10844 官方 `--verify-only` 退出码 0，352 产品文件 + 3 辅助与底版 2c72d02 一致；系统 python3 全量跑在 load(test_cli.py) 时因无 pytest 退出 1，当时 CLI 已 11/11 且 manifest 已核验；未安装、未改工装，改用 README 要求的现成服务 venv 解释器后官方脚本退出 0）。5 节点 / 4 边、未知端点明确诊断、SQLite 重启不落库。不是浏览器补验，未重跑 W15 浏览器关口。

# MCIS W15 离线原 Bow-tie 核心验收

- 执行时间：2026-11-26 05:16–05:19（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`8d108442f94901bee862ba5f53dd6343350b2718`（2026-11-26 03:24:27 +0800，“test(W15): add pinned offline original Bow-tie core gate”）。按 `tests_acceptance/w15-bowtie-real-core/README.md` **原脚本**执行，**未改验收文件、未改产品**。相对产品底版仅新增两组验收目录（含本关口与既有负向浏览器工装文件）。未重跑、未改动 W15 浏览器关口。
- 产品源：`2c72d022f3d3275af637b0cdc6e545735e3200a9`。352 个唯一固定产品文件（339 既有针 + 15 核心路径，launcher/recipe 重叠）与 3 个未改的负向辅助文件均已核对。
- 现成 SDK：`/home/box/.dotnet/dotnet`，.NET SDK **8.0.428**，运行时 8.0.34。正常用户 HOME `/home/box` 已有 first-use sentinel；预检 `dotnet nuget locals all --list` 退出码 0（不在 unshare 中、不伪造初始化）。全量跑在 `unshare -r -n`（仅 loopback）中沿用该原 HOME，不设 `DOTNET_CLI_HOME`，不跳预检。官方脚本使用任务专用 `NUGET_PACKAGES` 与空 `RestoreSources`。未用外部 NuGet feed，未安装任何软件。
- 现成服务 Python：`/workspace/mcis-w17-871db66/service/.venv/bin/python`（CPython 3.13.5，pytest 9.2.0）。FastAPI 仅 127.0.0.1。仅合成案。
- 未改产品，未合并，未部署，未触发远程 CI。

## 1. `--verify-only`

退出码 **0**。打印 `W15 pinned 352 exact product files; 12 declared original build inputs, original CLI test and 3 unchanged negative helpers`。

## 2. 全量跑（两次解释器，同一官方脚本）

无外网核对：nuget.org / api.nuget.org / 8.8.8.8 / 1.1.1.1 均不可达，仅 lo。

- 第一次按 README 示例用系统 `/usr/bin/python3`：退出码 **1**。已完成 SDK 8.0.428、原 W153 CLI **11 passed in 7.40s**、artifact manifest。停点：`load(tests_acceptance/W153/test_cli.py)` 执行 `import pytest` 时报 `ModuleNotFoundError: No module named 'pytest'`。无 receipt。见 `attempt1/`。未安装 pytest，未改工装。
- 第二次仍用**未改**官方脚本，运行器改为 README 已要求的现成服务 venv 解释器（该解释器本就作为 `--host-python`，且已含 pytest 9.2.0）：退出码 **0**。CLI 11 passed in 5.73s。官方打印 `W15 actual service + original C# + SQLite restart: both paths pass without mutation`。`receipt.json`：`originalCliPassed=true`，`httpPositivePassed=true`，`httpUnknownEndpointPassed=true`，`sqliteUnchangedAfterReopen=true`，`browserVerified=false`，`sdk=8.0.428`。

正向预览：`structureValid=true`，5 节点 / 4 边，`persisted=false`，`assessment=hypothesis-structure-only`，无 construction/validation 问题，无 safety/risk 结论。未知端点：`structureValid=false`，`constructionErrors` 含 `sys_unknown_node`（「边的端点不存在：GHOST → TOP」），未变成成功的部分图。重启后库摘要与预览前一致，两案来源仍分开可读。

输出：`outputs/receipt.json`、`valid-preview.json`、`unknown-preview.json`、`build-manifest.json`、`cli.log`。

## 3. 未验

浏览器（按派遣不重跑 W15 浏览器关口，也不把本项当浏览器补验）；Unity；正式身份；真实案卷；模型；部署；业务判断；远程 CI。

## 4. 文件

`logs/00-env.txt`、正常 HOME 预检、针核对、离线命名空间核对、两次全量原始日志；`attempt1/`；`outputs/`。
