# EXPERTVAULTCHECK 独立验收

结论：本轮文档更正与默认拒绝证据范围通过，8个独立pytest用例通过（0.08秒），3/3冻结一致。真实请求仍HOLD；不构成平台兼容或占位符接通验收。

运行：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTVAULTCHECK/test_independent.py`。结果results.txt，冻结hashes.txt。

## 独立证据

- managed、transport、isolated、worker、adapter五个运行文件与父cafffbd逐字节一致。本轮没有新增猜测的placeholder实现。
- ready字符串、合成placeholder引用、调用者ready字典均不能变成生产信任；生产platform_binding仍拒绝。
- 将managed模块的os引用替换为只含不可读合成环境对象，未修改实际os.environ；拒绝在环境读取、HTTP客户端和进程创建之前成立。不依赖允许PYTHONASYNCIODEBUG例外。
- transport/isolated均dispatched=false，isolated无worker启动，不回退旧raw-key。
- worker普通与mock入口均无成功result/transportMocked回执；mock模式的保守dispatched标志不等于真实外发。
- 静态确认旧Bearer raw-key路径仍存在，未执行该分支。文档明确HOLD不是全局封锁，不把managed默认拒绝描述成整个程序不能联网。

## 文档裁定与限制

MANAGED_PROXY顶部明确纠正旧header-injection假设并指向VAULT_BOOTSTRAP_HOLD；后者不宣称实现占位符替换，要求可信控制面/父worker绑定和回执接线，禁止从模型可写文件、环境ready或占位符前缀推断可信类型。secrets=[]被准确限制为当前实例状态，不推导用户Vault为空。

本独审遵守无网络限制，未重新访问文档中的官方网页或控制面状态工具；官方机制说明和本实例状态取自父协调者已记录证据，不作为本测试独立重取的证据。代码默认拒绝和文档与现有代码的一致性已独立核验。未读取凭据/真实环境值、未修改环境配置、未启动服务/真实模型、未推送。未来可信bootstrap、占位符实际替换、Executor与回执接线均未实现，仍须新冻结及独立审查。
