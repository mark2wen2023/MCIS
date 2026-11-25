W17 C# 读取：离线互读通过（固定验收 aca9dfd 官方脚本 `--pins-only` 与离线真跑均为退出码 0；190+9 针与产品源 d40e3b5 一致；未改源、未改产品、未安装、未用外部 NuGet feed）。只记合成归档互读，非 Unity、正式身份或完整归档。

# MCIS W17 custody JSONL 离线 .NET 互读验收

- 执行时间：2026-11-26 02:48–02:49（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`aca9dfd254581a5711c4b38a4f897233f292dedb`（2026-11-25 21:35:46 +0800，“Prepare offline .NET custody ledger interoperability acceptance”）。按 `tests_acceptance/w17-csharp-custody/README.md` 原脚本执行，未改验收文件，也未改产品。
- 产品源：`d40e3b5fd2e208af84c84d6faf61095d0a0a89fb`（2026-11-25 19:17:55 +0800）。按 README 用 `git archive` 仅展开 `service`、`contracts`、`tools/mcis-compat` 与既有 Unity 域只读 C#（Primitives / Evidence），作为 `--source`。
- 现成 SDK：`/home/box/.dotnet/dotnet`，.NET SDK **8.0.428**，运行时 Microsoft.NETCore.App / Microsoft.AspNetCore.App **8.0.34**（linux-x64）。未把 `dotnet` 加入父进程 PATH；`DOTNET_ROOT` 与 CLI 环境仅由官方 `run.py` 在本次进程内设置。`DOTNET_CLI_TELEMETRY_OPTOUT=1`。
- 现成服务 Python：`/workspace/mcis-w17-871db66/service/.venv/bin/python`（CPython 3.13.5），以官方要求的 `-I -B` 调用。FastAPI 仅监听 127.0.0.1。仅合成案。
- 无外网：`unshare -n` 需特权，不可用；改用已有的 `unshare -r -n`（用户命名空间 + 新网络命名空间，仅 loopback）。跑前核对 nuget.org / api.nuget.org / 8.8.8.8 / 1.1.1.1 均不可达。官方脚本以临时空包缓存 + 清空 package/fallback/audit 源的 NuGet.Config 做 restore，再 `--no-restore` 构建。未添加、未改用外部 feed，未安装任何软件。
- 未改产品，未合并，未部署，未触发远程 CI。

## 1. `--pins-only`

退出码 **0**。打印 `Verified d40e3b5…: 190 service/contract + 9 C# blob pins`。日志：`logs/01-pins-only.*`。

## 2. 离线真跑（原服务合成导出 → 原 C# 读取器）

退出码 **0**。官方 stderr 打印 SDK 8.0.428 与上述运行时。restore 在 65 ms 内完成（无外网、空源），构建 0 警告 0 错误。官方 stdout 结果：

```json
{"archive": "1.4.0", "custodySha256": "431bc69024b01f65179ad11cae2b1f12c22cd3b0b7d123216ee6f34c5a146239", "events": 4, "items": 2, "statuses": ["NeedsReview", "Verified"], "restrictedCount": 1, "nonCanonicalRejected": "custody_chain_broken"}
```

与 README 期望一致：导出格式 1.4.0；未改动的 `audit/custody.jsonl` 交给新编译的现成读取器，rc 0、4 条事件、2 个条目、NeedsReview 与 Verified 分属正确 ID、恰好 1 个 restricted；非规范末行 rc 1 且 `custody_chain_broken`。

日志：`logs/02-real.*`、`logs/02-offline-ns-check.txt`、`outputs/result.json`。

## 3. 未验

Unity 运行时 / 场景；浏览器回放；正式身份；完整归档（重导、再导出、非合成案）；W11 原 ECFC 核心（按派遣在本项完成后再接，本轮未开跑）。

## 4. 文件

`logs/00-env.txt`、针与真跑原始日志、离线命名空间核对、`outputs/`。
