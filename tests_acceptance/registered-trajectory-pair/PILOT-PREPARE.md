# 单案待审引用：未启用的内部候选

票据范围：Mark 明确同意本机试点账号在指定合成案核对报告草稿和原件，生成一条待审引用；不保存报告/绑定、不导出、不接 4A。此次没有创建实际账号、提升任何人的角色或启用试点。

基线 c3189c621555c07016cc9ad54aa9c491fa6fd283；设计 a1bba0aa9f644b2cd0e5359f211028a978f61850。服务器会话两文件取自 0a7c09aaf25218337852bc55a075a400acb3402e；仅 PilotSessions 构造器增加显式主体限定的内部操作。generation_snapshot.py 原样取自 94014643c02a1dd046ee8b0bfb76ae3b36631509。没有合并分支、更新旧冻结或修改角色/路由操作映射。

## 可调用范围

可信本机启动方必须同时显式配置 PilotSessions.report_reference_subject、该主体的精确 `(SYN-XREPO-001, report.reference.prepare)` 与 `evidence.original.access` grant，以及 enabled=True 的 PilotTrajectoryPrepare。默认拒绝；不能从 HTTP header、URL、客户端 JSON 建立此配置。没有公开路由、默认装配或浏览器调用方。服务端固定生成快照/句 key 和登记 pin，只支持 A-t100 /points/7、2026-02-01T12:01:40.000Z。输出只是内部待审状态和最小定位，不含正文、坐标或原始行，不能当授权凭证、持久绑定或原件真实性结论。

现有完整报告 category/field policy、report_draft/audit 权限和原件 authorize/load_receipt/protect_container/Access 路径均保留。普通 Investigator 默认仍被拒绝；正例是工装明确创建的合成 LeadInvestigator 会话，原策略本来允许它，没有把实际账号升级。

SQLite BEGIN IMMEDIATE 与同一个 Database.session 覆盖策略、RA及审计链、固定原件读取和 Access 追加；成功提交后才返回。失败沿既有 registered_pair 组合规则回滚本次 Access，不返回候选。这不是审计静默丢弃：失败没有成功读取交付记录，异常向调用方传播；没有另写失败审计。提交结果不明时禁止调用方据此自动重试。本次只实测提交前拒绝，不模拟已提交后断连。

会话到期/撤销检查在读取前及提交前执行；独立会话表不是 SQLite 的一部分，最后检查后的撤权竞态没有解决。文件系统也不是数据库事务快照；沿用原件完整性路径。RA 与生成审计关联及审计哈希链可核对，不声称 afterValue 自身获得防篡改存储保证。

## 复跑

保留固定 Git 对象 db90fdf73de7bd26ba75819f0102fc03d0789faf 和工装所列对象；缺对象失败，不自动联网。使用已有包含 SQLAlchemy/FastAPI/jsonschema 的环境：

```bash
/path/to/existing/venv/bin/python -I tests_acceptance/registered-trajectory-pair/pilot_prepare.py
```

本轮实际命令使用 `/workspace/mcis/service/.venv/bin/python`，4 项 unittest 通过，退出 0（原业务3项＋本票1项多分支）。源码先按明确白名单从固定 Git 对象复制到自动清理目录，检查实际模块导入清单，未导入 main/models_registry。

真实执行：临时 SQLite、生产证据 preview/commit、文件字节完整性、政策/保管链/Access审计、实际 PilotSessions 核验和 generation_sentence。合成替身/夹具：临时案件与策略行、手造完整 RA 和 report.generate 审计，非真实报告生成；随机临时会话非登录验证；before_commit 异常注入非真实磁盘故障。

覆盖：同案正例；缺凭据/grant、到期/撤销、错案、普通 Investigator/Public 与伪造角色头、报告/证据策略拒绝、错误 pin；读取后到期和提交异常不返回且回滚；成功恰有1条 Access、操作者为服务器主体且两条链有效；报告0行、RA仅夹具1行且未改、无绑定表；无正文泄漏。

尚未验：实际账号/登录、HTTP、UI、本机部署、跨进程撤权、真实报告生成/保存/导出/恢复。没有启动服务、浏览器、容器、模型或读取真实资料。下一步需独立审查此限用途授权及审计失败口径，再另行批准运行；本候选不构成启动许可。
