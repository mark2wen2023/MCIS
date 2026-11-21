# T+100 报告待审定位／单席证据核对交叉回归

仅测试新增，基线 `22c3c0fd06c5f6c85a4c41a3eabd6714965d6689`；原源码、原5项测试及冻结不变。参考单席 `6d4b00032abdba1f3b1cce46ecd3dff488f1aa81` 的 host validator／固定措辞分层，不改其 T+124.25 用例，不调用 Pi/Agent/模型。这里是两个离线组件的交叉断言，不是两位实际账号共同调查，也不是新的服务。

## 真实与合成边界

- 原 prepare 测试照常执行：临时真实 SQLite、生产登记 preview/commit、服务器合成会话核验、完整报告政策、RA审计关联、原件完整性与 Access、提交后返回。旁观包装器只在原调用成功后复制返回，不修改授权或响应。
- 仍只有明确配置的合成 LeadInvestigator 正例；普通 Investigator 拒绝。报告 RA 是工装准备，不是实际报告生成。原拒绝/撤销/到期/提交失败/无保存断言保留。
- 同案共享字段在可信测试侧比较：SYN-XREPO-001、T+100（2026-02-01T12:01:40.000Z）、固定登记 evidenceId/requestDigest/sourceSha256 和 `/points/7`。独立 projector 输入来自本地已知合成登记夹具，而不是以待审输出换取读取权。核对该夹具登记时的确切序列化字节摘要，A-t100、recorded（仅合成质量）、HDG missing 与 COG存在。没有重新读取登记原件。
- host `_validate` 原样从固定 Git 对象 `420284ab5fd44c94b737f8c1cf51bc0ef09aea29:research/expert_group/packet.py` 物化至自动清理临时目录，Git blob 必须为 `ff2018dad2d58e9fe158f503ecd71a004c20e226`；不调用其 load_packet，不读取公开材料。缺对象失败，不下载、不装依赖、不追 latest。
- host 仅收到“合成精确时点有一条登记位置记录”和“该记录HDG缺失，COG不是HDG”两条最小说明，不含pin、JSON Pointer、正文、坐标或原始行。没有模型上下文或模型调用。固定措辞断言限制‘单点不能判断转向’，不是通用语义检测；host 只验证结构和引文，不能单独证明结论或授权。
- 本票组合场景 prepare 成功仅有原来1条 Access，失败按既有事务规则回滚。交叉核对前后 evidence/custody/audit 数量相等；没有额外原件请求或写入。三个继承业务用例各自独立临时库，不把它们的 Access 累加为本场景。

## 复跑

在具备固定Git对象及已有 SQLAlchemy/FastAPI/jsonschema 的环境：

```bash
/path/to/existing/venv/bin/python -I tests_acceptance/registered-trajectory-pair/t100_seat_crosscheck.py
/path/to/existing/venv/bin/python -I tests_acceptance/registered-trajectory-pair/pilot_prepare.py
```

本轮用 `/workspace/mcis/service/.venv/bin/python`：新入口4项通过（既有业务3项＋扩展prepare交叉1项），原入口5项通过；两个命令退出0。不重复累计为9项独立覆盖。新入口逐字节锁定上述22c3c0f的六个源码/工装文件，旧materializer继续约束既有生产依赖；受管导入白名单不含main/registry。

未验：真实登录、UI、模型、HTTP、实际报告生成/保存/导出、持久引用、跨进程撤权。RA正文不在现有审计链全文覆盖内，案号依靠服务器关系范围；原限制不变。没有新增路由、grant、共同生产事务或可信模型身份，不构成产品闭环或运行许可。
