# 海青君单席：T+124.25 离线核对研究

基线 `afc72a1180ae345556a85fb63a4020a476893d14`，独立候选，不接队列、Pi、模型、UI、路由或业务保存。只交两个研究脚本和本说明，不跟踪生产源码/JSON副本。

## 准备与复跑

在具备已批准离线 Python 3.12 + jsonschema 的 MCIS 检出目录运行（不安装）：

```sh
/workspace/mcis/service/.venv/bin/python -I research/haiqing_single_seat/check.py
```

其他本机可用已有合格解释器替换绝对路径，仍须 `-I`。脚本不会联网/fetch；必须已有以下完整提交对象。缺对象、路径或blob不符即退出非零，不改取latest，不补下载。浅克隆需要先由使用者通过批准流程准备这些固定对象，脚本本身不准备网络依赖。

|来源|文件|固定Git blob SHA-1|
|---|---|---|
|420284ab5fd44c94b737f8c1cf51bc0ef09aea29|research/expert_group/packet.py|ff2018dad2d58e9fe158f503ecd71a004c20e226|
|0dc1226364524977a4155e480d96436443cd8967|service/mcis_service/trajectory_exchange/registered_query.py|a7a5a12294308395413af75de1837de284a94a1c|
|同上|service/mcis_service/trajectory_exchange/validation.py|cd1be59c2c74327ca5468eab06d1461c71ad0afe|
|2048c60fd6650c6f2c99a76a16be463a3895655d|tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-a.json|d8e132c566f07004d76227af52745d5b5ad943c4|
|同上|tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-b.json|7b332f3af0acbe9d5260fca88b889de95c5279c0|

先核对Git条目是100644普通blob，再用`git show ref:path`取字节，逐份重算Git blob SHA-1（含blob长度头）。全部核验后在自动清理的临时深层目录普通import；保留validation.py原始相对路径计算，不修改源文件。仅调用 `_stamp` / `_point_from_committed_original` 与 host `_validate`，不调用V1 schema读取/全量校验、登记/授权原件读取、公共packet文件读取或生产app。临时包名仅解决相对import，不替换生产逻辑。

## 实际范围与可靠性

实跑5项退出0：固定缺口/明确无行生成待人工核对意见；错案/错时/借pin及改身份/颠倒顺序；无行不得借邻点或另一船缺口；真实host validator拒绝借quote/跨item/额外scope字段；host形状校验通过但越过本题固定文字仍拒绝。

- A/B预期身份独立写为SYN-VESSEL-A/B和SYN-E-A/B，不从模型参数或待验frame反推；固定文件也先检查同案与船ID。
- frame由本地固定投影生成，trusted_pins由工装自造；handoff的模型候选参数只含reviews。试图在该参数加入frame/trusted_pins由真实host validator拒绝。本模块未注册成工具；Python调用者能传关键字不构成安全授权边界。
- pin里的requestDigest是明确的合成夹具摘要，**不是实际登记回执**；sourceSha256是固定合成JSON字节的摘要。身份/pin均不等于真实授权或来源真实性，不声称读取了生产“已提交”批次。
- A只保留 `/sampling/missingIntervals/1` 的本地缺口定位；B无精确行，对应reference为null。缺口不是轨迹点，不借相邻T+125行。
- review packet只有两个短sourceText和itemId，不包含原件全文、pin或pointer；本地handoff结果中的reference不能直接展示/保存为已核验事实。
- rationale/uncertainty精确固定文字只适用本题T+124.25，不是通用语义检测，也不声称模型已认知“不足”。结果固定pending human review、factActivated=false、saved=false。

首次本轮运行曾因临时路径浅于validation.py的parents[3]要求而退出1；只修临时目录层级，随后5项通过。没有变动固定输入或源规则。未调用任何模型、服务、ORM、网络API；没有业务表写入、报告绑定、产品认证、端到端或人工批准。
