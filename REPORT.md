# W12 窄屏布局 — 官方验收记录

- 底版：`03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5`。独立候选 `candidate/w12-narrow-layout`。沿用同一合成夹具。73aa88b / efcb43a 的跨案与等候帧行为不重跑。
- Before（未改产品，正常沙箱 Chrome，390×844）：完成态 `innerWidth=390`，`documentElement.scrollWidth=941`；等待态 `scrollWidth=802`。与 Dot 所述 941 / 802 一致。1440×900 无横滚。
- 溢出源头：共享壳 `.app` 网格（`--sidebar-w: 224px` + 1fr，无窄屏断点）与顶栏 nowrap 案头，见 `web/src/styles.css`、`web/src/Layout.tsx` @ 03a8e786；完成态另有分析页 `page-head` / `case-switcher` / `.an-top` 双列与来源表，见 `AnalysisView.tsx`、`analysis.css`。未改共享 `styles.css` 或 `Layout.tsx`。
- 修改（分析页/该路由窄屏壳）：新增 `web/src/analysis/analysis-route-shell.css`，仅由 `AnalysisPage.tsx` 引入，并在挂载时给 `html` 加上 `w12-analysis-route`。`@media (max-width: 600px)` 下单列堆叠侧栏与顶栏、分析区折行；图表/表格保留 `panel-body` 内横向滚动，不用整页 `overflow: hidden` 裁剪。`AnalysisView.tsx` 仅为案头切换与曲线选择补了 Enter/Space 键盘激活，未改取数、时钟、CPA 或轨迹版本（`useAnalysisSnapshot.ts`、`derive.ts`、`types.ts`、`router.py` 哈希未变）。
- After（官方 150s，2026-11-27 09:00:26–09:00:30 CST，退出 0，127.0.0.1:18773）：390 完成/等待 `scrollWidth=390`（≤ innerWidth）。Tab 24 步可到角色、重新读取、两案切换与「案件航迹」；对乙案控件按 Enter 完成切换。1440 关键尺寸与 before 一致，视口 PNG 像素级相同（0/1,296,000）。
- 不是 W12 整包。未重跑完整切案回归。
