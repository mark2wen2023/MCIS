# 独立出处微样本验收

先写 source-records.txt，再从其记录正文制作三张卡；sample.json、CRITERIA.json、FROZEN.sha256 在首次执行排序之前冻结。未读取旧27卡标签或改其文件。

这是独立存储的手造合成来源，不是独立机构或真实事故证据。第一张卡故意错误引用不存在的文件，但正文仍来自已冻结来源；第二张引用未证实且涉及别船的陈述；第三张引用转速为零的观察，明确不证明原因。

复跑：
```bash
python -I -B research/w19_case_ranking/source_traceability/check.py research/w19_case_ranking/rank.py
```
原排序来自 c1b988306a06e1d75f5b42c79fa1b50bd06ed596，Git blob df014103e47dcb1bb4a1115c6d05e1d4d30385c5；脚本逐字节核验，不复制或重写排序。输入仅三张Published Case、同一推进异常标签及词表。sourceBinding 是实验定位清单，不是产品schema变更。

实跑三张均由原排序以1/1返回，顺序01、02、03保持不变。独立检查得到SOURCE_NOT_FOUND、LOCATED、LOCATED。已拒绝6个变体：SHA、越界行号、记录ID、locator、摘录和正文不一致。预期答案在预测结束后才用于断言，不参与排序或定位。

LOCATED只证明固定文件字节、1起始行号、声明记录ID及引用文字一致；不证明来源真实性、对当前船/问题的适用性、支持关系或原因。三项均保持PENDING，support和causation均NOT_ASSESSED。引用成功的第二项不能自动判支持；第三项也不能从观察推导原因。未过滤召回，未计算语义precision/recall，不宣称解决W19召回。

仓库文件仅含冻结合成输入、离线验收脚本和离线路径的结果。执行验收不需要模型、网络、业务原件或依赖安装；不改产品路径。
