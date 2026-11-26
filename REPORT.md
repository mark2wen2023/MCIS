# W19 已审核知识卡检索出处 — 官方验收记录

- 固定 SHA：origin/main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`（GitHub 可核的当前默认分支 HEAD）
- 选定理由：origin HEAD 已含现成知识卡审核生命周期与 `GET /api/v1/knowledge/cards`；后来的 W19 search 候选相对该 SHA 未改 `knowledge/router.py`；避开 8183226 模板变更 Chromium 回归。不重跑 W11。
- 候选提交：`eeb7a2a152f95274346f07884fbe6f3b77c299b1`（只新增 `tests_acceptance/w19-knowledge-card-retrieval/`）
- 检索类型：字面大小写折叠子串（普通关键词），**不是**向量或语义检索。合同 `contracts/W19.1-knowledge-cards.md` 写明「q为大小写折叠字面子串，不是语义相似度」。实现为 `Card.search_text.contains(...)`。未调用模型或嵌入。
- 官方运行（Asia/Shanghai）：2026-11-27 05:43:14–05:43:17 CST，退出码 0
- `timeout --signal=TERM --kill-after=10s 150s unshare -r -n`，仅监听 127.0.0.1:18767
- HTTP 结果是 HTTP，不是浏览器结果；不是 W19 整包通过
- `knowledge/router.py@94d5e38` SHA-256 `26686dd2fc14b9f80600b676b547d6a8d9d325b16cdd2b5ca9672383ee76e632`

记录数量：同一合成场景 3 张知识卡（Published / Candidate / Withdrawn）。Dot 原文「两条」；三种状态要在同一次可用检索快照中对照，最少需要 3 条。本 SHA 上知识卡没有案件绑定。

结果：Public 默认 `status=Published` 关键词检索只命中已审核卡，并原样返回 `content.source`（type=Synthetic，excerpt=`SYN-W19-RETR-SRC-PUB`，locator=段落1）。待审与撤回不进入可用结果。Public 查询 Candidate/Withdrawn 为 403。审计链有效，count=6。无首个断点。

未验：向量检索（本入口不存在）、浏览器、正式产品/W19 整包、真实数据、8183226 模板浏览器回归。
