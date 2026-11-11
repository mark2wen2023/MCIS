# MCIS (Maritime Collision Investigation Simulator) Unity 集成与引导文档

本文档为 Unity 工程师与系统集成人员提供 MCIS P1 原型系统在 Unity 项目中的部署、场景搭建、外部数据接入及第三方资产共存指南。

---

## 1. 目标运行环境与依赖包

### 1.1 核心环境
* **Unity 版本**：`Unity 6.0 LTS`（`6000.0.x` 系列，首选 `6000.0.23f1` 或更新补丁版本）。
* **渲染管线**：`Universal Render Pipeline (URP) 17.x`（线性色彩空间 Linear Color Space）。
* **C# 语言标准**：C# 9.0 兼容规范（无 file-scoped namespace，无 record，无 required/init）。

### 1.2 Package Manager 依赖包清单
| 包名称 | 推荐版本 | 用途说明 | 必要性 |
|---|---|---|---|
| `UI Toolkit` | 内置（com.unity.ui） | 新一代声明式 UI、矢量绘制（Painter2D 小地图） | **必需** |
| `Unity.Mathematics` | `1.3.2` 或更高 | 高性能双精度向量与数学计算（`double3`） | **必需** |
| `Cesium for Unity` | `1.13.0` 或更高 | WGS84 实景地球与 3D Tiles 海洋地理投影 | **可选**（不装自动回退 ENU） |
| `Universal RP` | `17.0.x` | 场景光影渲染、后处理与水面着色 | **推荐** |

> [!NOTE]
> **Cesium 宏定义机制**：`Mcis.Integrations.Cesium.asmdef` 配置了 `versionDefines`。当工程中通过 Package Manager 安装了 `com.cesium.unity` 时，Unity 会自动激活 `MCIS_CESIUM` 条件编译宏；若未安装，该程序集代码自动跳过 Cesium 原生 API，整体工程依然能够顺利编译并运行本地平面 ENU 模式。

---

## 2. 工程目录结构与程序集拷贝步骤

### 2.1 P1 核心程序集列表
将 `Assets/_Project/Scripts/` 下的 P1 模块拷贝至目标工程对应目录：
* `Core/` (`Mcis.Core.asmdef`)：纯 C# 基础类型（`SimTime`, `Result<T>`）。
* `Domain/` (`Mcis.Domain.asmdef`)：无引擎依赖核心（`GeoMath`, `AisDecoder`, `TrackCleaner`, `TrackInterpolator`）。
* `Simulation/` (`Mcis.Simulation.asmdef`)：确定性仿真时钟（`SimClock`）、`CpaService`、`ShipController`。
* `Presentation/` (`Mcis.Presentation.asmdef`)：表现层视图组件（`ShipView`, `SimulationLoopRunner`, `McisP1DemoBootstrap`）。
* `UI/` (`Mcis.UI.asmdef`)：UI Toolkit 控制器与矢量小地图（`SimHudController`, `NavHud`, `TimelineBar`, `MiniMapElement`）。
* `Integrations/Cesium/` (`Mcis.Integrations.Cesium.asmdef`)：Cesium 地理参考适配器。
* `Assets/StreamingAssets/Mcis/`：包含虚构演示航迹 `lily_mary_demo.csv` 与 `lily_mary_demo.nmea`。

### 2.2 并行开发模块（P2–P5）与依赖说明
仓库 `unity/Assets/_Project/Scripts/` 下包含并行研发的高级模块目录：`Data/`、`Export/`、`Damage/`、`Ecfc/`、`Environment/`、`Analysis/`。
* **注意 `Mcis.Presentation.asmdef` 的引用关系**：
  当前 `Mcis.Presentation.asmdef` 的 `references` 列表中包含了 `"Mcis.Export"`（用于离线高清视频帧抓取组件）。
  * **方案 A（整包拷贝，推荐）**：一并拷贝 `Scripts/Export/` 目录至目标工程，可直接使用完整的视频录制和离线导出管线。
  * **方案 B（仅试用 P1 基础引导）**：若目标工程仅需要 P1 基础仿真功能，可打开 `Mcis.Presentation.asmdef`，从 `references` 中删除 `"Mcis.Export"`，并在 `Presentation/Export/` 排除 `OfflineFrameCapture.cs`。

