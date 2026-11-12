# W20.1 本地 LLM 人员/作业文本抽取

依据 ARCHITECTURE §15.5–15.7，第一片仅接通 people_ops；其余五角色保持 not_connected。

## 调用和数据边界

`POST /api/v1/cases/{caseId}/agents/people_ops/interviews/{recordId}:extract` 无请求体，返回 201 AgentDraft。
需 Investigator / LeadInvestigator / AgentService，且当前角色可读 testimony、可写 agent_drafts；AgentService 的 testimony 也必须可读。
配置默认禁用。`MCIS_AGENT_BASE_URL=http://127.0.0.1:端口/v1`（也支持 `[::1]`）、`MCIS_AGENT_MODEL` 均必填。仅字面回环地址，不接受域名、远程地址、userinfo、query、fragment；不跟随重定向、不读代理、不发送密钥。固定超时 30 秒，响应限 256 KiB，输入限 24,000 字符，最多 20 条陈述。使用 OpenAI-compatible `POST /chat/completions`，非流式 JSON 输出。
登记状态 configured 表示配置可用，不代表已成功推理。默认 not_connected；错误配置 invalid_configuration。网络调用仅在显式执行抽取时发生。
只发送经过 AgentService 脱敏后的 round/question/answer，不发送人员元数据、已有结论或整个案件。额外强制应用默认脱敏规则，案件配置不能减弱此出口底线。模型不得执行工具或写数据。

## 模型响应

严格 JSON：`{"statements":[{"kind":"Operation","subject":"vessel.operation","summary":"...","claim":{"valueType":"Occurrence","occurred":true},"round":1,"field":"Answer","quote":"原文逐字片段"}]}`。
kind/claim 与 interview schema 一致，其他字段不接受。引用必须在指定已脱敏问答与原始问答中均唯一出现，拒绝空引用、遮盖标记、未知问次、跨问引用。服务从原文计算 UTF-16 span，而非信任模型坐标。所有条目原子校验，不合格则不创建草稿。

## 草稿与确认

`kind=statement_extraction`、`targetEntityType=interviewStatements`、`targetEntityId=recordId`，payload 遵守 `agent-extraction` schema：recordId、sourceDigest（原始 turns 的 SHA-256）、statements（未分配 ID 的严格模型输出）。每条 citations 与条目按顺序一一对应。
生成后仅进入 PendingReview，原笔录 statements 不变。草稿记录 model、promptDigest，审计记录模型调用开始/成功/失败（摘要与错误码，不写提示词、响应或密钥）。
Confirmed / Modified 时才分配陈述 ID 并原子追加到同一笔录，extractedBy=Agent、revision=1。保留既有陈述及比对结果。再次验证权限、来源摘要和全部引用；来源变更返回 409 SOURCE_CHANGED。Modified 只能修改 summary / subject / kind / claim，不能改变来源、条目数量或引用。Rejected 不写入陈述；重复确认返回 409。现有单条 statement 草稿行为不变。
通用 POST drafts 不得提交此受控目标类型，防止冒充服务生成的可写回草稿。

## 限制

字面引用匹配不能证明模型解读正确，调查员仍必须逐条核验含义。此片不提供远程模型、API 密钥配置、自动执行或生产部署；不改变现有本地角色头信任模型。真实模型质量必须用另行安装的本地模型验收，HTTP 假服务仅验证协议与安全链路。
