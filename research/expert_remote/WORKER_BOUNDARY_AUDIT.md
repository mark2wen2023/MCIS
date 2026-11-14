> 2026-11-14 更新：专家旧raw-key在线入口已默认拒绝；下文旧在线能力描述仅为历史。参见 research/expert_remote/RAW_KEY_HOLD.md，真实运行仍HOLD。

# 真实 worker 路径离线审计（EXPERTWORKERBOUNDARY）

基线 f296f3d，2026-11-14。真实 DeepSeek 请求为0，平台安全绑定HOLD。本轮只运行合成凭据与MockHTTP、安全进程测试，不读真实凭据、不改环境或网络配置。

## 当前实际路径与阻断

官方 [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments) 描述网络秘密为占位符交付，获准 HTTPS:443 请求经代理替换；直接变量会向程序交付值。当前不能把旧 proxy_header_injection 实验当作此平台机制。managed.platform_binding 仍无条件拒绝；无可验证的父进程/worker bootstrap，没有把环境JSON或人工ready当信任证据。

Executor remote → Adapter(remote) → isolated.request → 固定Python worker → transport.request 是现有raw-key路径：key经stdin，不进argv/Pi消息；worker净化环境、stderr丢弃。它仍存在，HOLD不是全局阻止网络。managed尚未接Executor/配置回执，worker重新resolve也会拒绝；程序没有代理端原始秘密，不能宣称能检测它的响应回显。仅配置代理变量或域名放行不证明绑定已完成。

## 已复现与修复

父版本允许响应content/id/model精确回显传入credential，可能进入Pi后续上下文/回执。共用transport现在在JSON解码后检查所有字符串（含对象键），匹配传入credential即拒绝整份响应；JSON转义不能绕过，worker只回静态response_invalid，不释放成功结果。已派发保持unknown，预算不退款，Adapter停止且不能重试。此为精确匹配防护，**不覆盖编码/分片/变形秘密，也不能识别程序未知的代理真实密钥**；错误上下文不输出响应内容，不声称完全DLP。

固定目标字面值校验从managed扩大至所有transport模式，在客户端创建前拒绝非https、其他域名、额外端口或query。正常目标固定https://api.deepseek.com/chat/completions（默认443），trust_env=False、follow_redirects=False、单次请求不变。红测通过替换模块ENDPOINT模拟配置漂移；现有外部请求没有URL参数，这不是已发现的用户URL注入，也不防有权改写Python代码的攻击者。

## 取消与预算边界

Adapter共享总计16请求、每角色4；Bridge工具总32/每角色8；调用前预留且未知不退款。Adapter计算总600秒/角色120秒deadline；isolated以同一单调时钟deadline和cancel轮询处理进程，超时回收自有组；worker HTTP也使用绝对deadline。子进程所有权仍要求独占reaper及稳定SIGCHLD；本轮不扩大保证、不改所有权代码。没有持久化重启预算恢复或货币上限，回执只证本地一致性而非真实提供方认证。

127项相关测试通过：新增11（5回显含JSON转义、4固定目标、worker输出、Adapter预算停止）；原transport/managed/bootstrap/Adapter/Pi-remote取消和硬deadline回归。Pi-remote仅MockHTTP，不是DeepSeek能力验收。新测试以socket禁止真实连接，worker main合成stdin和MockTransport；既有硬deadline测试用受控本地子进程。真实平台代理/CA注入、可信配置交付及真实多轮能力仍未验。