---

## 3. 接入 Mark 已有 AIS 数据管线

MCIS 提供了三层灵活的数据接入方式，可与任何既有 AIS 采集/回放系统无缝拼接：

### 3.1 方式 A：NMEA 0183 原始报文接入
若已有数据源为从串口、TCP/UDP 流或文件捕获的 `!AIVDM`/`!AIVDO` 报文：
```csharp
using Mcis.Domain.Ais;

AisDecoder decoder = new AisDecoder();
// 支持多句拼接、校验和自动核验、时间纪元补偿
Result<AisImportBatchResult> result = decoder.DecodeNmeaText(rawNmeaContent);
if (result.IsSuccess)
{
    AisImportBatchResult batch = result.Value;
    // batch.RecordsByMmsi 包含按 MMSI 分组的位置报告（类型 1/2/3/18/19）
    // batch.DiscoveredStaticParticulars 包含静态航次报告（类型 5/24）
}
```

### 3.2 方式 B：自定义 CSV 文件导入（列映射配置）
若 Mark 的系统导出了包含非标准表头的 CSV 航迹，可通过 `CsvMappingProfile` 进行列名别名映射，无需修改代码：
```csharp
using Mcis.Domain.Ais;

// 参数依次为：配置名、MMSI列、时间列、时间格式(可空自动识别)、时区偏移分钟、经度列、纬度列、航速列、航向列、船首向列、船名列
CsvMappingProfile customProfile = new CsvMappingProfile(
    "MarkCustomAis",
    mmsiColumn: "MMSI",
    timestampColumn: "RecordTime",
    timestampFormat: "yyyy-MM-dd HH:mm:ss",
    sourceTimeZoneOffsetMinutes: 480, // UTC+8
    lonColumn: "Longitude",
    latColumn: "Latitude",
    sogColumn: "SpeedKnots",
    cogColumn: "CourseOverGround",
    hdgColumn: "TrueHeading",
    vesselNameColumn: "ShipName"
);

Result<AisImportBatchResult> res = new AisDecoder().DecodeCsvText(csvText, customProfile);
```

### 3.3 方式 C：内存直接注入（接 Mark 运行时管线）
若 Mark 的 Unity 工程内已经有实时的网络 AIS 流或现成的点位结构体：
1. 直接转换为领域层 `AisDecodedRecord` 或 `TrackSample`。
2. 使用 `TrackInterpolator.BuildFromAisRecords` 进行数据清洗与 Hermite 平滑插值，得到 `IShipTrack`。
3. 将得到的 `IShipTrack` 赋给 `ShipController` 或调用 `SimHudController.Bind(clock, cpaService, lilyTrack, maryTrack)`。

---

## 4. 接入 Cesium for Unity 实景数字孪生场景

### 4.1 CesiumGeoreference 原点配置
* 在 Unity 场景中创建或选中 `CesiumGeoreference` 游戏对象。
* 将其大地原点（Origin）设置为事发海域中心位置，例如珠江口/虚构海岛会遇水域：
  * `Latitude`: `21.78`°
  * `Longitude`: `113.70`°
  * `Height`: `0.0` 米
* 在该物体上（或独立管理对象上）添加 `CesiumGeoreferenceAdapter` 组件。当 `McisP1DemoBootstrap` 的 `Use Cesium Adapter` 开启时，适配器会自动同步经纬度原点，并借助 Cesium 的双精度坐标投影将大地经纬度转为 Unity 世界空间三维坐标。

### 4.2 船模挂载方案取舍：CesiumGlobeAnchor vs 本地适配器
在 Cesium 场景中放置三维船模有两种常见方案：
1. **方案 1：挂载 `CesiumGlobeAnchor`（纯 Cesium 原生驱动）**
   * *原理*：每个船体模型挂载 `CesiumGlobeAnchor`，直接设置其 `longitudeLatitudeHeight`。
   * *优缺点*：适合静态建筑物或大范围航天器，但会与确定性物理时钟重放与插值算法产生多重更新冲突，拖慢高频刷新性能。
