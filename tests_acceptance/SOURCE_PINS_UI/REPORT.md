# 选中来源版本绑定：独立 TS / UI 验收

## 最终结果

新增 issue-source-pins-independent.tsx：22项检查通过，退出0。
最终既有回归：主 issue-workspace.tsx 流程通过；issue-workspace-independent.tsx 29项、issue-sources-independent.tsx 24项、issue-host-independent.ts 15项全部通过；严格TypeScript产品三文件检查通过，均退出0。

真实跨语言链路 issue-host-integration.tsx 通过：React/HappyDOM读取两份已登记虚构CSV、选择EV-001，提交五条工作记录，重新读取；经过TS hostPort、Node stdio、Python受保护ASGI、临时SQLite。不是生产浏览器IPC、真实登录、部署、LLM或真实事故案例。

## 新增覆盖

- 带sourceIds但无pins、pins重复/数量不符、ID顺序不匹配、损坏hash/代次UUID、pin额外字段均在send前拒绝。
- 来源候选缺失/非字符串/错误形态sourceIncarnation拒绝。
- send直接抛SourceSelectionChanged不能伪装成已关联的明确服务器拒绝。
- requestId/contextId/caseId/status/productionLogin错误关联不会变成typed source-conflict。
- 只有精确关联的ok=false、409、ISSUE_SOURCE_SELECTION_CHANGED变成typed异常。
- 明确来源冲突保留意见、清清单/选择/旧操作、允许重新选择；无未知重试按钮。
- 未知响应丢失时，同操作重试保持原operationId、完整payload及sourcePins，清UI选择不能改变冻结请求。

## 语义检查与边界

独立审查提出：响应丢失后的同op重试不可把此前已成功提交说成“未写入”。实现者确认后端优先查同op原pins历史成功并复核权限，成功后来源再变化仍回原成功；改pins重试为普通冲突，不触发精确source-change分支。该后端行为由父任务独立Python测试覆盖，本TS报告不伪称另行执行该Python测试。

任意自定义JournalPort仍由可信host承担语义契约；本组件与错误类型本身不是身份认证，也不是防恶意同进程代码的边界。绑定的是选择时的原件SHA/本地来源代次，不证明内容事实、时钟准确或责任认定。

## 审查者文件修改

新增 web/tests/issue-source-pins-independent.tsx；更新 web/tests/issue-sources-independent.tsx 的虚构候选fixture以包含sourceIncarnation；新增本报告。未修改产品，未推送/合并/部署。

## 冻结 SHA-256

- model.ts: 41562430119661c7551d572e41cdb08cafd5dddfd37aa60bb863b5e934a5b9cf
- hostPort.ts: 288e93825ac83bde4741710823f07e95c9c1fc0686c879360a44d4da0f7780bd
- IssueWorkspace.tsx: 6d146a0e2a5fe1a278151bc439fcce29c951f810f84254796d19f84c9ea980bf
