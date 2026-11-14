# EXPERTMEETINGMAIN 独立验收

13项独立pytest通过，冻结7/7一致。执行日志results.txt，冻结hashes.txt。复跑：
`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m pytest --import-mode=importlib -q tests_acceptance/EXPERTMEETINGMAIN/test_independent.py`。

## 核验

scripted及remote两种模式完整两轮各自验证：第一轮双方均不见同轮同伴意见；第二轮两席取得完全相同的完整上轮responses。相同标签仍same_labels_not_consensus。remote通过submit_provider_response保存的是声明，不执行提供方；完成后modelExecuted/piExecuted/identityAuthenticated/factActivated/consensusComputed全部false，快照验证通过。分别篡改三项执行/身份false标志为true，重放验证拒绝。

人工停止、failed、unknown保持不同终态，已接受第一份意见不丢失，迟到第二份拒绝。600秒时重复提交此前已接受动作仍触发timeout，不延续下一席。重复issue/精确submit不增加事件；变更重复内容、异context或模式不匹配拒绝且原快照不变。

公开packet原字节固定SHA通过；三条locator相同，条目仅claim/sourceText/sourceSha/locator/citation固定字段，无逐条参考答案字段；追加空格也因pin拒绝。claim为人工测试主张含反例，不等于逐字报告结论，README明确模型选取quote与固定citation分离、原始出处未重新认证。

独立仅复制packet.py、public-packet.json、machine.py、demo.py四文件至临时目录，python -S无site-packages运行Meeting停止/导出/验证成功，禁socket且没有engine/httpx/remote transport导入。说明此片依赖闭合，不以旧engine或服务隐藏依赖实现。

## 限制与结论

限定离线协议/来源保留范围无阻断，可本地提交。输入意见为合成，remote仅声明并非模型验收；预算为协议预留、不代表真实请求数/费用。没有真实网络、模型、凭据读取或推送。未独立重复父71/24回归，不计入13独审。原生浏览器、生产认证、桥接执行器和可信平台绑定均未接通，真实运行HOLD保持。哈希/重放不能认证来源或语义；Receipt原私有目录/单写者限制不变。
