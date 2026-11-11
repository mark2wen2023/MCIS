using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Models;
using Mcis.Domain.Systemic;
using Xunit;
using static Mcis.Acceptance.W15.Fx;

namespace Mcis.Acceptance.W15
{
    /// <summary>W15.1 复测：覆盖 D01–D04、A1–A11 及已接受的新假设。演示数据虚构。</summary>
    public sealed class RetestW151AcceptanceTests
    {
        private const string GoodSha = "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd";

        // ---------- D01 ----------

        [Fact]
        public void D01_PublicCollections_AreReadOnly_TamperDoesNotStick()
        {
            var bt = MiniBowTie();
            var am = MiniAcciMap();
            for (int i = 0; i < 5; i++) Ok(am.Connect("N" + i, "N" + (i + 1)));
            int edgeCount = bt.Edges.Count;
            int nodeCount = am.Nodes.Count;

            Assert.True(bt.Edges is not IList<SystemicEdge> l || l.IsReadOnly || !TryAdd(l, new SystemicEdge("C1", "T1")));
            Assert.True(bt.Elements is not IList<BowTieElement> els || els.IsReadOnly || !TryRemoveAt(els, 0));
            Assert.True(am.Edges is not IList<SystemicEdge> ae || ae.IsReadOnly || !TryAdd(ae, new SystemicEdge("N5", "N0")));
            var ev = bt.Get("T1").Refs.EvidenceIds as IList<string>;
            if (ev != null && !ev.IsReadOnly)
            {
                try { ev[0] = " "; }
                catch (NotSupportedException) { }
            }

            Assert.Equal(edgeCount, bt.Edges.Count);
            Assert.NotNull(bt.TopEvent);
            Assert.Equal(nodeCount, am.Nodes.Count);
            Assert.Equal("EV-001", bt.Get("T1").Refs.EvidenceIds[0]);
            var load = SystemicDocument.FromJson(new SystemicDocument("CASE-T", true, bt, am).ToJson());
            Assert.True(load.IsSuccess, load.ErrorCode + " " + load.ErrorMessage);
        }

        private static bool TryAdd<T>(IList<T> list, T item)
        {
            try { list.Add(item); return true; }
            catch (NotSupportedException) { return false; }
        }

        private static bool TryRemoveAt<T>(IList<T> list, int i)
        {
            try { list.RemoveAt(i); return true; }
            catch (NotSupportedException) { return false; }
        }

        // ---------- D02 / D03 covered by original KnownDefect tests (tags removed) ----------

        [Fact]
        public void D03_CreateFactory_RejectsInvalidCaseId_SameRuleAsEvidence()
        {
            foreach (var id in new[] { null, "", "  bad id \n", "ab", "有中文" })
            {
                Assert.False(EvidenceItem.IsValidCaseId(id));
                Code(SystemicErrors.InvalidId, SystemicDocument.Create(id, false, MiniBowTie()));
            }
            Assert.True(SystemicDocument.Create("CASE-2026-LM01", true, MiniBowTie()).IsSuccess);
        }

        [Fact]
        public void D04_Degraded_IsFirstClass_AndRoundTrips()
        {
            var m = MiniBowTie();
            Ok(m.SetBarrierState("PB1", BarrierState.Degraded));
            Assert.Equal(BarrierState.Degraded, m.Get("PB1").State);
            Assert.Equal(1, m.BarrierStats()[BarrierState.Degraded]);
            var doc = new SystemicDocument("CASE-DEG", true, m);
            string json = doc.ToJson();
            Assert.Contains("\"Degraded\"", json);
            var back = Ok(SystemicDocument.FromJson(json));
            Assert.Equal(BarrierState.Degraded, back.BowTie.Get("PB1").State);
            Assert.Equal(json, back.ToJson());
        }

        // ---------- A1 ----------

