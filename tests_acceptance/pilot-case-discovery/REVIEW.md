# 授权案发现真实API切片（未挂载、待独验）

祖先 f55f74ec18e7d24fefc849033c981a2b08f9a126；同一 candidate/local-review-pilot。

## 可调用增量

新增 `common/pilot_case_discovery.py:_register_pilot_case_discovery(app, enabled=False, sessions=None, origin=None)`，显式注册唯一 `GET /api/v1/pilot/cases`，不替换旧 `/cases`。默认未配置/未启用拒绝。复用前一候选同源Cookie检查和真实服务器会话源；无会话发行、登录或客户端身份自报入口。

`PilotSessions.authorized_cases` 只返回当前有效会话中精确 `case.read` 许可的排序案号，过期/撤销/未知返回None，空授权返回空元组。复用同一 `_active_session` 逻辑供既有verify使用，没有默认角色/全局案许可。

真实handler先确认会话许可，非空时才按案调用现有 `cases.service.load_case(session, case_id)`，只投影caseId/title；不调用 `list_cases`、`list_docs` 或先读全库再过滤。每案读取前verify、结束前复核会话集合；同案身份不符/标题格式错/读取异常整体失败，不返回部分结果。复用调用方已配置db的单个session与no_autoflush，不创建库/表，不写业务行。现有Database.session成功退出仍有原commit语义，不能宣称绝无数据库副作用或已获一致快照。

只注册该API，无页面/按钮/工厂；注册冲突立即失败。目标app须是已审计的全新合成专用实例，不能放进生产或旧main。目前没有入口调用此注册函数。

## 为什么不拼完整工厂

- `db.py:Database.create_all` 导入 `models_registry` 并全量create_all，不能满足本轮仅白名单必要路由/表要求。
- `image_review/app.py:_register_image_review_only`、`audio_review/app.py:_register_audio_review_only` 保留自身表/触发器，却依赖现有证据/回执/策略/审计与动态task-backed完整性检查；不是独立闭包。
- `evidence_intake/router.py:receipt_evidence/download/load_receipt` 有历史拒绝、报告容器保护与文件完整性路径。不得少建表、删权限或截掉报告保护来拼最小工厂。
- `cases/service.py:load_case` 是已有双case/key点读取（get_doc）；同文件的 `list_cases` 是全表读取，本API明确不调用。该模块经db/models的运行导入仍未隔离验收，测试没有执行它。

下一步先固定真实受限存储/初始化闭包和最终路由集，定义可信会话发放/同源HTTPS引导；仅在获准干净环境中验证真正FastAPI解析/路由集及授权前无受保护读写，然后挂工作台与限定图音页。第一次两合成案（A有已核对回执但零运行）导入→保存→冲突保留草稿→刷新重开仍未执行。没有全量main、旧launcher、模型任务、报告/归档变更的注册。

## 实跑范围

```sh
python tests_acceptance/pilot-case-discovery/check.py
python tests_acceptance/local-review-pilot/check.py
python tests_acceptance/verified-case-context/check.py
```

新增5组、相邻7及6组均退出0。生产注册与handler AST使用手写App/Request/Response/DB上下文及唯一允许的 `cases.service.load_case` 假导入；核对注册路径/元数据、逐案读顺序、no_autoflush、无未授权案/额外字段、缺配置/会话失效/跨站不碰存储、空授权、读错/异常/读取中撤销、重复注册。假事务的rollback标记不是真实数据库回滚证明。

未导入FastAPI/应用/ORM，未跑HTTP/浏览器/真实权限/恢复/模型或暂停测试，未看真实案件/原件/seed/凭据，不访问4A。撤销后再次检查不能消除核查与读取之间的所有竞态，不承诺多进程事务一致性。本增量不是完整试用上线或认证验收。
