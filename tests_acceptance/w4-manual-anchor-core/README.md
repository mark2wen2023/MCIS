# W4 带锚校时独立核心验收（合成）

只测核心 CLI `align`，不动网页/API、不接服务、不写回、不使用正式案卷。
钉 MCIS `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。不改核心或产品。不是 W4 整包。

优先复用已验证的同版构建：`/workspace/mcis-w41-core-out/mcis-core.dll`
（SHA-256 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`），
其 56 项编译输入与本钉源码逐文件一致。不要使用 `tools/mcis-core/mcis-core.sh`（会自动构建）。
不要使用箱上来历不明的 `bin/Release/net8.0/mcis-core.dll`。

## 仓库既有契约（不新增）

- 人工锚点 CSV 表头：`event_key,source_a,time_a_utc,source_b,time_b_utc,note,investigator`
  （见 `ManualAnchorCsvImporter`）。
- 钟差定义：偏移 = 源时间 − 基准时间；校准后时间 = 源时间 − 偏移
  （见 `ClockOffsetEstimate`）。
- 关闭自动来源锚点：各源 `emitGnssAnchors: false`，且 CSV 不设 `eventColumn` / `markChanges`。
- 请求经 stdin 交给：`dotnet <dll> align`。格式错误的人工锚点抛 `BAD_REQUEST`（退出码 4）。

## 三组

1. 两源同事件、已知合成钟差 +12.000 s（SYN-VDR 快于 SYN-GNSS），用人工锚点校时，核符号与量值。
2. 同输入去掉人工锚点，并关闭自动来源锚点：应明确未校准，不得伪造偏差。
3. 格式错误的人工锚点必须给出明确错误，不能报校时成功。

CLI 若未输出逐点对齐时刻，记「未验」，不借冲突摘要声称逐点验证。

```sh
python3 tests_acceptance/w4-manual-anchor-core/run.py \
  --source /path/to/94d5e38-checkout \
  --core-dir /workspace/mcis-w41-core-out \
  --dotnet /home/box/.dotnet/dotnet \
  --out /path/to/empty-out
```

外层请用 `timeout --signal=TERM --kill-after=10s 150s`。有首错即停。
