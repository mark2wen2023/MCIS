W4：服务通过；真浏览器通过

# MCIS W4 合成 PDF 预览验收报告

- 执行时间：2026-11-25 11:20–11:30（北京时间，UTC+8）；执行机：Grok Bot 的 Linux 盒子（uid 1000，非 root）
- 数据：仅测试脚本生成的合成 PDF（SHA256 `92cf698d3070092139444f94b7dacb7286f774b6186503917e534b253734e774`，2 页 72×72pt）。未用真实案卷、未用密钥。服务只绑 `127.0.0.1`（随机端口）。
- 未改产品代码、未触发远程 CI、未部署、未合并、未推任何分支（无候选分支：只读复验，测试工具无需修改）。

## 1. 固定版本

| 项 | 值 |
|---|---|
| 工作树 | `/workspace/mcis-w4-3ae5166`（`git worktree add --detach`，未用 main） |
| `git rev-parse HEAD` | `3ae5166b7522f63bf39827a02341c856e394a0c9`（提交时间 2026-11-25 07:05 +0800，"Pin synthetic W4 live HTTP and browser acceptance entry"） |
| `git status --porcelain` | 空（干净；全部运行结束后复查仍为 0 行。`service/.venv` 被 .gitignore 忽略） |
| 固定产品提交（pins.json） | `67654fd9801735dfe81361caf5e6f0148ab5e7da`，是 HEAD 的祖先；run.py 启动时核对 180 个 blob，全部一致（不一致会直接退出） |
| 获取方式 | `git -c http.extraHeader=<token header> fetch origin` 成功（令牌未打印、未写入任何文件） |

## 2. 工具版本与路径

| 工具 | 版本 / 路径 |
|---|---|
| Python | 3.13.5，`service/.venv` 按 `service/requirements.txt` 新建（fastapi 0.165.0、uvicorn 0.54.0、SQLAlchemy 2.1.9、pydantic 2.14.4、pillow 13.0.0、reportlab 5.1.1；完整见 logs/00-env.txt） |
| Poppler | pdfinfo / pdftoppm 25.03.0（`/usr/bin`） |
| Node | v24.22.1（`/usr/local/bin/node`） |
| Playwright | 1.63.0-alpha-2026-08-31，`/usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright` |
| Chromium | Google Chrome 156.0.8078.47，`/opt/google/chrome/google-chrome`（`/usr/bin/google-chrome` 的实际目标）。本机**没有** `/usr/bin/chromium` |
| 沙箱 | `chromiumSandbox:true`，进程参数中无 `--no-sandbox`/`--disable-setuid-sandbox`；存在 zygote；渲染进程 `Seccomp: 2`（seccomp-bpf 生效）、`NoNewPrivs: 1` |

## 3. 执行命令与退出码（仓库根 `/workspace/mcis-w4-3ae5166`）

| # | 命令 | 退出码 | 输出 |
|---|---|---|---|
| 1 | `service/.venv/bin/python -I -B tests_acceptance/w4-synthetic-pdf-live/run.py --repo .` | **0** | `{"http":"passed","derivedAccessDelta":1,"registeredImageAccessDelta":1,"distinctPixels":true,"ocrReviewRowsUnchanged":true,"browser":"not_run"}` |
| 2 | `service/.venv/bin/python -I -B tests_acceptance/w4-synthetic-pdf-live/run.py --repo . --browser --playwright-module /usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright --chromium /opt/google/chrome/google-chrome` | **0** | `{"http":"passed","browser":{"passed":true,"sandbox":true,"realCanvasPixel":[255,0,0,255],"derivedRequests":1,"restoredPngRequests":1,"ocrWrites":0}}` |
| 2' | 同 2 再跑 3 次（稳定性） | 0 / 0 / 0 | logs/05-browser-repeat-*.stdout |
| 2'' | 同 2 但 `--chromium /usr/bin/chromium`（README 示例路径） | 2 | `browserExit:20, browserStage:"browser_launch"`：本机该路径不存在 → 属**依赖路径**问题，不是沙箱/页面问题。README 里"Linux Chromium 在导航前启动失败"很可能同因，建议在那台机器先 `ls -l` 实际路径 |
| 3 | `service/.venv/bin/python -I -B /workspace/mcis-w4-report/harness/harness.py --repo . --data /tmp/w4data-1440x900 --viewport 1440x900 --pw <同上> --chromium /opt/google/chrome/google-chrome --shots /workspace/mcis-w4-report/screenshots --tag vp1440` | **0** | logs/03-ext-1440x900.stdout |
| 4 | 同 3，`--viewport 390x844 --tag vp390 --data /tmp/w4data-390x844` | **0** | logs/03-ext-390x844.stdout |
| 5 | Poppler 独立检查：`pdfinfo synthetic.pdf`；`pdftoppm -f N -l N -r 72 -scale-to 256 -png synthetic.pdf pN -singlefile`（N=1,2） | 0 | logs/poppler/poppler-check.txt |

