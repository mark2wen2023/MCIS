using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Recommendations;
using Mcis.Domain.Systemic;
using Xunit;

namespace Mcis.W15.Sys.Tests
{
    internal static class Fx
    {
        public const EvidenceStrength S = EvidenceStrength.Strong;
        public const EvidenceStrength M = EvidenceStrength.Moderate;
        public const EvidenceStrength V = EvidenceStrength.ToBeVerified;
        public static readonly DateTimeOffset T = new DateTimeOffset(2026, 5, 18, 14, 30, 0, TimeSpan.FromHours(8));
        private const string Sha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

        public static SystemicRefs Ev(params string[] ids) { return new SystemicRefs(ids); }

        /// <summary>W15.1 A6：Moderate 也必须挂证据，自测夹具统一引用虚构证据 EV-001。</summary>
        public static readonly SystemicRefs E = new SystemicRefs(new[] { "EV-001" });

        public static CustodyLedger Ledger(IEnumerable<string> ids)
        {
            var l = new CustodyLedger();
            foreach (var id in ids)
            {
                var r = l.Register(new EvidenceItem(id, "虚构证据 " + id, "演示", "调查员甲", T, Sha), "调查员甲", T);
                Assert.True(r.IsSuccess, r.ErrorMessage);
            }

            return l;
        }

