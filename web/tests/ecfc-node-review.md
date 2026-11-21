# ECFC 逐节点待补导航（前端候选）

固定基线 `015df41bdac65ed7b43c73e945c3d268bba6f2ab`，来源分支 `work/w111-new-manual-ecfc`。原 Graph 的 null 时间提示和草图级来源选择仍保留；新增摘要不改 W11 模型、合同、验证、保存、报告或自动因果逻辑。

在人工编辑区之前列出当前节点标签、时间填写状态、来源绑定待核状态。时间严格 null 才是未填；0 为已填相对秒，不推断日期/UTC，不说已证实。任一节点来源不在当前授权来源与选中集合的交集中，都显示待重新核对；混合有效/无效也一样。没有节点绑定时，即使草图已选来源仍显示尚未绑定。新摘要只接收来源 ID 用于集合比较，不输出任何证据名称、摘要或 ID。

每个编辑实例使用 React useId 加当前行下标，给原时间 input 和原节点来源 fieldset 添加唯一 ID；原生按钮带 aria-controls，显式 scrollIntoView + focus。来源组 tabindex=-1。可重复/可修改的业务节点 ID 不参与 DOM ID。只读、忙碌或其他原编辑禁用状态下导航按钮也禁用，不假装能编辑。

来源确认还需 sourceAck、非 needReopen/忙碌、同案 envelope/context 与当前身份；身份/导航失效事件把本摘要来源状态设为未确认。父加载/错误态不渲染 Editor，原 EcfcPage 按案/身份 key 重建保持。即使状态未确认也不为旧来源贴可用标签；未实现新的授权机制或业务请求。现有编辑区本身的来源展示不属于此次摘要隐藏承诺。

## 可复验

使用已存在的离线 Node/React/esbuild/TypeScript/Vite，不安装：

```sh
bash web/tests/run-ecfc-node-review.sh
web/node_modules/.bin/tsc -b web/tsconfig.json --force
(cd web && node_modules/.bin/vite build)
```

本轮三条退出0。脚本先跑新增纯函数/SSR/原生按钮回调检查，再跑既有 `ecfc-model.test.tsx`（82条历史模型/严格JSON/渲染断言，本轮重跑，非新增82条）。覆盖 null/0、混合/未选/已失效、无绑定但草图有选择、空态、文字转义、语义列表、aria-controls 唯一目标、禁用状态；实际 Panel 定位和父 key/清除接线仅源码断言。按钮回调在手造组件树中执行，不是浏览器 focus 验收或真实 React effects/reconciliation。SSR无证据 ID 输出。

Vite 保留大于1500kB chunk警告。未运行服务、HTTP、API/权限、保存/归档、DB/ORM、真实数据/媒体/模型、浏览器或4A。未改旧冻结清单；本增量冻结在 `logs/ecfc-node-evidence-review.txt`，尚待独立复核。真实浏览器键盘滚动与焦点、换案/迟到生命周期仍待后续许可验收。
