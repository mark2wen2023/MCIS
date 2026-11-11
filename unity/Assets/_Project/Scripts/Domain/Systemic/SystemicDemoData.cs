using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.HumanFactors;

namespace Mcis.Domain.Systemic
{
    /// <summary>
    /// 【示例数据（虚构）】星屿港 Lily × Mary 窄航道碰撞演示（原型时间线 2026-05-18 14:15–14:27，船时 UTC+8）：
    /// 14:15:00 Lily 卸空离泊（E1）→ 14:18:30 两船进入窄航道（E2）→ 14:20:12 VTS 呼叫 Mary，答“保持航向”→
    /// 14:20:30 形成小 DCPA 对遇（E3）→ 14:22:15 Mary 左舵 20° 违规左转（E4）→ 14:22:45 Lily 紧急右满舵（E5）→
    /// 14:23:20 Mary 停车 / 14:23:34 Mary 船长上驾驶台 → 14:24:00 Mary 球鼻艏撞 Lily 左舷（E6）→ 14:27:30 Lily 进水开始下沉（E7）。
    /// 条件：C1 Mary 航速 13.5 kn 过高；C2 Mary 瞭望疏忽（推定）；C3 VHF 未达成一致；C4 航道狭窄且能见度 1.6 nm；
    /// C5 1.8 kn 横流；C6 Lily 空载吃水浅、水密受损。
    /// 所有船名、ID、时间、证据、HFACS 发现与建议编号均为虚构，不代表任何真实事故；不使用 reports/ 下任何内容。
    /// </summary>
    public static class SystemicDemoData
    {
        public const string CaseId = "CASE-2026-LM01";

