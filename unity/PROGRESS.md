# P1 进度（每完成一个模块更新）

| 模块 | 状态 | 模型 | 测试 | 备注 |
|---|---|---|---|---|
| 脚手架：asmdef、Core/Primitives、Domain/Common、Domain/Models | 完成 | Gemini 4 Argon（agy） | 编译通过 | |
| DotnetTests 工程（Mcis.Pure + xUnit） | 完成 | 手工搭建 | restore 成功 | |
| M1 Ais 解码 + CSV | 完成 | Gemini 4 Argon（agy） | 9/9 | NMEA 1/2/3/5/18/19/24A/B + 多句重组 + CSV 映射 |
| M2 Tracks | 完成 | Gemini 4 Argon（agy） | 11/11 | TrackCleaner + Hermite/CatmullRom/Linear 插值 + 缺口检测 + 双船时间对齐 |
| M3 Geo | 完成 | Gemini 4 Argon（agy） | 16/16 | GeoMath + LocalEnuGeoConverter |
| M4 SimClock | 完成 | Gemini 4 Argon（agy） | 13/13 | 整数微秒 tick 确定性时钟 + ISimClock |
| M5 CpaCalculator + CpaService | 完成 | Gemini 4 Argon（agy） | 11/11 | 向量法 + 论文3.4矢量三角形 + 全时段预计算与正向滞回 |
| M6 Unity：Ships/Cesium | 完成（Unity 部分未编译验证） | Gemini 3.8 Flash（agy） | 63/63 | ShipController + IShipController + ShipStateSourceAdapter + SimulationLoopRunner + ShipView + CesiumGeoreferenceAdapter (Unity 6 / MCIS_CESIUM) |
| M7 Unity：UI Toolkit | 完成（未编译验证） | Gemini 4 Argon（agy） | 未编译验证 | ThemeVariables.uss + NavHud + TimelineBar + MiniMapElement(Painter2D) + SimHudController（Unity 6 [UxmlElement]） |
| M8 Demo + 示例数据 + INTEGRATION.md | 完成（Bootstrap 未编译验证） | Gemini 3.8 Flash（agy） | 63/63 | M8a 数据与测试 + M8b Demo 引导与 INTEGRATION.md 完成 |
| 约束更新 16:24 | Unity 6.0 唯一目标（见 P1_TASK_B.md 末尾） | | | M6/M7/M8 完成后统一修正 |

# P2–P5 纯逻辑进度（2026-11-11 17:18 Asia/Shanghai，追加，不改上行）

| 模块 | 状态 | 模型 | 测试 | 备注 |
|---|---|---|---|---|
| N1 案件包 .mcase / SHA-256 / AuditLog / CommandHistory | 完成 | 执行器直接实现 | 4/4 | manifest.json、raw/derived/evidence/audit 约定、VerifyIntegrityAsync、IsFictionalDemo |
| N2 手绘航迹 | 完成 | 执行器直接实现 | 3/3 | 关键点 + Hermite/Catmull-Rom，按航速分配时间，Provenance=ManualDrawn |
| N3 ECFC | 完成 | 执行器直接实现 | 4/4 | 论文 2.5 节表 4 校验、自动布局、按 SimTime 查询可见卡片 |
| N4 碰撞/进水/烘焙 | 完成 | 执行器直接实现 | 5/5 | OBB 净距、二分搜索 tc（0.05 s）、等效动能与破口、Q=Cd·A·√(2gh)、10 Hz DamageTrack |
| N5 分析 | 完成 | 执行器直接实现 | 2/2 | 全时段距离/DCPA/TCPA、首次警告/危险、最近距离、tc、剔除点统计 |
| N6 PDF 报告 | 完成 | 执行器直接实现 + PDFsharp/MigraDoc 6.2.1 | 已生成样例 | 中文报告 + 矢量航迹/CPA/ECFC + SHA-256 清单 + 每页水印；字体 Noto Sans SC（OFL，TTF） |
| N7 视频导出管线 | 完成（Unity 采帧未编译验证） | 执行器直接实现 | 2/2 | FFmpeg RGBA→H.264 MP4，水印/进度/取消；合成帧实测通过 |
| 环境时间线插值 + Enviro3/DWP2 适配器脚本 | 完成（适配器未编译验证） | 执行器直接实现 | 2/2 | EnvironmentBridge 纯接口与插值；适配器脚本在 Integrations/Enviro、Integrations/Dwp2 |
| 全量 DotnetTests2 | 完成 | — | 82/82 | 含原 P1 的 60 个 + 本批 22 个 |

样例：
- PDF：`/workspace/maritime-sim-design/samples/Demo_LilyMary_调查报告.pdf`（6 页），首页预览 `samples/pdf-preview/page-1.png`
- MP4：`/workspace/maritime-sim-design/samples/Demo_LilyMary_合成帧.mp4`（H.264 640×360 / 15 fps / 45 帧 / 3.00 s）
- 测试工程：`unity/DotnetTests2`（避免与仍在运行的 M6 抢同一 DotnetTests）
- 未使用 agy/Gemini 完成本批，以免与并行 M6（gemini-4-argon-medium）争额度。

# P2–P5 报告图与演示航迹修订（2026-11-11 17:30 Asia/Shanghai，追加，不改上行）

| 模块 | 状态 | 模型 | 测试 | 备注 |
|---|---|---|---|---|
| 样例 PDF 曲线/附图修订 | 完成 | 执行器直接实现 | 82/82 | 第 4 页改为距离/DCPA/TCPA 三幅共用时间轴子图（网格、刻度、北京时间、警告/危险阈值带、首次警告/危险/tc 竖线；tc 后不绘 DCPA/TCPA；TCPA 限幅 15 min）。航迹图补比例尺、北箭头、图例与时间标签；ECFC 图补图例、北京时间并避免裁切。 |
| Lily/Mary 虚构航迹重设 | 完成 | 执行器直接实现 | 含于 82/82 | 按论文 5.4 情节：t=0 安全（DCPA≈1.09 nm），t=209 s（18:03:29）首次警告，t=296 s（18:04:56）首次危险，t=600 s（18:10:00）OBB 首次接触 tc。数据在 `Scripts/Fixtures/LilyMaryDemo.cs`，**请 M8 示例场景直接采用此工厂，勿另写一套冲突航迹**。 |

样例（已逐页目视）：
- PDF：`/workspace/maritime-sim-design/samples/Demo_LilyMary_调查报告.pdf`（5 页）
- 预览：`samples/pdf-preview/page-1.png` … `page-5.png`（封面含全部关键时刻；第 3 页航迹图；第 4 页 CPA 子图；第 5 页 ECFC）

| P1 收尾 18:1x | Unity 侧近似编译检查（UnityEngine.Modules 2021.3 + Unity 6 API 桩）：仅剩 MeshGenerationContext.painter2D（Unity 6 专有）；DotnetTests 63/63、DotnetTests2 82/82；打包 maritime-p1-unity.zip | 执行器 | 通过 | Cesium #if 分支与 UXML/USS 未验证 |
