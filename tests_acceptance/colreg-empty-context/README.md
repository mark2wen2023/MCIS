# 避碰对照空时间带：前端评审候选

基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。只修 ColregView：空 bands 不再把布局默认 0–1 秒显示成分析区间，明确无时间带不表示无危险，已有核查项供人工核对。

复跑（已有离线 Node/React/esbuild/TypeScript/Vite 依赖，不自动安装）：

```sh
node web/tests/colreg-empty-context.cjs
cd web
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

测试实际编译旧、新 ColregView 并 SSR，旧版空带反例、空态提示、真实零时刻以及存量未知/推算/转义内容。非空合成结果的整个 HTML 与基线逐字相同。未运行含案件样例的历史测试。本次不改规则、默认阶段语义、复核状态、API、来源或权限；不是浏览器、效果生命周期、法律判断或规则引擎验收。
