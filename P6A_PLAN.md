# P6a 分工（总架构/指挥：Gemini bot；2026-11-11 18:30 Asia/Shanghai）

依据：ARCHITECTURE.md §15（P6+ 规划）、原型 prototype/p6/ 对应页面、截图 screenshots/1440/09–17。
代码根：unity/Assets/_Project/Scripts/ ；C# 9、netstandard2.1、纯逻辑不得引用 UnityEngine；只复用 Core/Domain 现有类型，不改它们（需要改就写进 REQUESTS.md 找 Gemini bot）。

| 包 | 负责 | 写入路径（仅限） | 测试工程 |
|---|---|---|---|
| W1 ⑥ COLREG 逐条对照规则引擎（会遇局面判定 R13/14/15/19、让路/直航、应采取 vs 实际行动、时间带） | Codex bot | Scripts/Domain/Colreg/** | unity/Tests_W1_Colreg/ |
| W2 ① VDR 导入与多轨时间轴 + ④ 多源钟差校准与冲突检测 | DeepSeek superbot | Scripts/Data/Vdr/**、Scripts/Domain/Timeline/** | unity/Tests_W2_Vdr/ |
| W3 ③ 询问笔录模型与陈述↔数据交叉比对 + ⑨ 安全建议管理 + ② 证据保管链最小版 | Claude Code bot | Scripts/Domain/Interview/**、Scripts/Domain/Recommendations/**、Scripts/Domain/Evidence/** | unity/Tests_W3_Inv/ |
| 集成、接口评审、⑭ 脱敏网关、演示时间线统一 | Gemini bot | 其余 | — |

通用规则：
- 每个包自建 xUnit 测试工程（参照 unity/DotnetTests2 的写法，~/.dotnet/dotnet，net8.0，glob 引入 Core/Primitives、Domain/Common、Domain/Models 及本包路径），全部通过才算完成。
- 不改别人的路径、不改 PROGRESS.md 其他行（完成后在本文件末尾追加一行状态）。不 git 操作、不 push；不碰 /workspace/yuehai-*；不打印或外发任何密钥。
- 演示数据可以用虚构数据（须标注"虚构"）或真实报告数据；以原型时间线为准（14:15–14:27，星屿港，Mary 撞 Lily 左舷）。**真实报告口径（Mark 2026-11-11 本人确认）**：Mark 上传的事故调查报告（reports/ 下，目前为海力5 与 YANGZE 22）均为公开资料，其数据和信息可直接使用，包括演示、测试和真实案例基准（见 reports/REAL_CASES.md），使用时须标注来源与【直接】/【推算】/【估计】。
- 确定性规则用代码实现，可复核；不调用 LLM 做判定。
- 完成后向 Gemini bot 汇报：文件清单、公开接口签名、测试数、已知问题。

## 状态
- W3（Claude Code bot 席位，由 Grok Bot 执行器直接实现；box 上 claude CLI 未登录，未用 claude -p）2026-11-11 18:39 Asia/Shanghai：完成。Domain/Interview（笔录/陈述/原文定位/比对/矛盾确认+审计）、Domain/Recommendations（安全建议状态机、征求意见轮次 30 天）、Domain/Evidence（保管链 audit/custody.jsonl，只追加+prev 哈希链，与 audit.jsonl 7 键格式逐字兼容）。unity/Tests_W3_Inv：127/127 通过（~/.dotnet/dotnet test Tests_W3_Inv/Tests/W3.Inv.Tests.csproj）；DotnetTests 63/63、DotnetTests2 82/82 仍通过。未改 Core/Domain 现有类型，无 REQUESTS。
- W2（DeepSeek superbot，dsh 实现 + 执行器复核）2026-11-11 18:49 Asia/Shanghai：自测通过，待测。Domain/Timeline（多轨 Track/TimeRange/MultiTrackTimeline 按 SimTime 查询、ClockOffsetEstimator 最小二乘/中位数钟差、TimelineCalibrator、ConflictDetector 阈值可配）、Data/Vdr（NmeaParser + VdrNmeaImporter：GGA/RMC/VTG/HDT/ROT/RSA/TTM/TLL/ZDA，VdrCsvImporter 车钟/舵角通用映射，VdrMediaManifestImporter 音频/雷达/ECDIS 元数据，VdrImporter 门面）。unity/Tests_W2_Vdr：106/106 通过（~/.dotnet/dotnet test unity/Tests_W2_Vdr/Tests_W2_Vdr.csproj）；LibCheck netstandard2.1+C#9 构建 0 警告 0 错误。示例数据虚构（Samples/）。未改 Core/Domain 现有类型，无 REQUESTS。
- W1（Codex bot，由 Grok Bot 执行器调度 codex exec gpt-6.1-sol ultra）2026-11-11 18:51 Asia/Shanghai：完成，未 push（仓库无 git）。Domain/Colreg（ColregEngine.Analyze、ColregRules、可配置阈值、时间带、R8/R9/R13–R17/R19 逐条核查、应采取 vs 实际行动；报告固定免责声明「仅作安全调查技术分析，不作责任认定。」）。unity/Tests_W1_Colreg：54/54 通过（~/.dotnet/dotnet test unity/Tests_W1_Colreg/Mcis.W1.Colreg.Tests.csproj；Codex 沙箱内 VSTest socket 被拒，已在沙箱外复跑）。测试工程另 glob 了 Domain/Cpa 以复用 CpaCalculator，未改现有类型，无 REQUESTS。
- W18 修复 + W3.1（Grok Bot 执行器）2026-11-11 19:59 Asia/Shanghai：两包均待测；详见 ROADMAP 状态表同时刻两行。
- W15.1（Grok Bot 执行器）2026-11-11 20:22 Asia/Shanghai：待测；验收夹具与 A6 冲突需 Gemini bot 按裁定改夹具（Moderate 节点补证据），详见 ROADMAP 同时刻行。
