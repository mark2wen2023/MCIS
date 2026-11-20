# 独立合成试用会话接线（未启用，待独验）

祖先 `247763cda3bac349ead5d1022101b3f8af5756c3`。参考工作台 `16eab9998ca9efe81b32ae9f82cf36511f0a3f01`、媒体 `33e0cebfd096cbdfeb1e29967fbe48a232758eb2` 均未改。新候选 `candidate/local-review-pilot`；不是主线部署，不接内网4A。

## 本次真实代码增量

`common/local_review_pilot.py` 提供服务器进程内 `PilotSessions`：受信启动器显式给入临时会话凭据 SHA-256→不可变主体/角色/到期时间/精确(case,operation)集合；默认没有条目，不生成令牌，不内置口令或可用凭据。保留副本，不从浏览器接收配置。每次 verify 检查同一进程单调时钟期限、撤销及准确案/操作；`revoke` 删除指定会话。未配置或未显式启用安装拒绝依赖，不能退回默认 Investigator。

`_install_local_review_pilot` 只给未来受限app显式调用，通过前一候选 `_install_verified_case_context` 接线。验证边界新增可选、装配方固定的 credential_reader；原 bearer 路径与默认拒绝行为保留。试用模式只接受Cookie，不接受Authorization混用，更不采信X-MCIS身份头、URL/localStorage。未来4A替换验证器及明确传输适配，不与试用会话混用。

本轮未注册路由、未启用任何factory、未导入main或初始化表。会话同样受前一候选15模板白名单约束；不放开案件列表、创建、overview或其他业务。原处理器的身份绑定、权限策略、证据/历史/修订/审计未修改。

## 浏览器同源方案及未完成部分

- 固定HTTPS origin，不能带路径/账号/查询。检查直接scheme、Host、Sec-Fetch-Site=same-origin；Origin存在时须精确匹配，所有非GET必须有匹配Origin。缺浏览器元数据时保守拒绝；不信任代理转发头，不新增CORS放行。
- Cookie名 `__Host-MCIS-Pilot`，固定建议属性 Secure/HttpOnly/SameSite=Strict/Path=/、无Domain；服务端拒绝缺失、重复、畸形Cookie和混入bearer。令牌不能进入页面、查询参数或JS存储。
- **还没有会话发放/浏览器引导端点。** COOKIE_OPTIONS 仅供后续受信引导响应使用，不表示属性已在真实浏览器设置。受信启动器须生成高熵秘密（如256位）、只把摘要及合成案授权留在服务器，通过经核验的受信通道给浏览器设置Cookie，绑定过期/退出/撤销；不可开放“按客户端自报身份领取会话”。本候选不提供任何可用试用凭据。
- HTTPS同源要求意味着仍需核对TLS与仅本机/授权试用地址方案；不改系统安全设置、不用关闭安全检查的HTTP降级。
- `SYN-` 案号只约束配置命名，绝不证明库中无真实资料。必须另验全新隔离库/目录、纯合成数据白名单；不允许给真实案件/生产应用装此身份源。
- 单进程内存表无跨进程同步/持久恢复。截止时间来自该进程的单调时钟，不可在重启时复用旧绝对值；撤销只保证后续核查，不能取消已通过验证的在途请求。外部授权与业务事务并非原子，不能声称并发/撤销全过程保障。

## 实跑（开发方）

```sh
python tests_acceptance/local-review-pilot/check.py
python tests_acceptance/verified-case-context/check.py
```

新增7组、相邻6组均退出0。仅标准库AST抽取定义，注入手写Request/Ctx/app与受控时钟；不导入FastAPI或应用。覆盖两合成案操作差异、角色头不生效、缺配置/未知/过期/撤销、重复Cookie/跨站/缺Origin/错误Host/HTTP/混合身份源、不同实例、配置格式、调用前拒绝和既有路由/依赖边界。测试字符串只存在内存夹具，未签发给任何服务；不是真实凭据、权限实测或HTTP认证。

## 下一步最小装配条件

1. 独立复核Cookie运输、验证器及原依赖适配；明确安全的会话发放引导和到期/撤销。没有这些不启用UI。
2. 受限路由注册需完整列明并验证：授权案发现须从会话授权集合逐案核对，不能调用当前全案 `cases.list_cases`；首次建案是否仅由受信准备器完成需定界。现有ctx白名单仍拒绝list/create。
3. 数据初始化仍未隔离：媒体只读核对注册虽然不挂任务surface，但仍有db全量registry及请求期动态完整性依赖；不能挂main/旧launcher或少建表绕保护。需保持证据、回执、历史拒绝及审计的真实依赖闭包。
4. 获准的隔离环境中再验证真实依赖解析/同源、两个全合成案（A仅登记回执、零运行）首次导入→保存→冲突保留草稿→刷新重开→切案无串案。此轮没有该运行许可、没有真实浏览器或原音检验。

未读案件/原件/seed/秘密，不运行应用、HTTP、DB/ORM、模型、播放器或暂停检查；不改契约、默认启动或其他分支，不合并部署。
