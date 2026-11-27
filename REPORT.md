# W12 已登记声明缺口 JSON 接线（独立候选）

- 底版：`c150548c16516f5ad7319e3a00213e5fbe448497`（不重跑 e2bc59d 可见性）
- 独立候选 `candidate/w12-registered-json-gap`：`e80a49aba61336f8db7b1337b6a555de5c735857`
- 复用历史隔离白名单 `db90fdf` 的 `_load_registered_pair` 与 `afc72a1` 登记/固定 pin 工装（物化到临时树，不改正式契约/存储/写路由）
- 原件锁定 2048c60 expanded A/B，字节未改：vessel-a `a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c`，vessel-b `07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca`
- 服务端持有两个固定 pin，公开快照不含 pin；视图只读，hover 不再读原件
- 官方：2026-11-27 16:15:17–16:15:22 CST（Asia/Shanghai），`timeout 150s`，127.0.0.1:18782，正常沙箱 Chrome，退出 0
- 既有回归：31 项、96 项通过
- 无首个断点。不是 W12 整包

## 已验

声明开区间保持原样 JSON：`(60,100)`、`(121,127.5)`。未猜缺口，未用演示 CPA，未走夹紧端点的采样。

既有 mcis-core（DLL SHA-256 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`，`mcis-core/0.1.0`）仅对账 T+120 / T+130，两次一致，与 d49a691 正对照相同：
- T+120（20:02:00）：currentDistanceNm=1.070062，dcpaNm=0.000226，tcpaMin=2.918352，Danger
- T+130（20:02:10）：currentDistanceNm=1.008757，dcpaNm=0.000213，tcpaMin=2.751155，Danger

样位分类：T+120 / T+130 为双船同刻；T+124.25 的 A 为 declared_gap，无 A 样位、无双船指标；T+121 与 T+127.5 为 A 原始端点（input_point），B 为 no_observation_at_time，非双船同刻。指标表只有两行，不含 T+121 / 124.25 / 127.5。

官方沙箱 Chrome：三条曲线 `showSymbol=true`、`connectNulls=false`；T+120 与 T+130 之间有裸 null 断线；有效数值与原件来源（两份证据身份 + 官方核心）可读；登记视图无「已自检 / 装配占位 / 种子生成」。hover 后 Access 仍为 2。一次成功装配双 Access（0→2）；拒绝 `policy-deny:403` 与无配对 `TWO_PINS_REQUIRED` 均无指标、无画布，Access 保持 2。390px 来源摘要 `scrollWidth=390`，无整页横滚。

## 未验

正式分析入口接到已登记 JSON；登录或跨进程撤权保证；同案换版；W21；真实案；4A；W12 整包。未把 JSON 改塞进 W10.2 CSV，也未改正式服务路由。