注：第一次扩展驱动（1440）在"蓝页重读"步骤超时，原因是**我的驱动**没先点「读取」——派生页显示时产品故意禁用「授权载入页图」，必须先主动重新读取（仓库 browser.cjs 也是这样做的）。修正驱动后重跑，上表为最终结果；首个错误原文保留在本报告附录。

## 4. 分项结果

### 4.1 仓库脚本覆盖项
| 项 | 结果 | 依据 |
|---|---|---|
| 固定产品 180 个 blob 核对 | 通过 | run.py 未报 mismatch |
| 真实进程 HTTP（health、证据登记 preview/commit、image-review 创建、/image-review-lab、pdf-host.js） | 通过 | 命令 1、2 退出 0 |
| 派生页响应只含 caseId/runId/revision/description/pngBase64，`Cache-Control: no-store`，不含 `%PDF-` 与登记摘要 | 通过 | 命令 1 |
| 红色第 1 页像素 (255,0,0)；登记 PNG 蓝色 (0,0,255)，二者不同 | 通过 | 命令 1（PIL）、命令 2（真实 canvas `getImageData`） |
| 两次受控读取各 1 条 Access，OCR 核对记录不变 | 通过 | 命令 1：Access (0→1→2)，Record 数恒为 1；命令 2：浏览器后 counts()==(2,1) |
| 真 Chromium：切案/切轮后旧回调（旧下载、旧保存按钮）不产生写请求 | 通过 | 命令 2 |
| 无外部请求、OCR 写入 0 | 通过 | 命令 2 |

### 4.2 独立补验（真实 Chromium，正常沙箱，无 page.route、无响应/画布模拟）
延迟方式：harness 在 ASGI 层包一层，真实处理（含审计写库）完成后再把**响应**推迟 3 秒发出；浏览器侧看到的是真实服务器字节。SQLite 计数由驱动在每步前后直接只读打开 `mcis.db` 查询 `custody_events`。

| 项 | 1440×900 | 390×844 | 说明 |
|---|---|---|---|
| 红色第 1 页确实画完 | 通过 | 通过 | 等 canvas 宽 256 且状态含「原PDF SHA256」后取像素：中心与 (5,5) 均 [255,0,0,255]；截图像素 (255,0,0) |
| 主动重新读取（点「读取」→「授权载入页图」）显示蓝色第 2 页 | 通过 | 通过 | canvas 中心 [0,0,255,255]，状态「页图已载入，字节摘要与登记匹配」；截图像素 (0,0,255) |
| A→B→A（复核轮次）：A 的派生页请求延迟中切到真实轮次 B；旧响应到达后不画 | 通过 | 通过 | 旧响应 200 到达后 canvas 1×1、状态「页图未显示」，截图为空白灰 (238,238,238)；随后读取 B 显示蓝；切回 A 再取派生页为红 |
| A→B→A（案件字段）：延迟中 case 改 OTHER-CASE 再改回 | 通过 | 通过 | 旧响应不画；重新读取后蓝页正常 |
| 延迟旧**蓝 PNG** 下载中切轮次 A→B→A，之后红页不被覆盖 | 通过 | 通过 | 旧 PNG 到达后不画；随后红页显示并在 1 秒后仍为红 |
| 派生页请求延迟中点「清除预览」 | 通过 | 通过 | 旧响应不画 |
| 外部请求 / OCR 核对写入 | 0 / 0 | 0 / 0 | |
| 截图在画布完成后截 | 通过 | 通过 | 先 waitForFunction 判定完成 + 2 帧 rAF 后截；logs/04-screenshot-pixels.json 为截图像素复核 |

