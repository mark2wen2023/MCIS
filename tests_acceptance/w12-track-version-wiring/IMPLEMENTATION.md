# W12 同案换版：接线核查与最小候选实施说明

固定 SHA：`03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5`（以下未另标明的行号与哈希均对此针）。底版 `94d5e38c926fda232bb987b60fa9145e4bcf01a7` 上，下列登记航迹与分析服务文件字节与本针相同；`useAnalysisSnapshot.ts` 仅存在于本针，`AnalysisPage.tsx` 在两针之间有快照钩子差异。本轮不改产品，只说明后续最小候选应接何处。

## 1. 已存在的登记航迹身份

首次导入身份不是整数版本号，而是绑定摘要 `previewDigest`。

计算（`service/mcis_service/tracks_import/parser.py` 76–77、159–160 行；SHA-256 `c33fc940cb82118a8893ced81953b10ec1b3838526ad13aacc45a16d9c564aab`）：

- `previewDigest = sha256(canonical({metadata, sourceSha256, caseId, caseEpochUtc, operator, role, parserVersion: 1}))`
- 预览/回执同时给出 `caseId`、`vesselId`、`sourceSha256`

持久化回执（`tracks_import/router.py` 258–260、284 行；SHA-256 `a89a366d003c2a991a1ba48a76cf0e75fdc219de03ce7e46fe78bde1571c9eb8`）增加 `reportSha256`、`pointCount`、`sourceEvidenceId`、`reportEvidenceId`。本地标记表 `track_local_receipts`（`track_history/models.py` 3–11 行；SHA-256 `77e988b23a5e5522e244a6e2c5b0a87a324dae742ccc3a9b69f7fc90f6ab8c9a`）以 `(case_id, preview_digest)` 为键，仅追加、禁止更新删除。

只读读取同一批固定输入身份的现成 API：

- `GET /api/v1/cases/{case_id}/track-imports?vesselId=`（`tracks_import/router.py` 296–320 行）
- `GET /api/v1/cases/{case_id}/track-imports/{digest}`（323–330 行）
- 原件 `GET .../track-imports/{digest}/{source|report}`（333–344 行）

归档只读（不是当前活跃版）：`GET /api/v1/cases/{case_id}/archive-history/track-imports`（`track_history/router.py` 11–16 行；SHA-256 `5eb2e4be12b8df150f931d4f51c9caa81ec180c48f34a5e3b0d80960c24e6b0d`），摘要含 `digest` 与 `identityMode: unverified-self-reported`（`track_history/service.py` 73 行；SHA-256 `7e33fc744fd4ff7c4b17738d9f34079a7a6f94197c1d8723605e5fc4adee2655`）。历史回执不能当作本次保存或换版成功。

`GET /api/v1/cases/{case_id}/tracks`（`cases/router.py` 106–129 行；SHA-256 `8c1af5e9138d95c578bec6219debba063dbe90fefb5b434dcf6a8e56c8afe15f`）只返回 `caseId` 与按 `vesselId` 分组的点，不含 `previewDigest` / `sourceSha256`。`GET /api/v1/cases/{case_id}/cpa`（`colreg/router.py` 150–177 行；SHA-256 `11e72064fd10b3961ad6afb0f0bdbe2e0de4532b39d13f2cc1732412bec73d21`）返回 `caseId`、`coreVersion` 与 CPA 序列，同样不含登记航迹身份。`GET /api/v1/core/version` 是核心软件版本，不是航迹版本。

## 2. 换版动作：不存在

合同 `contracts/W10.2-track-input.md` 第 40 行（SHA-256 `51d2435d86553cdb869ded3642f20cfa5b515d76b869b6f06f7de51a220bc9de`）明确本切片为「首次保存且不支持后续编辑」；未来编辑须另定版本/原始与派生数据协议。

实现：`parser.py` 158 行在已有点数时发出 `TRACK_EXISTS`（「该船已有航迹，本切片不覆盖、不追加」）；`router.py` 243–244 行提交时以 409 `TRACK_EXISTS` 拒绝。不存在激活、替换或切换当前登记版的路由。因此「一案两版本」不能通过现有 commit API 持久化。本轮不新增该动作。

## 3. 分析服务可复用的计算/读取入口

运行时分析（`service/mcis_service/analysis/router.py`，SHA-256 `b3e91f7606b20da2c4ec1f07de396df0d041603dfbea694431a963f6e41bb4be`，与 94d5e38 相同）：

