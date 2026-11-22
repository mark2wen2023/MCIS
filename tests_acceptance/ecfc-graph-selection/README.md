# W11 实际 Graph / Panel 只读选边候选

固定基线 dc261c6b18c88c4942c8511d5948a679cc1539d8。不是第三套图或并行演示：实际 Graph 的 SVG 边和图旁原生按钮共享 EdgeSelection；实际 Panel/Editor 控制可读范围。原合同、后端、授权、保存流程、旧冻结不变。

默认 EcfcPage 不传 candidateEdgeReader，明确显示“可信边关联尚未接通”，没有原件读取动作或请求。候选注入点仅为受控合成测试使用，函数引用不是身份、授权或可信关联证明；不得从 URL/浏览器输入构造它。生产接线须另审服务端固定图/边/原件关联、逐次重新授权及 Access 审计。没有真实读取器接入本候选。

Panel 仅将已保存、来源未变、未修改且无未知保存/拒绝/重开要求的文档交给选边视图，不以 writeAllowed 代替原件读取资格。编辑（包括同边端点不变时改节点文字）、来源变更、忙状态和保存回执重开要求使旧子树失效；重新预览不恢复可读文档。已有 EcfcPage 的 case/identity key 和 Panel 的身份/导航守卫保留。读取器得到当前文档 revision/digest 与边身份；这里只作显示对应核对，不验证来源真实性。有限结果不转发额外字段，UTC不成为事件回放时刻；没有 Seek、签认、报告或保存出处动作。

## 离线复跑

已有 Node / React / esbuild，无安装，无网络。仓库根执行：

```sh
MCIS_NODE_MODULES=/absolute/existing/web/node_modules node tests_acceptance/ecfc-graph-selection/run.cjs
```

10 个场景退出0：真实 Graph SVG/按钮同选择；默认关闭；已存草稿守门；迟到成功/失败；错版本拒绝和新版本自己映射；实际 Editor 只读资格；改节点文字后重预览不恢复；模拟保存确认后必须重开；来源/错案失效；无回放跳转。

run.cjs 仅在内存构建时暴露原 Editor，替换其 React hooks 为明确手写槽和请求为纯合成 Promise。Graph 使用真实源码（useId 替身），默认视图另用真实 React SSR。不是 React DOM/effects、网络、真实保存或权限验收。fetch 明确禁止，构建产物仅写自动清理临时目录。初次测试的合成 Sequence.bold 不符合现有解析器，修正夹具为原合同要求的 true 后通过，未改产品解析器。

相邻回归（web 目录、使用已有 node_modules）：

```sh
./node_modules/.bin/esbuild tests/ecfc-model.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/ecfc-graph-model.cjs --jsx=automatic --log-level=warning
node /tmp/ecfc-graph-model.cjs
./node_modules/.bin/esbuild tests/ecfc-node-review.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/ecfc-graph-node.cjs --jsx=automatic --log-level=warning
node /tmp/ecfc-graph-node.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

实际均退出0；原82项模型/Graph SSR、节点导航回归通过（不与新场景累计覆盖数）。Vite8.3.8 / 775模块，既有大于1500kB警告保留。

未启动浏览器/服务/HTTP/DB/ORM/模型；未读真实证据。浏览器实测、效果清理时序、Tab/Enter焦点、SVG命中范围、视觉与真实身份/关联仍待验。正常入口为既有 ECFC 页面，受原先门控；未启用新的可访问产品能力，不合并部署。

## 5549ee8 后续：焦点归位候选（2026-11-22）

只在应用内重开和身份通知将移除选边区域前，检查当前焦点仍属于该区域，才同步 focus({preventScroll:true}) 到标题。不处理其他输入、已断开的节点；不使用延时、localStorage 或页面加载 autofocus。EcfcPage 的标题位于 keyed Panel 外，身份换版不会把归位目标一并卸载。Panel 单独使用时回退到自己的小标题。主动包导航设置抑制标志并清内容，不归位。无原件权限时不恢复任何旧内容。

同一 run.cjs 现为13场景：原10场景不变，另加手写DOM焦点所有权判据、实际Panel重开回调、静态身份/导航接线检查。13场景、原82项模型SSR、节点导航、tsc、Vite均退出0；Vite776模块，原大包警告保留。相邻节点导航断言首次因属性顺序不符失败，恢复原key属性顺序后原断言通过，未放宽测试。

**没有实跑React effects、真实DOM或浏览器键盘**。下一关应在正常沙箱浏览器验证：边按钮/出处读取控件持焦时重开与身份失效；别处输入不被抢焦；点击导航/后退不归位；权限拒绝后标题仍可见且旧出处为空。整页浏览器刷新后的焦点恢复未实现、未声称通过；不持久保存焦点或旧出处。原5549ee8冻结继续对应该固定提交，本增量用独立focus冻结。
