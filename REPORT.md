# W9 正式环境页只读检索（真浏览器通过）

- 检索：未发现覆盖「现有正式产品壳：同案环境记录只读、切案后不串来源/UTC/数值或未知」的等价真 Chrome 回执。`3d0e46e` / 产品底版 `26dd466` 是隔离页保存超时恢复，未重跑、未充数。`aca3e1e` 是 Happy DOM 只读接合，报告写明不是真浏览器，也不在 main 上，本单不把它当作真浏览器证据。
- 底版：`94d5e38c926fda232bb987b60fa9145e4bcf01a7`
- 候选 `candidate/w9-env-page-read-browser`：`e32816b3d704bc87a9f9f025adcb2d4d90373be2`
- 只新增 `tests_acceptance/w9-env-page-read/` 三份验收文件，未改产品、权限、CI、契约或主线，未另造页面。
- 现有正式环境页 `#/env` 已接 `GET /api/v1/cases/{caseId}` 与 `GET /api/v1/cases/{caseId}/environment-observations`，可显示来源、UTC、数值或未知；因此用正常沙箱 Chrome 验收，未停在断点。
- 官方脚本 `timeout 150 … run.py` 退出码 **0**。时间 2026-11-28 03:21:43–03:21:52（Asia/Shanghai）。Google Chrome 156.0.8078.47，`chromiumSandbox: true`，没有 `--no-sandbox`。服务与 Vite 只听 127.0.0.1:18796 / 18797，临时 SQLite，`seed_demo=False`。
- 浏览前用标准服务预置两件虚构合成案件与各一条观察；浏览器验证期间只读，`verificationWrites=[]`。壳层对案件列表和案件元数据发过只读 GET，未当作写入。
- 合法零值案 `SYN-W9-ENV-ZERO-A`：实际请求返回 `windSpeedMps=0`、UTC `2026-03-11T08:17:40Z`、来源 `SYN-W9-ENV-SRC-ZERO`；页面同步显示 `0 m/s` 及该来源与时刻，未混入另一案。
- 未知案 `SYN-W9-ENV-UNK-B`：对应字段按合同留空，实际请求不含 `windSpeedMps`；切案后页面风速为「未知」，UTC `2026-04-22T19:03:11Z`、来源 `SYN-W9-ENV-SRC-UNK`，不残留零值或上一案来源/时刻。
- 桌面 1440 与 390 各只跑同一条读链，两段均通过、均零写入。
- 此项不等于 W9 整包，也不等于 W20 或 W12。未验 Firefox/WebKit、headed、真案、外部模型或生产身份。未验保存/新增写入路径。
