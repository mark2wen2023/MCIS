# W12 首次登记接线（隔离宿主）

从 `34d6acf` 开独立候选。复用 8266aba 已验证的同一只读事务捕获（`WRITE_LOCK` + `BEGIN IMMEDIATE`、两份回执与 previewDigest/sourceSha256/reportSha256），在隔离宿主把读服务结果接到 `34d6acf` 的 `AnalysisView`。不改正式存储、写入或契约，不绕过 W10.2。正式 `GET /analysis` 仍读离线种子，本轮不把它接到已登记输入。

图区按 `metricProvenance` 区分真实核心与装配占位；占位不得自称核心。公共 `EChart` 不再默认挂出 `data-testid` / `__echartsOption` / `__echartsInstance`；隔离装配用 `echarts.getInstanceByDom`。

双船同刻有出处时调用既有官方 mcis-core（DLL SHA 锁定）。缺输入或无同刻样本不显示指标，不用离线种子补。登记 CSV 没有授权的显式缺口元数据，缺口适配保持未接并写清来源缺失，不从步长猜测。

不是同案换版、W21、真实案或 W12 整包。
