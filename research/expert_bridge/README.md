# 有界会议与 Pi 角色的隔离协议接口

基线 `649d8656c5f5b3aca93751468c108edd73f5ce61`。只新增本目录，不改已冻结会议状态机、a686 Pi执行器、工作台或正式案件。本次没有安全凭据，**只运行离线协议单测**：不启动Pi子进程，不导入网络模型适配器，不连接服务、不读取凭据。

## 已接通的边界

`Bridge(meeting)` 独占一个内存会议实例。允许一个控制器，第二个Bridge不能对同一会议重建预算；也不能重连/恢复一个已丢失控制器。会议本身仍是simulation_only。初次绑定后，程序通过原Meeting显式开始轮次，再 `issue(role)` 取得ticket和Pi配置。

配置沿用现有 `pi-runner.mjs` 的roleId/systemPrompt/tools/model字段和初始user prompt；不复制或更改其代码。协议接收 `model / tool / done`；可传入严格单行UTF8 JSON bytes（含末尾换行），拒绝重复键、多行、坏编码、未知op、超限。结构化dict入口仅供本地控制器/测试，重新序列化复制并限额。单条含换行最多262144字节。

1. `from_runner(ticket, {'op':'model'})` 返回 **scripted_model_request**，不是网络请求；先扣一次协议轮数再返回规范化模型历史。唯一回填入口名为 `scripted_response(ticket, requestId, message)`，身份/票据不匹配即终止，不存在真实provider/endpoint/key参数。
2. host保管规范化历史与pending tool calls，Pi声明的工具必须逐个精确匹配已授权id/name/args。未知工具、变更参数、重复ID、读完工具前再次要求模型都拒绝。
3. `read_packet` 只返回固定公开包及ticket绑定的meetingContext。第一轮上下文无同伴意见；第二轮双方都获得上一完整轮的同一快照，不看同轮较早角色意见。父会议上下文变化、终止或旧票据均关闭接口。源文和其他意见是数据，不是指令。
4. `validate_review` 必须在读取上下文之后；复用固定包精确引用/完整覆盖校验，并采用会议2000字符上限。候选摘要同时绑定ticket、contextDigest和reviews。引用合法不证明语义正确，也不证明真实阅读。
5. 最终模型消息与Pi `done` 必须精确等于同一 `COMPLETED:<candidateId>`，没有未完成工具。此时**仍不提交意见**，只进入awaiting_exit。控制器显式调用 `exited(ticket, 0)` 后，先写接受尝试审计，再将经验证的模拟意见交给父状态机；只有父状态实际接受才返回completed_unverified。非零/布尔退出码、提前done/exit、取消/时限、记录失败都不能生成完成意见。

## 预算、停止与未知结局

每席次最多4次协议模型请求/8次工具，Bridge总16/32，父会议仍最多2轮4席。未答复模型请求不能再次请求或重试；新wrapper不能重置计数。它们是模拟协议事件计数，**不是已执行模型请求、实际token或账单计量**。Pi当前usage/cost占位值没有用于任何验收。

每次接口操作先检查120秒席次截止与父会议合作式600秒截止，并核对父active ticket。`Bridge.stop()`先终止父会议，再关闭未完成session。外部直接调用Meeting.stop也会在下一接口操作被观察到；迟到响应和exit不能重开会议。有未回填模型请求时失败/取消保守标unknown，绝不自动重试，但realModel/realPi始终false：本片没有真正发出提供方请求。

没有后台网络、进程或强制超时线程。本片只能拒绝后续协议操作，不能声称杀死未接通的Pi进程或取消HTTP。退出码是测试控制器提供的声明，不是操作系统采集证据。

## 可审计性与故障

`audit()`返回深拷贝元数据：ticket/context摘要、请求与工具计数、阶段、输入/输出摘要和哈希链；不返回密钥、模型正文或完整消息历史。日志失败设置auditComplete=false并终止，不因失败记录后来写成功而恢复完整标记。接受尝试事件发生在父提交前，本身不证明父接受；以父快照及Bridge状态交叉核对。父状态机的verify_snapshot可验证其转换自洽，Bridge哈希链仅记录协议轨迹，不认证执行或身份。

内存审计不具备持久性、签名、跨进程恢复或真实提供方回执。没有自动导出文件、案件写入或上传。真实执行需要另行设计进程生命周期、持久请求预算和提交失败/未知确认边界，不能把这些单测当作真实会议已运行。

## 复跑与后续

```
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_bridge research/expert_meeting
```

环境复用现有service虚拟环境。测试纯脚本构造Pi协议消息，patch子进程/网络/提供方入口为禁止，覆盖两轮冻结意见、工具授权、预算、取消、退出与审计故障；没有真实DeepSeek、实际Pi进程或浏览器测试。

下一步接入真实执行之前：为本接口的新system prompt/共享意见上下文制定新的披露摘要与显式授权；安全凭据仅留可信host，真实Pi子进程仍用净化环境和有界管道；请求前计量、未知结局停止、取消杀进程及出口受控必须独立验收。不得直接把scripted_response改名为真实响应而宣称验收通过。整个真实会议仍只可用授权公开报告，不能接未认证案件服务。