        [Fact]
        public void A1_ThreatChain_Acyclic_OnlyLastConnectsToTop()
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T0", "前因", M, Ev1));
            Ok(m.AddThreat("Tmid", "中间", M, Ev1));
            Ok(m.Connect("T0", "Tmid"));
            Ok(m.Connect("Tmid", "T1")); // T1 已连向 PB1→TOP，Tmid 是新的链末？不对：T1 已连屏障，所以 Tmid→T1 合法（T1 是链末）
            Assert.Equal(SystemicErrors.InvalidEdge, m.Connect("T0", "PB1").ErrorCode);
            Assert.Equal(SystemicErrors.InvalidEdge, m.Connect("Tmid", "TOP").ErrorCode);
            Assert.Equal(SystemicErrors.Cycle, m.Connect("T1", "T0").ErrorCode);
            Assert.Equal(SystemicErrors.Cycle, m.Connect("T0", "T0").ErrorCode);
            var v = m.Validate();
            Assert.True(v.IsValid, Issues(v));
        }

        // ---------- A2 ----------

        [Fact]
        public void A2_InformationFlow_UpwardAllowed_IgnoredInCycleCheck()
        {
            var am = MiniAcciMap();
            Ok(am.Connect("N0", "N1"));
            Ok(am.Connect("N1", "N2"));
            Ok(am.Connect("N2", "N3"));
            Ok(am.Connect("N3", "N4"));
            Ok(am.Connect("N4", "N5"));
            // 因果上行仍拒
            Code(SystemicErrors.LevelDirection, am.Connect("N5", "N0"));
            // 信息流可由下往上，且不参与成环
            Ok(am.ConnectInformationFlow("N5", "N0"));
            Ok(am.ConnectInformationFlow("N5", "N2"));
            var v = am.Validate();
            Assert.True(v.IsValid, Issues(v));
            Assert.False(v.Has(SystemicErrors.Cycle));
            Assert.Equal(2, am.InformationFlows.Count);
            Assert.All(am.InformationFlows, e => Assert.Equal(SystemicEdgeKind.InformationFlow, e.Kind));
            // 信息流不在因果边集合里
            Assert.DoesNotContain(am.Edges, e => e.Kind == SystemicEdgeKind.InformationFlow);
        }

        // ---------- A4 ----------

        [Fact]
        public void A4_ActorId_Optional_Validated_RoundTrips()
        {
            var m = MiniBowTie();
            Ok(m.UpdateElement("T1", actorId: "MARY"));
            Assert.Equal("MARY", m.Get("T1").ActorId);
            Code(SystemicErrors.InvalidId, m.UpdateElement("T1", actorId: "坏 id"));
            Ok(m.UpdateElement("T1", clearActor: true));
            Assert.Null(m.Get("T1").ActorId);
            Ok(m.UpdateElement("T1", actorId: "LILY"));
            var json = new SystemicDocument("CASE-ACT", true, m).ToJson();
            Assert.Contains("\"actorId\":\"LILY\"", json);
            Assert.Equal("LILY", Ok(SystemicDocument.FromJson(json)).BowTie.Get("T1").ActorId);
        }

        // ---------- A5 ----------

        [Fact]
        public void A5_TypedRefs_UnregisteredKindWarns_RegisteredValidates()
        {
            var am = Ok(AcciMapModel.Create("AM-R", "t"));
            var refs = new SystemicRefs(new[]
            {
                new SystemicRef(SystemicRefKinds.Evidence, "EV-001"),
                new SystemicRef(SystemicRefKinds.Statement, "IR-06"),
                new SystemicRef(SystemicRefKinds.ColregCheck, "R6"),
                new SystemicRef(SystemicRefKinds.DamageTrack, "DT-1"),
                new SystemicRef("CustomKind", "CK-1")
            });
            Ok(am.AddNode("A", "a", AcciMapLevel.Company, M, refs));
            Ok(am.AddNode("B", "b", AcciMapLevel.Company, V));
            Ok(am.Connect("A", "B"));

            var bare = am.Validate(new SystemicRefContext());
            Assert.True(bare.IsValid);
            Assert.True(bare.Has(SystemicErrors.UnregisteredRefKind));

            var ctx = new SystemicRefContext();
            Ok(ctx.RegisterValidator(SystemicRefKinds.Statement, id => id == "IR-06"));
            Ok(ctx.RegisterValidator(SystemicRefKinds.ColregCheck, id => id == "R6"));
            Ok(ctx.RegisterValidator(SystemicRefKinds.DamageTrack, id => id == "DT-1"));
            // CustomKind 仍未注册 → 警告；已注册的不报 unknown
            var v = am.Validate(ctx);
            Assert.True(v.IsValid, Issues(v));
            Assert.True(v.Has(SystemicErrors.UnregisteredRefKind));
            Assert.False(v.Has(SystemicErrors.UnknownRef));
            Ok(ctx.RegisterValidator("CustomKind", id => id == "CK-1"));
            Assert.False(am.Validate(ctx).Has(SystemicErrors.UnregisteredRefKind));
        }

