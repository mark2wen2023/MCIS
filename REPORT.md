# W11 组合试点报告（阻塞：现有产品接口无法组合）

结论：**阻塞**。不是 W11 整包。已有两轮官方证据不能当作同一轮组合通过，故未重跑那两轮。组合业务实跑：**未验**。未改产品、未开新接口、未用假核心、未直写生产表、未给 Mark 发消息。未改第 40–42 行。

- 派遣：#106 评论 7200240703
- 已接：https://github.com/mark2wen2023/MCIS/issues/106#issuecomment-7200309035 （id 7200309035，2026-11-27 02:18:43 CST）
- 候选基准：`875ccc50b049fb24b82f6b0663f3f9476db1880e`（理由：该钉已同时包含真实 .NET 验收与 41eb599/b40a6ca 单边原文工装，且是已复核的真实 .NET 验收钉）
- 单边原文钉：`41eb599f5a42eb2d0938ad4212936a0949a1cef5`（875ccc50 的祖先；http_real.py / host.py / check.py / pilot.py / 产品 router 字节与 875ccc50 一致）
- 验收候选：`candidate/w11-combined-pilot` @ `e1ee4f162465cffaafcb9e75d7bf5514ddd4334a`（相对 875ccc50 只新增 `tests_acceptance/w11-combined-pilot/`）
- 官方运行时刻：2026-11-27 02:22:03 CST
- 外层：`timeout --signal=TERM --kill-after=10s 150s`，官方脚本退出码 **3**（有意的接口断点，不是超时或崩溃）
- SDK 预检：dotnet 8.0.428，`nuget locals` 退出 0。组合实跑未启动服务。

## 既有证据为何不算同一轮

1. `evidence/w11-core-grokbot-875ccc5` @ `5d33addffde4565903367276e7ad4e0568860327`（zip SHA-256 `87dbabc691ab77a58a08fecbd78dd78df582a681fb98a42c10eeb21c4bb100d6`）：原 .NET 合成预览/保存/同库重开通过，官方声明不含 association / 浏览器 / 完整 HTTP 生命周期。
2. `evidence/w11-grokbot-b40a6ca`（基于 41eb599 的 b40a6ca 浏览器轮，zip SHA-256 `b2038e908ced208e2787a36d87e96afec9c393d8ab2ba5d5119999abb2365b1f`）：显式点击读取、改版/撤销后旧关联不可读、T+109 作为原文记载时间。但保存走 `fixture_core`，登记靠直写 `pilot_single_source`，读取走工装私有路由 `/__local_synthetic_w11/{CASE}/edge-excerpt`，不是产品接口。
3. `tests_acceptance/ECFCNEW/http_real.py`（41eb599/875ccc50 原件 SHA-256 `2fe1b3ad833b4af289e7d74b8818c705276c0cb6ea0e7019abcb19a89f0b45c4`）：真实回环 HTTP 预览/保存，但草稿 `edges=[]`，无单边原文登记或读取。

## 各门槛

- 同一轮已有证据覆盖全部门槛：否
- 原 .NET 生成/保存当前草稿：仅在 875ccc5 核心轮单独满足；组合轮未验
- 该版本单边已登记合成通联原文：仅在 b40a6ca 以试点表满足；组合轮未验
- 明确点击/读取意图才返回片段：仅在 b40a6ca 试点路由上满足；组合轮未验
- 读取保持指定图版本/边/原文片段：仅在 b40a6ca 试点适配器上满足；组合轮未验
- 改版或撤销后旧关联不可再读：仅在 b40a6ca 试点适配器上满足；组合轮未验
- T+109 只作为原文记载时间：仅在 b40a6ca 轮（2026-02-01T12:01:49.000Z）；组合轮未验
- 同一库 SQLite 状态与既有审计：两轮各自核对，不是同一库同一轮；组合轮未验
- 不用假核心、不直写生产表：单边原文工装不满足，故不能当作产品组合
- 现有产品接口可组合且无须新开接口：否

## 首个断点

- 文件：`service/mcis_service/ecfc_drafts/router.py`
- 版本：`875ccc50b049fb24b82f6b0663f3f9476db1880e`（与 41eb599 及 d9187fe 导出字节相同）
- SHA-256：`a3e29516ba1116c4f4876ebeab325d3d3f3364d0061919f96409a14c2979f4b6`
- 内容：产品 ECFC 仅有 GET context、GET draft、POST save、GET audit、POST preview；context 声明 `sourceBinding=registered-metadata-only`（约第 322 行）。没有按「图版本/边」登记或在明确读取意图下返回通联原文片段的产品接口。按派遣不得临时开接口或改产品，故停止。

对照工装（未当作产品接口使用）：

- `tests_acceptance/w11-edge-host-optin/host.py` SHA-256 `9ffcc5152f5de516ade287c8998f68322bb108015ed0d0e4eac2f83b0fbe2255`
- `tests_acceptance/w11-excerpt-binding-local/check.py` SHA-256 `79f0583a1a18edef8cec7f15b8f9c507be29117803f77dc937b68387f116de86`
- `tests_acceptance/w11-excerpt-binding-local/pilot.py` SHA-256 `6d09489264e3bbff5a36576702bf5b91b8536d6f6c991ad78731885de120fe66`（写明不是 API）

原始回执：`accept-out/receipt.json`、`accept-out/summary.json`、`accept-out/logs/product-ecfc-routes.json`。
