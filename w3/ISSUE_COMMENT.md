【Grokbot｜W3 草稿冲突｜待复核】

**W3 草稿冲突：真浏览器通过（固定验收 6a231db 官方脚本 --build-only 与浏览器运行均为退出码 0；192 针与产品底版 bd02094 一致；未改工装、未改产品）**

— Grokbot

### 版本
- 固定验收：`6a231db3ad4821e450af869def15f39ba95803ea`（相对产品仅四份验收文件）。本轮按该提交原脚本跑通，没有再改验收文件。
- 产品底版：`bd02094a7cbb95d9ebb24a33e51bab2e695cccd7`。192 个固定源与验收工作树文件、以及底版 Git blob 逐一对照，全部一致。产品未改。

### 浏览器与退出码
- Google Chrome **156.0.8078.47**（`/opt/google/chrome/google-chrome`，`chromiumSandbox:true`，没有 `--no-sandbox`）。现成 Node Playwright 1.63.0-alpha-2026-08-31（未新装包）。
- `run.cjs --build-only` 退出码 **0**（192 pins，bundle 1,281,976 字节）。
- `run.cjs` 真浏览器退出码 **0**。`exit.json`：`pass: true`，阶段 complete，`cleanupErrors: []`。未把 HTTP-only 或 DOM 模拟算作真浏览器通过。

静态页与试验宿主只监听 127.0.0.1，临时 SQLite，页面请求限制在本源。

### 流程断言（真页面，1440 操作 / 390 读回）
合成双卡 `CASE-TRIAL-FICTIONAL`：卡甲真实版本冲突（409 / `ISSUE_HOST_REJECTED`）后保留未交草稿「合成保留稿甲：仍针对原判断」，须重读并重选当前来源 EV-001 后方可写入。卡乙判断从 #1 变为 #2 后，草稿「合成保留稿乙：不重新绑定」仍在但禁止提交，提示「原草稿针对判断 #1；当前判断 #2」，变更判断不能直接复用。重开同一临时 SQLite 后，390 窗口读回卡甲版本 3（历史含稿甲与 EV-001）、卡乙版本 2（「并行添加新的判断」，不含甲/乙未交草稿）。两张卡相互独立。无跨源请求。

### 截图
- 确定冲突、未交草稿保留：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w3-conflict-grokbot-6a231db/w3/screenshots/01-definite-conflict.png
- 判断已变、不能直接复用：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w3-conflict-grokbot-6a231db/w3/screenshots/02-no-rebind.png
- 390 重开卡甲（版本 3）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w3-conflict-grokbot-6a231db/w3/screenshots/03-card-a-reopened.png
- 390 重开卡乙（版本 2，独立）：https://raw.githubusercontent.com/mark2wen2023/MCIS/evidence/w3-conflict-grokbot-6a231db/w3/screenshots/04-card-b-reopened.png

### 未验
Firefox / WebKit；headed；完整响应式签收；生产登录或挂载；真实模型或真实案卷；远程 CI。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w3-conflict-grokbot-6a231db/w3
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w3-conflict-grokbot-6a231db/w3/REPORT.md
- 脱敏回执：https://github.com/mark2wen2023/MCIS/blob/evidence/w3-conflict-grokbot-6a231db/w3/logs/02-browser-exit.json
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w3-conflict-grokbot-6a231db/w3/mcis-w3-report.zip
- SHA-256：`425b3ea15aa707162ca25738ff14eb4d9022d8f48b896a5d9897177354c69bc6`

没有修改产品，没有合并，没有部署，也没有触发远程 CI。未接真实模型或数据。

请 Dot 在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
