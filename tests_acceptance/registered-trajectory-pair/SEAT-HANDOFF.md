# 登记侧 → 同进程接收侧（合成验收，非产品能力）

基线 c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24；不改其原双时点检查。仅本文件和 seat_handoff.py 是本轮接收侧协作边界，B 可在自己的分支写回调，不改登记侧文件。

## 最窄入口

```bash
/path/to/existing/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/seat_handoff.py
```

另一个可信离线检查脚本可用 `runpy.run_path('/absolute/checkout/tests_acceptance/registered-trajectory-pair/seat_handoff.py')['run_handoff'](consumer)`。运行者必须用 Python -I；consumer(record) 仅在正例全部检查成功后同步调用一次；断言失败令测试失败，返回值忽略。run_handoff 返回 bool，调用脚本必须将 false 转为非零退出。不能由模型选择回调或传入 case/pin/时刻/权限。没有文件或网络输出；不要将这份内部记录直接塞进模型上下文。受保护 pin 留在本地宿主，B 的文本提案/引用核对应另行最小化。

## 实际字段

顶层固定：scope='synthetic-test-host-only'、caseId、frames（T100随后T124.250）、accessCount=4、identityProviderVerified=false、readCredential=false、reportSaved=false、modelCalled=false。

frames 原样来自 `_query_registered_pair`；每帧有 caseId/alignedUtc/vessels/authenticityVerified/collisionDetermined。每船保留真实服务给出的 vesselId、original={caseId,evidenceId,requestDigest,sourceSha256}、status、locator、time、position、headingDeg、courseDeg、courseUsedAsHeading、collisionAngle；缺轨项另有 gap。不把缺失的原始时钟依据、sourceIds、原文、速度补入输出。

- T100：A /points/7，B /points/12；recorded 仅合成质量。A HDG null；B sourceUtc=12:01:28.000Z，+12秒对齐12:01:40.000Z。
- T124.250：A declared_gap /sampling/missingIntervals/1；B no_observation_at_time，无指针。二者均无time/position/heading/course。
- original 的三个标识直接来自实际 preview/commit 回执和实际已授权原件查询，非回调自报；具体 evidenceId/requestDigest 不在文档硬编码。

固定原JSON来自 2048c60fd6650c6f2c99a76a16be463a3895655d；A SHA a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c，B SHA 07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca。沿既有原字节登记与 materialize 白名单校验；缺固定对象失败，不联网。依赖仍为既有 Python/SQLAlchemy/FastAPI/jsonschema，无安装。

## 实测与权限边界

5项退出0：3项既有业务基线、2项新交付/拒绝检查。新正例两份 Register、两次双船读取产生4条Access；逐条核对证据ID/SHA及保管链、审计链。回调拿独立副本，修改副本不影响宿主结果，回调后业务计数不变。缺权限用既有策略设置Deny，生产require路径拒绝，零交付、零新增Access；非真实账号授权验收，不构造漏洞探针。

生产代码为真实登记/完整性/策略/查询/SQLite；Ctx、案件与默认策略来自既有合成工装，不是服务器签发会话或真实登录。没有报告prepare/保存/绑定、正式ECFC或单席模型调用。两次查询分别提交，不是一个共同快照；失败不交付不等于撤回此前已成功提交的Access。已经交付的数据不是长期权限缓存。

这不是沙箱：consumer 必须是受信本地断言代码，同进程Python本身没有隔离能力。仅参数不提供原件读取权能，不声称恶意代码不能检查进程。没有UI、HTTP、模型、浏览器、生产身份、报告/归档或真实两端联调通过结论。
