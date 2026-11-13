# 调查员非浏览器试验闭环：独立验收与 UI 接入设计

## 独立执行

独立审查者未修改产品和该测试。执行：

```sh
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh \
PYTHONPATH=protected-read/service mcis-work/service/.venv/bin/pytest -q \
protected-read/service/tests/test_investigator_trial_roundtrip.py
```

结果：1 passed，零跳过，0.87 秒；一项既有 Starlette/httpx 弃用警告。

检查 core wrapper 实际调用已有 .NET runtime 与 mcis-core.dll；本测试未替换 core_run，未使用模拟核心返回。保存经 ASGI TestClient、同库本地身份和实际 W2；随后读取已保存结果、相同操作 ID 重试、只读权限与会话撤销。

## 实际覆盖与边界

- 当前登记虚构单源 CSV，经实际 W2 保存，GET 返回相同 runId/caseId、当前 source SHA，sourcesImported=1。
- 结果明确 unreviewed / not_assessed；同一 operationId 重试回到原结果。
- 带 Origin 的浏览器式 POST 被拒400。
- 移除 save grant 后 GET 仍200、POST403；撤销 session 后 GET403且不输出 serverPreview。
- 最后只有一个结果索引和一个保存审计事件。

这是一条测试，不是独立核查新增三十多项测试，也不是全部工程回归。单源结果不证明冲突算法正确或独立证据互证。测试没有统计核心进程启动次数，不能凭本例断言读取/重试绝未启动核心；该性质由已有测试和本次静态代码检查支持。

重要：案件创建与证据登记是测试准备，仍借旧测试应用和旧角色头完成；subject/session/membership由可信测试host直接配置。因此不能称“整个调查员工作台已完成真实身份端到端闭环”。本例仅验证已准备本地数据后的受保护保存/读取路径，不是实际网络socket、浏览器、IdP、LLM、生产登录或部署验收。

## 独立 UI 设计结论

现有工作台不能立即接通这个试验 API。当前 Origin/Cookie拒绝、无浏览器登录/会话交付，旧 api.ts/intakeRequest 使用可修改角色头，案件/证据清单也尚未迁移身份入口。父任务已从远端 fa19715 核对 web/src/api.ts、align/registered.ts、RegisteredPreviewPanel.tsx、worksheet.ts；独立审查者看过本地对应历史快照，不另称逐字远端核验。

下一步可以独立开发不含凭据的 DTO、纯状态机与展示组件，默认 transport unavailable，不挂生产路由、不把Bearer放进浏览器/localStorage、不创建替未认证浏览器持有高权限token的代理。

状态应区分：未连接安全服务、可提交、保存中、保存结果未知（同一operationId重试）、已保存待读取、读取中、已读取未审核结果、权限失效/上下文变化/来源过期。保存成功不是读取成功；读取失败不抹掉已保存事实、不自动重算。案件、身份上下文、选中来源与声明变化立即清除旧结果并丢弃迟到响应。

保存GET封套应有独立 StoredUnreviewedResult 验证器。现有 RegisteredResult 是瞬时预览结构，不能人工补sourceBinding字段伪装复用。严格核对caseId/runId/请求声明/来源与父报告版本，仅投影已知展示字段，始终显示unreviewed/not_assessed/非写入凭证/核心实现未认证/关联仅人工声明等限制。不得增加人工审核或正式时间线准入按钮。

## 下一步验收清单

1. 双击只发一次保存；响应丢失保留同一operationId，不显示“确定未写入”。
2. 保存成功后读取403/409分别显示权限失效/来源过期；禁止静默重算。
3. 切案、身份切换、关闭重开、迟到响应、导航返回不能重新显示旧结果。
4. 跨案、错runId、错版本、缺字段、伪造approved状态均拒绝。
5. 无token持久化、旧角色头、Cookie或隐式旧API回退。
6. 纯组件测试标明模拟；未来独立认证适配器需要浏览器认证、CSRF/Origin、Host/TLS/proxy、可信案件/来源列表、限流与泄露面审核后才能接通。

未发现本测试范围内阻断项。未改产品、未推送、未合并、未部署。