2. **方案 2：适配器统一换算并作为 Georeference 的子物体（MCIS 推荐）**
   * *原理*：三维船体模型作为场景常规物体或 `CesiumGeoreference` 的子节点；由 `Mcis.Domain.Geo` 双精度矩阵或 `CesiumGeoreferenceAdapter` 完成坐标投影，`ShipView` 统一负责单帧 Transform 的 Smooth 插值。
   * *优缺点*：完全保持确定性重放、平滑无抖动、支持离线脱机运行且不依赖 Cesium 内部更新顺序。

### 4.3 浮点精度与大范围漫游对策
Unity 内部 Transform 使用 32 位单精度浮点数（`float`）。当模型距离场景原点超过 10 公里时，精度损耗可能导致模型微小抖动：
* MCIS 的 `McisP1DemoBootstrap` 将场景 ENU 原点默认锚定在双船会遇点几何中心（21.78°N, 113.70°E）。
* 在以原点为中心的 20 海里（约 37 公里）范围内，单精度浮点定位误差小于 1 毫米，完全满足海事调查事故重构对于厘米级的高精度显示需求。

---

## 5. 快速上手：场景搭建分步指南

按照以下步骤，5 分钟内即可在全新或既有工程中启动完整的海事推演仿真：

### 步骤 1：创建或打开场景
* 打开一个空场景，或直接打开已有包含海面水体与天空的 URP / Cesium 场景。

### 步骤 2：创建 UI Document
1. 在 Hierarchy 中右键：`UI Toolkit -> UI Document`，命名为 `MCIS_HUD`。
2. 选中该物体，在 Inspector 中配置：
   * **Panel Settings**：新建或指定一个 `PanelSettings` 资产（建议将 Scale Mode 设为 `Scale With Screen Size`，Reference Resolution 设为 `1920 × 1080`）。
   * **Source Asset**：指定为 `Assets/_Project/Scripts/UI/SimHud/SimHudView.uxml`。
3. 在同一物体上点击 `Add Component`，添加 `SimHudController` 组件（位于 `MCIS/UI` 命名空间）。

### 步骤 3：创建引导调度器（Bootstrap）
1. 在 Hierarchy 中右键新建空物体，命名为 `MCIS_Bootstrap`。
2. 点击 `Add Component`，挂载 `McisP1DemoBootstrap`（位于 `MCIS/Presentation/Demo Bootstrap`）。
3. 检查并配置 Inspector 参数：
   * **Data Source Relative Path**：保持默认 `Mcis/Demo/lily_mary_demo.csv`。
   * **Origin Lon/Lat/Alt**：保持默认 `113.70 / 21.78 / 0.0`。
   * **Use Cesium Adapter**：若在 Cesium 场景中则勾选，并将场景中的 `CesiumGeoreferenceAdapter` 拖入引用框；若为纯平面场景则保持未勾选（自动使用纯 C# ENU 投影）。
   * **Lily / Mary Prefab**：分别指定散货船与集装箱船的 3D 模型预制体（若暂时留空，系统将自动创建带朝向与标识的基础方块模型）。
   * **Hud Controller**：将刚才创建的 `MCIS_HUD` 拖入字段（留空时亦会自动通过 `FindFirstObjectByType` 寻找）。
   * **Initial Playback Rate**：设为 `1.0`（可支持 0.5x, 1x, 2x, 4x, 8x, 16x）。
   * **Auto Play**：勾选 `true`。

### 步骤 4：运行推演
* 点击 Unity 编辑器的 **Play** 按钮。
* 控制台将输出 `[MCIS] 示例数据（虚构），改编自论文 5.4 节。Lily(散货船)与 Mary(集装箱船)窄航道会遇至碰撞演示引导就绪。`
* 界面上将自动呈现：
  * 左上角/右上角：两船实时动态遥测（经纬度度分秒、SOG、COG、HDG）与 CPA 会遇距离/时间及三级风险警报变色。
  * 底部时间轴：确定性进度滑块、关键事件点标记、播放/暂停与倍速切换按钮。
  * 屏幕侧边：Painter2D 绘制的实时矢量海图小地图、两船全航迹线、船首向三角标与动态 CPA 连线。

