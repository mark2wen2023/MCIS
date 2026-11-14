# EXPERTCOORDINTEGRATED 实际组合独立验收

通过：实际当前候选合跑139项，0.86秒。包括原19receipt开发/16receipt独审、Meeting相关模块、21独立deadline、10独立coordination及4新增组合边界；不要把二次采样3项另加总数。证据independent-results.txt。

来源：从原两个源目录的Git对象ced79f561821fe274e7916910a37750da76ebc84与d26314b196c22608bbb57baf933abf5941ebe4a1读取各自改动文件，排除明确手工追加的REQUESTS/ROADMAP，其他每项与组合工作区逐字相同。原红断言及失败日志均保留。详见source-check.txt。组合目录本身无源提交对象，最初本地git查对象失败后改用已有源目录只读git show，未fetch或新增Git依赖。

运行时确认Coordination.Meeting就是当前组合目录machine.Meeting。两源有效冻结各3/3以及组合冻结4/4均一致，见independent-hashes.txt；旧pre-r1冻结仅历史证据，不冒充当前有效冻结。

合跑包含fractional start4194262.256341955的4公共边界：截止前nextafter保持pending；恰好start+600变timed_out且pending未知，不能升级returned。原二次采样NaN(stop/failed/unknown)三红断言同时通过。跨轮预算16/32、竞争仅一pending、精确重复幂等和多起点重放测试均实际使用组合依赖通过。

因此此前独立Coordination报告中“截止依赖未提取/未修”这一具体阻断在本组合关闭，不等于解除真实执行HOLD。gate仍合作式、无watchdog/硬取消/原子网络许可/认证，Python私有属性不构成敌对边界。未模型、网络、凭据或推送；不改冻结实现。此组合离线范围无剩余阻断，可按父明确授权保存独立分支。

复跑：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m pytest --import-mode=importlib -q research/expert_meeting tests_acceptance/EXPERTRECEIPT tests_acceptance/EXPERTDEADLINE tests_acceptance/EXPERTCOORDINATION tests_acceptance/EXPERTCOORDINTEGRATED`。