        /// <summary>演示用 ECFC 节点（与原型 ECFC 图一致，虚构）。</summary>
        public static readonly IReadOnlyList<string> EcfcNodeIds = new[] { "E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "C1", "C2", "C3", "C4", "C5", "C6" };

        /// <summary>演示用证据（虚构）：EV-001 Mary VDR 舵角/车钟；EV-002 AIS 轨迹；EV-003 VHF16 录音；EV-004 Mary ARPA 截图；
        /// EV-005 Mary 大副询问笔录；EV-006 Lily 破损检验；EV-007 VTS 值班记录；EV-008 Mary 公司 SMS 文件。</summary>
        public static readonly IReadOnlyList<string> EvidenceIds = new[] { "EV-001", "EV-002", "EV-003", "EV-004", "EV-005", "EV-006", "EV-007", "EV-008" };

        /// <summary>演示用 HFACS 发现（虚构，对应 W18）：HF-F01 疲劳；HF-F02 误判左转；HF-F03 未召唤船长（BRM）；HF-F04 SMS 无雾航程序。</summary>
        public static readonly IReadOnlyList<string> HfacsFindingIds = new[] { "HF-F01", "HF-F02", "HF-F03", "HF-F04" };

        /// <summary>演示用安全建议（虚构，对应 W3）：SR-2026-01 VTS 雾中单向管制；SR-2026-02 公司雾航程序；SR-2026-03 BRM 召唤船长培训。</summary>
        public static readonly IReadOnlyList<string> RecommendationIds = new[] { "SR-2026-01", "SR-2026-02", "SR-2026-03" };

        private static SystemicRefs R(string[] ev = null, string[] ecfc = null, string[] hf = null, string[] sr = null)
        {
            return new SystemicRefs(ev, ecfc, hf, sr);
        }

        private static T Ok<T>(Result<T> r)
        {
            if (!r.IsSuccess)
            {
                throw new InvalidOperationException("演示数据构建失败：" + r.ErrorCode + " " + r.ErrorMessage);
            }

            return r.Value;
        }

        public static SystemicDocument Build()
        {
            return new SystemicDocument(CaseId, true, BuildBowTie(), BuildAcciMap(), BuildStamp());
        }

        public static BowTieModel BuildBowTie()
        {
            const EvidenceStrength S = EvidenceStrength.Strong, M = EvidenceStrength.Moderate, V = EvidenceStrength.ToBeVerified;
            var m = Ok(BowTieModel.Create("BT-LM01", "狭窄航道·雾中双向通航（虚构）", "TOP", "两船碰撞 Lily × Mary 14:24:00（虚构）", S, R(new[] { "EV-001", "EV-002" }, new[] { "E6" })));
            Ok(m.AddThreat("T-VIS", "能见度不良（雾，1.6 nm）", S, R(new[] { "EV-007" }, new[] { "C4" })));
            Ok(m.AddThreat("T-CUR", "横流影响（1.8 kn）", M, R(new[] { "EV-002" }, new[] { "C5" })));
            Ok(m.AddThreat("T-TURN", "Mary 判断失误左转（14:22:15 左舵 20°）", S, R(new[] { "EV-001", "EV-005" }, new[] { "E4" }, new[] { "HF-F02" })));
            Ok(m.AddThreat("T-LOOK", "瞭望不足（推定）", V, R(null, new[] { "C2" })));
            Ok(m.AddThreat("T-VHF", "船间通信不畅（VHF 未达成一致）", S, R(new[] { "EV-003" }, new[] { "C3" })));

            Ok(m.AddBarrier("PB-FOG", "雾航程序 / 安全航速", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(new[] { "EV-001", "EV-008" }, new[] { "C1" }, new[] { "HF-F04" }, new[] { "SR-2026-02" })));
            Ok(m.AddBarrier("PB-ARPA", "雷达 / ARPA 观测与碰撞报警", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(new[] { "EV-004" })));
            Ok(m.AddBarrier("PB-PLAN", "航路规划余量", BowTieElementKind.PreventionBarrier, BarrierState.Unknown, V));
            Ok(m.AddBarrier("PB-VTS", "VTS 交通组织与警告", BowTieElementKind.PreventionBarrier, BarrierState.Degraded, S, R(new[] { "EV-003", "EV-007" }, null, null, new[] { "SR-2026-01" }), "VTS-XY"));
            Ok(m.AddBarrier("PB-BRM", "BRM 交叉核查 / 召唤船长", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(new[] { "EV-005" }, null, new[] { "HF-F03" }, new[] { "SR-2026-03" })));
            Ok(m.AddBarrier("PB-LOOK", "专职瞭望", BowTieElementKind.PreventionBarrier, BarrierState.Missing, M, R(new[] { "EV-005" }, new[] { "C2" })));
            Ok(m.AddBarrier("PB-VHF", "VHF 协调", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(new[] { "EV-003" }, new[] { "C3" })));

            Ok(m.AddBarrier("MB-WT", "水密分舱", BowTieElementKind.MitigationBarrier, BarrierState.Degraded, S, R(new[] { "EV-006" }, new[] { "C6" }), "LILY"));
            Ok(m.AddBarrier("MB-DC", "应急堵漏 / 排水", BowTieElementKind.MitigationBarrier, BarrierState.Unknown, V));
            Ok(m.AddBarrier("MB-SAR", "救生与搜救", BowTieElementKind.MitigationBarrier, BarrierState.Effective, M, R(new[] { "EV-007" })));
            Ok(m.AddBarrier("MB-OIL", "油舱封堵 / 溢油应急", BowTieElementKind.MitigationBarrier, BarrierState.Effective, M, R(new[] { "EV-007" })));
            Ok(m.AddBarrier("MB-NAV", "航行警告 / 沉船标示", BowTieElementKind.MitigationBarrier, BarrierState.Effective, M, R(new[] { "EV-007" })));

            Ok(m.AddConsequence("CQ-SINK", "Lily 左舷破损进水下沉（14:27:30）", S, R(new[] { "EV-006" }, new[] { "E7" })));
            Ok(m.AddConsequence("CQ-PERSON", "人员落水 / 伤亡风险", M, R(new[] { "EV-007" })));
            Ok(m.AddConsequence("CQ-OIL", "燃油泄漏", V));
            Ok(m.AddConsequence("CQ-BLOCK", "航道阻塞", M, R(new[] { "EV-007" })));

            Ok(m.AddEscalationFactor("EF-MASTER", "船长 14:23:34 才上驾驶台（之前未被召唤）", "PB-BRM", S, R(new[] { "EV-005" }, null, new[] { "HF-F03" })));
            Ok(m.AddEscalationFactor("EF-FATIGUE", "Mary 大副前一晚睡眠不足（推定）", "PB-LOOK", V, R(null, null, new[] { "HF-F01" })));
            Ok(m.AddEscalationFactor("EF-BALLAST", "Lily 空载吃水浅、受风面大", "MB-WT", M, R(new[] { "EV-006" }, new[] { "C6" })));

            Connect(m, "T-VIS", "PB-FOG", "PB-ARPA", "TOP");
            Connect(m, "T-CUR", "PB-PLAN", "TOP");
            Connect(m, "T-TURN", "PB-VTS", "PB-BRM", "TOP");
            Connect(m, "T-LOOK", "PB-LOOK", "TOP");
            Connect(m, "T-VHF", "PB-VHF", "TOP");
            Connect(m, "TOP", "MB-WT", "MB-DC", "CQ-SINK");
            Connect(m, "TOP", "MB-SAR", "CQ-PERSON");
            Connect(m, "TOP", "MB-OIL", "CQ-OIL");
            Connect(m, "TOP", "MB-NAV", "CQ-BLOCK");
            return m;
        }

        private static void Connect(BowTieModel m, params string[] path)
        {
            for (int i = 1; i < path.Length; i++)
            {
                Ok(m.Connect(path[i - 1], path[i]));
            }
        }

        public static AcciMapModel BuildAcciMap()
        {
            const EvidenceStrength S = EvidenceStrength.Strong, M = EvidenceStrength.Moderate, V = EvidenceStrength.ToBeVerified;
            var m = Ok(AcciMapModel.Create("AM-LM01", "星屿港 Lily × Mary 碰撞 AcciMap（虚构）"));
            Ok(m.AddNode("G1", "港区雾中单向通航规定缺位", AcciMapLevel.Government, V));
            Ok(m.AddNode("R1", "VTS 未实施雾中单向管制", AcciMapLevel.Regulatory, S, R(new[] { "EV-007" }, null, null, new[] { "SR-2026-01" })));
            Ok(m.AddNode("R2", "航标配置不足", AcciMapLevel.Regulatory, V));
            Ok(m.AddNode("CO1", "SMS 无雾航程序", AcciMapLevel.Company, S, R(new[] { "EV-008" }, null, new[] { "HF-F04" }, new[] { "SR-2026-02" })));
            Ok(m.AddNode("CO2", "船期与航次压力", AcciMapLevel.Company, V));
            Ok(m.AddNode("CO3", "工休管理失效", AcciMapLevel.Company, M, R(new[] { "EV-005" }, null, new[] { "HF-F01" })));
            Ok(m.AddNode("SM1", "船长未上驾驶台（14:23:34 才到）", AcciMapLevel.ShipManagement, S, R(new[] { "EV-003", "EV-005" }, null, new[] { "HF-F03" })));
            Ok(m.AddNode("SM2", "BRM 失效（未召唤船长、无交叉核查）", AcciMapLevel.ShipManagement, S, R(new[] { "EV-005" }, null, new[] { "HF-F03" }, new[] { "SR-2026-03" })));
            Ok(m.AddNode("SM3", "OOW 疲劳（推定）", AcciMapLevel.ShipManagement, V, R(null, null, new[] { "HF-F01" })));
            Ok(m.AddNode("CA1", "Mary 14:20:12 答 VTS“保持航向”", AcciMapLevel.CrewActs, S, R(new[] { "EV-003" }, new[] { "E3" })));
            Ok(m.AddNode("CA2", "Mary 14:22:15 左舵 20° 违规左转", AcciMapLevel.CrewActs, S, R(new[] { "EV-001" }, new[] { "E4" }, new[] { "HF-F02" }), "MARY"));
            Ok(m.AddNode("CA3", "Lily 14:22:45 紧急右满舵", AcciMapLevel.CrewActs, S, R(new[] { "EV-002" }, new[] { "E5" }), "LILY"));
            Ok(m.AddNode("EE1", "ARPA 设置不当", AcciMapLevel.EquipmentEnvironment, M, R(new[] { "EV-004" })));
            Ok(m.AddNode("EE2", "能见度 1.6 nm", AcciMapLevel.EquipmentEnvironment, S, R(new[] { "EV-007" }, new[] { "C4" })));
            Ok(m.AddNode("EE3", "横流 1.8 kn", AcciMapLevel.EquipmentEnvironment, M, R(new[] { "EV-002" }, new[] { "C5" })));
            Ok(m.AddNode("EE4", "14:24:00 Mary 球鼻艏撞 Lily 左舷", AcciMapLevel.EquipmentEnvironment, S, R(new[] { "EV-001", "EV-002" }, new[] { "E6" })));
            Ok(m.AddNode("EE5", "14:27:30 Lily 进水开始下沉", AcciMapLevel.EquipmentEnvironment, S, R(new[] { "EV-006" }, new[] { "E7" })));

            string[,] edges =
            {
                { "G1", "R1" }, { "R1", "CA1" }, { "R2", "CA2" },
                { "CO1", "SM2" }, { "CO2", "SM1" }, { "CO3", "SM3" },
                { "SM1", "CA2" }, { "SM2", "CA2" }, { "SM3", "CA2" }, { "SM2", "CA1" },
                { "CA1", "CA2" },
                { "EE1", "CA2" }, { "EE2", "CA2" }, { "EE3", "CA3" },
                { "CA2", "EE4" }, { "CA3", "EE4" }, { "EE4", "EE5" }
            };
            for (int i = 0; i < edges.GetLength(0); i++)
            {
                Ok(m.Connect(edges[i, 0], edges[i, 1]));
            }

            // A2 信息流（由下往上，不参与成环与方向规则）：Mary 回复“保持航向”上报到 VTS 层。
            Ok(m.ConnectInformationFlow("CA1", "R1"));

            return m;
        }

        public static StampModel BuildStamp()
        {
            const EvidenceStrength S = EvidenceStrength.Strong, M = EvidenceStrength.Moderate, V = EvidenceStrength.ToBeVerified;
            var m = Ok(StampModel.Create("ST-LM01", "两船在雾中窄航道内碰撞（虚构）"));
            Ok(m.AddController("MSA", "海事主管机关（虚构）", V)); // W15.1 A6：无证据 → 降为 ToBeVerified
            Ok(m.AddController("VTS", "星屿港 VTS（虚构）", S, R(new[] { "EV-007" })));
            Ok(m.AddController("CO", "Mary 管理公司（岸基）", M, R(new[] { "EV-008" })));
            Ok(m.AddController("MASTER", "Mary 船长", M, R(new[] { "EV-005" })));
            Ok(m.AddController("OOW", "Mary 值班大副", S, R(new[] { "EV-005" })));
            Ok(m.AddController("LOOW", "Lily 值班二副", M, R(new[] { "EV-002" })));
            Ok(m.AddControlledProcess("SHIP-M", "Mary 船舶操纵运动", S, R(new[] { "EV-001" })));
            Ok(m.AddControlledProcess("SHIP-L", "Lily 船舶操纵运动", S, R(new[] { "EV-002" })));

            Ok(m.AddControlAction("CA-REG", "通航管制规定 / 授权", "MSA", "VTS", V));
            Ok(m.AddControlAction("CA-VTS", "交通信息与避让建议（14:20:12 呼叫）", "VTS", "OOW", S, R(new[] { "EV-003" })));
            Ok(m.AddControlAction("CA-SMS", "SMS / 雾航程序 / 工休安排", "CO", "MASTER", S, R(new[] { "EV-008" }, null, new[] { "HF-F04" })));
            Ok(m.AddControlAction("CA-ORD", "船长常规命令（何时召唤船长）", "MASTER", "OOW", M, R(new[] { "EV-005" })));
            Ok(m.AddControlAction("CA-HELM", "舵令 / 车令", "OOW", "SHIP-M", S, R(new[] { "EV-001" }, new[] { "E4" })));
            Ok(m.AddControlAction("CA-LHELM", "舵令 / 车令", "LOOW", "SHIP-L", S, R(new[] { "EV-002" }, new[] { "E5" })));

            Ok(m.AddFeedback("FB-VTS", "VTS 运行报告", "VTS", "MSA", V));
            Ok(m.AddFeedback("FB-OOW-VTS", "回复“保持航向”（14:20:12）", "OOW", "VTS", S, R(new[] { "EV-003" })));
            Ok(m.AddFeedback("FB-MASTER-CO", "航次报告", "MASTER", "CO", V));
            Ok(m.AddFeedback("FB-SHIP-M", "雷达 / ARPA / 目视", "SHIP-M", "OOW", M, R(new[] { "EV-004" })));
            Ok(m.AddFeedback("FB-SHIP-L", "雷达 / 目视", "SHIP-L", "LOOW", M, R(new[] { "EV-002" })));
            // 有意缺省：OOW → MASTER 的反馈（召唤船长）未建立 → 校验会报 sys_missing_feedback（CAST 发现）。

            Ok(m.AddUnsafeControlAction("UCA-1", "VTS 未提供单向管制或明确避让建议", "CA-VTS", UcaType.NotProvided, "雾中能见度 1.6 nm、两船对遇 DCPA < 0.1 nm（14:20:30，按 ROADMAP 重算值）", S, R(new[] { "EV-003", "EV-007" }, new[] { "E3" }, null, new[] { "SR-2026-01" })));
            Ok(m.AddUnsafeControlAction("UCA-2", "Mary 左舵 20°", "CA-HELM", UcaType.ProvidedCausesHazard, "对遇态势下向左转（14:22:15），违反 R14(a)", S, R(new[] { "EV-001" }, new[] { "E4" }, new[] { "HF-F02" })));
            Ok(m.AddUnsafeControlAction("UCA-3", "Mary 停车 / 倒车过迟", "CA-HELM", UcaType.WrongTimingOrOrder, "14:23:00 应停车倒车，实际 14:23:20 停车", S, R(new[] { "EV-001" })));
            Ok(m.AddUnsafeControlAction("UCA-4", "Mary 保持航向 008° 持续过久", "CA-HELM", UcaType.StoppedTooSoonOrAppliedTooLong, "14:20:40 起应大幅右转，仍保持航向至 14:22:15", S, R(new[] { "EV-001", "EV-002" }, new[] { "E3" })));
            Ok(m.AddUnsafeControlAction("UCA-5", "常规命令未要求雾中召唤船长", "CA-ORD", UcaType.NotProvided, "进入雾区窄航道（14:18:30）", M, R(new[] { "EV-005" }, new[] { "E2" }, new[] { "HF-F03" }, new[] { "SR-2026-03" })));
            return m;
        }
    }
}
