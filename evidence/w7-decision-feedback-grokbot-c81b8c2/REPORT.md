# MCIS W7 已登记回复意见 → 采纳决定与反馈 → 重开核对（真浏览器通过）

- 执行时间：2026-11-28 08:54（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 检索：本版本没有可复用的真浏览器原件覆盖本链。`7164675100` / `evidence/w7-deadline-grokbot-1f329c3` / 工装 `0092734` 是期限、回复、关闭与 SQLite 重开，未重跑、未充数。`cbb3997` 的同页切轮回执（`7d85b68`）不是本产品版本，未当作本项证据。产品树内 `consultation_browser.py` 使用 `--no-sandbox`，且范围扩到冲突、权限和旧响应并发，不能作为本单合格原件。
- 产品固定：`b2ecb50b32b721c9f171b74ecd576691c0048b94`（2026-11-25 20:41:08 +0800）。启动前核对其 `ConsultationPanel.tsx`（`492b65fcace052d6ced7860fc4576f2cc5ba240c`）、`model.ts`（`462537d3eb3421bef6699d904d7841d497450077`）、`recommendations/router.py`（`aa39f644a3205f255c1a686295fc06f559282ebf`）的 Git blob 与工装钉扎一致。
- 独立验收候选 `candidate/w7-decision-feedback-browser`：`c81b8c2e7f0fa78aeb08df0c533683a03370d840`。只新增 `tests_acceptance/w7-decision-feedback/{README.md,host.py,run.py}`。未改产品、权限、CI、契约、主线。未安装、未合并、未部署。未用真案/4A/模型。
- 正式页 `#/recs?case=` + 真实本机服务（127.0.0.1:18794 / Vite 127.0.0.1:18795），隔离临时 SQLite，`seed_demo=False`。官方接口预置一案一轮一条待处理合成意见：`SYN-W7-DECISION-001`，第 1 轮 `SYN-DRAFT-D1`，意见 `R1-C01`「合成待处理意见一条（虚构）。」
- 官方脚本 `timeout 150 … run.py` 退出码 **0**。Google Chrome 156.0.8078.47，`chromiumSandbox: true`，没有 `--no-sandbox`。
- 真页面：选择「部分采纳」后不填理由，「保存决定」禁用且无写入；仅填空白后按钮仍禁用、仍无写入。填入合成反馈「合成部分采纳反馈：仅核对待处理意见的书面理由（虚构）。」后只发出一次 `PATCH /consultation/rounds/1/comments/R1-C01`（HTTP 200），表单消失，页面显示「部分采纳」与原样反馈。保存后征求意见审计恰好新增一条 `consultation.decide`（`after=PartiallyAdopted；`加原样反馈，`entityId=R1-C01`），哈希链有效。重启同一临时 SQLite 后再打开正式页：仍为第 1 轮 `SYN-DRAFT-D1`、意见 `R1-C01`、决定「部分采纳」与原样反馈，无保存按钮；重开只读、无新写入，审计三条不变（`consultation.open` / `reply` / `decide`）。
- 截图 `01` 与 `02` 像素相同（空白与空理由在页面上看不出差别）；空白路径的禁用与无写入由脚本断言，不以截图差异代替。`03` 为保存后，`04` 为重开同一数据库后。
- 工装在首次试跑时，截图滚动用了非唯一的 `.w7-comment`（回复块与意见行同名），已只改验收脚本后重跑官方路径；未放宽断言，未改产品。
- 未发送、未签发、未做旧响应并发。此项不等于 W7 整包。未验 Firefox / WebKit、headed、真实案卷。
