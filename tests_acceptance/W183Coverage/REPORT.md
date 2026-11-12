# W18.3 覆盖声明修正：独立验收

结果：通过。独立 5 项真实 CLI/API 合成测试通过；另以 4 组合成记录完成真实浏览器 → 服务 → C# CLI 联调。没有使用真实案件资料，服务关闭演示数据初始化。测试仅确认技术输出及边界披露，不作法律裁定。

## 实际观察

- 24 小时记录中三段休息 6+4+1 小时：休息总量 11 小时；没有 RestSplit 偏离。界面、服务明确总休息段数未评估，最长两段时长检查不等于总段数判断。
- 5 小时完整标注休息：24 小时及 7 日覆盖均为 false，findings 为空。页面明确即使列表为空也不能判断合规，未返回数据不足条目不表示资料充分。
- 两段休息间隔 15 小时：有 RestInterval 条目。人工插入 1 分钟 Rest 后该条目消失。服务及界面明确短 Rest 未经专业认定，不能证明间隔被有效打断，也没有新增所谓法定最短休息阈值。
- 原 assumptions 原文仍保留，包括历史“均判合规”措辞。展开前有醒目非结论提示；展开处再次注明原文仅供核查，不能超出未评估边界解释。
- 四种输入均经实际 API 与独立 CLI 逐项对比结果相同；assessment 仍为 technical-preview-only，persisted=false。

## 不变边界

本次仅验收声明修正，不改变核心计算或法律阈值，不证明模型与法规等价，不认证真实人员工休合规，也不复验完整 W18.3 身份/并发/出处生命周期。那些属于既有独立验收范围。

原 RestHours.cs 及既有 mcis-core.dll SHA-256 与 W18.3 已验收清单一致。冻结范围及相对路径见 `verified-impl-sha256.txt`。独立验收未发现新增产品缺陷，无失败断言被删除或放宽。

## 可复现

仓库根目录，配置既有 SDK 的 `MCIS_DOTNET` 与已有浏览器的 `MCIS_BROWSER_BIN`：

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/W183Coverage/test_coverage.py
python tests_acceptance/W183Coverage/browser_real.py
sha256sum -c tests_acceptance/W183Coverage/verified-impl-sha256.txt
```

浏览器脚本需要 Python Playwright 与已安装 Chromium，启动仅监听 localhost 的隔离服务及前端。复用 `W183/test_rest.py` 中合成夹具，不采集旧测试。原始本地运行日志不随报告发布。
