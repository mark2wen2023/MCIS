# W12 分析快照跨案浏览器对照 — 官方验收记录

- 选用固定 SHA：`candidate/analysis-snapshot-scope` @ `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5`（基于 origin/main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`）。理由：Dot 指定先核该 README 与相应候选；该候选尖端即此提交，含切案立即停用旧分析快照的页面钩子。产品文件哈希与 `logs/analysis-snapshot-scope-impl-hashes-frozen.txt` 一致。
- 已有 SSR、构建、合成切案（`web/tests/analysis-snapshot.cjs`、`web/tests/analysis-page-scope.cjs`、tsc/vite，见原 README）只引用，不作为本轮新验收。这些原件明确不是真实浏览器。
- 本轮只新增 `tests_acceptance/w12-snapshot-scope-browser/`，未改产品。运行时在宿主进程中替换 `load_seed` 默认路径，只提供两张纯合成案（SYN-W12-SNAP-A / SYN-W12-SNAP-B），不加载产品目录中的历史分析种子。
- 依赖：Node v24.22.1；已有 node_modules（package-lock SHA-256 与 03a8e786 一致，从既有工作树硬链复制，未安装）；Python Playwright 1.65.2（`/workspace/w17-pyplaywright-venv`）；Chrome 156.0.8078.47；服务 Python 为既有 venv。预构建使用既有 Vite 8.3.8，767 模块，未走外网。
- 官方运行（Asia/Shanghai）：2026-11-27 07:24:12–07:24:17 CST，退出码 0。`timeout --signal=TERM --kill-after=10s 150s`。正常沙箱（`chromium_sandbox=True`，无 `--no-sandbox`）。未使用 unshare（避免嵌套用户命名空间破坏沙箱）。服务与 web 同进程只监听 `127.0.0.1:18770`。
- 视口：先跑桌面 1440×900，随后有条件补跑 390×844，两次均通过。关键截图见 `official/screenshots/`。
- 轨迹换版：未验。页面只显示本次读取的 seedSha256，并写明「未确认登记轨迹实时版本」；未接登记轨迹换版信号，不伪造版本变化，不把跨案保护算成同案换版通过。
- 不是 W12 整包。HTTP-only 或 DOM 模拟未冒充浏览器结果。
