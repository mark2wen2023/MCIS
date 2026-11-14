# 问题卡隔离试验 HTTP：独立验收

独立审查者未改产品，新增 test_issue_http_independent.py 21项。
最终独21+主16联合：37 passed、零跳过、28.10秒；一项既有Starlette/httpx警告。

```sh
PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q \
 issue-journal/service/tests/test_issue_http_trial.py \
 issue-journal/service/tests/test_issue_http_independent.py --disable-warnings
```

## 实际发现与修复

首18项17通过/1失败。命名空间判断使用 `'/issues' in path`，误拦截caseId以issues开头
的原有来源目录路径 `/api/v1/trial/cases/issues-example/sources`，得到404而不是交给
目录入口按案件授权返回403。实现者改成case之后完整issues路径段匹配；回归保留并通过。
此次真实复现使用不存在/无权限case的目录请求，并未另建名为issues-example的有效案件；
路径段匹配修复及目录正常授权机制共同解决该命名碰撞。

## 独立覆盖

- 无IssueGrant时POST在读取body前403，流读取计数0。
- 重复Authorization/Content-Type/Content-Length、伪role/operator、Transfer-Encoding
  拒绝且不读取body；40000字节多块流第二块超限413，不继续接收第三块。
- 接收请求体时撤销IssueGrant，最终403且没有事件写入。
- 嵌套JSON重复key、请求路径/正文issueId冲突、创建revision覆盖、append revision0拒绝。
- disconnect不写；注入TimeoutError得固定408，未执行真实十秒慢请求压力测试。
- 未预期写异常返回“保存结果未确认、同operation重试”代码，不回显token/路径/正文。
- 原件字节损坏HTTP409，不泄漏提交意见；无案件成员身份读list/detail/foreign统一403。
- 未显式初始化journal时HTTP503且数据库中两表仍不存在，没有自动安装或发grant。
- 默认protected_app对新路径仍503；HEAD、编码/双斜线/尾斜线变体不读取body或返回正文。

主16项另覆盖真实SQLite HTTP创建→幂等重放→核实→讨论→读取/list，以及撤销write grant
后仍可read、会话撤销后read拒绝、Origin/Cookie和精确路由等。测试覆盖有重叠。

## 诚实边界

实际临时SQLite与文件、ASGI TestClient/原始ASGI，不是网络socket、浏览器、IdP、LLM或
W2执行。此模块只记录工作意见与核实/讨论历史，不自动批准事实或时间线。可信host仍须
显式初始化、配置账号与IssueGrant；不存在生产登录、前端会话交付或浏览器集成。
不挂旧应用；旧应用若另起仍不因此得到认证保护。问题卡归档恢复仍未纳入此切片。

最终本切片未发现剩余阻断项。未推送、合并或部署。

## 最终产品 SHA-256

- investigation/http_trial.py: 365c4cfe698f67b925903e6af89606dd4aea1b8406b6340f1b7b18b3a0bced52
- identity/http_trial.py: 41d548f215fb8d610c70e5ee564d1aa7715c12eee602e1da7e64aba018c0f786
