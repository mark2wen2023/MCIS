# W12 请求时读取 — 证据策略拒绝（独立隔离候选）

- 底版：`f7b1f11e719f4ebba0a3a1f6146fadbe3ba8d346`
- 独立候选 `candidate/w12-request-time-policy-deny`：`688a7bb0eb16b29bb295d13376ab56f4cc7fd10b`
- 只补一条正常权限流程：允许与拒绝两条固定测试上下文，在同一个隔离 GET 内都实际调用冻结 `_load_registered_pair`。拒绝上下文复用 e80a49a 合成拒绝策略种子（Investigator evidence_meta=Deny），独立临时 SQLite。仅把预期的证据策略拒绝（HTTPException 403 / FORBIDDEN）映射为 403，不用测试角色提前代答，不把其他错误吞成 403。
- 未改正式认证、路由、存储、契约、生产权限或核心。
- 官方：2026-11-27 18:51:33–18:51:38 CST（Asia/Shanghai），`timeout 150s`，127.0.0.1:18784，正常沙箱 Chrome，退出 0
- 无首个断点。此前正向读取证据仍有效。本次不算 W12 整包。

## 已验

先授权、再全新浏览器会话访问独立合成拒绝上下文。

- 授权：GET `/assembly/api/view` 在请求内调用 `_load_registered_pair`，outcome=allowed。Access 0→2（Δ=2）。悬停仍为 2。简短正控：T+120 / T+130 两点可读且断线。
- 拒绝：同一入口被实际调用，服务端策略结果为 HTTPException 403、`code=FORBIDDEN`、`角色 Investigator 无权访问 evidence_meta`（e80a49a 种子）。响应 403，无身份、无指标、无快照。Access 0→0（Δ=0）。

## 未验

真实登录；撤权竞态；换版；W21；3D；真案；4A；正式分析入口；W12 整包。数学与缺口整套未重跑。
