【Grokbot｜W19｜待复核】

**W19：真浏览器通过（产品固定 d0c4d8c；工具候选 9c878b1 原脚本在 get_by_label「标题」处阻塞；验收工装候选 9d7d843 修复选择器后退出码 0）**

— Grokbot

### 版本
- 产品固定：`d0c4d8c2a6f2aaeee5e49b2085d4f744a491d642`。`KnowledgePage.tsx` / `knowledge/api.ts` blob 与脚本钉扎一致。产品未改。
- 派发的工具候选：`9c878b1ad055deea52ba8c0fb46ef7c3e05017fa`（相对产品仅两份验收文件）。
- 本轮工装候选：`9d7d84326d050f004b633fd80f27a38297d7b135`，分支 `candidate/w19-chromium-label-fix-grokbot-9c878b1`。相对产品仍只有验收文件。diff：用 label 首个文本节点定位创建表单的 textarea，并增加可选 `--out`。

### 浏览器与退出码
- Google Chrome **156.0.8078.47**（`/opt/google/chrome/google-chrome`，`chromium_sandbox=True`，没有 `--no-sandbox`）。Python Playwright 1.65.2（支持 `route_web_socket`，现成依赖，未新装包）。
- 按 README 跑 `9c878b1` 原脚本（**不用** `--http-only`）：退出码 **1**。沙箱 Chrome 已打开知识页并点了「填入合成示例」，但 `get_by_label("标题", exact=True)` 超时——填入示例后无障碍名会带上文本框内容。复试同一阻塞。这是原工装的首个阻塞，不是缺少沙箱，也不是产品逻辑失败。
- 同一产品流程，用 `9d7d843` 工装重跑：退出码 **0**。输出 `Sandboxed Chromium + Vite + FastAPI/SQLite PASS (... withdrawn / Public denied)`。未把 `--http-only` 算作真浏览器通过。

服务只监听 127.0.0.1，临时 SQLite，页面流量限制在 Vite 回环源。

### 流程断言（真页面，产品 d0c4d8c）
同案纯合成卡「W19 真浏览器专用合成卡」：内部新建待审 → 公众不可见 → 三项人工勾选后发布 → 重启同一 SQLite 后按编号读回「已人工批准发布」，摘录/定位/digest/审核说明不变 → 撤回后按编号为「已撤回」，公众列表与详情仍 404。审计恰好 3 条：`knowledge.create`、`knowledge.published`、`knowledge.withdrawn`，`audit:verify` count=3。无跨源请求。

### 截图（通过那次 `--out`）
- 已填表单：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/01-create-form-filled.png
- 内部待审：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/02-saved-candidate.png
- 按编号待审：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/03-readback-candidate.png
- 发布前公众不可见：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/04-public-denied-before-publish.png
- 三项勾选可发布：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/05-three-checks-ready.png
- 已发布：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/06-published.png
- 重启后按编号已发布（出处仍在）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/07-reopen-after-restart.png
- 撤回后按编号已撤回：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/09-reopen-withdrawn.png
- 撤回后公众仍读不到：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w19-grokbot-9c878b1/w19/screenshots/10-public-denied-after-withdraw.png

### 未验
未改工装的 `9c878b1` 原脚本真浏览器路径未跑完（首个阻塞见上）。Firefox / WebKit；headed；触屏；真实模型或真实案卷；远程 CI。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w19-grokbot-9c878b1/w19
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w19-grokbot-9c878b1/w19/REPORT.md
- 工装候选：https://github.com/mark2wen2023/MCIS/tree/candidate/w19-chromium-label-fix-grokbot-9c878b1
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w19-grokbot-9c878b1/w19/mcis-w19-report.tar.gz
- SHA-256：`28f68a9a32129fbd3899bab86f97f879987177c2a4c71b9dbe2f6c4adfc30eaa`

没有修改产品，没有合并，没有部署，也没有启用远程 CI。未接真实模型或数据。

请 Dot 在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
