# W16 单条 T+100 存储形状回归

父固定 `540f9343c307385fb0e6d537119348c15a9947d0`。新入口，不改变任何旧 runner 或产品。使用现成依赖，仓库根运行：

```bash
/absolute/existing/python -I -B tests_acceptance/registered-trajectory-pair/t100_shape_only.py
```

仅构造一个 unittest：原 `StorageShape.test_absent_identity_and_rejections`，不改该测试及其断言。普通 runpy 加载前逐文件核对固定父的四个测试文件；不执行它们的 __main__，不调用自动装入双船/策略修改回归的 base.run。产品白名单逐 Git blob 固定并物化后普通导入，无 main、registry、reports.service/sources、种子；缺对象失败，GIT_NO_LAZY_FETCH=1，无网络回退。

前置明确缩为一个新临时SQLite、一个SYN-XREPO-001合成案、原default_policy和A一份原件。case/policy是初始工装，不是实际登录；不改策略。原Raw.register通过正式preview/commit登记2048c60fd6650c6f2c99a76a16be463a3895655d原样vessel-a.json，保留原字节SHA；不登记B，不调用双船读取。A-t100定位/UTC/缺HDG先核对，不把COG当艏向。

原测试会插入4份明确标注的ReportAuditRow存储形状夹具与1条生成事件夹具；不是正式生成器、签名或真实报告。原PilotSessions核验使用短期随机合成凭据，不打印/持久化凭据，不新增产品grant。仅缺失snapshotId的正确键正例返回待审且saved=false；显式null、冲突ID、错审计引用、错案和原策略不允许的Investigator都不增加Access或审计。四个快照不变，ReportRow为0，无绑定表/导出/归档。

观察计数：登记1 custody+1 audit，宿主生成事件夹具1 audit，成功prepare增加1 Access+1 audit；最终1 evidence/2 custody/3 audit。拒绝逐项由原测试核对计数不变；追加tearDown核对仅一案和策略未改。共1项测试，不将内部断言或此前通过数累计为端到端。

正例结论严格为UNSAVED。没有不可变引用持久化、报告保存/历史重开、真实账号、HTTP/浏览器、生成器或归档验收；已有固定pin核验不意味着快照正文具有永久不可变或密码学真实性。临时库退出时清理，不接用户库、4A、模型或真实材料。
