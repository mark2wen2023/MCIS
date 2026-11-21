# W15.3：当前草图未画屏障的路径

基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。独立候选，不改变契约、核心图规则、API、权限、持久化或 ECFC。

用户入口仍是现有 `#/systemic?case=<明确案号>` 的人工 Bow-tie 草拟。原结构核查成功后，在结果区增加语义 section/标题/列表：显示威胁→顶事件未画预防屏障、顶事件→后果未画减缓屏障的节点名称和 ID。无见证时说明不代表控制充分；有见证不表示现实中没有屏障或风险成立。

实现复用输入节点/边和原 `parsePreview` 校验结果。核心 `BowTie.cs:IsAllowed`（基线297–310行）允许 Threat→Threat/PreventionBarrier/TopEvent，TopEvent→MitigationBarrier/Consequence；后果无出边。只在核心 structureValid 为真时，从现有边中排除屏障，逐端点 BFS，ID ASCII 固定排序，最短见证优先，每端点至多一条。64节点/128边预算沿原 validateInput，visited 限制搜索；不是枚举所有路径，也不另行实现核心结构裁定。经过屏障的替代路线不会隐藏另一条未画屏障的见证。

结果只在原异步 hash/parsePreview 成功后记录完整 canonical input 及当时身份字符串。本次列表再比较当前案、身份、来源和 canonical input；未检查、结构失败、编辑、来源失效或上下文不符返回 null 而不是“没有路径”。原 edit/身份事件的 clear 和 SystemicPage 按案/身份 keyed Session 保留。名单/哈希不是授权证明。

## 实跑（已有离线 Node 依赖，无下载）

```sh
bash web/tests/run-bowtie-unprotected-paths.sh
web/node_modules/.bin/tsc -b web/tsconfig.json --force
(cd web && node_modules/.bin/vite build)
```

三条退出0。第一条仅新纯 TS + React SSR：direct、允许的威胁链、两类屏障阻挡、同端点有/无屏障两路、排序稳定、节点预算/异常、编辑/跨案/同角色不同身份/来源改变/未验证状态、文字转义和语义列表。真实 Form 清结果和父 key 接线为源码断言，并非 React effects 或浏览器生命周期测试。运行脚本缺已有 esbuild 返回2，不会安装；临时 bundle 自动清理。

首次稀疏检出缺少现有 report.schema.json 导致类型/构建失败，补齐受管 schema 后上述检查通过；没有改 schema。Vite 保留原大于1500kB chunk 警告。未运行旧 W153 API/浏览器套件、服务、HTTP、核心 CLI、数据库、媒体、模型或真实权限；无视觉/键盘浏览器验收。本轮 SSR 不等于端到端或专业风险判断。
