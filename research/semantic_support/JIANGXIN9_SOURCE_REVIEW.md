# 第二公开案例：源页阅读与受控文本样例

## 来源与核验范围

PDF 来源记录：https://www.sh.msa.gov.cn/u/cms/www/202410/151707421728983262136.pdf

本地 PDF 实算 SHA-256：`d424673df94377cbf93cad769ca514b08a24b8a0bb552b042cc34e5149c4ff55`。

实际查看 PDF 页 8、11、12、16 整页渲染及图 6、图 13 时钟框放大图；印刷页码相同。另独立运行 pdftotext -layout 重提取四页文本。未联网重新验证 URL、未运行模型。执行本核验的AI随后参与构造下列样例，因此不能把样例标签称为独立专家裁定；投影交由另一任务独立检查。

## 原页观察

- 页 12 图 6 截图内时钟框可读 `20:55:53`、`23-10-2023`；正文写两船相距约 `3.4 海里`。
- 页 16 图 13 截图内时钟框可读 `20:55:09`、`23-10-2023`；正文写两船相距约 `3.5 海里`。
- 两图说明均写 10 月 23 日 2055 时；秒值来自AI查看截图渲染，不来自自动 OCR 或 PDF 文本层。这轮验的是明确转录的受控文本判断，不是模型视觉读取能力。
- 截图时标差 44 秒仅是时钟文字算术比较；不能自动证明设备时钟同步、距离测量与截图精确同刻，或真实动态时间间隔。约数距离不同本身不足以判定报告同刻矛盾。
- 页 8“（五）船舶载货及航次情况”第 1 项确实记为江信 9 轮 `2023 年 10 月 29 日 1648 时左右` 从厦门港离泊。
- 页 11“事故经过”确实记为 `2023 年 10 月 20 日 1947 时左右` 从厦门港离泊开航。
- 保留两段日期/时间差异，不在 sourceText 内纠错，不擅断哪段为笔误或哪段为真实日期。

## 引文及定位方式

`jiangxin9-provisional.json` 包含 8 项。采用两个联合材料包：页 12+16 的时间/距离材料、页 8+11 的离泊材料。每段明确标 PDF/印刷页和正文摘录或受控图示转录（AI查看渲染页）类别。`sourceLocator.pdfPage` 仅主定位；section 明确联合页及“非单页原始摘录”，不假称整包是某一页原文。

正文片段直接由 pdftotext -layout 输出截取，包含其换行及空白；时钟转录明确注明AI查看渲染页。Citation 取完整联合材料包，从 code-point 0 开始，长度为包全文长度，避免引用掉落来源身份。包的定位 exact 仅证明精确对应该受控材料包，不等于每个字均来自 PDF 文本层。

| 项目 | 建议标签（非专家真值） | 边界 |
|---|---|---|
| clock_elapsed | supported | 仅转录截图时钟相差 44 秒 |
| clock_same_instant | conflicted | 两个截图时钟秒值并不相同 |
| distance_proves_contradiction | insufficient | 两段约数不同不足证明同一精确时刻矛盾 |
| distance_false_precision | insufficient | 约 3.4 不提供无误差保证 |
| departure_page8_report | supported | 仅复述页 8 记载，不背书日期真实 |
| departure_page11_report | supported | 仅复述页 11 记载，不背书日期真实 |
| departure_actual_29 | insufficient | 两段不能确定真实日期必为 29 日 |
| departure_typo_certain | insufficient | 原文不一致不证明某页必为笔误、另一页必对 |

建议侧分析未加入 sourceText。待评主张本身的数字/判断是测试对象，不是额外答案提示。

## 离线校验与盲投影

沿用 evaluate.py schema 检查通过：8 项 source SHA 和 code-point 引文 exact；无需更改生产代码。用仅内存统一 insufficient 的 fixture 提交检查 schema，未存成模型预测结果。

Corpus SHA-256：`f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782`。

`jiangxin9-blind-input.json` 是候选盲投影：8 项 `case_001` 至 `case_008`，每项只含 id/sourceText/sourceSha256/sourceLocator/claim/citation，不包含原语义 ID、suggestedLabel、编写 rationale 或意见。投影 SHA-256：`56e09066bf71aa74eb786d4f6fd534458493f1122d525dd3f7427efb1a33352d`。

注意：生成投影不等于 runtime 已接入。现有第一案例 host 的 corpus pin/11 项限制不得静默绕过；第二案例需单独受控清单及独立验收后才能运行。真实模型请求次数：0。

本切片是时间/来源主张的语义支持评测，不是完整时间线抽取、视觉识别或真人专业人工核对。受控图示转录由AI查看渲染页逐字转录，不代表真人认证。
