# 内部同案双份 V1 原件核验（待独验，未接线）

基线：f9f4e599cdb670d864a5e7e986067216e7105636。不合并 pilot 分支，不改旧冻结或共享契约。

`evidence_intake.router._read_original_for_access` 是原下载事务内部逻辑的原序提取。原 download 仍保留先授权、请求 purpose/operator 校验、WRITE_LOCK、begin、同一 session、Response；AST 展开对照整个 router 完全等价。

`trajectory_exchange.registered_pair._read_registered_pair` 未注册路由、未导出包 API、无默认调用者。服务器调用方必须提供已验证主体与个案/操作上下文、固定的服务器选定 pins、已经校验的 purpose/operator，并负责异常时回滚整个事务。普通 Ctx、浏览器声明或该函数通过均不证明认证。每份原件都重新走原授权、登记/摘要完整性检查、容器保护及 Access 审计；然后核对固定 case/evidence/requestDigest/sourceSha256，运行现有 V1 校验器。两船全部有效才返回 tuple，不返回半份、yield 或修改回放状态。

锁定的是已登记不可变原文字节及登记摘要，不是当前航迹版本计数。相同案不同船才可用；时间未核实拒绝整组，缺轨/未知 HDG 保留。没有 CSV→V1 转换或 latest 回退。失败前第一份可能已向调用方 session 追加 Access：必须整体回滚，不能捕获异常后继续提交。仅传同一 session 不证明数据库一致快照、撤权竞态或磁盘文件稳定性。

复验（已有 Python/jsonschema，无安装）：

```sh
python tests_acceptance/registered-trajectory-pair/check.py
```

初版 bdb0c60 的 9 组：整个 router AST 展开等价、两船及缺轨/缺 HDG原样、跨案 pin、合成读取拒绝、合成授权/容器失败顺序、错误摘要/回执、坏契约/同船、原文错案、新记录不替代旧 pin。执行 AST 提取的真实函数，手写 authorize/load_receipt/container/audit；真实 V1 纯校验器读取现有固定 Schema 和合成夹具。未导入 router、FastAPI 或 ORM。

未验证：实际身份、权限、load_receipt 的数据库/文件执行、事务回滚/持久审计、浏览器、HTTP、回放接入和报告。下一步必须在可信装配点证明授权上下文和一致读取/回滚边界，再考虑调用；不提供启动许可。


## 后继事务入口（2026-11-21）

`_load_registered_pair` 是新的内部调用边界：复用原 purpose/operator 文本检查，取得既有 WRITE_LOCK，再开启全新 `ctx.db.session()`，调用原 `reports.access.begin`，运行两份读取；退出 session 的 commit/close 成功后才 return。没有在事务内部捕获/映射错误；调用方只能在外层映射，不自动重试。旧下层函数和原下载行为保留。仍无路由/默认调用者，不赋予权限、不宣称 SQLite 锁解决会话撤销或文件并发变化。

审计规则核查：`evidence.service.append_custody` 与 `audit.service.append` 都只 add/flush，没有独立 commit；`Database.session` 在异常时 rollback。与这些生产调用点的既有事务责任一致，本候选不将第一份成功读取另行提交。提交后连接/确认异常可能导致“两份均已提交但未交付结果”；不能将提交异常说成必然没记录。

不可同步的有限诊断现在为 `REPLAY_BLOCKED:` 后接稳定排序的 `TIME_UNRESOLVED`、`TIME_CONFLICT`、`TIME_NOT_INCREASING`、`POSITION_MISSING`、`IDENTITY_UNRESOLVED`。未知校验诊断失败关闭；结构/语义契约异常仍是 `TRAJECTORY_INVALID`。声明缺轨和缺 HDG 本身不拒绝精确点查询，仍保留原 validator 的 gaps/orientation，不改同步窗口交集/并集或任何契约。

实跑命令（使用已有离线 venv，不安装；其它环境显式选择已有同等依赖的解释器）：

```sh
python tests_acceptance/registered-trajectory-pair/check.py
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/transactions.py
python tests_acceptance/shared-trajectory-cross-repo-expanded/check.py
```

本轮：10 组合成读取/分类与 AST 等价检查；6 组**真实 SQLite 事务原语**检查。后者从固定源码 AST 提取原 `Database` 类和 `begin`，使用已有 SQLAlchemy 2.1.8，在自动清理的新临时目录建唯一 `synthetic_access_probe` 表；未导入 app、业务模型/registry，未调用 create_all。生产授权/原件读取/容器仍为手写替身，Access 以探针 INSERT 表示，**不是实际保管链/审计表测试**。覆盖成功后可见两条、第二份读取失败回滚第一条、第二份校验失败回滚两条、提交前异常不交付且回滚、提交后异常不交付但两条可能持久化、无效 purpose 不启动读取。未执行真实权限、业务 ORM/原件/审计链、并发撤权或浏览器。

接 UI 仍缺已验证的服务器调用装配、可信 pin 来源及真实授权/原件/持久审计验收。本次只补事务所有权的内部接缝，不开放入口，也未改变已冻结图片/镜像或旧 bdb0c60 哈希记录。新冻结见 `logs/registered-trajectory-pair-transaction-hashes-frozen.txt`。
