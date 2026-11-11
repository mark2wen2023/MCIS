using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>行级确认/驳回须写审计；预检失败不得半更新。</summary>
    public class ReviewActionsAcceptanceTests
    {
        private static InterviewRecord Row(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit, bool submit = true)
        {
            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("怎么用舵？", "就在 14:23 开始左舵，左舵 20 度。", rec.StartUtc.AddMinutes(2)));
            Ok(rec.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(rec.Locate(1, QaField.Answer, "左舵 20 度")), At(5, 18, 14, 23)));
            audit = new InMemoryInvestigationAuditSink();
            reg = new CrossCheckRegister(audit);
            if (submit)
            {
                Ok(reg.Submit(new CrossCheckResult("S-r", rec.RecordId, CrossCheckOutcome.Contradictory, 0, "deg", "20°", "20°", "VDR（虚构）", "|Δ|≤1"), Agent, At(5, 19, 10, 0)));
            }

            return rec;
        }

        [Fact]
        public void ConfirmRow_ConfirmsStatementAndEntry_WritesTwoAuditEntries()
        {
            InterviewRecord rec = Row(out var reg, out var audit);
            int n = audit.Entries.Count;
            var d = Ok(InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit, "核对（虚构）"));
            Assert.Equal(StatementReviewStatus.Confirmed, d.Statement.ReviewStatus);
            Assert.Equal(CrossCheckState.Confirmed, d.Entry.State);
            Assert.Equal(n + 2, audit.Entries.Count);
            Assert.Contains(audit.Entries.Skip(n), e => e.Action == InterviewRecord.ActionStatementReview);
            Assert.Contains(audit.Entries.Skip(n), e => e.Action == CrossCheckRegister.ActionConfirm);
            Assert.All(audit.Entries.Skip(n), e => Assert.Equal(Investigator, e.OperatorName));
        }

        [Fact]
        public void ConfirmRow_StatementOnly_WhenNotChecked_AndEntryOnly_WhenStatementAlreadyConfirmed()
        {
            InterviewRecord rec = Row(out var reg, out var audit, submit: false);
            int n = audit.Entries.Count;
            Ok(InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit));
            Assert.Equal(StatementReviewStatus.Confirmed, rec.GetStatement("S-r").ReviewStatus);
            Assert.Equal(n + 1, audit.Entries.Count);

            Ok(reg.Submit(new CrossCheckResult("S-r", rec.RecordId, CrossCheckOutcome.Consistent, 0, "deg", "20°", "20°", "VDR（虚构）", "|Δ|≤1"), Agent, At(5, 19, 11, 1)));
            int n2 = audit.Entries.Count;
            Ok(InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 2), audit));
            Assert.Equal(CrossCheckState.Confirmed, reg.Get("S-r").State);
            Assert.Equal(n2 + 1, audit.Entries.Count);
            Assert.Equal(CrossCheckRegister.ActionConfirm, audit.Entries[audit.Entries.Count - 1].Action);
        }

        [Fact]
        public void RejectRow_RejectsStatementAndDismissesEntry_WritesAudit_RequiresReason()
        {
            InterviewRecord rec = Row(out var reg, out var audit);
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.RejectRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit, "  "));
            Assert.Equal(StatementReviewStatus.Draft, rec.GetStatement("S-r").ReviewStatus);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S-r").State);
            Assert.Equal(n, audit.Entries.Count);

            var d = Ok(InterviewReviewActions.RejectRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit, "原文理解有误（虚构）"));
            Assert.Equal(StatementReviewStatus.Rejected, d.Statement.ReviewStatus);
            Assert.Equal(CrossCheckState.Dismissed, d.Entry.State);
            Assert.Equal(n + 2, audit.Entries.Count);
            Assert.Contains(audit.Entries.Skip(n), e => e.Action == InterviewRecord.ActionStatementReview);
            Assert.Contains(audit.Entries.Skip(n), e => e.Action == CrossCheckRegister.ActionDismiss);
        }

        [Fact]
        public void RejectRow_EntryAlreadyConfirmed_ReturnsEntryNotPending_NothingChanges()
        {
            InterviewRecord rec = Row(out var reg, out var audit);
            Ok(reg.Confirm("S-r", Investigator, At(5, 19, 11, 0)));
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.EntryNotPending, InterviewReviewActions.RejectRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 5), audit, "想驳回（虚构）"));
            Assert.Equal(StatementReviewStatus.Draft, rec.GetStatement("S-r").ReviewStatus);
            Assert.Equal(CrossCheckState.Confirmed, reg.Get("S-r").State);
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void ConfirmRow_NothingPending_OrRejected_NotReviewable_NoAudit()
        {
            InterviewRecord rec = Row(out var reg, out var audit);
            Ok(InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit));
            int n = audit.Entries.Count;
            Code(InterviewCompareErrors.NotReviewable, InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 5), audit));
            Assert.Equal(n, audit.Entries.Count);

            InterviewRecord rec2 = Row(out var reg2, out var audit2, submit: false);
            Ok(rec2.ReviewStatement("S-r", StatementReviewStatus.Rejected, Investigator, At(5, 19, 11, 0), audit2, "废弃（虚构）"));
            int n2 = audit2.Entries.Count;
            Code(InterviewCompareErrors.NotReviewable, InterviewReviewActions.ConfirmRow(rec2, reg2, "S-r", Investigator, At(5, 19, 11, 5), audit2));
            Assert.Equal(n2, audit2.Entries.Count);
        }

        [Fact]
        public void Validation_MissingStatement_RecordMismatch_EmptyInvestigator()
        {
            InterviewRecord rec = Row(out var reg, out var audit);
            Code(InterviewCompareErrors.StatementNotFound, InterviewReviewActions.ConfirmRow(rec, reg, "S-NOPE", Investigator, At(5, 19, 11, 0), audit));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.ConfirmRow(rec, reg, "S-r", "  ", At(5, 19, 11, 0), audit));
            Code(InterviewCompareErrors.InvalidArgument, InterviewReviewActions.ConfirmRow(null, reg, "S-r", Investigator, At(5, 19, 11, 0), audit));

            InterviewRecord other = NewRecord("IR-15");
            Ok(other.AddTurn("问", "左舵 20 度。", other.StartUtc.AddMinutes(2)));
            Ok(other.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(other.Locate(1, QaField.Answer, "左舵 20 度"))));
            // 登记簿里 S-r 属于 IR-09，拿到 IR-15 上操作
            int n = audit.Entries.Count;
            StatementReviewStatus before = other.GetStatement("S-r").ReviewStatus;
            Code(InterviewCompareErrors.RecordMismatch, InterviewReviewActions.ConfirmRow(other, reg, "S-r", Investigator, At(5, 19, 11, 0), audit));
            Assert.Equal(before, other.GetStatement("S-r").ReviewStatus);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S-r").State);
            Assert.Equal(n, audit.Entries.Count);
        }
    }
}
