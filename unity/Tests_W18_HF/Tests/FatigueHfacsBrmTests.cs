using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Xunit;

namespace Mcis.W18.HF.Tests
{
    public class FatigueTests
    {
        private static readonly TimeSpan Cn = TimeSpan.FromHours(8);

        private static FatigueIndicators At(int hh, int mm, TimeSpan? shipOffset = null)
        {
            var incident = new DateTimeOffset(2026, 3, 2, hh, mm, 0, Cn);
            var r = FatigueCalculator.Compute(incident, shipOffset, new[] { (incident.AddHours(-20), incident.AddHours(-14)) });
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        [Theory]
        [InlineData(1, 59, false)]
        [InlineData(2, 0, true)]
        [InlineData(5, 59, true)]
        [InlineData(6, 0, false)]
        public void CircadianLow_IsHalfOpen_0200_0600_ShipLocal(int hh, int mm, bool expected)
        {
            Assert.Equal(expected, At(hh, mm).InCircadianLow);
        }

        [Fact]
        public void ShipLocalOffset_OverridesIncidentOffset()
        {
            // 18:00Z = 船时(+8) 02:00 → 低谷；按事发自身 UTC 偏移则不是。
            var incident = new DateTimeOffset(2026, 3, 1, 18, 0, 0, TimeSpan.Zero);
            var sleep = new[] { (incident.AddHours(-10), incident.AddHours(-4)) };
            Assert.True(FatigueCalculator.Compute(incident, Cn, sleep).Value.InCircadianLow);
            Assert.False(FatigueCalculator.Compute(incident, null, sleep).Value.InCircadianLow);
            Assert.Equal(Cn, FatigueCalculator.Compute(incident, Cn, sleep).Value.LocalOffset);
        }

        [Fact]
        public void InvalidOffset_Fails()
        {
            var incident = new DateTimeOffset(2026, 3, 1, 18, 0, 0, TimeSpan.Zero);
            Assert.Equal("hf_invalid_offset", FatigueCalculator.Compute(incident, TimeSpan.FromHours(15), new (DateTimeOffset, DateTimeOffset)[0]).ErrorCode);
        }

        [Fact]
        public void AwakeLast24h_Is24hMinusSleep_AndContinuousAwake()
        {
            var f = At(4, 0);
            Assert.Equal(TimeSpan.FromHours(6), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(18), f.AwakeLast24h);
            Assert.Equal(TimeSpan.FromHours(14), f.ContinuousAwake);
            Assert.False(f.SleepIsRestProxy);
        }

        [Fact]
        public void SleepCrossingLookbackStart_IsClipped_AndSleepAfterIncidentIgnored()
        {
            var incident = new DateTimeOffset(2026, 3, 2, 4, 0, 0, Cn);
            var f = FatigueCalculator.Compute(incident, null, new[]
            {
                (incident.AddHours(-26), incident.AddHours(-22)),
                (incident.AddHours(1), incident.AddHours(5))
            }).Value;
            Assert.Equal(TimeSpan.FromHours(2), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(22), f.AwakeLast24h);
            Assert.Equal(TimeSpan.FromHours(22), f.ContinuousAwake);
        }

        [Fact]
        public void AsleepAtIncident_ContinuousAwakeZero_NoSleep_Null()
        {
            var incident = new DateTimeOffset(2026, 3, 2, 4, 0, 0, Cn);
            Assert.Equal(TimeSpan.Zero, FatigueCalculator.Compute(incident, null, new[] { (incident.AddHours(-1), incident.AddHours(1)) }).Value.ContinuousAwake);
            // B7：空列表视同 null（无排班 → hf_empty_input）；显式 sleepRecordComplete 才表示“确认无睡眠”。
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(incident, null, new (DateTimeOffset, DateTimeOffset)[0]).ErrorCode);
            var none = FatigueCalculator.Compute(incident, null, new (DateTimeOffset, DateTimeOffset)[0], null, null, true).Value;
            Assert.Null(none.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, none.ContinuousAwakeStatus);
            Assert.Equal(TimeSpan.FromHours(24), none.AwakeLast24h);
        }

