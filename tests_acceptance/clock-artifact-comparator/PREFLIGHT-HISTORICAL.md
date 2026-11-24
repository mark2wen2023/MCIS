# 固定合成四帧离线预检

只检查原合成资料和同一份历史回执。不要称其为新浏览器运行、采集出处认证或 SQLite 联验。脚本不联网、不启动服务、不更改产品；本目录不包含轨迹副本、JSONL、压缩包或截图。取用授权存档中的原字节，不复制或重序列化：

- MCIS `2048c60fd6650c6f2c99a76a16be463a3895655d`：`tests_acceptance/shared-trajectory-cross-repo-expanded/` 内三份同名合成文件（按固定提交的树定位）。
- mcis-3d `de9356a4616c0ef593ffff0ca81fd959ff24c1b3`：`tests/fixtures/mcis-cross-repo-2048c60f/` 内三份文件。
- MCIS `8d68f6fa076b7acad90fab10e95ab88c6945a018` 的 `tests_acceptance/cross-repo-clock-receipt/receipt.json`。
- 历史 `four-point-clock-receipt.jsonl` 原样，4377 字节，SHA-256 `c56ee87fb35aac8cc356314b2be4684b43fe33cbf8a90df7a968b498dcac6ec6`；此摘要不证明浏览器版本或执行来源。

```sh
python3 -I -B tests_acceptance/clock-artifact-comparator/preflight_historical_capture.py \
  --mcis /path/to/fixed-mcis-fixtures --three-d /path/to/fixed-3d-fixtures \
  --expected /path/to/receipt.json --observed /path/to/four-point-clock-receipt.jsonl
```

退出 0 表示四个时点与 48 个共有船舶字段符合固定收据，并列明 16 个仅此历史产物允许的显式空值省略；退出 1 为拒绝。输入必须满足三个原件的 SHA-256、Git blob 和跨仓字节一致，不会以测试重新制造 Git 历史。新回执即使时间正确也必须走正式的独立采集和对账，不能使用这条固定历史摘要冒充验收。
