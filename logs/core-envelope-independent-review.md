# Core envelope 类型边界：第二切片独立审查

结论：可作为独立窄健壮性修复提交。没有阻断问题。审查者只新增测试，未修改 core_client 或 router。

## 确认行为

在读取 `.get`、错误码hash查表或返回结果前校验顶层dict、ok严格bool、失败error dict及code/message字符串、成功result dict。此前可能 AttributeError/TypeError 的畸形输出现在稳定产生 CORE_BAD_OUTPUT/502，并经第一切片HTTP映射去除核心自由文本。合法成功外壳及附加字段原样；已知领域错误码/状态不变；空错误dict、缺code/message仍保留原默认。

missing error、falsey非dict error、整数/字符串ok、非dict result从宽松处理改成502，属于已明确声明的无效外壳收紧，不是所有JSON逐字兼容。合同成功响应result为对象，故没有发现合法合同被新检查拒绝。

## 独立测试

新增 tests_acceptance/HTTP_CORE_ERRORS/test_core_envelope_independent.py 共22项：17种畸形输出经过真实 create_app/全router注册/正式HTTP异常handler，断言502而非500且不回显合成stderr/字段；4种合法错误字典缺字段默认；1项前导构建文本+末行JSON+扩展字段保留。所有进程返回是synthetic subprocess mock，无实际C#程序或真实秘密读取。每个HTTP用例用全新无种子临时SQLite。

全 HTTP_CORE_ERRORS 目录75 passed，1 warning，3.10s；这是前53项+新增22项。日志 envelope-independent-log.txt。警告是既有starlette/httpx弃用提示。不是完整service、Web或.NET验收。

## 未扩大保证

不校验command/coreVersion/result业务schema、未知扩展、exit code与ok一致性或非有限数值。不修改CLI本身；变化位于Python调用器。未覆盖OSError/PermissionError等其他异常。旧HTTP align文件路径入口和身份风险仍在，不可因此部署。
