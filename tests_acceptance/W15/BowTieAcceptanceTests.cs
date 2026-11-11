using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Systemic;
using Xunit;
using static Mcis.Acceptance.W15.Fx;

namespace Mcis.Acceptance.W15
{
    /// <summary>Bow-tie 验收。依据：CCPS/EI《Bow Ties in Risk Management》(2018) 要素定义——顶事件、威胁、后果、预防屏障（左）、减缓屏障（右）、升级因素（削弱屏障）；
    /// 规格：每条威胁必须有路径到顶事件、每个后果必须由顶事件到达；已接受假设：仅 8 种合法边、升级因素挂屏障不参与路径。</summary>
    public class BowTieAcceptanceTests
    {
        private static readonly BowTieElementKind[] Kinds = (BowTieElementKind[])Enum.GetValues(typeof(BowTieElementKind));

        [Fact]
        public void Minimal_IsValid_AndKindsCounted()
        {
            var m = MiniBowTie();
            var v = m.Validate();
            Assert.True(v.IsValid, Issues(v));
            Assert.Single(m.OfKind(BowTieElementKind.TopEvent));
            Assert.Equal(BowTieElementKind.TopEvent, m.TopEvent.Kind);
            Assert.Equal(4, m.Edges.Count);
        }

        /// <summary>A1 后合法组合为原 8 种加上 Threat→Threat（前因链）。非法组合仍拒绝。</summary>
        [Fact]
        public void EdgeMatrix_ExactlyEightAllowed()
        {
            var expected = new HashSet<(BowTieElementKind, BowTieElementKind)>
            {
                (BowTieElementKind.Threat, BowTieElementKind.Threat),
                (BowTieElementKind.Threat, BowTieElementKind.PreventionBarrier),
                (BowTieElementKind.Threat, BowTieElementKind.TopEvent),
                (BowTieElementKind.PreventionBarrier, BowTieElementKind.PreventionBarrier),
                (BowTieElementKind.PreventionBarrier, BowTieElementKind.TopEvent),
                (BowTieElementKind.TopEvent, BowTieElementKind.MitigationBarrier),
                (BowTieElementKind.TopEvent, BowTieElementKind.Consequence),
                (BowTieElementKind.MitigationBarrier, BowTieElementKind.MitigationBarrier),
                (BowTieElementKind.MitigationBarrier, BowTieElementKind.Consequence),
            };
            int n = 0;
            foreach (var a in Kinds)
            foreach (var b in Kinds)
            {
                bool ok = BowTieModel.IsAllowed(a, b);
                Assert.True(ok == expected.Contains((a, b)), a + "→" + b);
                if (ok) n++;
            }

            Assert.Equal(9, n);
        }

        /// <summary>非法组合经 Connect 也被拒绝（sys_invalid_edge），且不留下边。</summary>
        [Theory]
        [InlineData("T1", "C1")]      // 威胁直达后果，绕过顶事件
        [InlineData("T1", "MB1")]     // 威胁 → 减缓屏障
        [InlineData("PB1", "MB1")]    // 跨越蝴蝶结中心
        [InlineData("PB1", "C1")]
        [InlineData("TOP", "PB1")]    // 反向
        [InlineData("C1", "TOP")]
        [InlineData("MB1", "TOP")]
        [InlineData("EF1", "C1")]     // 升级因素不参与路径（A1 后威胁→威胁已合法，改测升级因素→后果）
        [InlineData("C1", "C1b")]
        [InlineData("EF1", "TOP")]    // 升级因素不参与路径
        [InlineData("T1", "EF1")]
        [InlineData("PB1", "EF1")]
        public void IllegalEdge_Rejected(string from, string to)
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T1b", "第二威胁", M, Ev1));
            Ok(m.AddConsequence("C1b", "第二后果", M, Ev1));
            Ok(m.AddEscalationFactor("EF1", "疲劳", "PB1", M, Ev1));
            int before = m.Edges.Count;
            Code(SystemicErrors.InvalidEdge, m.Connect(from, to));
            Assert.Equal(before, m.Edges.Count);
        }

