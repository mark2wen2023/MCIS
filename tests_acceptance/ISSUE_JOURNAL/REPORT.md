# 问题卡递进记录：独立验收

独立审查者未修改实现，新增 test_issue_journal_independent.py 18项。
最终与主测试11项联合：29 passed，零跳过，15.71秒；一项既有Starlette/httpx警告。

```sh
PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q \
 issue-journal/service/tests/test_issue_journal.py \
 issue-journal/service/tests/test_issue_journal_independent.py --disable-warnings
```

## 初始化问题及修复

静态审查发现初稿Event/Grant继承全局db.Base。导入journal后，旧Database.create_all
会创建问题表但不安装其专用追加保护触发器，违反显式初始化边界。实现者改为独立
JournalBase metadata。独立测试确认旧factory不自动创建两表。旧版在测试启动前已修改，
因此此问题是静态发现，不称已执行旧版失败复现。

## 独立覆盖

- 创建权限独立于原保存grant；取消问题write grant后仍可按当前案件/完整内容权限读取。
- operation重放绑定真实主体：另一有授权subject用相同operation与内容得到409。
- 同operation并发两次：一次新增、一次幂等重放，仅一事件；不同operation同revision
  并发：一成功、一409。
- 注入Session.commit失败：事件不落库，恢复后同操作可重新成功且只保存一次。
- 原件在末次source_current时变化：409并回滚刚flush的事件。
- 最后授权时撤销session/grant/membership：403并回滚。
- read/list在末次授权前会话到期：无结果返回。
- 来源后来变化，旧操作可历史重放，不重新声称当前源有效；历史marker明确。
- 新判断出现后旧核实不能解锁讨论；必须核实当前最新判断。
- 伪造approved、role、authorSubjectId输入由strict Entry拒绝，未落库。

主测试另覆盖判断→反证核实→新判断→再次核实→讨论的旧判断保留、DB UPDATE/DELETE
触发器拒绝、初始非判断拒绝、跨案拒绝、源损坏及基础幂等。统计有重叠，不是29种
互不相关的生产验收。

## 边界

真实本地SQLite、临时登记文件、Python服务callable；新模块不挂HTTP/浏览器。
主/独本套不运行W2/LLM/实际UI或生产登录。并发验证是同进程线程/SQLite，不是多节点。
账号及IssueGrant由可信host配置；正文是提交主体的工作意见，不证明真实真人或专家背书。
append-only由服务接口和本地触发器约束，不抵御有权修改数据库/触发器的管理员。
source snapshot只是记录时历史信息，读取/重放不认证当前原件；没有事实批准或正式时间线准入。
目前没有问题卡归档/恢复整合，也未验证原归档包含这些新数据；不能宣称完整备份。

未发现最终切片剩余阻断项。未推送、合并或部署。

最终 journal.py SHA-256:
9ad54de4acf7c787819efc7af33b3618f7c2ef1502cef9e923e2933f9abe1a4f
