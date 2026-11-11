using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Audit;
using Mcis.Domain.Evidence;
using Mcis.Domain.Recommendations;
using Xunit;
using S = Mcis.Domain.Recommendations.RecommendationStatus;

namespace Mcis.W3.Tests
{
    public class SafetyRecommendationTests
    {
        private static (SafetyRecommendationBoard board, InMemoryInvestigationAuditSink audit) NewBoard()
        {
            var audit = new InMemoryInvestigationAuditSink();
            return (new SafetyRecommendationBoard(audit), audit);
        }

        private static SafetyRecommendation Draft(SafetyRecommendationBoard b, string id = "SR-2026-01", DateTimeOffset? due = null)
        {
            Result<SafetyRecommendation> r = b.CreateDraft(id, "Mary 轮公司 SMS 增加狭水道与雾航程序（虚构）", "Mary 轮公司（虚构）",
                new[] { "HFACS-3", "ECFC-E4" }, due ?? W3Demo.Day(8, 30), "调查员 A（虚构）", W3Demo.Day(6, 1), "正文（虚构）");
            Assert.True(r.IsSuccess, r.ToString());
            return r.Value;
        }

        [Fact]
        public void CreateDraft_RecordsFieldsAndCauseLinks()
        {
            var (b, audit) = NewBoard();
            SafetyRecommendation r = Draft(b);
            Assert.Equal(S.Draft, r.Status);
            Assert.Equal(new[] { "HFACS-3", "ECFC-E4" }, r.CauseNodeIds);
            Assert.Equal("Mary 轮公司（虚构）", r.Addressee);
            Assert.Equal(W3Demo.Day(8, 30), r.DueUtc);
            Assert.False(r.IsInterim);
            Assert.Single(audit.Entries);
            Assert.Equal("safetyrec.create", audit.Entries[0].Action);
            Assert.Equal("SafetyRec", audit.Entries[0].Category);
            Assert.Same(r, b.ByCauseNode("ECFC-E4").Single());
            Assert.Empty(b.ByCauseNode("COLREG-R19"));
        }

