# EXPERTCONNECTED 独立验收

隔离目录 `/workspace/mcis-expert-connected-workbench-20261114`，基线6f8f429。范围为schema2复合回执验证→展示投影→独占HTML及同app多轮显示。独审只新增本目录及DEFECTS，不改实现或冻结。

## 初验与返工

初验10Python用例通过（其中1项运行8DOM场景）。父实现者随后自查展示parser计数不足，独审以真实验证投影变更5种矛盾全部复现被接受：完成角色调用数超过received、not_started非零计数、ready带已完成轮、round_review有两轮全部完成、round_open全席完成。原0/5红测见parser-initial-results.txt，测试parser-boundaries.mjs保留。Python完整原回执validator不受此漏洞影响；不声称受控原回执导出可绕过完整验证。

C01：embedded会议已显示但role=status沿用“尚未载入结果”，已要求准确显示已载入只读会议视图。

## 独立覆盖

- 使用已保存的实际4Pi/12MockHTTP worker回执 `/tmp/mcis-connected-mock-receipt.json`，重新通过完整validator并实际调用node --meeting导出HTML。没有重跑Pi/模型。原回执逐字不变，投影/HTML包含其原字节SHA；输出权限0600，CSP含connect-src none。
- 输出已存在（包括等于输入）拒绝覆盖，原始字节不变。输入/父目录symlink、FIFO、输出symlink拒绝；fd保持基线。两个并发发布仅一方成功；中途短写后失败不发布最终路径且清临时文件。
- 原回执篡改mock真实标记在调用builder前拒绝。
- 实际合法投影进入HappyDOM；两轮切换各自显示独立观点，第一轮不读取同伴/第二轮完整上一轮语义清楚；固定报告引文与双角色选择不同子串分区，三条人工测试主张同页非独立证据。
- 恶意rationale/uncertainty仅文字，无script/img/iframe/a节点。partial未知轮不补造第二角色，切回已完成轮不掩盖整体未知；禁用旧文件导入时不冒充legacy格式，清空后恢复旧入口且无自动模型请求。
- 页内明确只读、不授权新模型调用、不重放全部回执及mock非真实模型验收。HOLD为投影固定true及明确禁止授权语义；不是要求所有UI必须展示英文字符串HOLD。
- model.ts保持固定原blobhash；packet/engine/Pi runner与6f8f429逐字节一致，未将答案/反例解释注入模型输入。

## 限制与复跑

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTCONNECTED/test_independent.py
```

测试依赖上列/tmp公开mock回执。若文件缺失应重新用经审查的显式MockHTTP流程生成，不得替换为未声明来源的“真实”结果。DOM partial/恶意文本是对展示投影的明确合成变更，不是声称其有对应真实提供方回执。

没有真实网络、模型、凭据、服务或推送；没有重试原生浏览器。HappyDOM不能证明实际浏览器文件/CSP/键盘/布局策略。已有Playwright sandbox启动失败仍未解决。展示摘要和完整validator只证明本地一致性，不认证来源/模型身份/语义质量；展示投影浏览器不重放全部回执。当前内存回执非持久化预算，真实调用HOLD不由HTML解除。

## 最终 r3 裁定

对最终 `logs/EXPERTCONNECTED-r3-impl-hashes-frozen.txt` 复核12/12项一致，见r3-hashes.txt。独立原断言与C01加载状态断言全部通过：**12个pytest用例，1.25秒**，其中包含8个DOM子场景与5个parser边界子场景（不重复计作pytest总数），见r3-results.txt。

D01五项原失败断言原样保留，r3全部拒绝；C01实际DOM确认显示“已载入只读会议视图”。在本次离线显示/导出范围内无剩余阻断，可提交此本地候选。此结论不扩大为真实模型能力验收、原生浏览器验收或真实调用授权；HOLD保持。父实现者的开发测试计数未在本独审中重复执行。
