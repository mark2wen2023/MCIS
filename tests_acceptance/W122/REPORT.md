# W12.2 独立验收报告

## 结论

**后端/API/数据库/真实 C# 数值与前端模型/SSR限定范围通过；浏览器交互验收阻塞，不能宣布 W12.2 完整通过，不合并。**

测试只使用合成临时数据，不修改真实案件、原W12基准或实现，不部署、不提交；没有触及W11。本次为当前案件已存同刻点CPA切片，不是完整W12或整体验收。

## 冻结与复测

- 集成基线：`80fad29`。
- 冻结清单：`logs/W122-impl-hashes-frozen.txt`，86项。
- 独立复测开始与结束各校验一次：**86/86一致**，测试期间冻结实现未变。
- `test_independent.py`：**47/47通过**，仅1条依赖库弃用警告。
- `ui_run_model.sh`：**36个独立断言通过**，包括2个错误信息中文映射断言。它们不是36个浏览器测试。
- 真实C#在47项内调用：独立解析几何对照、40组固定随机向量（属于1个测试，不额外叠加计数）、退化及微小负TCPA舍入为0。
- 原W12 seed SHA256：`988e9abd3b39959864f42912d8d3454dacd7821156fd8b21268631f30f4693e3`，与原`.sha256`一致。

## 已验证范围

- 非虚构flag；Measured/Interpolated/ManualDrawn/Simulated及缺来源原样保留；反向插入仍按存点时间排序，不宣称采集顺序。
- 近似但不严格相等的时间不配对；UTC格式与精度、负秒、±10^12窗口、索引与doc不一致、缺COG不能用HDG替代、重复点；无点/无公共时刻不调用核心。
- 每船5000预算独立验证；局部原点纬度边界、跨日界线、超100km拒绝。
- 核心错序/错船/非有限/布尔冒充数值/巨大整数拒绝；退化标志与输入相对速度一致、退化距离自洽；核心风险字段不返回。
- 核运行中输入损坏、删船、删案、破坏纪元、超过预算返回409；权限撤销403；非法权限值拒绝。无部分结果。
- 重复调用结果稳定；所有数据库表前后逐表比较无变化。
- UI模型拒绝错案/错船/错窗/错计数、重复/非有限/无效UTC，来源枚举与XSS转义、空表、2000绘图索引上限/端点；SSR与中文错误映射通过。

## D01–D04复核

| 缺陷 | 返工后证据 | 状态 |
|---|---|---|
| D01 运行期间坏输入/消失错误分类 | 两组midflight参数化用例，409/403及无rows均通过 | 关闭 |
| D02 核心退化标志未核验 | false_degenerate、equal_velocity两例及真实退化/微小负TCPA通过 | 关闭 |
| D03 元数据错误仅显示代码 | CurrentAnalysis使用readError的接线静读；FORMAT/METADATA_LIMIT中文映射断言通过 | 代码/模型范围关闭；实际浏览器错误态仍未验 |
| D04 巨大整数500 | 4种存点字段返回422、核心巨大数返回502，共5例通过 | 关闭 |

## 浏览器阻碍和未验范围

`ui_accept.py`准备了真实Vite/Chromium+合成API拦截场景，但Chromium通过正常工具审批仍在启动时报`socket() Operation not permitted`。**浏览器断言实际执行0项，无截图。** 已停止，未换浏览器二进制或绕权限。

身份/案件/输入/模式变化与迟到响应、重复点击、导航/Back、pagehide、实际图表和分页、1440/1920布局与空错态交互尚未实证。真实BFCache/关闭恢复及真实HTTP+核心整链浏览器也未完成。模型/SSR或实现方自测不能替代这些证据。必须在允许本地socket的批准环境完成独立浏览器复验后，再讨论完整验收及合并。

## 复现

在仓库根目录执行。`MCIS_DOTNET`指向已安装且获准使用的dotnet；如需独立运行目录，可预先配置`DOTNET_CLI_HOME`和`NUGET_PACKAGES`。

```bash
sha256sum -c logs/W122-impl-hashes-frozen.txt
export MCIS_DOTNET="$(command -v dotnet)"
PYTHONPATH=service service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/W122/test_independent.py
bash tests_acceptance/W122/ui_run_model.sh
sha256sum -c logs/W122-impl-hashes-frozen.txt
(cd service/mcis_service/analysis/data && sha256sum -c w12-analysis-seed.sha256)
```

浏览器脚本保留供获准环境使用，不在当前受限环境再次尝试。原始机器日志及缓存不随报告发布。
