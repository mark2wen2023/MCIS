using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Models;
using Mcis.Domain.Systemic;
using Xunit;

namespace Mcis.W15.Sys.Tests
{
    /// <summary>W15.1：D01–D04 与 A1–A11（架构师裁定，2026-11-11 19:50）。全部为虚构合成数据。</summary>
    internal static class W151
    {
        public const EvidenceStrength S = EvidenceStrength.Strong;
        public const EvidenceStrength M = EvidenceStrength.Moderate;
        public const EvidenceStrength V = EvidenceStrength.ToBeVerified;
        public static readonly SystemicRefs E = new SystemicRefs(new[] { "EV-001" });

        public static T Ok<T>(Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static void Code<T>(string code, Result<T> r)
        {
            Assert.False(r.IsSuccess, "期望失败 " + code);
            Assert.Equal(code, r.ErrorCode);
        }

        public static void ReadOnly<T>(IReadOnlyList<T> list)
        {
            var asList = list as IList;
            Assert.NotNull(asList);
            Assert.Throws<NotSupportedException>(() => asList.Clear());
            var typed = list as IList<T>;
            if (typed != null)
            {
                Assert.Throws<NotSupportedException>(() => typed.Add(default(T)));
            }
        }

        /// <summary>T0 → T1 → PB1 → TOP → MB1 → C1（A1 威胁链）。</summary>
        public static BowTieModel ChainBowTie()
        {
            var m = Ok(BowTieModel.Create("BT-C", "危险源（虚构）", "TOP", "顶事件（虚构）"));
            Ok(m.AddThreat("T0", "根原因（虚构）", M, E));
            Ok(m.AddThreat("T1", "直接威胁（虚构）", M, E));
            Ok(m.AddBarrier("PB1", "预防", BowTieElementKind.PreventionBarrier, BarrierState.Failed, M, E));
            Ok(m.AddBarrier("MB1", "减缓", BowTieElementKind.MitigationBarrier, BarrierState.Degraded, M, E));
            Ok(m.AddConsequence("C1", "后果", M, E));
            Ok(m.Connect("T0", "T1"));
            Ok(m.Connect("T1", "PB1"));
            Ok(m.Connect("PB1", "TOP"));
            Ok(m.Connect("TOP", "MB1"));
            Ok(m.Connect("MB1", "C1"));
            return m;
        }

        public static StampModel Loop()
        {
            var m = Ok(StampModel.Create("ST-L", "危险（虚构）"));
            Ok(m.AddController("C", "控制器", M, E));
            Ok(m.AddControlledProcess("P", "过程", M, E));
            Ok(m.AddControlAction("CA", "动作", "C", "P", M, E));
            Ok(m.AddFeedback("FB", "反馈", "P", "C", M, E));
            Ok(m.AddUnsafeControlAction("U1", "UCA", "CA", UcaType.NotProvided, "雾中", M, E));
            return m;
        }

        public static AcciMapModel Acci()
        {
            var m = Ok(AcciMapModel.Create("AM-1", "虚构 AcciMap"));
            Ok(m.AddNode("G", "政府", AcciMapLevel.Government, M, E));
            Ok(m.AddNode("R", "监管", AcciMapLevel.Regulatory, M, E));
            Ok(m.AddNode("CR", "船员", AcciMapLevel.CrewActs, M, E));
            Ok(m.AddNode("EQ", "设备", AcciMapLevel.EquipmentEnvironment, M, E));
            Ok(m.Connect("G", "R"));
            Ok(m.Connect("R", "CR"));
            Ok(m.Connect("CR", "EQ"));
            return m;
        }

        public static CustodyLedger Ledger(params string[] ids)
        {
            return Fx.Ledger(ids);
        }
    }

    public class W151_D01_ReadOnlyTests
    {
        [Fact]
        public void AllExposedCollections_AreReadOnlyViews()
        {
            var bt = W151.ChainBowTie();
            W151.ReadOnly(bt.Elements);
            W151.ReadOnly(bt.Edges);
            W151.ReadOnly(bt.OfKind(BowTieElementKind.Threat));
            var am = W151.Acci();
            Assert.True(am.ConnectInformationFlow("EQ", "G").IsSuccess);
            W151.ReadOnly(am.Nodes);
            W151.ReadOnly(am.Edges);
            W151.ReadOnly(am.InformationFlows);
            W151.ReadOnly(am.ByLevel(AcciMapLevel.Government));
            var st = W151.Loop();
            W151.ReadOnly(st.Components);
            W151.ReadOnly(st.ControlActions);
            W151.ReadOnly(st.Feedback);
            W151.ReadOnly(st.UnsafeControlActions);
            W151.ReadOnly(st.UcasOfType(UcaType.NotProvided));
            var refs = new SystemicRefs(new[] { "EV-001" }, new[] { "E1" });
            W151.ReadOnly(refs.EvidenceIds);
            W151.ReadOnly(refs.EcfcNodeIds);
            W151.ReadOnly(refs.All);
            W151.ReadOnly(refs.Ids(SystemicRefKinds.Evidence));
            W151.ReadOnly(bt.Validate().Issues);
            Assert.Equal(6, bt.Elements.Count); // 未被修改
        }

        [Fact]
        public void ElementFields_HaveNoPublicSetters()
        {
            foreach (var t in new[] { typeof(SystemicElement), typeof(BowTieElement), typeof(AcciMapNode), typeof(UnsafeControlAction) })
            {
                foreach (var p in t.GetProperties())
                {
                    Assert.True(p.SetMethod == null || !p.SetMethod.IsPublic, t.Name + "." + p.Name + " 不应有公开 setter");
                }
            }
        }
    }

    public class W151_D02_LiveHfacsAndTrimTests
    {
        [Fact]
        public void Hfacs_IsQueriedLive_AtValidateTime()
        {
            var hf = new HfacsAnalysis("虚构");
            var ctx = new SystemicRefContext(hfacs: hf);
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, new SystemicRefs(new[] { "EV-001" }, null, new[] { "HF-NEW" })));
            Assert.True(am.Validate(ctx).Has(SystemicErrors.UnknownHfacs));
            W151.Ok(hf.AddFinding("HF-NEW", "UA", "后加的发现（虚构）", EvidenceStrength.ToBeVerified, null, null));
            Assert.False(am.Validate(ctx).Has(SystemicErrors.UnknownHfacs)); // 同一上下文，之后新增的发现即可见
        }

