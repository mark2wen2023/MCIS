# W20.2 独立验收（2026-11-12）

## 裁定

**通过本片限定范围验收；未发现阻塞性缺陷。** 不等于真实模型质量、全站无障碍或生产安全认证。

最终组合基线：W20.2 冻结实现 + W10.1 `8fce05a65b3df0364819207d749c50ce6f86be8b` 的精确共享前端变化。验收只写本缺陷单、`tests_acceptance/W20UI/`、`logs/w20ui-independent*`，未改冻结实现。开始/最终结束8项SHA256均匹配。

## 独立证据

- 独立浏览器断言 **30/30 PASS**：`logs/w20ui-independent-browser.log`。使用真实 FastAPI/SQLite、既有W20提取/审核/笔录接口及本机HTTP假模型；所有材料合成。
- 合同回归 **4/4 PASS**：`logs/w20ui-independent-contracts.log`。这是执行仓库既有合同测试，不将其宣称为新独立断言。
- 冻结证据：`logs/w20ui-independent-hashes-before.txt`、`logs/w20ui-independent-hashes-after.txt`。
- 1365px桌面、390px移动截图仅保留本地临时输出，已人工查看，未提交PNG。W20面板移动列折叠、按钮/勾选可见，长文本换行且不执行HTML。现有W5下方面板移动显示较拥挤，本片不宣称改造全站移动布局。

## 已验证边界

1. 六角色登记五个未连接，people_ops配置不被写成已验证健康；注入未配置/非法配置登记响应后不可执行。
2. 键盘启动、逐条含义/引用勾选后明确确认；确认前原笔录无陈述，确认后仅追加1条并刷新W5计数；驳回理由必填且不追加。
3. HTTP假模型失败不创建草稿；真实后端SOURCE_CHANGED、ALREADY_REVIEWED拒绝不会伪报成功。
4. 实际后端403独立于按钮存在与否；AgentService实际审核403，UI可读取但不可确认。服务账号不在普通角色选择器中，测试通过开发模块设置该身份，未冒充生产登录。
5. 防双击一次POST；异步返回时切笔录、身份、同页案件均不会显示旧结果。
6. 已提交但响应丢失后锁定；读取不重发，需要操作者核查确认后解锁；不匹配成功响应同样不能声称成功。
7. 跨案队列响应拒绝展示；双条候选必须每条勾选；恶意HTML作为纯文本显示；390px无文档横向溢出；无浏览器运行异常。

## 注入与限制

- 配置状态、队列跨案/双条/HTML、响应丢失/不匹配通过Playwright响应故障注入验证UI，不能替代对应真实部署环境测试。SOURCE_CHANGED、ALREADY_REVIEWED、403、模型HTTP失败及写回均走真实后端。
- 没有提供真实LLM：模型名 `controlled-http-fixture-not-real-LLM`，只验证协议和安全审核闭环，不验证推理准确率、泛化或真实性能。没有使用或外发真实用户笔录。
- CUA无法连接后依照任务授权使用工程Playwright fallback。未验证实际屏幕阅读器、触摸设备、多浏览器或完整WCAG；键盘只验证本片主流程。
- 页面会话写锁不是服务端幂等键；整页重载、多标签及跨设备恰好一次不在保证内，UI已有提示。
- 测试夹具复用实现方提供的服务启动样板，断言独立构造。此前两次中断是验收脚本等待条件和服务账号选择方式问题，修正测试后在最终组合基线完整重跑，不修改实现以适应测试。

## 复现

参见 `tests_acceptance/W20UI/README.md`。执行 `bash tests_acceptance/W20UI/run.sh`，需允许loopback socket和本机Chromium；路径按脚本位置解析，端口动态分配，临时数据/截图隔离。Playwright/Chromium可通过README所列环境变量选择。无需真实模型、无需密钥、无需外部服务。

## 发布前夹具可复现性整理

移除固定私有workspace与工具路径，ROOT按脚本位置解析；Playwright/Chromium通过环境参数或已安装默认package/browser选择。所有运行数据及截图默认系统临时目录，artifact目录可覆盖，PNG不入库。保留原30项断言，整理后在同一最终组合基线完整重跑。
