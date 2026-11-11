# HTTP core error boundary 独立审查

## 结论

允许作为窄 CoreError HTTP 呈现脱敏切片提交。审查未修改实现，仅新增独立测试。没有阻止此切片提交的缺陷；不表示旧 align 入口、身份认证或整个服务已安全。

实现变化只在 colreg.router._core 的 CoreError 分支。成功 envelope 不变，CLI/core_client 不变；已知领域错误保留 code/status、文本固定化，未知 code 统一 CORE_ERROR/502。未知错误码收敛与错误文字变化已在 CONTRACTS 明确披露，不能称所有失败字段逐字兼容。from None 防止 chained exception 被作为此 HTTP 异常上下文重抛。未更改网络、权限、数据库或原始报告。

## 独立验收

security_tests/test_http_core_errors_independent.py 新增12项：6个真实 Python core_client.run + subprocess 合成边界（缺失程序、超时、stderr、坏JSON、领域错、未知错误码），4种畸形 envelope 的非debug HTTP 无合成秘密回显，CPA成功响应原样，以及真实 create_app + fresh unseeded 临时数据库的正式 HTTPException handler 平铺错误body。没有执行真实 C#，没有读取真实敏感文件。

独立测试与作者17项一起执行：29 passed, 1 warning, 1.91s。警告是既有 starlette/httpx 弃用提示。日志 independent-test-log.txt。受测源码是固定 b667bf4 的 service/contracts 部分快照及本候选，不是完整clone，未跑全service、种子、报告、Web或C#回归。

## 保留边界

- 某些畸形 core envelope（null/list/非字符串code）仍能导致未捕获异常/500；默认非debug HTTP未泄露合成标记。这是既有健壮性缺口，不建议在本切片增加宽泛catch掩盖bug。
- 旧 `/core/align` 任意路径能力、无案件授权与客户端角色声明仍在；不因错误文本收敛而宣称文件访问已关闭。
- 成功路径中的任意结果字段、合同校验的错误detail不属本次 CoreError 脱敏覆盖。
- 真实程序、真正core错误与完整有种子服务流程仍需后续验收，不以mock替代。
