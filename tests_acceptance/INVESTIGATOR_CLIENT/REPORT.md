# 可信 host 调查员试验客户端：独立验收

独立审查者未改产品，新增 test_investigator_client_independent.py 20项。
最终独20+主3：23 passed、零跳过、13.37秒。设置实际W2命令后包含主测试
actual_w2_runnable_client，走真实本地W2；其余采用受控计算夹具。不是23次W2。

```sh
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh \
PYTHONPATH=investigator-client/service mcis-work/service/.venv/bin/pytest -q \
 investigator-client/service/tests/test_investigator_client.py \
 investigator-client/service/tests/test_investigator_client_independent.py --disable-warnings
```

## 实际发现与修复

首9项8通过1失败：选择的受保护目录GET已完成、延迟交付期间调用close，随后
select将closed重新改为selected并分配operationId。扩大到18项仍17通过/1失败。
实现者增加独立closed终态、在await之后检查并防止异常处理覆盖closed。
修复版18/18通过。再增加保存/读取响应期间关闭两项，最终23联合全过。
关闭后的late response不恢复选择/结果；已在服务器提交的记录保留，不声称关闭回滚。

## 覆盖

- 保存响应丢失后outcome-unknown保留同operationId，重试只得到一个保存记录。
- 选择请求及返回的pins均与外部可变对象隔离；双execute拒绝第二个，忙时clear拒绝。
- 选择后会话撤销、成员失效、原件改变拒绝，无保存；读取403保留已知runId，可单独重读。
- 保存取消进入unknown，原operation可重试；关闭期间select/save/read均保持closed。
- 服务端pins的案件、代次、epoch、登记digest、来源incarnation、额外字段、缺项不匹配
  都在计算之前409拒绝，零保存；已保存同operation带不同pins也不得重放。
- HTTP异常中的虚构token/path不出现在客户端错误文本。客户端公开receipt、返回值与repr
  不含token由主测试覆盖。不意味着Python调试器、宿主日志或内存转储的秘密保护。

## 边界

固定内存ASGITransport，客户端不能指定远端URL；不挂旧应用、不使用role/operator头。
账号由可信测试host直接配置；创建案件/登记原件仍用旧测试fixture。故这里只验证准备好
数据后的受保护目录→选择→计算保存→读取，不是整个工作台真实认证E2E或生产登录。
无浏览器、socket网络、IdP、LLM、实际UI操作、部署或全系统验收。
expectedSelection是可选的版本前置条件，不是权限或审批凭据；新客户端始终提交，旧调用
仍可不提交。类型错误可能由DTO422拒绝，值/字段不匹配由409拒绝。案件及来源权限仍另验。
单源虚构CSV不证明独立证据互证；父报告客户端正向实物链路不是这23项新增验证的范围。

未发现最终本切片剩余阻断项。未推送、合并或部署。

## 最终产品SHA-256

- identity/trial_client.py: 36f22366bdebbdbfefcb8ba135ce75769e7fbc2f7244474ea67222c940e1d41e
- identity/http_trial.py: a21c3df966cb522c52e9f4b96edd7fd0f0bccac9ff893f9d57beb527ecf547bb
- timeline/unreviewed_storage.py: 9cbcf54e418aea49854d389b8620bef1552ed0f78134f01a3cff699201755ac4
