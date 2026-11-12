# TRACKHISTORY 独立裁定

冻结范围通过：独立48项+OpenAPI路由1项通过，知识归档既有独立70项回归通过，真实历史浏览器及明确模拟409状态检查通过。最终33SHA前后匹配。

## 修复原红项
旧发布服务恢复包后GET digest/list及同body commit错误返回活跃200/replayed:true。新1.3严格历史索引与不迁移local-proof使恢复后旧入口409；原CSV/report和链保全，新历史读取独立授权，不能解锁未知当前提交。

## 必须保留的限制
真实旧1.2 restricted恢复库升级后原报告正文可读、可导出1.3再恢复；原库report provenance解析旧W10 source.mcase现返回精确409 ARCHIVE_HISTORY_UNSUPPORTED而非误称完整性损坏，不自动迁移。真坏包及其它422仍INTEGRITY；真实浏览器确认兼容提示保留正文，权限403仍清除正文。旧本地无proof亦保守ORIGIN_UNVERIFIED，不表明旧写入失败，不应重提。身份/来源均非认证。

原权限排序疑点经真实旧库Deny测试未复现，authorize已先拦Restricted可见性，不列为漏洞。未测边界及测试自身定位修正见REPORT。私有复现与环境日志不发布。

## 最终错误分类补修
上一冻结将受限旧版本来源统称INTEGRITY，已按合同明确为精确UNSUPPORTED分支。独立升级API、原包损坏/其它reason回归及真实浏览器均通过；不是把旧包当已验证有效，也没有弱化权限。最终报告和哈希以33文件为准。
