# W16.2 完整报告访问边界：独立验收

仅使用合成案件与哨兵文本，关闭演示数据初始化。没有读取真实事故资料；没有改变默认权限策略或实现。本切片是保守访问拒绝，不是脱敏或身份认证。

## 独立结果

49 项真实 API/数据库测试通过，包括真实 PDF/DOCX 渲染下载。真实浏览器会话及下载隔离复测通过。

- 十二权限类别各测试 Deny、Redacted、缺项，共 36 项；读取/新建均拒绝，完整业务表无变化。
- 默认 Investigator 对报告列表、详情、历史、snapshot、两种导出、GISIS、全局审计、案件包和写操作均拒绝；默认 Lead 可生成、复核、读取审计及导出。
- PDF 具有有效文件头，DOCX 实际 document.xml 含合成修改内容。全文审计实际保留合成 reason。
- 适用字段规则、未知方法、null 策略、非法权限值、缺角色行拒绝，不回退默认。
- 仅 report_draft=ReadOnly 可读不可写；拒绝无新报告/审计。先 gate 后 case_info：无权限时不调用被注入异常的 case loader；有权限内部异常返回无敏感异常文本的 500/no-store。
- 仅留 ReportAuditRow 而无 ReportRow 的案件包仍拒绝；旧报告标记审计、完整 line/reason 不通过全局审计或案件包泄漏。伪造 RPT-ID 的建议历史路径不返回报告原文。
- 真实第二连接在 DOCX 渲染暂停时更新政策，直到受保护响应构造结束前不能提交；随后收紧政策生效，详情返回 403。这是事务线性化，不是声称撤回已交付字节。

## 浏览器及测试修正说明

实际服务而非 API doubles：默认 Investigator 被拒，手动切到 Lead 后真实生成报告、读取审计，实际下载 DOCX/PDF；拦住真实下载响应后切换身份，旧下载不触发且旧审计清空。通过真实政策更新接口撤权，再请求报告，已验证界面清空并禁用导出。

首轮浏览器末步误将 lang 参数重复追加，未改变组件读取的首个 lang，因此等候新请求超时。已保存原本地日志，将夹具改为替换现有 lang 参数，未改产品或降低拒绝断言。

## 边界与复现

本次独立真实浏览器验证身份切换及撤权；换案/同案换报告迟响应属于实现侧浏览器测试覆盖，未计入本次独立真实服务场景。

19 个冻结文件的相对路径 SHA-256 见 verified-impl-sha256.txt。未声称全项目回归、真实身份认证、字段级脱敏、法规/事实认定，或已经下载文件的远程撤回。普通 evidence 原件出口不是本次生成报告出口完整性声明的一部分。

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/W162/test_access.py
MCIS_BROWSER_BIN=<existing Chromium> python tests_acceptance/W162/browser_real.py
sha256sum -c tests_acceptance/W162/verified-impl-sha256.txt
```

需现有前端依赖、Python Playwright、已安装 Chromium。所有服务仅 localhost。发布白名单：REPORT.md、test_access.py、browser_real.py、server.py、verified-impl-sha256.txt；不发布 local 日志或 PLAN。
