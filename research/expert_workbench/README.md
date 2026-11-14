# 公开双角色研究工作台

基线专家候选 `a686c851333428d35374fb1596b6772a1cc6e9a8`；只新增本目录，不改变执行器/模型/回执/正式案件。以冻结 YANGZE22 三条待审主张及原文为唯一来源，显示两角色独立意见、精确引用、来源页码/摘要、不确定性、标签分歧或意见缺失。标签相同不计算共识，任何结果不写案件。

## 使用

```
npm ci --prefix web
node research/expert_workbench/build.mjs > /tmp/mcis-expert-workbench.html
```

用浏览器打开自包含 HTML，明确选入该版本输出目录的 `result.json`（最多1MiB；此展示上限比原导出8MiB更小）。没有预置答案、运行按钮、API、服务监听、持久化或自动上传。更换结果时完整校验后替换；失败保留先前结果；清空/更新选择使迟到读取失效。分歧/相同/缺失过滤和三条主张选择只改变显示。资料不写入浏览器存储；刷新需重选。

严格JSON解析拒绝重复键、坏UTF8、孤立代理码、过深结构、超限、未知字段。只接受固定 packet SHA `1dc5f6...d8790e`、manifest SHA `71cd8d...c4052`，相应 DeepSeek/Pi 配置、两角色及原文精确子串。源包构建时核对完整字节摘要；依赖现有 `web/src/reportOutput/strictJson.ts`（只读复用）。标题/解释/引用/来源均通过 textContent 渲染；无外部链接。CSP 仅允许内嵌脚本/样式的精确SHA，connect/form/frame/object/default均禁用。浏览器仍须实际验收其策略执行。

## 来源与证明边界

- `transportMocked=true`：脚本模拟提供方，**不是**真实模型能力验收。
- `transportMocked=false, realModel=true`：结果**声明**收到真实提供方响应；不认证底层身份、能力或意见正确性。
- `transportMocked=false, realModel=false`：真实提供方模式声明，未声明收到响应；不补造成成功。
- `realPi`、请求计数和 runId 都是结果字段声明。任何人可制作未签名JSON；通过校验不构成真实性证据。
- 这里只选入 result.json，**没有核验 completion.json/receipt.jsonl/comparison.html**。页面明确提示未证明导出完整。需要原执行器 `cli.py --verify-dir` 独立验证本地导出一致性；它本身也不认证作者、PDF或模型。
- 公开PDF URL/摘要/页码沿用冻结来源声明，未重新联网或认证。只接受既有公开冻结包，不能载入正式案件或其他报告。
- group `not_accepted` 即使已有一个完整角色，也显示失败/未知/取消状态，另一角色缺失；不把完整导出等同成功运行。

## 已执行验证

```
node research/expert_workbench/test.mjs
web/node_modules/.bin/tsc --noEmit --module esnext --target es2022 --moduleResolution bundler --resolveJsonModule --allowSyntheticDefaultImports --skipLibCheck research/expert_workbench/app.ts research/expert_workbench/model.ts
```

测试使用合成JSON和HappyDOM（可用MCIS_HAPPY_DOM_MODULE指定模块）；没有模型调用。另只读加载旧 `/tmp/mcis-expert-group-fixture-r1-20261114/result.json`：原CLI核验本地完整性成功，工作台接受，realPi=true/transportMocked=true/realModel=false。未重新运行Pi/模型；该兼容性不代表模型能力。

Browser plugin/skill本环境未提供；支持的Playwright + Chromium `chromiumSandbox:true` 在导航前因SUID helper/crashpad配置失败。未绕过沙箱或启动服务。未验收真实浏览器页面身份、截图、移动布局、控制台、键盘、文件选择/CSP；合成DOM不是原生浏览器替代。生产身份、真实DeepSeek能力和正式案件集成不在范围内。

## r1 计数一致性

独审发现仅上界校验允许不可能由固定执行器产生的计数。已要求未开始角色计数全零，完成角色至少两轮模型和两次工具，真实提供方完整组请求数等于模型轮数总和。失败/未知组仍允许请求数小于模型轮次（例如调用前回执失败），不抹去合法部分结果。这些仍是结构校验，不认证执行或真实模型身份。

