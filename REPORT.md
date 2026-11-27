# W12 请求时读取（独立隔离候选）

- 底版：`7345c1eb5ee6fb76558d88ff6d75172145b53ea2`
- 独立候选 `candidate/w12-request-time-read`：`f7b1f11e719f4ebba0a3a1f6146fadbe3ba8d346`
- 只把只读快照装配移到同一个本机 HTTP 请求内。沿用已验合成 JSON、服务端固定 pin 与冻结 `_load_registered_pair`。未改正式路由、契约、存储或核心。
- 测试服务端角色上下文是合成接头，不是真实身份认证。一个响应只下发当前角色的那一份结果，不夹带全套成功/拒绝夹具。
- 官方：2026-11-27 17:33:15–17:33:19 CST（Asia/Shanghai），`timeout 150s`，127.0.0.1:18783，正常沙箱 Chrome，退出 0
- 无首个断点。不是 W12 整包。不重跑前序回合整套。

## 已验

两个独立合成浏览器会话：

- 未授权（synthetic-denied-reader）：GET /assembly/api/view 返回 403，`policy-deny:403`，`view=null`，无指标、无证据身份、无画布。Access 0→0。
- 授权（synthetic-authorized-reader）：同一路径在该次请求内装配只读快照并调用 `_load_registered_pair`，只返回这一份视图。Access 0→2（Δ=2）。图中 T+120 / T+130 两个有效点可读（1.070062 / 0.000226 / 2.918352 与 1.008757 / 0.000213 / 2.751155），声明缺口间断线。悬停后 Access 仍为 2。

## 未验

真实登录；撤权竞态；换版；W21；3D；真案；4A；正式分析入口；W12 整包。前序回合整套（含 390px、未配对夹具开关）未重跑。
