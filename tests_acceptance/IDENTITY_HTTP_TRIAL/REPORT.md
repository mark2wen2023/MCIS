# 非生产身份HTTP试验入口：独立验收

## 结论

本切片范围内未发现剩余阻断项。独立审查者未改产品，仅添加 `test_identity_http_trial_independent.py` 20项。被审查产品hash为 `01c4df4dd2605f1f70f6f36706b05d62d0dc3e1af05d04ed6e019ffcea3c99d9`。

## 本地执行与诚实边界

- 原始ASGI独立首批16/16通过。
- 最终主测试+20独立测试：36 passed、1 skipped；跳过的是需要显式实际W2命令的用例。
- 独立复跑真实W2时最初误把包含参数的命令字符串作为core可执行路径，36 passed/1 failed（503）。这是测试配置错误，不是已复现的产品缺陷。
- 改用现有 `/tmp/mcis-preflight-core.sh` 包装器，单独真实W2 HTTP用例1/1通过（3.51秒）。因此最终37个测试均分别验证；不将首批、复跑和最终数累加。

实际W2用例经ASGI TestClient→实际本地身份/SQLite→真实W2→持久化；不是实际网络socket、浏览器或LLM调用。其他计算由受控输出夹具模拟。

## 独立覆盖

原始ASGI多块请求超64KiB后停止接收；5000位Content-Length有界413；重复Authorization/Content-Type/Content-Length拒绝；单凭旧角色/操作人头不能授权；未授权请求不读取body；body接收期间会话撤销后403且无保存；具体export/audit/access-policy/evidence路径、尾斜线、双斜线、编码路径无旧路由回退；unknown授权/保存异常不泄漏token/路径；timeout固定408；disconnect不保存；合法Bearer与伪造角色头并存时审计采用本地subject而非伪操作人。

静态审查建议的“检查chunk长度后再extend”已被实现者采纳，避免超过预算后才复制大chunk；最终产品按该顺序执行。没有声称执行真实内存压力/慢请求十秒压力测试，timeout测试是注入TimeoutError。

## 保留限制

唯一POST试验路由，不挂载旧应用；默认protected入口和CLI仍未启用此试验。拒绝所有Origin/Cookie是非浏览器试验限制，不是完成浏览器登录/CSRF设计。provisioning仍需可信host；TLS、Host/proxy约束、生产容量/限流、IdP及管理员管理、浏览器、CI、全系统尚未验证。旧应用若单独暴露仍不受本入口保护。无合并、无部署。