        [Fact]
        public void NoSleep_UsesScheduleRestAsProxy_NeitherFails()
        {
            var t0 = RestHourTests.T0;
            var s = WorkRestSchedule.FromRest(t0, t0.AddHours(48), new[] { (t0.AddHours(30), t0.AddHours(36)) }).Value;
            var f = FatigueCalculator.Compute(t0.AddHours(40), null, null, s).Value;
            Assert.True(f.SleepIsRestProxy);
            Assert.Equal(TimeSpan.FromHours(6), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(4), f.ContinuousAwake);
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(t0, null, null, null).ErrorCode);
        }

        [Fact]
        public void OverlappingOrInvalidSleep_Fails()
        {
            var t = RestHourTests.T0;
            Assert.Equal("hf_overlap", FatigueCalculator.Compute(t.AddHours(30), null, new[] { (t, t.AddHours(10)), (t.AddHours(1), t.AddHours(2)), (t.AddHours(3), t.AddHours(4)) }).ErrorCode);
            Assert.Equal("hf_invalid_interval", FatigueCalculator.Compute(t.AddHours(30), null, new[] { (t.AddHours(2), t.AddHours(2)) }).ErrorCode);
        }
    }

    public class HfacsTests
    {
        private const string Sha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

        internal static CustodyLedger LedgerWith(params string[] ids)
        {
            var ledger = new CustodyLedger();
            foreach (var id in ids)
            {
                var r = ledger.Register(new EvidenceItem(id, "虚构证据 " + id, "VDR", "调查员甲", RestHourTests.T0, Sha), "调查员甲", RestHourTests.T0);
                Assert.True(r.IsSuccess, r.ErrorMessage);
            }

            return ledger;
        }

        [Fact]
        public void Taxonomy_HasFourLayersPlusExternal_AndConsistentParents()
        {
            var all = HfacsMaTaxonomy.All;
            Assert.Equal(5, all.Select(c => c.Layer).Distinct().Count());
            Assert.Equal(all.Count, all.Select(c => c.Code).Distinct().Count());
            foreach (var c in all.Where(c => c.ParentCode != null))
            {
                var parent = HfacsMaTaxonomy.Get(c.ParentCode);
                Assert.NotNull(parent);
                Assert.Equal(parent.Layer, c.Layer);
            }

            Assert.Equal(HfacsLayer.ExternalFactors, HfacsMaTaxonomy.LayerOf("EF-REG"));
            Assert.Contains(HfacsMaTaxonomy.ChildrenOf("PC-PER"), c => c.Code == "PC-PER-BRM");
            Assert.Null(HfacsMaTaxonomy.LayerOf("XX"));
        }

        [Fact]
        public void Finding_LinksEvidenceAndEcfc_CountsByLayer()
        {
            var a = new HfacsAnalysis("值班驾驶员（虚构）");
            var r = a.AddFinding("F-1", "PC-OPR-PHY", "疲劳", EvidenceStrength.Strong, new[] { "EV-001", " " }, new[] { "ECFC-07" }, LedgerWith("EV-001"));
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Assert.Equal(new[] { "EV-001" }, r.Value.EvidenceIds);
            Assert.Equal(HfacsLayer.Preconditions, r.Value.Layer);
            Assert.True(a.AddFinding("F-2", "UA-ERR-DEC", "未及早避让", EvidenceStrength.Moderate, new[] { "EV-002" }, new[] { "ECFC-03" }).IsSuccess);
            Assert.Equal(0, a.CountByLayer()[HfacsLayer.UnsafeActs]); // D05：草稿不计入
            Assert.True(a.Confirm("F-1", "调查员甲", RestHourTests.T0).IsSuccess);
            Assert.True(a.Confirm("F-2", "调查员甲", RestHourTests.T0).IsSuccess);
            Assert.Equal(1, a.CountByLayer()[HfacsLayer.UnsafeActs]);
            Assert.Equal(0, a.CountByLayer()[HfacsLayer.ExternalFactors]);
            Assert.Single(a.ByLayer(HfacsLayer.Preconditions));
        }

        [Fact]
        public void Finding_ValidationErrors()
        {
            var a = new HfacsAnalysis("虚构");
            Assert.Equal("hf_unknown_category", a.AddFinding("F-1", "ZZ", "x", EvidenceStrength.Strong, new[] { "EV-001" }, new[] { "N1" }).ErrorCode);
            Assert.Equal("hf_non_leaf_category", a.AddFinding("F-1", "UA", "x", EvidenceStrength.Strong, new[] { "EV-001" }, new[] { "N1" }).ErrorCode); // B4
            Assert.Equal("hf_missing_evidence", a.AddFinding("F-1", "UA-ERR-DEC", "x", EvidenceStrength.Strong, new[] { "  " }, new[] { "N1" }).ErrorCode);
            Assert.Equal("hf_missing_ecfc_link", a.AddFinding("F-1", "UA-ERR-DEC", "x", EvidenceStrength.Moderate, new[] { "EV-001" }, null).ErrorCode);
            Assert.Equal("hf_unknown_evidence", a.AddFinding("F-1", "UA-ERR-DEC", "x", EvidenceStrength.Strong, new[] { "EV-009" }, new[] { "N1" }, LedgerWith("EV-001")).ErrorCode);
            Assert.Equal("hf_unknown_evidence", a.AddFinding("F-1", "UA", "x", EvidenceStrength.ToBeVerified, new[] { "EV-009" }, null, LedgerWith("EV-001")).ErrorCode);
            Assert.Equal("hf_invalid_argument", a.AddFinding(null, "UA", "x", EvidenceStrength.ToBeVerified, null, null).ErrorCode);
            Assert.True(a.AddFinding("F-1", "UA", "待核实", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            Assert.Equal("hf_duplicate_finding", a.AddFinding("F-1", "UA", "x", EvidenceStrength.ToBeVerified, null, null).ErrorCode);
        }
    }

    public class BrmTests
    {
        [Fact]
        public void Default_HasItems_SetResult_Summary()
        {
            var c = BrmChecklist.CreateDefault("当值班组（虚构）");
            Assert.Equal(6, c.Items.Count);
            Assert.All(c.Items, i => Assert.Equal(BrmResult.NotAssessed, i.Result));
            var r = c.SetResult("HF-LOOK-01", BrmResult.Fail, new[] { "EV-001" }, "调查员甲", "无专职瞭望", HfacsTests.LedgerWith("EV-001"));
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Assert.Equal(new[] { "EV-001" }, c.Items.Single(i => i.Id == "HF-LOOK-01").EvidenceIds);
            Assert.True(c.SetResult("HF-VTS-01", BrmResult.Pass, null, "调查员甲").IsSuccess);
            var sum = c.Summary();
            Assert.Equal(1, sum[BrmResult.Fail]);
            Assert.Equal(1, sum[BrmResult.Pass]);
            Assert.Equal(4, sum[BrmResult.NotAssessed]);
        }

        [Fact]
        public void ValidationErrors()
        {
            var c = BrmChecklist.CreateDefault("虚构");
            Assert.Equal("hf_duplicate_item", c.AddItem("HF-CAP-01", "重复", "指挥").ErrorCode);
            Assert.Equal("hf_invalid_argument", c.AddItem(null, "x", "y").ErrorCode);
            Assert.Equal("hf_unknown_item", c.SetResult("NOPE", BrmResult.Pass, null, "甲").ErrorCode);
            Assert.Equal("hf_invalid_argument", c.SetResult("HF-CAP-01", BrmResult.Pass, null, " ").ErrorCode);
            Assert.Equal("hf_missing_evidence", c.SetResult("HF-CAP-01", BrmResult.Partial, new string[0], "甲").ErrorCode);
            Assert.Equal("hf_unknown_evidence", c.SetResult("HF-CAP-01", BrmResult.Pass, new[] { "EV-404" }, "甲", null, HfacsTests.LedgerWith("EV-001")).ErrorCode);
            Assert.Equal("hf_invalid_argument", c.SetResult("HF-CAP-01", (BrmResult)99, null, "甲").ErrorCode);
        }
    }

    public class PurityTests
    {
        [Fact]
        public void HumanFactorsAssembly_DoesNotReferenceUnity()
        {
            var asm = typeof(RestHourChecker).Assembly;
            Assert.DoesNotContain(asm.GetReferencedAssemblies(), a => a.Name.StartsWith("UnityEngine", StringComparison.Ordinal));
        }
    }
}
