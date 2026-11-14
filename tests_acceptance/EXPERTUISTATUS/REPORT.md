# EXPERTUISTATUS 独立验收

通过：9个独立合成DOM场景，network=0；冻结3/3一致。测试源independent.mjs，执行输出results.txt，冻结hashes.txt。复跑 `node tests_acceptance/EXPERTUISTATUS/independent.mjs`。

独立覆盖：remote零received但receiptComplete=true仍仅称未声明收到响应，显示尚未开始/无席次；人工停止、失败停止、未知停止、超时停止四种状态都有中文，切到缺席第二轮不造意见，返回第一轮保留真实存在于输入的两侧不同标签和引文且不掩盖全局停止；unknown/not_accepted角色无引文、回执不完整明确；两轮完整MockHTTP仅称模拟协议，切轮只显示所选轮次rationale与角色引文，固定报告引用不变；合成恶意img只以文字出现。伪造remote零received但realDeepSeekExecuted=true由展示parser拒绝。

所有场景检查不再无条件宣称转换器已校验，明确页面不能证明执行过转换，计数/模式/摘要未认证。9场景是独立用例计数，不与开发43断言混加。

另逐字核对model.ts、meeting.ts、export.py、public-packet.json、engine.py、pi-runner.mjs与父c137ea2一致，见unchanged.txt。未改原文或模型输入、未执行模型/服务/网络或读凭据，未修改实现。

限制：输入是明确合成展示投影，非真实模型响应或原回执全链验收。本轮没有独立重复22项Python导出回归。父协调者报告受支持Playwright sandbox启动在导航前失败（SUID helper/crashpad），未绕过；本独审未重复原生浏览器。HappyDOM不能证明原生布局、键盘、辅助技术与CSP执行。真实调用HOLD保持，UI文字改善不认证提供方身份、语义能力或事实。
