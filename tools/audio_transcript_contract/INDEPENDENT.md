# 人工转写侧车合同独审

限定范围通过，无新增阻断缺陷。作者19+独立16，**35/35通过（0.20秒）**，日志independent-results.txt。

独立测试包括严格类型（bool不得作int）、错误哈希大小写、数组/对象混淆、未知speaker拒绝、跨evidence拒绝、located/unlocated重复ID拒绝、未重算hash的修改在unknown-current情况下仍拒绝、返回值深复制与输入不变。版本parent要求、跨case、过期判断及合法重叠分段由作者测试一并运行。

关键否定用例：自洽伪造文本及登记/当前hash并重新封装，仍能达到supplied_snapshot_matches_not_authenticated；admissionAllowed/authorizationVerified/asrExecuted全部false。revision=999与任意格式合法parent hash也可接受，证明这里只检查关系格式而未读取历史链、未认证当前快照或真实音频内容。

Schema经Draft202012Validator.check_schema通过；未知字段/bool结构拒绝。摘要不匹配的材料可通过schema但必须被contract.validate拒绝，测试证实两层不可互相替代。schema的integer按JSON语义可能接受1.0，runtime严格Python int更窄，应始终运行runtime，不单靠schema放行。

registeredSha256保留于artifact完整摘要，但compare的current快照只比较case/evidence/currentHash/stateDigest/artifactHash，未重新读取权威登记库；无时间戳或实时撤权机制，不应把“匹配所供快照”说成“真实当前有效”。

纯离线合成结构测试，无ASR、真实录音模型、API、数据库或权限验证；未修改实现、推送或部署。
