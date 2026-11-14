# PUBLICREPORTTEXT sourceUrl 只读独立审查

对象：`/workspace/mcis-report-text-handoff-20261114`，HEAD `c862419c8c2fb5d51fdf505c00afaecdccb30ae7`。
日期：2026-11-14。本轮无源码/仓库文件改动、提交、网络、服务或模型调用。git status --porcelain 输出为空。

## 实际复现

将当前 model.ts 用已有 esbuild 编译到 `/tmp/PUBLICREPORTTEXT-sourceurl-model.cjs`，执行 `/tmp/PUBLICREPORTTEXT-sourceurl-repro.cjs`，结果 `/tmp/PUBLICREPORTTEXT-sourceurl-results.txt`。

8/8 合成用例证明“接受并原样导出”，不是8项安全验收通过。fetch/http/https请求入口设为抛错计数，networkCalls=0，无真实秘密。

| 输入 | publicSource | textHandoff.publicMaterial.sourceUrl |
|---|---|---|
| https://127.0.0.1/report.pdf | 接受 | 原样 |
| https://192.168.1.1/report.pdf | 接受 | 原样 |
| https://example.org/report?token=SYNTHETIC | 接受 | 原样 |
| https://localhost/report.pdf | 接受 | 原样 |
| https://[::1]/report.pdf | 接受 | 原样 |
| https://2130706433/report.pdf | 接受（URL解析主机为127.0.0.1） | 原样 |
| https://0x7f000001/report.pdf | 接受（URL解析主机为127.0.0.1） | 原样 |
| https://example.org/report#access_token=SYNTHETIC | 接受 | 原样 |

所有导出仍保留 verified=false、user-declaration-only，未改变未解析/未核实状态。

## 证据和裁定

- `web/src/reportTextHandoff/model.ts:3-9` 只检查长度、空白/控制/反斜杠、可解析URL、HTTPS、非空主机及userinfo账号口令；没有主机地址范围、query或fragment内容限制。函数名publicSource不构成公开地址证明。
- `model.ts:21` sourceUrl原样写入JSON。`Panel.tsx:29-31` 声明要求字段适合公开处理，但未明确提示地址自身也可能含临时凭据。`docs/PUBLICREPORTTEXT.md:5-7` 已说明不访问/不认证及未签名交接，但未明确禁止后续消费者将该字段当网络许可。
- 当前路径没有URL抓取调用，不能据此声称已复现SSRF、外发、密钥失窃或实际公开发布。当前风险是用户可能把含令牌或内网信息的地址原样保存在可转交文件中，以及“公开来源”的名称使下游误认为已通过安全校验。
- 前次20/20受限验收没有覆盖这些URL类别；它证明当时列出的功能边界，不证明公开主机识别或SSRF防护。本次是新增未覆盖边界，不改写历史计数。

## 最小保护建议（尚未实施）

1. 先补无需网络的文案与合同：sourceUrl定义为“用户声明的、未认证的来源定位字符串”，既非公开性认证，也非网络抓取授权。现有verified=false/basis保留；不要通过新增true标记声称host已核实。
2. 在本地输入阶段拒绝显然不适合此公开交接片的目标：localhost及其子域、规范化后IP literal。若选择仅拒非公网IP而保留公网IP，必须完整覆盖IPv4/IPv6、映射地址/保留范围，不能只用`127.`或`192.168.`字符串前缀。对此小切片，更小且易审的工程规则是明确“只接受DNS主机名，不接受任何IP literal或localhost”；这会拒绝部分合法公开IP来源，必须说明是支持范围限制，仍不证明DNS名称公开。
3. 对URL自身的秘密最小明确防线：至少拒绝明显凭据参数（token/access_token/api_key/signature等，键名按解析后的值不区分大小写，query和fragment均考虑），并在输入旁要求人工核查完整地址，不能声称关键词扫描能识别所有秘密。令牌还可能藏在未知参数名、路径或子域。若本轮追求简单、可证明的保守规则，可将query/fragment暂列不支持，要求用户自行取得稳定公开链接；会影响正常文档检索参数或页码锚点，须先确认产品取舍。不要静默去参数、脱敏后冒充原始来源或自动修复URL。
4. 加对应单元与DOM测试：规范化数字IP、IPv6、localhost、凭据参数大小写/编码、fragment；拒绝后保持输入且不下载，改变地址需重新声明。任何规则变更应新冻结，并明确保留原20例中合法带query/fragment测试或经裁定更新其期望，不能悄悄删断言。

建议直接显示：

> 来源 HTTPS 地址（仅记录，不访问；未验证为公开地址）
> 请使用稳定公开链接。地址本身可能包含内网信息、登录令牌或临时签名；请核查完整地址，不要填入此类内容。此声明不授权任何后续工具访问该地址。

建议声明文案：

> 我声明材料、交接字段和完整来源地址均适合公开资料处理，且地址不含凭据或临时访问令牌。系统不认证此声明、来源公开性、作者或事实。

建议合同追加：

> sourceUrl是不可信定位声明。接收器必须忽略其作为访问许可的含义，禁止自动抓取。当前语法检查、用户勾选、双摘要和verified=false均不能代替下游网络安全策略。旧profile及既有导出可能含内网地址或凭据；下游须对每次使用重新校验，不因其来自MCIS或曾通过导出而放行。

## 后续若增加抓取的独立门槛

应另立接口/授权与验收，服务端逐请求校验目的地；不能复用浏览器publicSource作为SSRF白名单。必须处理解析后IP及所有DNS答案、DNS变化/连接目标绑定、IPv4/IPv6保留/本地/私网地址、重定向每跳、代理与凭据继承、超时/大小预算以及网络出口限制。默认不跟随重定向或每跳重新审批校验；不上传来源URL到其他模型/服务，不自动打开浏览器链接。只增加字符串黑名单不等于完成上述保护。

本轮结论：所要求3例全部复现，附加5例也接受；当前没有网络利用路径证据。建议先落实定位声明/凭据提示和下游禁止自动抓取合同，再独立裁定主机/参数支持范围并补拒绝测试。无实现或提交。
