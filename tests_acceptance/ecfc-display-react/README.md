# W11 候选前端展示适配：React SSR + 手动事件 + 受控 Promise

基线 d1db803b06ed89a02629a3bd2817ec6ef3a72fb9。现有 dc261c6 的 `web/src/ecfcDrafts/Graph.tsx` 仅绘图，无边原件加载或会话状态；不改生产图组件，不将研究映射接进产品。当前依赖有 React/react-dom/server/esbuild，没有 react-test-renderer/jsdom。本增量全部位于 tests_acceptance，不修改原 Python Selection 或契约。

`Adapter.tsx` 是候选专用纯前端适配，含真正 React 只读视图和外置会话控制器。合成宿主调用 select(context) 同步清空；真实 JSX 按钮的 onClick 发起受控 Promise。新会话序号隔离旧完成与旧控件；不使用任何身份凭据。上下文固定同案、图revision/digest、edge ID与端点；结果必须匹配当前上下文。这里只验证展示选择，不是生产映射或授权验证。

片段为同一合成例的 `/fragments/0` 和 `2026-02-01T12:00:37.000Z`，另附显式合成摘录以验证清空和 React 转义。无实际登记或原件访问、无 Access 增量。有效源UTC不提供已审核回放UTC或精度，不启动播放。待审/非因果证明标记保留，无保存/签认/报告按钮。

## 单一复跑命令

```sh
MCIS_NODE_MODULES=/absolute/existing/web/node_modules \
  node tests_acceptance/ecfc-display-react/run.cjs
```

只用已有依赖。esbuild产物在新临时目录，成功/失败均清理，不安装联网。6项场景通过，退出0：

1. 已显示V1切V2，同步去除旧定位、摘录和跳转控件；不自动读取，旧渲染控件无效。
2. 待决V1成功在V2后返回，不触发重新渲染；当前V2新映射才恢复。
3. 待决V1失败在V2后返回，同样忽略，错误原文不展示。
4. 删除当前边（select null），旧完成无效、读取禁用。
5. V2请求收到V1映射，显示有限失败状态且无出处。
6. 当前读取普通失败，清空且不显示异常正文。

正例同时检查真实 React SSR 的摘录转义、源UTC可见、待审标签，以及 disabled 跳转按钮没有 onClick。事件通过遍历实际候选组件返回的 React element 调用，不模拟浏览器点击。网络fetch被测试禁用。

本轮实际编译并执行6项；首次构建有缺失结束括号，修正后重跑通过。Node脚本语法与git diff检查通过。未运行Python/DB/服务/模型、浏览器或生产组件生命周期；这不是 React DOM reconciliation、effects、并发render、键盘/焦点或视觉验收。没有新生产边绑定、身份机制、权限、存储或接口，也不证明真实异步撤权。旧d1db803节点/边工装保持原样，未累计其测试数。