- `load_seed` 36–46 行：读离线 `data/w12-analysis-seed.json` 并按旁注自检
- `_meta` 49–52 行：输出 `seedSha256` 等生成元数据
- `GET /api/v1/analysis/cases` 55–60 行、`GET /api/v1/cases/{case_id}/analysis` 63–78 行：按种子案号/key 返回，不读登记航迹，不调用 CPA

可复用、但当前分析运行时未接通的入口（离线 `build_seed.py` 已引用，SHA-256 `b82788238d8a43b3f9637138e6875f8c9df6bb0ccfef5a9c6c00f169d07603be`）：

- 读点：`cases.service.track_points` / `state_at`（`cases/service.py` 28–69 行；SHA-256 `e17e1c5709ec510cf5e443961039092d0315ad64f0342c67c38de684c706ebdf`）
- 计算：`GET /api/v1/cases/{case_id}/cpa`（或同等 `_core(..., "cpa")`）
- 身份：上面的 `load_receipt` / `list_inputs`，不要另造一套摘要

前端 `derive.ts`（SHA-256 `abf69a5f53a6334e474b6af7278d4b29748128e1bcae5c11e7dc7832b6e05e53`）只格式化已返回的种子曲线，不取数、不计算 CPA。`types.ts` 的 `AnalysisMeta`（90–101 行；SHA-256 `608614a5ce1fafb39afa24e508ed4c169d2f116d969d0b81eab15c1d400a2f17`）只有 `seedSha256`，没有登记航迹身份字段。

## 4. 前端应失效的接点

`web/src/analysis/useAnalysisSnapshot.ts`（SHA-256 `ac9da6f6bc6fa8d01ff24aa3fc4247a6269a1bfe1756df109e607eb4e0a53910`，仅 03a8e786）：

- 作用域是 `JSON.stringify([caseId, role, operator])`（5、11、38 行）
- 切案、身份变化或显式 `reload` 会清空快照并增加代次，迟到响应不可写回（16–20、39–41、43–44 行）
- 列表与详情须 `seedSha256` 一致（26–31 行）
- **不读取、不比较** `previewDigest` / `sourceSha256`；同案换版若身份仍为同一 `caseId` 与操作者，钩子不会自动失效

`web/src/pages/AnalysisPage.tsx` 33 行（SHA-256 `793d8ebbcb30dddebbce27aa3843781f4cf60c99b0e013d57b34e6af10e3bfe2`）已写明：展示的 `seedSha256`「只代表本次读取，未确认登记轨迹实时版本」。

## 5. 首个断点

文件：`service/mcis_service/analysis/router.py`

- @ `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5`（与 `94d5e38c926fda232bb987b60fa9145e4bcf01a7` 字节相同）
- SHA-256：`b3e91f7606b20da2c4ec1f07de396df0d041603dfbea694431a963f6e41bb4be`
- 位置：`load_seed` / `_meta` / `list_analysis_cases` / `get_analysis`（36–78 行）

影响：分析 HTTP 只输出离线种子文件哈希，不输出与 `GET /track-imports` 同一批固定输入的登记身份。因此本轮不能用既有分析 API「直接读出版本」，也不把先前跨案/等候帧/窄屏结果当作换版通过。相关但非首个：同船换版动作本身不存在（见第 2 节），即使分析改接身份，一案两版本仍无法经现有 commit 持久化。

## 6. 最小候选实施说明（后续授权时，本轮不实施）

1. 分析读路径改为先取本案计算所需各船的当前本地回执（复用 `list_inputs` / `load_receipt`）。缺任一已验证来源则不返回分析结果（无源即无结果），不得回退到种子文件或旧响应。
2. 响应元数据携带与回执相同的身份：每船 `caseId`、`vesselId`、`previewDigest`、`sourceSha256`（必要时 `reportSha256`）。禁止把 `seedSha256` 称为登记版本。
3. 计算复用现有 `track_points` / `state_at` 与 `GET /cpa`（或同等核心调用），输入必须是上述身份对应的当前点。本说明不改 CPA 算法本身。
4. 前端作用域在案号与操作者之外纳入分析响应中的登记身份（各船 `previewDigest` 集合）。身份变化时：先清空并停用旧快照（沿用现有代次），再按新身份读取；旧请求不得写回新作用域。无源时只显示无当前分析，不保留旧指标。
5. 同船换版/替换写入是单独的合同与产品项（W10.2 已推迟），不在分析接线里偷偷放宽 `TRACK_EXISTS`。未另定换版动作之前，不得声称端到端「一案两版本」已接通。