        // ---------- A6 / A10 + new assumption: Mismatch also rejected for Strong ----------

        [Fact]
        public void A6_StrongAndModerate_NeedEvidence_UnreliableEvidence()
        {
            var ledger = Ledger(new[] { "EV-001", "EV-002" });
            Ok(ledger.Verify("EV-001", "甲", T0.AddMinutes(1), new string('0', 64)));
            Assert.Equal(EvidenceStatus.Mismatch, ledger.StatusOf("EV-001"));
            Ok(ledger.MarkNeedsReview("EV-002", "甲", T0.AddMinutes(2), "待核"));

            Code(SystemicErrors.ModerateWithoutEvidence, MiniBowTie().AddThreat("TX", "x", M));
            var am = Ok(AcciMapModel.Create("AM", "t"));
            Code(SystemicErrors.StrongWithoutEvidence, am.AddNode("S0", "s", AcciMapLevel.Company, S));

            Ok(am.AddNode("A", "a", AcciMapLevel.Company, S, Ev("EV-001")));
            Ok(am.AddNode("B", "b", AcciMapLevel.Company, M, Ev("EV-002")));
            Ok(am.Connect("A", "B"));
            var ctx = new SystemicRefContext(ledger: ledger);
            var v = am.Validate(ctx);
            Assert.True(v.Has(SystemicErrors.EvidenceUnreliable)); // Strong + Mismatch
            Assert.True(v.Has(SystemicErrors.EvidenceNeedsReview)); // Moderate + NeedsReview 警告
            Assert.False(v.IsValid);
        }

        // ---------- A7 ----------

        [Fact]
        public void A7_IsolatedController_IsWarningNotError()
        {
            var m = MiniStamp();
            Ok(m.AddController("ISO", "孤立控制器", M, Ev1));
            var v = m.Validate();
            Assert.True(v.IsValid, Issues(v));
            Assert.True(v.Has(SystemicErrors.IsolatedController));
            Assert.Equal("ISO", v.Of(SystemicErrors.IsolatedController).Single().ElementId);
        }

        // ---------- A8 + assumption: check action before context ----------

