> 历史证据归档（2026-11-14），不是当前授权或可执行说明。未在本次归档重跑原测试/模型；旧raw-key路径已在498f807禁用，真实执行仍HOLD。来源、原始摘要和归档摘要见MANIFEST.json。

# 显示澄清候选

独立本地clone：/workspace/mcis-workbench-provenance-20261114；分支codex/expert-workbench-provenance-20261114；父基线872815c240b6b709d8a1b1182d252ffe28ceca92。未提交/推送，原工作目录未修改。

修改app.ts显示与README；新增test-provenance.mjs；REQUESTS先登记冻结app修改，ROADMAP标待测。11项实现/只读依赖冻结。

40项原有模型/DOM断言+19项新增显示断言通过；新增以两角色选择互不相同且不同于固定报告引用的合法文本，逐一核对全部三主张展示。四项只读依赖字节与git基线比对通过：model、packet、engine、pi-runner。TS noEmit和自包含HTML构建通过，产物/tmp/mcis-workbench-provenance.html。依赖只读复用原副本web/node_modules（符号链接，不提交），Happy DOM复用/tmp现有安装；未下载依赖。

只支持原单轮result.json，未接会议结果/回执。无模型提示/答案真值标签更改，无真实Pi/模型、服务、网络、凭据或PDF认证。Happy DOM不替代真实浏览器；本轮未启动浏览器，不绕过既有沙箱限制。等待其他独立审查者验收。
