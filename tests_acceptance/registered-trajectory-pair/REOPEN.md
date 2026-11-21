# 登记原件 → 精确点位 → 新 Database 重读（纯合成组件验收）

候选基线 `c51c73ca255df124a149728091dd7e0f621500a2`，生产白名单固定 `db90fdf73de7bd26ba75819f0102fc03d0789faf`，复用 business.py 的逐文件 Git 字节核验和导入来源检查，不修改既有冻结。报告候选只读参考 `94014643c02a1dd046ee8b0bfb76ae3b36631509`，没有合并。

已有允许的 Python 环境（SQLAlchemy/FastAPI/jsonschema），不安装：

```sh
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/reopen.py
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/business_query.py
```

本轮分别退出0：前者4项（原业务3项+新增重建1项），后者5项（重复原业务3项+原精确查询2项），不能相加为9个不同场景。

新增纵切实际调用：原 preview_input/commit_input → 原件文件、Evidence/Custody/Audit → _query_registered_pair → Database.dispose/重新构造 → 原固定pin重新查询 → _load_registered_pair原字节验证及JSON Pointer核对。

- T+100是已有观测点：A `/points/7`；未知HDG保留，不使用COG代替。
- 另登记同船且一个点纬度不同的独立V1原件，明确是另一份登记，不是假造轨迹修订号。新、旧pin各自可查，旧结果逐字段不变，不取latest。
- 重建对象读取同一临时磁盘SQLite；没有重新建表或重新写入旧记录。会话由真实Database管理，真实原件位于该测试独占临时目录。
- 新场景结束3份登记、8条Access；custody/audit各11行。检查Access证据/摘要顺序与两个哈希链；原3项验证真实策略拒绝及第二份业务校验失败回滚。
- 案件/访问策略是原工装直接写入的合成前置；Ctx明确注入测试角色/operator，**不是登录、真实身份或报告grant验证**。仅请求传输Body是手写替身；登记、授权策略判定、原件读写、SQLite、事务、审计均用固定生产模块。没有新增权限机制。
- 没有重新启动进程/服务，只重新建立Database及其连接/会话。调用方保留的pin仅测试内存值，不是报告持久化。每次重读仍走既有授权/完整性/审计路径；不证明撤权竞态解决。

## 第一个报告阻断，未绕过

报告候选 `reports/sentence_binding.py:172–210` 的 `prepare_audio_binding` 使用生成审计、固定句与 `read_exact_audio_range`，200行明确要求 media=audio，payload为 `frozen-sentence-audio-binding/2`。当前轨迹 pin 是 caseId/evidenceId/requestDigest/sourceSha256 + JSON Pointer，不能转换成音频 run/revision/segment；没有可信轨迹报告 BindingReadScope。`sentence_binding_store.py` 自述仅低层opt-in存储、非授权边界，无生产调用点，不能直接塞入自造轨迹payload来冒充保存。

因此**没有调用报告保存、归档、导出或恢复**，没有产出报告持久引用；报告正文与权限均未变。最小下一步是批准轨迹引用类型及真实报告/证据授权交集与同读事务的产品调用点，再单列存储/归档兼容及重开授权验收；不能用本次临时库重读替代。

本次不启动应用/HTTP/浏览器/容器/媒体/模型，不访问4A、真实材料或seed；不改变契约、路由、生产代码。只可称组件级真实合成持久化验证。
