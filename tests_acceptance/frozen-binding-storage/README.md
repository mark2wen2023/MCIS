# 冻结句引用的内部 SQLite 持久层（待独立验收）

基线 `0514755778127efa33c0b47b0fcb00e617cb753d`；独立候选 `candidate/frozen-binding-storage`。仅新增既有 `BindingStore` 的实现，不改原 pin SHA、绑定信封、报告合同、路由、权限或旧冻结。

## 已实现的边界

`sentence_binding_store.py` 的初始化与构造均默认拒绝，只有显式 `enabled=True` 才可使用；该参数不是授权。没有默认调用方、模型 registry 注册或应用启动接线。

- 四元键 `(caseId,generationSnapshotId,sectionId,sentenceId)` 唯一。原始 binding/2 字节只插入一次，重复插入返回已有值，由既有 `decide_binding` 区分相同与冲突；不覆盖，不查 latest。
- SQLite 外键要求同案真实 `report_operation_snapshots` 父行；更新/删除触发器拒绝改写。存储中只有既有最小身份、pin、摘要和范围信封，不复制句子正文。
- 复用调用方 SQLAlchemy Session，内部不提交。调用者必须在外层提交成功以后才能交付持久成功；数据库异常原样传播。
- `get` 是内部存储操作，**不是授权读取接口**。使用前必须由可信服务器范围重新核验报告与证据权限、精确读取同一视图并调用既有 prepare/decide。普通 JSON、已有父行、摘要相等均不证明授权或真实性。

## 迁移与归档

这是独立 v1 表，只用于显式审查后的隔离装配。初次创建要求真实报告快照表存在；现存表或触发器与固定 SQL 不符即拒绝，不自动修复、升级或迁移旧库。外键限制已绑定父行的删除，不把原快照正文变成不可变。数据库管理员仍能改 DDL，不能声称防篡改。

未加入归档允许表。源码中普通导出在报告历史存在时走 working-records 分支；其现有 `reject_unsupported_tables` 将拒绝含本表同案行的归档。测试仅抽取该原函数在真实临时库执行，**没有执行完整导出/恢复**。恢复、迁移、删除生命周期须另审，当前不得用于默认服务库。其他归档入口不得凭本测试认为已覆盖。

## 复跑

需本地有固定基线 Git 对象及现有 SQLAlchemy/jsonschema Python 环境；不联网、不安装。

```bash
# Python 路径替换为已经审过、具备依赖的现有环境。
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/frozen-binding-storage/check.py
/workspace/mcis/service/.venv/bin/python tests_acceptance/frozen-sentence-binding/check.py
```

首条显式复制白名单固定源码到自动清理的临时目录，只创建两个真实报告业务表和新增表；不导入 main、models_registry 或 reports.service。8 项通过：实际磁盘 SQLite/引擎关闭重开、幂等与冲突、SQL 更新删除保护、跨案/父行约束、回滚、双连接唯一赢家、新生成独立绑定/旧绑定保持、默认关闭与归档拒绝及 schema drift。测试写入的报告行和审计快照均为自造夹具；不是实际报告生成。

权限和媒体读取使用原纯测试的手写 `Scope`；拒绝用例只验证调用协议，**不是真实权限验收，也没有证明授权交集/同一读取事务**。原10项纯绑定回归单独运行，不与本8项累计为端到端覆盖。

## 下一接线门槛

该基线没有生产 `BindingReadScope` 实现；报告编排模块还含种子顶层导入，未导入执行。需要可信服务器报告及证据授权交集、统一读取/写入事务和提交后返回钩子，才可接保存/重开。当前报告修改后存储仍保留旧引用，但不能据此宣称产品会正确重新判权。

报告正文、审计、PDF/DOCX 新导出中的来源短语/元数据必须另行验证撤权效果，仅隐藏链接不够；已下载文件不可撤回。本轮没有 HTTP/UI、实际音频或原件、报告生成/导出/恢复、4A、服务或部署验收。
