> 历史证据归档（2026-11-14），不是当前授权或可执行说明。未在本次归档重跑原测试/模型；旧raw-key路径已在498f807禁用，真实执行仍HOLD。来源、原始摘要和归档摘要见MANIFEST.json。

# PR57 最小依赖提取可行性 · 2026-11-14

结论：可提取为独立的离线研究工具；不需要带入PR56的97个提交。尚不能称正式工作台集成、真实浏览器验收或作者/模型来源认证。此次没有提交、推送、远端改动、服务启动、部署或新模型请求。

## 已知基线与实际隔离

- 干净main：`3aba2bf03e393909c611489ae573a887087637ac`。
- PR56依赖取自：`254167e3e957784fd9d2d136a275731f33314d9b`。
- PR57增量：上述PR56至`2104fcbeef2d1fd296b046fbf44a972c43c351e1`，排除共同REQUESTS.md和ROADMAP.md追加，保留17个功能/测试/证据文件。
- 探测目录：`/workspace/mcis-semantic-extraction-probe-20261114`，HEAD仍为main；所有提取仅未提交本地文件，不含祖先合并。
- 第二复现目录：`/workspace/mcis-semantic-reproduce-20261114`，只有清单选出的40个文件，连main生产代码都未复制。测试同样通过。

## 最小运行文件：7个

均放在`research/semantic_support/`同目录：

| 来源 | 文件 | 必须保留的作用 |
|---|---|---|
|PR56|evaluate.py|严格JSON/结构/大小/来源文本摘要/语料绑定验证；区分引用位置与语义确认|
|PR56|render_review.py|原文、模型标签/解释、来源定位和未核实声明；HTML转义及基础CSP|
|PR56|export_review.py|备注schema、双摘要模板、严格CLI导出、独占创建文件|
|PR57|render_browser_review.py|生成浏览器显式JSON下载页，固定脚本CSP哈希|
|PR57|render_restore_review.py|生成显式导入/确认/取消/清空页，固定额外脚本哈希|
|PR57|browser_review.js|读取备注/待核实标记、显式Blob下载，不声称落盘|
|PR57|browser_import.js|严格解析、双摘要绑定、全部控件预检、原子替换、取消与竞态保护|

Python仅标准库；无服务端、数据库、身份模块、Pi、模型harness、字体或网络依赖。裸模块导入要求保留同目录、按原脚本路径运行，不是现成可安装package。模板拼接依赖固定HTML/CSP结构，应固定精确版本而非自由拼配。

无内置语料也可运行，但调用者必须提供合法语料及对应预测快照。Python直接函数相信调用方传入摘要；可复核入口是CLI重新读取原文件并计算摘要。不得直接包装成信任远端自报摘要的API。

## 验收资料与出处清单（不属于运行依赖）

原有回归需要PR56的6个测试：`test_evaluate.py`、`test_evaluate_independent.py`、`test_render_review.py`、`test_render_review_independent.py`、`test_export_review.py`、`test_export_review_independent.py`。特别是PR57测试引用了`test_render_review_independent.py`中的Parser。

6个固定资料：`yangze22-provisional.json`、`fixture-predictions.json`、`empty-review-template.json`、`jiangxin9-provisional.json`、`jiangxin9-real-predictions.json`、`jiangxin9-research-review.html`。

建议一并携带约束文档`CONTRACT.md`、`REVIEW_PAGE.md`、`EXPORT_REVIEW.md`；携带历史预测样例时保留`JIANGXIN9_SOURCE_REVIEW.md`、`JIANGXIN9_BLIND_RUN.md`、`JIANGXIN9_RESULT_REVIEW.md`、`jiangxin9-real-run.json`、`jiangxin9-real-receipt.jsonl`作出处背景。它们只是历史材料，本轮未重新运行模型、重新下载PDF、独立认证历史receipt，也未带入原盲测harness。样例`model_output_unverified`状态不得升级。scripted_fixture保持明确标注。

以上23个PR56文件及17个PR57文件的精确路径、来源提交、SHA256分别见`dependency-manifest.json`和`pr57-manifest.json`。这些是可复现的完整测试选择，不声称40个全部都是最小运行必需文件。JSON不得重排/格式化，原字节摘要必须保持。

## 必须随提取保留的安全边界

1. CSP禁止默认资源、网络与表单；脚本仅允许实际字节的SHA256。保留HTML/script安全转义，不添加任意script-inline许可；来源URL作为声明而非自动访问。
2. 备注必须同时匹配语料和预测原字节摘要；来源片段hash与Unicode码点定位单独验证。位置exact不是语义/事实正确，双摘要不是数字签名/作者认证。
3. 导入4MiB上限、严格UTF8、拒绝BOM/重复键/未知字段/非整数schema版本/超深结构；条目完整且唯一，布尔标记、4000码点备注，待核实标记必须填写原因。
4. 选择/校验不覆盖已有编辑，明确确认才替换；失败/取消不破坏备注，代次令牌忽略迟到读取，编辑使待导入/清空失效。重复导入替换而非累计。
5. 备注状态始终`unverified_research_notes_not_case_facts`，不认证身份，不自动确认事实，不写入案件或自动上传/持久化。未勾选不表示核实。
6. 浏览器只承诺请求下载，不承诺磁盘保存；CLI独占创建0600文件，不覆盖既有输出。清空页面不删除已下载文件。

## 实测与复现

- 仅加入3个运行依赖后，原测试因缺Parser和样例数据发生3项收集错误，证明测试依赖必须单列；日志`runtime-only-test.txt`。
- 完整选择：`PYTHONPATH=research/semantic_support service/.venv/bin/pytest --import-mode=importlib -q research/semantic_support tests_acceptance/SEMANTIC_BROWSER_EXPORT`，**122通过**，日志`extracted-tests.txt`。
- 单独7文件烟测：`python -S`禁用site-packages，socket.socket替换为拒绝，实际生成恢复页成功；文件权限0600，重复同输出路径返回2且原字节不变。结果`seven-file-smoke.json`；运行文件副本与生成页保留在本证据目录。
- 以源码提交和SHA清单重建纯文件目录再测：**122通过**，日志`reproduced-tests.txt`。使用当前venv Python运行：

```sh
/workspace/mcis-local-export/service/.venv/bin/python \
  /workspace/mcis-semantic-extraction-evidence/reproduce.py \
  /workspace/mcis-semantic-extraction-probe-20261114 \
  /tmp/mcis-semantic-fresh-reproduction
```

目标目录必须尚不存在；脚本只执行本地git show读取固定提交、校验hash、写新目录和运行离线测试，不进行git提交/网络/模型请求。需pytest和Node可执行文件，运行工具本身不需它们。

独立只读代理使用git show和AST再次确认7文件依赖闭合及安全约束，无生产依赖。已通过的是实际生成脚本的DOM/文件适配器和CLI测试；未证明真实浏览器的文件选择、下载落盘、实际CSP执行或布局。当前环境前次开启沙箱的Chromium启动因SUID配置失败，不绕过。

## 建议后续

如获授权创建main候选，只导入清单文件，重新记录REQUESTS/ROADMAP与新冻结；不要retarget现有PR57带入PR56祖先，也不要顺手引入blind_host/runner/Pi配置或生产服务。必须先完成受支持浏览器验收再扩大产品承诺。要挂载正式工作台或认证主体，应另立合同与权限审查，不能借本次离线依赖闭合跳过。

附件候选bd34b83保持暂停：主协调者的新独审确认父目录symlink竞态及提交最终授权后撤权缺口。此次未修改或发布附件候选；其最小安全依赖需另一开发线修复并重验，不受本研究工具可提取结论影响。