        public static HfacsAnalysis Hfacs(IEnumerable<string> ids)
        {
            var a = new HfacsAnalysis("虚构");
            foreach (var id in ids)
            {
                Assert.True(a.AddFinding(id, "UA", "虚构发现", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            }

            return a;
        }

        public static SafetyRecommendationBoard Board(IEnumerable<string> ids)
        {
            var b = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            foreach (var id in ids)
            {
                var r = b.CreateDraft(id, "虚构建议 " + id, "虚构机构", new[] { "E4" }, T.AddDays(90), "调查员甲", T);
                Assert.True(r.IsSuccess, r.ErrorMessage);
            }

            return b;
        }

        public static SystemicRefContext DemoContext()
        {
            return new SystemicRefContext(
                Ledger(SystemicDemoData.EvidenceIds),
                Hfacs(SystemicDemoData.HfacsFindingIds),
                Board(SystemicDemoData.RecommendationIds),
                SystemicDemoData.EcfcNodeIds);
        }

        /// <summary>最小合法 Bow-tie：T1 → PB1 → TOP → MB1 → C1。</summary>
        public static BowTieModel MinimalBowTie()
        {
            var m = BowTieModel.Create("BT-1", "危险源", "TOP", "顶事件").Value;
            Assert.True(m.AddThreat("T1", "威胁", M, Fx.E).IsSuccess);
            Assert.True(m.AddBarrier("PB1", "预防", BowTieElementKind.PreventionBarrier, BarrierState.Effective, M, Fx.E).IsSuccess);
            Assert.True(m.AddBarrier("MB1", "减缓", BowTieElementKind.MitigationBarrier, BarrierState.Failed, M, Fx.E).IsSuccess);
            Assert.True(m.AddConsequence("C1", "后果", M, Fx.E).IsSuccess);
            Assert.True(m.Connect("T1", "PB1").IsSuccess);
            Assert.True(m.Connect("PB1", "TOP").IsSuccess);
            Assert.True(m.Connect("TOP", "MB1").IsSuccess);
            Assert.True(m.Connect("MB1", "C1").IsSuccess);
            return m;
        }
    }

    public class CommonTests
    {
        [Fact]
        public void Refs_TrimDropBlankDistinct()
        {
            var r = new SystemicRefs(new[] { " EV-001 ", "", null, "EV-001", "EV-002" }, null, new[] { "  " });
            Assert.Equal(new[] { "EV-001", "EV-002" }, r.EvidenceIds);
            Assert.Empty(r.HfacsFindingIds);
            Assert.False(r.IsEmpty);
            Assert.True(SystemicRefs.None.IsEmpty);
        }

        [Fact]
        public void ElementValidation_ErrorCodes()
        {
            var m = BowTieModel.Create("BT-1", "危险源", "TOP", "顶事件").Value;
            Assert.Equal("sys_invalid_id", m.AddThreat("", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_id", m.AddThreat("-bad", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_id", m.AddThreat("has space", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_id", m.AddThreat(new string('a', 65), "x", Fx.M, Fx.E).ErrorCode);
            Assert.True(m.AddThreat(new string('a', 64), "x", Fx.M, Fx.E).IsSuccess);
            Assert.Equal("sys_invalid_id", m.AddThreat("T1\n", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_id", m.AddThreat("T\u0661", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_id", m.AddThreat("Ｔ1", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_argument", m.AddThreat("T1", "  ", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_argument", m.AddThreat("T1", "x", (EvidenceStrength)9).ErrorCode);
            Assert.Equal("sys_duplicate_id", m.AddThreat("TOP", "x", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_id", BowTieModel.Create("", "h", "TOP", "t").ErrorCode);
            Assert.Equal("sys_invalid_argument", BowTieModel.Create("B", " ", "TOP", "t").ErrorCode);
            Assert.Equal("sys_invalid_argument", AcciMapModel.Create("A", "").ErrorCode);
            Assert.Equal("sys_invalid_argument", StampModel.Create("S", null).ErrorCode);
        }

        [Fact]
        public void Strong_RequiresEvidence_EcfcAloneIsNotEnough_InAllThreeModels()
        {
            var ecfcOnly = new SystemicRefs(null, new[] { "E4" }, new[] { "HF-F02" }, new[] { "SR-2026-01" });
            Assert.Equal("sys_strong_without_evidence", BowTieModel.Create("B", "h", "TOP", "t", Fx.S, ecfcOnly).ErrorCode);
            var bt = Fx.MinimalBowTie();
            Assert.Equal("sys_strong_without_evidence", bt.AddThreat("T2", "x", Fx.S).ErrorCode);
            Assert.Equal("sys_strong_without_evidence", bt.AddBarrier("PB2", "x", BowTieElementKind.PreventionBarrier, BarrierState.Failed, Fx.S, ecfcOnly).ErrorCode);
            Assert.True(bt.AddThreat("T2", "x", Fx.S, Fx.Ev("EV-001")).IsSuccess);
            Assert.Equal("sys_moderate_without_evidence", bt.AddThreat("T3", "x", Fx.M, ecfcOnly).ErrorCode); // W15.1 A6

            var am = AcciMapModel.Create("A", "t").Value;
            Assert.Equal("sys_strong_without_evidence", am.AddNode("N1", "x", AcciMapLevel.Company, Fx.S, ecfcOnly).ErrorCode);

            var st = StampModel.Create("S", "h").Value;
            Assert.Equal("sys_strong_without_evidence", st.AddController("C", "x", Fx.S).ErrorCode);
            st.AddController("C", "x", Fx.M, Fx.E);
            st.AddControlledProcess("P", "y", Fx.M, Fx.E);
            st.AddControlAction("CA", "z", "C", "P", Fx.M, Fx.E);
            Assert.Equal("sys_strong_without_evidence", st.AddUnsafeControlAction("U", "u", "CA", UcaType.NotProvided, "c", Fx.S).ErrorCode);
        }

        [Fact]
        public void ValidationToResult_UsesFirstIssueCode()
        {
            var m = BowTieModel.Create("BT-1", "危险源", "TOP", "顶事件").Value;
            var v = m.Validate();
            Assert.False(v.IsValid);
            Assert.Equal("sys_empty_model", v.ToResult().ErrorCode);
            Assert.True(Fx.MinimalBowTie().Validate().ToResult().IsSuccess);
        }
    }

    public class BowTieTests
    {
        [Fact]
        public void Minimal_IsValid()
        {
            Assert.True(Fx.MinimalBowTie().Validate().IsValid);
        }

        [Fact]
        public void Demo_IsValid_WithAllReferenceContexts_AndBarrierStats()
        {
            var m = SystemicDemoData.BuildBowTie();
            var v = m.Validate(Fx.DemoContext());
            Assert.True(v.IsValid, string.Join("\n", v.Issues));
            var stats = m.BarrierStats();
            Assert.Equal(4, stats[BarrierState.Failed]);   // W15.1 D04：PB-VTS、MB-WT 改为 Degraded
            Assert.Equal(2, stats[BarrierState.Degraded]);
            Assert.Equal(1, stats[BarrierState.Missing]);
            Assert.Equal(2, stats[BarrierState.Unknown]);
            Assert.Equal(3, stats[BarrierState.Effective]);
            Assert.Equal(5, m.OfKind(BowTieElementKind.Threat).Count);
            Assert.Equal(4, m.OfKind(BowTieElementKind.Consequence).Count);
        }

        [Fact]
        public void IsolatedThreat_IsOrphan()
        {
            var m = Fx.MinimalBowTie();
            m.AddThreat("T2", "孤立威胁", Fx.M, Fx.E);
            var v = m.Validate();
            var i = Assert.Single(v.Of("sys_orphan_threat"));
            Assert.Equal("T2", i.ElementId);
        }

        [Fact]
        public void ThreatThroughDeadEndBarrier_IsOrphan_AndBarrierOrphan()
        {
            var m = Fx.MinimalBowTie();
            m.AddThreat("T2", "威胁 2", Fx.M, Fx.E);
            m.AddBarrier("PB2", "断头屏障", BowTieElementKind.PreventionBarrier, BarrierState.Unknown, Fx.M, Fx.E);
            Assert.True(m.Connect("T2", "PB2").IsSuccess);
            var v = m.Validate();
            Assert.Equal("T2", Assert.Single(v.Of("sys_orphan_threat")).ElementId);
            Assert.Equal("PB2", Assert.Single(v.Of("sys_orphan_barrier")).ElementId);
        }

        [Fact]
        public void ThreatDirectlyToTop_IsValidPath()
        {
            var m = Fx.MinimalBowTie();
            m.AddThreat("T2", "无屏障的威胁", Fx.M, Fx.E);
            Assert.True(m.Connect("T2", "TOP").IsSuccess);
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void UnreachableConsequence_AndUnusedMitigationBarrier()
        {
            var m = Fx.MinimalBowTie();
            m.AddConsequence("C2", "孤立后果", Fx.M, Fx.E);
            m.AddBarrier("MB2", "未用屏障", BowTieElementKind.MitigationBarrier, BarrierState.Missing, Fx.M, Fx.E);
            var v = m.Validate();
            Assert.Equal("C2", Assert.Single(v.Of("sys_orphan_consequence")).ElementId);
            Assert.Equal("MB2", Assert.Single(v.Of("sys_orphan_barrier")).ElementId);
        }

        [Fact]
        public void PreventionBarrierReachableOnlyFromTopSide_IsOrphan()
        {
            // 预防屏障能到顶事件但没有任何威胁指向它。
            var m = Fx.MinimalBowTie();
            m.AddBarrier("PB2", "无威胁的预防屏障", BowTieElementKind.PreventionBarrier, BarrierState.Effective, Fx.M, Fx.E);
            m.Connect("PB2", "TOP");
            Assert.Equal("PB2", Assert.Single(m.Validate().Of("sys_orphan_barrier")).ElementId);
        }

        [Theory]
        [InlineData("T1", "C1")]
        [InlineData("T1", "MB1")]
        [InlineData("PB1", "MB1")]
        [InlineData("PB1", "C1")]
        [InlineData("TOP", "T1")]
        [InlineData("TOP", "PB1")]
        [InlineData("C1", "TOP")]
        [InlineData("MB1", "PB1")]
        public void DisallowedEdges_AreInvalidEdge(string from, string to)
        {
            Assert.Equal("sys_invalid_edge", Fx.MinimalBowTie().Connect(from, to).ErrorCode);
        }

        [Fact]
        public void EdgeErrors_UnknownDuplicateCycle()
        {
            var m = Fx.MinimalBowTie();
            Assert.Equal("sys_unknown_node", m.Connect("T1", "NOPE").ErrorCode);
            Assert.Equal("sys_duplicate_edge", m.Connect("T1", "PB1").ErrorCode);
            Assert.Equal("sys_cycle", m.Connect("PB1", "PB1").ErrorCode);
            m.AddBarrier("PB2", "p2", BowTieElementKind.PreventionBarrier, BarrierState.Effective, Fx.M, Fx.E);
            m.AddBarrier("PB3", "p3", BowTieElementKind.PreventionBarrier, BarrierState.Effective, Fx.M, Fx.E);
            Assert.True(m.Connect("PB2", "PB3").IsSuccess);
            Assert.True(m.Connect("PB3", "PB1").IsSuccess);
            Assert.Equal("sys_cycle", m.Connect("PB1", "PB2").ErrorCode);
            m.AddBarrier("MB2", "m2", BowTieElementKind.MitigationBarrier, BarrierState.Effective, Fx.M, Fx.E);
            Assert.True(m.Connect("MB1", "MB2").IsSuccess);
            Assert.Equal("sys_cycle", m.Connect("MB2", "MB1").ErrorCode);
        }

        [Fact]
        public void BarrierAndEscalationErrors()
        {
            var m = Fx.MinimalBowTie();
            Assert.Equal("sys_invalid_argument", m.AddBarrier("X", "x", BowTieElementKind.Threat, BarrierState.Failed, Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_argument", m.AddBarrier("X", "x", BowTieElementKind.PreventionBarrier, (BarrierState)7, Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_unknown_node", m.AddEscalationFactor("EF1", "x", "NOPE", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_edge", m.AddEscalationFactor("EF1", "x", "T1", Fx.M, Fx.E).ErrorCode);
            var ef = m.AddEscalationFactor("EF1", "升级因素", "PB1", Fx.M, Fx.E);
            Assert.True(ef.IsSuccess);
            Assert.Equal("PB1", ef.Value.BarrierId);
            Assert.Equal("sys_invalid_edge", m.Connect("EF1", "PB1").ErrorCode);
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void EmptyModel_OnlyTop_OrNoConsequence()
        {
            var m = BowTieModel.Create("BT", "h", "TOP", "t").Value;
            Assert.True(m.Validate().Has("sys_empty_model"));
            m.AddThreat("T1", "x", Fx.M, Fx.E);
            m.Connect("T1", "TOP");
            Assert.True(m.Validate().Has("sys_empty_model"));
        }
    }

    public class AcciMapTests
    {
        private static AcciMapModel Six(bool allowEnvToCrew = true)
        {
            var m = AcciMapModel.Create("AM", "t", allowEnvToCrew).Value;
            m.AddNode("G", "政府", AcciMapLevel.Government, Fx.M, Fx.E);
            m.AddNode("R", "监管", AcciMapLevel.Regulatory, Fx.M, Fx.E);
            m.AddNode("C", "公司", AcciMapLevel.Company, Fx.M, Fx.E);
            m.AddNode("S", "船舶管理", AcciMapLevel.ShipManagement, Fx.M, Fx.E);
            m.AddNode("A", "船员行为", AcciMapLevel.CrewActs, Fx.M, Fx.E);
            m.AddNode("E", "设备环境", AcciMapLevel.EquipmentEnvironment, Fx.M, Fx.E);
            return m;
        }

        [Fact]
        public void Demo_IsValid_SixLevelsAllUsed()
        {
            var m = SystemicDemoData.BuildAcciMap();
            var v = m.Validate(Fx.DemoContext());
            Assert.True(v.IsValid, string.Join("\n", v.Issues));
            foreach (AcciMapLevel l in Enum.GetValues(typeof(AcciMapLevel)))
            {
                Assert.NotEmpty(m.ByLevel(l));
            }

            Assert.Equal(6, Enum.GetValues(typeof(AcciMapLevel)).Length);
            Assert.Equal("政府与法规", AcciMapModel.LevelLabel(AcciMapLevel.Government));
            Assert.Equal("设备与环境", AcciMapModel.LevelLabel(AcciMapLevel.EquipmentEnvironment));
        }

        [Fact]
        public void Downward_AndSameLevel_Allowed_SkippingLevelsAllowed()
        {
            var m = Six();
            Assert.True(m.Connect("G", "R").IsSuccess);
            Assert.True(m.Connect("G", "E").IsSuccess);
            m.AddNode("C2", "公司 2", AcciMapLevel.Company, Fx.M, Fx.E);
            Assert.True(m.Connect("C", "C2").IsSuccess);
        }

        [Theory]
        [InlineData("A", "C")]
        [InlineData("R", "G")]
        [InlineData("E", "S")]
        [InlineData("E", "G")]
        [InlineData("A", "S")]
        public void Upward_IsLevelDirectionError(string from, string to)
        {
            Assert.Equal("sys_level_direction", Six().Connect(from, to).ErrorCode);
        }

        [Fact]
        public void EnvironmentToCrew_AllowedByDefault_RejectedWhenDisabled()
        {
            Assert.True(Six().Connect("E", "A").IsSuccess);
            Assert.Equal("sys_level_direction", Six(false).Connect("E", "A").ErrorCode);
            Assert.True(AcciMapModel.IsDirectionAllowed(AcciMapLevel.Company, AcciMapLevel.Company, false));
            Assert.False(AcciMapModel.IsDirectionAllowed(AcciMapLevel.CrewActs, AcciMapLevel.ShipManagement, true));
        }

        [Fact]
        public void Cycles_Rejected_SameLevelAndAcrossCrewEnvironment()
        {
            var m = Six();
            m.AddNode("C2", "公司 2", AcciMapLevel.Company, Fx.M, Fx.E);
            m.AddNode("C3", "公司 3", AcciMapLevel.Company, Fx.M, Fx.E);
            Assert.True(m.Connect("C", "C2").IsSuccess);
            Assert.True(m.Connect("C2", "C3").IsSuccess);
            Assert.Equal("sys_cycle", m.Connect("C3", "C").ErrorCode);
            Assert.Equal("sys_cycle", m.Connect("C", "C").ErrorCode);
            // 船员→设备环境（向下）与 设备环境→船员（例外）组合成环。
            Assert.True(m.Connect("A", "E").IsSuccess);
            Assert.Equal("sys_cycle", m.Connect("E", "A").ErrorCode);
        }

        [Fact]
        public void EdgeErrors_UnknownDuplicate_AndInvalidLevel()
        {
            var m = Six();
            Assert.Equal("sys_unknown_node", m.Connect("G", "NOPE").ErrorCode);
            Assert.True(m.Connect("G", "R").IsSuccess);
            Assert.Equal("sys_duplicate_edge", m.Connect("G", "R").ErrorCode);
            Assert.Equal("sys_invalid_argument", m.AddNode("X", "x", (AcciMapLevel)6, Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_duplicate_id", m.AddNode("G", "x", AcciMapLevel.Government, Fx.M, Fx.E).ErrorCode);
        }

        [Fact]
        public void IsolatedNodes_AndEmptyModel()
        {
            var m = Six();
            m.Connect("G", "R");
            var v = m.Validate();
            Assert.Equal(new[] { "C", "S", "A", "E" }, v.Of("sys_isolated_node").Select(i => i.ElementId));
            Assert.True(AcciMapModel.Create("AM", "t").Value.Validate().Has("sys_empty_model"));
        }
    }

    public class StampTests
    {
        private static StampModel Loop()
        {
            var m = StampModel.Create("ST", "危险").Value;
            m.AddController("C", "控制器", Fx.M, Fx.E);
            m.AddController("C2", "下级控制器", Fx.M, Fx.E);
            m.AddControlledProcess("P", "过程", Fx.M, Fx.E);
            Assert.True(m.AddControlAction("CA1", "指令", "C", "C2", Fx.M, Fx.E).IsSuccess);
            Assert.True(m.AddControlAction("CA2", "操纵", "C2", "P", Fx.M, Fx.E).IsSuccess);
            Assert.True(m.AddFeedback("FB1", "报告", "C2", "C", Fx.M, Fx.E).IsSuccess);
            Assert.True(m.AddFeedback("FB2", "测量", "P", "C2", Fx.M, Fx.E).IsSuccess);
            return m;
        }

        [Fact]
        public void ClosedLoops_AreValid()
        {
            Assert.True(Loop().Validate().IsValid);
        }

        [Fact]
        public void Demo_OnlyIssue_IsIntentionalMissingFeedback_AllFourUcaTypes()
        {
            var m = SystemicDemoData.BuildStamp();
            var v = m.Validate(Fx.DemoContext());
            var i = Assert.Single(v.Issues);
            Assert.Equal("sys_missing_feedback", i.Code);
            Assert.Equal("CA-ORD", i.ElementId);
            foreach (UcaType t in Enum.GetValues(typeof(UcaType)))
            {
                Assert.NotEmpty(m.UcasOfType(t));
            }

            Assert.Equal(4, Enum.GetValues(typeof(UcaType)).Length);
        }

        [Fact]
        public void ControlActionErrors()
        {
            var m = Loop();
            Assert.Equal("sys_unknown_node", m.AddControlAction("X", "x", "C", "NOPE", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_unknown_node", m.AddControlAction("X", "x", "FB1", "P", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_edge", m.AddControlAction("X", "x", "P", "C", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_cycle", m.AddControlAction("X", "x", "C", "C", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_cycle", m.AddControlAction("X", "x", "C2", "C", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_duplicate_id", m.AddControlAction("CA1", "x", "C", "P", Fx.M, Fx.E).ErrorCode);
            Assert.True(m.AddControlAction("CA3", "越级直接控制", "C", "P", Fx.M, Fx.E).IsSuccess);
        }

        [Fact]
        public void FeedbackAndUcaErrors()
        {
            var m = Loop();
            Assert.Equal("sys_invalid_edge", m.AddFeedback("X", "x", "C", "P", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_unknown_node", m.AddFeedback("X", "x", "NOPE", "C", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_cycle", m.AddFeedback("X", "x", "C", "C", Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_unknown_node", m.AddUnsafeControlAction("U", "u", "NOPE", UcaType.NotProvided, null, Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_unknown_node", m.AddUnsafeControlAction("U", "u", "FB1", UcaType.NotProvided, null, Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_argument", m.AddUnsafeControlAction("U", "u", "CA2", (UcaType)4, null, Fx.M, Fx.E).ErrorCode);
            // W15.1 A8：情境必填
            Assert.Equal("sys_invalid_argument", m.AddUnsafeControlAction("U", "u", "CA2", UcaType.WrongTimingOrOrder, null, Fx.M, Fx.E).ErrorCode);
            Assert.Equal("sys_invalid_argument", m.AddUnsafeControlAction("U", "u", "CA2", UcaType.WrongTimingOrOrder, "  ", Fx.M, Fx.E).ErrorCode);
            var u = m.AddUnsafeControlAction("U", "u", "CA2", UcaType.WrongTimingOrOrder, "雾中", Fx.M, Fx.E);
            Assert.True(u.IsSuccess);
            Assert.Equal("雾中", u.Value.Context);
        }

        [Fact]
        public void MissingFeedback_IsolatedProcess_EmptyModel()
        {
            var m = StampModel.Create("ST", "危险").Value;
            Assert.True(m.Validate().Has("sys_empty_model"));
            m.AddController("C", "c", Fx.M, Fx.E);
            m.AddControlledProcess("P", "p", Fx.M, Fx.E);
            m.AddControlledProcess("P2", "无人控制的过程", Fx.M, Fx.E);
            m.AddControlAction("CA", "a", "C", "P", Fx.M, Fx.E);
            var v = m.Validate();
            Assert.Equal("CA", Assert.Single(v.Of("sys_missing_feedback")).ElementId);
            Assert.Equal("P2", Assert.Single(v.Of("sys_isolated_node")).ElementId);
            // 反馈来自别的组件不算闭环。
            m.AddFeedback("FB", "f", "P2", "C", Fx.M, Fx.E);
            Assert.True(m.Validate().Has("sys_missing_feedback"));
        }
    }

    public class ReferenceTests
    {
        private static BowTieModel WithRefs(SystemicRefs refs)
        {
            var m = Fx.MinimalBowTie();
            Assert.True(m.AddThreat("T9", "引用测试", Fx.M, refs).IsSuccess);
            Assert.True(m.Connect("T9", "TOP").IsSuccess);
            return m;
        }

        [Fact]
        public void UnknownReferences_ReportedPerKind_OnlyWhenContextGiven()
        {
            var m = WithRefs(new SystemicRefs(new[] { "EV-001", "EV-404" }, new[] { "E1", "E99" }, new[] { "HF-F01", "HF-X" }, new[] { "SR-2026-01", "SR-2026-99" }));
            Assert.True(m.Validate().IsValid);
            var v = m.Validate(Fx.DemoContext());
            Assert.Contains("EV-404", Assert.Single(v.Of("sys_unknown_evidence")).Message);
            Assert.Contains("E99", Assert.Single(v.Of("sys_unknown_ecfc")).Message);
            Assert.Contains("HF-X", Assert.Single(v.Of("sys_unknown_hfacs")).Message);
            Assert.Contains("SR-2026-99", Assert.Single(v.Of("sys_unknown_recommendation")).Message);
            Assert.All(v.Issues, i => Assert.Equal("T9", i.ElementId));
        }

        [Fact]
        public void PartialContext_ChecksOnlyProvidedKinds()
        {
            var m = WithRefs(new SystemicRefs(new[] { "EV-404" }, new[] { "E99" }, new[] { "HF-X" }, new[] { "SR-2026-99" }));
            var v = m.Validate(new SystemicRefContext(ledger: Fx.Ledger(new[] { "EV-001" })));
            Assert.Equal(new[] { "sys_unknown_evidence" }, v.Issues.Where(i => i.Severity != SystemicIssueSeverity.Info).Select(i => i.Code));
            Assert.Equal(3, v.NotCheckedRefCount); // W15.2：ECFC / HFACS / 建议未传来源，各 1 处
        }

        [Fact]
        public void ReferencedObjects_AreNotModified()
        {
            var ledger = Fx.Ledger(new[] { "EV-001" });
            var hf = Fx.Hfacs(new[] { "HF-F01" });
            var board = Fx.Board(new[] { "SR-2026-01" });
            var before = (ledger.Items.Count, hf.Findings.Count, board.All.Count, board.All[0].Status);
            SystemicDemoData.Build().Validate(new SystemicRefContext(ledger, hf, board, SystemicDemoData.EcfcNodeIds));
            Assert.Equal(before, (ledger.Items.Count, hf.Findings.Count, board.All.Count, board.All[0].Status));
        }
    }

    public class JsonTests
    {
        [Fact]
        public void Demo_RoundTrip_IsByteIdentical_AndValidationPreserved()
        {
            var doc = SystemicDemoData.Build();
            string json = doc.ToJson();
            var back = SystemicDocument.FromJson(json);
            Assert.True(back.IsSuccess, back.ErrorMessage);
            Assert.Equal(json, back.Value.ToJson());
            Assert.True(back.Value.IsFictionalDemo);
            Assert.Equal(SystemicDemoData.CaseId, back.Value.CaseId);
            var ctx = Fx.DemoContext();
            Assert.Equal(doc.Validate(ctx).Issues.Select(i => i.ToString()), back.Value.Validate(ctx).Issues.Select(i => i.ToString()));
            Assert.Equal(doc.BowTie.Elements.Count, back.Value.BowTie.Elements.Count);
            Assert.Equal(doc.AcciMap.Edges.Count, back.Value.AcciMap.Edges.Count);
            Assert.Equal(doc.Stamp.UnsafeControlActions.Count, back.Value.Stamp.UnsafeControlActions.Count);
            Assert.Equal(BarrierState.Missing, back.Value.BowTie.Get("PB-LOOK").State);
            Assert.Equal("PB-BRM", back.Value.BowTie.Get("EF-MASTER").BarrierId);
            Assert.Equal(new[] { "EV-001", "EV-002" }, back.Value.BowTie.TopEvent.Refs.EvidenceIds);
        }

        [Fact]
        public void SpecialCharacters_RoundTrip()
        {
            const string label = "引号\"反斜杠\\换行\n制表\t控制\u0001 Emoji😀 斜杠/";
            var m = AcciMapModel.Create("AM", label, false).Value;
            m.AddNode("N1", label, AcciMapLevel.Company, Fx.M, Fx.E);
            m.AddNode("N2", "b", AcciMapLevel.CrewActs, Fx.M, Fx.E);
            m.Connect("N1", "N2");
            var doc = new SystemicDocument(null, false, null, m, null);
            var back = SystemicDocument.FromJson(doc.ToJson()).Value;
            Assert.Equal(label, back.AcciMap.Title);
            Assert.Equal(label, back.AcciMap.Get("N1").Label);
            Assert.False(back.AcciMap.AllowEnvironmentToCrew);
            Assert.Null(back.CaseId);
            Assert.Equal(doc.ToJson(), back.ToJson());
        }

        [Fact]
        public void EmptyDocument_RoundTrips_AndIsEmptyModel()
        {
            var doc = new SystemicDocument("CASE-X", false);
            var back = SystemicDocument.FromJson(doc.ToJson());
            Assert.True(back.IsSuccess, back.ErrorMessage);
            Assert.Null(back.Value.BowTie);
            Assert.Equal("sys_empty_model", Assert.Single(back.Value.Validate().Issues).Code);
        }

        [Theory]
        [InlineData("")]
        [InlineData("{")]
        [InlineData("{\"schema\":\"mcis.systemic/1\"} x")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"schema\":\"mcis.systemic/1\"}")]
        [InlineData("[1,2]")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"isFictionalDemo\":\"yes\"}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\"}")]
        [InlineData("{\"a\":\"\\q\"}")]
        [InlineData("{\"a\":tru}")]
        public void MalformedJson_IsJsonInvalid(string json)
        {
            Assert.Equal("sys_json_invalid", SystemicDocument.FromJson(json).ErrorCode);
        }

        [Fact]
        public void NullJson_AndDeepNesting_AreJsonInvalid()
        {
            Assert.Equal("sys_json_invalid", SystemicDocument.FromJson(null).ErrorCode);
            Assert.Equal("sys_json_invalid", SystemicDocument.FromJson(new string('[', 100) + new string(']', 100)).ErrorCode);
        }

        [Fact]
        public void WrongSchema_IsUnsupported()
        {
            string json = new SystemicDocument("C", true).ToJson().Replace("mcis.systemic/1", "mcis.systemic/2");
            Assert.Equal("sys_json_unsupported_schema", SystemicDocument.FromJson(json).ErrorCode);
        }

        [Fact]
        public void TamperedJson_StructuralRulesEnforcedOnLoad()
        {
            string json = SystemicDemoData.Build().ToJson();
            // 未知枚举名 / 数字枚举 → json_invalid
            Assert.Equal("sys_json_invalid", SystemicDocument.FromJson(json.Replace("\"state\":\"Missing\"", "\"state\":\"Partial\"")).ErrorCode);
            Assert.Equal("sys_json_invalid", SystemicDocument.FromJson(json.Replace("\"level\":\"Government\"", "\"level\":\"0\"")).ErrorCode);
            // 层间反向：插入 船员行为 → 公司 的边
            Assert.Equal("sys_level_direction", SystemicDocument.FromJson(json.Replace("[\"EE4\",\"EE5\"]", "[\"EE4\",\"EE5\"],[\"CA2\",\"CO1\"]")).ErrorCode);
            // 成环：EE5 → EE4
            Assert.Equal("sys_cycle", SystemicDocument.FromJson(json.Replace("[\"EE4\",\"EE5\"]", "[\"EE4\",\"EE5\"],[\"EE5\",\"EE4\"]")).ErrorCode);
            // Strong 无证据：清空 R1 的证据
            string strongNoEv = json.Replace("\"id\":\"R1\",\"label\":\"VTS 未实施雾中单向管制\",\"strength\":\"Strong\",\"refs\":{\"evidence\":[\"EV-007\"]",
                                             "\"id\":\"R1\",\"label\":\"VTS 未实施雾中单向管制\",\"strength\":\"Strong\",\"refs\":{\"evidence\":[]");
            Assert.NotEqual(json, strongNoEv);
            Assert.Equal("sys_strong_without_evidence", SystemicDocument.FromJson(strongNoEv).ErrorCode);
            // 未知节点
            Assert.Equal("sys_unknown_node", SystemicDocument.FromJson(json.Replace("[\"EE4\",\"EE5\"]", "[\"EE4\",\"ZZ\"]")).ErrorCode);
        }

        [Fact]
        public void Json_IsDeterministic_AndLabelsFictional()
        {
            string a = SystemicDemoData.Build().ToJson();
            string b = SystemicDemoData.Build().ToJson();
            Assert.Equal(a, b);
            Assert.Contains("\"isFictionalDemo\":true", a);
            Assert.Contains("虚构", a);
            Assert.Contains("14:24:00", a);
        }
    }

    public class PurityTests
    {
        [Fact]
        public void SystemicAssembly_HasNoUnityReference()
        {
            Assert.DoesNotContain(typeof(BowTieModel).Assembly.GetReferencedAssemblies(), a => a.Name.StartsWith("UnityEngine", StringComparison.Ordinal));
        }

        [Fact]
        public void SystemicSources_DoNotUseDataAssemblyOrUnity()
        {
            string dir = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../../Assets/_Project/Scripts/Domain/Systemic"));
            Assert.True(Directory.Exists(dir), dir);
            foreach (string f in Directory.GetFiles(dir, "*.cs"))
            {
                string src = File.ReadAllText(f);
                Assert.DoesNotContain("using Mcis.Data", src);
                Assert.DoesNotContain("UnityEngine", src);
            }
        }
    }
}
