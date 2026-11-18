# UI + PR104 固定候选交接（仅合成复验，禁止合并/部署）

这不是 main、生产版本或可直接使用真实案件的演示。分支是 `test/report-review-service-ui`；禁止接入真实资料、正式数据库、凭据或模型。不要把根 README 下方的通用快速开始当成本候选验收步骤，不要运行 `run_dev.sh`、默认种子服务或全套测试。

## 固定版本和拉取

- 已限定独验的测试头：`f7f4070bbc31756930662b29ad58d96c5680efd9`。
- 直接父提交（UI 三组 + PR104 产品组合）：`9cc3ecee7251b6f19a739c14ce316740c048594e`。
- 产品组合输入：UI `139f18849b89a451cd1198635bd571c00571a579`、PR104 `b4df82306d9bab87b938b9e447e27a64b0464406`；共同主线基线 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。这些是本次固定依赖，不代表未来 main/PR 最新头。
- 本指南是上述测试头之后的文档更新，未改变产品或测试；不要把文档后续头称为新的独立功能验收。

在自己控制的、尚不存在的目录检出；以下为交接命令，本轮未另做全新联网安装验证：

```bash
git clone --branch test/report-review-service-ui --single-branch https://github.com/mark2wen2023/MCIS.git mcis-ui-review
cd mcis-ui-review
git checkout --detach f7f4070bbc31756930662b29ad58d96c5680efd9
git rev-parse HEAD
git status --short
```

确认完整 SHA 精确一致且工作树干净。分支有新提交也不得自动把它当作同一已验版本；检出失败、权限拒绝或版本不符即停止，不换途径绕过。固定旧头内没有本后续指南，请保留本指南链接用于阅读。

## 依赖与唯一限定复验命令

需要 Python 虚拟环境 `service/.venv`、`service/requirements.txt` 所列依赖，以及 PATH 上的 Node 和本检出 `web/node_modules` 中的 React、react-dom、esbuild；前端依赖以 `web/package-lock.json` 为准。服务 requirements 使用范围约束，并非精确锁定环境。既有开发执行复用了已安装依赖；全新安装、其他操作系统及离线安装未验。缺依赖时按单位正常流程准备并记录版本，不降级保护、安装模型或绕过网络限制。本节点不需要 .NET/HFACS、浏览器或办公软件。

仅当依赖就绪，从仓库根目录运行这一项：

```bash
service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_report_review_service_ui.py::test_synthetic_sentence_patch_response_reaches_parent_view
```

不要替换成整个文件夹、全仓或旧验收批次。Node 子检查由此节点启动并通过 stdin 接收临时合成响应，不单独拿空输入运行。pytest 自动使用全新临时目录/SQLite，代码显式 `seed_demo=False`；无需配置服务地址或数据库，不复制生产环境配置。测试不监听端口，不打开浏览器，不生成报告，不调用模型。临时目录会包含合成数据库，不提交这些运行产物。应用初始化经 `Database.create_all()` 注册全部 ORM 表并创建既有追加表触发器，包含 HFACS 相关表；这不等于调用 HFACS 业务或核心，本限定节点未调用 HFACS 核心。

## 已验与未验

协调方报告：在固定 `f7f4070` 上，限定独立复验通过。开发侧同一节点也通过（1 passed）；两次结果不相加。实际 FastAPI TestClient 正常 PATCH/GET，保留现有权限检查；保存的来源、原文、引用、修订与审计得到核对。真实返回章节随后回放给实际 ReportSession 父回调并用 ReportView SSR 检查显示。

协调方后续独立复核反馈（对应固定产品组合头 `9cc3ecee7251b6f19a739c14ce316740c048594e`，不是本次文档头）：

| 验证范围 | 开发侧记录 | 独立复核归属 |
| --- | --- | --- |
| 19 个限定 UI 脚本 | 通过 | 已独立复核通过 |
| 新增继承引用提示 SSR（三语言、15 断言） | 通过 | 已独立复核通过 |
| TypeScript 与 Vite 构建 | 通过 | 已独立复核通过 |
| 6 个后端纯格式化参数案例 | 通过 | 尚未独立复核，不纳入独验通过范围 |

上述归属依据协调方反馈；本次仅修订交接说明，没有重跑。原组合 `DEVELOPER.md` 保留执行当时的开发记录，不应将其中当时的“待独验”文字误作最新验收归属。

必须保留的边界：

- 合成报告是通过 schema 校验后写入的测试夹具，不是报告生成/导入验收，没有虚构生成审计。
- 前端是捕获响应回放及合成 hooks，不是实时浏览器连接；refresh 后完整重挂载、跨页、失败/提交未知和并发未验。
- 使用现有 LeadInvestigator 角色头测试约定，未改策略；这不是可信生产认证，也不证明生产权限完整安全。
- 实际浏览器、视觉、读屏、真实后端完整业务、全量 CI、HFACS、真实模型未验。旧 LibreOfficeDev 记录不是 Word，也不是本次视觉验收。
- 上表是不同类型和版本的有限证据，不相加，也不与历史 558/560 项累计；历史批次含已暂停节点，禁止照抄运行。暂停、安全/拒写探测继续禁止。
- 复杂归档恢复仍受原保护，不能因本测试通过宣称案件闭环或生产可用。

详细材料（固定头内可读）：

- [正常复核响应回放记录](../../tests_acceptance/report-review-service-ui/DEVELOPER.md)
- [UI + PR104 组合范围与测试](../../tests_acceptance/ui-pr104/DEVELOPER.md)
- [精确组合来源及 blob](../../tests_acceptance/ui-pr104/inputs.json)
- [本节点冻结清单](../../logs/report-review-service-ui-impl-hashes-frozen.txt)

若出现非预期响应、权限错误、依赖或安全拦截，保存脱敏错误和版本后停止；不要修改角色策略、自动重试未知结果或扩大测试范围。
