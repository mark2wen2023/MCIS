# W7 同一页面切轮/刷新（真浏览器通过；延迟旧轮抵达后不回填在既有入口不可实现）

- 检索：未发现覆盖本项的等价真 Chrome 与真实请求回执。`0092734` / GB-8 / `evidence/w7-deadline-grokbot-1f329c3` 是另一项默认 30／商定 45 的期限/重开，未重跑、未充数。固定候选 `cbb3997` 原先只有模拟 DOM，未把模拟当成真浏览器证据。
- 底版：`cbb3997ccb9f948b9762c7954fde21d8d9b275d7`
- 候选 `candidate/w7-round-switch-browser`：`7d85b68a5d681dd43308de32dd5b39f637966f7f`
- 只新增 `tests_acceptance/w7-round-switch/` 三份验收文件。未改产品、权限、CI、契约、主线。未安装、未合并、未部署。未用真案/4A。
- 正式页 `#/recs?case=`（报告草案征求意见）+ 真实本机服务（127.0.0.1:18792 / Vite 18793），隔离临时 SQLite，`seed_demo=False`。官方接口预置一案两轮合成已登记记录：SYN-W7-ROUND-001，第 1 轮 SYN-DRAFT-R1 已关闭（回复「第一轮已登记回复（虚构）」），第 2 轮 SYN-DRAFT-R2 未关闭（回复「第二轮已登记回复（虚构）」）。
- 官方脚本 `timeout 150 … run.py` 退出码 **0**。Google Chrome 156.0.8078.47，`chromiumSandbox: true`，没有 `--no-sandbox`。验证期间浏览器只发 GET，未向 `/consultation/` 或 `/recommendations` 发 POST/PATCH，未发征求意见、未中途写数据库、未捏造响应。
- 真页面：默认当前轮为第 2 轮，选择器与已登记回复显示 SYN-DRAFT-R2 / 「第二轮已登记回复（虚构）」，不混第 1 轮；切到第 1 轮后显示 SYN-DRAFT-R1 / 「第一轮已登记回复（虚构）」，不混第 2 轮；再切回第 2 轮仍不混旧；选中第 1 轮后点官方「重新读取」，加载结束后仍保持第 1 轮内容与来源，不回填第 2 轮。
- 延迟旧轮真实只读响应、当前轮显示后旧响应完整抵达仍不回填：在既有官方入口不可实现（「重新读取」会清空当前编辑区并在加载期间禁用第二次刷新；「选择轮次」不发新 GET）。未取消请求。`producibleAtOfficialEntry: false`，`cancelled: false`，`countedAsArrivalProtection: false`。此项不作为已收到防护，也不单独记为首断点。
- 候选不是正式验收。此项不等于 W7 整包，也不等于 W12 或 W3 整包。
