using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Systemic;
using Xunit;
using static Mcis.Acceptance.W15.Fx;

namespace Mcis.Acceptance.W15
{
    /// <summary>
    /// 真实案例用例：广州“10·25”海力5 / WAN HAI A17 碰撞（公开调查报告，Mark 已同意使用；只读 reports/haili5/case.json 与 ecfc.json）。
    /// 用报告认定的 3 条直接原因、3 条间接原因手工搭 AcciMap 与 Bow-tie，检验模型能否表达。节点标签直接取 case.json 原文，
    /// 证据引用用报告页码（report:pNN，与 ecfc.json 一致），ECFC 引用用 ecfc.json 节点 ID 并以其全集做引用校验。
    /// </summary>
    public class RealCaseHaili5Tests
    {
        private sealed class Case
        {
            public string CaseId;
            public bool IsFictionalDemo;
            public string[] Direct;
            public string[] Indirect;
            public string[] EcfcIds;
            public Dictionary<string, string[]> EcfcEvidence;
        }

        private static Case Load()
        {
            string dir = Path.Combine(RepoRoot(), "reports", "haili5");
            using var c = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "case.json")));
            using var e = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "ecfc.json")));
            var lia = c.RootElement.GetProperty("liability");
            var nodes = e.RootElement.GetProperty("nodes").EnumerateArray().ToArray();
            return new Case
            {
                CaseId = c.RootElement.GetProperty("caseId").GetString(),
                IsFictionalDemo = c.RootElement.GetProperty("isFictionalDemo").GetBoolean(),
                Direct = lia.GetProperty("directCauses").EnumerateArray().Select(x => x.GetString()).ToArray(),
                Indirect = lia.GetProperty("indirectCauses").EnumerateArray().Select(x => x.GetString()).ToArray(),
                EcfcIds = nodes.Select(n => n.GetProperty("nodeId").GetString()).ToArray(),
                EcfcEvidence = nodes.ToDictionary(n => n.GetProperty("nodeId").GetString(), n => n.GetProperty("evidenceIds").EnumerateArray().Select(x => x.GetString()).ToArray()),
            };
        }

        /// <summary>ECFC 节点引用 + 这些节点在报告中的页码证据（Strong 结论的证据来源）。</summary>
        private static SystemicRefs R(Case k, params string[] ecfc)
        {
            return new SystemicRefs(ecfc.SelectMany(id => k.EcfcEvidence[id]), ecfc);
        }

        private static AcciMapModel BuildAcciMap(Case k)
        {
            var m = Ok(AcciMapModel.Create("AM-HAILI5", "广州“10·25”海力5 / WAN HAI A17 碰撞 AcciMap"));
            // 船舶管理层：3 条间接原因（原文）
            Ok(m.AddNode("SM-H5-SEA", k.Indirect[0], AcciMapLevel.ShipManagement, S, R(k, "C11", "C12"), "haili5"));
            Ok(m.AddNode("SM-H5-EMG", k.Indirect[1], AcciMapLevel.ShipManagement, S, R(k, "E14", "E15"), "haili5"));
            Ok(m.AddNode("SM-WH-BRM", k.Indirect[2], AcciMapLevel.ShipManagement, S, R(k, "C21", "C23"), "wanhai_a17"));
            // 船员行为层：直接原因 2、3（原文）+ 应急发电机开关未复位
            Ok(m.AddNode("CA-H5-VHF", k.Direct[1], AcciMapLevel.CrewActs, S, R(k, "E16"), "haili5"));
            Ok(m.AddNode("CA-WH-LOOK", k.Direct[2], AcciMapLevel.CrewActs, S, R(k, "E23", "E25", "E26"), "wanhai_a17"));
            Ok(m.AddNode("CA-H5-SW", "轮机长解除岸电后未将应急发电机开关转回自动", AcciMapLevel.CrewActs, S, R(k, "E14"), "haili5"));
            // 设备与环境层：直接原因 1（原文）及物理事件序列
            Ok(m.AddNode("EE-CLOG", "右舷低位海底门滤器堵塞，冷却海水不足", AcciMapLevel.EquipmentEnvironment, S, R(k, "C13", "C14"), "haili5"));
            Ok(m.AddNode("EE-BLACKOUT", k.Direct[0], AcciMapLevel.EquipmentEnvironment, S, R(k, "E01", "C16"), "haili5"));
            Ok(m.AddNode("EE-LIGHTS", "海力5失电后航行灯熄灭", AcciMapLevel.EquipmentEnvironment, S, R(k, "C22"), "haili5"));
            Ok(m.AddNode("EE-DRIFT", "海力5舵机失灵向左偏转进入进口航路", AcciMapLevel.EquipmentEnvironment, S, R(k, "E02", "E03"), "haili5"));
            Ok(m.AddNode("EE-COLL", "两船在马友石灯船东北侧碰撞（19:54:32）", AcciMapLevel.EquipmentEnvironment, S, R(k, "E04")));
            Ok(m.AddNode("EE-SINK", "海力5沉没，15人落水2人死亡", AcciMapLevel.EquipmentEnvironment, S, R(k, "E06"), "haili5"));

            string[,] edges =
            {
                { "SM-H5-SEA", "EE-CLOG" }, { "EE-CLOG", "EE-BLACKOUT" },
                { "SM-H5-EMG", "CA-H5-SW" }, { "CA-H5-SW", "EE-BLACKOUT" }, { "SM-H5-EMG", "EE-BLACKOUT" },
                { "EE-BLACKOUT", "EE-DRIFT" }, { "EE-BLACKOUT", "EE-LIGHTS" },
                { "EE-BLACKOUT", "CA-H5-VHF" },   // 设备→船员（例外）：失控后应通报
                { "EE-LIGHTS", "CA-WH-LOOK" },    // 设备→船员（例外）：灯光熄灭增大发现难度
                { "CA-H5-VHF", "CA-WH-LOOK" },    // 同层：未通报贻误对方避让
                { "SM-WH-BRM", "CA-WH-LOOK" },
                { "EE-DRIFT", "EE-COLL" }, { "CA-H5-VHF", "EE-COLL" }, { "CA-WH-LOOK", "EE-COLL" }, { "EE-COLL", "EE-SINK" },
            };
            for (int i = 0; i < edges.GetLength(0); i++)
            {
                Ok(m.Connect(edges[i, 0], edges[i, 1]));
            }

            return m;
        }

        private static BowTieModel BuildBowTie(Case k)
        {
            var m = Ok(BowTieModel.Create("BT-HAILI5", "广州港主航道进出口航路船舶对遇（夜间）", "TOP", "海力5与WAN HAI A17碰撞（19:54:32）", S, R(k, "E04")));
            // A1：威胁前因链 滤器堵塞 → 冷却不足 → 发电机停车（只有链末连屏障/顶事件）
            Ok(m.AddThreat("T-CLOG", "右舷低位海底门滤器堵塞（推定）", S, R(k, "C13"), "haili5"));
            Ok(m.AddThreat("T-COOL", "冷却海水供应不足", S, R(k, "C14"), "haili5"));
            Ok(m.AddThreat("T-BLACKOUT", k.Direct[0], S, R(k, "E01", "E02"), "haili5"));
            Ok(m.AddThreat("T-WH-LOOK", k.Direct[2], S, R(k, "C21", "E23"), "wanhai_a17"));

            Ok(m.AddBarrier("PB-SEA", "冷却海水系统维护（险情后排查、清洗海底门滤器）", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "C11"), "haili5"));
            Ok(m.AddBarrier("PB-EMG", "应急发电机自动启动供电", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "C16"), "haili5"));
            Ok(m.AddBarrier("PB-VHF", "失控后及时VHF通报附近船舶", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "E16"), "haili5"));
            Ok(m.AddBarrier("PB-LOOK", "WAN HAI A17 瞭望（目视/雷达）", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "C21"), "wanhai_a17"));
            Ok(m.AddBarrier("PB-BRM", "驾驶台资源管理（船长—引航员指挥权）", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "C23"), "wanhai_a17"));
            Ok(m.AddBarrier("PB-AVOID", "及早果断采取避碰行动", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "E26", "C24"), "wanhai_a17"));

            Ok(m.AddEscalationFactor("EF-LOWSEA", "进出港一直使用右舷低位海底门且富裕水深约2米", "PB-SEA", S, R(k, "C12")));
            Ok(m.AddEscalationFactor("EF-SWITCH", "应急发电机启动开关处于手动模式", "PB-EMG", S, R(k, "C16")));
            Ok(m.AddEscalationFactor("EF-LIGHTS", "海力5失电后航行灯熄灭", "PB-LOOK", S, R(k, "C22")));
            Ok(m.AddEscalationFactor("EF-HANDOVER", "驾驶台6人处于交接班", "PB-LOOK", S, R(k, "E22", "C21")));

            Ok(m.AddBarrier("MB-WT", "海力5水密完整性与破损控制", BowTieElementKind.MitigationBarrier, BarrierState.Failed, S, R(k, "E05"), "haili5"));
            // D04：13 人获救、2 人死亡 → 部分有效（Degraded）
            Ok(m.AddBarrier("MB-SAR", "落水人员救助与搜救", BowTieElementKind.MitigationBarrier, BarrierState.Degraded, S, R(k, "E06")));
            Ok(m.AddConsequence("CQ-SINK", "海力5破损进水沉没", S, R(k, "E05", "E06"), "haili5"));
            Ok(m.AddConsequence("CQ-PERSON", "15人落水，13人获救，2人死亡", S, R(k, "E06"), "haili5"));
            Ok(m.AddConsequence("CQ-WH", "WAN HAI A17球鼻艏破损、艏尖舱进水", M, R(k, "E04"), "wanhai_a17"));

            void P(params string[] path) { for (int i = 1; i < path.Length; i++) Ok(m.Connect(path[i - 1], path[i])); }
            P("T-CLOG", "T-COOL", "T-BLACKOUT");
            P("T-BLACKOUT", "PB-SEA", "PB-EMG", "PB-VHF", "TOP");
            P("T-WH-LOOK", "PB-LOOK", "PB-BRM", "PB-AVOID", "TOP");
            P("PB-VHF", "PB-AVOID");                      // 海力5未通报 → 对方避让屏障
            P("TOP", "MB-WT", "CQ-SINK");
            P("TOP", "MB-SAR", "CQ-PERSON");
            P("TOP", "CQ-WH");
            return m;
        }

        [Fact]
        public void CaseFile_IsRealNotDemo_SixCauses()
        {
            var k = Load();
            Assert.False(k.IsFictionalDemo);
            Assert.Equal(3, k.Direct.Length);
            Assert.Equal(3, k.Indirect.Length);
        }

        /// <summary>AcciMap 能表达全部 6 条报告原因，层间方向与无环均满足；引用全部落在 ecfc.json 节点集合内。</summary>
        [Fact]
        public void Haili5_AcciMap_Expressible_AllSixCausesMapped_Valid()
        {
            var k = Load();
            var m = BuildAcciMap(k);
            var v = m.Validate(new SystemicRefContext(knownEcfcNodeIds: k.EcfcIds));
            Assert.True(v.IsValid, Issues(v));
            foreach (var cause in k.Direct.Concat(k.Indirect))
            {
                Assert.Contains(m.Nodes, n => n.Label == cause);
            }

            // 报告认定的原因只到船舶管理层：政府/监管/公司三层为空——这是报告本身的取向，不是模型限制（模型允许空层）。
            Assert.Empty(m.ByLevel(AcciMapLevel.Government));
            Assert.Empty(m.ByLevel(AcciMapLevel.Regulatory));
            Assert.Empty(m.ByLevel(AcciMapLevel.Company));
            Assert.Equal("haili5", m.Get("SM-H5-SEA").ActorId);
            Assert.Equal("wanhai_a17", m.Get("SM-WH-BRM").ActorId);
        }

        /// <summary>Bow-tie 能表达：两条威胁（海力5 失电失控、WAN HAI A17 疏忽瞭望）→ 顶事件 → 沉没/伤亡/他船受损，升级因素挂在屏障上。</summary>
        [Fact]
        public void Haili5_BowTie_Expressible_Valid()
        {
            var k = Load();
            var m = BuildBowTie(k);
            var v = m.Validate(new SystemicRefContext(knownEcfcNodeIds: k.EcfcIds));
            Assert.True(v.IsValid, Issues(v));
            Assert.Equal(7, m.BarrierStats()[BarrierState.Failed]);
            Assert.Equal(1, m.BarrierStats()[BarrierState.Degraded]);
            Assert.Equal(0, m.BarrierStats()[BarrierState.Unknown]);
            Assert.Equal(4, m.OfKind(BowTieElementKind.EscalationFactor).Count);
            Assert.Equal(4, m.OfKind(BowTieElementKind.Threat).Count);
            Assert.Equal("haili5", m.Get("T-CLOG").ActorId);
            Assert.Equal("wanhai_a17", m.Get("T-WH-LOOK").ActorId);
        }

        /// <summary>真实案件文档：IsFictionalDemo=false，caseId 取自 case.json，JSON 往返字节一致。</summary>
        [Fact]
        public void Haili5_Document_RoundTrip()
        {
            var k = Load();
            var doc = new SystemicDocument(k.CaseId, false, BuildBowTie(k), BuildAcciMap(k), null);
            string j = doc.ToJson();
            var back = Ok(SystemicDocument.FromJson(j));
            Assert.False(back.IsFictionalDemo);
            Assert.Equal("GZ-2025-1025-Haili5-WanHaiA17", back.CaseId);
            Assert.Equal(j, back.ToJson());
            Assert.True(back.Validate(new SystemicRefContext(knownEcfcNodeIds: k.EcfcIds)).IsValid);
        }

        /// <summary>
        /// A1：威胁前因链（滤器堵塞 → 冷却不足 → 发电机停车）现以 Threat→Threat 表达，且只有链末连顶事件/屏障。
        /// A2：AcciMap 因果边仍不可由下往上；同方向的信息流边可以。
        /// </summary>
        [Fact]
        public void Haili5_ExpressivenessLimits_DocumentedBehaviour()
        {
            var k = Load();
            var bt = BuildBowTie(k);
            // 链已建好：T-CLOG → T-COOL → T-BLACKOUT → 屏障
            Assert.Contains(bt.Edges, e => e.FromId == "T-CLOG" && e.ToId == "T-COOL");
            Assert.Contains(bt.Edges, e => e.FromId == "T-COOL" && e.ToId == "T-BLACKOUT");
            // 中间威胁不可再连屏障/顶事件
            Assert.Equal(SystemicErrors.InvalidEdge, bt.Connect("T-CLOG", "TOP").ErrorCode);
            Assert.Equal(SystemicErrors.InvalidEdge, bt.Connect("T-COOL", "PB-SEA").ErrorCode);
            // 成环拒绝
            Assert.Equal(SystemicErrors.Cycle, bt.Connect("T-BLACKOUT", "T-CLOG").ErrorCode);

            var am = BuildAcciMap(k);
            Ok(am.AddNode("EE-NEARMISS", "避台途中发生发电机高温停车（9月22日险情）", AcciMapLevel.EquipmentEnvironment, S, R(k, "E11"), "haili5"));
            Assert.Equal(SystemicErrors.LevelDirection, am.Connect("EE-NEARMISS", "SM-H5-SEA").ErrorCode);
            Ok(am.ConnectInformationFlow("EE-NEARMISS", "SM-H5-SEA"));
            var v = am.Validate(new SystemicRefContext(knownEcfcNodeIds: k.EcfcIds));
            Assert.True(v.IsValid, Issues(v));
        }
    }
}
