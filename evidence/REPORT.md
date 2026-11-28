# W9 船舶参数只读实测（Grokbot）

时间：2026-11-28 11:54（北京时间，Asia/Shanghai）
派遣：#106 comment 7232952386
接单：#106 comment 7233415961

## 检索

固定版本 `9ff7a0488e30fad050d21bafc2bdc7d55d0043da`（`candidate/vessel-dimension-status`，相对 main 底版 `94d5e38`）下，没有可复用的真浏览器原件覆盖「真实登记预置两个合成案 → 官方 `#/ships` 页经大厅正常切 A→B→A → 对照实际 GET 与页面」。候选自带的 `web/tests/vessel-dimensions.cjs` 是 React SSR，其 README 写明本轮未运行 `#/ships`、真浏览器未验。已通过的 W9 气象页（`e32816b` / `3d0e46e`）是不同提交与不同页面，未重跑。`candidate/w91-vessel-static-readback-20261125` 不含本固定 SHA，不能当本版本原件。

## 独立验收候选

- 分支：`candidate/w9-ships-read-browser`
- 完整 SHA：`5c0e83efcbb0cde619c1aa20be88d2d4ff19f4f0`
- 只新增 `tests_acceptance/w9-ships-read/` 三份验收文件；产品树未改，未改契约、权限、CI、主线、3D 或数据接入，未安装、未合并、未部署。

## 预置（单列，非浏览器阶段）

用真实官方 API 在临时 SQLite（`seed_demo=False`）写入两个纯合成虚构案：

1. `POST /api/v1/cases` → `SYN-W9-SHIP-A`（201）
2. `POST /api/v1/cases` → `SYN-W9-SHIP-B`（201）
3. `POST /api/v1/cases/SYN-W9-SHIP-A/vessels` → 有总长 96、无型宽、明确登记首吃水 0 m，来源声明 Direct「合成 Direct 来源甲」（201）
4. `POST /api/v1/cases/SYN-W9-SHIP-B/vessels` → 总长 72、型宽 12、不登记首吃水，来源声明 Estimated「合成估计来源乙」（201）

预置写入 4 次。预置后只读 GET 与写入体一致；A 的响应不含 `beamM`，B 的响应不含 `draftForeM`。

## 正式跑

`timeout 150` 官方脚本退出码 **0**（2026-11-28 11:54 北京时间）。Google Chrome 156.0.8078.47，正常沙箱，没有 `--no-sandbox`。服务与页面均在 127.0.0.1（本跑 API `51617`，页面 `52135`）。身份为页面官方角色选择器中的 Investigator。

经真实案件大厅「进入案件」再点侧栏「船舶参数」，在官方 `#/ships` 页做 A→B→A。1440 与 390 各跑同一条只读链。

- 每次切换都发出对应案的真实 GET `/api/v1/cases/{id}/vessels` HTTP 200，正文与预置登记一致。
- 案 A：总长 `96 · 已登记值`，来源声明【直接】且「尚未核验」；型宽「未登记 · 不填默认值」，不据来源标签推定；首吃水 `0 · 已登记值`（合法零，未改成未知或未登记）。
- 案 B：总长 72、型宽 12 为已登记值，来源声明【估计】且「尚未核验」；首吃水「未登记 · 不填默认值」，没有把 A 的 0 带过来。
- 切回 A 后页面与 GET 回到 A 的原样，与第一次进入 A 的截图像素相同。
- 浏览器只读阶段页面请求与宿主日志的写入计数均为 0；同一 SQLite 摘要在预置后与浏览器阶段后均为 `352a9bb23c329c5a9bf235baf56917358b5b64b03f1a11d261fadae9c3cdb721`。证据包不含数据库。

## 未验 / 边界

此项不等于 W9 整包，不替代三维物理尺度或内网船档。未签发、未外发、未接真案或 4A。未验 Firefox/WebKit、headed。未重跑气象页。截图 01-desktop-A 与 A-return、02-390-A 与 A-return 分别像素相同，属同一只读回访。
