W17：服务（同一 29cbfe2 工作树的后端）通过；真浏览器通过

# MCIS W17 Chromium 回执 29cbfe2

- 执行时间：2026-11-25 11:37–11:46（北京时间，UTC+8）。执行环境是 Grok Bot 的 Linux 盒子，uid 1000。
- 本回执取代 #106 里基于 3ae5166 的 W17 结果。
- 数据全部合成。服务只监听 127.0.0.1。没改产品，没触发 CI，没合并，没部署，没碰三维仓库。

## 1. 版本
| 项 | 值 |
|---|---|
| 工作树 | `/workspace/mcis-w17-chr-29cbfe2`（独立 worktree；先用令牌请求头 fetch，成功） |
| HEAD | `29cbfe255967fc6814abafd919ed9a7485ef8710`（2026-11-24 09:27 +0800，"fix(w17): require explicit evidence selection after case switch"） |
| `git status --porcelain` | 运行前为空。运行中 README 指定的 `.evidence-page-browser-dist/` 是未跟踪的构建产物，跑完已删除。候选分支的提交是在临时分支上做的，结束时已切回 detached 29cbfe2，状态为空 |
| W17 验收内容 | `web/tests/evidence-page-browser/`（README 标题就是「W17 EvidencePage browser gate (authored, browser NOT RUN)」，本次是首次真实运行）；`tests_acceptance/W171/`（旧 W17.1 工作台的真浏览器脚本）。这个 SHA 上没有 `w17-evidence-selection-receipt`（它在 a80226d 才加），也没有 `DEFECTS/W17*` |

## 2. 工具
Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。
Node 用的 Playwright 是 W4 那个 pnpm 路径 `/usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright`。仓库的两个 .py 浏览器脚本要 Python 版 Playwright，用的是仓库外 venv `/workspace/w17-pyplaywright-venv`（playwright 1.65.2）。
Node v24.22.1；web 下 `npm ci`（Vite 8.3.8、React 19.3.1）；service/.venv（Python 3.13.5）。
沙箱：所有浏览器启动都是 `chromiumSandbox/chromium_sandbox=True`。实测进程参数里没有 `--no-sandbox` / `--disable-setuid-sandbox`，有 3 个渲染进程，Seccomp=2，NoNewPrivs=1。

## 3. 命令与退出码（工作树根目录）
| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 1 | `./web/node_modules/.bin/vite build --config web/tests/evidence-page-browser/vite.config.ts` | 0 | 夹具构建 |
| 2 | `python -m py_compile web/tests/evidence-page-browser/check.py`；`node web/tests/evidence-page-browser/predicates.test.cjs`；`node web/tests/evidence-page-browser/request-policy.test.mjs` | 0/0/0 | 13 条谓词、37 条端点白名单离线检查通过（未启动浏览器） |
| 3 | `/workspace/w17-pyplaywright-venv/bin/python -B web/tests/evidence-page-browser/check.py --chromium /opt/google/chrome/google-chrome --dist "$PWD/.evidence-page-browser-dist" --output /workspace/mcis-w17-chr-report/receipt-evidence-page-browser` | **0** | `PASS EvidencePage synthetic Chromium lifecycle`；receipt.json：`passed=true`、`externalRequests=0`、`browserVersion=156.0.8078.47`、12/12 项检查通过 |
| 4 | `<报告>/tooling/run_e2e.sh 1440x900 vp1440`；`… 390x844 vp390`（后端 uvicorn :18773 和 Vite :18774 都来自 29cbfe2 工作树） | **0 / 0** | 真实后端端到端，两种视口全部通过 |
| 5 | 候选分支上：`W171_SHOTS=<报告>/screenshots/w171 MCIS_BROWSER_BIN=/opt/google/chrome/google-chrome /workspace/w17-pyplaywright-venv/bin/python -B tests_acceptance/W171/browser_real.py` | **0** | `PASS real browser/API: …` |

## 4. 分项结果

