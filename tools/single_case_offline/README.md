# 软件单案离线交接入口（默认仅预检）

基线 `3eabe40551b871e509442e707e514f4ad0e26d85`；仅同支新增工具和测试，不改原生产、交叉实验或授权。不是可启动试点，不连接c51c73c浏览器预览。旧测试和旧冻结原样保留。

```bash
/path/to/existing/venv/bin/python -I tools/single_case_offline/run.py
/path/to/existing/venv/bin/python -I tools/single_case_offline/run.py --run
/path/to/existing/venv/bin/python -I tools/single_case_offline/check.py
```

默认预检不创建业务库；--run只运行四个明确离线脚本。必须Python3.12，已验证依赖SQLAlchemy2.1.8/FastAPI0.162.7/jsonschema4.26.0；版本不符明确拒绝，不安装或自动放宽。预检导入上述库但不导入应用；完整传递依赖供应链/跨平台兼容不因此得到证明。缺Git对象/文件/摘要不符、工作树受测文件变化均失败，不联网拉取、切分支或修改工作树。inputs.json列出固定来源SHA与文件SHA-256；只允许同一字节的后继文档/工具提交，不接受产品悄悄变化。

浅克隆需由同事另外明确获取清单中的固定Git对象（3eabe405、db90fdf7、22c3c0fd、420284ab、2048c60f）；本命令不执行fetch。依赖/对象缺失退出2；阶段失败/超时退出1且后续不跑，保留已跑结果；缺失不能算通过。每阶段120秒限时。预检通过只代表可运行这些限定脚本，不是隔离或启动批准。

## 实际执行（2026-11-21）

使用 `/workspace/mcis/service/.venv/bin/python`，Python3.12.14。最终完整--run退出0，总9.700秒：

|阶段|退出|耗时秒|本次用例数及范围|
|---|---|---|---|
|business_query.py|0|3.355|5，真实合成登记/临时SQLite/固定UTC查询与原审计|
|pilot_prepare.py|0|1.850|5，实际合成会话和完整政策、RA审计、原件读取及提交后待审输出|
|t100_seat_crosscheck.py|0|1.746|4，复用原实验，不改模型/单席代码|
|raw_fixture_prepare.py|0|1.699|4，原固定字节正常登记后调用原prepare回归|

四阶段包含同一既有3项业务回归，不相加宣称18项独立覆盖。check.py三项普通守门检查退出0；默认预检退出0；不带-I的实际入口退出2，未进入业务阶段。耗时是当次墙钟，非性能承诺。标准输出包含预检摘要和阶段JSON，stderr保留合成测试结果，未保存业务数据或日志制品。

## 原字节接缝（不是两端联调）

旧business.py登记 `json.dumps(doc,separators=(',',':'))`，不是Git夹具原文件。同case/UTC/point/pointer不意味着同原字节。预检实际输出：

|固定文件2048c60f|原字节SHA-256|旧compact SHA-256|
|---|---|---|
|vessel-a.json|a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c|14651f5517fcae11e3a811a559daeca8959c375eb562a8e43a47ad1a2b0893c1|
|vessel-b.json|07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca|23cce18ad385542f29979bdbca501f4fff9acefbf287256d6677707d3a2a6057|

新增Raw工装只覆盖register方法：git show固定A/B原字节，断言解析等于既有样例、SHA不同于compact，经真实preview/commit后断言receipt.sourceSha256与实际存储字节匹配。继承原prepare同案A-t100 /points/7正例及拒绝/回滚/无报告保存检查；每场景成功prepare仍仅1条Access。不是修改已登记文件或绕过完整性探针，没有假造回执。两种工装各有新临时库，旧工装保持原样。

原件SHA不是requestDigest：登记请求摘要还取决于登记元数据，不要求另一端任意登记请求的requestDigest相同。本轮没有读取或写mcis-3d；这些原字节SHA仅供未来获准两端验收核对，不声称另一端实际加载了相同文件。

## 已过和未过的门

已过限定门：真实组件登记→精确时点（已存插值/缺轨/无精确点/HDG未知）→本机单案待审引用，原件字节和Access可核对。报告快照是手造RA工装而非真实报告生成；正例显式合成LeadInvestigator，普通Investigator原政策拒绝，不提升实际账号。SQLite真实临时表与文件，原请求传输是手写替身，无HTTP。

未过：真实浏览器桌面/窄屏、账号登录、同源页面装配、3D两端连点、报告保存/绑定/导出/归档、跨进程撤权。c51c73c的浏览器命令独立且不在此入口；不重试已知坏Chromium。下一步须先具备获准的正常沙箱浏览器及可信本机会话/隔离运行条件，再按这里的同一原字节核对来源。当前不启动任何服务/镜像/浏览器/用户试点。

## 9799501 后本地先决文件守门

旧预检对未展开路径仅检查Git对象，可能显示预检通过但执行时缺本地文件。现明确要求4个入口、business.py及4个由原工装本地复制的生产文件共9项为真实普通文件，逐项匹配既有SHA；缺项、非普通文件或字节变化拒绝。不要求其余从固定Git对象物化的产品路径全部展开；inputs.json与旧产品冻结不变。此为稳定普通目录下的预检，不声称消除文件系统并发替换或实现沙箱。

普通临时目录检查逐项缺文件、目录及不匹配字节，4项guard测试通过；未运行安全漏洞探针。新入口四阶段再次退出0，总8.058秒（1.826/1.886/1.745/1.664秒），仍不累计重叠通过数。原字节闭合仅为MCIS raw登记→待审prepare；旧compact预览、模型、三维并未同跑。新工具冻结 logs/single-case-offline-local-guard-impl-hashes-frozen.txt，旧记录保留。
