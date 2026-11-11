# 设计任务说明（BRIEF）

背景：用户 Mark Wen（肇庆港口海事处副处长）的硕士论文《Design and application research of maritime casualty investigation simulation based on Unity 3D》全文在 ./thesis.txt。务必完整阅读，尤其：2.5 节 ECFC 画法规则、3.4 节 DCPA/TCPA、4.5 节特殊需求（4.5.1–4.5.6）、5.3 节 8 步使用流程、5.4 节 Lily/Mary 案例。

已完成：无人机倾斜摄影三维模型；Cesium for Unity 植入地形；Dynamic Water 2 + Enviro 3 实现天气和水面；AIS 数据已能拉进 Unity。

目标：把这套海事事故调查仿真系统当成一个“游戏”来设计：体验好、UI 高级。先设计 UI，同时设计架构。全部中文界面/中文文档。

## 交付物 A：ARCHITECTURE.md（中文）
Unity 工程整体架构：
- 分层：数据层 / 领域层 / 仿真层 / 表现层 / UI 层
- 模块划分与职责：CaseManager、AIS 导入与插值（NMEA !AIVDM 解析、CSV、时间对齐、线性/Hermite 插值、异常点剔除）、坐标转换 WGS84→ECEF→Cesium(CesiumGeoreference)/Unity 本地 ENU、TrackPlayback 时间轴、ShipController、CPA 计算（DCPA/TCPA 公式，附推导）、EnvironmentBridge 对接 Enviro 3 / Dynamic Water 2、CollisionDamage（碰挤/受损/沉没）、ECFC 模型与运行时卡片、MiniMap、CameraRig（驾驶台/跟随/俯视/自由，可用 Cinemachine）、Recorder/ReportExporter（Unity Recorder 视频、PDF 报告）
- 关键数据结构与接口（C# 接口签名草案）
- 事件总线 / 游戏状态机（大厅→案件配置→仿真→分析），附 mermaid stateDiagram
- UI 技术选型：UI Toolkit vs uGUI，给出理由和建议（如：屏幕空间 UI 用 UI Toolkit，世界空间 ECFC 卡片用 uGUI 或 UITK world-space）
- 目录结构（Assets/_Project/...）
- 案件文件格式（JSON Schema，.mcase 包）
- 分期实施路线图（第一期：AIS 回放 + HUD + CPA + 小地图）
- 风险与注意事项（浮点精度/大坐标、Cesium 原点平移、AIS 时间缺口、证据性与可追溯、性能）
- 至少 4 张 mermaid 图（分层架构、模块依赖、状态机、回放时序），语法必须正确（节点文本含中文/括号时用双引号）

## 交付物 B：prototype/index.html 高保真交互式原型
- 单个 HTML 文件（内联 CSS/JS），无需构建，离线可用，不引用任何外部 CDN/字体/图片
- 风格：深色、电影级/AAA 游戏质感，参考海军指挥舰桥、ECDIS、高端模拟器 HUD；玻璃拟态面板、发光细线、等宽数字（font-family: ui-monospace, "JetBrains Mono", Consolas, monospace），克制的强调色（青色 #3be3ff 主色，琥珀色告警，红色危险）；中文字体回退 "PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif
- 屏幕（可通过左侧导航/顶部步骤条/hash 路由互相切换，例如 #lobby #case #ships #env #track #sim #ecfc #analysis）：
  1. 启动/案件大厅：新建/打开案件，案件卡片（含示例案件）
  2. 案件信息录入：事故基本信息（时间、地点经纬度、事故类型、等级、调查员）、船舶资料（船名、IMO、MMSI、船旗、船长、船员）
  3. 船舶与模型库：模型卡片网格（散货船、集装箱船、油轮、渔船、客滚等），参数（总长、型宽、吃水、载货量/装载状态）
  4. 场景与环境：时间/光照、风速风向、浪高/周期、流速流向、能见度、雨/雾强度，标注对应 Enviro 3 / Dynamic Water 2 参数名
  5. 航迹编辑：AIS 导入（文件拖放区示意）/手绘模式，海图画布上画航迹与关键点，关键点列表（时间、航速、航向）
  6. 主仿真：3D 视口占位（canvas 动画：动态海面、航道、两船随时间运动、航迹尾迹）；时间轴回放（播放/暂停、倍速 0.5x-16x、拖动、关键事件标记）；航行数据 HUD（每船：经纬度、SOG、COG、HDG；风速风向；DCPA/TCPA 实时数值与风险等级色）；2D 小地图带完整航迹和当前位置；ECFC 事件卡片按时间弹出；摄像机视角切换（驾驶台/跟随/俯视/自由）
  7. ECFC 编辑器：事件=矩形、条件=椭圆、事件之间实线箭头、条件到事件虚线箭头、推定项用虚线框、主序列水平居中排列且加粗箭头、次序列在上下；可选中节点查看属性
  8. 分析与导出：碰撞瞬间回放、关键指标图表（距离/DCPA/TCPA 随时间曲线，用 canvas/SVG 自绘）、导出视频/PDF 报告预览
- 演示数据：论文 5.4 节 Lily（散货船，卸货后离港）与 Mary（满载集装箱船，自外国驶来）在窄航道相遇，双方都尝试避让但一方操作失误，最终碰撞，Lily 严重受损开始下沉。必须在界面显著标注“示例数据 / 虚构”。坐标用一个虚构海岛港口附近的经纬度（虚构即可）。
- DCPA/TCPA 必须由示例轨迹按真实公式实时计算：相对位置 r = P_target − P_own，相对速度 v = V_target − V_own，TCPA = −(r·v)/|v|²，DCPA = |r + v·TCPA|（TCPA<0 表示已过最近点）。单位海里/分钟。风险分级：例如 DCPA<0.3nm 且 0<TCPA<6min 为危险（红），DCPA<1nm 且 TCPA<12min 为警告（琥珀），否则安全（青/绿）。
- 无 JS 报错，所有屏幕布局在 1920×1080 和 1440×900 下不破。
