【Grokbot｜W17.1｜待复核】

**W17.1@871db66：根因是测试调度，不是服务缺陷；已修测试工装。目标测试 1/1 通过，同目录 14/14，连跑 20 次 20/20 通过；产品代码未改。**

— Grokbot

### 版本与环境
- 固定提交 `871db66badc6566d82239ee701958c0ef8feb558`，独立工作树，运行前 `git status --porcelain` 为空。
- Python 3.13.5，pytest 9.2.0，SQLite 3.46.1，Linux 盒子；只用合成数据。

### 根因
- 端点 `access_workbench/router.py` 在读取前通过 `begin()` 执行 `BEGIN IMMEDIATE`，先占写锁以保证策略与审计同一快照。
- 原测试把竞争写入放在 monkeypatch 的 `get_doc` 里同步执行，运行在持有写事务的请求线程上，等于自己等自己；实测 5.01 秒（sqlite3 默认 busy timeout）后 `database is locked`，端点返回 500。
- 正常并发（写方在独立线程）：写方被阻塞，读方提交后写方成功（等了 0.54 秒），读方得到一致的旧快照（1.0.0、无事件），下一次读到 2.0.0。服务无需改动。

### 改动
- 候选分支：https://github.com/mark2wen2023/MCIS/tree/candidate/w17-1-sqlite-snapshot-grokbot-871db66（提交 `340ba7cf3eed5d02174ed83630e87f3bad96f957`，父提交 871db66）。
- 只改 `tests_acceptance/W171/test_workbench.py`（+35/−7）：竞争写入改为独立线程，用 Event 确定性同步；新增"读方事务未结束时写方必须被阻塞"和"写方最终成功"的断言；原一致快照断言原样保留，另加一次后续读取必须是 2.0.0。没有跳过、放宽或拉长超时，也没动权限逻辑。
- 反向验证：在临时副本里屏蔽端点的 `begin()`，同一断言失败（`('1.0.0', ['version-2'])`），说明混合快照仍会被抓到。

### 测试与退出码（`cd service && PYTHONPATH=.`）
| 命令 | 退出码 | 结果 |
|---|---|---|
| `pytest -q ../tests_acceptance/W171/test_workbench.py -k snapshot` | 0 | 1 passed |
| `pytest -q ../tests_acceptance/W171/` | 0 | 14 passed |
| 目标测试连跑 20 次 | 全 0 | 20/20 |
| `pytest -q tests/test_access_workbench.py` | 0 | 33 passed |

复现旧错误：在 871db66 原样运行第一条命令，得到 `500 INTERNAL_ERROR`。

### 单独列出
归档/导出：合成演示案 `GET /export` 仍返回 409 `ARCHIVE_RESTORE_UNSUPPORTED`，本任务未处理。

### 未验
多进程部署下的锁行为；全量 service 回归；其他测试里是否有同类写法。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-1-grokbot-871db66/w17-1
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-1-grokbot-871db66/w17-1/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-1-grokbot-871db66/w17-1/mcis-w17-1-report.tar.gz
- SHA-256：`89922d25511673f20f72e159fa153d13525aae9aef8e6d60aa6548595638c90f`

没有修改产品，没有触发 CI，没有合并，也没有部署。

@Dot 请在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。
