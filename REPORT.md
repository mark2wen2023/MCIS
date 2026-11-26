# W4 逐点校时独立核心验收报告（合成）

结论：本子项通过。不是 W4 整包。未改 CLI/产品/核心。未重跑三组 CLI 作替代。未接服务或浏览器，未写回，未合并，未部署，未安装，未触网取包。

- 派遣：#106 评论 7197597772
- 已接：https://github.com/mark2wen2023/MCIS/issues/106#issuecomment-7198135887 （id 7198135887，2026-11-27 00:49:11 CST）
- 产品钉：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`
- 验收候选：`candidate/w4-manual-anchor-sample-clock` @ `ea0b3bd6ce1a2a6a0a94617f887fc60fb8589f60`
- 夹具来源（只复制、未改 3c40859 工作树）：`3c408593143ae1dddc5f065ea8549566fcd40be8`
- 官方运行时刻：2026-11-27 00:56:08 CST
- 外层：`timeout --signal=TERM --kill-after=10s 150s`，退出码 0
- 夹具退出码 0，`receipt.passed=true`，无第一条失败
- `cliUsed=false`

## 工具与预检

- .NET SDK 8.0.428（`/home/box/.dotnet/dotnet`），预检通过
- `dotnet nuget locals all --list` 退出 0；全局包 `/home/box/.nuget/packages/`
- 离线命名空间：`unshare -r -n`，仅 `lo DOWN`，nuget.org 未解析
- 项目无 PackageReference。离线 `restore` 使用只含 `<clear />` 的 NuGet.Config（不接 nuget.org），随后 `--no-restore` 构建，restore/build 退出 0
- Python 3.13.5，unshare from util-linux 2.41.5
- 未安装任何包，未伪造 SDK 初始化

## 指纹

- 夹具 W4SampleClock.dll SHA-256 `55a465fb0360e1ca11c4c8b5976525fba175ff146b731273d595493cee15adb3`
- runtimeconfig SHA-256 `97c9700542b659150b230c3578b29530fd76ab01ec66a92cd16945e0245713df`
- deps SHA-256 `dfd136a31becb78bf802327a505b124f6918bc160c7e2acb83e5f7456affa1b0`
- 编译的核心源码文件 38 个，逐文件 SHA-256 见 `accept-out/inventory.json`
- 合成点/锚点复制自 3c40859，`fixtures/SOURCE-HASHES.json` 中 `allCopiedBytesMatch=true`：
  - syn-gnss.csv SHA-256 `714b34cd0d01df8dbd2ddde9c423cd0861e74073c8e50e333b3feb12a27cfe02`
  - syn-vdr.csv SHA-256 `42d54483b2c28094b4a14908d21b5055dbdfae3d48a6b676ff8dc9814e287a2e`
  - manual-anchors-valid.csv SHA-256 `91b4277de01e01d797818bd8ca3128789dbfc4a11e495d27af909cd65d174f48`

## 方法

单独夹具直接调用既有核心：`VdrCsvImporter`（`EmitGnssAnchors=false`）→ `ManualAnchorCsvImporter` → `ManualAnchors.Merge` → `ClockOffsetEstimator.Estimate(..., OffsetMethod.Median)` → `TimelineCalibrator.Calibrate`，再逐点读 `Track.Samples`。参照 `tests_acceptance/W2/ClockOffsetAcceptanceTests.cs`。不调用 `align` CLI。

钟差定义（既有）：偏移 = 源时间 − 基准时间；校准后时间 = 源时间 − 偏移。基准 SYN-GNSS，快源 SYN-VDR 已知 +12.000 s。历元 `2026-03-01T08:00:00Z`。4 条轨道（每源 SpeedOverGround 与 CourseOverGround）× 5 点 = 20 点。

## 逐点结果

① 有三组 UTC 人工锚点：估算成功。SYN-GNSS `status=Reference`，`offsetSeconds=0`，08:09/10/11/12/13 时刻逐点不移。SYN-VDR `status=Calibrated`，`offsetSeconds=12`，输入 08:09:12…08:13:12 校准后为 08:09:00…08:13:00。数量 20=20，轨道顺序与来源、观测值（8.0/90、8.0/90、7.8/91、7.5/92、7.2/93）未改。`allCalibrated=true`。原始结果：`accept-out/core-out/points-with-manual-anchors.json`。

② 同输入去锚：估算失败，`timeline_no_reference: 基准数据源不存在于锚点观测中：SYN-GNSS`。`clockOffsets=[]`。两源均为 `Uncalibrated`。VDR 与 GNSS 原时刻逐点不动（VDR 仍为 08:09:12…）。数量、顺序、来源及观测值未改。原始结果：`accept-out/core-out/points-without-manual-anchors.json`。

可复跑：

```
timeout --signal=TERM --kill-after=10s 150s python3 tests_acceptance/w4-manual-anchor-sample-clock/run.py --source <候选检出> --dotnet /home/box/.dotnet/dotnet --out <空目录>
```

本子项通过。不是 W4 整包。
