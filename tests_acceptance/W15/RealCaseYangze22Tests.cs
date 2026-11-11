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
    /// YANGZE 22 / VEGA DREAM 真实案例（公开调查报告，Mark 已确认可直接使用）。
    /// 用 case.json 原因与 ecfc.json 节点搭 AcciMap 与 Bow-tie：威胁含“舵令反向执行”“三副未监舵”，节点和边引用 ecfc 节点。
    /// </summary>
    public sealed class RealCaseYangze22Tests
    {
        private sealed class Pack
        {
            public string CaseId;
            public string[] EcfcIds;
            public Dictionary<string, string[]> Ev;
            public JsonElement Root;
            public JsonElement Ecfc;
        }

        private static Pack Load()
        {
            string dir = Path.Combine(RepoRoot(), "reports", "yangze22");
            using var c = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "case.json")));
            using var e = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "ecfc.json")));
            var nodes = e.RootElement.GetProperty("nodes").EnumerateArray().ToArray();
            return new Pack
            {
                CaseId = c.RootElement.GetProperty("caseId").GetString(),
                EcfcIds = nodes.Select(n => n.GetProperty("nodeId").GetString()).ToArray(),
                Ev = nodes.ToDictionary(n => n.GetProperty("nodeId").GetString(), n => n.GetProperty("evidenceIds").EnumerateArray().Select(x => x.GetString()).ToArray()),
                Root = c.RootElement.Clone(),
                Ecfc = e.RootElement.Clone()
            };
        }

        private static SystemicRefs R(Pack k, params string[] ecfc) =>
            new SystemicRefs(ecfc.SelectMany(id => k.Ev[id]), ecfc);

        private static string Cause(Pack k, string id) =>
            k.Root.GetProperty("directCauses").EnumerateArray().First(x => x.GetProperty("id").GetString() == id).GetProperty("text").GetString();

        private static string Indirect(Pack k, string id) =>
            k.Root.GetProperty("indirectCauses").EnumerateArray().First(x => x.GetProperty("id").GetString() == id).GetProperty("text").GetString();

        private static AcciMapModel BuildAcciMap(Pack k)
        {
            var m = Ok(AcciMapModel.Create("AM-Y22", "长江口“12·30”YANGZE 22 / VEGA DREAM 碰撞 AcciMap"));
            // 政府 / 监管 / 公司
            Ok(m.AddNode("GV-STCW", "《船员条例》、STCW、COLREG、《引航管理规定》", AcciMapLevel.Government, S, R(k, "C13"), "regulator"));
            Ok(m.AddNode("RG-VTS", "吴淞 VTS 交通管制时段与应急指挥", AcciMapLevel.Regulatory, S, R(k, "C31")));
            Ok(m.AddNode("CO-TRAIN", "上海润元未做越控培训、操作手册测试项不全", AcciMapLevel.Company, S, R(k, "C17"), "yangze22"));
            Ok(m.AddNode("CO-PILOT", "上海港引航站通信方式（直呼姓名）", AcciMapLevel.Company, S, R(k, "C22")));
            // 船舶管理
            Ok(m.AddNode("SM-MASTER", Indirect(k, "IC1"), AcciMapLevel.ShipManagement, S, R(k, "E12"), "yangze22"));
            Ok(m.AddNode("SM-ARRANGE", "安排无驾驶台值班经验的白班水手在深水航道操舵，上午操反舵后未培训接替者", AcciMapLevel.ShipManagement, S, R(k, "E15", "C14", "C15"), "yangze22"));
            // 船员行为
            Ok(m.AddNode("CA-HELM", Cause(k, "DC1"), AcciMapLevel.CrewActs, S, R(k, "E01", "E02", "E03", "E05"), "yangze22"));
            Ok(m.AddNode("CA-WATCH", Cause(k, "DC2"), AcciMapLevel.CrewActs, S, R(k, "C11"), "yangze22"));
            Ok(m.AddNode("CA-EMERG", Cause(k, "DC3"), AcciMapLevel.CrewActs, S, R(k, "C12", "C13"), "yangze22"));
            Ok(m.AddNode("CA-ANCHOR", Cause(k, "DC4"), AcciMapLevel.CrewActs, S, R(k, "C23"), "vega_dream"));
            Ok(m.AddNode("CA-VHF", Indirect(k, "IC2"), AcciMapLevel.CrewActs, S, R(k, "E21", "C21")));
            // 设备与环境
            Ok(m.AddNode("EE-DIAL", "手轮刻度盘随手轮转动，指针所指刻度与操舵方向相反", AcciMapLevel.EquipmentEnvironment, S, R(k, "C16"), "yangze22"));
            Ok(m.AddNode("EE-CHAN", Indirect(k, "IC3"), AcciMapLevel.EquipmentEnvironment, S, R(k, "C32")));
            Ok(m.AddNode("EE-COLL", "VEGA DREAM 船首与 YANGZE 22 右舷 5 舱碰撞", AcciMapLevel.EquipmentEnvironment, S, R(k, "E06")));

            void E(string a, string b) => Ok(m.Connect(a, b));
            E("GV-STCW", "CO-TRAIN"); E("GV-STCW", "CO-PILOT"); E("RG-VTS", "EE-CHAN");
            E("CO-TRAIN", "SM-ARRANGE"); E("CO-PILOT", "CA-VHF");
            E("SM-MASTER", "CA-WATCH"); E("SM-ARRANGE", "CA-HELM");
            E("CA-WATCH", "CA-HELM"); E("CA-HELM", "EE-COLL"); E("CA-EMERG", "EE-COLL"); E("CA-ANCHOR", "EE-COLL"); E("CA-VHF", "EE-COLL");
            E("EE-DIAL", "CA-HELM"); E("EE-CHAN", "EE-COLL"); // 设备→船员例外
            return m;
        }

        private static BowTieModel BuildBowTie(Pack k)
        {
            var m = Ok(BowTieModel.Create("BT-Y22", "长江口深水航道分道对驶", "TOP", "YANGZE 22 失去航向控制并越线进入对向航道", S, R(k, "E04")));
            Ok(m.AddThreat("T-REVERSE", "操舵水手反向执行舵令", S, R(k, "E01", "E02", "E03"), "yangze22"));
            Ok(m.AddThreat("T-NOWATCH", "值班三副未监舵、未纠正", S, R(k, "C11"), "yangze22"));
            Ok(m.AddThreat("T-MISJUDGE", "驾驶台误判为舵效差", S, R(k, "C12", "E13"), "yangze22"));

            Ok(m.AddBarrier("PB-LOOP", "指令复述与核对执行", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "E03"), "yangze22"));
            Ok(m.AddBarrier("PB-WATCH", "值班驾驶员监舵", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "C11"), "yangze22"));
            Ok(m.AddBarrier("PB-MASTER", "船长在驾驶台", BowTieElementKind.PreventionBarrier, BarrierState.Missing, S, R(k, "E12"), "yangze22"));
            Ok(m.AddBarrier("PB-NFU", "NFU 或越控操舵", BowTieElementKind.PreventionBarrier, BarrierState.Missing, S, R(k, "C13"), "yangze22"));
            Ok(m.AddBarrier("PB-STOP", "停车或倒车（COLREG 8(e)）", BowTieElementKind.PreventionBarrier, BarrierState.Missing, S, R(k, "C13"), "yangze22"));
            Ok(m.AddBarrier("PB-VHF", "船间 VHF 协调", BowTieElementKind.PreventionBarrier, BarrierState.Failed, S, R(k, "C21")));

            Ok(m.AddBarrier("MB-AVOID", "他船避让（右满舵、后退三）", BowTieElementKind.MitigationBarrier, BarrierState.Degraded, S, R(k, "E22"), "vega_dream"));
            Ok(m.AddBarrier("MB-ANCHOR", "他船应急抛锚", BowTieElementKind.MitigationBarrier, BarrierState.Missing, S, R(k, "C23"), "vega_dream"));
            Ok(m.AddConsequence("CQ-COLL", "碰撞，货舱和燃油舱破损", S, R(k, "E06", "E07")));
            Ok(m.AddConsequence("CQ-OIL", "约 171 t 燃油泄漏、岸滩污染", S, R(k, "E08")));
            Ok(m.AddBarrier("MB-OIL", "驳油、围油栏、清污", BowTieElementKind.MitigationBarrier, BarrierState.Effective, S, R(k, "E08")));

            void P(params string[] path) { for (int i = 1; i < path.Length; i++) Ok(m.Connect(path[i - 1], path[i])); }
            P("T-REVERSE", "PB-LOOP", "PB-WATCH", "PB-MASTER", "TOP");
            P("T-NOWATCH", "PB-WATCH");
            P("T-MISJUDGE", "PB-NFU", "PB-STOP", "TOP");
            P("PB-VHF", "TOP");
            // PB-VHF 需要来源：将 T-MISJUDGE 也连过去会违反“链末才连屏障”？ T-MISJUDGE 已连 PB-NFU，不能再连 PB-VHF。单独把 VHF 接到 T-NOWATCH？
            // T-NOWATCH 已连 PB-WATCH（屏障），不能再连 PB-VHF。用一条独立威胁不合适。让 TOP 的预防侧 VHF 接在主链上：
            Ok(m.Connect("PB-MASTER", "PB-VHF")); // wait, already P VHF to TOP but VHF has no incoming. Fix below if validate fails.
            P("TOP", "MB-AVOID", "MB-ANCHOR", "CQ-COLL");
            P("TOP", "MB-OIL", "CQ-OIL");
            return m;
        }

        [Fact]
        public void Yangze22_AcciMapAndBowTie_Valid_RefsEcfc_RoundTrip()
        {
            var k = Load();
            Assert.Equal("CJK-2024-1230-YangZe22-VegaDream", k.CaseId);
            var am = BuildAcciMap(k);
            var bt = BuildBowTie(k);
            var ctx = new SystemicRefContext(knownEcfcNodeIds: k.EcfcIds);
            var av = am.Validate(ctx);
            var bv = bt.Validate(ctx);
            Assert.True(av.IsValid, Issues(av));
            Assert.True(bv.IsValid, "bowtie: " + Issues(bv));

            Assert.Contains(am.Nodes, n => n.Label.Contains("反向") || n.Id == "CA-HELM");
            Assert.Equal(Cause(k, "DC1"), am.Get("CA-HELM").Label);
            Assert.Equal(Cause(k, "DC2"), am.Get("CA-WATCH").Label);
            Assert.Equal("yangze22", am.Get("CA-HELM").ActorId);
            Assert.Equal("vega_dream", am.Get("CA-ANCHOR").ActorId);

            Assert.NotNull(bt.Get("T-REVERSE"));
            Assert.NotNull(bt.Get("T-NOWATCH"));
            Assert.Equal(BarrierState.Degraded, bt.Get("MB-AVOID").State);
            // 每个节点（除纯结构）都应引用至少一个 ecfc 节点
            Assert.All(bt.Elements, e => Assert.True(e.Refs.EcfcNodeIds.Count > 0, e.Id));
            Assert.All(am.Nodes, n => Assert.True(n.Refs.EcfcNodeIds.Count > 0, n.Id));
            Assert.All(bt.Elements.SelectMany(e => e.Refs.EcfcNodeIds).Concat(am.Nodes.SelectMany(n => n.Refs.EcfcNodeIds)),
                id => Assert.Contains(id, k.EcfcIds));

            var doc = new SystemicDocument(k.CaseId, false, bt, am);
            Assert.False(doc.IsFictionalDemo);
            string json = doc.ToJson();
            var back = Ok(SystemicDocument.FromJson(json));
            Assert.Equal(json, back.ToJson());
            Assert.True(back.Validate(ctx).IsValid, Issues(back.Validate(ctx)));
        }
    }
}
