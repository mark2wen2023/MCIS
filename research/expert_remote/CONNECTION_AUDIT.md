# 历史成功与当前受信连接差异

基线4b09333，2026-11-14。仅审公开仓库文件和安全状态元数据；未读取、复制、传输凭据，未运行旧主机/模型或探测API。精确源提交与文件SHA见connection-audit.json；历史源码逐字对照git对象，未复制整套预览栈。

## 历史记录支持什么

PR56快照254167e保存的PI_PUBLIC_UI/LIVE_RESULT.md记载5d3b415b实际Pi1.5.2+DeepSeek成功运行。对应JSONL为15个连续事件，同一runId，3次model_request_started及3次returned，最终accepted_pending_review，models3/tools2/proposals6/citations6，并有UI/归档/清理验证阶段。本审计核对的是既有记录，不重跑，也不独立认证提供方、作者或原始模型内容。

PI_SKILL/REPORT.md明确后续7dac16e4是模拟：3模型轮/2工具/1提案、providerRequests=0；旧真实5d3b运行不验证新Skill版本。不能因共用Pi版本、模型名称或仓库就继承真实能力结论。

| 项目 | 历史5d3b链路 | 当前两轮专家候选 |
| --- | --- | --- |
| 任务与材料 | YANGZE22损害摘录，PDF3/印刷1；陈述抽取 | 油量片段PDF28/印刷26，3条人工测试主张含反例 |
| 协作 | 单Pi抽取→临时working/review/archive | 两角色两轮，下一轮仅见完整上一轮 |
| 运行主机 | public-ui-host stdio临时数据库，脚本review_origin | research/expert_executor隔离Pi与provider worker，不写案件 |
| 凭据路径 | stdin raw apiKey进cfg；旧transport trust_env=True | raw-key在线已在498f807禁用；managed bootstrap始终拒绝 |
| 用户界面 | React/HappyDOM测试组件，非原生浏览器/生产认证 | 离线只读工作台+不执行的intent导出，非认证服务 |
| 回执 | 阶段/计数日志，不含当前多轮配置绑定 | schema2复合链及provider预算，仍非提供方认证 |

旧broker明确不是生产session/HTTP服务，ready输出不是用户认证凭证。其成功记录不证明当前Personal Vault存在可用绑定。旧transport允许环境代理，也不证明当时使用了现在受支持的占位符机制。

当前候选不含那套public-ui-host/service Pi依赖。它们位于PR56预览栈；复制旧脚本既缺依赖又恢复raw-key入口，不能作为安全接线捷径。旧CLI提供的apiKey输入能力也不能转换成平台信任根。

## 现在实际可用的受信路径

只有条件性路线，**没有已可运行的连接路径**：平台在对应环境请求Network secret key→用户已有Vault条目按scope绑定→平台交付占位符和受支持代理/CA→受信宿主/固定worker按可验证绑定处理→固定官方DeepSeek HTTPS:443请求→带配置与意图关联的预算/回执。实际key不得进入浏览器/Pi/日志或本仓库。官方机制见 https://learn.chatgpt.com/docs/environments/cloud-environments 。

此次environment_status仍为current，无secret/runtime变量绑定及source config引用；没有可用的worker认证bootstrap工具。只查存在性元数据，不枚举Vault、不读env值/诊断、无配置变更。不能确认其他历史测试环境与当前相同；也不能据空绑定推断用户Vault为空。

必须先由平台提供可验证的配置来源/实例与版本/目标范围/撤销与新鲜度交付。随后在独审下接worker与Executor、持久预算/幂等/取消、授权主体及intent→receipt绑定；不能手填ready、启用旧raw-key、trust_env=True或改网络策略作为替代。当前intent/preflight保持BLOCKED，没有凭历史记录授权的字段。

## 本轮离线工作

未发现可在不虚构平台绑定的前提下开启真实连接的运行修复。现有拒绝逻辑已符合该条件，因此不改生产路径。新增历史成功/模式/ready/receipt字段不能提升当前intent授权的安全回归，并核对合法请求依旧blocked及旧raw-key拒绝。历史回执只作审计证据，不能送进前置授权接口当通行证。模型能力、原生浏览器和真实平台代理仍未验；新增测试不计真实请求。
