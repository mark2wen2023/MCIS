# 历史浏览器验证障碍：已解决（2026-11-12，UTC+8）

以下为修复前的历史记录，不代表当前验收状态。经授权改用同一进程树中的官方 Chrome for Testing Headless Shell 157.0.8103.50 后，本地浏览器可运行；最终 W6 原套件 19 passed，跨页 35/35，console/HTTP 无错误。未改变系统安全设置，仍仅监听 127.0.0.1。

最终结果、官方来源与 SHA256：[浏览器验收报告](continued-browser-validation.md)。[原始 W6 输出](continued-w6-browser.txt)。[逐项结果](continued-browser-result.json)。仍不代表用户本机、移动端或完整项目验收。

---
## 修复前记录（保留审计）

# 当前本地浏览器验证限制

先尝试CUA云浏览器连接只监听127.0.0.1的独立临时服务，连接拒绝；不同exec会话也不能互访该回环端口。未把监听扩大到0.0.0.0或添加隧道。

经本次测试授权，改运行项目已有本地E2E，将服务和浏览器放进同一个pytest进程树：4个网络检查通过，15个浏览器项失败。实际原因是Chromium启动即报`ProcessSingleton socket() failed: Operation not permitted`，无有效DOM或截图，不是已确认页面逻辑错误。提升执行权限仍相同；官方Playwright headless shell下载返回无效ZIP，未获得可运行浏览器。没有修改系统安全设置或项目依赖。

因此未验证报告、W5、W6、W12当前页面实际渲染/交互/控制台或1440/1920截图；只报告静态组件、请求合同和真实后端结果。归档图片仅核对历史尺寸和SHA，不是新视觉通过，更不是用户本机/移动端验收。
