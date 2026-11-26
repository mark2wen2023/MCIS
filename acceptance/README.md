# W12 分析快照跨案浏览器对照

固定底版：`candidate/analysis-snapshot-scope` @ `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5`（基于 origin/main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`）。选用理由：Dot 指定先核该 SHA 的 README 与相应候选；该分支尖端即此提交，且含切案立即停用旧分析快照的页面专用钩子。

已有 SSR、构建、合成切案（`web/tests/analysis-snapshot.cjs`、`web/tests/analysis-page-scope.cjs`、tsc/vite，见 `tests_acceptance/analysis-snapshot-scope/README.md`）只引用，不作为本轮新验收。那些原件明确不是真实浏览器、不是 HTTP、不是业务服务。

本目录只新增浏览器对照工装：真实本机服务 + 已构建 web 只监听 127.0.0.1；两案纯合成数据（运行时覆盖分析种子，不改产品源码、不使用产品目录中的历史种子）；正常沙箱 Chromium（禁止 `--no-sandbox`）。官方门槛只验：A 案当前快照与 CPA/距离曲线可见 → 切到 B 不再显示 A 的快照或标值 → 切回 A 只展示 A。

轨迹换版信号：产品只展示本次读取的 seedSha256，并写明未确认登记轨迹实时版本；本工装不伪造版本变化，同案换版记「未验」，不把跨案保护算成换版通过。

不是 W12 整包。DOM 模拟或 HTTP-only 不能冒充浏览器结果。
