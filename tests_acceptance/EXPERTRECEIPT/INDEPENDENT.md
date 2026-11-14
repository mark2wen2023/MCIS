# EXPERTRECEIPT 独立验收

结果：16项独立测试通过（0.05秒），冻结3/3一致。receipt.py与1d5262c源文件逐字相同，AST导入仅hashlib/json/os/re/stat。证据independent-results.txt、independent-hashes.txt。

复跑：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m pytest --import-mode=importlib -q tests_acceptance/EXPERTRECEIPT/test_independent.py`。

独立覆盖：尾换行缺失、截断、空链、错误seq/previous及事件篡改，在重新绑定外层receipt摘要后仍拒绝；result及链行重复JSON键拒绝；自洽hash但错误终态也拒绝。输入自称authenticityVerified=true不会提升验证结果，unknown保持unknown，exportStatus仅verified_local_consistency；factActivated/consensusComputed=true拒绝。

写入故障：第一次短写后OSError留下5字节部分文件，但sequence/previous/file_hash不推进；零写立即失败，不无限重试。由调用方清理/标为不完整，不自动生成completion。独审未更改冻结实现。

范围符合RECEIPT_SCOPE：可信私有目录、单写者，本地一致性而非身份、模型、事实或完整业务schema。祖先链接不禁止、分文件读取非原子快照、row schemaVersion True及transportMocked类型非严格、metadata不检测秘密等限制明确保留，不能用作敌对上传/正式案件原件边界。没有导入模型/服务/进程运行器，无网络或凭据读取。

本次限定基础层无阻断缺陷，可本地提交。未重复父19自测/24路由回归，不合计为独审数量；没有整栈、真实模型或原生浏览器验收，真实HOLD保持。未来业务层需完整schema和授权验证，不继承本报告为执行许可。
