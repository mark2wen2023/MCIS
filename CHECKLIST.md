# 校验清单

- [x] 已核对并检出 2447b14076bbf39db014b8bf4a3a3b350cbf0e05
- [x] 已读 AcciMapStampAcceptanceTests.cs 与 AcciMap.cs
- [x] 原测例 xunit 依赖本地已备，AcciMap 无 UnityEngine；执行方法=原套件
- [x] 只新增 tests_acceptance/w15-accimap-core/；未改核心/Web/主入口/契约/归档/权限/原 W15 测例
- [x] SDK 8.0.428 与 nuget locals 预检；unshare -r -n 离线 restore/build
- [x] 未安装、未接外部源、不伪造初始化
- [x] 官方 150s 外超时退出 0；restore/build/test 0；9/9 Passed
- [x] 覆盖分层关系与信息流分别保留，以及无效端点由核心标出
- [x] 未跑真实案卷；未用网页组件
- [x] 保留原始输出、断言、退出码、工具版本、源码/二进制指纹、SHA256SUMS
- [x] 不把本子项通过说成 W15 整包通过
- [ ] 令牌扫描、推送、待复核、表第 42 行：打包时补记
