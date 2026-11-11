# 海事事故调查三维仿真系统（MCIS-3D）· UI 原型与架构设计

> 依据 Mark Wen 硕士论文《Design and application research of maritime casualty investigation simulation based on Unity 3D》。原型里的 Lily / Mary 案例全部为**示例数据（虚构）**，改编自论文 5.4 节。

## 如何打开原型
直接用 Chrome / Edge 打开 `prototype/index.html`，双击即可。单文件，离线可用，没有外部依赖。推荐分辨率 1920×1080。

地址后面的 hash 对应各屏幕，也可以用左侧导航或顶部步骤条切换。

| # | Hash | 屏幕 | 对应论文 |
|---|------|------|---------|
| 1 | `#lobby` | 启动 / 案件大厅：案件卡片、新建/打开 `.mcase`、5.3 节 8 步流程 | 5.3 |
| 2 | `#case` | 案件信息录入：事故基本信息、船舶资料、证据清单 | 5.3 ① |
| 3 | `#ships` | 船舶与模型库：船型卡片、尺度/吃水/载货参数、线图预览 | 4.5.1, 5.3 ② |
| 4 | `#env` | 场景与环境：时间光照、风浪流、能见度、雨雾（标注 Enviro 3 / DWP2 参数） | 4.5.2 |
| 5 | `#track` | 航迹编辑：AIS(NMEA) 导入 / 手绘、关键点表、插值方式 | 4.5.3 |
| 6 | `#sim` | 主仿真：动态海面与两船、时间轴（播放/倍速/拖动/事件标记）、HUD、实时 DCPA/TCPA 风险色、小地图、ECFC 弹卡、四种视角 | 4.5.4–4.5.6, 5.3 ④⑤⑥ |
| 7 | `#ecfc` | ECFC 编辑器：事件矩形、条件椭圆、实线/虚线箭头、推定项虚线框、主序列水平 | 2.5 |
| 8 | `#analysis` | 分析与导出：距离/DCPA/TCPA 曲线、碰撞瞬间回放、PDF 报告预览、导出视频/PDF | 5.3 ⑦⑧ |

DCPA/TCPA 按示例轨迹实时计算。r 是目标船相对本船的位置，v 是相对速度：

- TCPA = −(r·v)/|v|²
- DCPA = |r + v·TCPA|

风险分三级：
- 红（危险）：DCPA < 0.3 nm 且 0 < TCPA < 6 min
- 琥珀（警告）：DCPA < 1 nm 且 0 < TCPA < 12 min
- 青（安全）：其余情况

## 文件
- `prototype/index.html`：高保真交互原型
- `ARCHITECTURE.md`：Unity 工程架构，包括：
  - 分层、模块、C# 接口草案
  - 状态机、目录结构
  - `.mcase` JSON Schema
  - 路线图、风险、测试
  - 7 张 mermaid 图
- `screenshots/`：1920×1080 截图；`screenshots/1440/` 是 1440×900 截图
- `BRIEF.md`：设计需求说明；`thesis.txt`：论文文本；`logs/`：生成过程日志
