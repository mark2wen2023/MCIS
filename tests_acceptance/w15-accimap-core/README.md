# W15 AcciMap 核心验收（原套件，合成）

执行方法：**原套件**。不改 `tests_acceptance/W15/` 或核心源码。本目录只提供可复跑包装：离线预检、构建并过滤实跑钉住的 xunit AcciMap 测例。不能用网页组件代替。不是 W15 整包。

钉 MCIS `2447b14076bbf39db014b8bf4a3a3b350cbf0e05`。先读 `tests_acceptance/W15/AcciMapStampAcceptanceTests.cs` 与 `unity/Assets/_Project/Scripts/Domain/Systemic/AcciMap.cs`。原工程 `tests_acceptance/W15/W15.Acceptance.csproj` 已引用 xunit 2.9.2、Microsoft.NET.Test.Sdk 17.11.1、xunit.runner.visualstudio 2.8.2；本地 NuGet 缓存已有这些包，AcciMap 核心无 UnityEngine 引用。因此实跑原套件，不写隔离夹具替代。

过滤（只用合成数据，不跑真实案卷或其他子系统）：

- `AcciMapAcceptanceTests`（8 项）：六层与中文层名、方向矩阵、分层因果连接、环境→船员开关、成环拒绝、未知/重复/非法端点、空模型与孤立、演示模型
- `A2_InformationFlow_UpwardAllowed_IgnoredInCycleCheck`：因果上行仍拒；信息流可由下往上、不参与成环、不进入因果边集合

testhost 需在隔离命名空间内将回环 `lo` 置 UP（仍无外部路由，nuget.org 不解析）。不安装、不接外部源。

```sh
timeout --signal=TERM --kill-after=10s 150s python3 tests_acceptance/w15-accimap-core/run.py \
  --source /path/to/this-checkout \
  --dotnet /home/box/.dotnet/dotnet \
  --out /path/to/empty-out
```
