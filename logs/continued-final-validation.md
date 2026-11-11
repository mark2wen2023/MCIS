# 续作验证摘要

最新状态：2026-11-12 UTC+8 当前可复现核心与真实再生成seed已纳入，完整service **316/316通过**。下方旧315/1记录保留为历史，不是当前未解决失败。

源基线：c6113bee85d25bf97d805fb2d264fb6ab138b2e2。真实.NET8.0.428、Python3.12、Node24环境。被测数值引擎实际构建运行，不是替身。

| 范围 | 最终结果 |
|---|---|
| service完整pytest | 315 passed / 1 failed / 0 skipped，133.43秒 |
| W3独立.NET | 186 passed |
| W5独立.NET | 49 passed（原47保留） |
| W6.2真实核心/静态验收 | 99 passed（原95+新增4） |
| W6回环网络检查 | 4 passed（重复运行不重复计数） |
| W6浏览器+网络 | 原套件19/19通过（4网络+15浏览器），11.12秒；不再单独累加4网络 |
| 跨页真实浏览器 | 35/35检查通过，19张新截图，临时DB正确案件读写 |
| W12.1独立验收 | 21 passed（原18+新增3），真实CPA 2348点最大偏差0 |
| 报告/YANGZE专项 | 182 passed（已包含于本轮服务套件，不与315相加） |
| Web生产构建 | 通过；主包约1.5MB体积告警仍在 |
| Web组件/合同 | COLREG18+58、询问38、报告148、分析94断言通过；新增案件上下文28+引用目标30，总414断言 |

## 唯一全服务失败（不隐藏、不改断言）
`tests/test_analysis_w12.py::test_seed_sources_not_stale`
历史seed记录核心DLL SHA256：b0e507b80b41f2d3a5de0dd73adac2b070dd7310e2f9c52b65a6ab44b9b652f3。
本轮当前仓库源码重建DLL SHA256：e24783c5baa9f16d6e1142369c0564733c51d1a6c570ec53be66378beeed6e8d。
后续精确重建证实：W5.1改变CLI编译输入 InvestigationAudit.cs，此外路径/Git元信息也改变工件。恢复严格SHA核验的旧源码并映射原路径后，历史DLL字节身份已完全复现。独立2348点数值重算全相同，但二进制字节身份不同，不能称来源哈希已通过。其余seed来源（包括两份原始CSV）均按固定上游blob核验，不改seed及旁注掩盖这个失败。

## 验证命令与限制
- `MCIS_DOTNET=<dotnet路径> DOTNET_ROOT=<SDK目录> service/.venv/bin/pytest -q -rs -p no:cacheprovider service/tests`（实际从service目录运行）。
- 独立验收分别使用tests_acceptance/W3、W5的dotnet test与W6、W12的pytest；日志见相应RETEST/continued文档。
- `npm run build`、`npm test`、`npm run test:w5`、`npm run test:w16`、`bash tests/run-analysis-w12.sh`。
- 最新文件冻结：logs/continued-impl-hashes-frozen.txt。旧阶段冻结保留历史，后续已登记改动可能不匹配旧清单。
- 已有云端本地官方headless浏览器验收；无用户本机、移动端或Unity场景验收。不合并、不部署；PR保留草稿以明确未完成门槛。

## 2026-11-12（UTC+8）后续收敛
历史DLL精确重建与复跑见 core-dll-provenance-investigation.md、reproduce_historical_core.py。没有覆盖生产DLL、历史seed或放宽断言，原315/1服务运行仍如实保留。当前源码应通过可重现构建及合法重新生成链另立新基线，不能冒充历史生成输入。
浏览器限制已通过官方Chrome for Testing headless shell解除，见 continued-browser-validation.md。实际修复了全局案名、证据/建议跨案链接和写入目标，以及缺轨迹误请求CPA的问题。独立审查与回归覆盖案件切换、异步加载、请求目标。

截图交付限制：19张新截图已本地留档；上传审批未获许可，未重试或绕过。此PR仅包含代码及无图测试记录，截图待用户明确授权后另交付。


## 当前基线最终回归（2026-11-12 UTC+8）
- 原 seed 与 SHA 旁注逐字节保存在 service/mcis_service/analysis/data/history/w12-original-20261111/。
- 当前 CLI 固定 SDK 8.0.428、所有55个Compile源码+项目文件及recipe指纹、固定路径映射；多个独立Linux临时根构建DLL字节一致。不是跨OS/SDK保证。
- 既有 build_seed 实际生成新seed，14539数值逐项全同；W14 52值差异0，完整JSON仅时间戳与DLL哈希变化，独立审查后纳入。
- 完整service **316 passed，0 failed，0 skipped，131.91s**，原来源断言未放宽。首次因compat缺DOTNET_ROOT的315/1另留日志，正确环境全套重跑不是拼接结果。
- W6核心/静态99/99重跑；W12独立21/21，来源工具9项；报告Web148断言；当前新seed跨页浏览器35/35无JS/console/HTTP错误。
- W12旧Layout硬编码架构断言改为实际effect的14路由/失败场景，保留原用例及analysis专属fallback要求；未改数值断言。
详见 current-core-seed-candidate.md、current-core-independent-review.md、current-core-service-configured-pytest.txt、current-core-browser-summary.md。
