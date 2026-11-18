# MCIS · 海事事故调查仿真系统

Mark Wen（WMU）硕士论文项目，依据论文《Design and application research of maritime casualty investigation simulation based on Unity 3D》。目标是做一套完整、接近游戏体验、高端 UI 的海事事故调查仿真系统：Unity 6 + URP 三维回放与推演（Cesium、Dynamic Water 2、Enviro 3、AIS/VDR），加调查工作台（证据、询问比对、COLREG、分析、What-if、系统分析、人为因素、报告）。原型里的每个 UI 功能都要实现。正式产品定位为内网联机版，另有离线单机现场版，同一代码库。

> **接手开发请先读 [docs/HANDOFF-STAGE1.md](docs/HANDOFF-STAGE1.md)**（阶段性交接），再读 [AGENTS.md](AGENTS.md) 和 [ROADMAP.md](ROADMAP.md)。

## 组成

| 部分 | 位置 | 技术 |
|---|---|---|
| 纯 C# 计算核心 | `unity/Assets/_Project/Scripts/` | C# 9、netstandard2.1、无 UnityEngine |
| 计算核心 CLI | `tools/mcis-core/` | `cpa` / `align` / `colreg`，stdin/stdout JSON |
| 调查服务 | `service/` | FastAPI + SQLite，只监听 127.0.0.1:8765 |
| Web 工作台 | `web/` | Vite + React + TypeScript + ECharts |
| 接口合同 | `contracts/` | OpenAPI + JSON Schema |
| 原型与截图 | `prototype/`、`screenshots/` | 17 页高保真 HTML 原型 |
| 真实案例数据 | `reports/` | 海力5、YANGZE 22 公开报告（结构化，标来源与【直接】/【推算】/【估计】） |
| 验收与缺陷 | `tests_acceptance/`、`DEFECTS/`、`logs/` | 独立验收测试、缺陷与裁定、冻结哈希 |

## 合成图像／音频隔离演示

**暂停图音 prepare、后端启动及归档测试。** `seed_demo=False` 仅关闭填充调用，当前候选仍会在应用导入时加载包含案例常量的种子模块。不要执行下方快速开始来替代隔离流程。请先阅读 [固定版本与暂停事项、限定独验记录](docs/MEDIA-DEMO.md)。历史启动记录不构成重跑许可；clone 不证明资料净化，禁止打开或加入真实资料。浏览器、HTTP联动、可信身份及正式媒体归档恢复仍未完成验收。

## 快速开始

```bash
cd service && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && cd ..
cd web && npm install --no-audit --no-fund && cd ..
./run_dev.sh          # 后端 127.0.0.1:8765 + 前端 127.0.0.1:5173
```

.NET 8 SDK（`~/.dotnet/dotnet`）用于纯 C# 测试和 mcis-core。完整的测试命令和交接时的基线数字见 `docs/HANDOFF-STAGE1.md` §3。

## UI 原型

原型里的 Lily / Mary 案例全部为**示例数据（虚构）**，改编自论文 5.4 节。

### 打开原型
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

原型 09–17 页（证据中心、询问比对、COLREG、What-if、人为因素、系统分析、安全建议/报告、知识库、权限）在 `prototype/p6/`，截图见 `screenshots/1440/09-*.png` 至 `17-*.png`。

## 主要文档

- `docs/HANDOFF-STAGE1.md`：阶段性交接（当前状态、接手顺序）
- `AGENTS.md`：给代理的仓库规则
- `ROADMAP.md`：工作包与状态表
- `ARCHITECTURE.md`：Unity 工程架构，含分层、模块、C# 接口草案、状态机、`.mcase` JSON Schema、mermaid 图
- `contracts/CONTRACTS.md`：模块接口约定
- `reports/REAL_CASES.md`：真实案例基准
- `BRIEF.md`：设计需求说明；`thesis.txt`：论文文本