### 4.3 Access 审计计数（SQLite 直查 `custody_events.kind='Access'`）
| 步骤 | PDF 证据 (EV-001) | 页图 PNG 证据 | 判定 |
|---|---|---|---|
| 红页派生读取 | +1 | 0 | 恰 1 条，通过 |
| 主动重读蓝页 | 0 | +1 | 恰 1 条，通过 |
| A→B→A（轮次，含 1 次被丢弃的延迟读取 + 1 次 B 蓝页 + 1 次回 A 红页） | +2 | +1 | 每次服务器实际读取各 1 条 |
| 案件 A→B→A（被丢弃的延迟读取 + 蓝页） | +1 | +1 | 同上 |
| 延迟旧 PNG（被丢弃的 PNG + 红页） | +1 | +1 | 同上 |
| 清除预览期间被丢弃的延迟读取 | +1 | 0 | 同上 |
| **每个视口合计** | **6** | **4** | 共 10 条，与浏览器实际发出的 10 个受控 POST 一一对应，无重复、无遗漏 |

观察（非失败）：被前端丢弃的迟到响应在服务端照样记了 Access——服务器确实读了原件，这样记是对的；只是审计里会出现"读了但用户没看到"的记录。是否需要区分由产品决定。

### 4.4 未验 / 其他
- **未验**：Firefox/WebKit；非 headless（有界面）窗口；真实触屏手势（390×844 只设了视口，没开 isMobile/hasTouch）；网络层（而非服务端）延迟/断线。
- 两种视口都有 1 条控制台消息 "Failed to load resource: 404"，Playwright 的页面级 response 事件里看不到对应 4xx，推测为浏览器自动请求的 `/favicon.ico`，与验收项无关（未单独证实，记为未验）。
- 1440×900 下 canvas 在 `.page-scroll`（max-height 55vh）内被裁一截，是现有布局，不影响判定。

## 5. 文件
- `logs/00-env.txt` 环境与版本；`logs/00-venv-install.log`
- `logs/01-service.*` 命令 1；`logs/02-browser.*` 命令 2；`logs/05-browser-repeat-*` 重复 3 次；`logs/06-browser-default-chromium-path.*` /usr/bin/chromium 路径失败复现
- `logs/03-ext-1440x900.*`、`logs/03-ext-390x844.*`：扩展驱动完整 JSON（每步 canvas 状态、像素、审计增量、全部 custody 行）
- `logs/04-screenshot-pixels.json` 截图像素复核；`logs/poppler/` 合成 PDF、pdftoppm 输出、检查结果（第 1 页 (255,0,0)，第 2 页 (0,0,255)）
- `harness/harness.py`、`harness/driver.cjs`：扩展验证脚本（放在仓库外，没改仓库）
- `screenshots/`：两种视口各 10 张（整页 + canvas 元素）

## 附录：首个错误（扩展驱动初版，已定位为驱动问题）
```
stage: blue_reread
locator.click: Timeout 30000ms exceeded.
  - locator resolved to <button disabled id="show-image">授权载入页图（记录访问）</button>
  - element is not enabled
```
原因：派生页模式下产品禁用原图读取，须先点「读取」。驱动补上该步后通过。
