# EXPERTRESEARCH_INTEGRATION 独立审计

隔离目录 `/workspace/mcis-expert-integration-20261114`，HEAD3125eaf。独审仅新增本目录及DEFECTS文件，没有实现适配器、应用合并、修改运行源码或远端。

结论：**离线整合审计与设计说明受限通过，7个独立用例通过（1.10s）**，见results.txt。4项审计实现冻结匹配，见hashes.txt。没有发现本审计材料需返工的阻断；但工作台不支持会议回执仍是实际功能接通阻断，不能称整合功能完成。

## 独立证据

1. git逐一确认父提交链main3aba→178c998→a686→649d865→0a4bf22→3125eaf；工作台872815c与执行器共同祖先a686，两侧分别3/2提交。实际git apply --check完整工作台补丁失败，错误只涉及REQUESTS/ROADMAP；排除两文档后整个剩余补丁检查通过。未应用补丁，工作台目录仍不存在于当前树。
2. packet/engine/pi-runner与a686逐字节一致。packet固定SHA、3条主张字段白名单无gold/expected/reference标签；同一来源页与同一sourceText。没有借合并更换数据或引入参考答案。
3. 独立运行一次新Meeting→Bridge→Executor双轮4席：4个不同PID的实际Pi进程，退出0、组清理且领进程已回收；12次脚本model协议请求/8次tool。旧engine.run_group、_remote及Python socket.connect均设为立即拒绝，测试仍通过。未使用旧engine运行绕过会议预算；复用其冻结fixture/校验原语不等于执行旧run_group。
4. 在Bridge实际返回给脚本提供方的请求处捕获12份messages。每席起始仅固定system/user，无同轮/旧角色历史串入；read_packet响应精确为固定packet+meetingContext+contextDigest。前轮意见数0/0/2/2，二轮双方上下文相同且严格等于第一轮已接受scripted_simulation意见。没有legacy UI合成答案、referenceAnswers/expectedLabel/goldLabel/counterexample字段混入这些消息。上一轮脚本标签作为未核实意见保留，是会议定义的上下文，不是参考答案证据。
5. 调用冻结Git blob工作台探针，用独立构造且标记合成的旧result作正例；旧result可见，新完整回执/Meeting/Bridge对象和矛盾真实模式声明被拒绝，失败保留旧显示，fetch计数0。逐一比对探针编译blob SHA与872815c原对象。冻结旧工作台缺人工主张显示标签，另一个显示修订未在本审计中伪装合入。
6. shared_receipt_checks位于测试模块，docstring明确只检查已知完整脚本运行，不是任意导入接纳；research生产Python中没有调用它。真实适配器文档标题和正文明确尚未实现、不授权网络调用、不得绕旧_remote、usage未知不可填零、未真实验收不宣称通过。

## 复跑

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTRESEARCH_INTEGRATION/test_independent.py
sha256sum -c logs/EXPERTRESEARCH-INTEGRATION-impl-hashes-frozen.txt
```

独立7例与父协调者的99相关合跑分开计数；未重新执行全库。工作台DOM证据复用已冻结探针但独立检查输入、输出及Git blob摘要；不是全新原生浏览器验收。

## 未完成项与边界

这是审计，不是已合并、已接通功能。需要新版本回执schema、严格生产导入校验器及多轮UI，不能修改旧manifest/UUID或压平四席到两角色绕过验证。测试oracle不认证来源、签名、身份或任意导入安全。

实际Pi仍只有脚本提供方，真实DeepSeek未执行；12是协议计数，不是API次数、费用或token usage。对实际消息的检查证明本次公开固定输入边界，不证明模型阅读/语义质量。没有模型/网络/服务/公开监听/部署/推送；未读取真实密钥。原生浏览器、生产身份、案件权限、真实usage及持久预算/崩溃恢复仍未验收。远端adapter是设计提案，不是已有代码能力或新调用授权。
