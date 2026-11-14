# EXPERTDEADLINE 独立验收

21项独立pytest通过（0.05秒），冻结3/3一致。证据independent-results.txt及independent-hashes.txt。复跑：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m pytest --import-mode=importlib -q tests_acceptance/EXPERTDEADLINE/test_independent.py`。

独立覆盖5起点（原失败4194262.256341955、负起点、0及2**40/2**50量级），分别在deadline前一个nextafter、恰好deadline及后一个nextafter提交有效意见，共15场景。前一可表示瞬间接受但不提前超时；截止与之后不接受迟到意见，timed_out保留，整数elapsed在600000同侧，全部导出快照重放一致。正负1e308、2**64导致不可表示递增deadline及inf/nan起点拒绝。

另确认snapshot/export不采样时钟：只有tick/action才观察截止，不能称自主watchdog或硬取消。源码无epsilon宽限。此次通过的是注入浮点单调时钟定义下绝对deadline语义，不认证历史墙钟准确性或真实提供方执行。

无限定修复范围阻断。没有重跑父97项，不混计；未网络、模型、凭据或推送操作。原边界红测保留在父测试，不改冻结文件。可继续本地提交；Coordination组合后仍需独立确认依赖实际使用新machine，不能自动推广为进程deadline保证。真实HOLD保持。