        [Fact]
        public void CreateDraft_RequiresCauseNode_ValidId_UniqueId_AndFutureDue()
        {
            var (b, audit) = NewBoard();
            Assert.Equal(SafetyRecommendationBoard.ErrNoCauseLink, b.CreateDraft("SR-2026-01", "t", "a", new string[0], W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNoCauseLink, b.CreateDraft("SR-2026-01", "t", "a", new[] { " ", null }, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNoCauseLink, b.CreateDraft("SR-2026-01", "t", "a", null, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidId, b.CreateDraft("REC-1", "t", "a", new[] { "N1" }, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidId, b.CreateDraft(null, "t", "a", new[] { "N1" }, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.CreateDraft("SR-2026-01", "t", " ", new[] { "N1" }, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.CreateDraft("SR-2026-01", "t", "a", new[] { "N1" }, W3Demo.Day(6, 1), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Empty(audit.Entries);
            Draft(b);
            Assert.Equal(SafetyRecommendationBoard.ErrDuplicateId, b.CreateDraft("SR-2026-01", "t", "a", new[] { "N1" }, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1)).ErrorCode);
        }

        [Fact]
        public void CreateDraft_DeduplicatesCauseNodes()
        {
            var (b, _) = NewBoard();
            SafetyRecommendation r = b.CreateDraft("SR-2026-05", "临时措施：雾航限速 8 kn（虚构）", "星屿 VTS（虚构）", new[] { "R6", "R6", "ECFC-C2" }, W3Demo.Day(6, 2), "op", W3Demo.Day(5, 25), isInterim: true).Value;
            Assert.Equal(new[] { "R6", "ECFC-C2" }, r.CauseNodeIds);
            Assert.True(r.IsInterim);
        }

        [Fact]
        public void HappyPath_DraftIssuedRespondedImplementedClosed()
        {
            var (b, audit) = NewBoard();
            Draft(b);
            Assert.True(b.Issue("SR-2026-01", "op", W3Demo.Day(6, 5)).IsSuccess);
            Assert.True(b.RecordResponse("SR-2026-01", "Mary 轮公司（虚构）", "已修订 SMS 第 7 章（虚构）", "op", W3Demo.Day(7, 1)).IsSuccess);
            Assert.True(b.MarkImplemented("SR-2026-01", "op", W3Demo.Day(8, 1), "已核查").IsSuccess);
            SafetyRecommendation r = b.Close("SR-2026-01", "op", W3Demo.Day(8, 2)).Value;
            Assert.Equal(S.Closed, r.Status);
            Assert.True(r.IsTerminal);
            Assert.Equal(new[] { S.Issued, S.Responded, S.Implemented, S.Closed }, r.History.Select(h => h.To));
            Assert.Equal(new[] { S.Draft, S.Issued, S.Responded, S.Implemented }, r.History.Select(h => h.From));
            Assert.Single(r.Responses);
            Assert.Equal(5, audit.Entries.Count);
            foreach (InvestigationAuditEntry e in audit.Entries)
            {
                Assert.Equal(e.ToJsonLine(), AuditRecord.FromJsonLine(e.ToJsonLine()).ToJsonLine());
            }
        }

        [Fact]
        public void Responded_CanGoNotAdopted_WithReason_ThenClosed()
        {
            var (b, _) = NewBoard();
            Draft(b);
            b.Issue("SR-2026-01", "op", W3Demo.Day(6, 5));
            b.RecordResponse("SR-2026-01", "Mary 轮公司（虚构）", "不同意（虚构）", "op", W3Demo.Day(7, 1));
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.MarkNotAdopted("SR-2026-01", "op", W3Demo.Day(7, 2), " ").ErrorCode);
            Assert.Equal(S.Responded, b.Get("SR-2026-01").Status);
            Assert.True(b.MarkNotAdopted("SR-2026-01", "op", W3Demo.Day(7, 2), "公司认为已有等效措施").IsSuccess);
            Assert.True(b.Close("SR-2026-01", "op", W3Demo.Day(7, 3)).IsSuccess);
        }

        [Fact]
        public void Responded_CanBeClosedDirectly()
        {
            var (b, _) = NewBoard();
            Draft(b);
            b.Issue("SR-2026-01", "op", W3Demo.Day(6, 5));
            b.RecordResponse("SR-2026-01", "p", "t", "op", W3Demo.Day(7, 1));
            Assert.True(b.Close("SR-2026-01", "op", W3Demo.Day(7, 3), "由后续建议取代").IsSuccess);
        }

        public static IEnumerable<object[]> AllPairs()
        {
            foreach (S from in Enum.GetValues(typeof(S)))
            {
                foreach (S to in Enum.GetValues(typeof(S)))
                {
                    yield return new object[] { from, to };
                }
            }
        }

        [Theory]
        [MemberData(nameof(AllPairs))]
        public void TransitionTable_MatchesSpec(S from, S to)
        {
            var legal = new HashSet<(S, S)>
            {
                (S.Draft, S.Issued),
                (S.Issued, S.Responded),
                (S.Responded, S.Implemented),
                (S.Responded, S.NotAdopted),
                (S.Responded, S.Closed),
                (S.Implemented, S.Closed),
                (S.NotAdopted, S.Closed),
            };
            Assert.Equal(legal.Contains((from, to)), SafetyRecommendationBoard.CanTransition(from, to));
        }

        [Theory]
        [InlineData(S.Draft, S.Implemented)]
        [InlineData(S.Draft, S.NotAdopted)]
        [InlineData(S.Draft, S.Closed)]
        [InlineData(S.Draft, S.Draft)]
        [InlineData(S.Issued, S.Implemented)]
        [InlineData(S.Issued, S.Closed)]
        [InlineData(S.Issued, S.Draft)]
        [InlineData(S.Responded, S.Issued)]
        [InlineData(S.Implemented, S.NotAdopted)]
        [InlineData(S.Implemented, S.Responded)]
        [InlineData(S.NotAdopted, S.Implemented)]
        [InlineData(S.Closed, S.Draft)]
        [InlineData(S.Closed, S.Issued)]
        [InlineData(S.Closed, S.Implemented)]
        public void IllegalTransition_IsRejected_WithoutStateChangeOrAudit(S start, S target)
        {
            var (b, audit) = NewBoard();
            Draft(b);
            DriveTo(b, start);
            int before = audit.Entries.Count;
            int hist = b.Get("SR-2026-01").History.Count;
            Result<SafetyRecommendation> r = b.Transition("SR-2026-01", target, "op", W3Demo.Day(8, 20), "reason");
            Assert.False(r.IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, r.ErrorCode);
            Assert.Equal(start, b.Get("SR-2026-01").Status);
            Assert.Equal(before, audit.Entries.Count);
            Assert.Equal(hist, b.Get("SR-2026-01").History.Count);
        }

        [Fact]
        public void GenericTransitionToResponded_IsRejected_MustUseRecordResponse()
        {
            var (b, _) = NewBoard();
            Draft(b);
            b.Issue("SR-2026-01", "op", W3Demo.Day(6, 5));
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, b.Transition("SR-2026-01", S.Responded, "op", W3Demo.Day(6, 6)).ErrorCode);
            Assert.Equal(S.Issued, b.Get("SR-2026-01").Status);
        }

        [Fact]
        public void RecordResponse_RulesAndFollowUps()
        {
            var (b, _) = NewBoard();
            Draft(b);
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, b.RecordResponse("SR-2026-01", "p", "t", "op", W3Demo.Day(6, 2)).ErrorCode);
            b.Issue("SR-2026-01", "op", W3Demo.Day(6, 5));
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.RecordResponse("SR-2026-01", "", "t", "op", W3Demo.Day(6, 6)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNotFound, b.RecordResponse("SR-2026-99", "p", "t", "op", W3Demo.Day(6, 6)).ErrorCode);
            b.RecordResponse("SR-2026-01", "p", "首次回复", "op", W3Demo.Day(6, 6));
            b.RecordResponse("SR-2026-01", "p", "补充回复", "op", W3Demo.Day(6, 7));
            SafetyRecommendation r = b.Get("SR-2026-01");
            Assert.Equal(S.Responded, r.Status);
            Assert.Equal(2, r.Responses.Count);
            Assert.Equal(2, r.History.Count);
            b.MarkImplemented("SR-2026-01", "op", W3Demo.Day(6, 8));
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, b.RecordResponse("SR-2026-01", "p", "t", "op", W3Demo.Day(6, 9)).ErrorCode);
        }

        [Fact]
        public void Transition_RequiresOperatorAndKnownId()
        {
            var (b, _) = NewBoard();
            Draft(b);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.Issue("SR-2026-01", " ", W3Demo.Day(6, 5)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNotFound, b.Issue("SR-2026-77", "op", W3Demo.Day(6, 5)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNotFound, b.Issue(null, "op", W3Demo.Day(6, 5)).ErrorCode);
        }

        [Fact]
        public void Kanban_ByStatus_Overdue_AndNextId()
        {
            var (b, _) = NewBoard();
            Draft(b, "SR-2026-01", W3Demo.Day(8, 30));
            Draft(b, "SR-2026-02", W3Demo.Day(7, 1));
            Draft(b, "SR-2026-07", W3Demo.Day(7, 1));
            b.Issue("SR-2026-02", "op", W3Demo.Day(6, 5));
            Assert.Equal(new[] { "SR-2026-01", "SR-2026-07" }, b.ByStatus(S.Draft).Select(r => r.Id));
            Assert.Equal("SR-2026-02", b.Overdue(W3Demo.Day(7, 2)).Single().Id);
            Assert.Empty(b.Overdue(W3Demo.Day(7, 1)));
            Assert.Equal("SR-2026-08", b.NextId(2026));
            Assert.Equal("SR-2027-01", b.NextId(2027));
            Assert.True(SafetyRecommendationBoard.IsValidId("SR-2026-100"));
            Assert.False(SafetyRecommendationBoard.IsValidId("SR-26-01"));
        }

        [Fact]
        public void AllowedNext_ReturnsDefensiveCopy()
        {
            var next = (S[])SafetyRecommendationBoard.AllowedNext(S.Draft);
            next[0] = S.Closed;
            Assert.False(SafetyRecommendationBoard.CanTransition(S.Draft, S.Closed));
            Assert.Empty(SafetyRecommendationBoard.AllowedNext(S.Closed));
        }

        private static void DriveTo(SafetyRecommendationBoard b, S target)
        {
            const string id = "SR-2026-01";
            if (target == S.Draft) return;
            Assert.True(b.Issue(id, "op", W3Demo.Day(6, 5)).IsSuccess);
            if (target == S.Issued) return;
            Assert.True(b.RecordResponse(id, "p", "t", "op", W3Demo.Day(6, 6)).IsSuccess);
            if (target == S.Responded) return;
            if (target == S.NotAdopted)
            {
                Assert.True(b.MarkNotAdopted(id, "op", W3Demo.Day(6, 7), "r").IsSuccess);
                return;
            }

            Assert.True(b.MarkImplemented(id, "op", W3Demo.Day(6, 7)).IsSuccess);
            if (target == S.Implemented) return;
            Assert.True(b.Close(id, "op", W3Demo.Day(6, 8)).IsSuccess);
        }
    }

    public class ConsultationTests
    {
        private static readonly ConsultationParty[] Parties =
        {
            new ConsultationParty("FLAG-A", "船旗国 A（Lily，虚构）"),
            new ConsultationParty("FLAG-B", "船旗国 B（Mary，虚构）"),
            new ConsultationParty("CO-LILY", "Lily 船公司（虚构）"),
        };

        private static (Consultation c, InMemoryInvestigationAuditSink audit) NewC()
        {
            var audit = new InMemoryInvestigationAuditSink();
            return (new Consultation("RPT-2026-LM01", audit), audit);
        }

        [Fact]
        public void OpenRound_DefaultsTo30Days_AndCountsDown()
        {
            var (c, audit) = NewC();
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "调查员 A（虚构）").Value;
            Assert.Equal(1, r.RoundNo);
            Assert.Equal(W3Demo.Day(7, 20), r.DeadlineUtc);
            Assert.False(r.IsAgreedDeadline);
            Assert.Equal(30, r.DaysRemaining(W3Demo.Day(6, 20)));
            Assert.Equal(12, r.DaysRemaining(W3Demo.Day(7, 8)));
            Assert.Equal(1, r.DaysRemaining(W3Demo.Day(7, 20, 8, 0)));
            Assert.Equal(0, r.DaysRemaining(W3Demo.Day(7, 21)));
            Assert.Equal("consultation.open", audit.Entries.Single().Action);
            Assert.Contains("默认 30 天", audit.Entries.Single().AfterValueSummary);
        }

        [Fact]
        public void OpenRound_AcceptsAgreedDeadline_AndValidates()
        {
            var (c, _) = NewC();
            Assert.Equal(Consultation.ErrInvalidArgument, c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op", W3Demo.Day(6, 20)).ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.OpenRound("v1", new ConsultationParty[0], W3Demo.Day(6, 20), "op").ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.OpenRound("v1", new[] { Parties[0], Parties[0] }, W3Demo.Day(6, 20), "op").ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.OpenRound("v1", new[] { new ConsultationParty("", "x") }, W3Demo.Day(6, 20), "op").ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.OpenRound("", Parties, W3Demo.Day(6, 20), "op").ErrorCode);
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op", W3Demo.Day(8, 4)).Value;
            Assert.True(r.IsAgreedDeadline);
            Assert.Equal(W3Demo.Day(8, 4), r.DeadlineUtc);
        }

        [Fact]
        public void OnlyOneOpenRound_NextRoundAfterClose()
        {
            var (c, _) = NewC();
            c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op");
            Assert.Equal(Consultation.ErrRoundOpen, c.OpenRound("v2", Parties, W3Demo.Day(6, 21), "op").ErrorCode);
            Assert.True(c.CloseRound(1, "op", W3Demo.Day(7, 21)).IsSuccess);
            Assert.Equal(Consultation.ErrInvalidArgument, c.OpenRound("v2", Parties, W3Demo.Day(7, 20), "op").ErrorCode);
            ConsultationRound r2 = c.OpenRound("v2", Parties, W3Demo.Day(7, 23), "op").Value;
            Assert.Equal(2, r2.RoundNo);
            Assert.Same(r2, c.CurrentRound);
            Assert.Equal(2, c.Rounds.Count);
        }

        [Fact]
        public void ReplyStatus_PendingRepliedLateOverdue()
        {
            var (c, _) = NewC();
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op").Value;
            c.RecordReply(1, "FLAG-A", W3Demo.Day(7, 1), "意见（虚构）", new[] { "3.2 节表述", "能见度数值" }, "op");
            c.RecordReply(1, "FLAG-B", W3Demo.Day(7, 25), "迟到意见（虚构）", null, "op");
            Assert.Equal(ReplyStatus.Replied, r.StatusOf("FLAG-A", W3Demo.Day(7, 30)));
            Assert.Equal(ReplyStatus.RepliedLate, r.StatusOf("FLAG-B", W3Demo.Day(7, 30)));
            Assert.Equal(ReplyStatus.Pending, r.StatusOf("CO-LILY", W3Demo.Day(7, 10)));
            Assert.Equal(ReplyStatus.Overdue, r.StatusOf("CO-LILY", W3Demo.Day(7, 30)));
            Assert.Equal(new[] { "C1-1", "C1-2" }, r.Comments.Select(x => x.CommentId));
            Assert.False(r.AllReplied);
        }

        [Fact]
        public void RecordReply_Rejections()
        {
            var (c, audit) = NewC();
            c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op");
            Assert.Equal(Consultation.ErrRoundNotFound, c.RecordReply(2, "FLAG-A", W3Demo.Day(7, 1), "t", null, "op").ErrorCode);
            Assert.Equal(Consultation.ErrUnknownParty, c.RecordReply(1, "NOBODY", W3Demo.Day(7, 1), "t", null, "op").ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.RecordReply(1, "FLAG-A", W3Demo.Day(6, 19), "t", null, "op").ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.RecordReply(1, "FLAG-A", W3Demo.Day(7, 1), "t", null, "").ErrorCode);
            Assert.True(c.RecordReply(1, "FLAG-A", W3Demo.Day(7, 1), "t", null, "op").IsSuccess);
            Assert.Equal(Consultation.ErrDuplicateReply, c.RecordReply(1, "FLAG-A", W3Demo.Day(7, 2), "t", null, "op").ErrorCode);
            c.CloseRound(1, "op", W3Demo.Day(7, 21));
            Assert.Equal(Consultation.ErrRoundClosed, c.RecordReply(1, "FLAG-B", W3Demo.Day(7, 22), "t", null, "op").ErrorCode);
            Assert.Equal(3, audit.Entries.Count);
        }

        [Fact]
        public void Adoption_RequiresWrittenFeedback_IsFinal_AndTallied()
        {
            var (c, audit) = NewC();
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op").Value;
            c.RecordReply(1, "FLAG-B", W3Demo.Day(7, 1), "t", new[] { "a", "b", "c", "d", "e" }, "op");
            Assert.Equal(Consultation.ErrInvalidArgument, c.DecideComment("C1-1", AdoptionDecision.NotAdopted, " ", "op", W3Demo.Day(7, 5)).ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.DecideComment("C1-1", AdoptionDecision.PartiallyAdopted, null, "op", W3Demo.Day(7, 5)).ErrorCode);
            Assert.Equal(Consultation.ErrInvalidArgument, c.DecideComment("C1-1", AdoptionDecision.Pending, "x", "op", W3Demo.Day(7, 5)).ErrorCode);
            Assert.Equal(Consultation.ErrCommentNotFound, c.DecideComment("C9-9", AdoptionDecision.Adopted, null, "op", W3Demo.Day(7, 5)).ErrorCode);
            Assert.True(c.DecideComment("C1-1", AdoptionDecision.Adopted, null, "op", W3Demo.Day(7, 5)).IsSuccess);
            Assert.True(c.DecideComment("C1-2", AdoptionDecision.Adopted, "已改", "op", W3Demo.Day(7, 5)).IsSuccess);
            ConsultationComment d = c.DecideComment("C1-3", AdoptionDecision.NotAdopted, "与 VDR 记录不符，维持原文", "调查员 A（虚构）", W3Demo.Day(7, 5)).Value;
            Assert.Equal("调查员 A（虚构）", d.DecidedBy);
            Assert.True(c.DecideComment("C1-4", AdoptionDecision.PartiallyAdopted, "调整措辞", "op", W3Demo.Day(7, 5)).IsSuccess);
            Assert.Equal(Consultation.ErrAlreadyDecided, c.DecideComment("C1-3", AdoptionDecision.Adopted, null, "op", W3Demo.Day(7, 6)).ErrorCode);
            AdoptionTally t = r.TallyFor("FLAG-B");
            Assert.Equal((2, 1, 1, 1, 5), (t.Adopted, t.PartiallyAdopted, t.NotAdopted, t.Pending, t.Total));
            Assert.Equal(0, r.TallyFor("FLAG-A").Total);
            Assert.Equal(5, r.TallyFor(null).Total);
            Assert.Equal(6, audit.Entries.Count);
            Assert.All(audit.Entries, e => Assert.Equal("Consultation", e.Category));
        }

        [Fact]
        public void CloseRound_OnlyWhenAllRepliedOrPastDeadline()
        {
            var (c, _) = NewC();
            c.OpenRound("v1", Parties.Take(2), W3Demo.Day(6, 20), "op");
            c.RecordReply(1, "FLAG-A", W3Demo.Day(7, 1), "t", null, "op");
            Assert.Equal(Consultation.ErrCannotClose, c.CloseRound(1, "op", W3Demo.Day(7, 10)).ErrorCode);
            Assert.Equal(Consultation.ErrCannotClose, c.CloseRound(1, "op", W3Demo.Day(7, 20).AddSeconds(-1)).ErrorCode);
            c.RecordReply(1, "FLAG-B", W3Demo.Day(7, 11), "t", null, "op");
            Assert.True(c.CloseRound(1, "op", W3Demo.Day(7, 12)).IsSuccess);
            Assert.Equal(Consultation.ErrRoundClosed, c.CloseRound(1, "op", W3Demo.Day(7, 13)).ErrorCode);
            Assert.Equal(Consultation.ErrRoundNotFound, c.CloseRound(5, "op", W3Demo.Day(7, 13)).ErrorCode);

            var (c2, _) = NewC();
            c2.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op");
            // 澄清 2：期限到达的那一刻（utc >= 期限）即可关闭
            Assert.True(c2.CloseRound(1, "op", W3Demo.Day(7, 20)).IsSuccess);
            Assert.Equal(W3Demo.Day(7, 20), c2.CurrentRound.ClosedUtc);
        }

        [Fact]
        public void Constructor_RequiresAuditSink()
        {
            Assert.Throws<ArgumentNullException>(() => new Consultation("r", null));
            Assert.Throws<ArgumentNullException>(() => new SafetyRecommendationBoard(null));
        }
    }
}
