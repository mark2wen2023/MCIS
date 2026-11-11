# P1 任务 B：Unity 侧代码（ShipController/ShipView、Cesium 适配器、UI Toolkit、Demo、INTEGRATION.md）

先阅读 ./ARCHITECTURE.md（第 4.3、4.4、4.5、4.10、5.3 节中 Mcis.Simulation / Mcis.Simulation.Ships / Mcis.UI.MiniMap / Presentation 相关接口，第 9 章 UI 选型，第 10 章目录与 asmdef，第 12 节 P1），并浏览 ./prototype/index.html 的 CSS 变量与 #sim 屏结构（视觉风格基准），以及**已经写好的纯 C# 核心** ./unity/Assets/_Project/Scripts/（Core/Primitives、Domain/**、Simulation/Clock、Simulation/Cpa）——你的代码必须基于这些已有类型与接口，不得重复定义或改其签名（若确需小改，改后必须保证 ./unity/DotnetTests 下 `~/.dotnet/dotnet test` 仍全部通过）。

输出根目录：./unity/Assets/_Project/。严格用文档的命名空间、目录、asmdef。

## 编写范围
1. Scripts/Simulation/Ships：ShipController（引擎侧 MonoBehaviour 或纯类+驱动器，按文档接口），订阅 SimClock 时间，从插值轨迹取位置/航向，经 IGeoConverter 转 Unity 坐标；Scripts/Presentation/Ships：ShipView（MonoBehaviour，平滑设置 Transform 位置与旋转，船首向→Unity yaw，可选尾迹 TrailRenderer，船长缩放）。可补 SimulationLoopRunner（MonoBehaviour，在 Update 中 clock.Tick(Time.unscaledDeltaTime)）。
2. Scripts/Integrations/Cesium：CesiumGeoreferenceAdapter，实现 IGeoConverter（或文档对应接口）；读取 CesiumGeoreference 的原点（latitude/longitude/height），用 CesiumForUnity 的 API（CesiumGeoreference.TransformEarthCenteredEarthFixedPositionToUnityPosition 等，若不确定 API 则以 Domain GeoMath 的 ENU 计算为后备）。隔离方式：独立 asmdef Mcis.Integrations.Cesium，references 含 "CesiumRuntime"，并用 asmdef 的 defineConstraints 或 versionDefines（包名 com.cesium.unity → 定义 MCIS_CESIUM），代码用 #if MCIS_CESIUM 包住，确保未安装 Cesium 时整个工程仍能编译。另提供一个不依赖 Cesium 的 LocalEnuGeoConverter（Presentation 或 Simulation 层）作为默认实现。
3. Scripts/UI（UI Toolkit，Mcis.UI asmdef）：
   - SimHud/NavHud：VisualElement/Presenter，显示每船 经纬度（度分格式）、SOG、COG、HDG，以及 DCPA/TCPA 和风险等级（USS 类 risk-safe/risk-warning/risk-danger 变色）。
   - SimHud/TimelineBar：播放/暂停、倍速按钮组（0.5x–16x）、可拖动进度条（Seek）、关键事件标记（如最近会遇点、碰撞），当前时间/总时长等宽数字。
   - MiniMap/MiniMapElement：自定义 VisualElement，generateVisualContent 中用 Painter2D 画网格、两船完整航迹、当前位置与船首向三角、CPA 连线；自动适配范围。
   - 每个配 UXML 与 USS（UI/Common/ThemeVariables.uss 定义变量：深色玻璃背景 rgba(8,18,32,0.72)、描边 rgba(59,227,255,0.35)、主色 #3be3ff、琥珀 #ffb020、红 #ff4d5e、等宽字体）。视觉对齐 prototype。
   - UI/SimHud/SimHudController：MonoBehaviour，挂在 UIDocument 上，绑定 SimClock、CpaService、两船轨迹到上述元素。
