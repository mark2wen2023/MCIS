【Grokbot｜W7 期限｜待复核】

**W7 期限：真浏览器通过（产品固定 b2ecb50；验收候选 1f329c3 原脚本在临时 Vite 缺 contracts/ 处阻塞；工装候选 0092734 修复后退出码 0）**

— Grokbot

### 版本
- 产品固定：`b2ecb50b32b721c9f171b74ecd576691c0048b94`。`RoundLifecycle.tsx` / `RecommendationsPage.tsx` / `recommendations/router.py` blob 与脚本钉扎一致。产品未改。
- 派发的验收候选：`1f329c36423456cc11446e0987daf4381e3cfee4`（相对产品仅三份验收文件）。
- 本轮工装候选：`0092734837f652a813be41eb65148a3ce57982a7`，分支 `candidate/w7-deadline-chromium-grokbot-1f329c3`。相对产品仍只有验收文件。diff：为已钉扎产品补上临时 Vite 对 `contracts/` 的只读链接；重启后 `reload` 建议页；角色已是 LeadInvestigator 时不再次选择（避免同一身份事件卡住「正在读取」）；可选 `--out` 截图；临时代理关闭 keep-alive。

### 浏览器与退出码
- Google Chrome **156.0.8078.47**（`/opt/google/chrome/google-chrome`，`chromiumSandbox:true`，没有 `--no-sandbox`）。现成 Node Playwright 1.63.0-alpha-2026-08-31（支持 `routeWebSocket`，未新装包）。
- 按 README 跑 `1f329c3` 原脚本（**不用** HTTP-only）：退出码 **1**。临时 Vite 副本缺少产品根目录 `contracts/`，页面无法解析 `report.schema.json`，`select.role-select` 超时。这是原工装的首个阻塞，不是缺少沙箱，也不是产品逻辑失败。
- 同一产品流程，用 `0092734` 工装重跑：退出码 **0**。输出 `W7 sandboxed Chromium PASS: two registered/closed rounds, default30 vs declared45, reopened UI and real audit.` 未把 HTTP-only 算作真浏览器通过。

服务只监听 127.0.0.1，临时 SQLite，页面流量限制在 Vite 回环源。

### 流程断言（真页面，产品 b2ecb50）
同一纯合成案 `SYN-W7-CHROMIUM-DEADLINE`：默认 30 天核对文案「默认期限：服务登记时间起 30 天」，确认前无写入，payload 无 `days`；已商定 45 天核对文案含「系统不核验是否已经商定」，payload `days: 45`。两轮均登记合成回复并关闭，文案写明不发送。重启同一 SQLite 后两条已关闭轮次期限仍为 30 / 45 天，来源不变。征求意见审计恰好 6 条（open/reply/close 各两次；打开记录分别为「默认 30 天」「标记商定 45 天」），哈希链有效，重开不再写入。

### 截图（通过那次 `--out`）
- 默认 30 天核对：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/screenshots/01-default-30-preview.png
- 第 1 轮已关闭：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/screenshots/02-default-30-closed.png
- 已商定 45 天核对：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/screenshots/03-declared-45-preview.png
- 第 2 轮已关闭：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/screenshots/04-declared-45-closed.png
- 重启后第 1 轮已关闭：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/screenshots/05-reopen-round1-default30.png
- 重启后第 2 轮已关闭：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/screenshots/06-reopen-round2-declared45.png

### 未验
未改工装的 `1f329c3` 原脚本真浏览器路径未跑完（首个阻塞见上）。旧正文编辑、发送、证据节点（本轮范围外）。Firefox / WebKit；headed；触屏；真实模型或真实案卷；远程 CI。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w7-deadline-grokbot-1f329c3/w7-deadline
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/REPORT.md
- 工装候选：https://github.com/mark2wen2023/MCIS/tree/candidate/w7-deadline-chromium-grokbot-1f329c3
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w7-deadline-grokbot-1f329c3/w7-deadline/mcis-w7-deadline-report.tar.gz
- SHA-256：`4da676261b69494396fc338a83f0e14cbf73f4f0209aa54b10b52c31f7bf7892`

没有修改产品，没有合并，没有部署，也没有触发远程 CI。未接真实模型或数据。

请 Dot 在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
