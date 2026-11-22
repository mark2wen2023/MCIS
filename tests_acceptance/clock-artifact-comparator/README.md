# 合成跨端时钟对账（仅测试产物）

此入口不启动浏览器，也不定义三维端的回执格式。基于 MCIS 固定回执检查未来采集产物的明确字段映射；不是 V1、运行时接口、授权或两端联调通过证明。

固定 MCIS 回执：`8d68f6fa076b7acad90fab10e95ab88c6945a018:tests_acceptance/cross-repo-clock-receipt/receipt.json`，原字节 SHA-256 `7860ef04924f49954ceba3be596a0258682de2f96c1060f1c8123fa34aa5c51a`。工具只读该 Git 对象，缺失即失败，不联网。其 fixtureCommit 是 `2048c60fd6650c6f2c99a76a16be463a3895655d`；A/B/混案文件摘要与生产模块摘要保留在原回执。这里不重新登记、不新增 Access，也不重复声称真实数据库实测。

## 现在可复跑

仓库内，Python 3.10+、标准库和 Git 即可：

```sh
python -I -B tests_acceptance/clock-artifact-comparator/check.py
```

10 项纯合成测试，退出 0。包括实际 CLI 子进程成功 0、改动产物字节后拒绝 1。`check.py:fixture()` 是明确模拟的另一种 JSON 形状，假 build 为 40 个 `a`，不是实际三维提交，也不是对方格式建议。正常映射依据固定 MCIS 回执构造；负例逐项独立改动。测试不会运行浏览器/HTTP/模型或读取业务库。

## 收到真实采集文件以后

先由验收者独立确认采集来源、候选完整 commit、采集类型与原始文件 SHA-256；保存只读产物，再按**实际字段语义**编写单独 mapping JSON。不要用 HUD 或悬停记录冒充播放帧。没有精确字段就拒绝/补采集，不推断、不修改原产物。不要把 `check.py` 的模拟字段要求移植为对方生产格式。

```sh
python -I -B tests_acceptance/clock-artifact-comparator/compare.py \
  --artifact /明确路径/采集.json --mapping /明确路径/审核映射.json
```

mapping 字段（完整模拟用法可读 `check.py:fixture()`）：

- `expectedCandidateCommit`：验收者确认的 40 位小写 Git SHA；工具比较声明，不证明该提交实际被浏览器执行。
- `expectedArtifactSha256`：采集文件**原字节** SHA-256，不能以 JSON 重序列化代替。
- `declaredArtifactOrigin`：`simulated_fixture` 或 `externally_supplied_browser_capture`，仅来源声明。
- `root`：candidateCommit/inputCommit/caseId/frames；`files`：原回执的三个文件名至对应 SHA 字段。
- `frame`：utc/kind/instantCpaAvailable/vessels；`vessel`：vesselId/status/jsonPointer/fileSha256/positionKind/headingKind/headingMissing，以及 time_sourceUtc/time_alignedUtc/time_correctionSeconds/time_status。
- 每个字段是 `{"path":["实际键",0,"实际键"]}`，相对当前根/帧/船对象；可选 `values` 字符串枚举翻译（如实际“悬停”只能映射 hover，不能映射 playback_frame）。映射本身须人工核对；工具报告其原字节 SHA。无表达式、默认值或缺失补值。

四帧必须按 T+100、121、124.250、127.500 顺序，UTC 精确匹配固定回执；状态/定位/品质/原始 UTC/修正/对齐逐项匹配。127.500 必须是 `2026-02-01T12:02:07.500Z`，`12:02:08` HUD 不可替代。B 后三帧无精确点，不可借邻点 pointer；A 缺口保留缺口 pointer，不是原点；仅当固定 MCIS 回执明确 `declared_gap` 时禁止即时 CPA 可用（本组为 T+124.250）；`no_observation_at_time` 仅表示原件无精确行，不能据此否定另行派生的回放位置。T+121/T+127.500 允许可用或不可用，但 B 原点 pointer 仍须为空，派生位置不充当原始观测。所有帧必须有布尔可用状态，缺失或数字 0/1 不接受；缺口必须显式 false。工具不复算或验证任何 CPA 数值，也不证明回放插值可靠。未知艏向不能由 COG 填补。

成功输出 `semantic_comparison_matches`、有限来源声明、固定 MCIS/输入/候选提交及文件/产物/映射摘要，**始终** `browserExecutionVerified:false` 与 `artifactAuthenticityVerified:false`。失败退出非零，不输出输入正文。10 项通过不是浏览器、播放、三维或真实账号通过；完整候选提交真实性、实际播放操作、采集链路真实性仍需独立证据。校时依据未交付、人审未签；展示对齐不确定同一事故事件先后/同时。

## 误拒修正的实测记录

在未改动的 3fa858a 比较逻辑上先加入端点反例：T+121 与 T+127.500 的 CPA=true 各被误拒，10 项测试退出 1（2 个错误）。收窄为 declared_gap 后同一套 10 项退出 0；原有精确 UTC、空原点 pointer、来源/品质/摘要、CLI 和未验真声明检查保留。新增模拟值仅验证对账规则，不是浏览器采集或 CPA 算法证明。原冻结记录不改，新冻结见 logs/clock-artifact-comparator-gap-fix-impl-hashes-frozen.txt。
