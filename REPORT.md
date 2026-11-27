# W3/5 六份盲标样本准备回执（不是正式验收）

时间：2026-11-28 05:19:18（北京时间，Asia/Shanghai）

固定基线（product pin）：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`
独立候选分支：`candidate/w35-blind-label-samples`
候选 SHA：`c826236f51485c3b380b191b86c5ef48bfb92224`
新增目录（仅此）：`tests_acceptance/W35_BLIND_LABEL/`
未改已有 fixture、产品、合同、权限、CI 或 main。未安装、未合并、未部署、未启模型、未用真案或公开报告模拟真案。

## 检索结论

在固定 `94d5e38` 及已取回的本地分支中，未找到可复用的等价待盲标样本（无「盲标 / 待盲标 / 标注模板」原件）。因此在独立候选上新准备草案，而不是改写 `InterviewCompareDemo` 或其他既有夹具。

## 样本清单

虚构案件 `SYN-CASE-W35-2026-0612`。每份 7 轮有上下文问答，固定问答 ID，船时东八区与 UTC 成对可追溯。均注明合成。草案状态：待人工复核并冻结原文。

- IR-SYN-01 陈海（P-SYN-LS-OOW），岚升二副：直接观察；须与 IR-SYN-05 同名区分
- IR-SYN-02 周平（P-SYN-LS-AB），岚升值班水手：转述
- IR-SYN-03 吴岩（P-SYN-LS-MASTER），岚升船长：记忆不确定
- IR-SYN-04 赵宁（P-SYN-LS-ENGINEER），岚升值班轮机员：近似时间与单位
- IR-SYN-05 陈海（P-SYN-QY-MASTER），青屿船长：直接观察；与 IR-SYN-01 同名不同人
- IR-SYN-06 孙牧（P-SYN-VTS-WATCH），青岚湾 VTS 值班员：转述（非登轮观察）

空白标注模板见 `annotation_template/`：证据定位、陈述类型、待查、不具可比性。JSON 的 rows 为空，CSV 只有表头。分母、争议裁定、漏提/误提口径留待评审人员先冻结，见 `POLICY_TO_FREEZE.md`。未提交期望答案、gold、自动标签或分数。

## 检查

命令：`python3 tests_acceptance/W35_BLIND_LABEL/test_blind_sample_format.py`

范围仅限格式、ID 唯一性、完整性与清单摘要。退出码：0。摘要见 `checklist-summary.txt`。

本准备不是正式验收，不是产品试点，不计算一致率。原文后续需人工复核并冻结。
