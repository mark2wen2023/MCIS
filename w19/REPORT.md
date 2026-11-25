W19：真浏览器通过（产品固定 d0c4d8c；工具候选 9c878b1 原脚本在 get_by_label「标题」处阻塞；验收工装候选 9d7d843 修复选择器后退出码 0）

# MCIS W19 知识卡真浏览器验收

- 执行时间：2026-11-25 20:50–20:58（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 产品固定：`d0c4d8c2a6f2aaeee5e49b2085d4f744a491d642`（2026-11-25 20:17:45 +0800，“Reopen saved knowledge cards by exact ID from the internal workspace”）。`KnowledgePage.tsx` / `knowledge/api.ts` 的 Git blob 哈希与脚本钉扎一致。
- 派发的工具候选：`9c878b1ad055deea52ba8c0fb46ef7c3e05017fa`（相对产品仅新增 `tests_acceptance/w19-chromium/{README.md,check.py}`）。
- 验收工装候选（本轮为跑通选择器而推送，未改产品）：`9d7d84326d050f004b633fd80f27a38297d7b135`，分支 `candidate/w19-chromium-label-fix-grokbot-9c878b1`。相对产品仍只有上述两份验收文件。
- 独立工作树 `/workspace/mcis-w19-9c878b1`。产品树未改。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromium_sandbox=True` 启动，没有 `--no-sandbox`。Python Playwright 1.65.2（已支持 `route_web_socket`）。
- 同工作树 Vite + FastAPI，仅监听 127.0.0.1；临时 SQLite，`MCIS_SEED_DEMO=0`。页面流量限制在 Vite 回环源，拦截 Service Worker，断言无跨源请求。不接真实模型或真实案卷。未跑、也未把 `--http-only` 写成真浏览器通过。
- 未改产品，未合并，未部署，未启用远程 CI。

## 1. 命令与退出码

按 README，先用现成 Python Playwright 跑派发的 `9c878b1` 脚本（不用 `--http-only`）：

```sh
/workspace/w17-pyplaywright-venv/bin/python tests_acceptance/w19-chromium/check.py \
  --web <worktree>/web --service <worktree>/service \
  --service-python <existing service .venv>/bin/python \
  --browser /opt/google/chrome/google-chrome
```

`9c878b1` 原脚本退出码 **1**。沙箱 Chrome 已启动并打开知识页、展开「人工创建候选」并点击「填入合成示例」，但 `get_by_label("标题", exact=True)` 等待 12s 超时。原因：填入示例后，`<label>标题<textarea>…</textarea></label>` 的无障碍名会带上文本框现有内容，精确标签「标题」匹配不到。复试一次（Vite 已预热）同一阻塞。日志：`logs/01-check.*`、`logs/02-check-retry.*`。这是原工具候选的首个阻塞，不是产品失败，也不是缺少 Playwright/沙箱。

随后只改验收文件（选择器改为按 label 的第一个文本节点定位 textarea，并增加可选 `--out` 截图），在 `9d7d843` 上重跑同一命令并加上 `--out <screenshots>`。退出码 **0**，打印：

`Sandboxed Chromium + Vite + FastAPI/SQLite PASS (W19 synthetic internal candidate → explicit review → service reopen → withdrawn / Public denied)`

日志：`logs/04-check-xpath.*`。

## 2. 通过的产品流程（9d7d843 工装，真 Chrome，产品 d0c4d8c）

同案纯合成卡「W19 真浏览器专用合成卡」：

- 内部首席身份新建待审；公众列表/直链 404。
- 三项人工勾选后「批准发布到公开资料库」才可点；审核理由「合成核验：明确批准该虚构资料。」
- 重启同一临时 SQLite 后，按编号读回「已人工批准发布」；摘录、定位「合成段落第 8 段」、digest、审核说明不变。
- 从列表控件撤回后，按编号读回「已撤回」；公众列表与详情仍读不到。
- 审计 3 条：`knowledge.create`、`knowledge.published`、`knowledge.withdrawn`，`audit:verify` 为 `{valid:true,count:3}`；仅这三次写入；无跨源请求。

## 3. 截图

来自通过的那次官方脚本 `--out`（真页面，非接口模拟）：

- `screenshots/01-create-form-filled.png`：已填合成标题、摘录与定位
- `screenshots/02-saved-candidate.png`：内部待审卡
- `screenshots/03-readback-candidate.png`：按编号读回「待人工审批」
- `screenshots/04-public-denied-before-publish.png`：公众看不到
- `screenshots/05-three-checks-ready.png`：三项勾选，可批准发布
- `screenshots/06-published.png`：已发布
- `screenshots/07-reopen-after-restart.png`：重启后按编号读回「已人工批准发布」，出处仍在
- `screenshots/08-withdrawn.png`：已撤回
- `screenshots/09-reopen-withdrawn.png`：按编号读回「已撤回」
- `screenshots/10-public-denied-after-withdraw.png`：撤回后公众仍读不到

`screenshots/probe/` 为定位原选择器阻塞时的诊断截图，不是验收通过条件。

## 4. 未验

- 未改工装的 `9c878b1` 原脚本：真浏览器路径未跑完（首个阻塞见上）。不能把它或 `--http-only` 算作真浏览器通过。
- Firefox / WebKit；headed；触屏；真实模型或真实案卷；远程 CI。

## 5. 文件

`logs/00-env.txt`、原脚本失败与修复后通过日志；`tooling/probe_form.py`；`screenshots/`。
