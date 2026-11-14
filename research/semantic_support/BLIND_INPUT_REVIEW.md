# 盲测输入独立内容核验

范围：源数据投影与送往模型的上下文/工具反馈；不修改实现，不调用真实 API，不认证专家身份或语义答案正确性。

## 核验结论

当前投影无答案泄漏阻断：11 项完整覆盖，按顺序使用 `case_001` 至 `case_011`，没有原语义 ID。每项仅 `id/sourceText/sourceSha256/sourceLocator/claim/citation` 六字段。后五字段逐项与 corpus 深比较一致，包括故意篡改引用的负例，未悄悄修正。两项 null 建议标签对应的 case 仍保持相同字段形状，没有 null 标识、特殊分组、跳过或额外提示。

- `suggestedLabel`、编写者 `rationale`、原语义 ID、fixture 预测及专家意见均未进入投影。
- Python host 才持有实际 provider messages；Node Pi 的独立上下文不等同于 provider 上下文。核验覆盖 Python 实际传入 transport 的每轮 messages。
- 读取工具返回完整盲投影；验证工具仅回复 schema/coverage 结果及 `semanticSupportVerified:false`。
- 原语义 ID 映射只在最终 host 输出恢复，没有回填到之后的模型请求。
- Host 的内部 corpus 完整性检查可读取建议标签，但结果不反馈逐项语义吻合情况；验证提交不比较建议答案。
- 固定系统提示包含通用审读规则（约数、主体、空白不等于否定、指令不等于实际执行、不能仅凭引用推导因果）。因此这是带方法提示的答案隐藏评测，不是无提示零样本实验。通用三分类枚举和模型自己的 `label/rationale` 不是泄漏的标准答案。

## 独立离线检查

新增 `test_blind_input_independent.py`，2 个测试方法通过：

1. 覆盖 11 项 opaque 编号、字段白名单、sourceText/hash/locator/claim/citation 深比较和两 null 样例保留。
2. 注入纯内存替代 transport，分别让全部 11 项提交 supported、conflicted、insufficient 三种极端统一标签，捕获每种流程全部 3 轮 provider messages 和工具结果。三者得到完全相同的 schema-valid 回复，没有答案分数、逐项纠错或建议标签反馈。并检查无原 ID/原 rationale/fixture/专家意见。

此测试通过注入 transport 检查远端分支组装的上下文；只使用测试占位 key，没有执行 `_http` 或 `remote`，不得将分支中的 `realModel` 元数据当成真实模型运行证据。

另独立复跑 `node --test blind-runner.test.mjs`，6 项 fixture 检查通过；同样 0 次真实 provider 请求。Node CLI 静态检查未读取或注入答案数据。本报告不替代收尾协议、持久回执、安全限额及异常处理的单独审查。

核验 corpus 原始哈希：`77cdbdf3f2656aa57b0772fadc909671bf5bbfbd7c480a3fcbb1cc79460ad19b`。
