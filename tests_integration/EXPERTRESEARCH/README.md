# 专家研究整合审计（非已接通功能）

2026-11-14，隔离基线3125eaf；未合并研究分支、未修改远端、未调用提供方。

## 实际依赖与冲突

main 3aba2bf → 178c998 → a686c85；其后两条路径：

- 649d865会议状态机 → 0a4bf2协议桥接 → 3125eaf Pi子进程执行器。
- b2707a4旧单轮工作台 → 872815c状态一致性修订。

两条路径共同祖先为a686c85。新增运行文件没有重叠；REQUESTS.md、ROADMAP.md尾部追加上下文冲突，完整补丁apply --check失败，单独工作台运行文件检查通过。没有实际应用补丁，不能据此宣称合并成功或引入预览栈97项提交。

工作台不在3125eaf树中，仅接受旧单轮result.json。实测拒绝完整执行器回执、meetingSnapshot、bridgeAudit，并保留旧视图。不能伪造旧manifest/runId或压平两轮以通过旧校验器。

## 可复现的离线证据

需要固定Git对象（见test_integration.py常量）、Python pytest、Pi core/ai 1.5.2、Node、esbuild及HappyDOM。测试不会自动安装、抓取或联网。此环境依赖分别位于共享研究node_modules、web/node_modules和/tmp/mcis-ui-deps。

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q --tb=short tests_integration/EXPERTRESEARCH/test_integration.py
```

15项测试通过。实际启动4个Pi进程但仅使用固定脚本提供方；产生12次模型协议请求、8次工具调用，上一轮意见数量为[0,0,2,2]。每轮两角色contextDigest一致，仅完整上一轮意见可见。测试交叉检查ticket、上下文摘要、预算、事件链、退出与回收；7种篡改被测试oracle发现。oracle只检查已知完整脚本运行，不是生产导入校验器。

旧UI正例仅是明确标注的合成JSON形状，不运行旧engine；旧run_group、_remote和Python socket.connect在测试中禁止。模拟占位环境值不是密钥。Node提供方仍固定脚本；这些限制不等同OS网络隔离证明。

Meeting/Bridge的simulation_only/realPi=false属于协议层声明；Executor的实际Pi进程事件属于运行层证据，不能直接合并为一个布尔值。真实DeepSeek始终未执行。旧engine最多8次请求，会议预算16次，且当前回执没有完整提供方usage。12次脚本协议请求不是12次真实API请求，也不是计费信息。

## 来源显示与接通顺序

冻结packet的三条均为人工编写测试主张（含反例），同一报告PDF28/印刷26，不是三份独立证据。第二、三条不是报告结论。展示应分为人工主张、冻结报告逐字引用、各模型选取引文；逐字匹配也不认证语义正确性。来源PDF本轮未重新获取认证。

另一个隔离工作台显示修订保持packet/model/engine/runner字节不变，只添加上述显示标签和分区。逐条参考答案、预期标签、反例判定不进入模型提示；新会议中上一轮模型意见只能作为未核实意见输入。该显示修订不解决会议schema兼容。

建议顺序：先独审状态机/桥接/执行器 → 明确版本化整合回执和预算语义 → 独立实现严格导入校验器 → 接通多轮只读工作台及来源分区 → 浏览器验收 → 安全注入与独审通过后才进行真实公开材料调用。任何一个阶段失败不得伪造完成。真实适配器设计见REMOTE_ADAPTER_DESIGN.md。

未验证：真实提供方、计费/usage、生产身份、正式案件、原生浏览器/CSP执行。当前输出是整合测试与设计，不是已接通的真实专家会议。
