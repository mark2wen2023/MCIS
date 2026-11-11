using System;
using System.Linq;
using System.Reflection;
using Mcis.Domain.Evidence;
using Mcis.Domain.Recommendations;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>验收重点④：征求意见 30 天期限（边界日）、每方每轮一次、关闭条件。对照原型 15 与 consultation-round.schema.json。</summary>
    public class ConsultationAcceptanceTests
    {
        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        private static ConsultationParty[] Parties()
        {
            return new[]
            {
                new ConsultationParty("flag-a", "船旗国 A（Lily）（虚构）"),
                new ConsultationParty("flag-b", "船旗国 B（Mary）（虚构）"),
                new ConsultationParty("co-lily", "Lily 船公司（虚构）"),
                new ConsultationParty("co-mary", "Mary 船公司（虚构）"),
            };
        }

        [Fact]
        public void OpenRound_DefaultDeadlineIs30Days()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT-2026-LN01（虚构）", audit);
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            ConsultationRound r = c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA).Value;
            Assert.Equal(1, r.RoundNo);
            Assert.Equal(opened.AddDays(30), r.DeadlineUtc);
            Assert.False(r.IsAgreedDeadline);
            Assert.Equal(Consultation.DefaultDeadlineDays, 30);
            Assert.Equal("consultation.open", audit.Entries.Last().Action);
            Assert.Equal(InvestigationAuditCategories.Consultation, audit.Entries.Last().Category);
            Assert.Contains("默认 30 天", audit.Entries.Last().AfterValueSummary, StringComparison.Ordinal);
        }

        [Fact]
        public void DeadlineBoundary_StatusAndDaysRemaining()
        {
            var c = new Consultation("RPT-2026-LN01（虚构）", new InMemoryInvestigationAuditSink());
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            ConsultationRound r = c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA).Value;
            DateTimeOffset deadline = r.DeadlineUtc;

            Assert.Equal(ReplyStatus.Pending, r.StatusOf("flag-a", deadline));
            Assert.Equal(ReplyStatus.Pending, r.StatusOf("flag-a", deadline.AddSeconds(-1)));
            Assert.Equal(ReplyStatus.Overdue, r.StatusOf("flag-a", deadline.AddSeconds(1)));
            Assert.Equal(0, r.DaysRemaining(deadline));
            Assert.Equal(0, r.DaysRemaining(deadline.AddHours(1)));
            Assert.Equal(1, r.DaysRemaining(deadline.AddHours(-1)));
            Assert.Equal(30, r.DaysRemaining(opened.AddSeconds(1)));
        }

        [Fact]
        public void Reply_OnDeadlineInstant_IsOnTime_AfterDeadline_IsLate()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT-2026-LN01（虚构）", audit);
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            ConsultationRound r = c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA).Value;

            AssertOk(c.RecordReply(1, "flag-a", r.DeadlineUtc, "意见全文（虚构）", new[] { "建议一（虚构）" }, W3AccFixture.OpA));
            Assert.Equal(ReplyStatus.Replied, r.StatusOf("flag-a", r.DeadlineUtc.AddDays(1)));

            AssertOk(c.RecordReply(1, "flag-b", r.DeadlineUtc.AddSeconds(1), "迟复（虚构）", new[] { "建议二（虚构）" }, W3AccFixture.OpA));
            Assert.Equal(ReplyStatus.RepliedLate, r.StatusOf("flag-b", r.DeadlineUtc.AddDays(1)));
            Assert.Equal("consultation.reply", audit.Entries.Last().Action);
            Assert.Contains("RepliedLate", audit.Entries.Last().AfterValueSummary, StringComparison.Ordinal);
        }

        [Fact]
        public void EachParty_MayReplyOncePerRound()
        {
            var c = new Consultation("RPT-2026-LN01（虚构）", new InMemoryInvestigationAuditSink());
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA);
            AssertOk(c.RecordReply(1, "co-lily", opened.AddDays(2), "已复（虚构）", new[] { "意见（虚构）" }, W3AccFixture.OpA));
            Mcis.Core.Result<ConsultationReply> second = c.RecordReply(1, "co-lily", opened.AddDays(3), "再次（虚构）", new[] { "又一条（虚构）" }, W3AccFixture.OpA);
            Assert.False(second.IsSuccess);
            Assert.Equal(Consultation.ErrDuplicateReply, second.ErrorCode);

            Mcis.Core.Result<ConsultationReply> unknown = c.RecordReply(1, "stranger", opened.AddDays(2), "x", null, W3AccFixture.OpA);
            Assert.False(unknown.IsSuccess);
            Assert.Equal(Consultation.ErrUnknownParty, unknown.ErrorCode);
        }

        [Fact]
        public void Close_RequiresAllRepliedOrPastDeadline()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT-2026-LN01（虚构）", audit);
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            ConsultationRound r = c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA).Value;

            Mcis.Core.Result<ConsultationRound> early = c.CloseRound(1, W3AccFixture.OpA, opened.AddDays(10));
            Assert.False(early.IsSuccess);
            Assert.Equal(Consultation.ErrCannotClose, early.ErrorCode);
            Assert.False(r.IsClosed);

            // 期限前 1 秒、尚未全员回复：不可关闭
            Mcis.Core.Result<ConsultationRound> justBefore = c.CloseRound(1, W3AccFixture.OpA, r.DeadlineUtc.AddSeconds(-1));
            Assert.False(justBefore.IsSuccess);
            Assert.Equal(Consultation.ErrCannotClose, justBefore.ErrorCode);
            Assert.False(r.IsClosed);

            // 架构师裁定（澄清2，2026-11-11）：到达期限时刻（utc >= deadline）即可关闭，即使未全员回复。
            AssertOk(c.CloseRound(1, W3AccFixture.OpA, r.DeadlineUtc));
            Assert.True(r.IsClosed);
            Assert.Equal(r.DeadlineUtc, r.ClosedUtc);
            Assert.Equal("consultation.close", audit.Entries.Last().Action);

            Mcis.Core.Result<ConsultationRound> again = c.CloseRound(1, W3AccFixture.OpA, r.DeadlineUtc.AddDays(1));
            Assert.False(again.IsSuccess);
            Assert.Equal(Consultation.ErrRoundClosed, again.ErrorCode);
        }

        [Fact]
        public void Close_AllowedWhenAllRepliedBeforeDeadline()
        {
            var c = new Consultation("RPT-2026-LN01（虚构）", new InMemoryInvestigationAuditSink());
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            ConsultationRound r = c.OpenRound("v2", Parties(), opened, W3AccFixture.OpA).Value;
            foreach (ConsultationParty p in r.Parties)
            {
                AssertOk(c.RecordReply(1, p.PartyId, opened.AddDays(5), "已复（虚构）", new[] { "意见（虚构）" }, W3AccFixture.OpA));
            }

            Assert.True(r.AllReplied);
            AssertOk(c.CloseRound(1, W3AccFixture.OpA, opened.AddDays(6)));
            Assert.True(r.IsClosed);
        }

        [Fact]
        public void CannotOpenNextRound_UntilCurrentClosed()
        {
            var c = new Consultation("RPT-2026-LN01（虚构）", new InMemoryInvestigationAuditSink());
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA);
            Mcis.Core.Result<ConsultationRound> second = c.OpenRound("v2", Parties(), opened.AddDays(31), W3AccFixture.OpA);
            Assert.False(second.IsSuccess);
            Assert.Equal(Consultation.ErrRoundOpen, second.ErrorCode);
        }

        [Fact]
        public void Adoption_RequiresWrittenFeedback_IsFinal_AndTallied()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT-2026-LN01（虚构）", audit);
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA);
            ConsultationReply reply = c.RecordReply(1, "flag-a", opened.AddDays(3), "回复（虚构）", new[] { "意见甲（虚构）", "意见乙（虚构）", "意见丙（虚构）", "意见丁（虚构）" }, W3AccFixture.OpA).Value;
            Assert.Equal(4, reply.Comments.Count);

            Mcis.Core.Result<ConsultationComment> noFb = c.DecideComment(reply.Comments[1].CommentId, AdoptionDecision.NotAdopted, "  ", W3AccFixture.OpA, opened.AddDays(4));
            Assert.False(noFb.IsSuccess);

            AssertOk(c.DecideComment(reply.Comments[0].CommentId, AdoptionDecision.Adopted, null, W3AccFixture.OpA, opened.AddDays(4)));
            AssertOk(c.DecideComment(reply.Comments[1].CommentId, AdoptionDecision.Adopted, null, W3AccFixture.OpA, opened.AddDays(4)));
            AssertOk(c.DecideComment(reply.Comments[2].CommentId, AdoptionDecision.PartiallyAdopted, "部分吸收（虚构）", W3AccFixture.OpA, opened.AddDays(4)));
            AssertOk(c.DecideComment(reply.Comments[3].CommentId, AdoptionDecision.NotAdopted, "超出调查范围（虚构）", W3AccFixture.OpA, opened.AddDays(4)));
            Mcis.Core.Result<ConsultationComment> again = c.DecideComment(reply.Comments[0].CommentId, AdoptionDecision.NotAdopted, "改判（虚构）", W3AccFixture.OpA, opened.AddDays(5));
            Assert.False(again.IsSuccess);
            Assert.Equal(Consultation.ErrAlreadyDecided, again.ErrorCode);

            AdoptionTally t = c.GetRound(1).TallyFor("flag-a");
            Assert.Equal(2, t.Adopted);
            Assert.Equal(1, t.PartiallyAdopted);
            Assert.Equal(1, t.NotAdopted);
            Assert.Equal(0, t.Pending);
            Assert.Equal(4, t.Total);
            Assert.Equal("consultation.decide", audit.Entries.Last().Action);
        }

        [Fact]
        public void AgreedDeadline_IsHonored()
        {
            var c = new Consultation("RPT-2026-LN01（虚构）", new InMemoryInvestigationAuditSink());
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            DateTimeOffset agreed = opened.AddDays(14);
            ConsultationRound r = c.OpenRound("v1", Parties(), opened, W3AccFixture.OpA, agreed).Value;
            Assert.True(r.IsAgreedDeadline);
            Assert.Equal(agreed, r.DeadlineUtc);
            Mcis.Core.Result<ConsultationRound> bad = c.OpenRound("v-bad", Parties(), opened, W3AccFixture.OpA, opened);
            // previous still open, but also test invalid agreed deadline via a fresh consultation
            var c2 = new Consultation("RPT-X（虚构）", new InMemoryInvestigationAuditSink());
            Mcis.Core.Result<ConsultationRound> invalid = c2.OpenRound("v1", Parties(), opened, W3AccFixture.OpA, opened);
            Assert.False(invalid.IsSuccess);
        }

        [Fact]
        public void W3_D06_Consultation_SupportsContractCaseIdWaivedAndDraftHash()
        {
            // consultation-round.schema.json required: caseId；responses.status 含 Waived；可选 draftSha256。
            Type round = typeof(ConsultationRound);
            Type consult = typeof(Consultation);
            Assert.True(consult.GetProperty("CaseId") != null || round.GetProperty("CaseId") != null,
                "合同必填 caseId，领域模型未提供。");
            string[] names = Enum.GetNames(typeof(ReplyStatus));
            Assert.Contains("Waived", names);
            Assert.True(round.GetProperty("DraftSha256") != null || consult.GetProperty("DraftSha256") != null,
                "合同提供 draftSha256（草案哈希）以关联保管链。");
        }
    }
}
