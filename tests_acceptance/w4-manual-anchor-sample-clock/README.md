# W4 逐点校时独立核心验收（合成）

直接走核心导入、人工锚点、偏移估算与校准流程，读取校准后时间线的逐点输入时刻、校准后时刻与基准源。不调用 CLI，不重跑三组 CLI 作替代，不改 CLI/产品。不是 W4 整包。

钉 MCIS `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。两源合成点与三组 UTC 锚点复制自已验证候选 `3c40859`，来源哈希见 `fixtures/SOURCE-HASHES.json`。核心调用参照 `tests_acceptance/W2/ClockOffsetAcceptanceTests.cs`：`VdrCsvImporter`、`ManualAnchorCsvImporter`、`ManualAnchors.Merge`、`ClockOffsetEstimator.Estimate`、`TimelineCalibrator.Calibrate`，再读 `Track.Samples`。

断言：基准源时刻不移；快 +12 s 的源减去 12 s；数量、顺序、来源及观测值未改；同输入去锚时原时刻逐点不动且状态为未校准。

```sh
python3 tests_acceptance/w4-manual-anchor-sample-clock/run.py \
  --source /path/to/this-checkout \
  --dotnet /home/box/.dotnet/dotnet \
  --out /path/to/empty-out
```

构建只用已有 .NET SDK 8.0.428 与本地缓存、离线完成。外层请用 `timeout --signal=TERM --kill-after=10s 150s`。有首错即停。
