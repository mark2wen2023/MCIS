# 第二案例真实输出逐项复核

## 范围、原件与结论

运行 `33acba11-3c47-48d3-9ab5-64f103ce0c64` 的落盘记录显示：真实 Pi 1.5.2、非模拟 transport、3 次 API 请求开始且完成、2 次工具调用、8 项预测，终态 completed；回执包含 cleanup_verified 和 node_protocol_complete。本复核仅读取这些产物和此前已查看的原页，没有再次调用模型，没有修改原预测。

结论：流程运行成功不等于语义验收全通过。发现 **1 项标签分歧**，另有 **1 项标签相同但解释越过证据的质性风险**；不得仅按标签一致宣称解释可靠、专家认定或正确率。

原件 SHA-256：

- run：`a293622ea9e9c7787e79f328ce95ab29552c60159475ceae1029b5850d9137bd`
- predictions：`73141374916ebbf72cc1003ba924b3c35516e264fc8143699b71b0857515e63d`
- comparison：`9ab281cff31c63c4ade63af231f2a3f485e2575f9fe7318529b7cd8e643e9a20`
- corpus：`f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782`

comparison 中 `realModelCalled:false` 指离线比较器自身未调用模型，不否定 run 的真实请求记录。模型输出仍标记 model_output_unverified，semanticSupportVerified/factActivated 均 false；reviewers 为空，未进行真人专家认证。

## 逐项内容审查

| itemId | 模型 / 建议标签 | 解释复核 |
|---|---|---|
| clock_elapsed | supported / supported | 对给定同日截图时钟 20:55:53 与 20:55:09 作 44 秒算术比较，有文本依据。限于时钟显示值；不能扩成两份设备记录已同步或两次实际距离测量严格间隔 44 秒。 |
| clock_same_instant | conflicted / conflicted | 解释指出秒值不同，符合输入。判断对象为截图时钟显示，不是事故系统统一标准时间。 |
| distance_proves_contradiction | insufficient / insufficient | **质性风险，不能记作解释通过。** 模型称正文 3.4/3.5 海里分别对应截图两个不同时刻，进而肯定“并非同一精确时刻”。原材料只给相邻正文约数和图中时标，未证明每个距离测量精确绑定该截图秒值。标签不足可保留，但解释把未知的正文—截图精确时刻关联当作确定事实。 |
| distance_false_precision | conflicted / insufficient | **保留标签分歧，不当作既定错误。** 模型理由抓住“约”与“精确、无任何误差”的表述不符；建议标签着眼于约数不能证明无误差，亦未证明真实测量值一定不同。两者暴露“冲突”与“证据不足”的标注边界未统一，需制定规则/专家复核，不能用建议标签当标准答案判模型错。 |
| departure_page8_report | supported / supported | 对页 8 的 2023 年 10 月 29 日 1648 时左右作报告归属式复述，符合已查看原页。未把记载等同实际真实日期。 |
| departure_page11_report | supported / supported | 对页 11 的 2023 年 10 月 20 日 1947 时左右作报告归属式复述，符合已查看原页。未擅自“修正”页 8。 |
| departure_actual_29 | insufficient / insufficient | 正确保留两段日期记载不一致及需进一步核实，没有单选 29 日为真。这里“彼此冲突”只宜理解为报告记载差异，不推定已证实哪个原始事件时间错误。 |
| departure_typo_certain | insufficient / insufficient | 解释未将明显可疑的日期差异升级为已知笔误，也未认定第 11 页一定正确，保持了核实边界。 |

## 对风险项的审查建议（不是改写模型原输出）

对 distance_proves_contradiction，更有依据的分析应为：两处距离均为约数；图中时钟文字不同，但正文距离与截图秒值的精确测量对应关系未建立。因此现有材料既不足以证明同一精确时刻距离矛盾，也不足以断言全部差异已由 44 秒解释。

此建议留在本审查文件，不覆盖模型 rationale。后续应把“标签判定”和“解释中每个关联/因果是否有证据”分轴记录；把准确的截图数值计算与未经证明的跨材料时间绑定分开。

## 不能据此声称的能力

本次输入是受控文本，截图时钟由 AI 查看渲染页转录并显式标注来源；不是本次模型自行 OCR、视觉识别、自动时间线抽取或原始 AIS 数据核验。建议标签由 AI 构造而非专家金标准；八项小样例不支持计算或推广整体准确率。

正式调查结论与事实层均未激活；没有合并原文时间、纠正报告日期或把意见包装成真人专家意见。本复核新增真实请求：0。
