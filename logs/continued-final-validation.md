# 续作最终验证摘要

源基线：c6113bee85d25bf97d805fb2d264fb6ab138b2e2。真实.NET8.0.428、Python3.12、Node24环境。被测数值引擎实际构建运行，不是替身。

| 范围 | 最终结果 |
|---|---|
| service完整pytest | 315 passed / 1 failed / 0 skipped，133.43秒 |
| W3独立.NET | 186 passed |
| W5独立.NET | 49 passed（原47保留） |
| W6.2真实核心/静态验收 | 99 passed（原95+新增4） |
| W6回环网络检查 | 4 passed（重复运行不重复计数） |
| W6浏览器 | 15无法实测：Chromium启动socket EPERM，无DOM/截图 |
| W12.1独立验收 | 21 passed（原18+新增3），真实CPA 2348点最大偏差0 |
| 报告/YANGZE专项 | 182 passed（已包含于本轮服务套件，不与315相加） |
| Web生产构建 | 通过；主包约1.5MB体积告警仍在 |
| Web组件/合同 | COLREG18+58、询问38、报告148、分析94断言通过 |

## 唯一全服务失败（不隐藏、不改断言）
`tests/test_analysis_w12.py::test_seed_sources_not_stale`
历史seed记录核心DLL SHA256：b0e507b80b41f2d3a5de0dd73adac2b070dd7310e2f9c52b65a6ab44b9b652f3。
本轮同源重建DLL SHA256：e24783c5baa9f16d6e1142369c0564733c51d1a6c570ec53be66378beeed6e8d。
生成的AssemblyInformationalVersion包含本地源码物化提交号；历史工件与当前构建环境/元信息不同。独立2348点数值重算全相同，但二进制字节身份不同，不能称来源哈希已通过。其余seed来源（包括两份原始CSV）均按固定上游blob核验，不改seed及旁注掩盖这个失败。

## 验证命令与限制
- `MCIS_DOTNET=<dotnet路径> DOTNET_ROOT=<SDK目录> service/.venv/bin/pytest -q -rs -p no:cacheprovider service/tests`（实际从service目录运行）。
- 独立验收分别使用tests_acceptance/W3、W5的dotnet test与W6、W12的pytest；日志见相应RETEST/continued文档。
- `npm run build`、`npm test`、`npm run test:w5`、`npm run test:w16`、`bash tests/run-analysis-w12.sh`。
- 最新文件冻结：logs/continued-impl-hashes-frozen.txt。旧阶段冻结保留历史，后续已登记改动可能不匹配旧清单。
- 无当前浏览器视觉、用户本机、移动端或Unity场景验收。不合并、不部署；PR保留草稿以明确未完成门槛。
