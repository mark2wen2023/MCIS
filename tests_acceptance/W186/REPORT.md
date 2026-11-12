# W18.6 HFACS 完整备份扩展：独立验收

本轮在恢复后的环境重新执行，不引用丢失环境的运行结果。全部使用合成数据，seed_demo=False；仅测试文件发生编辑，没有修改实现或触及 W11。

## 结果及范围

独立 20 项 API/数据库/真实 CLI 测试通过（19 项 guards，1 项长历史多次往返）；另完成真实浏览器 → 两个隔离 FastAPI 服务 → 真实 CLI 的下载、导入、重开及再次导出。没有使用 API doubles。未发现新增产品缺陷，没有删除或放宽红测断言。

- 连续保存 51 个不同草稿修订，实际导出包含全部 51 条历史及回执，不受审计 UI 最近 50 条限制。第二空库恢复后原 ID 保存返回 409；新 ID 更新到 revision 52，原历史不变。再导出至第三空库，current、完整审计、全部原回执逐项保持。
- 导入的历史请求仅在 append-only archive 表；active 请求表为空。数据库拒绝归档回执 UPDATE/DELETE。
- 同包双请求并发提交只有一次创建，另一请求返回 replayed 回执。随后 GET 恢复查询无新写入或重复审计。
- current 内容、前链、回执响应、额外字段、跨案、分类版本、缺失来源、缺失历史等语义篡改后重新计算 ZIP manifest，预览/提交仍拒绝，数据库无变化。
- 1.0.0 加 HFACS、未知 1.2.0、1.1.0 缺扩展、未知 HFACS 成员拒绝；旧导入端点拒绝新扩展。超过完整历史预算整体拒绝；真实 CLI 不可用时 503，无伪计算或部分恢复。
- 真实证据登记后，仅历史修订保留的来源变为不可读，导出被拒，且不追加导出审计。当前草稿仍可读，证明检查不是只看当前来源。
- 导出持有一致快照时并发保存：包包含完整旧版本，新保存随后成为 revision 2，无 worksheet/审计/回执混搭。
- 审计插入、归档回执插入、最终 DB commit 三处故障：完整业务表回滚，本次案件目录移除；解除故障可成功重试。
- 真实浏览器人工保存草稿，实际下载 1.1.0 ZIP；另一空服务界面显示历史回执归档范围及数量，必须勾选确认；导入后重开/刷新读回同一草稿；再次下载的 HFACS 备份对象与首次一致。

## 完整性和未覆盖边界

23 个冻结实施/合同/测试文件核对通过；7 个实际 HFACS 原核心依赖加入相对路径哈希清单。恢复环境中旧 `tools/mcis-core/out/mcis-core.dll` 不存在，因此本轮没有声称校验该 DLL，也没有构建它。

本报告不证明原始操作者身份、来源真实性、专业分类正确性或因果关系。原 request body 未保存，request_digest 仅作格式和归档关联检查，不能重算证明其真实性。完整重算的伪造历史不是本测试所声称能鉴别的对象。

只保证所验收的新受限入口；不声称所有旧版/Unity reader 能安全识别扩展。普通异常回滚不等于进程崩溃原子性、多进程部署安全或全系统备份。未覆盖真实非合成案件。

## 复现

配置已有 SDK 的 MCIS_DOTNET、可写 DOTNET_CLI_HOME、已有浏览器的 MCIS_BROWSER_BIN：

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/W186/test_guards.py tests_acceptance/W186/test_roundtrip.py
python tests_acceptance/W186/browser_real.py
sha256sum -c tests_acceptance/W186/verified-impl-sha256.txt
```

长历史往返逐项调用真实 CLI，约需两分钟，取决于环境。浏览器需要 Python Playwright 及前端依赖，仅启动 localhost 服务。公开文件：本报告、helpers.py、test_guards.py、test_roundtrip.py、browser_real.py、server.py、verified-impl-sha256.txt。不发布 PLAN 或 local 原始执行日志。