        [Fact]
        public void A8_EmptyContextFails_ActionCheckedBeforeContext()
        {
            var m = MiniStamp();
            Code(SystemicErrors.InvalidArgument, m.AddUnsafeControlAction("U1", "x", "CA", UcaType.NotProvided, null, M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddUnsafeControlAction("U1", "x", "CA", UcaType.NotProvided, "\t", M, Ev1));
            // 控制动作不存在时，即使情境也为空，仍报 unknown_node（先查动作）
            Code(SystemicErrors.UnknownNode, m.AddUnsafeControlAction("U1", "x", "NOPE", UcaType.NotProvided, null, M, Ev1));
            Ok(m.AddUnsafeControlAction("U1", "x", "CA", UcaType.NotProvided, "雾中未转向", M, Ev1));
        }

        // ---------- A9 ----------

        [Fact]
        public void A9_MutationsAndEcfcImport()
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T2", "第二威胁", M, Ev1));
            Ok(m.Connect("T2", "TOP"));
            Ok(m.Disconnect("T2", "TOP"));
            Assert.DoesNotContain(m.Edges, e => e.FromId == "T2" && e.ToId == "TOP");
            var removed = Ok(m.RemoveElement("T2"));
            Assert.Contains("T2", removed);
            Assert.Null(m.Get("T2"));
            Code(SystemicErrors.InvalidArgument, m.RemoveElement("TOP"));
            Ok(m.UpdateElement("C1", label: "进水扩大"));
            Assert.Equal("进水扩大", m.Get("C1").Label);

            var nodes = new[]
            {
                new EcfcNode("E1", EcfcNodeKind.Event, "虚构事件", evidenceIds: new[] { "EV-001" }, actorVesselId: "MARY"),
                new EcfcNode("C1", EcfcNodeKind.Condition, "虚构条件", evidenceIds: new[] { "EV-002" })
            };
            var edges = new[] { new EcfcEdge("e1", "E1", "C1", Mcis.Domain.Common.EcfcEdgeKind.Influence, false) };
            var imported = SystemicEcfcImport.Convert(nodes, edges, "IMP-");
            Assert.Equal(2, imported.Nodes.Count);
            Assert.Equal("IMP-E1", imported.Nodes[0].Id);
            Assert.Equal("E1", imported.Nodes[0].SourceEcfcNodeId);
            Assert.Equal("MARY", imported.Nodes[0].ActorId);
            Assert.Contains(imported.Nodes[0].Refs.EcfcNodeIds, id => id == "E1");
            Assert.Contains(imported.Edges, e => e.FromId == "IMP-E1" && e.ToId == "IMP-C1");
        }

        // ---------- A11 ----------

        [Fact]
        public void A11_TwoPassLoad_DoesNotDependOnElementOrder()
        {
            var m = MiniBowTie();
            Ok(m.AddEscalationFactor("EF1", "疲劳", "PB1", M, Ev1));
            string json = new SystemicDocument("CASE-ORD", true, m).ToJson();
            // 把升级因素挪到其屏障之前
            int ef = json.IndexOf("{\"id\":\"EF1\"", StringComparison.Ordinal);
            int pb = json.IndexOf("{\"id\":\"PB1\"", StringComparison.Ordinal);
            Assert.True(ef > 0 && pb > 0 && ef > pb, "ToJson 应先写屏障再写升级因素，作为对照：" + json);
            // 截取 elements 数组，交换 EF1 与 PB1 对象
            string swapped = SwapJsonObjects(json, "PB1", "EF1");
            Assert.True(swapped.IndexOf("{\"id\":\"EF1\"", StringComparison.Ordinal) <
                        swapped.IndexOf("{\"id\":\"PB1\"", StringComparison.Ordinal), swapped);
            var back = Ok(SystemicDocument.FromJson(swapped));
            Assert.Equal("PB1", back.BowTie.Get("EF1").BarrierId);
            Assert.True(back.BowTie.Validate().IsValid, Issues(back.BowTie.Validate()));
        }

        private static string SwapJsonObjects(string json, string firstId, string secondId)
        {
            // 在 "elements":[ ... ] 内按 id 交换两个完整对象（对象本身不含嵌套 {} 数组以外的复杂结构，refs 含 {}）。
            string key1 = "{\"id\":\"" + firstId + "\"";
            string key2 = "{\"id\":\"" + secondId + "\"";
            int a = json.IndexOf(key1, StringComparison.Ordinal);
            int b = json.IndexOf(key2, StringComparison.Ordinal);
            string objA = SliceObject(json, a);
            string objB = SliceObject(json, b);
            if (a < b)
                return json.Substring(0, a) + objB + json.Substring(a + objA.Length, b - (a + objA.Length)) + objA + json.Substring(b + objB.Length);
            return json.Substring(0, b) + objA + json.Substring(b + objB.Length, a - (b + objB.Length)) + objB + json.Substring(a + objA.Length);
        }

