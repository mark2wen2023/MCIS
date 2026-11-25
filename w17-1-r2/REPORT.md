W17.1@871db66 补证：已按 Dot 要求补上可观察的锁证据；目标测试 1/1 通过，同目录 14/14，连跑 20/20 通过；产品代码未改

# W17.1 补证（r2）：SQLITE_BUSY 观察与确定性回收

- 执行时间：2026-11-25（北京时间，UTC+8）。Grok Bot 的 Linux 盒子，uid 1000，全程合成数据。
- 固定基线：`871db66badc6566d82239ee701958c0ef8feb558`。
- 候选分支：`candidate/w17-1-sqlite-snapshot-grokbot-871db66`，本轮追加提交 `6b294b36d2d7279f49d3241ea660ae4191674145`（父提交 `340ba7c`，没有 force push，没有改历史）。
- **只改** `tests_acceptance/W171/test_workbench.py`（相对 340ba7c：+52/−25）。没改产品，没碰归档，没合并，没部署，没触发远程 CI。

## 1. 对应 Dot 的每一条要求

| 要求 | 做法 |
|---|---|
| `writer_ready` 在取锁前就置位，0.5 秒还活着不能证明已遇到锁 | 已删除 `writer_ready` 和“join 0.5 秒后仍存活”的断言。锁证据改为：读方已置 `reading`、事务仍开放时，**另一条连接** `sqlite3.connect(..., timeout=0)` 再 `BEGIN IMMEDIATE`，断言抛出 `OperationalError` 且信息含 `locked`/`busy`（即 SQLITE_BUSY）。该探测通过后才启动独立写方线程。 |
| 读方未断言 `release.wait()` 成功 | 读方钩子改为 `assert release.wait(10) is True`，失败时带说明。主线程同样 `assert reading.wait(10) is True`。 |
| 先观察锁，再释放读方，让独立写方实际提交 | 顺序：读方停在事务中 → timeout=0 探测 SQLITE_BUSY 并关闭探测连接 → 启动写方线程 → `finally` 里 `release.set()`，写方随后提交。 |
| 本次读为旧版本＋无新审计；下一次读为新版本＋恰一条新审计 | 见第 2 节语义说明。断言：本次 GET 响应 `version=='1.0.0'` 且 `policyAudit.events==[]`；写方加入后库中 `policy.update` 命令恰好为 `['version-2']`；下一次 GET 响应 `version=='2.0.0'` 且事件恰好 `['version-2']`；该次 GET 之后库中仍是 `['version-2']`（GET 本身不写审计）。 |
| 等待失败须报告 | 所有 `wait()` 都断言 `is True`。 |
| `finally` 释放并回收线程，join 后断言不再存活 | `finally` 中 `release.set()`，对已启动的读/写线程 `join(15)`，并 `assert not t.is_alive()`。 |

## 2. “恰一条新审计”与服务实际语义

access-workbench 的 GET 是只读的，**不会**写入 `audit_events`。新审计来自测试里独立写方调用的 `event(..., command='version-2')`（`action=policy.update`，`category=Access`，`entity_type=accessPolicy`）。`save()` 只写策略文档，不追加审计，所以竞态开始前该过滤下的审计列表为空。

因此：
- “本次读无新审计”= 响应里没有 `version-2` 事件（读方事务在写方提交之前结束，快照仍是 1.0.0 + 空列表）。
- “下一次读恰一条新审计”= 响应里恰好一条 `command=='version-2'` 的 `policy.update` 事件，且第二次 GET 不会再多写一行。

这与 Dot “恰一条新审计”的可观察结果一致，来源是并发写方，不是第二次读取本身。回执里写明这一点，测试没有为了字面凑数去改服务或放宽断言。

## 3. 测试结果（`cd service && export PYTHONPATH=.`）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `.venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/test_workbench.py -k snapshot` | 0 | 1 passed（0.87 秒） |
| `.venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/` | 0 | 14 passed（2.19 秒） |
| 目标测试连跑 20 次 | 全 0 | 20/20，每次约 1.1–1.3 秒（logs/05-target-x20.log） |
| `.venv/bin/pytest -q -p no:cacheprovider tests/test_access_workbench.py` | 0 | 33 passed（7.63 秒） |

反向验证（`/tmp` 临时副本，不在仓库里）：把端点的 `begin()` 换成空操作后，timeout=0 的 `BEGIN IMMEDIATE` **不再**遇到 SQLITE_BUSY，测试在该断言处失败（logs/06-mutation-check.log）。说明锁证据确实依赖端点预留写锁，而不是测试自己持锁。

## 4. 单独列出（不属于本任务）

归档/导出仍未处理：合成演示案 `GET /export` 在上一轮为 409 `ARCHIVE_RESTORE_UNSUPPORTED`。本轮没有重跑，也没有改相关代码。

## 5. 文件

`candidate.diff`（相对 340ba7c）；`logs/`（03 目标测试、04 同目录、05 连跑 20 次、06 反向验证、07 服务侧模块、09 新提交 SHA）。
