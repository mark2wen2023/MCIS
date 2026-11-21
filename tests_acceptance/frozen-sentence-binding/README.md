# 冻结报告句的单一音频引用：内部候选，未接线

基线 `da8cda69bfb421177c702587c45426a2cc5ce5e1` 已包含 `3a19c75221dc770042708972bf7a1a36d681e121`；本次不改旧读函数、摘要算法、合同、生成器、路由、权限或冻结文件。仅新增 `reports/sentence_binding.py` 的服务端读取适配与纯比较决策，不是保存→导出→重开产品闭环。

已存在的 `generation_sentence` 只解析完整生成 RA，`read_exact_audio_range` 只验证指定旧摘要与范围。原组合测试的关联是手造夹具，没有同句唯一/不可覆盖决策。本次补此缺口，首版仅音频（image 不接受），不重复实现读取器。

## 接入合同

- 唯一键 `(caseId, generationSnapshotId, sectionId, sentenceId)`。仅允许显式 RA；不查当前报告或 latest。
- 调用方只传键，不能直接传快照/引用 JSON。`BindingReadScope` 必须由可信服务端装配注入；它目前没有生产实现。继承该类、普通 JSON、返回布尔量、测试通过均不是身份或授权证明。
- 先 `require_generation_access`，再 `read_generation`，用现有 report schema 校验器和 `generation_sentence` 解析唯一冻结句。随后 `read_pin` 取得**已存在的服务端可信旧引用关联**，其完整键、auditSeq/reportId/familyId/version 必须与冻结句一致。尚无可信关联时返回 None，绝不从客户端或当前媒体自动推断。不能利用此候选新建可信来源。
- 在任何媒体读取前调用 `require_media_access`；真实实现必须核对该主体对报告和精确证据/媒体的权限交集、来源与任务绑定等原守门。取得的 `media_reader` 使用现有 `ScopedMediaReader` 或同一既有精确只读合同。读取顺序仍为 revision 0、指定 revision、指定证据。旧 SHA 必填，segment 必须匹配；缺修订/源变化失败，不回退。
- 上述权限、RA、审计、关联、精确修订与证据摘要必须由调用方同一个稳定读取视图提供。本模块不创建事务，无法证明这些前置；不得在普通 Web 请求里直接构造测试 Scope。
- 输出为内部 v2 canonical bytes，仅含 contract、key、核心不可变 pin 和 sentenceSha256；不保存句子正文、generatedText、citations、摘录、操作者或范围副本。sentenceSha256 使用既有 `_bytes` 排序/ASCII JSON 配方对完整冻结句作 SHA-256，确保可信冻结正文改变也不能静默覆盖同键绑定；这不是旧媒体引用 SHA 配方的更改。范围仍每次调用既有读取器验证，未知 start/end 在其返回中保持 null，不写为零。本候选不返回原音或显示对象，不产生真实性/持久化证明。

## 存储接口，不含真实存储

`BindingStore.get(key)` 返回原始 bytes 或 None。`insert_if_absent(key, payload)` 必须在数据库唯一约束及事务内原子领取，返回已存在或刚插入的完整 bytes，永不覆盖。调用方用 `decide_binding` 检查返回值；禁止用 get 后无条件写入代替原子操作。提交异常/未知不得声称已保存。

`decide_binding` 的结果是 `insert_required`、`identical`、`no_historical_reference`；任何同 key 字节变动抛 `BindingConflict`。None 才是无历史；非法/不规范字节或错误 envelope 抛 `BindingCorrupt`；已有绑定而可信 pin 消失也失败。能解析的被改载荷与新提案不相等仍为冲突，不冒称能鉴别伪造者。**相同字节不能证明真实性**，防篡改、持久化恢复及原子性均依赖未来受信存储。不得将任意请求 bytes 作为 freshly prepared proposal；纯比较不是安全入口。

## 本轮可复验

使用现有 Python 与 jsonschema；无安装、应用包导入、ORM、文件媒体、网络或权限实测：

```sh
python tests_acceptance/frozen-sentence-binding/check.py
python tests_acceptance/report-generation-snapshot/check.py
python tests_acceptance/audio-reference-range/check.py
python tests_acceptance/report-audio-snapshot-combination/check.py
python tests_acceptance/media-report-reference/check_reader.py
python tests_acceptance/media-report-reference/check.py
```

新 10 组使用原手造夹具、真实纯函数及显式剥离包导入的既有 AST 加载方式；服务端 Scope 和原子存储均为手写内存替身。覆盖顺序、重复幂等、逐 pin 字段冲突、两层模拟访问拒绝、非生成审计/缺句/重复句、跨案/错 pin/旧 SHA/缺版本、null 与损坏记录、新修订及当前正文不替代旧句、新审计独立。不是实际数据库竞争、权限拒绝或受保护接口测试。

下一步必须先提供真实授权交集和同一事务内 RA/关联/媒体读取调用点，再做存储唯一约束、提交/恢复验证，之后才允许保存→导出→重开或 UI。当前不开放接口，不提高旧报告权限，不执行原音定位/回听，不改变图片试用或 OCI 允许表。

## 加固增量（基于 a5a920a，不刷新其旧冻结）

旧头的合成句正文可直接出现在序列化 bytes 中；10000 层嵌套 bytes 可抛原始 RecursionError。本增量删除内容副本并用新内部 envelope `frozen-sentence-audio-binding/2`，v1 不再接受且不自动迁移。没有现存生产绑定或数据库迁移；如果以后发现真实持久 v1，须先停止并单独审查处理，不直接升级读写。

记录最多 16384 bytes、JSON 嵌套最多 8 层，在 json.loads 前扫描字符串转义及结构深度；超限、重复键导致的非规范字节、二次编码、非对象、额外字段、非法摘要/标量、损坏编码及解析/编码 RecursionError 统一抛 BindingCorrupt。正常的 immutable conflict 不包在解析异常捕获内，仍是 BindingConflict。冻结句摘要输入另有限制：深度32、20000节点、累计字符串长度与最终编码上限1048576；超限抛 BindingUnavailable，不把无法计算摘要当无历史。

即使只剩标识符和摘要，它们仍可能透露案件关联，也可能用于猜测原文；**全部是内部受保护元数据，不是显示/API对象，不允许直接返回浏览器**。若以后另存时间范围，也须按同样敏感级别控制。字节相等与散列相等均不是授权、真实性或防篡改证明。

新定向用例覆盖独特合成短语不落盘、可信冻结句变动冲突、二次编码/深层/超长/破损/v1拒绝、范围已知/未知重验以及无 latest 回退；仅内存替身。旧的 `logs/frozen-sentence-binding-impl-hashes.txt` 保留对应 a5a920a，本增量另立 `logs/frozen-sentence-binding-hardening-hashes.txt`。

后续集成门槛（本轮不执行）：有证据权限时旧版本在 rev2 后仍能解析；无证据权限时报告正文、快照及新签发 PDF/DOCX 都不能泄露源短语或元数据，不能只隐藏链接。已下载导出不可撤回。真实正文/权限/审计/导出及统一事务均未改、未实测。