        [Fact]
        public void ThreatWithoutAnyEdge_IsOrphanThreat()
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T2", "横流", M, Ev1));
            var v = m.Validate();
            Assert.Equal(new[] { "T2" }, v.Of(SystemicErrors.OrphanThreat).Select(i => i.ElementId));
            Assert.Equal(SystemicErrors.OrphanThreat, v.ToResult().ErrorCode);
        }

        /// <summary>威胁只连到一条走不到顶事件的屏障链 → 威胁与屏障都报孤立。</summary>
        [Fact]
        public void ThreatIntoDeadEndBarrierChain_OrphanThreatAndBarriers()
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T2", "横流", M, Ev1));
            Ok(m.AddBarrier("PB2", "航路余量", BowTieElementKind.PreventionBarrier, BarrierState.Unknown, V));
            Ok(m.AddBarrier("PB3", "VTS", BowTieElementKind.PreventionBarrier, BarrierState.Failed, V));
            Ok(m.Connect("T2", "PB2"));
            Ok(m.Connect("PB2", "PB3"));
            var v = m.Validate();
            Assert.Contains(v.Of(SystemicErrors.OrphanThreat), i => i.ElementId == "T2");
            Assert.Equal(new[] { "PB2", "PB3" }, v.Of(SystemicErrors.OrphanBarrier).Select(i => i.ElementId).OrderBy(x => x));
        }

        /// <summary>多条威胁共享屏障链：只要有一条路径到顶事件即合规。</summary>
        [Fact]
        public void SharedBarrierChain_BothThreatsValid()
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T2", "横流", M, Ev1));
            Ok(m.Connect("T2", "PB1"));
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void ConsequenceNotReachableFromTop_IsOrphan_AndDanglingMitigation()
        {
            var m = MiniBowTie();
            Ok(m.AddConsequence("C2", "溢油", V));
            Ok(m.AddBarrier("MB2", "溢油应急", BowTieElementKind.MitigationBarrier, BarrierState.Unknown, V));
            Ok(m.Connect("MB2", "C2")); // MB2 未从顶事件出发
            var v = m.Validate();
            Assert.Equal(new[] { "C2" }, v.Of(SystemicErrors.OrphanConsequence).Select(i => i.ElementId));
            Assert.Equal(new[] { "MB2" }, v.Of(SystemicErrors.OrphanBarrier).Select(i => i.ElementId));
        }

        /// <summary>减缓屏障从顶事件出发但走不到任何后果 → 孤立屏障。</summary>
        [Fact]
        public void MitigationFromTopButNoConsequence_IsOrphanBarrier()
        {
            var m = MiniBowTie();
            Ok(m.AddBarrier("MB2", "搜救", BowTieElementKind.MitigationBarrier, BarrierState.Effective, M, Ev1));
            Ok(m.Connect("TOP", "MB2"));
            var v = m.Validate();
            Assert.Equal(new[] { "MB2" }, v.Of(SystemicErrors.OrphanBarrier).Select(i => i.ElementId));
            Assert.False(v.Has(SystemicErrors.OrphanConsequence));
        }

        [Fact]
        public void EmptyModel_NoThreat_OrNoConsequence()
        {
            var m = Ok(BowTieModel.Create("BT-E", "危险源", "TOP", "顶事件"));
            Assert.True(m.Validate().Has(SystemicErrors.EmptyModel));
            Ok(m.AddThreat("T1", "威胁", M, Ev1));
            Ok(m.Connect("T1", "TOP"));
            Assert.True(m.Validate().Has(SystemicErrors.EmptyModel));
            Ok(m.AddConsequence("C1", "后果", M, Ev1));
            Ok(m.Connect("TOP", "C1"));
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void BarrierChainCycle_AndSelfLoop_Rejected()
        {
            var m = MiniBowTie();
            Ok(m.AddBarrier("PB2", "VTS", BowTieElementKind.PreventionBarrier, BarrierState.Failed, M, Ev1));
            Ok(m.Connect("PB1", "PB2"));
            Code(SystemicErrors.Cycle, m.Connect("PB2", "PB1"));
            Code(SystemicErrors.Cycle, m.Connect("PB2", "PB2"));
            Ok(m.AddBarrier("MB2", "堵漏", BowTieElementKind.MitigationBarrier, BarrierState.Failed, M, Ev1));
            Ok(m.Connect("MB1", "MB2"));
            Code(SystemicErrors.Cycle, m.Connect("MB2", "MB1"));
        }

        [Fact]
        public void EdgeAndNodeErrors()
        {
            var m = MiniBowTie();
            Code(SystemicErrors.DuplicateEdge, m.Connect("T1", "PB1"));
            Code(SystemicErrors.UnknownNode, m.Connect("T1", "NOPE"));
            Code(SystemicErrors.UnknownNode, m.Connect(null, null));
            Code(SystemicErrors.DuplicateId, m.AddThreat("PB1", "重复", M, Ev1));
            Code(SystemicErrors.DuplicateId, m.AddConsequence("TOP", "与顶事件同 ID", M, Ev1));
            Code(SystemicErrors.InvalidId, m.AddThreat(null, "x", M, Ev1));
            Code(SystemicErrors.InvalidId, m.AddThreat("-bad", "x", M, Ev1));
            Code(SystemicErrors.InvalidId, m.AddThreat("a b", "x", M, Ev1));
            Code(SystemicErrors.InvalidId, m.AddThreat("威胁1", "x", M, Ev1));
            Code(SystemicErrors.InvalidId, m.AddThreat("T\n", "x", M, Ev1));
            Code(SystemicErrors.InvalidId, m.AddThreat(new string('a', 65), "x", M, Ev1));
            Ok(m.AddThreat(new string('a', 64), "64 字符边界", M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddThreat("T9", "  ", M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddThreat("T9", "x", (EvidenceStrength)42));
        }

        [Fact]
        public void BarrierAndEscalationErrors()
        {
            var m = MiniBowTie();
            Code(SystemicErrors.InvalidArgument, m.AddBarrier("B9", "x", BowTieElementKind.Threat, BarrierState.Failed, M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddBarrier("B9", "x", BowTieElementKind.TopEvent, BarrierState.Failed, M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddBarrier("B9", "x", BowTieElementKind.PreventionBarrier, (BarrierState)9, M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddEscalationFactor("EF1", "x", "NOPE", M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddEscalationFactor("EF1", "x", null, M, Ev1));
            Code(SystemicErrors.InvalidEdge, m.AddEscalationFactor("EF1", "x", "T1", M, Ev1));
            Code(SystemicErrors.InvalidEdge, m.AddEscalationFactor("EF1", "x", "TOP", M, Ev1));
            var ef = Ok(m.AddEscalationFactor("EF1", "船长未被召唤", "MB1", M, Ev1));
            Assert.Equal("MB1", ef.BarrierId);
            Code(SystemicErrors.InvalidEdge, m.AddEscalationFactor("EF2", "升级因素挂升级因素", "EF1", M, Ev1));
            Assert.True(m.Validate().IsValid); // 升级因素不参与路径、不导致孤立
        }

        [Fact]
        public void BarrierStats_AllStatesKeyed()
        {
            var demo = SystemicDemoData.BuildBowTie();
            var s = demo.BarrierStats();
            Assert.Equal(Enum.GetValues(typeof(BarrierState)).Length, s.Count);
            int barriers = demo.Elements.Count(e => e.IsBarrier);
            Assert.Equal(barriers, s.Values.Sum());
            Assert.Equal(12, barriers);
            Assert.Equal(4, s[BarrierState.Failed]);
            Assert.Equal(2, s[BarrierState.Degraded]);
            Assert.Equal(1, s[BarrierState.Missing]);
            Assert.Equal(2, s[BarrierState.Unknown]);
            Assert.Equal(3, s[BarrierState.Effective]);
        }

        /// <summary>Strong 结论须有证据：顶事件/威胁/屏障/后果/升级因素均执行；只挂 ECFC 不够。</summary>
        [Fact]
        public void Strong_RequiresEvidence_AllElementKinds()
        {
            Code(SystemicErrors.StrongWithoutEvidence, BowTieModel.Create("BT-S", "h", "TOP", "t", S));
            Code(SystemicErrors.StrongWithoutEvidence, BowTieModel.Create("BT-S", "h", "TOP", "t", S, Refs(null, new[] { "E1" })));
            var m = MiniBowTie();
            var ecfcOnly = Refs(null, new[] { "E1" }, new[] { "HF-1" }, new[] { "SR-2026-01" });
            Code(SystemicErrors.StrongWithoutEvidence, m.AddThreat("X1", "x", S, ecfcOnly));
            Code(SystemicErrors.StrongWithoutEvidence, m.AddConsequence("X2", "x", S));
            Code(SystemicErrors.StrongWithoutEvidence, m.AddBarrier("X3", "x", BowTieElementKind.MitigationBarrier, BarrierState.Failed, S));
            Code(SystemicErrors.StrongWithoutEvidence, m.AddEscalationFactor("X4", "x", "PB1", S, Ev("  ", "")));
            Ok(m.AddThreat("X5", "x", S, Ev("EV-1")));
            Code(SystemicErrors.ModerateWithoutEvidence, m.AddThreat("X6", "Moderate 必须有证据（A6）", M));
            Ok(m.AddThreat("X6ok", "Moderate 有证据", M, Ev("EV-1")));
            Ok(m.AddThreat("X7", "待核实可以无证据", V));
        }

        [Fact]
        public void Validation_CollectsAllIssues_NotStopAtFirst()
        {
            var m = MiniBowTie();
            Ok(m.AddThreat("T2", "孤立威胁", M, Ev1));
            Ok(m.AddConsequence("C2", "孤立后果", M, Ev1));
            Ok(m.AddBarrier("PB9", "孤立屏障", BowTieElementKind.PreventionBarrier, BarrierState.Missing, M, Ev1));
            var v = m.Validate();
            Assert.True(v.Has(SystemicErrors.OrphanThreat));
            Assert.True(v.Has(SystemicErrors.OrphanConsequence));
            Assert.True(v.Has(SystemicErrors.OrphanBarrier));
            var r = v.ToResult();
            Assert.False(r.IsSuccess);
            Assert.Equal(v.Issues[0].Code, r.ErrorCode);
        }

        [Fact]
        public void Demo_BowTie_Valid_FiveThreatsFourConsequences_LikePrototype()
        {
            var m = SystemicDemoData.BuildBowTie();
            Assert.True(m.Validate(DemoContext()).IsValid, Issues(m.Validate(DemoContext())));
            Assert.Equal(5, m.OfKind(BowTieElementKind.Threat).Count);       // 原型左侧 5 条威胁
            Assert.Equal(4, m.OfKind(BowTieElementKind.Consequence).Count);  // 原型右侧 4 个后果
            Assert.Equal(3, m.OfKind(BowTieElementKind.EscalationFactor).Count);
        }
    }
}
