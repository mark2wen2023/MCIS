using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Systemic;
using Xunit;

namespace Mcis.W15.Sys.Tests
{
    /// <summary>W15.2 / D05：未传来源的引用必须留痕——NotCheckedRefCount + 每种 kind 一条 Info 级 sys_ref_not_checked（21:25 改名）。合成数据（虚构）。</summary>
    public class W152Tests
    {
        private static readonly string Sha = new string('a', 64);

        private static AcciMapModel FourKinds()
        {
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, new SystemicRefs(new[] { "EV-404", "EV-405" }, new[] { "X" }, new[] { "HF-X" }, new[] { "SR-2026-99" })));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.M, new SystemicRefs(new[] { "EV-404" })));
            W151.Ok(am.Connect("A", "B"));
            return am;
        }

        [Fact]
        public void Code_IsSysPrefixed_PerRuling2125()
        {
            // 21:25 裁定：改名 sys_ref_not_checked，所有错误码都带 sys_ 前缀。
            Assert.Equal("sys_ref_not_checked", SystemicErrors.RefNotChecked);
            var codes = typeof(SystemicErrors).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static)
                .Where(f => f.IsLiteral && f.FieldType == typeof(string)).Select(f => (string)f.GetRawConstantValue()).ToList();
            Assert.NotEmpty(codes);
            Assert.All(codes, c => Assert.StartsWith("sys_", c));
            Assert.Equal(codes.Count, codes.Distinct().Count());
        }

        [Fact]
        public void NoSource_NoError_ButInfoAndPositiveCount()
        {
            // 21:25 裁定对 EachKindCheckedOnlyWhenProvided 的新口径：未提供来源 → 不报 Error，但必须有 Info 级 sys_ref_not_checked，且 NotCheckedRefCount > 0。
            var v = FourKinds().Validate(new SystemicRefContext());
            Assert.DoesNotContain(v.Issues, i => i.Severity == SystemicIssueSeverity.Error);
            Assert.Contains(v.Issues, i => i.Severity == SystemicIssueSeverity.Info && i.Code == "sys_ref_not_checked");
            Assert.True(v.NotCheckedRefCount > 0);
        }

        [Fact]
        public void NoSources_OneInfoPerKind_CountIsReferenceOccurrences_StillValid()
        {
            var v = FourKinds().Validate(new SystemicRefContext());
            Assert.True(v.IsValid);
            Assert.Empty(v.Errors);
            Assert.Empty(v.Warnings);
            Assert.Equal(6, v.NotCheckedRefCount); // 3 证据 + 1 ECFC + 1 HFACS + 1 建议
            var info = v.Of(SystemicErrors.RefNotChecked);
            Assert.Equal(4, info.Count);
            Assert.All(info, i => Assert.Equal(SystemicIssueSeverity.Info, i.Severity));
            Assert.Equal(new[] { SystemicRefKinds.Evidence, SystemicRefKinds.Ecfc, SystemicRefKinds.Hfacs, SystemicRefKinds.Recommendation }, info.Select(i => i.ElementId));
            Assert.Contains("3", info[0].Message);
            Assert.Contains("未核对", info[0].Message);
            Assert.Equal(4, v.Infos.Count);
            Assert.True(v.ToResult().IsSuccess);
            Assert.False(info[0].IsWarning);
        }

        [Fact]
        public void PerKindCounts_Exposed()
        {
            var v = FourKinds().Validate(new SystemicRefContext());
            Assert.Equal(3, v.NotCheckedByKind[SystemicRefKinds.Evidence]);
            Assert.Equal(1, v.NotCheckedByKind[SystemicRefKinds.Recommendation]);
            Assert.False(v.NotCheckedByKind.ContainsKey(SystemicRefKinds.Statement));
            Assert.Throws<NotSupportedException>(() => ((IDictionary<string, int>)v.NotCheckedByKind).Clear());
        }

        [Fact]
        public void NullContext_TreatedAsNoSources()
        {
            var v = FourKinds().Validate();
            Assert.Equal(6, v.NotCheckedRefCount);
            Assert.Equal(4, v.Of(SystemicErrors.RefNotChecked).Count);
            Assert.DoesNotContain(v.Issues, i => i.Code == SystemicErrors.UnregisteredRefKind); // 原行为不变
        }

        [Fact]
        public void PartialSources_OnlyMissingKindsTallied()
        {
            var ledger = new CustodyLedger();
            Assert.True(ledger.Register(new EvidenceItem("EV-404", "虚构", "VDR", "甲", DateTimeOffset.UnixEpoch, Sha), "甲", DateTimeOffset.UnixEpoch).IsSuccess);
            var v = FourKinds().Validate(new SystemicRefContext(ledger, knownEcfcNodeIds: new[] { "X" }));
            Assert.Equal(2, v.NotCheckedRefCount); // HFACS 1 + 建议 1
            Assert.Equal(new[] { SystemicRefKinds.Hfacs, SystemicRefKinds.Recommendation }, v.Of(SystemicErrors.RefNotChecked).Select(i => i.ElementId));
            Assert.Contains(v.Errors, i => i.Code == SystemicErrors.UnknownEvidence); // EV-405 未登记：已核对、报错
        }

        [Fact]
        public void AllSources_NoTrace()
        {
            var ledger = new CustodyLedger();
            foreach (var id in new[] { "EV-404", "EV-405" })
            {
                Assert.True(ledger.Register(new EvidenceItem(id, "虚构", "VDR", "甲", DateTimeOffset.UnixEpoch, Sha), "甲", DateTimeOffset.UnixEpoch).IsSuccess);
            }

            var v = FourKinds().Validate(new SystemicRefContext(ledger, new HfacsAnalysis("虚构"), new Mcis.Domain.Recommendations.SafetyRecommendationBoard(new InMemoryInvestigationAuditSink()), new[] { "X" }));
            Assert.Equal(0, v.NotCheckedRefCount);
            Assert.Empty(v.Of(SystemicErrors.RefNotChecked));
            Assert.Empty(v.Infos);
            Assert.Empty(v.NotCheckedByKind);
        }

        [Fact]
        public void ExtensionKind_Unregistered_WarningKept_PlusInfoSummary_RegisteredIsChecked()
        {
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            var refs = new SystemicRefs(new[] { new SystemicRef(SystemicRefKinds.Statement, "IR-06"), new SystemicRef(SystemicRefKinds.Statement, "IR-07"), new SystemicRef(SystemicRefKinds.Evidence, "EV-001") });
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, refs));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.V));
            W151.Ok(am.Connect("A", "B"));
            var v = am.Validate(new SystemicRefContext());
            Assert.Single(v.Of(SystemicErrors.UnregisteredRefKind));
            Assert.Equal(new[] { SystemicRefKinds.Evidence, SystemicRefKinds.Statement }, v.Of(SystemicErrors.RefNotChecked).Select(i => i.ElementId));
            Assert.Equal(3, v.NotCheckedRefCount);

            var ctx = new SystemicRefContext();
            W151.Ok(ctx.RegisterValidator(SystemicRefKinds.Statement, id => id == "IR-06"));
            var v2 = am.Validate(ctx);
            Assert.Equal(1, v2.NotCheckedRefCount); // 只剩证据
            Assert.Contains(v2.Errors, i => i.Code == SystemicErrors.UnknownRef);
        }

        [Fact]
        public void Order_BuiltInFirst_ThenExtensionOrdinal_EvenIfNameSortsEarlier()
        {
            var am = W151.Ok(AcciMapModel.Create("AM-1", "t"));
            var refs = new SystemicRefs(new[] { new SystemicRef(SystemicRefKinds.Statement, "IR-06"), new SystemicRef(SystemicRefKinds.ColregCheck, "R6"), new SystemicRef(SystemicRefKinds.Recommendation, "SR-2026-01"), new SystemicRef(SystemicRefKinds.Evidence, "EV-001") });
            W151.Ok(am.AddNode("A", "a", AcciMapLevel.Company, W151.M, refs));
            W151.Ok(am.AddNode("B", "b", AcciMapLevel.Company, W151.V));
            W151.Ok(am.Connect("A", "B"));
            Assert.Equal(new[] { SystemicRefKinds.Evidence, SystemicRefKinds.Recommendation, SystemicRefKinds.ColregCheck, SystemicRefKinds.Statement },
                am.Validate().Of(SystemicErrors.RefNotChecked).Select(i => i.ElementId));
        }

        [Fact]
        public void Document_MergesModels_OneInfoPerKind()
        {
            var d = new SystemicDocument("CASE-2026-X1", true, W151.ChainBowTie(), FourKinds());
            var v = d.Validate(new SystemicRefContext());
            var info = v.Of(SystemicErrors.RefNotChecked);
            Assert.Equal(4, info.Count);
            Assert.Equal(5 + 3, v.NotCheckedByKind[SystemicRefKinds.Evidence]);
            Assert.Equal(8 + 3, v.NotCheckedRefCount);
            Assert.Contains("8", info.Single(i => i.ElementId == SystemicRefKinds.Evidence).Message);
            Assert.True(v.IsValid);
        }

        [Fact]
        public void BowTieAndStamp_AlsoTally()
        {
            Assert.Equal(5, W151.ChainBowTie().Validate().NotCheckedRefCount);
            var st = W151.Loop().Validate(new SystemicRefContext());
            Assert.Equal(5, st.NotCheckedRefCount); // 5 个元素各引用 EV-001
            Assert.Equal(st.Issues.Count(i => i.Code == SystemicErrors.RefNotChecked), st.NotCheckedByKind.Count);
            Assert.Equal(st.NotCheckedByKind.Values.Sum(), st.NotCheckedRefCount);
        }

        [Fact]
        public void LegacyConstructor_NoTally_ZeroCount()
        {
            var v = new SystemicValidation(new[] { new SystemicIssue("sys_x", "A", "m", SystemicIssueSeverity.Warning) });
            Assert.Equal(0, v.NotCheckedRefCount);
            Assert.Empty(v.NotCheckedByKind);
            Assert.Empty(v.Infos);
        }
    }
}
