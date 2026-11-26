# W15 AcciMap 核心验收报告（原套件，合成）

结论：本子项通过。执行方法为**原套件**（非隔离夹具，非网页组件）。不是 W15 整包。未改核心、Web、主入口、契约、归档或权限，未跑真实案卷，未安装，未接外部源。

- 派遣：#106 评论 7198721691
- 已接：https://github.com/mark2wen2023/MCIS/issues/106#issuecomment-7198816671 （id 7198816671，2026-11-27 01:18:59 CST）
- 产品钉（已核对）：`2447b14076bbf39db014b8bf4a3a3b350cbf0e05`
- 验收候选：`candidate/w15-accimap-core` @ `8d1fd2575598aa1517418d69c7337f3f56a18eb0`（相对钉只新增 `tests_acceptance/w15-accimap-core/`）
- 官方运行时刻：2026-11-27 01:29:34 CST
- 外层：`timeout --signal=TERM --kill-after=10s 150s`，退出码 0
- restore/build/test 退出码均为 0；trx 9/9 Passed

## 依赖判断

已阅读钉住的 `tests_acceptance/W15/AcciMapStampAcceptanceTests.cs` 与 `unity/Assets/_Project/Scripts/Domain/Systemic/AcciMap.cs`。

- 原测例框架为 xunit 2.9.2 + Microsoft.NET.Test.Sdk 17.11.1 + xunit.runner.visualstudio 2.8.2（`W15.Acceptance.csproj`），本地 `/home/box/.nuget/packages` 已有这些包。
- `AcciMap.cs` 及 W15 工程所 glob 的核心/领域源码均无 UnityEngine 引用，无需 Unity 替身。
- 因此实跑原套件，不写隔离夹具替代。真实案卷测例与 Stamp/BowTie 等未跑（未验）。

## 工具与预检

- .NET SDK 8.0.428，`nuget locals` 退出 0
- `unshare -r -n`：先证隔离（仅 lo DOWN，nuget.org 未解析）；testhost 运行时将回环 lo 置 UP，仍无外部解析
- 离线 restore 使用只含 `<clear />` 的 NuGet.Config，随后 `--no-restore` 构建

## 指纹

- `AcciMap.cs` SHA-256 `9564edc9ac9874b4018a06f308a3d00f45a62e9965d11483930f7458cd25bc07`
- 官方 `W15.Acceptance.dll` SHA-256 `6f7fe117f0ae534e89f89b47a957ca8a5a3affa099d10b1b81155d283cbfacdf`
- 编译核心/领域源码 30 个文件指纹见 `accept-out/inventory.json`
- Python 3.13.5

## 过滤实跑（合成）

1. `SixLevels_TopDownOrder_ChineseLabels` Passed — 六层中文层名
2. `DirectionMatrix_MatchesAcceptedAssumption` Passed — 分层方向矩阵
3. `Connect_DownSameSkip_Allowed_UpRejected` Passed — 上层/同层/跨层下行允许，上行拒绝
4. `EnvironmentToCrew_DefaultOn_ConfigurableOff` Passed
5. `Cycles_Rejected_IncludingViaEnvironmentException` Passed
6. `Errors_UnknownDuplicateInvalidLevelAndCreate` Passed — 无效端点 `sys_unknown_node` 等由核心标出
7. `Validate_EmptyAndIsolated` Passed
8. `Demo_AcciMap_Valid_AllSixLevelsUsed` Passed
9. `A2_InformationFlow_UpwardAllowed_IgnoredInCycleCheck` Passed — 因果上行仍拒；信息流可由下往上、不参与成环、不进入因果边集合（分层关系与信息流分别保留）

原始输入为钉住测例内的合成夹具（`MiniAcciMap` / `SystemicDemoData`）。原始输出见 `accept-out/logs/test.stdout` 与 `accept-out/test-results/accimap-core.trx`。

可复跑：

```
timeout --signal=TERM --kill-after=10s 150s python3 tests_acceptance/w15-accimap-core/run.py --source <候选检出> --dotnet /home/box/.dotnet/dotnet --out <空目录>
```

本子项通过。不是 W15 整包。