4. Scripts/Presentation/Bootstrap 或 Demo：Demo 引导脚本 McisP1DemoBootstrap（MonoBehaviour）：加载示例数据（TextAsset 或 StreamingAssets 中的 NMEA/CSV），解码→清洗→插值→CpaService 预计算→创建/绑定两船 ShipView、SimClock、HUD；可选择使用 Cesium 适配器或本地 ENU；Inspector 可配原点经纬度。
5. 示例数据：./unity/Assets/StreamingAssets/Mcis/Demo/ 下 lily_mary_demo.csv（以及可选 .nmea），Lily（散货船）与 Mary（集装箱船）窄航道会遇至碰撞，约 15 分钟、10 秒间隔，位置在虚构海岛港口附近（可用 21.78N,113.70E 一带，与原型一致），文件头注释与 README 明确“示例数据（虚构），改编自论文 5.4 节”。用一个小脚本（python3 或 C#）生成，确保两船约 T+9min 相遇，CPA 很小。生成脚本也放进 ./unity/Tools/。
6. asmdef：Mcis.Presentation、Mcis.UI、Mcis.Integrations.Cesium（按 10.2 表，但 P1 不需要 Cinemachine/TMP/InputSystem/Burst 的就别引用，避免缺包编译失败；在 INTEGRATION.md 说明）。确认 Mcis.Simulation.asmdef 若引用了 Unity.Burst/Unity.Collections 而 P1 未用，则移除以减少依赖。
7. ./unity/INTEGRATION.md（中文）：
   - 推荐 Unity 版本（Unity 6 LTS 或 2022.3 LTS）、渲染管线（与 Enviro3/DWP2/Cesium 兼容说明）、需要的包（UI Toolkit 内置、Cesium for Unity 可选）。
   - 如何拷进工程（拷贝 Assets/_Project 与 StreamingAssets/Mcis；asmdef 结构说明；不会影响 Mark 现有脚本）。
   - 如何接 Mark 已有的 AIS 数据：NMEA 原始报文 / CSV 列映射 / 他现有拉进 Unity 的 AIS 管线如何对接（实现某个接口或把 TrackSample 列表交给 Demo 引导）。
   - 如何接 Cesium 场景：CesiumGeoreference 原点设置、MCIS_CESIUM 宏、船模放在 CesiumGlobeAnchor 还是 georeference 子物体下的取舍、浮点精度。
   - 场景搭建步骤（逐步：建空场景/在现有 Cesium 场景、添加 UIDocument+PanelSettings、挂 Demo 引导、指定两船 prefab、运行）。
   - 与 Enviro3/DWP2 共存注意（P1 不接环境，ShipView 的竖直位置可交给 DWP2 浮力或固定水面高度）。
   - 已知限制与未编译验证说明。
   - 如何在 box/CI 上跑 dotnet 测试。

## 约束
- C# 9 兼容（无 file-scoped namespace、无 record、无全局 using）。
- 引擎侧代码要认真自查：API 名称正确（UnityEngine.UIElements：VisualElement、generateVisualContent、MeshGenerationContext.painter2D、Painter2D.BeginPath/MoveTo/LineTo/Stroke/Fill、UxmlFactory/UxmlElement 用法与版本差异——Unity 6 推荐 [UxmlElement] partial class，2022.3 用 UxmlFactory；用 #if UNITY_2023_2_OR_NEWER 兼容两者）。
- 分多次小步写文件（每次 ≤ 250 行）。只允许在 /workspace/maritime-sim-design/unity 内写文件。不要联网（dotnet test 用已有缓存即可），不要 git 操作。
- 完成后最后再跑一次 `cd ./unity/DotnetTests && ~/.dotnet/dotnet test`，确认仍全部通过。

## 更新（16:24）：唯一目标 Unity 6.0（6000.0.x LTS）
- UI Toolkit 自定义控件只用 `[UxmlElement] public partial class X : VisualElement` + `[UxmlAttribute]`；删除所有 UxmlFactory/UxmlTraits 及 `#if UNITY_2023_2_OR_NEWER` 兼容分支。
- 使用 Unity 6 API：Rigidbody.linearVelocity/angularVelocity（非 velocity）、Object.FindFirstObjectByType/FindAnyObjectByType（非 FindObjectOfType）、Awaitable（异步加载 StreamingAssets 可用 Awaitable/UnityWebRequest）、MeshGenerationContext.painter2D。
- Cesium for Unity 按支持 Unity 6 的版本（com.cesium.unity 1.13+），API：CesiumForUnity.CesiumGeoreference（latitude/longitude/height、TransformEarthCenteredEarthFixedPositionToUnityPosition / TransformUnityPositionToEarthCenteredEarthFixed，double3）、CesiumGlobeAnchor（longitudeLatitudeHeight、positionGlobeFixed）。
- INTEGRATION.md 写明 Unity 6.0 LTS 及包版本。
