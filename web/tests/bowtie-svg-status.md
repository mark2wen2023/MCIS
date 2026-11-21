# W15 SVG 状态提示（待独验）

基线 99b3b4bb8e88cbd390ac0c3e7a519ed533a890f3，独立候选 candidate/bowtie-svg-status-labels。原候选不变。

真实 Diagram 已有 SVG，但 Unknown 只在外围页面说明。新增 SVG desc：全节点待核验、屏障 Unknown、参考资料仅整图而非已核实节点引用。两个屏障类型新增可见“待核验 · 屏障未知 (Unknown)”；其它无屏障绑定节点显示 ToBeVerified。升级因素保留原绑定屏障行，完整 title 继续标待核验。不引入状态推断、逐节点证据或导出接口；原来源选择与清空守卫不变。

## 离线复跑

已有 Node/esbuild/React 依赖，不安装；从 web 目录：

```bash
bash tests/run-bowtie-svg-status.sh
./node_modules/.bin/esbuild tests/bowtie-unprotected-paths.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/bowtie-paths.cjs
node /tmp/bowtie-paths.cjs
./node_modules/.bin/esbuild tests/bowtie-preview-w153.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/bowtie-preview-regression.cjs
node /tmp/bowtie-preview-regression.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

本轮均退出0。新增检查：真实 React SSR 的 SVG desc、全部标题、两种屏障 Unknown、其它节点待核验、连线及输入不变、空图；来源边界只做实际 Form 源码断言。旧 Diagram 在新同一断言下失败（exit1），未修改旧提交。原 preview 检查用合成 fetch 替身，不连接 API。首次 tsc 因稀疏检出缺基线 report.schema.json 失败，原样补取后通过；未改合同。Vite 8.3.8 /768模块，既有 >1500kB 警告保留。

不是完整 W15 验收：未运行浏览器、SVG视觉/辅助技术实测、服务、C#核心、正式导出或保存。页面现状仍是 Bow-tie 假设草拟；AcciMap/STAMP 未实现。未获取任何原件或真实资料，不将“结构有效”当事实或屏障有效。
