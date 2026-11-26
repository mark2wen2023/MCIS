# W4 带锚校时独立核心验收报告（Grokbot）

时间：2026-11-26 23:55 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7195884007
已接：#106 comment 7196743533（2026-11-26 23:46 Asia/Shanghai）

本项在独立候选只新增 `tests_acceptance/w4-manual-anchor-core/` 合成夹具与验收脚本，实测核心 CLI `align`。未改核心或产品，不接服务，不写回，不动网页/API 或正式案卷，不碰 W4.1 原验证、W21、3D 仓库、main、CI，不合并、不部署、不安装。不是 W4 整包。

## 钉 SHA 与核心复用

- 产品钉：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`。候选 `candidate/w4-manual-anchor-core` @ `3c408593143ae1dddc5f065ea8549566fcd40be8` 以其为祖先，相对钉只新增本验收目录。
- `tools/mcis-core/src/AlignCommand.cs` SHA-256 `4ce13b7fec0898f01d3157b99278561a1ea391d0f4ce3140c1bc9f79fda99b58`，与已验证构建清单一致。
- `/workspace/mcis-w41-src-94d5e38` 的 56 项编译输入与 `/workspace/mcis-w41-core-out/build-manifest.json` 全部一致，故复用已验证核心，未重建：
  - `mcis-core.dll` `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`
  - `mcis-core.runtimeconfig.json` `3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598`
  - `mcis-core.deps.json` `fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12`
- 工具：.NET SDK / 运行时 8.0.428（`/home/box/.dotnet/dotnet`），Python 3.13.5。直接 `dotnet <dll> align`，未用会自动构建的 `mcis-core.sh`，未用箱上来历不明的 `7afd120c…` DLL。

钟差定义（仓库既有，未新增契约）：偏移 = 源时间 − 基准时间；校准后时间 = 源时间 − 偏移。人工锚点 CSV 表头为 `event_key,source_a,time_a_utc,source_b,time_b_utc,note,investigator`。三组均设 `emitGnssAnchors: false`，CSV 不设 `eventColumn` / `markChanges`。

## 官方运行

`timeout --signal=TERM --kill-after=10s 150s run.py`，退出码 **0**。`receipt.passed=true`，无第一条失败。未手发信号。

合成案件 `SYN-W4-MANUAL-ANCHOR-1`，纪元 `2026-03-01T08:00:00Z`，基准 `SYN-GNSS`，对比源 `SYN-VDR`，已知合成钟差 +12.000 s（VDR 快）。

### ① 人工锚点校时

退出码 0，`ok=true`。三条人工锚点（EVT-IMPACT / EVT-CUE / EVT-STOP）将同一事件的 GNSS 时刻与 VDR 时刻（各 +12.000 s）对齐。
- SYN-GNSS：`isReference=true`，`status=Reference`，`offsetSeconds=0`。
- SYN-VDR：`status=Calibrated`，`offsetSeconds=12`，符号为正，与「源 − 基准」一致；`manualAnchorCount=3`；描述「已校准，偏移 +12.000 s ±0.001 s（锚点 3，人工 3）」。
- `calibration.allCalibrated=true`，未校准源为空。`stats.manualAnchorCount=3`，`stats.anchorCount=6`（每人锚点两条观测，无自动锚点）。

### ② 去掉人工锚点并关闭自动来源锚点

同输入、无 `manualAnchors`。退出码 0，`ok=true`。`clockOffsets=[]`，未伪造 +12 或其他有限偏差。`allCalibrated=false`。SYN-GNSS 与 SYN-VDR 均为 `Uncalibrated`，`offsetSeconds=null`，描述「未校准（无共同锚点，按原始时间使用）」。`calibration.error` 为 `timeline_no_reference: 基准数据源不存在于锚点观测中：SYN-GNSS`。`anchorCount=0`，`manualAnchorCount=0`。

### ③ 格式错误的人工锚点

`time_a_utc=not-a-utc-timestamp`。退出码 4，`ok=false`，无校时成功结果。`error.code=BAD_REQUEST`，`error.message=人工锚点导入失败：vdr_manual_anchor_bad_time 人工锚点第 3 行 time_a_utc 无效：not-a-utc-timestamp`。

### 逐点对齐时刻

未验。CLI `align` 的 JSON 只给出各源钟差与校准摘要，不含逐样本对齐时刻。不借冲突摘要声称逐点验证（本组冲突列表为空）。

已验：三组核心 CLI 请求/原始输出/退出码、偏差符号与量值、未校准不伪造、格式错误明确失败。未验：逐点对齐时刻、网页/API、写回、服务、W4.1 原验证、W21、W4 整包。
