# 粤海探析：共享时点 → 原始记录（离线只读候选）

这是第一条可检查的小闭环，不是三维播放器或真实事故重建。画面与证据侧栏共用 `caseId + alignedUtc` 查询结果，点击位置或记录能查看原始 JSON、校时依据、文件摘要和 JSON Pointer。没有业务写入、HTTP、外部地图或云调用。

## 基线与为何未接三维

- 新分支从 `2048c60fd6650c6f2c99a76a16be463a3895655d` 建立，沿用该提交独立 A/B 单船 V1 文件、校验器和 schema；没有更改契约或固定夹具字节，没有另造双船 V1 封装。`inputs.json` 固定 A/B 与本次手造设备文件摘要。
- 只读检查的 main 为 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。`web/src/routes.ts:18` 的 sim 未标 live；`web/src/tracks/TrackView.tsx` 的 Plot/PointDetail 是数据库航迹散点及相对时间，不接受这两份 V1 原始时基。
- `unity/Assets/_Project/Scripts/Presentation/ReplaySync/ReplayCommandAdapter.cs` 的 Apply 只执行已授权的 seek/play 等命令；调用者仍负责案范围、字段映射和主线程调度。这里不假造授权或 Unity 场景连接，也不挂图音 pilot。
- 因此交付固定输入的共享时点查询 + 网络禁用的二维散点证据原型。实际 mcis-3d / Unity UI 连点、持续播放与真实回放未做。

## 本机入口

需已有 Python 3（使用仓内校验器所需的现有 `jsonschema`）和 Node；不安装依赖。缺库会非零退出，不能算通过。检出本候选后从仓库根运行：

```sh
python tests_acceptance/shared-trajectory-cross-repo-expanded/check.py
python tests_acceptance/replay-evidence-clock/check.py
python tools/replay_evidence_clock/query.py --at 100
python tools/replay_evidence_clock/preview.py --output /tmp/mcis-replay-clock-preview.html
node tests_acceptance/replay-evidence-clock/panel.cjs /tmp/mcis-replay-clock-preview.html
```

输出 HTML 必须是不存在的新文件；不覆盖旧文件。可在本机浏览器直接打开生成文件，无需服务。初始 T+100 秒；选择时点或上一/下一时点，然后点击船点/“查看原始点”/设备记录。每次换时点清除旧定位。CSP 禁止网络，页面无 fetch、外部资产或地图。这里仅生成并执行了手写 DOM 替身，没有实际浏览器、截图或像素验收。

`query.py` 命令只读取列明固定合成文件。其内部 `query()` 供已通过固定加载器校验的输入使用，不是面向不可信业务载荷的 API、认证器或生产导出器。设备资料是独立内部合成样例，未改共享 V1 schema。设备定位只是同案/同船声明关联到该时点已有航迹，`position:null` 不伪装成设备测位。

## 必查时点与含义

| 时点（共同起点 2026-02-01T12:00:00Z 后秒） | 预期 |
|---|---|
| 20 | 两船精确命中已存行，**各自 position.kind=interpolated**，不是实测或本次插值；B 原 12:00:08Z +12 → 12:00:20Z。源锚 10/30 秒仍见固定夹具记录/校验。 |
| 60 / 100 / 121 / 127.5 | A 四个端点有输入观测，HDG 未知、COG=90，不代替艏向。 |
| 60.001 / 80 / 99.999 | A 在 (60,100) 缺轨内，不返回位置；80 秒 B 仍能显示有效点。 |
| 121.001 / 124.25 / 127.499 | A 在 (121,127.5) 缺轨内，不跨点补位置；6.5 秒缺口不是“完全落入单个 5 秒间隔”。 |
| 100 | 设备01原 12:01:33Z +7 → 12:01:40Z，与 A-t100 对齐；设备原文和修正依据可查看。 |
| 任意 | 设备02日期/时区未知，不入同步事件，独立显示原始屏显与未知依据，不影响有效双船。 |

这版**所有非精确观测时点均不插值**，不仅缺轨内。B 连续覆盖的契约诊断不意味着这版生成连续位置；没有观测时明确为空，不沿用前一时点。不用 COG 补 HDG，不画确定船体方向，`collisionAngle:null` / `collisionInferred:false`。校时值完全手造，不代表真实设备时间已验证。

## 实跑与限制

本轮上述五条命令均退出 0：固定参考校验及几何粗验；8 项纯查询/产物单测；T+100 JSON；新 HTML 生成；实际面板 JS 的内存 DOM 核对（选点、设备、缺口、切时点清旧数据、t20 品质）。非有限/越窗、混案、错设备校时均拒绝。输入未修改。

没有运行服务、Unity、浏览器、ORM、模型、媒体、4A 或容器，没有读真实案例/seed/凭据；不是权限、原件真实性、持续三维回放、碰撞判定或端到端验收。下一步是独立复核这个精确时点与证据定位合同，再由实际三维消费者按同一时点读取；仍须保留缺口和未知标记，不能直接插值越过本候选的空位置。
