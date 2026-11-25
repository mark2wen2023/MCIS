W17.1@871db66：根因是测试调度（不是服务缺陷），已改测试工装；目标测试 1/1 通过，同目录 14/14，连跑 20 次 20/20 通过；产品代码未改

# W17.1：test_policy_and_audit_are_one_snapshot 的 SQLite 锁

- 执行时间：2026-11-25 13:17–13:30（北京时间，UTC+8）。Grok Bot 的 Linux 盒子，uid 1000，全程合成数据。
- 固定提交：`871db66badc6566d82239ee701958c0ef8feb558`，独立工作树 `/workspace/mcis-w17-1-871db66`（detached），先用令牌请求头 fetch，运行前 `git status --porcelain` 为空。
- 候选分支：`candidate/w17-1-sqlite-snapshot-grokbot-871db66`，提交 `340ba7cf3eed5d02174ed83630e87f3bad96f957`，父提交就是 871db66。**只改 `tests_acceptance/W171/test_workbench.py`**（+35/−7）。
- 没改产品，没触发 CI，没合并，没部署。

## 1. 第一处错误（复现）
```
cd /workspace/mcis-w17-1-871db66/service
PYTHONPATH=. .venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/test_workbench.py -k snapshot
→ 1 failed：assert 500 == 200  {"code":"INTERNAL_ERROR","message":"请求处理失败"}
```
日志：logs/01-repro-first-error.log。

## 2. 根因：测试调度，不是服务缺陷
证据：`tooling/probe_lock_timing.py` 的输出（logs/02-root-cause-probe.log）。

1. 服务端点 `access_workbench/router.py` 在读策略之前调用 `reports.access.begin()`，对 SQLite 执行 `BEGIN IMMEDIATE`，先占住写锁，保证策略和审计在同一快照里（871db66 之前是普通 `BEGIN`，写方可以在 WAL 下并发提交，这个旧用例就是在那时写的）。
2. 原测试把"竞争写入"放在 monkeypatch 的 `get_doc` 里**同步执行**。这个钩子运行在处理请求的线程上，而该线程正持有写事务。于是第二个连接的写入只能等这条请求自己释放锁，而请求又在等钩子返回，自己等自己。
3. 实测：处理线程为 AnyIO worker 线程，`in_transaction=True`；嵌套写入在 **5.01 秒**后抛 `OperationalError: database is locked`，5 秒正是 Python sqlite3 的默认 busy timeout。异常从钩子冒出去，端点返回 500。
4. 正常并发（写方在**独立线程**）：读方停在事务中时，写方被阻塞（0.5 秒后仍在等）；读方释放后写方成功，耗时 0.54 秒；读方返回 200，`version=1.0.0`、事件为空，是一致的旧快照；下一次 GET 得到 `2.0.0` 和 `['version-2']`。

结论：服务在真实并发下行为正确，写方被正确串行化，快照一致。不需要改产品事务，所以没有产品改动建议或 diff 草稿。

## 3. 改动（测试工装，保留真实并发和一致快照断言）
`tests_acceptance/W171/test_workbench.py::test_policy_and_audit_are_one_snapshot`，完整 diff 见 `candidate.diff`。
- 竞争写入放到**独立线程**（独立连接），用 `threading.Event` 确定性同步：读方读完策略后置 `reading`，等 `writer_ready`，再等 `release`；写方等到 `reading` 才开始写。不靠 sleep 保证正确性，也没有拉长超时。
- 新增断言：读方事务未结束时写方**必须仍被阻塞**（`thread.is_alive()`），证明读方真的预留了写锁；写方在读方结束后必须成功（`outcome=={'ok':True}`），不吞异常。
- 原断言**原样保留**：`(version, 事件) in [('1.0.0',[]),('2.0.0',['version-2'])]`；另外追加：下一次 GET 必须是 `('2.0.0',['version-2'])`。
- 没跳过、没放宽，权限逻辑没动。
- **反向验证**（`/tmp` 的临时副本，不在仓库里）：把端点的 `begin()` 屏蔽后，同一断言失败：`assert ('1.0.0', ['version-2']) in [('1.0.0', []), ('2.0.0', ['version-2'])]`，也就是混合快照会被抓到。日志 logs/06-mutation-check.log。

## 4. 测试结果与命令（`cd service && export PYTHONPATH=.`）
| 命令 | 退出码 | 结果 |
|---|---|---|
| `.venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/test_workbench.py -k snapshot` | 0 | 1 passed（1.43 秒） |
| `.venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/`（同目录） | 0 | 14 passed |
| 上面目标测试连跑 20 次 | 20 次均为 0 | 20/20 通过，每次约 1.7 秒（logs/05-target-x20.log） |
| `.venv/bin/pytest -q -p no:cacheprovider tests/test_access_workbench.py`（服务侧同名模块） | 0 | 33 passed |

## 5. 单独列出：归档/导出（不属于本任务）
`GET /export`（合成演示案，LeadInvestigator）仍返回 **409 ARCHIVE_RESTORE_UNSUPPORTED**（"此案未通过完整恢复预检，未生成部分案件包"）。没有处理。日志 logs/08-export-probe.log。

## 6. 未验
- 其他数据库方言；多进程部署下的锁行为（SQLite 单进程假设）。
- 全量 service 回归没跑，只跑了上面列出的目录和模块。
- 其他测试里是否还有同类"持锁线程里同步再写"的写法，没有排查。

## 7. 文件
`logs/`（00 环境、01 复现、02 根因探针、03 目标测试、04 同目录、05 连跑 20 次、06 反向验证、07 服务侧测试、08 导出探针、09 候选提交）；`candidate.diff`；`tooling/`（仓库外探针）。