### 4.1 真实 Chromium + 真实后端（29cbfe2 的 uvicorn + Vite 代理）：通过
自写驱动 `tooling/e2e_driver.cjs`，没有 page.route，没有 fetch 替身。「迟到响应」是后端测试包装层在真实处理完成后把响应推迟 3–4 秒再发。种数据走真实 intake preview/commit HTTP，SYN-A / SYN-B 都是 EV-001。
| 项 | 1440×900 | 390×844 |
|---|---|---|
| 进入 SYN-A：列表显示 SOURCE-SYN-A，保管链显示「请选择证据」，没有发出 custody 请求 | 通过 | 通过 |
| 显式点选 → custody 200 →「保管链 · EV-001」 | 通过 | 通过 |
| 切案 B→A→B，前两次列表响应都推迟 4 秒（实际都以 200 送达）：A 列表等待期间旧 A 已清空；当前 B 显示 SOURCE-SYN-B 和「请选择证据」，没有自动选中，没有替 B 发 custody 请求；迟到的 A/B 列表送达后没有回填 SOURCE-SYN-A | 通过 | 通过 |
| 点选 B → 打开登记面板（此时不发 intake 请求）→ 读回执 200：回执里有 SYN-B.txt、登记的 sourceSha256 和 requestDigest，没有 SYN-A | 通过 | 通过 |
| 旧回执：在 A 发起读回执（服务端推迟 3 秒）后立刻切到 B → 页面**主动中止**了这个请求（net::ERR_ABORTED），等满延迟后也没有回执、没有 SYN-A.txt | 通过 | 通过 |
| 切换身份为 Public：列表 403，页面上没有 SOURCE-SYN-B | 通过 | 通过 |
| 已选中 B 后，服务端把 SYN-B 的 LeadInvestigator 权限改成 Deny，再读回执 → 403，显示 alert，没有回执 | 通过 | 通过 |
| 全程只有 GET（0 个写请求）；没有 download / content / :commit / :preview 请求；没有外部请求；没有 pageerror | 通过 | 通过 |
| SQLite 直查：custody 只有 2 行 Register，没有 Access；audit 2 行 | 通过 | 通过 |
说明：旧回执那一项里，产品是用中止请求来防迟到数据，浏览器根本没收到这个迟到的回执响应，所以「迟到的回执真的送到浏览器后被丢弃」这条路径在真浏览器里没有发生（未验）。迟到的**列表**响应确实送到了浏览器，验证的是丢弃路径。

### 4.2 真实 Chromium + 合成 API（仓库门禁 evidence-page-browser，没有后端）：通过
README 写明：这里的 fetch 由夹具控制，只返回手工构造的合成列表或 403，静态资源通过拦截 `https://mcis-synthetic.invalid` 提供。所以它是**真浏览器、假后端**，不能当作端到端验收。
- 1440 和 390 两种宽度下，late=data/deny 各 1 项、conflicts=deny/empty/empty/data 各 1 项，一共 12 项全部通过。
- 外部请求 0，`gate.unexpected()` 为空。截图见 `receipt-evidence-page-browser/`（empty-*、conflicts-*）。

### 4.3 W17.1 工作台真浏览器（tests_acceptance/W171/browser_real.py，真实 FastAPI + Vite，都来自 29cbfe2 工作树）：通过
原脚本写死了 `args=['--no-sandbox']`，按规定**没有原样运行**。在候选分支上改了这个 W17 验收目录里的文件后才运行（见第 5 节）。
覆盖的内容：只读配置；不回退旧 `/access-policy` 接口；刷新时清空；旧案和旧身份的迟到响应（用 `route.fetch()` 拿到真实后端响应后推迟送达）不会恢复数据；Public 被拒绝；没有页面错误。截图在 `screenshots/w171/`。

### 4.4 模拟 DOM
本回执没有使用。Happy DOM 的结果在服务回执 a80226d 里。

### 4.5 未验
- 迟到回执真的送到浏览器后被丢弃（见 4.1 说明）。
- 外部角色（ExternalExpert 等）在 UI 上的表现。服务回执发现 custody 端点会向外部角色暴露 Restricted 元数据；在 UI 上，它们的列表为空，点不到行，所以没测。
- 真实触屏（390 宽度只设了视口）；Firefox / WebKit；有界面（headed）窗口；原件下载和 Access 写入。
- web/tests 下其他写死 `--no-sandbox` 的 browser.py（不属于 W17 验收目录，没改也没跑）。

## 5. 候选分支（只改 W17 验收目录里的测试工具）
`candidate/w17-chr-sandbox-grokbot-29cbfe2`，提交 `55bb0a8aace8dc4116099c73a00c1df163cae153`，父提交是 29cbfe2，已推送。
只改了 `tests_acceptance/W171/browser_real.py`（+7/−1）：`args=['--no-sandbox']` 换成 `chromium_sandbox=True`；另外加了一个可选截图函数 `shot()`（由环境变量 `W171_SHOTS` 控制），在 3 个断言点之后截图。原有断言一条没改。完整 diff 见 logs/06-candidate.diff。

## 6. 首个错误
没有产品或验收层面的错误。我自己的驱动调试时有过 3 次失败，都已定位修正，原始日志被重跑覆盖：
1. 用文字出现来判断 custody 是否返回不可靠：面板标题先于响应出现，改成等待 waitForResponse。
2. 上一次运行的后端子进程没退出，占着 18773 端口，导致新后端没就绪：改成 exec 启动并清理残留进程。
3. 旧回执请求被页面中止，所以永远等不到 response 事件：改成同时监听 requestfinished 和 requestfailed。

## 7. 文件
- `logs/`：00 环境；01 夹具构建；02 离线谓词和白名单；03 仓库门禁；05 端到端（每个视口的 JSON、后端日志、Vite 日志、监听端口）；06 候选分支 SHA、diff、W171 日志。
- `screenshots/`：vp1440-*、vp390-*（真实后端端到端，各 7 张）；`w171/`（3 张）。
- `receipt-evidence-page-browser/`：仓库门禁的 receipt.json 和 4 张截图。
- `tooling/`：e2e_server.py、e2e_driver.cjs、run_e2e.sh，都在仓库外。
