# 引用能定位，不等于主张被支持

这是一个可运行的离线业务评测切片，不是自动事实裁判，也不是已认证的海事专家金标准。公开报告原文是真实来源；主张、反例及建议标签由 AI 助手构造，仍待两名业务专家独立核实。工具不会调用 LLM、联网、读取案件数据库或激活事实。

## 两个轴分开

1. **定位轴**：检查给定 UTF-8 页文本的摘要，以及 Unicode code point 区间是否逐字等于引用。不是现有笔录 API 的 UTF-16 坐标，也不自动核验 PDF。
2. **支持轴**：逐项展示外部预测、建议标签及理由。`supported` / `conflicted` / `insufficient` 只讨论给定引用是否支持主张，不代表真实世界事实已核实。没有确定建议的样例为 `null`，不会强迫分类。工具不计算准确率、不以标签一致作为专家认证。

## 11 个公开报告样例

来自上海海事局 YANGZE 22 / VEGA DREAM 报告，印刷页1、22、25、26已作图像核对；语料具体使用22、25、26。PDF SHA-256：`99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f`。见 `SOURCE_REVIEW.md`。

- 保留“报告认定”“约171.053吨”的支持例；强化成精确无误差的不足例；错认泄漏船的冲突例。
- 仅删“约”而没有强化精确性，保留建议标签待定，不武断认定真假。
- 表3的舵角指令右18°与实际反馈左33°正确分列，以及混列反例。
- 空白不等于“有口令”或“没有口令”；单行信号差异不能直接归因液压故障。
- “报告认定事故发生前工况正常”必须保留来源归属和时段范围。
- 引用171.053故意篡改为171.503，必须先在定位轴失败，不能由语义标签掩盖。

页文本取自 `pdftotext -layout`，保留空白及换行。代码验证的是提供的页文本内部一致性，不是 PDF 来源真实性；输出 `sourceLocatorVerified:false` 不应改成 true。独立源页复核由另一个 AI 子任务完成，不冒称真人专家。

## 运行

在仓库根目录：

```bash
python research/semantic_support/evaluate.py \
  --corpus research/semantic_support/yangze22-provisional.json \
  --predictions research/semantic_support/fixture-predictions.json \
  --reviews research/semantic_support/empty-review-template.json
```

自带预测是 `scripted_fixture` 固定输出，只验证接口，不是模型结果。外部模型输出须显式写 `origin:model_output_unverified`，且绑定原语料文件的 SHA-256；这个声明不认证模型身份或来源。CLI 不调用模型、不替任何既有模型结果背书。错误输入返回固定错误和 exit2，不回显输入。

## 后续两名业务专家复核

先分别提供相同原页、主张和引用，让两位专家独立给标签及理由，再由有权人员整理进审核 JSON；不要提前把一人的意见展示给另一人。当前切片不提供盲审系统，不能技术证明独立性。

`empty-review-template.json` 当前明确为空，尚无专家意见。最多两份不同 reviewerId 的记录；同一 ID 不能占两席，每人每样例一条意见。保留双方意见、分歧、身份及资格自述，不自动投票形成事实。`scripted_test` 始终是脚本；`user_submission_unverified` 只是人类提交的声明，身份/资格/独立性均未认证。两个不同 ID 不证明两名不同真人。离线 JSON 可编辑，不是防篡改审计；修改意见应另存版本并人工保存来源。

此切片尚未接入生产 UI、Pi 工具回路、专家会议或正式事实审批；不能用建议标签直接惩罚模型、训练模型或产生已认证准确率。后续应由业务专家复核样例和边界，再安排真实模型盲测。

## 已完成的一次真实能力试验

在独立安全验收后，使用真实 DeepSeek API 与官方 Pi1.5.2 跑了一次固定公开样例，3次请求、2次工具、11项输出。模型只看到opaque编号及公开原文/主张/引用，没有建议标签、理由或专家意见。见 `BLIND_RUN.md` 与 `blind-real-*` 文件。这是未认证模型预测，不是专家真值；发现“与来源冲突”和“材料不足”的边界仍需打磨。模型能力结论只来源于这次真实运行，fixture仍只作协议/安全测试。没有新增专家意见或自动事实判断。

## Second public case: time and provenance claims

The fixed `jiangxin9-v1` profile adds 8 answer-hidden public-report claims without changing the original Yangze22 profile or execution manifest. See JIANGXIN9_BLIND_RUN.md, JIANGXIN9_SOURCE_REVIEW.md and JIANGXIN9_RESULT_REVIEW.md. One real Pi/DeepSeek run completed 3 requests/2 tools; no retry. This evaluates supplied controlled text, not model vision or complete timeline extraction. One provisional-label disagreement and one matching-label but unsupported rationale association remain for review; no accuracy or factual certification is claimed. Raw outputs and receipt use jiangxin9-real-* filenames.

## Offline explanation review sheet

`render_review.py` creates an isolated static research page from strictly validated corpus/predictions, separating label and rationale from citations and source declarations. All review boxes start empty; notes are temporary unsaved browser state, not authenticated or durable review. See REVIEW_PAGE.md and REVIEW_PAGE_INDEPENDENT.md; an actual 8-item second-case HTML artifact is included. No new model call or production connection.
