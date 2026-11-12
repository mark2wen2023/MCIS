# W5.2a 笔录原文访问隔离：独立验收

只用合成案件、人物、问答及哨兵文本，seed_demo=False。没有访问真实资料，没有改默认策略或产品实现，不涉及 W11。

## 独立结果

47 项可发布 API/数据库回归通过；另将原 private preview 越权红测按原断言重跑通过，不把该重复回归另加到47项。真实服务浏览器读写权限与迟响应测试通过。

- 12类权限分别Deny/Redacted，覆盖列表、详情、crosscheck、compare roster/detail、agent输入与案件包；preview请求目标Lead不能提升实际调用者权限。适用字段规则及坏策略拒绝，不回退。拒绝no-store且全业务表无变化。
- 来源仅其他案件存在、缺失、登记hash变化均拒绝，不静默重绑；笔录、compare、agent输入及包出口分别检查。
- signed笔录在五条追加/复核/比对写路径拒绝；旧create拒绝signed、非空问答、注入Confirmed陈述及客户端sourceSha256。空unsigned笔录可真实保存重开。没有新增录入UI，幂等与乐观并发接口属于后续切片。
- 四并发追加保存全部四条，轮次唯一连续。追加事务期间第二连接撤权被串行化，事务完成后新读取被拒。
- agent Modified最终payload由无关内容变为笔录引用时重新授权，拒绝且无写。模型使用明确的测试stub，不是真模型调用：调用期间另一连接可成功提交policy/source/transcript变化，随后403/409丢弃输出、不返回输出marker、不新建AgentDraft。
- 删除当前笔录、仅残留笔录审计的合成包，旧导入仍拒绝且目标数据库/案件目录无副作用。包是测试构造的合成归档，不来自真实资料。
- 真实浏览器连接FastAPI，默认Investigator拒绝；手动Lead可读取并刷新重开。真实IR-02响应被延迟后换IR-01/换身份，旧文本不复活；真实policy API撤权后切换笔录触发403并清空原文。无API doubles。

## 原缺陷与测试说明

修复前私有复现：Investigator testimony=Deny，直接GET403，而preview指定Lead返回200及合成marker。原始红测文件/日志保留本地、不发布；修后原断言通过，公开等价回归包含在测试文件中。

首轮47项前的测试准备发现包夹具缺incidentTimeUtc，补齐合成case时间字段后继续，未修改拒绝断言或产品代码。浏览器主动取消延迟请求时Playwright记录callback CancelledError，脚本退出0、产品pageerror列表为空、全部内容隔离断言通过；不将工具取消消息描述为产品失败或无条件全日志无误。

## 边界

22个冻结文件SHA-256复核一致。默认Investigator被拒是刻意兼容限制，不自动升级角色；本地角色自报不是认证。此切片不提供签字证明、全字段脱敏、专业事实确认、新录入表单、请求幂等或笔录完整备份恢复。含笔录/残留原文审计的旧包导入被拒绝，不能说已支持往返备份。

模型调用前授权点之后已经发送的字节不能撤回；模型期间不持全库写锁。测试只验证本地stub期间上下文变化后的丢弃行为，不宣称实际模型能力或外部网络行为通过。

## 可复现与发布

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/W52A/test_boundary.py
MCIS_BROWSER_BIN=<existing Chromium> python tests_acceptance/W52A/browser_real.py
sha256sum -c tests_acceptance/W52A/verified-impl-sha256.txt
```

需现有Python Playwright、Chromium和前端依赖，仅localhost监听。发布五文件：REPORT.md、test_boundary.py、server.py、browser_real.py、verified-impl-sha256.txt。不发布private基线测试、local日志。
