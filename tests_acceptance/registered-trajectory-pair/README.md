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


## 真实业务表与合成原件限定复验（2026-11-21）

```sh
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/business.py
```

此入口固定生产源码为 `ca8bb781545228a3333167b6188fcde1c53c2509`；只读取脚本 PATHS 明列的普通 Git blob，先与当前 HEAD 对应源码逐字节比较，不一致则停。将原样源码、四份 Schema 与两份既有合成 V1 文件复制到全新自动清理目录；用 `-I` 和该目录导入真正生产模块，不 AST 替换或 monkeypatch。无 main/models_registry/seed 文件可导入；配置类只定义、不实例化；未启动应用或 HTTP。

用原 `Database` + 显式七张真实模型表建立独立新 SQLite：cases/evidence_items/custody_events/audit_events/access_policies/archive_import_history/track_local_receipts；不调用全量 create_all。原模型 after_create 保护保留，audit/custody 四条追加保护 SQL 与 Database 原定义相同，核对实际触发器存在。其他 ORM 模型可能因原归档模块导入而注册到 metadata，但未建表、未执行业务。临时根和引擎在成功/失败后清理。

**真实执行**：生产 preview_input/commit_input 的 body 解析、完整业务授权与 Schema 检查、编号分配、保管链/审计、独占原件文件写入；生产 `_load_registered_pair`、load_receipt、原件字节重读/摘要和登记绑定核验、容器检测、V1 校验、事务提交/回滚。读取并验证真实 audit 和 custody 两条哈希链。

**手造部分**：请求只由 Body.stream/headers 替身传递（无 HTTP）；Ctx 的测试主体/既有 Investigator 角色显式注入，**不是已认证用户或会话验收**。案件与初始策略是经 case Schema 校验后的 fixture 用 put_doc 建立，未验建案 API。两船原文完全合成；证据、回执、Register/Access 与审计均由生产登记/读取函数生成，没有手工插这些行。

3 组退出 0：
1. 同案两船：真实登记后 (证据,保管,审计)=(2,2,2)，读取后=(2,4,4)，案/证据摘要匹配、Access 逐证据正确，审计/保管链 valid，各回执 accessCount=1。
2. 持久策略 evidence_meta=Deny：真实业务 require 返回 403，无双份结果，行数不变。仅业务策略检查，不是认证/4A/并发撤权测试。
3. 第二份为合法登记且单船契约有效、但文内 caseId 不同：读取失败；两份 Access 与对应审计全部回滚，登记记录/原件不撤销、原链仍有效。

首次运行因夹具缺 accidentType 在 case Schema 处失败，未开始登记；补齐纯合成字段后通过。既有生产源码及旧冻结没有修改。此轮不包含真实容器内容、档案恢复、真实业务数据、HTTP/浏览器、文件并发变更、撤权竞态或 UI。仍不能直接宣称可接 UI：尚需可信会话/固定 pin 选择来源与受控调用装配的验收。

## 精确 UTC 内部查询（2026-11-21）

产品固定头 `db90fdf73de7bd26ba75819f0102fc03d0789faf`；新增 `trajectory_exchange.registered_query._query_registered_pair(ctx, case_id, pins, purpose, aligned_utc)`。没有 HTTP/包级导出/UI 调用。输入由可信服务器调用方提供，不接受客户端批次。每次查询都重新走 `_load_registered_pair`，授权读取与 owned session 提交/关闭之后才产生查询结果；不缓存批次为权限。先验证严格 UTC Z、秒或毫秒格式，不能传本地时刻或自动取邻点。

原工具 `point_at` 与 Git 溯源和 rawRecord 原文输出耦合，因此未引入服务器路径。新窄适配复用 V1 `_stamp`，用固定原实现作差分对照：声明缺口内部先返回 declared_gap；端点可命中；其余仅匹配精确已存 alignedUtc，不插值、不拼补。固定工作台/query.py/HTML hashes 均未修改。没有新增同步窗口的交集/并集规则，也不接独立设备样例。

最小模型含 caseId/alignedUtc、两船 status、position/headingDeg/courseDeg 的 value/kind、时间 status/sourceUtc/correctionSeconds/alignedUtc，以及每船 original 固定 caseId/evidenceId/requestDigest/sourceSha256 与 JSON Pointer。点定位 `/points/n`，缺口定位 `/sampling/missingIntervals/n`，无精确行 locator=null。原始字段中的来源 ID、说明、basis、整行记录和 Git 路径不复制到结果；需要进一步查看须另走授权读取。输出的坐标、标识、时间、摘要仍属内部受保护信息，**不是公开响应**。recorded 与 interpolated 保留原 kind；后者为契约已有值，非本次计算或观测认证。缺 HDG 不使用 COG，collisionAngle=null。

```sh
python tests_acceptance/registered-trajectory-pair/query.py
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/business_query.py
```

实跑：纯合成 3 组差分/输入/精简输出检查；真实模块业务组合命令 5 组（其中复用既有 3 组，新增 2 组），不要重复累计。组合测试从固定产品 Git 对象物化白名单，复用 business.py 同一个登记/原件/业务表工装；原 business.py 默认仍冻结 ca8bb78，新增参数仅供这个显式固定测试入口使用，不关闭逐字节校验。

