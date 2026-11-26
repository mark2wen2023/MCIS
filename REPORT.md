# W11 隔离合成组合试点 — 官方验收记录

- 候选分支起点：`875ccc50b049fb24b82f6b0663f3f9476db1880e`
- 报告目录：`/workspace/mcis-w11-isolated-pilot-report`
- 官方运行（Asia/Shanghai）：2026-11-27 03:53:57 CST → 03:54:03 CST
- 退出码：0（`timeout --signal=TERM --kill-after=10s 150s` + `unshare -r -n`，先 `ip link set lo up`）
- 监听：仅 `127.0.0.1:18765`，未见 `0.0.0.0`
- HTTP 结果是 HTTP，不是浏览器结果
- 本项不是 W11 整包通过
- 未改产品源码、未改锁定脚本、未改图格式、未放宽权限、未写正式库、未合并、未部署、未触发本机以外安装或 NuGet

## 命名产物说明

任务括号中的 `/workspace/mcis-w41-core-out/mcis-core.dll` SHA-256
`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`
合同为 `mcis-core-build/1`，是 W4.1 对准/校时核心，不是 ECFC 校验器，未用于本次 validate。

实际使用的是按已验 `CORE_SOURCES` / `d9187fe` 配方、SDK 8.0.428、离线 `unshare` 构建的 `mcis-ecfc.dll`：
SHA-256 `f548818bd21c45d640293601f2ae271171c086f7e0b22912472a2d7dc771e75a`，
合同 `mcis-ecfc-build/1`，`coreVersion=mcis-ecfc-draft/1`。

## 复用方式

只新增 `tests_acceptance/w11-isolated-synthetic-pilot/`。
隔离装配取已有 186 文件钉扎树（含 `_read_original_for_access` 的 evidence intake 与权限/审计实现），
并复用 `host.setup` / `read_excerpt` / 既有 DDL·TRIGGER。
未改 `check.py`、`host.py`、`pilot.py`、`router.py` 或 `main.py`。

875ccc5 工作区现行 `evidence_intake/router.py` 已不再导出 `_read_original_for_access`，
因此不能把该工作区服务树直接替换钉扎装配。

钉扎 `create_app`（`source-export/service/mcis_service/main.py` SHA-256
`2c21e58417fe208462921543762eaf3a9c81e9fd40238be44de50e5a9ff28d93`）
未 `include_router(ecfc_drafts_router)`，故正式应用 HTTP 无 `/ecfc/preview` 与 `/ecfc/save`。
未改常规入口去挂上这些路由。草稿预览/保存走既有服务函数 `preview_sync` / `save_sync`
（与已验 `w11-real-core/workflow.py` 相同路径），在同一 `127.0.0.1` 进程内调用真实 `mcis-ecfc`。
摘录路由仅在试点进程 `create_app()` 之后由 `setup(app)` 注册。

## 门槛

1. 既有服务生成并保存现行草稿：通过。`coreVersion=mcis-ecfc-draft/1`，revision=1，
   digest=`2d1ce99dc5ca27cbe7171c4980742975ff22977d011c6d9b943bb19d67b54c63`；预览 `persisted=false`。
   ECFC 审计 2 条（revision 1、2）。
2. 显式读取只返指定图版本/边/已登记合成原文片段：通过。HTTP POST 试点路由 200，
   `excerpt`/`sourceUtc`=`2026-02-01T12:01:49.000Z`，`locator=/sourceBytes/97/121`；
   Public 与错误边 404；成功前保管链仅 Register，成功后为 Register, Access。
3. 改版或撤销后旧关联拒绝：通过。revision 2 后旧关联 HTTP 404 `SOURCE_UNAVAILABLE`；
   撤销后再读仍 404；未绑定的 revision 2 亦 404；拒绝读取未新增 Access。
4. T+109 只作原文记载时间：通过。记载时间为 `2026-02-01T12:01:49.000Z`；
   案件 `incidentTimeUtc` 仍为 `2026-02-01T12:00:00Z`。

正式应用未启用试点：独立 `127.0.0.1` 进程中 `create_app()` 不注册试点路由，
对该路径 POST 返回框架 404 `Not Found`（不是试点处理器的 `SOURCE_UNAVAILABLE`）。

未验：浏览器、真实案卷、4A、归档、3D、产品 HTTP `/ecfc/*` 路由、W11 整包。

## 固定 SHA（提交后补记）

- 候选 `candidate/w11-isolated-synthetic-pilot`：`6fe7777fbad84d60ed0854442734bebb967794b4`
- 证据分支名预留：`evidence/w11-isolated-grokbot-6fe7777`
- 已接评论：7201873406
