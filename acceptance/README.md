# W12 已登记声明缺口 JSON 接线（隔离装配）

从 c150548 只新增本目录，并把分析组件的登记身份展示扩展为可显示 `evidenceId` / `requestDigest`。不改正式契约、存储或写路由，不把 JSON 改塞进 W10.2 CSV，不合并、不部署。

当前主线（c150548）没有 `trajectory_exchange`，且 `evidence_intake.router` 已去掉 `_read_original_for_access`。本装配复用历史隔离生产白名单 `db90fdf` 的 `_load_registered_pair` 与 `afc72a1` 的 preview/commit 固定 pin 工装：按 SHA 锁清单物化到临时树，不写入正式服务路径。

原件只用 `2048c60` expanded A/B，字节与 SHA 先锁：
- vessel-a.json `a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c`
- vessel-b.json `07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca`

两个固定 pin 由服务端在登记回执中持有，浏览器 API 不接受 pin。成功装配只做一次 `_load_registered_pair`（双 Access），视图快照只读，hover 不再读原件。声明开区间取自原件 `sampling.missingIntervals`：`(60,100)`、`(121,127.5)`，不从步长猜测。仅 T+120 / T+130 调用现有官方 mcis-core（对照 d49a691）。审计不扩大到登录或跨进程撤权保证。
