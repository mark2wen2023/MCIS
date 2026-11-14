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
