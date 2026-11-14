# PUBLICREPORTTEXT 独立验收

审查范围：main `3aba2bf03e393909c611489ae573a887087637ac` 上 Document 回执的公开报告本地待解析交接。实现冻结后独立审查；未改实现、分支或远端。

## 初次结果

原冻结 `logs/PUBLICREPORTTEXT-impl-hashes-frozen.txt` 6/6 SHA-256 匹配。独立20具名用例，16通过、4失败。D01 三条已声明导出字段变化失效失败；D02 下载元素创建异常泄漏对象URL。断言及失败输出原样保留在 `independent.test.tsx`、`initial-results.txt`，裁定见 `DEFECTS/PUBLICREPORTTEXT.md`。

## 验证内容

- 实际生成 Blob 并读取文本、JSON.parse 回读；双摘要/原来源/Unicode/特殊字符原样保留，完整固定状态检查，不导出人员字段/备注/原文件。
- Verified、Mismatch、NeedsReview、Unverified 四种证据字节状态均不升级为事实确认或已提取。
- 受控类别、明确布尔声明、坏摘要/证据关联/日期/长度/来源/文件名/危险URL拒绝。
- 正常导出、连续重复、声明撤销、取消、对象URL创建失败、点击异常、元素创建失败。检查内容确定性、输入保留、没有自动重试或额外fetch。
- 8种回执字段变更失效，包括跨案、跨证据、版本摘要、原字节摘要、metadata、文件名、字节数、登记UTC。
- 挂载正式 EvidenceIntakePanel，以合成 GET 回执通过现有真实解析逻辑，进入handoff并导出实际Blob；切换身份清空。fetch仅为内存替身，未启动服务/发网络请求。
- 只读核对 EvidencePage 的案件/选择/身份 key 边界及正式面板仅新增 import+挂载两行；现有服务或访问控制实现未改变。HEAD和merge-base均为main3aba。

复跑：仓库根执行 `bash tests_acceptance/PUBLICREPORTTEXT/run.sh`。使用仓库 esbuild、React 和预装 HappyDOM；测试bundle在本目录生成。

## 限制

这是合成DOM及实际本地Blob内容验证，不是浏览器下载磁盘成功证据。实现者提供的 `logs/PUBLICREPORTTEXT-browser-attempt.txt` 显示启用沙箱 Chromium 在导航前因 SUID helper/crashpad 配置退出；独审未绕过沙箱或重复启动服务。未验收真实文件选择、浏览器下载策略、键盘/布局/辅助技术。

未调用模型、OCR、解析器、外部URL或生产API；不宣称模型能力、真实身份认证、来源公开性或内容真实性。HTTPS URL只是未访问字符串声明；标题/来源可含人名，必须人工核查。原件及完整回执未包含，交接不是签名、可恢复备份或完整摘要重验工具；后续消费者不存在，须另行获取原件并校验。没有验证真实生产权限策略或完整保管链，也不认为已有header身份成为认证。本次未重跑全库、提交、推送或部署。

## r1 最终裁定（2026-11-14）

实现者完成最小返工后，独审原20个具名用例原样复跑：**20 passed / 0 failed**。实际输出 `r1-results.txt`。新冻结 `logs/PUBLICREPORTTEXT-r1-impl-hashes-frozen.txt` **6/6 SHA-256 匹配**，输出 `r1-hashes.txt`。

D01 的文件名/字节数/登记UTC变更现清空声明；D02 创建元素失败不再分配Blob URL；C01 UI已明确“提取人/登记人字段”不导出、标题/来源可能含人员信息。缺陷关闭，受限独立验收通过。以上限制不变：不得把合成DOM通过解释为真实浏览器下载、认证、公开性核实或正文提取成功。

测试计数不与实现自测混计：独审20个具名用例；实现者另报告35条新断言、88条旧W4.2回归和build通过，独审未将它们算作自身新增用例。

## r2 URL限制独立复验（2026-11-14）

前次只读审查对象提交 `c862419c8c2fb5d51fdf505c00afaecdccb30ae7`，8种地址均被接受并原样导出；这8项是行为复现，不是安全验收通过，且没有网络请求。原证据复制到 `sourceurl-initial-review.md`、`sourceurl-initial-results.txt`、`sourceurl-initial-repro.cjs`。历史复现脚本依赖当时编译的 `/tmp/PUBLICREPORTTEXT-sourceurl-model.cjs`；如重新复现，必须使用c862419版本的model.ts及其依赖编译，不能用r2替代旧版。

根据明确的新支持范围裁定，原20个具名用例全部保留，成功流程的来源从带query/fragment改为 `https://example.org/报告.pdf`。旧原值保留为 `legacySource`，新增独立拒绝断言；没有静默删掉原输入覆盖。

最终独立 **36 passed / 0 failed**（原20 + 新16具名用例），见 `r2-results.txt`。新冻结 `logs/PUBLICREPORTTEXT-r2-impl-hashes-frozen.txt` **6/6匹配**，见 `r2-hashes.txt`，复验后再次匹配。

新增验证：
- 初始8个loopback/private/query-token/localhost/IPv6/numeric-IP/fragment-token复现值全部拒绝，函数与完整交接入口均拒绝。
- 原合法带参数值转为拒绝；空?/#、普通查询及页码fragment同样拒绝，符合保守支持范围。
- localhost/local/localdomain/internal/lan/home.arpa本身及子域、大小写/根点变体、单标签拒绝；缩写/八进制/十六进制/percent/fullwidth IPv4、IPv4-mapped IPv6及公网IP literal也拒绝。
- Unicode域名/路径、编码后的路径字符保持原样；%3F/%23作为路径字符不当作查询或fragment，不意味着内容已脱敏。2000字符允许、2001拒绝。
- 接受的普通域名/含合成路径token地址仍严格 `fetchAuthorized=false`、`urlVerification=not-performed`、`verified=false`；不假装字符串过滤已识别所有秘密。
- DOM中逐一输入原8例和旧query/fragment地址：拒绝后不分配Blob、不点击下载、不调用fetch，保留输入；改回支持的Unicode路径需重新声明，实际Blob回读含新增false/not-performed字段。
- UI明确完整路径可能有敏感信息、不授权抓取、域名仍可能私网、不得自动联网。

裁定：D03当前有限字符串入口及文案返工验收通过，没有新增阻断。它仍不是SSRF网络防护、公开性认证或秘密检测器。未执行DNS解析/联网/模型/服务；已有导出文件不会被追溯修改，旧v1缺少新增字段也不能被未来消费者当作授权。历史与新JSON均未经签名；未来抓取必须另行授权和服务端防护。本轮未重跑全库或浏览器，原浏览器/真实身份/磁盘下载限制不变。
