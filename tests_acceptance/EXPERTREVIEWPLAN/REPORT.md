# EXPERTREVIEWPLAN 独立验收

10项独立测试通过（0.08秒），冻结4/4一致。复跑：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m pytest --import-mode=importlib -q tests_acceptance/EXPERTREVIEWPLAN/test_independent.py`。证据results.txt/hashes.txt。

独立覆盖第二轮0/1/2席已接受意见，均只使用当前轮次，不拿已完整第一轮补缺席；完成也全部pending_human_review并保留human_review_required。失败/未知/停止/超时不关闭任务或造答案。ready round0两席均缺；不同标签与insufficient理由同时保留，不构成语义裁决。

taskId绑定精确snapshot原字节SHA+itemId，合法换JSON排版会换ID；篡改packet绑定先拒绝，修改投影locator不污染后续调用。身份/模型/共识/事实均false，原snapshot不变。

实际HTMLParser检查新问题区明确当前轮次/全部待复核/不认证审查人；历史恶意闭合标签只显示文字，无input/button/script/img/link/form等主动标签或src/href/on*属性。这里只是静态结构检查，不声称原生浏览器CSP/视觉/辅助技术验收。

只读离线问题投影范围无阻断，可继续本地提交。没有身份授权、任务持久化/关闭或执行接口；任务ID不是幂等锁/凭证。未模型、网络、凭据或推送，不混加父154测试。真实HOLD保持。
