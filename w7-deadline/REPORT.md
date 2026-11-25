W7 期限：真浏览器通过（产品固定 b2ecb50；验收候选 1f329c3 原脚本在临时 Vite 缺 contracts/ 处阻塞；工装候选 0092734 修复后退出码 0）

# MCIS W7 默认/已商定期限真浏览器验收

- 执行时间：2026-11-25 21:26–21:35（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 产品固定：`b2ecb50b32b721c9f171b74ecd576691c0048b94`（2026-11-25 20:41:08 +0800，“Keep default consultation deadlines distinct from declared agreements”）。`RoundLifecycle.tsx`、`RecommendationsPage.tsx`、`recommendations/router.py` 的 Git blob 哈希与脚本钉扎一致。
- 派发的验收候选：`1f329c36423456cc11446e0987daf4381e3cfee4`（相对产品仅新增 `tests_acceptance/w7-deadline-chromium/{README.md,browser.cjs,run.py}`）。
- 本轮工装候选（只改验收文件，未改产品）：`0092734837f652a813be41eb65148a3ce57982a7`，分支 `candidate/w7-deadline-chromium-grokbot-1f329c3`。相对产品仍只有上述三份验收文件。
- 独立工作树 `/workspace/mcis-w7-deadline-1f329c3`。产品树未改。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromiumSandbox:true` 启动，没有 `--no-sandbox`。现成 Node Playwright 1.63.0-alpha-2026-08-31（支持 `routeWebSocket`），未新装依赖。
- 同工作树 Vite + FastAPI，仅监听 127.0.0.1；临时 SQLite，`MCIS_SEED_DEMO=0`。页面流量限制在 Vite 回环源。不接真实模型、真实案卷、旧正文编辑、发送或证据节点。未跑、也未把 HTTP-only 写成真浏览器通过。
- 未改产品，未合并，未部署，未触发远程 CI。

## 1. 命令与退出码

按 README，先用现成 Node Playwright 跑派发的 `1f329c3` 脚本（不用 `--http-only`）：

```sh
python3 -B tests_acceptance/w7-deadline-chromium/run.py \
  --web <worktree>/web --service <worktree>/service \
  --service-python <existing service .venv>/bin/python \
  --browser /opt/google/chrome/google-chrome \
  --playwright <existing playwright/index.mjs>
```

`1f329c3` 原脚本退出码 **1**。临时 Vite 副本只复制了 `web/` 内文件，没有产品根目录的 `contracts/`，页面在 `reportOutput/model.ts` 无法解析 `report.schema.json`，`select.role-select` 超时。这是原验收脚本的首个阻塞，不是产品逻辑失败，也不是缺少沙箱或 Playwright。日志：`logs/01-check.*`。

随后只改验收文件并重跑同一产品流程（加 `--out`）。工装要点：

- 在临时目录把现成产品 `contracts/` 只读链接到 Vite 副本旁，供已钉扎的 schema 引用解析。
- FastAPI/SQLite 重启后，对已打开的建议页执行 `reload`（同哈希 `goto` 不会整页刷新）。
- 若角色已是 LeadInvestigator，不再次 `selectOption`：对同一角色再触发 identity 监听会取消进行中的轮次读取且不重新挂载，面板会停在「正在读取轮次与权限…」。
- 可选 `--out` 截图；临时 Vite 代理关闭 keep-alive，避免重启后持有旧套接字。

工装候选 `0092734` 官方路径退出码 **0**，打印：

`W7 sandboxed Chromium PASS: two registered/closed rounds, default30 vs declared45, reopened UI and real audit.`

日志：`logs/09-check-official.*`。

## 2. 通过的产品流程（0092734 工装，真 Chrome，产品 b2ecb50）

同一纯合成案 `SYN-W7-CHROMIUM-DEADLINE`：

- 默认 30 天：核对新建时可见「默认期限：服务登记时间起 30 天」，确认前无写入，线上 payload 无 `days` 字段；登记回复「仅登记合成答复，不发送。」后关闭。
- 已商定 45 天：勾选「登记已商定期限」并填 45；核对文案为「申报已商定期限：服务登记时间起 45 天（系统不核验是否已经商定）」；确认前无写入；payload 含 `days: 45`。
- 两轮文案均写明不会向相关方发送消息。
- 重启同一临时 SQLite 后，按轮次读回两条已关闭轮次（`SYN-DEADLINE-1` / `SYN-DEADLINE-2`），期限间隔仍为 30 与 45 天，默认/已商定来源不变。
- 征求意见审计恰好 6 条：`consultation.open` / `reply` / `close` 各两次；打开记录分别含「默认 30 天」「标记商定 45 天」；哈希链有效。重开不再写入。

## 3. 截图

来自通过的那次官方脚本 `--out`（真页面，非接口模拟、非 HTTP-only）：

- `screenshots/01-default-30-preview.png`：默认 30 天核对，确认前无发送
- `screenshots/02-default-30-closed.png`：第 1 轮 `SYN-DEADLINE-1` 已关闭，已登记合成答复
- `screenshots/03-declared-45-preview.png`：已商定 45 天核对，系统不核验是否已经商定
- `screenshots/04-declared-45-closed.png`：第 2 轮 `SYN-DEADLINE-2` 已关闭
- `screenshots/05-reopen-round1-default30.png`：重启后读回第 1 轮已关闭
- `screenshots/06-reopen-round2-declared45.png`：重启后读回第 2 轮已关闭

`diagnostics/diag-enter-failed.*` 为修复前重启后面板停在「正在读取」的诊断材料，不是验收通过条件。

## 4. 未验

- 未改工装的 `1f329c3` 原脚本：真浏览器路径未跑完（首个阻塞见上）。不能把它或 HTTP-only 算作真浏览器通过。
- 旧正文编辑、发送、证据节点（本轮范围外）。
- Firefox / WebKit；headed；触屏；真实模型或真实案卷；远程 CI。

## 5. 文件

`logs/00-env.txt`、原脚本失败与修复后通过日志；`screenshots/`；`diagnostics/`。