## r2 真实提供方部分结果

只要真实提供方模式存在已完成角色，realModel必须为true，providerRequests至少覆盖所有已完成角色的modelCalls之和。否则其完成意见与组级请求声明矛盾，拒绝整份载入并保留旧视图。未完成角色允许调用前回执失败，因此部分组请求数仍可小于模型轮数总和；没有完成角色、请求发出但响应未知时，realModel=false仍可保留unknown状态。此校验只验证声明内部一致性，仍不是独立真实调用证据。

## 显示来源澄清（872815c 后续独立切片）
三条主张统一显示为“人工编写测试主张（含反例）”，不作为报告结论。它们均对应同一份报告同一页（PDF28/印刷26），不是三份独立证据。固定报告引用取packet.citation.quote，单独显示；两角色各自review.quote明确为模型选取引文，仍需人工审读。逐字引用来自冻结文本片段，PDF未重新认证。显示说明不进入模型提示或公开包，不增加逐条答案标签。查看器仍只读取旧单轮result.json，未接通会议结果/回执。

## 两轮复合回执接线（6f8f429依赖）

本目录从43d9f62979082afebf4ab3dac413b452bd2a362d的既有工作台提取；仅目录文件，不合并其父链/共享文档。model.ts及公开包保持原字节，旧单轮文件导入仍按原合同。当前依赖主链为已知main3aba2bf→178c998→a686c85→649d865→0a4bf22→3125eaf→93284d8→1b897f7→8f2fa05→6f8f429，新增本地只读接线；不带入PR56预览栈。

受控数据流：实际Pi执行器已有schema2复合回执 → Python receipt.validate_receipt重放/交叉校验 → export.projection → Node build --meeting结构校验 → 同一app.ts的多轮只读视图。没有生成另一套研究原型或伪造旧单轮runId/manifest。HTML包含展示投影而非完整源回执，保留原始输入bytes的SHA256供与原件对照；源回执需单独保管。

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m research.expert_workbench.export --receipt /绝对路径/receipt.json --output /绝对路径/meeting.html
```

这是本地转换，不运行Pi或模型。接收最大8MiB复合回执，拒绝符号链接、非普通文件、目录及FIFO；输出完整写入并fsync后独占发布，已有文件永不覆盖，失败不宣称成功。目录最后fsync失败时完整输出可能已经存在，需核对而不能盲目重试。Node构建使用解析后的绝对可执行路径、净化环境和30秒超时。

视图可切换实际已有轮次，各轮按角色并列意见/分歧/未知；第二轮只显示原回执已接受意见，不补造结果。预算区分协议请求预留、工具、已返回/未知/未派发。MockHTTP明显标非真实模型验收；远端字段只是本地观察声明，不认证提供方。始终标明人工编写测试主张（含反例）、同报告同页不是独立证据；固定报告逐字引用与模型选取引文分区。显示文字不进入模型提示。

浏览器仅校验展示结构和冻结来源，不重放Python全回执链；HTML/摘要没有签名，不是作者、模型、事实或源PDF认证。直接调用build --meeting可输入人工构造投影，不能拿生成HTML当独立执行证明；受控路径必须从export CLI校验原回执开始。hold:true只代表只读显示不授权新调用，不推断历史审批。原生多轮回执不能直接塞进旧单轮文件选择器；应显式使用本地转换路径。

安全状态：6f8f429协调复验仅进程所有权通过；独占reaper/稳定SIGCHLD仍必需。本轮安全凭据不存在，真实DeepSeek调用0，只有实际Pi+明确MockHTTP的离线接线验证。无正式案件/身份/服务、无模型按钮、无上传/部署。当前工作台并非正式案件工作台路由。

测试：Python test_export.py 22项（含实际Pi+MockHTTP端到端HTML），原40+来源19断言、新test-connected.mjs 34断言及TS检查；新断言可选传入本地projection JSON，未传则明确合成显示数据。浏览器插件未提供，使用现有Playwright+chromiumSandbox:true访问file HTML尝试在浏览器启动阶段失败，未导航/截图；未加no-sandbox。HappyDOM交互不是原生布局/键盘/辅助技术或CSP执行验收。
