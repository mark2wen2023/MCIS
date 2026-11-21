# 手动真实浏览器验收入口 — 待实机验证

只验固定产品 `f536f7482f1e1bff5f448a699cf4b0af320f2af7` 生成的合成 HTML。本目录新增脚本和说明，不改应用、固定夹具、共享契约、依赖清单或 CI。脚本源码 SHA-256：`bd01033f78e7cef4505d651c76d4dbda556b632cbf4453889777c2e5de113627`。

HTML 必须逐字节匹配 `8ad4bf30eebbe7309155292682361c1b977baacb667dc3019bd99c22307c00e6`；不是接受任意 HTML 的浏览器驱动。生成器与输入仍是原提交，不刷新旧冻结。

## 最短复跑（正常 Linux/macOS 本机）

前提：已有 Node、Python 与原校验器所需 jsonschema；已有可被 Node `require('playwright')` 找到的 Playwright，以及正常配置沙箱的 Chromium/Chrome。本入口不安装、不下载、不启动 Web 服务。缺任一环境条件即失败；不要添加 `--no-sandbox`、修改安全策略或公开托管。

从此候选仓库根运行：

```sh
CLOCK_QA_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mcis-clock-qa.XXXXXX")"
python tools/replay_evidence_clock/preview.py --output "$CLOCK_QA_DIR/preview.html"
node tests_acceptance/replay-evidence-clock/browser/check.cjs   --html "$CLOCK_QA_DIR/preview.html"   --output "$CLOCK_QA_DIR/result"   --chromium /usr/bin/chromium --screenshots
```

macOS 的现有 Chrome 可将 `--chromium` 换成 `'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'`。省略该参数仅使用 Playwright **已有**浏览器，不自动下载。Playwright 装在其它已批准目录时可用 Node 标准 `NODE_PATH` 指向该已有 node_modules；不要求本仓添加依赖。省略 `--screenshots` 可只记结果。`--output` 必须不存在；错误参数、非普通文件、摘要不符、已有输出目录在启动前非零拒绝。

脚本将经散列确认的 HTML 复制到自己新建的结果目录，直接打开 `file:` URL；不使用宿主业务服务。固定 1440×900、全新临时浏览器上下文、`chromiumSandbox:true`、`offline:true`、阻止 Service Worker；没有已有登录 profile、端口、云服务或后台托管。

## 判断结果

仅进程退出 **0** 且 `result/result.json` 中 `status: passed`、`stage: complete`、`browserClosed: true` 才表示这次真实 Chromium 检查通过。结果记录产品/HTML 标识、实际浏览器与 Playwright 版本、检查项目、页面请求、console/page errors、可选截图名。截图为 t20、t100、t80、t124-25 四种关键状态的完整页面。

启动/导航/断言/关闭失败均非零；已有部分检查和截图不能冒称全部通过。通过输入检查并创建结果目录后，失败会留下 `result.json` 和原始错误供定位；启动前输入错误只输出错误并非零退出。日志可能含本机临时路径，分享前自行核对。不自动删验收制品，浏览器由 finally 关闭。

覆盖实际控件：

- T+0 原点 A-t0、固定夹具 ref 与 `/points/0`；点击按钮查看原始记录。
- T+20 B 原 12:00:08Z +12 → 12:00:20Z；`position.kind=interpolated` 是既有样例品质，不是实测。
- T+100 设备 +7 秒与 A-t100；未知设备独列，不进入当前同步事件。
- T+80 一点：A 缺轨，B 有当前观测；换时点清除旧详情。
- T+124.25 零点：A 缺轨、B 无精确输入，不能沿用 B 上次位置。
- 60/100/121/127.5 四端点显示未知艏向，COG=90 不补 HDG。
- 请求仅允许本地 HTML 本身；任何额外页面请求均使断言失败。离线上下文中记录的是页面请求/尝试，不是浏览器全进程网络审计。console/page errors 必须为空。

## 本轮实际证据与阻碍

已执行：`node --check .../browser/check.cjs` 退出 0；原候选 `check.py` 8 项退出 0；原固定双船校验退出 0；全新临时 HTML 生成/摘要核对及 `panel.cjs` 手写 DOM 退出 0；无参数/错误 HTML 摘要/已有输出目录三项启动前检查分别按预期退出 1。未用模拟 DOM 来执行或冒充 Playwright 验收。

**本脚本真实浏览器尚未跑通。**此前临时脚本在 Chromium 156.0.8078.79 / Playwright 1.62.1、保留沙箱时于导航前 SIGABRT：`/usr/lib/chromium/chrome-sandbox` 属主 nobody、模式4755，Chromium 要求 root 属主；另报 `chrome_crashpad_handler: --database is required`。没有绕过或修改权限。本轮没有反复启动这个已知失效环境。受管浏览器也不能打开此容器本地文件/环回，未公开托管。

本入口不是实际三维、Unity/mcis-3d、业务授权、真实资料、媒体或端到端验收；不包含自动像素比较或移动端验收。请在正常沙箱浏览器环境运行后保留 result.json 与截图，再报告浏览器是否通过。