---

## 6. 与 Enviro 3 / Dynamic Water Physics 2 (DWP2) 共存说明

在具备动态天气、水体波浪与浮力物理的高拟真工程中，MCIS 与以下主流中间件可无冲突共存：

### 6.1 Enviro 3（天气与日夜循环系统）
* **定位**：Enviro 3 负责全域体积云、大气散射、降水粒子与能见度/雾效。
* **P1 集成要点**：
  * P1 阶段不直接控制天气系统，完全由场景主控或 Mark 既有系统接管。
  * `ShipView` 提供了 `_waterHeightOffsetM` 字段，用于针对 Enviro 水面绝对标高微调船模吃水深浅，避免船体悬空或过度下沉。
  * （注：P2 模块已在 `Integrations/Enviro/` 中提供 `Enviro3Adapter`，支持根据历史风浪报告自动驱动天气预设）。

### 6.2 Dynamic Water Physics 2 (DWP2)（水动力学与浮力模拟）
* **定位**：DWP2 负责船体多网格切片浮力计算、波浪冲击响应与水阻动力学推演。
* **运动学 vs 动力学共存策略**：
  * **P1 运动学重放模式（默认）**：船舶水平位置（X, Z）与真航向（Yaw）由 `ShipView` 严格根据 AIS 插值轨迹驱动；
  * **波浪姿态叠加**：在启用 DWP2 物理时，可保留 DWP2 的垂直浮力驱动（Y轴升沉 Heave、横摇 Roll、纵摇 Pitch），并调用 `ShipController.SetVisualWaveMotionEnabled(false)` 关闭表现层的纯数学晃动合成，将物理波浪晃动完全交由 DWP2 的刚体动力学解算。

---

## 7. CI / 无头环境自动化测试运行指南

MCIS 遵循“纯 C# 领域核心与引擎表现层解耦”架构。核心逻辑（AIS 解析、大地测量、航迹清洗、Hermite 插值、CPA 预计算、确定性时钟）均脱离 UnityEngine 独立组织在 `DotnetTests/` 工程中，可在无图形界面服务器或 CI/CD 管线中直接运行。

### 7.1 本地或 CI 执行命令
```bash
# 确保已安装 .NET 8 SDK
export DOTNET_CLI_TELEMETRY_OPTOUT=1

# 切换至测试工程目录并运行测试
cd unity/DotnetTests/Tests
~/.dotnet/dotnet test
```

### 7.2 测试覆盖范围
目前 `Mcis.Pure.Tests` 包含 63 个严格的单元测试：
* **AIS 报文解码**：真实 NMEA !AIVDM 1/2/3/5/18/19/24A/24B 报文往返解码与校验和错误拦截；
* **大地测量往返精度**：WGS84 ⇄ ECEF ⇄ ENU 坐标转换在毫米级与 1e-9 度极小容差下闭合；
* **Hermite 插值与缺口检测**：节点连续性、缺口跳过与直线外推验证；
* **CPA 算法双向交叉验证**：相对运动矢量法与论文 3.4 节三角函数解析法在极端交叉、对遇、追越场景下严格吻合；
* **确定性仿真时钟**：Seek(t) 跳转与连续微秒 Tick(t) 产生完全相同的状态机重放轨迹；
* **Demo 真实碰撞验证**：`lily_mary_demo.csv` 与 `lily_mary_demo.nmea` 真实数据全流程验证在约 T+9min 触发 Danger 告警并发生极近距离交汇。

---

## 8. 已知限制与未编译验证脚本清单

