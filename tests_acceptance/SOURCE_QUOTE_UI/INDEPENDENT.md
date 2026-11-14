# 原文引用只读组件独立验收

结论：当前切片无阻断；仅 UI 与安全边界检查，不是真实模型或浏览器引擎验收。

已静态审查共享 `SourceQuoteReview.tsx` 及当前提案、历史归档两处入口。组件直接把 quote 作为 React 文本子节点，不 trim、normalize、解析 HTML、不重新判定语义、不写事实或调用 RPC。CSS 使用 `white-space: pre-wrap`，只保留输入文本的空白，不承诺还原 PDF 表格/列布局。提示常显，不隐藏在 details；历史内容继续标注未经认证。摘要/结构化主张与原文分别显示。

新增 `issue-ui/web/tests/source-quote-independent.tsx`，7 项独立 HappyDOM 检查通过：

- 当前与历史入口中，前后空格、双空格、换行、制表符、“约”、补充平面 emoji、组合 Unicode 字符及 HTML 样式文字的 blockquote.textContent 与原字符串逐字相同。
- `pre-wrap` 生效于 inline style；HTML/script/img 字符串保持文本，不产生对应元素。
- 限定词与空白不证明有/无的提示常显，引用定位不等于语义支持。
- 当前脚本复核仍明确“非真人审核”；历史仍有历史包未经认证标识。
- 初次挂载、重挂载不自动发命令；当前仅显式生成，未发 review；历史仅显式 list/read，未 import/export/activate。
- 未连接按钮禁用、旧引用隐藏，fetch 调用为 0。

独立复跑通过：

| 检查 | 结果 |
|---|---|
| 新组件主测 | 5 |
| Pi 当前 / 历史主测 | 30 / 28 |
| Skill UI 回归 | 26 |
| 旧当前工作记录主测 / 独测 | 24 / 9 |
| 旧历史归档主测 / 独测 | 27 / 13 |
| strict TypeScript（组件、两入口及两 hostPort） | exit 0 |

旧工作记录主测覆盖未知写入结果后的原操作重试、停止重试后重读；本变更没有改 operationId 或 RPC 协议。无真实 API 调用，无事实自动激活，无部署或提交操作。
