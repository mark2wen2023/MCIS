# 同库四时点查询 → 一条待审预备（仅离线合成）

本脚本新增一项组合回归，复用三项已有业务回归；不得累加为四项新覆盖。
仅测试编排，无生产接线、HTTP、真实账号、浏览器、模型、三维或归档验收。

## 固定输入

- 父工装：`d3fd9542249f214a5aa3776d7c0b8c7609ad81a7`。
- 四时点参考：`8d68f6fa076b7acad90fab10e95ab88c6945a018`。核对其 business.py / business_query.py 与父工装逐字节一致；本测试复用相同时点及点指针预期，不执行其另一套独立数据库工装。
- 待审生产增量：`22c3c0fd06c5f6c85a4c41a3eabd6714965d6689`，四个 NEW 文件逐字节校验。
- A/B 原样 JSON：`2048c60fd6650c6f2c99a76a16be463a3895655d`，由既有 Raw.register 通过 git show 读取并真实登记；不重编码、不改样例。

原工装还固定读取 `db90fdf73de7bd26ba75819f0102fc03d0789faf` 的 BASE 白名单；仍逐项核对 Git 普通文件及候选 HEAD 产品字节。保留既有全部检查，不重新冻结。候选 HEAD 必须以固定父工装为祖先；新增测试文件不会要求 HEAD 等于父提交。缺任一固定对象、入口文件、允许的生产源码或既有依赖，均非零退出；无联网、fetch、安装或版本回退。

入口在任何 Git 调用及被调用工装之前设置 `GIT_NO_LAZY_FETCH=1`，禁止 partial/promisor clone 自动补取对象。运行前须由使用者预置上述四个固定提交及所需文件 blob，并预置 `db90fdf73de7bd26ba75819f0102fc03d0789faf` 的完整 BASE 白名单对象；仅有提交对象不代表依赖齐备。此设置仅限制 Git 懒加载，不是环境或网络隔离保证。

## 运行

从本候选仓库根目录，用已有兼容 Python 3.12 环境（SQLAlchemy、FastAPI、jsonschema）：

```bash
/path/to/existing/venv/bin/python -I -B tests_acceptance/registered-trajectory-pair/four_frames_prepare_joined.py
```

`/path/to/existing/venv` 是使用者选择的已有环境，不是脚本内固定路径。禁止 `-O`；入口拒绝关闭 assert。不启动应用或服务。使用临时源码副本、SQLite 和原件目录，退出清理。不得把本预检视为环境隔离证明。

## 断言与边界

同一个 SYN-XREPO-001、同一 A/B 登记及数据库：T+100、121、124.250、127.500 每次查询新增两条 Access，总计 8；随后 A T+100 `/points/7` 待审预备新增 1，总计 9。核对 Access 的 evidenceId/SHA 顺序为 `(A,B)×4 + A`，以及保管链和审计链。

每帧明确断言顶层 caseId、请求 alignedUtc 及恰好两船，避免 zip 截断漏验；T+100 的 A headingDeg 必须为 `{value: null, kind: "missing"}`。

T+124.250 的 A 只为声明缺轨，B 没有精确点；B 后三帧无原点指针。输入时间字段逐项匹配固定样例，不拿 COG 补艏向。校时为合成声明，不证明事故先后或人审已签。

错案查询、ExternalExpert 读取、错案预备、缺 prepare grant 均拒绝，拒绝后行数与 Access 不增。已有三个回归另验实际原件/回执、策略拒绝及第二份错案回滚；各自使用独立测试库，不计入新增联验的 9 次 Access。

案件/默认策略由既有工装构造；报告生成快照也是手造测试输入，附真实格式的审计事件，不是正式生成器执行。原件登记和查询、预备授权/完整性、SQLite 提交均调用实际组件。预备使用显式合成 LeadInvestigator 短期会话，不提升任何实际账号。测试会话随机值不打印或持久化。

最终业务 ReportRow 为 0，冻结绑定表不存在；ReportAuditRow 为 1（上述输入夹具）。共 11 条保管链记录（2 Register + 9 Access），12 条审计（另含 1 条夹具生成事件）。输出不含合成私有正文。这里的零报告保存不表示测试没有写入快照夹具。

各查询和预备是顺序独立事务，不是跨阶段单一事务，也不证明撤权竞态闭环。无报告保存、绑定、导出、恢复、UI/HTTP 或真实登录验收。

## 本次实跑

2026-11-22，已有 Python 3.12 环境，命令退出 0：`Ran 4 tests in 0.574s / OK`。
新增联验结果：Access 2→4→6→8→9；reportRows=0，snapshotFixtureRows=1，bindingTableExists=false；拒绝不增写。

独审收口后复跑同命令退出 0：`Ran 4 tests in 0.597s / OK`；新增帧身份/时刻/数量及缺艏向断言通过，8+1 审计结果不变。未执行真实 partial clone 联网试验；只落实禁用懒加载设置和固定对象检查。
