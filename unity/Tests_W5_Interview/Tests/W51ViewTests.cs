using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    /// <summary>W5.1（DEFECTS/W5.md 21:32）：过期结论在视图中可见、不计入矛盾；过期结论不能确认；重新比对走 Submit / Resubmit（示例数据·虚构）。</summary>
    public class W51ViewTests
    {
        private const string Inv = "调查员 A（虚构）";

        private static InterviewRecord Modified(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit, string id = "S1")
        {
            InterviewRecord r = Small(out reg, out audit);
            SubmitAll(r, reg);
            Statement s = r.GetStatement(id);
            Ok(r.ModifyStatement(id, s.Summary + "（更正，虚构）", s.Claim, s.Span, s.ReferenceUtc, Inv, Day19(11, 0), audit));
            return r;
        }

        [Fact]
        public void Rows_FlagStale_AndSummaryExcludesStaleContradictions()
        {
            InterviewRecord r = Modified(out CrossCheckRegister reg, out _);
            var rows = InterviewComparisonView.Rows(r, reg);
            Assert.True(rows.Single(x => x.StatementId == "S1").IsStale);
            Assert.False(rows.Single(x => x.StatementId == "S1").IsContradiction);
            Assert.Equal(1, rows.Single(x => x.StatementId == "S1").StatementVersion);
            Assert.Equal(2, rows.Single(x => x.StatementId == "S1").StatementRevision);
            Assert.False(rows.Single(x => x.StatementId == "S2").IsStale);
            Assert.True(rows.Single(x => x.StatementId == "S3").IsContradiction);

            ComparisonSummary s = InterviewComparisonView.Summarize(r, reg);
            Assert.Equal(1, s.StaleCount);
            Assert.Equal(1, s.ContradictionCount);
            Assert.Equal(2, s.PendingCount); // 过期的待确认不再算“待确认”，算“需重新比对”
            Assert.Equal("3 条陈述 · 1 条矛盾 · 1 条需重新比对", s.HeaderText);
        }

        [Fact]
        public void Rows_UnmodifiedRecord_HasNoStaleAndHeaderUnchanged()
        {
            InterviewRecord r = Small(out CrossCheckRegister reg, out _);
            SubmitAll(r, reg);
            Assert.All(InterviewComparisonView.Rows(r, reg), x => Assert.False(x.IsStale));
            ComparisonSummary s = InterviewComparisonView.Summarize(r, reg);
            Assert.Equal(0, s.StaleCount);
            Assert.Equal("3 条陈述 · 2 条矛盾", s.HeaderText);
        }

        [Fact]
        public void ConfirmedStaleContradiction_LeavesConfirmedCount_AndRosterAsksForRecheck()
        {
            InterviewRecord r = Small(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            SubmitAll(r, reg);
            Ok(reg.Confirm("S1", Inv, Day19(10, 30)));
            Ok(reg.Confirm("S2", Inv, Day19(10, 30)));
            Ok(reg.Confirm("S3", Inv, Day19(10, 30)));
            RosterEntry before = InterviewComparisonView.Roster(r, reg);
            Assert.Equal("2 处矛盾", before.Label);

            Statement s = r.GetStatement("S1");
            Ok(r.ModifyStatement("S1", "14:22 开始左舵（更正，虚构）", s.Claim, s.Span, s.ReferenceUtc, Inv, Day19(11, 0), audit));
            ComparisonSummary sum = InterviewComparisonView.Summarize(r, reg);
            Assert.Equal(1, sum.ConfirmedContradictionCount);
            Assert.Equal(1, sum.StaleCount);
            RosterEntry after = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(1, after.ConfirmedContradictions);
            Assert.Equal(1, after.StaleCount);
            Assert.Equal(RosterStatus.Contradictions, after.Status);
            Assert.Equal("1 处矛盾 · 1 条需重新比对", after.Label);
        }

        [Fact]
        public void Roster_OnlyStale_IsPendingWithRecheckLabel()
        {
            InterviewRecord r = Small(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            SubmitAll(r, reg);
            Ok(reg.Confirm("S2", Inv, Day19(10, 30))); // 只确认比对结论；陈述仍为草稿（已确认的陈述不可修改）
            Ok(reg.Dismiss("S1", Inv, Day19(10, 31), "数据源有误（虚构）"));
            Ok(reg.Dismiss("S3", Inv, Day19(10, 31), "数据源有误（虚构）"));
            Statement s = r.GetStatement("S2");
            Ok(r.ModifyStatement("S2", "左舵 25°（更正，虚构）", StatementClaim.ScalarValue(25, "deg"), s.Span, s.ReferenceUtc, Inv, Day19(11, 0), audit));
            RosterEntry e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(RosterStatus.Pending, e.Status);
            Assert.Equal("1 条需重新比对", e.Label);
        }

        [Fact]
        public void Highlighter_StaleContradiction_IsNotMarked()
        {
            InterviewRecord r = Modified(out CrossCheckRegister reg, out _);
            var seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer, reg).Where(x => !x.IsPlain).ToList();
            Assert.Equal(new[] { ContradictionMark.None, ContradictionMark.None, ContradictionMark.Pending }, seg.Select(x => x.Contradiction));
        }

        [Fact]
        public void Chart_StalePoint_HasNoObservedTime()
        {
            InterviewRecord r = Small(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            SubmitAll(r, reg);
            Assert.NotNull(InterviewComparisonView.Chart(r, reg).Points.Single(p => p.StatementId == "S1").ObservedUtc);
            Statement s = r.GetStatement("S1");
            Ok(r.ModifyStatement("S1", "14:22 开始左舵（虚构）", StatementClaim.EventTime(At(14, 22)), s.Span, s.ReferenceUtc, Inv, Day19(11, 0), audit));
            TimeChartPoint p1 = InterviewComparisonView.Chart(r, reg).Points.Single(p => p.StatementId == "S1");
            Assert.True(p1.IsStale);
            Assert.Null(p1.ObservedUtc);
            Assert.Null(p1.DeltaSeconds);
            Assert.Equal("需重新比对", p1.Note);
            Assert.False(InterviewComparisonView.Chart(r, reg).Points.Single(p => p.StatementId == "S2").IsStale);
        }

        [Fact]
        public void ConfirmRow_OnStaleEntry_IsRefused_AndWritesNothing()
        {
            InterviewRecord r = Modified(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.EntryStale, InterviewReviewActions.ConfirmRow(r, reg, "S1", Inv, Day19(11, 5), audit));
            Assert.Equal(n, audit.Entries.Count);
            Assert.Equal(StatementReviewStatus.Modified, r.GetStatement("S1").ReviewStatus);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S1").State);
        }

        [Fact]
        public void RecheckRow_StalePending_DismissesThenResubmitsWithCurrentRevision()
        {
            InterviewRecord r = Modified(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            CrossCheckEntry old = reg.Get("S1");
            int n = audit.Entries.Count;
            RowDecision d = Ok(InterviewReviewActions.RecheckRow(r, reg, "S1", SmallSource(), Inv, Day19(11, 10), audit, "陈述已更正（虚构）"));
            Assert.Equal(CrossCheckState.Superseded, old.State);
            Assert.Same(d.Entry, reg.Get("S1"));
            Assert.Equal(CrossCheckState.PendingConfirmation, d.Entry.State);
            Assert.Equal(2, d.Entry.StatementVersion);
            Assert.False(d.Entry.IsStale(r));
            Assert.Equal(new[] { CrossCheckRegister.ActionDismiss, CrossCheckRegister.ActionResubmit }, audit.Entries.Skip(n).Select(a => a.Action).ToArray());
            Assert.Contains("r1→r2", audit.Entries[n].AfterValueSummary);
            Assert.False(InterviewComparisonView.Rows(r, reg).Single(x => x.StatementId == "S1").IsStale);
            // 重新比对后可以确认
            Ok(InterviewReviewActions.ConfirmRow(r, reg, "S1", Inv, Day19(11, 15), audit));
        }

        [Fact]
        public void RecheckRow_UncheckedStatement_Submits_AndDismissed_Resubmits()
        {
            InterviewRecord r = Small(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            RowDecision d = Ok(InterviewReviewActions.RecheckRow(r, reg, "S2", SmallSource(), Inv, Day19(10, 0), audit));
            Assert.Equal(CrossCheckRegister.ActionSubmit, audit.Entries.Last().Action);
            Assert.Equal(CrossCheckOutcome.Consistent, d.Entry.Result.Outcome);

            Ok(reg.Dismiss("S2", Inv, Day19(10, 5), "数据源有误（虚构）"));
            RowDecision d2 = Ok(InterviewReviewActions.RecheckRow(r, reg, "S2", SmallSource(), Inv, Day19(10, 6), audit, "换数据源（虚构）"));
            Assert.Equal(CrossCheckRegister.ActionResubmit, audit.Entries.Last().Action);
            Assert.Equal(CrossCheckState.Superseded, d.Entry.State);
            Assert.NotSame(d.Entry, d2.Entry);
        }

        [Fact]
        public void RecheckRow_Refusals()
        {
            InterviewRecord r = Small(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit);
            SubmitAll(r, reg);
            int n = audit.Entries.Count;
            // 未过期的待确认：直接确认或驳回即可，不允许绕过
            Code(InterviewCompareErrors.RecheckNotAllowed, InterviewReviewActions.RecheckRow(r, reg, "S1", SmallSource(), Inv, Day19(11, 0), audit, "想重比（虚构）"));
            Ok(reg.Confirm("S2", Inv, Day19(10, 30)));
            Code(InterviewCompareErrors.RecheckNotAllowed, InterviewReviewActions.RecheckRow(r, reg, "S2", SmallSource(), Inv, Day19(11, 0), audit, "想重比（虚构）"));
            // 已有条目时理由必填；参数为空
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.RecheckRow(r, reg, "S1", SmallSource(), Inv, Day19(11, 0), audit, " "));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.RecheckRow(r, reg, "S1", null, Inv, Day19(11, 0), audit, "r"));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.RecheckRow(r, reg, "S1", SmallSource(), " ", Day19(11, 0), audit, "r"));
            Code(InterviewCompareErrors.StatementNotFound, InterviewReviewActions.RecheckRow(r, reg, "S9", SmallSource(), Inv, Day19(11, 0), audit, "r"));
            Assert.Equal(n + 1, audit.Entries.Count); // 只有上面那次 Confirm
            // 已驳回的陈述不再比对
            InterviewRecord r2 = Small(out CrossCheckRegister reg2, out InMemoryInvestigationAuditSink audit2);
            Ok(InterviewReviewActions.RejectRow(r2, reg2, "S3", Inv, Day19(10, 0), audit2, "不是陈述（虚构）"));
            Code(InterviewCompareErrors.NotReviewable, InterviewReviewActions.RecheckRow(r2, reg2, "S3", SmallSource(), Inv, Day19(10, 1), audit2));
        }
    }
}