> [!WARNING]
> **无头容器未编译验证说明**：
> 当前开发与验证容器（Linux Docker）未安装 Unity Editor 运行时环境，因此所有依赖 `UnityEngine`、`UnityEngine.UIElements` 或第三方包（CesiumRuntime）的代码未经过 Unity 6 引擎编译器的链接验证。代码均依据 Unity 6.0 LTS API 手册编写，导入 Unity 6 工程后如遇细节警告可参考下表处理。

### 8.1 依赖 Unity 引擎环境的脚本清单
以下脚本需要在打开 Unity 6.0 LTS 编辑器后进行编译和目视核验：
1. **仿真驱动与物理控制器**：
   * `Assets/_Project/Scripts/Simulation/Ships/ShipController.cs`
   * `Assets/_Project/Scripts/Simulation/Ships/IShipController.cs`
2. **三维呈现与视图组件**：
   * `Assets/_Project/Scripts/Presentation/Ships/ShipView.cs`
   * `Assets/_Project/Scripts/Presentation/Ships/ShipStateSourceAdapter.cs`
   * `Assets/_Project/Scripts/Presentation/Bootstrap/SimulationLoopRunner.cs`
   * `Assets/_Project/Scripts/Presentation/Bootstrap/McisP1DemoBootstrap.cs`
3. **第三方平台适配器**：
   * `Assets/_Project/Scripts/Integrations/Cesium/CesiumGeoreferenceAdapter.cs`
4. **UI Toolkit 界面控件与表现层**：
   * `Assets/_Project/Scripts/UI/SimHud/SimHudController.cs`
   * `Assets/_Project/Scripts/UI/SimHud/SimHudControllerLayout.cs`
   * `Assets/_Project/Scripts/UI/SimHud/NavHud.cs`
   * `Assets/_Project/Scripts/UI/SimHud/TimelineBar.cs`
   * `Assets/_Project/Scripts/UI/MiniMap/MiniMapElement.cs`
   * `Assets/_Project/Scripts/UI/MiniMap/MiniMapElementDrawing.cs`

### 8.2 已知限制与注意事项
1. **UI Toolkit Unity 6 控件语法**：
   自定义 VisualElement（如 `NavHud`, `TimelineBar`, `MiniMapElement`）采用了 Unity 6 推荐的 `[UxmlElement] public partial class ...` 声明方式。如果工程降级到 Unity 2022.3，需恢复 `UxmlFactory` 工厂样板代码。
2. **Android / WebGL 平台 StreamingAssets 读取**：
   `McisP1DemoBootstrap` 目前使用 `File.ReadAllText` 进行桌面端同步读取。在 Android 移动端或 WebGL 运行环境中，StreamingAssets 位于只读压缩归档包内，必须使用 `UnityEngine.Networking.UnityWebRequest` 或 Unity 6 的 `Awaitable` 异步接口加载。
3. **Cesium 适配器原点同步**：
   若使用 `CesiumGeoreferenceAdapter`，其内部会直接读写 `CesiumGeoreference.latitude`、`longitude`、`height`。请确保场景中挂载了有效的 CesiumGeoreference 组件。

## 9. box 上的近似编译检查（2026-11-11 补充）
没有 Unity 编辑器，因此用 NuGet 包 `UnityEngine.Modules 2021.3.33` 作为参考程序集，近似编译了 P1 的 Unity 侧代码：`Simulation/Ships`、`Presentation/Ships`、`Presentation/Bootstrap`、`UI/**`，以及未定义 `MCIS_CESIUM` 时的 `Integrations/Cesium`。

检查方法：
- 那个包里没有 Unity 6 才有的 `UxmlElement`、`UxmlAttribute`、`Painter2D`，这几个类型用桩补上。
- 补桩之后只剩 1 个错误：`MeshGenerationContext.painter2D`。这是 Unity 6 才有的属性，不是代码问题。
- 其余代码与我们自己的类型对接，全部编译通过。

这项检查覆盖不到：
- Unity 6 的 UXML 源生成器和 USS 解析。
- Cesium API（`#if MCIS_CESIUM` 分支）。
- 运行时行为。

以上要以 Unity 6000.0.x 编辑器里实际打开为准。
