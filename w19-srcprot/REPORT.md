W19 来源变更：真浏览器通过（产品固定 b3b8ae3；验收候选 8183226 官方脚本退出码 0，未改工装）

# MCIS W19 新版来源变更保护真浏览器验收

- 执行时间：2026-11-25 22:17–22:18（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 产品固定：`b3b8ae36e7eaeac759eecb7f136ca46e77dc6571`（2026-11-25 21:19:57 +0800，“Invalidate copied knowledge templates when their source context changes”）。`KnowledgePage.tsx` / `knowledge/api.ts` 的 Git blob 哈希与脚本钉扎一致。
- 派发的验收候选：`8183226c579af6ddcdcfef2078c68fdacf1885d2`（相对产品仅新增 `tests_acceptance/w19-chromium/{README.md,check.py}`）。本轮按该提交原脚本跑通，未再改验收文件，也未改产品。
- 独立工作树 `/workspace/mcis-w19-srcprot-8183226`。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromium_sandbox=True` 启动，没有 `--no-sandbox`。现成 Python Playwright 1.65.2（支持 `route_web_socket`），未新装依赖。
- 同工作树 Vite + FastAPI，仅监听 127.0.0.1；临时 SQLite，`MCIS_SEED_DEMO=0`，`MCIS_KNOWLEDGE_SUGGESTION_PROVIDER=template-stub-v1`。页面流量限制在 Vite 回环源，拦截 Service Worker，断言无跨源请求。不接真实模型或真实案卷。未跑、也未把 `--http-only` 写成真浏览器通过。
- 未改产品，未合并，未部署，未触发远程 CI。

## 1. 命令与退出码

按 README 用现成 Python Playwright 跑派发的 `8183226` 脚本（不用 `--http-only`）：

```sh
/workspace/w17-pyplaywright-venv/bin/python -u -B tests_acceptance/w19-chromium/check.py \
  --web <worktree>/web --service <worktree>/service \
  --service-python <existing service .venv>/bin/python \
  --browser /opt/google/chrome/google-chrome \
  --out <screenshots>
```

退出码 **0**。打印：

`Sandboxed Chromium + Vite + FastAPI/SQLite PASS (W19 template source drift blocked → single synthetic internal candidate → explicit review → service reopen → withdrawn / Public denied)`

日志：`logs/01-check.*`。

## 2. 通过的产品流程（8183226 原工装，真 Chrome，产品 b3b8ae3）

合成卡「W19 真浏览器专用合成卡」：

- 套用旧摘录「旧合成摘录，只用于模板对照。」的模板预览后，将来源摘录改为新文字，出现「原模板填入内容不能直接保存」警告，正文仍为旧摘录，保存按钮禁用；恢复旧摘录后保存仍禁用。此阶段无卡片 POST、无记录、无审计，仅一次 suggestions 预览。
- 按当前获准来源重新预览/套用后，只创建一条内部待审候选；公众列表与直链 404。
- 三项人工勾选后「批准发布到公开资料库」才可点；审核理由「合成核验：明确批准该虚构资料。」
- 重启同一临时 SQLite 后，按编号读回「已人工批准发布」；来源「W19 真浏览器专用合成卡 · 合成段落第 8 段」、摘要与 digest、审核说明不变。
- 从列表控件撤回后，按编号读回「已撤回」；公众列表与详情仍读不到（发布前、撤回后均为 0 条）。
- 审计恰好 3 条：`knowledge.create`、`knowledge.published`、`knowledge.withdrawn`，`audit:verify` 为 `{valid:true,count:3}`；无跨源请求。

## 3. 截图

来自通过的那次官方脚本 `--out`（真页面，非接口模拟、非 HTTP-only）：

- `screenshots/01-template-stale-after-restoring-old-source.png`：恢复旧来源后仍禁止保存
- `screenshots/02-saved-candidate.png`：仅一条内部待审候选
- `screenshots/03-readback-candidate.png`：按编号读回「待人工审批」
- `screenshots/04-public-denied-before-publish.png`：发布前公众看不到
- `screenshots/05-three-checks-ready.png`：三项勾选，可批准发布
- `screenshots/06-published.png`：已发布
- `screenshots/07-reopen-after-restart.png`：重启后按编号读回「已人工批准发布」，来源与摘要仍在
- `screenshots/08-withdrawn.png`：已撤回
- `screenshots/09-reopen-withdrawn.png`：按编号读回「已撤回」
- `screenshots/10-public-denied-after-withdraw.png`：撤回后公众仍读不到

## 4. 未验

Firefox / WebKit；headed；触屏；真实模型或真实案卷；远程 CI。未跑 `--http-only`，也不把它算作真浏览器通过。

## 5. 文件

`logs/00-env.txt`、官方通过日志；`screenshots/`。
