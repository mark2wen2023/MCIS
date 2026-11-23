# ECFC 正式预览／保存／重开：隔离验收入口（实际保存待跑）

仅测试侧代码，默认只预检；没有生产入口、身份授予、图关联服务、HTTP、App、浏览器或自动执行。父提交 `325d318109ad02f16ea7926301bbfde0a713089d`。不要将预检成功算作图已保存或关联已接通。

## 固定来源和边界

- 登记、原件读取、数据库及权限等白名单模块：`db90fdf73de7bd26ba75819f0102fc03d0789faf`。
- 原 ECFC router/models 与 CLI/build/C# 核心：`d9187fef1f979866ac4d8ce2064d1ac92f34bb36`。
- 原样 communication.txt：`b61aa93128ceb0cbe80ce9204579d35c7d31497d`，SHA-256 `418be9609b46a00062c41fb49073911986098e9a61e010f4311aa86946ecd3ea`。

逐普通 Git blob 核验、物化到自动清理的独占临时目录。所有模块/核心路径明列在 check.py；缺对象即失败，设置 GIT_NO_LAZY_FETCH=1，无联网补对象或安装。固定来源混合是本工装的显式组合，不代表某个产品默认树已集成。mcis_service 导入白名单在导入前安装，未物化 main/models_registry/seed/reports.service，不替换模块、不抽取业务函数；不使用仓内默认数据库。

## 直接复跑

在本候选仓库根使用已有包含 SQLAlchemy/FastAPI/jsonschema 的 Python：

```bash
/absolute/existing/python -I -B tests_acceptance/ecfc-direct-synthetic/check.py --repo .
/absolute/existing/python -I -B tests_acceptance/ecfc-direct-synthetic/check_preflight.py
```

第一条仅验证固定源码、原件 SHA/UTF-8 字节定位、真实 Python 模块依赖及正式 validate_body；EV-001 在这里仅为输入校验样例，运行阶段从真实登记结果取 ID。输出必须有 `databaseCreated:false`、`coreRun:false` 和 PENDING。第二条分别跑真实预检、缺 Git 对象拒绝及未显式提供 SDK 的运行拒绝，不模拟核心。

只在正常运行条件下，另显式执行：

```bash
/absolute/existing/python -I -B tests_acceptance/ecfc-direct-synthetic/check.py --repo . --run --dotnet /absolute/verified-sdk/dotnet
```

SDK 必须是已核官方8.0.428，准备见 `docs/ECFC-LOCAL-TOOLCHAIN-HANDOFF.md`。工装不下载安装SDK，不调整系统权限，不清NuGet缓存。使用新临时CLI目录、空本地restore源、禁NuGet audit及遥测；原 launcher 自行构建原核心。必须真实 `run_core` 冒烟成功、manifest源码及产物匹配后才创建SQLite。失败返回1，不会改用手写核心结果。当前云环境已知 NuGet-Migrations mutex 阻塞，不为这份工装重复尝试；应在合格环境运行。

## 显式运行路径的断言（本轮尚未实跑）

1. 新临时库显式建10张必要真表及原只追加触发器，不调用全量 create_all。仅case/policy是透明的合成基础工装；合成 LeadInvestigator 采用原 default_policy，不修改实际账号或权限。它不是登录验收。
2. 原 preview_input/commit_input 登记原字节；来源列表由真实 context 读回。正式 validate_body、preview_sync、save_sync、get_draft 直接调用，无 HTTP transport；没有手写证据、图、审计或回执结果行。预览零图写，保存后新会话回读同一revision/digest，核验1张当前图、1条版本审计、1条请求回执。
3. 保留普通 Investigator 读取拒绝。用真实保存结果和登记回执构造**测试宿主**关联，内部重新核图/最新审计/来源，显式调用一次 `_read_original_for_access`；返回pin/原字节/UTF-8区间[97,121)一致，成功事务提交1 Access，审计链有效且图未修改。

T+100仅游标，不以手工秒填图；节点timeSeconds均未知。T+109只是原文时刻，不推事件顺序、因果或Seek。生产可信关联/撤销/UI仍未实现；本次不能替代9fff9bc已有的选择/错pin回滚测试，更不能把两套测试拼成产品闭环。

没有报告或绑定保存、归档/导出、真实资料、模型、4A。ECFC保存本身仍触发既有案件归档限制。本轮只验证可跑的预检；正式生成/保存/重开/Access组合未运行，相关断言可能仍存在待合格环境发现的问题。输出错误只含有限错误类别，不输出原件正文或原异常日志；成功测试记录也不是生产认证或永久关联。
