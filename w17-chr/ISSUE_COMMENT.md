【Grokbot｜W17｜待复核】Chromium 回执 29cbfe2

**W17：服务（同一 29cbfe2 工作树的后端）通过；真浏览器通过**

本回执和服务回执 a80226d 一起，**取代本帖前面基于 3ae5166 的 W17 结果**。

### 版本
- `29cbfe255967fc6814abafd919ed9a7485ef8710`，独立工作树 `/workspace/mcis-w17-chr-29cbfe2`，先 fetch 再检出。
- 运行前后 `git status --porcelain` 都为空：README 指定的构建产物 dist 已删除；候选分支提交完后已切回 detached 29cbfe2。
- 这个 SHA 上的 W17 浏览器门禁是 `web/tests/evidence-page-browser/`，README 原写着「browser NOT RUN」，本次是首次真实运行。另有 `tests_acceptance/W171/`。

### 工具
- Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。
- Node 版 Playwright：W4 用的那个 pnpm 路径（1.63.0-alpha）。
- Python 版 Playwright 1.65.2：装在仓库外的 venv，给仓库的 .py 脚本用。
- Vite 8.3.8，Node v24.22.1，Python 3.13.5。
- 沙箱正常：没有用 `--no-sandbox`，渲染进程 Seccomp=2、NoNewPrivs=1。

### 命令与退出码
| 命令 | 退出码 |
|---|---|
| `./web/node_modules/.bin/vite build --config web/tests/evidence-page-browser/vite.config.ts`；离线谓词 13 条、端点白名单 37 条 | 0 |
| `python web/tests/evidence-page-browser/check.py --chromium /opt/google/chrome/google-chrome --dist $PWD/.evidence-page-browser-dist --output <新目录>` | 0（receipt：passed=true，externalRequests=0，12/12） |
| 真实后端端到端 `tooling/run_e2e.sh 1440x900` 和 `390x844`（uvicorn 与 Vite 都来自 29cbfe2 工作树，127.0.0.1:18773/18774） | 0 / 0 |
| 候选分支 `MCIS_BROWSER_BIN=/opt/google/chrome/google-chrome python tests_acceptance/W171/browser_real.py` | 0 |
| 仓库原版 W171 browser_real.py | 未跑：写死了 `--no-sandbox` |

### 分项结果
**真实浏览器 + 真实后端（自写驱动，没有 route 或 fetch 替身；迟到响应由后端在真实处理之后延迟送出）**：两种视口全部通过。
- 进入 SYN-A 时只显示列表和「请选择证据」，不发 custody 请求；显式点选后 custody 返回 200。
- B→A→B 切案时把列表响应推迟 4 秒，迟到的 200 送达后没有回填 SOURCE-SYN-A；B 没有自动选中，也没有替 B 发 custody 请求。
- 读回执显示 SYN-B.txt，SHA 和摘要都与登记一致。
- 在 A 读回执时立刻切到 B，页面主动中止了旧请求（ERR_ABORTED），没有显示回执。
- 切到 Public 后列表 403，看不到 B 的元数据；撤销 SYN-B 权限后读回执得到 403，页面显示 alert。
- 全程只有 GET，没有下载、commit、preview 请求，也没有外部请求；SQLite 里只有 2 条 Register，没有 Access。

**真实浏览器 + 合成 API（仓库门禁 evidence-page-browser，没有后端，fetch 由夹具控制）**：通过。1440 和 390 两种宽度下，late=data/deny 和 conflicts=deny/empty/empty/data 共 12 项都通过，外部请求为 0。

**W17.1 工作台真浏览器（真实 FastAPI + Vite，都来自 29cbfe2）**：通过。只读；不回退旧接口；旧案和旧身份的迟到响应都没有恢复数据；Public 被拒绝；没有页面错误。

**模拟 DOM**：本回执没有用，Happy DOM 的结果在服务回执 a80226d 里。

### 首个错误
没有产品或验收层面的错误。我自写驱动调试时失败过 3 次，都已修正，原因写在 REPORT 第 6 节。

### 未验
- 迟到的回执真的送到浏览器后被丢弃：产品是直接中止请求，所以这条路径没发生。
- 外部角色在 UI 上的表现：服务回执发现 custody 端点会泄露，但外部角色在 UI 上列表为空，点不到行。
- 真实触屏，Firefox 和 WebKit，有界面（headed）窗口，原件下载。

### 测试工具改动（只改 W17 验收目录）
- 候选分支：https://github.com/mark2wen2023/MCIS/tree/candidate/w17-chr-sandbox-grokbot-29cbfe2（提交 `55bb0a8aace8dc4116099c73a00c1df163cae153`，父提交 29cbfe2）
- `tests_acceptance/W171/browser_real.py` +7/−1：去掉 `--no-sandbox`，改用 `chromium_sandbox=True`；另加可选截图 `W171_SHOTS`，断言没有改。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-chr-grokbot-29cbfe2/w17-chr
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-chr-grokbot-29cbfe2/w17-chr/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-chr-grokbot-29cbfe2/w17-chr/mcis-w17-chr-report.tar.gz
- SHA-256：`1ce11e8c2470a04765f135a7d0c52dc9bc5bc4b4cd2452aa320e2cb54a96eb2b`
- 截图：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-chr-grokbot-29cbfe2/w17-chr/screenshots

没有修改产品，没有触发 CI，没有合并，也没有部署。

@Dot 请在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
