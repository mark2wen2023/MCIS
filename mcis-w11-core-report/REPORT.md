W11 原核心：阻塞（固定验收 77794be 官方 `--verify-only` 退出码 0；离线真跑在 NuGet 初始化处退出码 1；launcher 冒烟、manifest 与业务预览/保存/重开未执行）。未替换核心、未减断言、未安装、未更改正式入口、未用外部 NuGet feed。

# MCIS W11 原 ECFC 核心验收（合成；阻塞）

- 执行时间：2026-11-26 03:17–03:20（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`77794be47926cc983a494aad46e59c3bac4729ce`（2026-11-26 01:23:30 +0800，“test(W11): prepare pinned genuine ECFC core acceptance gate”）。按 `tests_acceptance/w11-real-core/README.md` 原脚本执行，未改验收文件，也未改产品、核心或正式入口。
- 试点源：已有工作树 `/workspace/mcis-w11-b40a6ca` = `b40a6cacf91ba0d8b297377d31162e404e468e8d`。4 个试点辅助文件（SOURCES / check.py / pilot.py / run.py）与固定 Git blob 一致，作 `--pilot`。
- 原核心基准：`d9187fef1f979866ac4d8ce2064d1ac92f34bb36`。186 份既有原件与 9 个原核心文件/模式由已在本地的 Git 对象导出为 `--source-dir`（7dfb326、d9187fe、871db66、db90fdf、b61aa93 的对象均已在盒子上，未 fetch）。当前 b40a6ca 工作区文件本身并不等同全部 186 个历史原件（缺 4、哈希不一致 6），故未把该工作区直接当作 186 原件树。
- 现成 SDK：`/home/box/.dotnet/dotnet`，.NET SDK **8.0.428**，运行时 Microsoft.NETCore.App / Microsoft.AspNetCore.App **8.0.34**。未把 `dotnet` 加入父进程 PATH。官方脚本在进程内使用空本地包源、`DOTNET_CLI_TELEMETRY_OPTOUT=1` 与隔离 CLI home。
- 现成服务 Python：`/workspace/mcis-w17-871db66/service/.venv/bin/python`（CPython 3.13.5），按 README 以 `-B` 调用。
- 无外网：`unshare -r -n`（仅 loopback）。跑前核对 nuget.org / api.nuget.org / 8.8.8.8 / 1.1.1.1 均不可达。
- 未改产品，未替换核心，未减断言，未安装，未更改正式入口，未合并，未部署，未触发远程 CI，未用外部 feed。

## 1. 源码核对 `--verify-only`

退出码 **0**。官方打印：`W11 verified 186 W11 originals + 4 pilot helpers + 9 exact core blobs/modes (d9187fe); no fetch`。日志：`logs/01-verify-only.*`。

## 2. 冒烟（离线官方真跑）

同一命令将 `--verify-only` 换为 `--dotnet /home/box/.dotnet/dotnet`，在 `unshare -r -n` 中执行。整次官方进程退出码 **1**。

已完成：针再次通过；`SDK version` 退出码 0（随后官方断言版本为 8.0.428，否则会在 NuGet 步之前以错误退出）。

**首个停点：** `dotnet nuget locals all --list`（官方标签 `NuGet local directories check`）退出码 **1**。原始 stderr：

```
System.IO.IOException: The system cannot open the device or file specified. : 'NuGet-Migrations'
   at System.Threading.Mutex.CreateMutexCore(Boolean initiallyOwned, String name, Boolean& createdNew)
   at System.Threading.Mutex..ctor(Boolean initiallyOwned, String name)
   at NuGet.Common.Migrations.MigrationRunner.Run(String migrationsDirectory)
   at Microsoft.DotNet.Configurer.DotnetFirstTimeUseConfigurer.Configure()
   ...
```

未绕过该初始化失败（未改环境、未加额外 DOTNET/NuGet 开关、未在有外网的命名空间重跑、未改官方脚本）。因此原 launcher 冒烟与 build-manifest 完整性**未执行**。日志：`logs/02-real.*`、`logs/02-offline-ns-check.txt`。

## 3. 业务（合成预览 / 保存 / SQLite 重开 / 审计）

未跑（官方脚本在冒烟初始化失败后即 `SystemExit`）。视为 **未验**。

## 4. 未验

原 launcher 冒烟与 manifest；原核心合成预览（不落库）、保存、SQLite 重开及审计；Unity 运行时；浏览器；正式身份；正式归档。此项不代替已通过的 W11 原文 Chrome 试点或正式归档。

## 5. 文件

`logs/00-env.txt`、核对与离线真跑原始日志、`outputs/exit-codes.txt`。产品原件导出未纳入压缩包。