新增实证：T+20 两船存量插值，B 原 08Z+12→20Z；T+80 A缺轨/B有点；T+124.25 A缺轨/B无精确行；T+100 A recorded、HDG null/COG存在；逐次 Access 审计增加；每船 pin 精确匹配真实登记且 pointer 指向原行。错摘要、错案和持久策略拒绝不产生新模型、不提交新增 Access。测试中调用方旧变量不被替换，**不是实际 UI 状态/竞态测试**；已经返回的数据不能因此撤销，仍未解决跨进程撤权、文件并发改动或长期缓存使用。

业务链沿用上一节真实/替身边界：真实登记、文件、策略、DB/审计与查询；Ctx 身份和请求传输是合成夹具。未启动应用/HTTP/浏览器/容器/媒体，未接 4A、报告或独立只读工作台。接 UI 仍需可信调用装配、服务器 pin 选择与请求生命周期控制，不可把内部函数当身份验证器。

## 同一复盘工作台的默认关闭适配入口（2026-11-21）

新增 `tools/replay_evidence_workbench/registered_build.py` 复用原 workbench.html/style.css 壳，改用 `registered.js` 绑定同一 map/time/timeline/证据侧栏 DOM。原 build.py/workbench.js、模板、CSS 和原 HTML 固定摘要完全不变。此入口不是第二套模拟回放器，也不替换默认演示。

```sh
python tools/replay_evidence_workbench/registered_build.py --output /tmp/registered-shell-new.html
```

目标必须不存在；输出默认空白待接状态，无案件数据、默认身份、查询或 HTTP。CSP 仍 `connect-src 'none'`。仅供未来可信同源装配选择的源码切片，**当前没有可用业务服务/浏览器入口**。不为接线放开 CSP 或提供角色/凭据。

注入接口（没有示例身份、固定案或网络实现）：
- `MCISRegisteredWorkbench.attach(query)`：query 接收 `{caseId,pins,alignedUtc}`，返回内部最小模型的 Promise。宿主须自己提供已验证会话、固定 pin 选择、服务端权限/事务及 purpose；不能把浏览器参数当授权。错误可用有限 `code=ACCESS_DENIED|SESSION_EXPIRED` 表示拒绝，其他异常统一失败，不输出 message/原日志。
- `selectCase({caseId,pins,times})`：配置来源须经宿主确认；这里只核格式和响应一致性。切案立即清除坐标/来源/旧详情，配置无效不保留旧案，也不发请求。times 只允许有限、有序、唯一 UTC 时间列表，**不是观测/连续轨迹证明**。
- 选择时点、oninput/onchange、前后移动仅本地暂选并清掉旧坐标，时间轴显示未查询标记；只有“查询当前时点”显式提交才调用 query。同一时点等待中防重复；没有 tick、自动重试或自动首读。
- `invalidate()`：宿主身份/会话/案权限上下文变化时必须调用，清旧模型并移除适配器。页面不能自行发现服务器撤权，不能拿已返回的模型作长期许可。

模型按实际内部查询形状逐字段校验：同案、相同顺序的完整 pins、精确时点、状态、坐标/方向范围、时间算术、JSON Pointer；额外原文/来源字段拒绝。显示固定 evidenceId/requestDigest/sourceSha256 与 Pointer，来源 UTC/校正/对齐时刻；server 未提供的原始设备时钟说明、sourceIds、basis、原文一律不补。设备与原文动作禁用，没有回退合成帧。地图仅示意当前点并明确自适应范围、不绘连续线；时间轴只标本次两份结果。插值、计算、人工假设和示意 kind 分别标注，不把它们叫观测；缺 HDG 不用 COG。

首次响应校验失败显示“首次载入未通过”；曾接受结果后的当前失败显示“此前显示已清除”。两种情况均无旧坐标或来源，**曾接受结果不等于已认证会话**。每次查询前先清除，generation/序号忽略旧成功与旧失败，旧详情回调也失效。忽略响应只阻止显示，**不取消已提交 Access、也不宣称回滚**。没有 URL/storage/log 数据写入。

复验：
```sh
node --check tools/replay_evidence_workbench/registered.js
python tests_acceptance/registered-trajectory-pair/shell.py
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/business_ui.py
python tests_acceptance/replay-evidence-workbench/check.py
python tests_acceptance/replay-evidence-clock/check.py
```

本轮均退出0：shell 2组；business_ui 4组（包含原业务3组，不重复累计）；旧工作台2组含原Node手写DOM、旧查询8组。business_ui 使用固定 db90fdf 真实生产登记/读取/查询，生成4个时点到临时文件后交生产registered.js＋原壳的手写DOM；真实查询4次审计从2到10。JS阶段为内存Promise适配，不是真实传输：20轮 input/change、前后移动0次调用；一次明确按钮1次调用；等待同点重复不派发；A→B、乱序/旧错误、权限拒绝、身份失效、错pin/时间/额外原文和旧详情不回填。此计数分层对账**不是一次真实浏览器点击打通HTTP的证明**。

未运行浏览器/视觉/键盘焦点实机验收、HTTP、App/容器/媒体/4A；未改可信身份装配或服务端路由。独立离线工作台仍保持默认原样；该适配只有注入接口，没有已批准的业务HTTP接缝，因此不对外启用。