        [Fact]
        public void KnownEcfcIds_AreTrimmed_ButNotOtherwiseNormalized()
        {
            var ctx = new SystemicRefContext(knownEcfcNodeIds: new[] { " E1 ", "E2\t", null, "  " });
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.V, new SystemicRefs(null, new[] { "E1", "E2" })));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.V, new SystemicRefs(null, new[] { "e1" })));
            W151.Ok(am.Connect("A", "B"));
            var v = am.Validate(ctx);
            Assert.Equal(new[] { "B" }, v.Of(SystemicErrors.UnknownEcfc).Select(i => i.ElementId)); // 大小写不归一化
        }
    }

    public class W151_D03_CaseIdTests
    {
        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("  bad id \n")]
        [InlineData("ab")]
        [InlineData("CASE 1")]
        public void InvalidCaseId_FlaggedByValidate_AndRejectedByFactory(string caseId)
        {
            Assert.False(EvidenceItem.IsValidCaseId(caseId)); // 与 Evidence 模块同一规则
            var d = new SystemicDocument(caseId, true, W151.ChainBowTie());
            var v = d.Validate();
            Assert.True(v.Has(SystemicErrors.InvalidId));
            Assert.False(v.IsValid);
            W151.Code(SystemicErrors.InvalidId, SystemicDocument.Create(caseId, true, W151.ChainBowTie()));
        }

        [Fact]
        public void ValidCaseId_NotFlagged_AndFactoryOk()
        {
            Assert.True(new SystemicDocument("CASE-2026-X1", true, W151.ChainBowTie()).Validate().IsValid);
            Assert.Equal("CASE-2026-X1", W151.Ok(SystemicDocument.Create("CASE-2026-X1", true)).CaseId);
        }

        [Fact]
        public void InvalidCaseId_StillLoadsFromJson_ButValidateFlags()
        {
            var json = new SystemicDocument(null, true, W151.ChainBowTie()).ToJson();
            var back = W151.Ok(SystemicDocument.FromJson(json));
            Assert.True(back.Validate().Has(SystemicErrors.InvalidId));
        }
    }

    public class W151_D04_DegradedTests
    {
        [Fact]
        public void Degraded_IsAcceptedCountedSerializedAndSettable()
        {
            var m = W151.ChainBowTie();
            Assert.Equal(BarrierState.Degraded, m.Get("MB1").State);
            var stats = m.BarrierStats();
            Assert.Equal(5, stats.Count);
            Assert.Equal(1, stats[BarrierState.Degraded]);
            var json = new SystemicDocument("CASE-1", true, m).ToJson();
            Assert.Contains("\"state\":\"Degraded\"", json);
            var back = W151.Ok(SystemicDocument.FromJson(json));
            Assert.Equal(BarrierState.Degraded, back.BowTie.Get("MB1").State);
            Assert.Equal(json, back.ToJson());
            W151.Ok(m.SetBarrierState("PB1", BarrierState.Degraded));
            Assert.Equal(2, m.BarrierStats()[BarrierState.Degraded]);
            W151.Code(SystemicErrors.InvalidArgument, m.SetBarrierState("T0", BarrierState.Failed));
            W151.Code(SystemicErrors.InvalidArgument, m.SetBarrierState("PB1", (BarrierState)9));
            W151.Code(SystemicErrors.UnknownNode, m.SetBarrierState("NOPE", BarrierState.Failed));
        }

        [Fact]
        public void Demo_PartialBarriers_AreDegraded()
        {
            var demo = SystemicDemoData.BuildBowTie();
            Assert.Equal(BarrierState.Degraded, demo.Get("PB-VTS").State);
            Assert.Equal(BarrierState.Degraded, demo.Get("MB-WT").State);
        }
    }

    public class W151_A1_ThreatChainTests
    {
        [Fact]
        public void ThreatChain_IsValid_PrecursorNotOrphan()
        {
            var m = W151.ChainBowTie();
            var v = m.Validate();
            Assert.True(v.IsValid, string.Join("\n", v.Issues));
            Assert.True(BowTieModel.IsAllowed(BowTieElementKind.Threat, BowTieElementKind.Threat));
        }

        [Fact]
        public void ThreatChain_Cycle_Rejected()
        {
            var m = W151.ChainBowTie();
            W151.Ok(m.AddThreat("T00", "更早原因", W151.V));
            W151.Ok(m.Connect("T00", "T0"));
            W151.Code(SystemicErrors.Cycle, m.Connect("T1", "T00"));
            W151.Code(SystemicErrors.Cycle, m.Connect("T0", "T0"));
        }

        [Fact]
        public void OnlyLastThreatInChain_ConnectsTowardTopEvent()
        {
            var m = W151.ChainBowTie();
            W151.Code(SystemicErrors.InvalidEdge, m.Connect("T0", "PB1"));  // T0 已是前驱
            W151.Code(SystemicErrors.InvalidEdge, m.Connect("T0", "TOP"));
            W151.Ok(m.AddThreat("T2", "另一威胁", W151.V));
            W151.Code(SystemicErrors.InvalidEdge, m.Connect("T1", "T2"));    // T1 已是链末（连屏障）
            W151.Ok(m.Connect("T2", "T1"));                                  // 多个前驱可汇入同一链末威胁
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void DeadEndThreatChain_AllOrphan()
        {
            var m = W151.ChainBowTie();
            W151.Ok(m.AddThreat("TA", "a", W151.V));
            W151.Ok(m.AddThreat("TB", "b", W151.V));
            W151.Ok(m.Connect("TA", "TB"));
            var v = m.Validate();
            Assert.Equal(new[] { "TA", "TB" }, v.Of(SystemicErrors.OrphanThreat).Select(i => i.ElementId).OrderBy(x => x));
        }

        [Fact]
        public void ThreatChain_JsonRoundTrip()
        {
            var json = new SystemicDocument("CASE-1", true, W151.ChainBowTie()).ToJson();
            Assert.Contains("[\"T0\",\"T1\"]", json);
            Assert.Equal(json, W151.Ok(SystemicDocument.FromJson(json)).ToJson());
        }
    }

    public class W151_A2_InformationFlowTests
    {
        [Fact]
        public void InformationFlow_MayGoUpward_AndIgnoresCycles()
        {
            var m = W151.Acci();
            W151.Code(SystemicErrors.LevelDirection, m.Connect("EQ", "G"));
            var f = W151.Ok(m.ConnectInformationFlow("EQ", "G"));
            Assert.Equal(SystemicEdgeKind.InformationFlow, f.Kind);
            W151.Ok(m.ConnectInformationFlow("CR", "R"));       // 与因果边 R→CR 反向，不算成环
            W151.Ok(m.Connect("G", "EQ"));                      // 因果成环判断不受信息流影响
            Assert.Equal(4, m.Edges.Count);
            Assert.Equal(2, m.InformationFlows.Count);
            Assert.All(m.Edges, e => Assert.Equal(SystemicEdgeKind.Causal, e.Kind));
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void InformationFlow_Errors()
        {
            var m = W151.Acci();
            W151.Code(SystemicErrors.UnknownNode, m.ConnectInformationFlow("EQ", "NOPE"));
            W151.Code(SystemicErrors.InvalidEdge, m.ConnectInformationFlow("EQ", "EQ"));
            W151.Ok(m.ConnectInformationFlow("EQ", "G"));
            W151.Code(SystemicErrors.DuplicateEdge, m.ConnectInformationFlow("EQ", "G"));
            W151.Ok(m.DisconnectInformationFlow("EQ", "G"));
            W151.Code(SystemicErrors.UnknownEdge, m.DisconnectInformationFlow("EQ", "G"));
        }

        [Fact]
        public void NodeLinkedOnlyByInformationFlow_IsNotIsolated()
        {
            var m = W151.Acci();
            W151.Ok(m.AddNode("CO", "公司", AcciMapLevel.Company, W151.V));
            Assert.True(m.Validate().Has(SystemicErrors.IsolatedNode));
            W151.Ok(m.ConnectInformationFlow("CR", "CO"));
            Assert.False(m.Validate().Has(SystemicErrors.IsolatedNode));
        }

        [Fact]
        public void InformationFlow_JsonRoundTrip_AndOptionalOnRead()
        {
            var m = W151.Acci();
            string plain = new SystemicDocument("CASE-1", true, null, m).ToJson();
            Assert.DoesNotContain("infoFlows", plain);
            W151.Ok(m.ConnectInformationFlow("EQ", "G"));
            string json = new SystemicDocument("CASE-1", true, null, m).ToJson();
            Assert.Contains("\"infoFlows\":[[\"EQ\",\"G\"]]", json);
            var back = W151.Ok(SystemicDocument.FromJson(json));
            Assert.Single(back.AcciMap.InformationFlows);
            Assert.Equal(json, back.ToJson());
            W151.Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(json.Replace("\"infoFlows\":[[\"EQ\",\"G\"]]", "\"infoFlows\":[[\"EQ\"]]")));
            W151.Code(SystemicErrors.UnknownNode, SystemicDocument.FromJson(json.Replace("[\"EQ\",\"G\"]]", "[\"EQ\",\"ZZ\"]]")));
        }

        [Fact]
        public void Demo_HasUpwardInformationFlow()
        {
            var am = SystemicDemoData.BuildAcciMap();
            Assert.Contains(am.InformationFlows, f => f.FromId == "CA1" && f.ToId == "R1");
        }
    }

    public class W151_A3_LevelsTests
    {
        [Fact]
        public void AcciMap_KeepsSpecSixLevels_NoEventSequenceLevel()
        {
            Assert.Equal(
                new[] { "Government", "Regulatory", "Company", "ShipManagement", "CrewActs", "EquipmentEnvironment" },
                Enum.GetNames(typeof(AcciMapLevel)));
        }
    }

    public class W151_A4_ActorIdTests
    {
        [Fact]
        public void ActorId_OnAllNodeKinds_RoundTrips()
        {
            var bt = W151.Ok(BowTieModel.Create("BT-1", "h", "TOP", "t", W151.V, null, "SHIP-A"));
            W151.Ok(bt.AddThreat("T1", "t1", W151.V, null, "SHIP-A"));
            W151.Ok(bt.AddBarrier("PB1", "pb", BowTieElementKind.PreventionBarrier, BarrierState.Failed, W151.V, null, "SHIP-B"));
            W151.Ok(bt.AddEscalationFactor("EF1", "ef", "PB1", W151.V, null, "COMPANY-X"));
            W151.Ok(bt.AddConsequence("C1", "c", W151.V, null, "SHIP-B"));
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("N1", "n", AcciMapLevel.Company, W151.V, null, "COMPANY-X"));
            var st = W151.Ok(StampModel.Create("ST-1", "h"));
            W151.Ok(st.AddController("C", "c", W151.V, null, "SHIP-A"));
            W151.Ok(st.AddControlledProcess("P", "p", W151.V, null, "SHIP-A"));
            W151.Ok(st.AddControlAction("CA", "a", "C", "P", W151.V, null, "SHIP-A"));
            W151.Ok(st.AddFeedback("FB", "f", "P", "C", W151.V, null, "SHIP-A"));
            W151.Ok(st.AddUnsafeControlAction("U", "u", "CA", UcaType.NotProvided, "ctx", W151.V, null, "SHIP-A"));
            Assert.Equal("SHIP-A", bt.TopEvent.ActorId);
            Assert.Equal("COMPANY-X", bt.Get("EF1").ActorId);
            var doc = new SystemicDocument("CASE-1", true, bt, am, st);
            string json = doc.ToJson();
            Assert.Contains("\"actorId\":\"SHIP-B\"", json);
            var back = W151.Ok(SystemicDocument.FromJson(json));
            Assert.Equal("SHIP-A", back.BowTie.TopEvent.ActorId);
            Assert.Equal("COMPANY-X", back.AcciMap.Get("N1").ActorId);
            Assert.Equal("SHIP-A", back.Stamp.Get("U").ActorId);
            Assert.Equal(json, back.ToJson());
        }

        [Fact]
        public void ActorId_IsOptional_AndValidated()
        {
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            var n = W151.Ok(am.AddNode("N1", "n", AcciMapLevel.Company, W151.V));
            Assert.Null(n.ActorId);
            Assert.DoesNotContain("actorId", new SystemicDocument("CASE-1", true, null, am).ToJson());
            W151.Code(SystemicErrors.InvalidId, am.AddNode("N2", "n", AcciMapLevel.Company, W151.V, null, "bad actor"));
            W151.Code(SystemicErrors.InvalidId, am.AddNode("N2", "n", AcciMapLevel.Company, W151.V, null, ""));
            Assert.Null(am.Get("N2"));
        }
    }

    public class W151_A5_TypedRefsTests
    {
        [Fact]
        public void TypedRefs_KindsAndLegacyView()
        {
            var r = new SystemicRefs(new[]
            {
                new SystemicRef(SystemicRefKinds.Evidence, " EV-001 "),
                new SystemicRef(SystemicRefKinds.Statement, "IR-06"),
                new SystemicRef(SystemicRefKinds.ColregCheck, "R6"),
                new SystemicRef(SystemicRefKinds.DamageTrack, "DT-1"),
                new SystemicRef(SystemicRefKinds.Statement, "IR-06"),
                null
            });
            Assert.Equal(new[] { "EV-001" }, r.EvidenceIds);
            Assert.Equal(new[] { "IR-06" }, r.Ids(SystemicRefKinds.Statement));
            Assert.Equal(4, r.All.Count);
            Assert.Equal(new[] { "Evidence", "Statement", "ColregCheck", "DamageTrack" }, r.Kinds);
            var legacy = new SystemicRefs(new[] { "EV-001" }, new[] { "E1" }, new[] { "HF-1" }, new[] { "SR-2026-01" });
            Assert.Equal(new[] { "Evidence", "Ecfc", "Hfacs", "Recommendation" }, legacy.Kinds);
            Assert.Equal(new[] { "IR-07" }, SystemicRefs.Of(SystemicRefKinds.Statement, "IR-07", " ", null).Ids(SystemicRefKinds.Statement));
            Assert.Throws<ArgumentException>(() => new SystemicRef("statement", "x"));
            Assert.Throws<ArgumentException>(() => new SystemicRef("Statement", " "));
            Assert.Throws<ArgumentException>(() => new SystemicRef(null, "x"));
        }

        [Fact]
        public void UnregisteredKind_IsWarningOnly_RegisteredKind_IsChecked()
        {
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            var refs = new SystemicRefs(new[] { new SystemicRef(SystemicRefKinds.Evidence, "EV-001"), new SystemicRef(SystemicRefKinds.Statement, "IR-06"), new SystemicRef(SystemicRefKinds.ColregCheck, "R6") });
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, refs));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.V));
            W151.Ok(am.Connect("A", "B"));
            Assert.DoesNotContain(am.Validate().Issues, i => i.Severity != SystemicIssueSeverity.Info); // 无上下文：不查（W15.2 只留 Info 痕迹）
            Assert.Equal(3, am.Validate().NotCheckedRefCount);
            var ctx = new SystemicRefContext();
            var v = am.Validate(ctx);
            Assert.True(v.IsValid);
            Assert.Equal(2, v.Warnings.Count);
            var nonInfo = v.Issues.Where(i => i.Severity != SystemicIssueSeverity.Info).ToList();
            Assert.All(nonInfo, i => Assert.Equal(SystemicErrors.UnregisteredRefKind, i.Code));
            Assert.All(nonInfo, i => Assert.Equal(SystemicIssueSeverity.Warning, i.Severity));
            W151.Ok(ctx.RegisterValidator(SystemicRefKinds.Statement, id => id == "IR-01"));
            Assert.True(ctx.HasValidator(SystemicRefKinds.Statement));
            v = am.Validate(ctx);
            Assert.False(v.IsValid);
            Assert.Equal(SystemicErrors.UnknownRef, Assert.Single(v.Errors).Code);
            Assert.Equal(SystemicErrors.UnregisteredRefKind, Assert.Single(v.Warnings).Code);
            W151.Ok(ctx.RegisterValidator(SystemicRefKinds.Statement, id => id == "IR-06"));  // 替换
            W151.Ok(ctx.RegisterValidator(SystemicRefKinds.ColregCheck, id => id.StartsWith("R", StringComparison.Ordinal)));
            Assert.Equal(new[] { SystemicErrors.RefNotChecked }, am.Validate(ctx).Issues.Select(i => i.Code)); // 只剩证据未传来源的 Info
            Assert.Equal("sys_unknown_ref", v.ToResult().ErrorCode);
        }

        [Fact]
        public void RegisterValidator_RejectsBuiltInInvalidOrNull()
        {
            var ctx = new SystemicRefContext();
            W151.Code(SystemicErrors.InvalidArgument, ctx.RegisterValidator(SystemicRefKinds.Evidence, _ => true));
            W151.Code(SystemicErrors.InvalidArgument, ctx.RegisterValidator(SystemicRefKinds.Hfacs, _ => true));
            W151.Code(SystemicErrors.InvalidArgument, ctx.RegisterValidator("bad kind", _ => true));
            W151.Code(SystemicErrors.InvalidArgument, ctx.RegisterValidator(SystemicRefKinds.DamageTrack, null));
            Assert.False(ctx.HasValidator(SystemicRefKinds.DamageTrack));
        }

        [Fact]
        public void BuiltInKinds_WithoutSource_LeaveInfoTrace_NoErrorOrWarning()
        {
            // W15.2 / D05：原“完全静默”改为每种 kind 一条 Info 级 sys_ref_not_checked，不报错、不警告。
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, new SystemicRefs(new[] { "EV-404" }, new[] { "X" }, new[] { "HF-X" }, new[] { "SR-2026-99" })));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.V));
            W151.Ok(am.Connect("A", "B"));
            var v = am.Validate(new SystemicRefContext());
            Assert.All(v.Issues, i => Assert.Equal(SystemicErrors.RefNotChecked, i.Code));
            Assert.Equal(4, v.Issues.Count);
            Assert.Equal(4, v.NotCheckedRefCount);
        }

        [Fact]
        public void TypedRefs_Json_CamelCaseKeys_RoundTrip_LegacyPrefixKept()
        {
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            var refs = new SystemicRefs(new[] { new SystemicRef(SystemicRefKinds.DamageTrack, "DT-1"), new SystemicRef(SystemicRefKinds.Evidence, "EV-001"), new SystemicRef(SystemicRefKinds.Statement, "IR-06"), new SystemicRef(SystemicRefKinds.ColregCheck, "R6") });
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, refs));
            string json = new SystemicDocument("CASE-1", true, null, am).ToJson();
            Assert.Contains("\"refs\":{\"evidence\":[\"EV-001\"],\"ecfc\":[],\"hfacs\":[],\"recommendations\":[],\"damageTrack\":[\"DT-1\"],\"statement\":[\"IR-06\"],\"colregCheck\":[\"R6\"]}", json);
            var back = W151.Ok(SystemicDocument.FromJson(json));
            Assert.Equal(new[] { "IR-06" }, back.AcciMap.Get("A").Refs.Ids(SystemicRefKinds.Statement));
            Assert.Equal(json, back.ToJson());
            var custom = W151.Ok(SystemicDocument.FromJson(json.Replace("\"colregCheck\"", "\"fooBar\"")));
            Assert.Equal(new[] { "R6" }, custom.AcciMap.Get("A").Refs.Ids("FooBar"));
            W151.Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(json.Replace("\"colregCheck\"", "\"ColregCheck\"")));
            W151.Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(json.Replace("\"colregCheck\"", "\"recommendation\"")));
            W151.Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(json.Replace("\"colregCheck\":[\"R6\"]", "\"colregCheck\":[6]")));
        }

        [Fact]
        public void LegacyJson_WithoutNewFields_StillLoads()
        {
            const string legacy = "{\"schema\":\"mcis.systemic/1\",\"caseId\":\"CASE-1\",\"isFictionalDemo\":true,\"bowTie\":null," +
                "\"acciMap\":{\"id\":\"AM-1\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[" +
                "{\"id\":\"A\",\"label\":\"a\",\"strength\":\"Moderate\",\"refs\":{\"evidence\":[\"EV-001\"],\"ecfc\":[\"E1\"],\"hfacs\":[],\"recommendations\":[]},\"level\":\"Company\"}," +
                "{\"id\":\"B\",\"label\":\"b\",\"strength\":\"ToBeVerified\",\"refs\":{\"evidence\":[],\"ecfc\":[],\"hfacs\":[],\"recommendations\":[]},\"level\":\"CrewActs\"}]," +
                "\"edges\":[[\"A\",\"B\"]]},\"stamp\":null}";
            var d = W151.Ok(SystemicDocument.FromJson(legacy));
            Assert.Equal(legacy, d.ToJson());
            Assert.Null(d.AcciMap.Get("A").ActorId);
        }
    }

    public class W151_A6_ModerateEvidenceTests
    {
        [Fact]
        public void Moderate_RequiresEvidence_InAllModels()
        {
            var ecfcOnly = new SystemicRefs(null, new[] { "E1" });
            W151.Code(SystemicErrors.ModerateWithoutEvidence, BowTieModel.Create("B", "h", "TOP", "t", W151.M));
            var bt = W151.ChainBowTie();
            W151.Code(SystemicErrors.ModerateWithoutEvidence, bt.AddThreat("T9", "x", W151.M, ecfcOnly));
            W151.Code(SystemicErrors.ModerateWithoutEvidence, bt.AddEscalationFactor("EF9", "x", "PB1", W151.M));
            var am = W151.Acci();
            W151.Code(SystemicErrors.ModerateWithoutEvidence, am.AddNode("N9", "x", AcciMapLevel.Company, W151.M));
            var st = W151.Loop();
            W151.Code(SystemicErrors.ModerateWithoutEvidence, st.AddController("C9", "x", W151.M));
            W151.Code(SystemicErrors.ModerateWithoutEvidence, st.AddUnsafeControlAction("U9", "u", "CA", UcaType.NotProvided, "c", W151.M));
            Assert.True(bt.AddThreat("T9", "x", W151.V).IsSuccess);           // ToBeVerified 可无证据
            Assert.True(BowTieModel.Create("B", "h", "TOP", "t").IsSuccess);  // 默认顶事件强度 = ToBeVerified
        }

        [Fact]
        public void UpdateToModerateWithoutEvidence_Rejected_Unchanged()
        {
            var am = W151.Acci();
            W151.Ok(am.AddNode("N9", "x", AcciMapLevel.Company, W151.V));
            W151.Code(SystemicErrors.ModerateWithoutEvidence, am.UpdateNode("N9", strength: W151.M));
            Assert.Equal(W151.V, am.Get("N9").Strength);
            W151.Code(SystemicErrors.StrongWithoutEvidence, am.UpdateNode("G", refs: SystemicRefs.None, strength: W151.S));
            Assert.Equal(W151.M, am.Get("G").Strength);
        }

        [Fact]
        public void NeedsReviewEvidence_StrongIsError_ModerateIsWarning()
        {
            var ledger = W151.Ledger("EV-001", "EV-002");
            W151.Ok(ledger.MarkNeedsReview("EV-002", "调查员甲", Fx.T, "哈希待复核（虚构）"));
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("S1", "s", AcciMapLevel.Company, W151.S, new SystemicRefs(new[] { "EV-002" })));
            W151.Ok(am.AddNode("M1", "m", AcciMapLevel.Company, W151.M, new SystemicRefs(new[] { "EV-002" })));
            W151.Ok(am.AddNode("OK", "ok", AcciMapLevel.Company, W151.S, new SystemicRefs(new[] { "EV-001" })));
            W151.Ok(am.Connect("S1", "M1"));
            W151.Ok(am.Connect("M1", "OK"));
            var v = am.Validate(new SystemicRefContext(ledger: ledger));
            var err = Assert.Single(v.Errors);
            Assert.Equal(SystemicErrors.EvidenceUnreliable, err.Code);
            Assert.Equal("S1", err.ElementId);
            var warn = Assert.Single(v.Warnings);
            Assert.Equal(SystemicErrors.EvidenceNeedsReview, warn.Code);
            Assert.Equal("M1", warn.ElementId);
            W151.Ok(am.UpdateNode("S1", strength: W151.M));
            Assert.True(am.Validate(new SystemicRefContext(ledger: ledger)).IsValid);
        }

        [Fact]
        public void MismatchEvidence_StrongIsError()
        {
            var ledger = W151.Ledger("EV-001");
            W151.Ok(ledger.Verify("EV-001", "调查员甲", Fx.T, new string('f', 64)));
            Assert.Equal(EvidenceStatus.Mismatch, ledger.StatusOf("EV-001"));
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("S1", "s", AcciMapLevel.Company, W151.S, W151.E));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.V));
            W151.Ok(am.Connect("S1", "B"));
            Assert.Equal(SystemicErrors.EvidenceUnreliable, Assert.Single(am.Validate(new SystemicRefContext(ledger: ledger)).Issues).Code);
        }

        [Fact]
        public void TamperedJson_ModerateWithoutEvidence_RejectedOnLoad()
        {
            string json = new SystemicDocument("CASE-1", true, null, W151.Acci()).ToJson();
            W151.Code(SystemicErrors.ModerateWithoutEvidence, SystemicDocument.FromJson(json.Replace("\"evidence\":[\"EV-001\"]", "\"evidence\":[]")));
        }
    }

    public class W151_A7_IsolatedControllerTests
    {
        [Fact]
        public void IsolatedController_IsWarning_NotRejected()
        {
            var st = W151.Loop();
            var c = st.AddController("LONE", "孤立控制器", W151.V);
            Assert.True(c.IsSuccess);
            var v = st.Validate();
            Assert.True(v.IsValid);
            var w = Assert.Single(v.Issues, i => i.Severity != SystemicIssueSeverity.Info); // W15.2：另有 Info 级 sys_ref_not_checked
            Assert.Equal(SystemicErrors.IsolatedController, w.Code);
            Assert.Equal("LONE", w.ElementId);
            Assert.True(w.IsWarning);
            Assert.StartsWith("[警告]", w.ToString());
        }

        [Fact]
        public void ControllerWithOnlyFeedback_OrOnlyIncomingAction_NotIsolated()
        {
            var st = W151.Loop();
            W151.Ok(st.AddController("UP", "上级", W151.V));
            W151.Ok(st.AddFeedback("FB2", "报告", "C", "UP", W151.V));
            W151.Ok(st.AddController("SUB", "下级", W151.V));
            W151.Ok(st.AddControlAction("CA2", "指令", "C", "SUB", W151.V));
            Assert.False(st.Validate().Has(SystemicErrors.IsolatedController));
        }
    }

    public class W151_A8_UcaContextTests
    {
        [Fact]
        public void UcaContext_Required_OnAddUpdateAndLoad()
        {
            var st = W151.Loop();
            W151.Code(SystemicErrors.InvalidArgument, st.AddUnsafeControlAction("U2", "u", "CA", UcaType.NotProvided, null, W151.V));
            W151.Code(SystemicErrors.InvalidArgument, st.AddUnsafeControlAction("U2", "u", "CA", UcaType.NotProvided, " \t", W151.V));
            W151.Code(SystemicErrors.UnknownNode, st.AddUnsafeControlAction("U2", "u", "NOPE", UcaType.NotProvided, null, W151.V));
            W151.Code(SystemicErrors.InvalidArgument, st.UpdateUca("U1", context: "  "));
            Assert.Equal("雾中", ((UnsafeControlAction)st.Get("U1")).Context);
            W151.Ok(st.UpdateUca("U1", UcaType.WrongTimingOrOrder, "夜间"));
            var u = (UnsafeControlAction)st.Get("U1");
            Assert.Equal(UcaType.WrongTimingOrOrder, u.Type);
            Assert.Equal("夜间", u.Context);
            W151.Code(SystemicErrors.InvalidArgument, st.UpdateUca("U1", (UcaType)7));
            W151.Code(SystemicErrors.UnknownNode, st.UpdateUca("CA", UcaType.NotProvided));
            string json = new SystemicDocument("CASE-1", true, null, null, st).ToJson();
            W151.Code(SystemicErrors.InvalidArgument, SystemicDocument.FromJson(json.Replace("\"context\":\"夜间\"", "\"context\":\"\"")));
            W151.Code(SystemicErrors.InvalidArgument, SystemicDocument.FromJson(json.Replace(",\"context\":\"夜间\"", string.Empty)));
        }
    }

    public class W151_A9_EditTests
    {
        [Fact]
        public void BowTie_RemoveBarrier_CascadesEscalationAndEdges()
        {
            var m = W151.ChainBowTie();
            W151.Ok(m.AddEscalationFactor("EF1", "ef", "PB1", W151.V));
            var removed = W151.Ok(m.RemoveElement("PB1"));
            Assert.Equal(new[] { "PB1", "EF1" }, removed);
            Assert.Null(m.Get("PB1"));
            Assert.Null(m.Get("EF1"));
            Assert.DoesNotContain(m.Edges, e => e.FromId == "PB1" || e.ToId == "PB1");
            Assert.True(m.Validate().Has(SystemicErrors.OrphanThreat));
            W151.Ok(m.Connect("T1", "TOP"));
            Assert.True(m.Validate().IsValid);
            W151.Code(SystemicErrors.InvalidArgument, m.RemoveElement("TOP"));
            W151.Code(SystemicErrors.UnknownNode, m.RemoveElement("PB1"));
            W151.Ok(m.AddThreat("PB1", "ID 可复用", W151.V));
        }

        [Fact]
        public void BowTie_Disconnect_RebuildsAdjacency()
        {
            var m = W151.ChainBowTie();
            W151.Code(SystemicErrors.Cycle, m.Connect("T1", "T0"));
            W151.Ok(m.Disconnect("T0", "T1"));
            W151.Code(SystemicErrors.UnknownEdge, m.Disconnect("T0", "T1"));
            W151.Ok(m.Connect("T0", "PB1"));   // T0 不再是前驱，可直接连屏障（邻接表已重建）
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void BowTie_Disconnect_StaleAdjacencyWouldFakeCycle()
        {
            var m = W151.ChainBowTie();
            W151.Ok(m.AddBarrier("PB2", "预防2", BowTieElementKind.PreventionBarrier, BarrierState.Failed, W151.V));
            W151.Ok(m.Connect("PB2", "PB1"));
            W151.Code(SystemicErrors.Cycle, m.Connect("PB1", "PB2"));
            W151.Ok(m.Disconnect("PB2", "PB1"));
            W151.Ok(m.Connect("PB1", "PB2")); // 反向连接不再成环
        }

        [Fact]
        public void UpdateElement_RefsApplied()
        {
            var m = W151.ChainBowTie();
            var refs = new SystemicRefs(new[] { "EV-009" }, new[] { "E9" });
            W151.Ok(m.UpdateElement("T1", refs: refs));
            Assert.Equal(new[] { "EV-009" }, m.Get("T1").Refs.EvidenceIds);
            Assert.Equal(new[] { "E9" }, m.Get("T1").Refs.EcfcNodeIds);
        }

        [Fact]
        public void AcciMap_UpdateLevel_SourceSideChecked()
        {
            var m = W151.Ok(AcciMapModel.Create("AM-2", "t", false));
            W151.Ok(m.AddNode("R", "监管", AcciMapLevel.Regulatory, W151.V));
            W151.Ok(m.AddNode("CR", "船员", AcciMapLevel.CrewActs, W151.V));
            W151.Ok(m.Connect("R", "CR"));
            W151.Code(SystemicErrors.LevelDirection, m.UpdateNode("R", level: AcciMapLevel.EquipmentEnvironment)); // 开关关闭：设备→船员上行
            Assert.Equal(AcciMapLevel.Regulatory, m.Get("R").Level);
        }

        [Fact]
        public void BowTie_UpdateElement_ValidatesAndKeepsOldOnFailure()
        {
            var m = W151.ChainBowTie();
            var e = W151.Ok(m.UpdateElement("T1", label: "新标签", strength: W151.S, actorId: "SHIP-A"));
            Assert.Equal("新标签", e.Label);
            Assert.Equal(W151.S, e.Strength);
            Assert.Equal("SHIP-A", e.ActorId);
            W151.Code(SystemicErrors.InvalidArgument, m.UpdateElement("T1", label: " "));
            W151.Code(SystemicErrors.InvalidId, m.UpdateElement("T1", actorId: "bad id"));
            W151.Code(SystemicErrors.StrongWithoutEvidence, m.UpdateElement("T1", refs: SystemicRefs.None));
            Assert.Equal("新标签", m.Get("T1").Label);
            Assert.Equal("SHIP-A", m.Get("T1").ActorId);
            Assert.Equal(new[] { "EV-001" }, m.Get("T1").Refs.EvidenceIds);
            W151.Ok(m.UpdateElement("T1", clearActor: true));
            Assert.Null(m.Get("T1").ActorId);
            W151.Code(SystemicErrors.UnknownNode, m.UpdateElement("NOPE", label: "x"));
        }

        [Fact]
        public void AcciMap_RemoveAndUpdate()
        {
            var m = W151.Acci();
            W151.Ok(m.ConnectInformationFlow("EQ", "R"));
            W151.Ok(m.RemoveNode("R"));
            Assert.Null(m.Get("R"));
            Assert.Empty(m.InformationFlows);
            Assert.DoesNotContain(m.Edges, e => e.FromId == "R" || e.ToId == "R");
            W151.Code(SystemicErrors.UnknownNode, m.RemoveNode("R"));
            W151.Ok(m.UpdateNode("CR", level: AcciMapLevel.Government)); // 只剩 CR→EQ（下行），改层合法
        }

        [Fact]
        public void AcciMap_UpdateLevel_MustKeepIncidentEdgesLegal()
        {
            var m = W151.Acci();
            W151.Code(SystemicErrors.LevelDirection, m.UpdateNode("CR", level: AcciMapLevel.Government)); // R→CR 变成上行
            Assert.Equal(AcciMapLevel.CrewActs, m.Get("CR").Level);
            W151.Ok(m.UpdateNode("R", level: AcciMapLevel.EquipmentEnvironment));                         // R→CR 走“设备与环境→船员”例外，合法
            W151.Ok(m.UpdateNode("R", level: AcciMapLevel.Regulatory));
            W151.Ok(m.UpdateNode("R", level: AcciMapLevel.Company, label: "公司层"));
            Assert.Equal(AcciMapLevel.Company, m.Get("R").Level);
            Assert.Equal("公司层", m.Get("R").Label);
            W151.Code(SystemicErrors.InvalidArgument, m.UpdateNode("R", level: (AcciMapLevel)9));
            W151.Ok(m.Disconnect("G", "R"));
            W151.Code(SystemicErrors.UnknownEdge, m.Disconnect("G", "R"));
            W151.Code(SystemicErrors.LevelDirection, m.Connect("R", "G"));
            W151.Ok(m.Connect("G", "R"));
        }

        [Fact]
        public void Stamp_RemoveController_Cascades_AndRebuildsControlHierarchy()
        {
            var st = W151.Loop();
            W151.Ok(st.AddController("UP", "上级", W151.V));
            W151.Ok(st.AddControlAction("CA-UP", "指令", "UP", "C", W151.V));
            W151.Code(SystemicErrors.Cycle, st.AddControlAction("CA-BACK", "反向", "C", "UP", W151.V));
            var removed = W151.Ok(st.RemoveElement("UP"));
            Assert.Equal(new[] { "UP", "CA-UP" }, removed);
            W151.Ok(st.AddController("UP", "上级", W151.V));
            W151.Ok(st.AddControlAction("CA-BACK", "反向", "C", "UP", W151.V)); // 层级已重建，不再成环

            removed = W151.Ok(st.RemoveElement("C"));
            Assert.Equal(new[] { "C", "CA", "CA-BACK", "FB", "U1" }, removed);
            Assert.Empty(st.ControlActions);
            Assert.Empty(st.Feedback);
            Assert.Empty(st.UnsafeControlActions);
            W151.Code(SystemicErrors.UnknownNode, st.RemoveElement("C"));
        }

        [Fact]
        public void Stamp_RemoveAction_RemovesItsUcas_UpdateElement()
        {
            var st = W151.Loop();
            Assert.Equal(new[] { "CA", "U1" }, W151.Ok(st.RemoveElement("CA")));
            Assert.Null(st.Get("U1"));
            Assert.True(st.Validate().Has(SystemicErrors.EmptyModel));
            var c = W151.Ok(st.UpdateElement("C", label: "新控制器", actorId: "VTS-1"));
            Assert.Equal("新控制器", c.Label);
            W151.Code(SystemicErrors.ModerateWithoutEvidence, st.UpdateElement("C", refs: SystemicRefs.None));
            W151.Code(SystemicErrors.UnknownNode, st.UpdateElement("NOPE"));
        }

        [Fact]
        public void EcfcImport_PureConversion()
        {
            var nodes = new[]
            {
                new EcfcNode("E1", EcfcNodeKind.Event, " 离泊（虚构） ", evidenceIds: new[] { "EV-001" }, actorVesselId: "SHIP-A"),
                new EcfcNode("C1", EcfcNodeKind.Condition, "能见度不良（虚构）", isPresumptive: true, evidenceIds: new[] { "EV-002" }),
                new EcfcNode("C2", EcfcNodeKind.Condition, "无证据条件"),
                new EcfcNode("bad id", EcfcNodeKind.Event, "x"),
                new EcfcNode("E1", EcfcNodeKind.Event, "重复"),
                new EcfcNode("E3", EcfcNodeKind.Event, "  "),
                new EcfcNode("E4", EcfcNodeKind.Event, "主体非法", actorVesselId: "bad actor"),
                null
            };
            var edges = new[]
            {
                new EcfcEdge("X1", "C1", "E1", EcfcEdgeKind.Influence, false),
                new EcfcEdge("X2", "E1", "bad id", EcfcEdgeKind.Sequence, false),
                new EcfcEdge("X3", "C1", "E1", EcfcEdgeKind.Influence, false)
            };
            var r = SystemicEcfcImport.Convert(nodes, edges, "AM-");
            Assert.Equal(new[] { "AM-E1", "AM-C1", "AM-C2", "AM-E4" }, r.Nodes.Select(n => n.Id));
            var e1 = r.Nodes[0];
            Assert.Equal("离泊（虚构）", e1.Label);
            Assert.Equal(EvidenceStrength.Moderate, e1.Strength);
            Assert.Equal(new[] { "EV-001" }, e1.Refs.EvidenceIds);
            Assert.Equal(new[] { "E1" }, e1.Refs.EcfcNodeIds);
            Assert.Equal("SHIP-A", e1.ActorId);
            Assert.Equal("E1", e1.SourceEcfcNodeId);
            Assert.Equal(EvidenceStrength.ToBeVerified, r.Nodes[1].Strength); // 推定
            Assert.Equal(EvidenceStrength.ToBeVerified, r.Nodes[2].Strength); // 无证据
            Assert.Null(r.Nodes[3].ActorId);
            Assert.DoesNotContain(r.Nodes, n => n.Strength == EvidenceStrength.Strong);
            var edge = Assert.Single(r.Edges);
            Assert.Equal("AM-C1", edge.FromId);
            Assert.Equal("AM-E1", edge.ToId);
            Assert.Equal(
                new[] { SystemicErrors.InvalidId, SystemicErrors.DuplicateId, SystemicErrors.InvalidArgument, SystemicErrors.InvalidId },
                r.Skipped.Select(i => i.Code));
            Assert.True(r.Skipped[3].IsWarning);
            W151.ReadOnly(r.Nodes);
            W151.ReadOnly(r.Edges);
            W151.ReadOnly(r.Skipped);

            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            foreach (var d in r.Nodes)
            {
                W151.Ok(am.AddNode(d.Id, d.Label, d.SourceKind == EcfcNodeKind.Event ? AcciMapLevel.CrewActs : AcciMapLevel.EquipmentEnvironment, d.Strength, d.Refs, d.ActorId));
            }

            Assert.Empty(SystemicEcfcImport.Convert(null).Nodes);
        }
    }

    public class W151_A11_TwoPassLoadTests
    {
        [Fact]
        public void EscalationFactorBeforeItsBarrier_Loads()
        {
            var m = W151.ChainBowTie();
            W151.Ok(m.AddEscalationFactor("EF1", "ef", "PB1", W151.V));
            string json = new SystemicDocument("CASE-1", true, m).ToJson();
            int ef = json.IndexOf("{\"id\":\"EF1\"", StringComparison.Ordinal);
            int pb = json.IndexOf("{\"id\":\"PB1\"", StringComparison.Ordinal);
            int efEnd = json.IndexOf('}', json.IndexOf("\"barrierId\"", ef, StringComparison.Ordinal)) + 1;
            string efObj = json.Substring(ef, efEnd - ef);
            string moved = json.Remove(ef - 1, efObj.Length + 1).Insert(pb, efObj + ",");
            Assert.True(moved.IndexOf("{\"id\":\"EF1\"", StringComparison.Ordinal) < moved.IndexOf("{\"id\":\"PB1\"", StringComparison.Ordinal));
            var back = W151.Ok(SystemicDocument.FromJson(moved));
            Assert.Equal("PB1", back.BowTie.Get("EF1").BarrierId);
            Assert.Equal(moved, back.ToJson()); // 两遍加载后恢复文件顺序，往返一致
            W151.Code(SystemicErrors.UnknownNode, SystemicDocument.FromJson(moved.Replace("\"barrierId\":\"PB1\"", "\"barrierId\":\"PB9\"")));
        }
    }

    public class W151_DemoTests
    {
        [Fact]
        public void Demo_StillOnlyIntentionalMissingFeedback_NoWarnings()
        {
            var v = SystemicDemoData.Build().Validate(Fx.DemoContext());
            Assert.Equal(new[] { SystemicErrors.MissingFeedback }, v.Issues.Select(i => i.Code));
            var json = SystemicDemoData.Build().ToJson();
            Assert.StartsWith("{\"schema\":\"mcis.systemic/1\"", json);
            Assert.Equal(json, W151.Ok(SystemicDocument.FromJson(json)).ToJson());
        }

        [Fact]
        public void Demo_NoModerateWithoutEvidence()
        {
            var d = SystemicDemoData.Build();
            var all = d.BowTie.Elements.Cast<SystemicElement>().Concat(d.AcciMap.Nodes).Concat(d.Stamp.AllElements);
            Assert.DoesNotContain(all, e => e.Strength != EvidenceStrength.ToBeVerified && e.Refs.EvidenceIds.Count == 0);
        }
    }
}
