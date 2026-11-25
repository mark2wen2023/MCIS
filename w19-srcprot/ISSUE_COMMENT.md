【Grokbot｜W19 来源变更｜待复核】

**W19 来源变更：真浏览器通过（产品固定 b3b8ae3；验收候选 8183226 官方脚本退出码 0，未改工装）**

— Grokbot

### 版本
- 产品固定：`b3b8ae36e7eaeac759eecb7f136ca46e77dc6571`。`KnowledgePage.tsx` / `knowledge/api.ts` blob 与脚本钉扎一致。产品未改。
- 派发的验收候选：`8183226c579af6ddcdcfef2078c68fdacf1885d2`（相对产品仅两份验收文件）。本轮按该提交原脚本跑通，没有再改验收文件。

### 浏览器与退出码
- Google Chrome **156.0.8078.47**（`/opt/google/chrome/google-chrome`，`chromium_sandbox=True`，没有 `--no-sandbox`）。现成 Python Playwright 1.65.2（支持 `route_web_socket`，未新装包）。
- 按 README 跑 `8183226` 原脚本（**不用** `--http-only`）：退出码 **0**。输出 `Sandboxed Chromium + Vite + FastAPI/SQLite PASS (W19 template source drift blocked → single synthetic internal candidate → explicit review → service reopen → withdrawn / Public denied)`。未把 HTTP-only 算作真浏览器通过。

服务只监听 127.0.0.1，临时 SQLite，`MCIS_KNOWLEDGE_SUGGESTION_PROVIDER=template-stub-v1`，页面流量限制在 Vite 回环源。

### 流程断言（真页面，产品 b3b8ae3）
合成卡「W19 真浏览器专用合成卡」：套用旧摘录模板后改来源，警告「原模板填入内容不能直接保存」，正文仍为旧摘录，保存禁用；恢复旧文字后仍禁用。此阶段无卡片 POST、无记录、无审计。按当前获准来源重新预览/套用后只创建一条内部待审候选；公众发布前不可见。三项人工勾选后发布。重启同一 SQLite 后按编号读回「已人工批准发布」，来源「合成段落第 8 段」与摘要/digest/审核说明不变。撤回后按编号为「已撤回」，公众列表与详情仍 404。审计恰好 3 条：`knowledge.create`、`knowledge.published`、`knowledge.withdrawn`，`audit:verify` count=3。无跨源请求。

### 截图（通过那次 `--out`）
- 恢复旧来源后仍禁止保存：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/01-template-stale-after-restoring-old-source.png
- 仅一条内部待审：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/02-saved-candidate.png
- 按编号待审：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/03-readback-candidate.png
- 发布前公众不可见：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/04-public-denied-before-publish.png
- 三项勾选可发布：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/05-three-checks-ready.png
- 已发布：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/06-published.png
- 重启后按编号已发布（来源与摘要仍在）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/07-reopen-after-restart.png
- 撤回后按编号已撤回：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/09-reopen-withdrawn.png
- 撤回后公众仍读不到：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/screenshots/10-public-denied-after-withdraw.png

### 未验
Firefox / WebKit；headed；触屏；真实模型或真实案卷；远程 CI。未跑 `--http-only`，也不把它算作真浏览器通过。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w19-srcprot-grokbot-8183226/w19-srcprot
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w19-srcprot-grokbot-8183226/w19-srcprot/mcis-w19-srcprot-report.tar.gz
- SHA-256：`b70d62974877dd4676096cd6f3385d659988859cea8018dc661019bf0ed0a46b`

没有修改产品，没有合并，没有部署，也没有触发远程 CI。未接真实模型或数据。

请 Dot 在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
