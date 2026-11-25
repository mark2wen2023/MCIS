# MCIS W11 原 ECFC 核心复验（initialized-home）

- 执行时间：2026-11-26 07:18–07:20（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`875ccc50b049fb24b82f6b0663f3f9476db1880e`（2026-11-26 06:18:09 +0800，“test(w11): opt into initialized SDK home for offline core recheck”）。按 `tests_acceptance/w11-real-core/README.md` **原脚本**执行，**未改验收文件、未改产品**。相对 `77794be` 仅验收工装增加 `--initialized-home` 说明与实现。
- 试点源：已有 `/workspace/mcis-w11-b40a6ca` = `b40a6cacf91ba0d8b297377d31162e404e468e8d`，作 `--pilot`。
- 原核心基准：`d9187fef1f979866ac4d8ce2064d1ac92f34bb36`。186 份既有原件与 9 个原核心文件/模式沿用已在本地、此前已核过的 Git 对象导出（`--source-dir`），未 fetch。
- 现成 SDK：`/home/box/.dotnet/dotnet`，.NET SDK **8.0.428**，运行时 8.0.34。未把 `dotnet` 加入父进程 PATH。
- 现成服务 Python：`/workspace/mcis-w17-871db66/service/.venv/bin/python`（CPython 3.13.5），按 README 作为外层解释器，以 `-B` 调用。
- 未安装，未用外部 NuGet feed，未伪造初始化，未跳过 SDK/NuGet 检查，未改产品，未合并，未部署，未触发远程 CI。未触碰 W15 浏览器关口。仅合成。

## 1. 正常 HOME 预检（不加 `--initialized-home` 的资格条件）

在**非** unshare 环境、沿用原登录 HOME `/home/box` 下记录：

- first-use sentinel：`/home/box/.dotnet/8.0.428.dotnetFirstUseSentinel` **已存在**（未复制、未制造）。
- `dotnet --version`：8.0.428。
- `dotnet nuget locals all --list` 退出码 **0**。列出 http-cache / global-packages / temp / plugins-cache 的原用户路径。

因此具备 README 要求的「已正常初始化」条件，才在后续仅 loopback 的全量中加 `--initialized-home`。

## 2. `--verify-only`

退出码 **0**。官方打印：`W11 verified 186 W11 originals + 4 pilot helpers + 9 exact core blobs/modes (d9187fe); no fetch`。

## 3. 离线 `unshare -r -n` + `--initialized-home` 全量

命名空间内仅 `lo`（官方 `initialized-home` 接口检查通过）。`HOME=/home/box`，不设、不继承 `DOTNET_CLI_HOME`。nuget.org / api.nuget.org 不可解析。官方脚本使用任务专用 `NUGET_PACKAGES` / HTTP / plugin 缓存、空 `RestoreSources`、`RestoreFallbackFolders=""`。未复制迁移状态，未跳过 `dotnet nuget locals all --list`。

官方整次进程退出码 **0**。分步：

| 步骤 | 退出码 |
| --- | --- |
| 针核对（全量内再次） | 0（打印与 `--verify-only` 相同） |
| SDK version | **0**（随后断言为 8.0.428） |
| NuGet local directories check | **0** |
| Core smoke（原 launcher） | **0** |
| 源码/制品 manifest | 通过（官方打印 Verified original SDK/core smoke and source-artifact manifest） |
| Real W11 core business flow | **0** |

官方打印：`W11 actual ECFC core synthetic preview/save/SQLite reopen PASS; not browser, association, archive, or production`。即：合成预览不落库、显式保存（含归档限制确认）、同库重开、一笔请求与一笔对应审计。stderr 仅有构建成功（0 Warning / 0 Error，约 3.85s）以及 FastAPI/Starlette TestClient 的既有 deprecation 警告，无业务失败。

工装把 SQLite 与回执放在进程临时目录，结束后删除；本报告以官方 stdout/stderr 与退出码为原件。

## 4. 保留的旧 fresh-HOME 阻塞

验收 `77794be47926cc983a494aad46e59c3bac4729ce` 在隔离 CLI home（fresh HOME）下，离线真跑在 `dotnet nuget locals all --list` 处因 `NuGet-Migrations` `IOException` 退出码 **1**；launcher 冒烟、manifest 与业务未执行。回执：https://github.com/mark2wen2023/MCIS/issues/106#issuecomment-7172162623 。本项**不声称**该 fresh-HOME 运行已通过。本行只记录 `--initialized-home` 复验。

## 5. 未验

完整 HTTP 生命周期；浏览器；正式原件关联；归档；Unity；正式身份；真实案卷；fresh-HOME 路径（仍为既有阻塞）；远程 CI。
