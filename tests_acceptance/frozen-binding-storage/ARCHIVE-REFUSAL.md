# 归档拒绝的真实临时库回归

固定运行代码：`73a1fa7fc75c03a71c035925873b0a1af74b7d27`。本增量只增加测试和记录，不改权限、路由、旧冻结或存储实现，不允许新表归档/恢复。

## 已实跑

```bash
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/frozen-binding-storage/archive_check.py
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/frozen-binding-storage/check.py
/workspace/mcis/service/.venv/bin/python tests_acceptance/frozen-sentence-binding/check.py
```

Python 路径可换成已有、已审依赖环境；不安装。需本地有固定 Git 对象。新增5项退出0，原8项SQLite存储及10项纯绑定分别退出0，不合计成业务端到端。

新测试按明确源码白名单复制固定 Git 字节到自动清理的临时目录，校验当前 HEAD 对应依赖未变。导入真实 `working_records_archive.service.build`，不是提取 AST 函数或替换权限实现；使用真实 Database.session、ReportAuditRow/ReportRow/AccessPolicyRow 等明确业务表和新增只追加表。未执行全量 registry/create_all。

5项实际结果：

1. 默认策略允许的 LeadInvestigator 合成角色输入走真实 full_access 后，因锁定引用表同案有行返回 422 WORKING_ARCHIVE_INVALID，具体原因是存在未支持业务状态；无返回归档、无素材目录产物。
2. Public 在同一状态先被真实策略拒绝403，不返回上述内部状态信息。
3. Investigator 默认缺完整报告权限，保持403，不修改默认策略来使测试通过。
4. 预先在同一事务改动的合成当前报告，遇归档拒绝后被原 Database.session 回滚；数据库逻辑dump前后相同，绑定仍在，audit/custody仍为0行。
5. 别案不会被本案锁定行阻挡；测试另一案无 CaseRow，继续得到原404，不声称该案归档成功。

所有角色都是明确的测试输入，无登录/主体认证。报告和生成快照是原纯测试夹具写入，非真实生成；证据、笔录表为空，故**没有验证非空来源授权、原件或真实权限交集**。实际数据库是新建SQLite，无旧库；比较的是业务逻辑状态，不是SQLite文件逐字节不变。

## 本轮未执行的外围

测试只直接执行工作记录组装 `build` 的拒绝路径。`package/mcase.py:180` 外层 `export_case` 在 `has_history` 分支、调用 build 前还导入 HFACS router/archive（约197–202行）；本轮没有为测归档扩大到该依赖，也没有运行HTTP、外层ZIP组装/导出审计、恢复或媒体。没有替换这条外围后再声称整体通过。build成功路径及完整归档生命周期仍未验。

## 报告可信调用点的具体阻断与最小下一步

以下位置均对应上方固定运行代码：

- `common/context.py:get_ctx`（约26行）使用客户端 X-MCIS-Role，缺失回退 Investigator；不是可接新绑定的可信登录源。
- `reports/router.py:check_access`（29行）调用 require_content、case_info、require；`reports/access.py:begin/require_content`（14/30行）可在SQLite保留写事务，但锁/同Session不是认证。
- `reports/service.py:13` 仍顶层导入 haili5_seed；本测试未导入该模块或报告router。
- `audio_review/app.py:receipt/source/check`（33/39/73行）复核同案登记及实际字节/采样、任务绑定；`evidence_intake/router.py:authorize/load_receipt`（24/90行）另有原件策略与历史拒绝。精确reader不会替调用方执行这些权限、来源和身份检查。
- `reports/sentence_binding.py:BindingReadScope` 仍无生产实现，`read_pin` 没有可直接复用的服务器历史关联来源。不能把存储get或浏览器pin当作这种来源。

最小待批准接线应在一个显式非默认服务器入口中确认主体和个案操作，再在同一受控事务中执行报告策略、精确媒体/原件策略、完整生成快照与服务器选定pin读取、prepare/decide和只追加写入；提交成功才返回。重开需重新走同样授权交集，不披露未经复核的get字节。需要先决定可信身份来源及首个服务器pin如何建立；本轮不新造权限或假接口。

现有报告正文、生成审计、PDF/DOCX等仍走旧路径，未纳入此检查，不能宣称撤权闭环；仅隐藏链接不足，已下载文件不可撤回。真实保存/重开接线及完整归档支持仍受阻，本轮交付的是可独立复验的拒绝/回滚证据。