        private static string SliceObject(string json, int start)
        {
            int depth = 0;
            bool inStr = false;
            for (int i = start; i < json.Length; i++)
            {
                char c = json[i];
                if (c == '"' && (i == 0 || json[i - 1] != '\\')) inStr = !inStr;
                if (inStr) continue;
                if (c == '{') depth++;
                else if (c == '}')
                {
                    depth--;
                    if (depth == 0) return json.Substring(start, i - start + 1);
                }
            }
            throw new InvalidOperationException("unbalanced object at " + start);
        }

        // ---------- new assumptions ----------

        [Fact]
        public void TopEvent_DefaultStrength_IsToBeVerified()
        {
            var m = Ok(BowTieModel.Create("BT-D", "危险", "TOP", "顶事件"));
            Assert.Equal(EvidenceStrength.ToBeVerified, m.TopEvent.Strength);
        }

        [Fact]
        public void W15_D05_BuiltInRefs_WithoutSource_MustLeaveATrace()
        {
            var am = Ok(AcciMapModel.Create("AM-1", "t"));
            Ok(am.AddNode("A", "a", AcciMapLevel.Company, M, new SystemicRefs(new[] { "EV-404" }, new[] { "X" }, new[] { "HF-X" }, new[] { "SR-2026-99" })));
            Ok(am.AddNode("B", "b", AcciMapLevel.Company, V));
            Ok(am.Connect("A", "B"));
            var v = am.Validate(new SystemicRefContext()); // 四类来源均未传
            Assert.True(v.IsValid, Issues(v));
            bool hasCount = typeof(SystemicValidation).GetProperty("NotCheckedRefCount", BindingFlags.Public | BindingFlags.Instance) != null
                         || typeof(SystemicValidation).GetProperty("UncheckedRefCount", BindingFlags.Public | BindingFlags.Instance) != null
                         || v.Issues.Any(i => i.Code.IndexOf("not_checked", StringComparison.OrdinalIgnoreCase) >= 0
                                           || i.Code.IndexOf("notchecked", StringComparison.OrdinalIgnoreCase) >= 0
                                           || (i.Message != null && i.Message.Contains("未核")));
            // 用反射读数值（若有）
            var prop = typeof(SystemicValidation).GetProperty("NotCheckedRefCount") ?? typeof(SystemicValidation).GetProperty("UncheckedRefCount");
            int? count = prop == null ? (int?)null : Convert.ToInt32(prop.GetValue(v));
            Assert.True(hasCount && (count == null || count > 0),
                "内置四类引用未传来源时校验无痕迹（缺 notCheckedRefCount 或同义字段/问题项）。issues=" + Issues(v) + " count=" + count);
        }

        [Fact]
        public void LegacyJson_WithoutNewFields_RoundTripByteIdentical()
        {
            const string legacy = "{\"schema\":\"mcis.systemic/1\",\"caseId\":\"CASE-1\",\"isFictionalDemo\":true,\"bowTie\":null," +
                "\"acciMap\":{\"id\":\"AM-1\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[" +
                "{\"id\":\"A\",\"label\":\"a\",\"strength\":\"Moderate\",\"refs\":{\"evidence\":[\"EV-001\"],\"ecfc\":[\"E1\"],\"hfacs\":[],\"recommendations\":[]},\"level\":\"Company\"}," +
                "{\"id\":\"B\",\"label\":\"b\",\"strength\":\"ToBeVerified\",\"refs\":{\"evidence\":[],\"ecfc\":[],\"hfacs\":[],\"recommendations\":[]},\"level\":\"CrewActs\"}]," +
                "\"edges\":[[\"A\",\"B\"]]},\"stamp\":null}";
            var d = Ok(SystemicDocument.FromJson(legacy));
            Assert.Equal(legacy, d.ToJson());
            Assert.Null(d.AcciMap.Get("A").ActorId);
            Assert.Empty(d.AcciMap.InformationFlows);
        }
    }
}
