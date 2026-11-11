# W12 · W14 数据导出与分析页种子生成（实施 A，2026-11-11 北京时间）

## 1. W14.2 导出（项目外临时目录，只读）
- 目录 `/tmp/w12-export/`：`ROADMAP.md`、`unity/`、`reports/` 为指向项目的**符号链接**（只读引用），`logs/` 为临时目录。
- 工程 `tests_acceptance/W12Export/`：`W14AccFixture.cs` 从 `tests_acceptance/W14/` 原样复制；`W12Export.csproj` 为 W14 验收工程的拷贝（仅改 RootNamespace）；
  新增 `W12ExportTests.cs`（副本存于 `service/mcis_service/analysis/export/*.txt`）。
- 运行：`~/.dotnet/dotnet test W12Export.csproj --filter ExportForW12` → `/tmp/w12-export/logs/w12-w14-export.json`，复制为 `service/mcis_service/analysis/data/w12-w14-export.json`。
- 内容：`WhatIfDemoFixture` 四个情景与 `Yangze22Case.Run` 五个情景的 `ComparisonTable` 行（结论、`DisplayVerdictText`、`IsCritical`、`CriticalReason`、`SensitivityRangeText`、
  最小净距及其时刻、最小中心距、碰撞时刻/角/部位）、`AntennaSensitivity` 四行、`Inputs`（SourcedValue）、`Assumptions`、`ToMarkdown()`，以及每秒航迹采样（t, E, N, 航向, 航速）。
- 未改 `unity/`、`tools/mcis-core`、`tests_acceptance/`；导出后 `logs/w14.2-impl-hashes-frozen.txt` 37 个文件 sha256 全部一致。

## 2. 种子生成
- `cd service && .venv/bin/python -m mcis_service.analysis.build_seed`
- 曲线全部由已构建的 mcis-core `cpa` 计算：Lily/Mary、海力5 用服务 `GET /cases/{id}/cpa?stepSec=5`（临时数据库）；W14 情景按 2 s 取导出航迹点（东/北 m→nm，航向作对地航向）。
- 交叉核对：导出值与 `logs/w14.2-retest-sensitivity-dump.json`、`logs/w14.2-retest-scenario-dump.json`（Codex 复测留档）逐项比较，容差 1e-6，不一致即中止；本次 52 个值，最大偏差 0。
- 输出 `data/w12-analysis-seed.json` 与旁注 `.sha256`；服务每次读取都按旁注自检。种子里记录全部输入文件的 sha256（`test_seed_sources_not_stale` 会在输入变化时报“种子已过期”）。
