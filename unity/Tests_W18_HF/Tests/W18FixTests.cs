using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.W18.HF.Tests.RestHourTests;

namespace Mcis.W18.HF.Tests
{
    /// <summary>W18 修复：D01–D05 + 裁定 B1–B7。全部为合成数据（虚构），不引用任何真实报告。</summary>
    public class W18FatigueFixTests
    {
        private static readonly DateTimeOffset Inc = H(200);
        private static readonly TimeSpan Ship = TimeSpan.FromHours(8);

        private static FatigueIndicators Ok(Mcis.Core.Result<FatigueIndicators> r)
        {
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        // ---------- D01 ----------

        [Fact]
        public void D01_ContinuousAwakeBeyond24h_IsMeasured()
        {
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-38), Inc.AddHours(-30)) }));
            Assert.Equal(TimeSpan.FromHours(30), f.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.Measured, f.ContinuousAwakeStatus);
            Assert.Equal(TimeSpan.FromHours(24), f.AwakeLast24h);
        }

        [Fact]
        public void D01_UpTo7Days_Measured_Beyond7Days_NoSleepWithinLimit()
        {
            var a = Ok(FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-170), Inc.AddHours(-160)) }));
            Assert.Equal(TimeSpan.FromHours(160), a.ContinuousAwake);
            var exact = Ok(FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-170), Inc.AddDays(-7)) }));
            Assert.Equal(TimeSpan.FromDays(7), exact.ContinuousAwake);
            var b = Ok(FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-180), Inc.AddHours(-169)) }));
            Assert.Null(b.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, b.ContinuousAwakeStatus);
            Assert.Contains(">7d", b.ContinuousAwakeNote);
        }

        [Fact]
        public void D01_LimitConfigurable()
        {
            var r = new FatigueRules { MaxContinuousAwakeLookback = TimeSpan.FromHours(48) };
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-60), Inc.AddHours(-50)) }, null, r));
            Assert.Null(f.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, f.ContinuousAwakeStatus);
            Assert.Equal("hf_invalid_rules", FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-6), Inc.AddHours(-1)) }, null, new FatigueRules { MaxContinuousAwakeLookback = TimeSpan.Zero }).ErrorCode);
        }

        [Fact]
        public void D01_ProxyWithoutSleepInShortRecord_InsufficientCoverage()
        {
            var s = WorkRestSchedule.FromWork(Inc.AddHours(-12), Inc, new[] { (Inc.AddHours(-12), Inc) }).Value;
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, null, s));
            Assert.Null(f.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.InsufficientCoverage, f.ContinuousAwakeStatus);
        }

        [Fact]
        public void D01_ProxyRecordEndsBeforeIncident_InsufficientCoverage()
        {
            var s = WorkRestSchedule.FromRest(Inc.AddHours(-30), Inc.AddHours(-2), new[] { (Inc.AddHours(-10), Inc.AddHours(-4)) }).Value;
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, null, s));
            Assert.Null(f.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.InsufficientCoverage, f.ContinuousAwakeStatus);
            Assert.Equal(Inc.AddHours(-2), f.CoverageEnd);
            Assert.Equal(TimeSpan.FromHours(2), f.UnknownLast24h);
        }

        // ---------- D02 ----------

        [Fact]
        public void D02_SubMinuteOffset_ReturnsInvalidOffset()
        {
            var ex = Record.Exception(() => FatigueCalculator.Compute(Inc, new TimeSpan(8, 0, 30), new[] { (Inc.AddHours(-9), Inc.AddHours(-1)) }));
            Assert.Null(ex);
            Assert.Equal("hf_invalid_offset", FatigueCalculator.Compute(Inc, new TimeSpan(8, 0, 30), new[] { (Inc.AddHours(-9), Inc.AddHours(-1)) }).ErrorCode);
            Assert.Equal("hf_invalid_offset", FatigueCalculator.Compute(Inc, TimeSpan.FromTicks(TimeSpan.FromHours(8).Ticks + 1), new[] { (Inc.AddHours(-9), Inc.AddHours(-1)) }).ErrorCode);
        }

        // ---------- D03 ----------

        [Fact]
        public void D03_ProxyShortRecord_OutsideTimeIsUnknown_WithCoverageFlags()
        {
            var s = WorkRestSchedule.FromRest(Inc.AddHours(-12), Inc, new[] { (Inc.AddHours(-10), Inc.AddHours(-6)) }).Value;
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, null, s));
            Assert.Equal(TimeSpan.FromHours(8), f.AwakeLast24h);
            Assert.Equal(TimeSpan.FromHours(4), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(12), f.UnknownLast24h);
            Assert.Equal(Inc.AddHours(-12), f.CoverageStart);
            Assert.Equal(Inc, f.CoverageEnd);
            Assert.True(f.Truncated);
            Assert.True(f.RestLast7dTruncated);
            Assert.Equal(TimeSpan.FromHours(4), f.RestLast7d);
            Assert.Equal(TimeSpan.FromHours(6), f.ContinuousAwake);
        }

        [Fact]
        public void D03_FullCoverage_NotTruncated()
        {
            var rest = Enumerable.Range(0, 9).Select(d => (H(d * 24 + 1), H(d * 24 + 12))).ToArray();
            var s = WorkRestSchedule.FromRest(T0, H(9 * 24), rest).Value;
            var f = Ok(FatigueCalculator.Compute(H(8 * 24 + 14), Ship, null, s));
            Assert.False(f.Truncated);
            Assert.False(f.RestLast7dTruncated);
            Assert.Equal(TimeSpan.Zero, f.UnknownLast24h);
            Assert.Equal(TimeSpan.FromHours(77), f.RestLast7d);
            Assert.Equal(TimeSpan.FromHours(2), f.ContinuousAwake);
        }

        [Fact]
        public void D03_ExplicitSleep_AssumedComplete_FullCoverage()
        {
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, new[] { (Inc.AddHours(-20), Inc.AddHours(-12)) }));
            Assert.False(f.Truncated);
            Assert.Equal(Inc.AddHours(-24), f.CoverageStart);
            Assert.Equal(Inc, f.CoverageEnd);
            Assert.Equal(TimeSpan.FromHours(16), f.AwakeLast24h);
        }

        // ---------- B7 ----------

        [Fact]
        public void B7_EmptySleepList_TreatedAsNull()
        {
            var s = WorkRestSchedule.FromRest(Inc.AddHours(-48), Inc, new[] { (Inc.AddHours(-20), Inc.AddHours(-12)) }).Value;
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, new (DateTimeOffset, DateTimeOffset)[0], s));
            Assert.True(f.SleepIsRestProxy);
            Assert.Equal(TimeSpan.FromHours(8), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(12), f.ContinuousAwake);
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(Inc, Ship, new (DateTimeOffset, DateTimeOffset)[0]).ErrorCode);
        }

        [Fact]
        public void B7_EmptySleepList_WithSleepRecordComplete_MeansNoSleep()
        {
            var f = Ok(FatigueCalculator.Compute(Inc, Ship, new (DateTimeOffset, DateTimeOffset)[0], null, null, sleepRecordComplete: true));
            Assert.False(f.SleepIsRestProxy);
            Assert.Equal(TimeSpan.FromHours(24), f.AwakeLast24h);
            Assert.Null(f.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, f.ContinuousAwakeStatus);
        }
    }

    public class W18HfacsFixTests
    {
        private static readonly string[] Ev = { "EV-001" };
        private static readonly string[] Node = { "ECFC-07" };
        private static readonly DateTimeOffset U = new DateTimeOffset(2026, 3, 5, 10, 0, 0, TimeSpan.FromHours(8));

        private sealed class BoomSink : IInvestigationAuditSink
        {
            public void Append(InvestigationAuditEntry entry) { throw new System.IO.IOException("audit down (simulated)"); }
        }

        // ---------- D04 ----------

        [Fact]
        public void D04_UndefinedStrength_Rejected()
        {
            var a = new HfacsAnalysis("虚构");
            Assert.Equal("hf_invalid_argument", a.AddFinding("F1", "UA-ERR-DEC", "d", (EvidenceStrength)99, Ev, Node).ErrorCode);
            Assert.Equal("hf_invalid_argument", a.AddFinding("F1", "UA-ERR-DEC", "d", (EvidenceStrength)(-1), Ev, Node).ErrorCode);
            Assert.Empty(a.Findings);
        }

        // ---------- D05 ----------

        [Fact]
        public void D05_NewFinding_IsDraft_NotCountedUntilConfirmed()
        {
            var a = new HfacsAnalysis("虚构二副");
            var f = a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node).Value;
            Assert.Equal(HfacsReviewStatus.Draft, f.ReviewStatus);
            Assert.Equal(HfacsOrigin.Agent, f.Origin);
            Assert.Equal(0, a.CountByLayer()[HfacsLayer.UnsafeActs]);
            Assert.Empty(a.ByLayer(HfacsLayer.UnsafeActs));
            Assert.Equal(1, a.CountByLayerIncludingDrafts()[HfacsLayer.UnsafeActs]);
            Assert.Single(a.ByLayerIncludingDrafts(HfacsLayer.UnsafeActs));
            Assert.Single(a.Pending());
            Assert.Empty(a.Audit.Logged());
        }

        [Fact]
        public void D05_Confirm_SetsReviewer_AndAudits()
        {
            var a = new HfacsAnalysis("虚构二副");
            a.AddFinding("F1", "UA-ERR-DEC", "未及早避让", EvidenceStrength.Strong, Ev, Node);
            var r = a.Confirm("F1", "调查员甲", U, "核对 VDR（虚构）");
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Assert.Equal(HfacsReviewStatus.Confirmed, r.Value.ReviewStatus);
            Assert.Equal("调查员甲", r.Value.ReviewedBy);
            Assert.Equal(U, r.Value.ReviewedUtc);
            Assert.Equal(HfacsReviewStatus.Confirmed, a.Findings[0].ReviewStatus);
            Assert.Equal(1, a.CountByLayer()[HfacsLayer.UnsafeActs]);
            var e = Assert.Single(a.Audit.Logged());
            Assert.Equal("hf.finding.confirm", e.Action);
            Assert.Equal(HfacsAnalysis.ActionConfirm, e.Action);
            Assert.Equal("HumanFactors", e.Category);
            Assert.Equal("调查员甲", e.OperatorName);
            Assert.Empty(a.Pending());
        }

        [Fact]
        public void D05_Reject_RequiresNote_ExcludedEverywhere()
        {
            var a = new HfacsAnalysis("虚构二副");
            a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node);
            Assert.Equal("hf_invalid_argument", a.Reject("F1", "调查员甲", U, " ").ErrorCode);
            Assert.Equal("hf_invalid_argument", a.Reject("F1", "调查员甲", U, null).ErrorCode);
            Assert.Empty(a.Audit.Logged());
            var r = a.Reject("F1", "调查员甲", U, "证据不支持（虚构）");
            Assert.True(r.IsSuccess);
            Assert.Equal(HfacsReviewStatus.Rejected, a.Findings[0].ReviewStatus);
            Assert.Equal("证据不支持（虚构）", a.Findings[0].ReviewNote);
            Assert.Equal(0, a.CountByLayer()[HfacsLayer.UnsafeActs]);
            Assert.Equal(0, a.CountByLayerIncludingDrafts()[HfacsLayer.UnsafeActs]);
            Assert.Equal("hf.finding.reject", a.Audit.Logged().Single().Action);
        }

        [Fact]
        public void D05_OnlyDraftCanBeReviewed_AndErrors()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var a = new HfacsAnalysis("虚构", sink);
            Assert.Same(sink, a.Audit);
            a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node, origin: HfacsOrigin.Investigator);
            Assert.Equal(HfacsOrigin.Investigator, a.Findings[0].Origin);
            Assert.Equal("hf_unknown_finding", a.Confirm("F9", "甲", U).ErrorCode);
            Assert.Equal("hf_invalid_argument", a.Confirm("F1", " ", U).ErrorCode);
            Assert.True(a.Confirm("F1", "甲", U).IsSuccess);
            Assert.Equal("hf_invalid_state", a.Confirm("F1", "甲", U).ErrorCode);
            Assert.Equal("hf_invalid_state", a.Reject("F1", "甲", U, "x").ErrorCode);
            Assert.Single(sink.Entries);
        }

        [Fact]
        public void D05_AuditFailure_LeavesDraft()
        {
            var a = new HfacsAnalysis("虚构", new BoomSink());
            a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node);
            Assert.Throws<System.IO.IOException>(() => a.Confirm("F1", "甲", U));
            Assert.Equal(HfacsReviewStatus.Draft, a.Findings[0].ReviewStatus);
            Assert.Null(a.Findings[0].ReviewedBy);
        }

        // ---------- B3 ----------

        private static CustodyLedger Ledger(out string badId, out string reviewId)
        {
            var ledger = HfacsTests.LedgerWith("EV-001", "EV-002", "EV-003");
            badId = "EV-002";
            reviewId = "EV-003";
            Assert.True(ledger.Verify(badId, "甲", RestHourTests.T0.AddHours(1), new string('b', 64)).IsSuccess);
            Assert.True(ledger.MarkNeedsReview(reviewId, "甲", RestHourTests.T0.AddHours(1), "虚构：来源存疑").IsSuccess);
            return ledger;
        }

        [Fact]
        public void B3_Strong_RejectsMismatchOrNeedsReviewEvidence()
        {
            var ledger = Ledger(out string bad, out string review);
            var a = new HfacsAnalysis("虚构");
            Assert.Equal("hf_evidence_unreliable", a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { "EV-001", bad }, Node, ledger).ErrorCode);
            Assert.Equal("hf_evidence_unreliable", a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { review }, Node, ledger).ErrorCode);
            Assert.Empty(a.Findings);
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { "EV-001" }, Node, ledger).IsSuccess);
            Assert.Empty(a.Findings[0].EvidenceWarnings);
        }

        [Fact]
        public void B3_Moderate_AllowedWithWarnings()
        {
            var ledger = Ledger(out string bad, out string review);
            var a = new HfacsAnalysis("虚构");
            var r = a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Moderate, new[] { "EV-001", bad, review }, Node, ledger);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Assert.Equal(new[] { bad, review }, r.Value.EvidenceWarnings);
        }

        [Fact]
        public void B3_ConfirmWithLedger_RechecksStrongEvidence()
        {
            var ledger = HfacsTests.LedgerWith("EV-001");
            var a = new HfacsAnalysis("虚构");
            a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { "EV-001" }, Node, ledger);
            ledger.MarkNeedsReview("EV-001", "甲", RestHourTests.T0.AddHours(2), "虚构：复核");
            Assert.Equal("hf_evidence_unreliable", a.Confirm("F1", "甲", U, null, ledger).ErrorCode);
            Assert.Equal(HfacsReviewStatus.Draft, a.Findings[0].ReviewStatus);
            Assert.Empty(a.Audit.Logged());
        }

        // ---------- B4 ----------

        [Fact]
        public void B4_StrongModerate_RequireLeafCode_WeakMayUseGroup()
        {
            var a = new HfacsAnalysis("虚构");
            Assert.Equal("hf_non_leaf_category", a.AddFinding("F1", "UA", "d", EvidenceStrength.Strong, Ev, Node).ErrorCode);
            Assert.Equal("hf_non_leaf_category", a.AddFinding("F1", "PC-OPR", "d", EvidenceStrength.Moderate, Ev, Node).ErrorCode);
            Assert.Empty(a.Findings);
            Assert.True(a.AddFinding("F1", "PC-OPR", "假设（虚构）", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            Assert.True(a.AddFinding("F2", "OI-PROC", "d", EvidenceStrength.Strong, Ev, Node).IsSuccess); // OI-PROC 是叶子
        }
    }

    public class W18BrmFixTests
    {
        private static readonly DateTimeOffset U = new DateTimeOffset(2026, 3, 5, 10, 0, 0, TimeSpan.FromHours(8));

        [Fact]
        public void B6_SetResult_CreatesDraftVersion_ConfirmAudits()
        {
            var c = BrmChecklist.CreateDefault("虚构班组");
            Assert.True(c.SetResult("HF-LOOK-01", BrmResult.Fail, new[] { "EV-001" }, "智能体（虚构）").IsSuccess);
            BrmItem item = c.Items[1];
            Assert.Equal(BrmReviewStatus.Draft, item.ReviewStatus);
            Assert.Equal(1, item.Version);
            Assert.Equal(1, c.ConfirmedSummary()[BrmResult.NotAssessed] - 5);
            Assert.Equal(1, c.Summary()[BrmResult.Fail]); // 含草稿视图

            var r = c.ConfirmResult("HF-LOOK-01", "调查员甲", U, "核对（虚构）");
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Assert.Equal(BrmReviewStatus.Confirmed, c.Items[1].ReviewStatus);
            Assert.Equal("调查员甲", c.Items[1].ReviewedBy);
            Assert.Equal(1, c.ConfirmedSummary()[BrmResult.Fail]);
            var e = Assert.Single(c.Audit.Logged());
            Assert.Equal("hf.brm.confirm", e.Action);
            Assert.Equal("HumanFactors", e.Category);
        }

        [Fact]
        public void B6_Reassess_KeepsHistory_ConfirmedStaysUntilNewConfirmed()
        {
            var c = BrmChecklist.CreateDefault("虚构班组");
            c.SetResult("HF-ARPA-01", BrmResult.Partial, new[] { "EV-001" }, "甲");
            c.ConfirmResult("HF-ARPA-01", "调查员甲", U);
            c.SetResult("HF-ARPA-01", BrmResult.NotApplicable, null, "乙", "虚构：未装 ARPA");
            var h = c.History("HF-ARPA-01");
            Assert.Equal(new[] { 0, 1, 2 }, h.Select(x => x.Version));
            Assert.Equal(BrmResult.NotAssessed, h[0].Result);
            Assert.Equal(BrmReviewStatus.Confirmed, h[1].ReviewStatus);
            Assert.Equal(BrmReviewStatus.Draft, h[2].ReviewStatus);
            Assert.Equal(BrmResult.NotApplicable, c.Items[2].Result);
            Assert.Equal(1, c.ConfirmedSummary()[BrmResult.Partial]);
            Assert.Equal(1, c.Summary()[BrmResult.NotApplicable]);
        }

        [Fact]
        public void B6_Reject_RequiresNote_FallsBackInSummary()
        {
            var c = BrmChecklist.CreateDefault("虚构班组");
            c.SetResult("HF-VTS-01", BrmResult.Pass, null, "智能体（虚构）");
            Assert.Equal("hf_invalid_argument", c.RejectResult("HF-VTS-01", "调查员甲", U, "").ErrorCode);
            Assert.True(c.RejectResult("HF-VTS-01", "调查员甲", U, "虚构：VTS 录音不符").IsSuccess);
            Assert.Equal(BrmReviewStatus.Rejected, c.Items[4].ReviewStatus);
            Assert.Equal(0, c.Summary()[BrmResult.Pass]);
            Assert.Equal(6, c.Summary()[BrmResult.NotAssessed]);
            Assert.Equal("hf.brm.reject", c.Audit.Logged().Single().Action);
            Assert.Equal("hf_invalid_state", c.ConfirmResult("HF-VTS-01", "调查员甲", U).ErrorCode);
            Assert.Equal("hf_invalid_state", c.ConfirmResult("HF-CAP-01", "调查员甲", U).ErrorCode); // 未评估，无草稿
            Assert.Equal("hf_unknown_item", c.ConfirmResult("HF-NOPE", "调查员甲", U).ErrorCode);
            Assert.Equal("hf_invalid_argument", c.ConfirmResult("HF-CAP-01", " ", U).ErrorCode);
        }
    }

    public class W18RestFixTests
    {
        private static RestHourReport Check(WorkRestSchedule s, RestHourRules rules = null)
        {
            var r = new RestHourChecker(rules ?? new RestHourRules { ApplyWorkHourLimits = false }).Check(s);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        private static WorkRestSchedule Rest(double hours, params (double a, double b)[] p)
        {
            return WorkRestSchedule.FromRest(T0, H(hours), p.Select(x => (H(x.a), H(x.b)))).Value;
        }

        // ---------- B1 ----------

        [Fact]
        public void B1_FullSegments_WindowCutDoesNotShortenSegment()
        {
            // 21:25 复裁：拆分规则按完整休息段判定。[24,30) 等恰 6h 的段即使被窗口截短也按 6h 计 → 不报拆分违规。
            var s = Rest(96, (12, 18), (24, 30), (36, 41), (46, 51), (52, 60), (70, 80), (88, 96));
            var rep = Check(s);
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.LongestRest || v.Rule == RestRule.RestSplit);
        }

        [Fact]
        public void B1_Daily6Plus4_IsCompliant_PerRuling()
        {
            // 21:25 复裁（方案 C 规范化）：每天 6h+4h 判合规（总量规则严格任意窗口仍满足 10h）。
            var rest = new List<(double, double)>();
            for (int d = 0; d < 4; d++) { rest.Add((d * 24 + 1, d * 24 + 7)); rest.Add((d * 24 + 13, d * 24 + 17)); }
            var rep = Check(Rest(96, rest.ToArray()));
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.Rest24h || v.Rule == RestRule.LongestRest || v.Rule == RestRule.RestSplit);
            W18_1Tests.AssertMatchesBruteForce(W18_1Tests.Run(96, rest.ToArray()), 96, rest);
        }

        // ---------- B2 ----------

        [Fact]
        public void B2_UnknownDecides_ReportedAsInsufficientData()
        {
            var s = WorkRestSchedule.Create(T0, H(24), new[]
            {
                new DutyInterval(H(0), H(8), DutyKind.Rest),
                new DutyInterval(H(16), H(24), DutyKind.Work)
            }).Value;
            var rep = Check(s, new RestHourRules());
            Assert.Empty(rep.Violations);
            var d = Assert.Single(rep.InsufficientData, x => x.Rule == RestRule.Rest24h);
            Assert.Equal(TimeSpan.FromHours(8), d.Actual);
            Assert.False(rep.IsCompliant);
            Assert.False(rep.IsConclusive);
            Assert.False(rep.HasViolations);
        }

        [Fact]
        public void B2_ViolationEvenIfUnknownIsRest_IsViolation_NotDuplicated()
        {
            var s = WorkRestSchedule.Create(T0, H(24), new[]
            {
                new DutyInterval(H(0), H(4), DutyKind.Rest),
                new DutyInterval(H(6), H(24), DutyKind.Work)
            }).Value;
            var rep = Check(s);
            var v = Assert.Single(rep.Violations, x => x.Rule == RestRule.Rest24h);
            Assert.Equal(TimeSpan.FromHours(6), v.Actual); // Unknown 全当休息仍只有 6h
            Assert.DoesNotContain(rep.InsufficientData, x => x.Rule == RestRule.Rest24h);
            Assert.True(rep.HasViolations);
        }

        [Fact]
        public void B2_SameRule_ViolationEarly_InsufficientLater_BothReported()
        {
            // 前段确定违规（4h 休息）；后段含 16h 未标注，结论取决于 Unknown → 另列数据不足，不被前段违规吞掉。
            var s = WorkRestSchedule.Create(T0, H(104), new[]
            {
                new DutyInterval(H(0), H(4), DutyKind.Rest),
                new DutyInterval(H(4), H(24), DutyKind.Work),
                new DutyInterval(H(24), H(34), DutyKind.Rest),
                new DutyInterval(H(34), H(48), DutyKind.Work),
                new DutyInterval(H(48), H(58), DutyKind.Rest),
                new DutyInterval(H(58), H(72), DutyKind.Work),
                new DutyInterval(H(72), H(80), DutyKind.Rest),
                new DutyInterval(H(96), H(104), DutyKind.Rest)
            }).Value;
            var rep = Check(s);
            Assert.Contains(rep.Violations, v => v.Rule == RestRule.Rest24h && v.WindowStart < H(24));
            Assert.Contains(rep.InsufficientData, v => v.Rule == RestRule.Rest24h && v.WindowStart > H(48));
        }

        [Fact]
        public void B2_NoUnknown_IsConclusive()
        {
            var rep = Check(Rest(24, (1, 7), (13, 17)));
            Assert.True(rep.IsConclusive);
            Assert.True(rep.IsCompliant);
            Assert.Empty(rep.InsufficientData);
        }

        // ---------- B5 ----------

        [Fact]
        public void B5_WorkKind_DutyInterval()
        {
            var w = new DutyInterval(H(0), H(1), WorkKind.OtherWork);
            Assert.Equal(DutyKind.Work, w.Kind);
            Assert.Equal(WorkKind.OtherWork, w.WorkKind);
            Assert.Equal(DutyKind.Rest, new DutyInterval(H(0), H(1), WorkKind.Rest).Kind);
            Assert.Equal(WorkKind.Watch, new DutyInterval(H(0), H(1), DutyKind.Work).WorkKind);
            Assert.Equal(WorkKind.Rest, new DutyInterval(H(0), H(1), DutyKind.Rest).WorkKind);
        }

        [Fact]
        public void B5_DailyTotals_ByShipCalendarDay()
        {
            // 记录 T0(UTC 00:00 = 船时 08:00) 起 48h；船时 +8。
            var s = WorkRestSchedule.Create(T0, H(48), new[]
            {
                new DutyInterval(H(0), H(4), WorkKind.Watch),
                new DutyInterval(H(4), H(6), WorkKind.OtherWork),
                new DutyInterval(H(6), H(14), WorkKind.Rest),   // 船时 14:00–22:00
                new DutyInterval(H(14), H(20), WorkKind.Rest),  // 船时 22:00–次日 04:00（跨日）
                new DutyInterval(H(20), H(24), WorkKind.Watch),
                new DutyInterval(H(24), H(48), WorkKind.Rest)
            }).Value;
            Assert.Equal(new[] { WorkKind.Watch, WorkKind.OtherWork, WorkKind.Watch }, s.WorkPeriods.Select(w => w.WorkKind)); // 不跨类合并
            var r = s.DailyTotals(TimeSpan.FromHours(8));
            Assert.True(r.IsSuccess, r.ErrorMessage);
            var days = r.Value;
            Assert.Equal(3, days.Count);
            Assert.Equal(new DateTime(2026, 3, 1), days[0].LocalDate);
            Assert.True(days[0].IsPartialDay);
            Assert.Equal(TimeSpan.FromHours(16), days[0].Covered);
            Assert.Equal(TimeSpan.FromHours(4), days[0].Watch);
            Assert.Equal(TimeSpan.FromHours(2), days[0].OtherWork);
            Assert.Equal(TimeSpan.FromHours(10), days[0].Rest);
            Assert.Equal(TimeSpan.Zero, days[0].Unknown);
            Assert.False(days[1].IsPartialDay);
            Assert.Equal(TimeSpan.FromHours(4 + 16), days[1].Rest);
            Assert.Equal(TimeSpan.FromHours(4), days[1].Watch);
            Assert.Equal(TimeSpan.FromHours(8), days[2].Rest);
            Assert.True(days[2].IsPartialDay);
            Assert.Equal("hf_invalid_offset", s.DailyTotals(new TimeSpan(8, 0, 30)).ErrorCode);
            Assert.Equal("hf_invalid_offset", s.DailyTotals(TimeSpan.FromHours(15)).ErrorCode);
        }

        [Fact]
        public void B5_DailyTotals_UnknownCounted()
        {
            var s = WorkRestSchedule.Create(T0, H(24), new[] { new DutyInterval(H(0), H(8), DutyKind.Rest) }).Value;
            var d = Assert.Single(s.DailyTotals(TimeSpan.Zero).Value);
            Assert.Equal(TimeSpan.FromHours(16), d.Unknown);
            Assert.Equal(TimeSpan.FromHours(8), d.Rest);
            Assert.False(d.IsPartialDay);
        }
    }

    internal static class AuditTestExtensions
    {
        public static IReadOnlyList<InvestigationAuditEntry> Logged(this IInvestigationAuditSink sink)
        {
            return ((InMemoryInvestigationAuditSink)sink).Entries;
        }
    }
}
