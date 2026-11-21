# W12 页面08：分析快照作用域（待独立复验）

基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`；独立候选 candidate/analysis-snapshot-scope。不合并报告、回放或试用候选。只改真实 AnalysisPage 的读取接缝，不改算法、接口或共享轨迹合同。

## 可验收变化

原 useLoad 在切案后的 render 和请求等待阶段仍返回旧案 data。现有实际钩子在合成生命周期中复现此反例。新页面专用钩子以案号/页面观察到的身份上下文及请求代次区分结果：等待、失败、重读、切案立即不渲染旧 AnalysisView；旧响应失效。新增“重新读取分析快照”，明确显示本次 seedSha256，但不称为当前登记轨迹版本。分别读取的列表与详情须有同一合法SHA，案号或服务支持的key别名须唯一匹配，错案/摘要不一致不能用于显示。

本机路径 `#/analysis?case=<已有分析案号或key>` 保持原路由语义，默认案兼容行为未在本任务扩大修改；没有联网或运行此路径。需要原服务才可实际使用，当前没有启动许可或运行验收。

## 实测（现有离线依赖，均退出0）

在 web 目录：

```bash
node tests/analysis-snapshot.cjs
node tests/analysis-page-scope.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

- 第一条执行原hooks源码反例与新hook源码，手写render/commit/cleanup、受控Promise：换案等待/失败、手动刷新同步失效、摘要不一致/错案、页面观察到的身份改变、迟到成功、卸载、合法别名。不是React真实调度或浏览器。
- 第二条实际AnalysisPage的React SSR；读取hook和AnalysisView边界被替换，核对等待/错误不渲染图表、当前结果提示与按钮。不是图表像素或effects验证。
- 两份TS配置及Vite 8.3.8构建；767模块，既有大于1500kB警告仍在。
- 最初构建因稀疏检出缺 report.schema.json 失败，补取固定源码合同文件后通过，未改合同。未下载依赖。

未运行原 `tests/run-analysis-w12.sh`：其 analysis-w12.test.tsx 明确读取案例seed及历史数据dump，不符合本次纯合成范围。没有把历史绿测当成本轮通过。

## 不应越过的结论

静态源码 `service/mcis_service/analysis/router.py:load_seed/_meta/get_analysis` 返回离线生成分析和seedSha256，不实时调用CPA，也不绑定登记双船pin。`analysis/types.ts` 的series/trackPlot没有显式缺轨版本字段。故本轮不可能从这条UI证明登记轨迹换版自动过期、短缺口不插值、当前精确观测或固定报告引用。

同SHA是两次读取的内容标识一致，不是服务端同事务、授权或来源真实性。页面未刷新时不能发现服务端变化；未改身份机制，快速身份变化和真实React并发仍需实机验证。下一步是先约定已有算子结果如何携带真实输入版本及缺轨语义，不能把示例seed摘要冒充证据pin。

DCPA/TCPA、距离曲线和关键时刻的计算与措辞本轮未改；无COG补艏向、最近距离替代预测DCPA或因果推断。无HTTP、真实浏览器、业务服务/ORM、媒体、4A、原案或模型验收。
