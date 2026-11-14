# 来源选择 UI 独立验收

## 最终冻结结果

最终修正版全部命令退出0：
- 新 issue-sources-independent.tsx：24项检查通过。
- 既有 issue-workspace-independent.tsx：29项检查通过。
- 既有 issue-host-independent.ts：15项检查通过。
- 既有 issue-workspace.tsx 主DOM流程通过（不伪造检查项总数）。
- issue-host-integration.tsx 真实跨语言链路通过：React/HappyDOM勾选EV-001，经TS port/Node stdio/Python受保护ASGI/临时SQLite保存五条工作记录并重读。
- model.ts / hostPort.ts / IssueWorkspace.tsx 严格TypeScript检查通过。

计数为脚本检查项，运行间可重叠，不表示完整系统或CI测试数。

## 覆盖与修正

来源封套错案件、重复ID、无效hash、unsupported类型、负字节数、无效日期拒绝；仅投影白名单字段。显式加载候选、勾选后command.sourceIds包含选项；刷新来源清空选择，加载失败清清单/选择，旧异步回包在context变化后不显示。20项选择上限、断连清空、无local/sessionStorage写入。

审查建议并经父任务明确授权修复：保存结果未知或历史刷新失败时隐藏来源清单与选择，不能在潜在撤权后继续展示旧元数据；冻结pending command保留原sourceIds、operationId与内容，同操作重试不被清空选择影响。独立验证失败后来源清空及重试原引用保持。

审查者另补checkbox函数式更新中的去重与长度上限，避免只依靠DOM disabled状态。此项为静态加固，未声称运行旧版绕过复现。

真实链路旧add辅助函数取首button，新增来源按钮后会误点。已修为按“追加记录，不覆盖历史”文字定位，并增加真实候选加载/勾选和历史EV-001断言。主DOM/旧独立DOM均按文字定位，本次未改其文件。

## 文件与边界

审查者修改产品 IssueWorkspace.tsx（仅上述失败清理/选项保护）；新增 issue-sources-independent.tsx；修改 issue-host-integration.tsx；新增本报告。model.ts、hostPort.ts由实现者修改，Python来源功能另由对应子任务验收。父任务应复核审查者所作产品改动，不把本报告当作完全无修改的黑盒独立审查。

来源为fixturehost直接登记的两份虚构CSV，不是真实案件。最终链路不是公网/真实浏览器IPC、登录/IdP、生产部署、LLM或图像视频解析。候选清单是受支持当前本地项，不是案件全部证据；选中时hash未钉住为保存前置条件，服务端保存时重核并记录当时快照。来源引用不代表已读原件、事实核实或定责。

## SHA-256

- model.ts: e59616a1eab445b1b6c892f06bf7b10eb11cb3646cd79257ca78f9bca1838cab
- hostPort.ts: fc6d48ddd2281cd3edaf40e9680c30d47976c50a1f67060cd44a3ab98a02fac6
- IssueWorkspace.tsx: 7116c147aeda0e80c18f0a0e0e133a26e9e6de68ca7133e84411fa58f2fb6c63
