using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    public class ReviewActionsTests
    {
        [Fact]
        public void ConfirmRow_ConfirmsStatementAndEntry_TwoAuditEntries()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            int before = audit.Entries.Count;
            var d = Ok(InterviewReviewActions.ConfirmRow(r, reg, "S1", "调查员甲", Day19(11, 0), audit, "与 VDR 核对（虚构）"));
            Assert.Equal(StatementReviewStatus.Confirmed, d.Statement.ReviewStatus);
            Assert.Equal(CrossCheckState.Confirmed, d.Entry.State);
            Assert.Equal(StatementReviewStatus.Confirmed, r.GetStatement("S1").ReviewStatus);
            Assert.Equal(before + 2, audit.Entries.Count);
            Assert.All(audit.Entries.Skip(before), e => Assert.Equal(InvestigationAuditCategories.Interview, e.Category));
        }

        [Fact]
        public void ConfirmRow_StatementOnly_WhenNotChecked()
        {
            var r = Small(out var reg, out var audit);
            var d = Ok(InterviewReviewActions.ConfirmRow(r, reg, "S2", "调查员甲", Day19(11, 0), audit));
            Assert.Equal(StatementReviewStatus.Confirmed, d.Statement.ReviewStatus);
            Assert.Null(d.Entry);
            Assert.Single(audit.Entries);
        }

        [Fact]
        public void ConfirmRow_EntryOnly_WhenStatementAlreadyConfirmed()
        {
            var r = Small(out var reg, out var audit);
            Ok(r.ReviewStatement("S1", StatementReviewStatus.Confirmed, "调查员甲", Day19(10, 30), audit));
            SubmitAll(r, reg);
            var d = Ok(InterviewReviewActions.ConfirmRow(r, reg, "S1", "调查员乙", Day19(11, 0), audit));
            Assert.Equal("调查员甲", d.Statement.ReviewedBy);
            Assert.Equal(CrossCheckState.Confirmed, d.Entry.State);
            Assert.Equal("调查员乙", d.Entry.DecidedBy);
        }

        [Fact]
        public void ConfirmRow_NothingPending_NotReviewable_NoAudit()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            Ok(InterviewReviewActions.ConfirmRow(r, reg, "S1", "调查员甲", Day19(11, 0), audit));
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.NotReviewable, InterviewReviewActions.ConfirmRow(r, reg, "S1", "调查员甲", Day19(11, 1), audit));
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void ConfirmRow_RejectedStatement_NotReviewable_EntryUntouched()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            Ok(r.ReviewStatement("S3", StatementReviewStatus.Rejected, "调查员甲", Day19(10, 30), audit, "抽取错误（虚构）"));
            Code(InterviewCompareErrors.NotReviewable, InterviewReviewActions.ConfirmRow(r, reg, "S3", "调查员甲", Day19(11, 0), audit));
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S3").State);
        }

        [Fact]
        public void ConfirmRow_Validation()
        {
            var r = Small(out var reg, out var audit);
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.ConfirmRow(null, reg, "S1", "甲", Day19(11, 0), audit));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.ConfirmRow(r, null, "S1", "甲", Day19(11, 0), audit));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.ConfirmRow(r, reg, "S1", "甲", Day19(11, 0), null));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.ConfirmRow(r, reg, "S1", " ", Day19(11, 0), audit));
            Code(InterviewCompareErrors.StatementNotFound, InterviewReviewActions.ConfirmRow(r, reg, "S9", "甲", Day19(11, 0), audit));
            Assert.Empty(audit.Entries);
            Assert.Equal(StatementReviewStatus.Draft, r.GetStatement("S1").ReviewStatus);
        }

        [Fact]
        public void EntryOfOtherRecord_RecordMismatch_NothingChanged()
        {
            var r = Small(out var reg, out var audit);
            Ok(reg.Submit(new CrossCheckResult("S1", "IR-77", CrossCheckOutcome.Contradictory, 60, "s", "a", "b", "x", "r"), "系统", Day19(10, 0)));
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.RecordMismatch, InterviewReviewActions.ConfirmRow(r, reg, "S1", "甲", Day19(11, 0), audit));
            Code(InterviewCompareErrors.RecordMismatch, InterviewReviewActions.RejectRow(r, reg, "S1", "甲", Day19(11, 0), audit, "理由"));
            Assert.Equal(n, audit.Entries.Count);
            Assert.Equal(StatementReviewStatus.Draft, r.GetStatement("S1").ReviewStatus);
        }

        [Fact]
        public void RejectRow_RejectsStatementAndDismissesEntry()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            var d = Ok(InterviewReviewActions.RejectRow(r, reg, "S3", "调查员甲", Day19(11, 0), audit, "转写错误（虚构）"));
            Assert.Equal(StatementReviewStatus.Rejected, d.Statement.ReviewStatus);
            Assert.Equal(CrossCheckState.Dismissed, d.Entry.State);
            Assert.Equal("转写错误（虚构）", d.Entry.Note);
            Assert.Equal(1, InterviewComparisonView.Summarize(r, reg).ContradictionCount);
        }

        [Fact]
        public void RejectRow_RequiresReason_NoChange()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.RejectRow(r, reg, "S3", "调查员甲", Day19(11, 0), audit, "  "));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.RejectRow(r, reg, "S3", "调查员甲", Day19(11, 0), audit, null));
            Assert.Equal(n, audit.Entries.Count);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S3").State);
        }

        [Fact]
        public void RejectRow_EntryAlreadyConfirmed_EntryNotPending_StatementUntouched()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            Ok(reg.Confirm("S1", "调查员甲", Day19(10, 30)));
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.EntryNotPending, InterviewReviewActions.RejectRow(r, reg, "S1", "调查员甲", Day19(11, 0), audit, "理由"));
            Assert.Equal(StatementReviewStatus.Draft, r.GetStatement("S1").ReviewStatus);
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void RejectRow_StatementAlreadyReviewed_NotReviewable()
        {
            var r = Small(out var reg, out var audit);
            Ok(r.ReviewStatement("S2", StatementReviewStatus.Confirmed, "调查员甲", Day19(10, 30), audit));
            Code(InterviewCompareErrors.NotReviewable, InterviewReviewActions.RejectRow(r, reg, "S2", "调查员甲", Day19(11, 0), audit, "理由"));
            Code(InterviewCompareErrors.StatementNotFound, InterviewReviewActions.RejectRow(r, reg, "S9", "调查员甲", Day19(11, 0), audit, "理由"));
        }

        [Fact]
        public void RejectRow_NoEntry_RejectsStatementOnly()
        {
            var r = Small(out var reg, out var audit);
            var d = Ok(InterviewReviewActions.RejectRow(r, reg, "S2", "调查员甲", Day19(11, 0), audit, "不是陈述（虚构）"));
            Assert.Null(d.Entry);
            Assert.Equal(StatementReviewStatus.Rejected, d.Statement.ReviewStatus);
        }
    }
}
