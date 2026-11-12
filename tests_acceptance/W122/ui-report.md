# W12.2 独立前端验收记录（未冻结预检）

## 实际执行

- 已读合同、论文 §3.4/4.5.6、ARCHITECTURE §4.6、CurrentAnalysis、model、AnalysisPage、identity/navigation。
- `bash tests_acceptance/W122/ui_run_model.sh`：34 项独立模型/SSR 断言通过。包括错案/错船/错窗/错计数、重复/非有限/无效 UTC、来源枚举、退化及微小负 TCPA 舍入为零、XSS 转义、空表、2000 点展示上限与端点保留。
- `python tests_acceptance/W122/ui_accept.py`：两次正常启动（含获准环境重试），均在 Chromium 启动时失败：`process_singleton_posix.cc:297 socket() failed: Operation not permitted (1)`。未换二进制或绕过权限。Vite 已清理。
- **浏览器断言执行数为 0，没有截图，没有浏览器通过结论。** Python 脚本仅语法编译通过，尚须在允许本地 socket 的环境完整实跑及修正测试夹具（若需要）。

## 尚未实证的浏览器范围

脚本准备覆盖真实前端 + 拦截合成 API（不代替真实后端/核心联调）：2501 点、实际 ECharts scatter 类型与 2000 点上限、26 页完整表、四来源/缺来源、非虚构声明、转义、重复点击、输入/身份/案件变化丢弃迟到结果、模式导航/Back/pagehide、403/502/未知案/无船/空结果、格式错与错案响应、1440/1920 布局、原始点不进入 local/sessionStorage。

真正关闭标签页、浏览器真实 BFCache 恢复、全链路真实核心、权限撤销与快照重检仍须对应独立服务/集成验收；模拟 pagehide 不等同于真实关闭/恢复。脚本待跑不算覆盖已完成。

## 静读观察

- 取消链条使用 AbortController + generation + identity，页面 key 含身份/案件/模式；pending ref 在异步请求前设置，防重复点击。仅为实现静读，不视为交互通过。
- 默认当前案、历史基准显式入口；散点/100 条分页及不保证真实性/不作责任安全结论措辞已存在。
- **可用性问题（已独立模型重现）**：非法案件/船舶元数据进入 `parseMetadata` 时抛 `TrackDataError('FORMAT')`，CurrentAnalysis 的 `message()` 原样使用 `e.message`，用户只见 `FORMAT`；元数据超限同理只见 `METADATA_LIMIT`。合同要求格式错明确。建议转换为中文“案件或船舶资料格式不符，未显示结果”，保留内部错误码可选。不涉及泄漏或错误计算。此项待负责方裁定级别，未改实现。

本记录不是完整 W12.2、完整 W12 或整体验收通过。

## 正式冻结后更新

86项冻结哈希起止一致。独立UI模型/SSR现36断言通过（原34+中文错误映射2）。D03已改为CurrentAnalysis使用readError，静读接线与中文映射验证通过，代码/模型范围关闭。内部parseMetadata保留FORMAT错误码合理，不再将其等同于用户显示消息。浏览器仍0项、无截图，上述交互未验范围不变；参见最终REPORT.md。
