> 历史证据归档（2026-11-14），不是当前授权或可执行说明。未在本次归档重跑原测试/模型；旧raw-key路径已在498f807禁用，真实执行仍HOLD。来源、原始摘要和归档摘要见MANIFEST.json。

# EXPERTWORKBENCH_PROVENANCE 独立验收

2026-11-14；隔离候选基线872815c，范围仅来源显示澄清。独审未改实现、分支或远端。

结论：受限独立验收通过，无当前切片阻断。**15个独立具名用例通过，0失败，network=0**，见results.txt。**11/11冻结哈希前后匹配**，见hashes.txt。

复跑：

```
node tests_acceptance/EXPERTWORKBENCH_PROVENANCE/independent.mjs
sha256sum -c logs/EXPERTWORKBENCH-PROVENANCE-impl-hashes-frozen.txt
```

## 证据

- 未载入结果时明确三条为人工编写测试主张（含反例），均来自同一报告同一页PDF28/印刷26，不是三份独立证据。
- 遍历三条主张，各自固定报告区pre严格等于packet.citation.quote；两角色分别选用不同sourceText子串，且均不同于固定引用，角色区正确显示各自review.quote。角色reviews数组刻意反向排列，验证按itemId映射，不把位置当身份。
- 来源展开区逐字保留sourceText、页码和片段摘要；固定引用明确未重新认证PDF，主张明确不等于报告结论或已认定事实。
- 合成恶意rationale/uncertainty中的script/img/iframe文本仅成为文字，未创建DOM元素/链接。非来源子串的恶意quote整份拒绝，保留旧固定引用和视图。
- 部分未知结果保留固定报告引用，仅显示已有角色选取引文，不补造另一角色；过滤、清空和清空后迟到读取不会串入旧引用面板。
- 三种合成会议/实际Pi脚本协议回执形状都被旧查看器拒绝；旧result夹带rounds/meetingSnapshot/referenceAnswers未知字段同样拒绝。没有把会议回执兼容性或执行能力伪造为成功。
- 独立逐字节比对model.ts、public-packet.json、engine.py、pi-runner.mjs与872815c，全部相同；packet内存对象和文件不变。显示解释没有进入模型输入或来源包。
- 实际执行本地build生成HTML，检查内嵌script/style的精确CSP SHA及connect/default拒绝策略。第一次测试直接搜索汉字失败是esbuild输出Unicode转义，已修正独立断言为解码转义后检查，未改实现；此项没有发现生产缺陷。

## 限制

测试为合成JSON、HappyDOM及静态生成HTML检查，无模型/Pi执行、无真实网络、服务或部署。network=0来自本地fetch拦截及计数，不代表执行了真实浏览器CSP测试。没有重复已知沙箱启动失败；原生文件选择、布局、键盘、屏幕阅读器及浏览器策略实际执行仍未验证。

当前只支持旧单轮result.json；会议结果/回执未接通。未核验completion.json或回执链，声明中的模型/Pi/请求数不成为独立执行证明。来源PDF未重新获取或认证，来源引文是冻结文本的逐字展示，不认证语义或事实；模型选择精确子串也不表示正确引用上下文。三个测试主张不是三份独立证据，反例不作为报告结论。生产身份/案件权限与真实模型能力不在本次范围。

计数独立：本报告15具名用例不与开发40+19断言混算。独审仅新增本目录和DEFECTS报告；可以按父任务授权进行本地提交，不据此推送、部署或扩展能力声明。
