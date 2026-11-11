using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Audit;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.Recommendations;
using Xunit;
using S = Mcis.Domain.Recommendations.RecommendationStatus;

namespace Mcis.W3.Tests
{
    /// <summary>W3 验收缺陷 D02–D06 的回归测试（示例数据虚构）。</summary>
    public class W3DefectFixTests
    {
        private static readonly string Sha = Sha256Hex.OfUtf8("示例数据（虚构）");
        private static readonly string Sha2 = Sha256Hex.OfUtf8("示例数据（虚构）2");

        // ---------- D02 落实进度与看板 ----------

        private static SafetyRecommendationBoard BoardAt(S target, out InMemoryInvestigationAuditSink audit)
        {
            audit = new InMemoryInvestigationAuditSink();
            var b = new SafetyRecommendationBoard(audit);
            Assert.True(b.CreateDraft("SR-2026-01", "t（虚构）", "Mary 轮公司（虚构）", new[] { "ECFC-E4" }, W3Demo.Day(8, 30), "op", W3Demo.Day(6, 1), caseId: "CASE-2026-LM01").IsSuccess);
            if (target == S.Draft) return b;
            b.Issue("SR-2026-01", "op", W3Demo.Day(6, 2));
            if (target == S.Issued) return b;
            b.RecordResponse("SR-2026-01", "Mary 轮公司（虚构）", "已开始修订 SMS（虚构）", "op", W3Demo.Day(6, 3));
            if (target == S.Responded) return b;
            if (target == S.NotAdopted) { b.MarkNotAdopted("SR-2026-01", "op", W3Demo.Day(6, 4), "r"); return b; }
            b.MarkImplemented("SR-2026-01", "op", W3Demo.Day(6, 4), "现场核实（虚构）");
            if (target == S.Implemented) return b;
            b.Close("SR-2026-01", "op", W3Demo.Day(6, 5), "关闭核实（虚构）");
            return b;
        }

        [Fact]
        public void D02_Progress_OnlyEditableInResponded_WithBoundsAndAudit()
        {
            SafetyRecommendationBoard b = BoardAt(S.Responded, out InMemoryInvestigationAuditSink audit);
            SafetyRecommendation r = b.Get("SR-2026-01");
            Assert.Equal(0, r.ProgressPct);
            int n = audit.Entries.Count;
            Assert.True(b.SetProgress("SR-2026-01", 0, "op", W3Demo.Day(6, 3)).IsSuccess);
            Assert.True(b.SetProgress("SR-2026-01", 60, "op", W3Demo.Day(6, 3), "培训完成一半").IsSuccess);
            Assert.True(b.SetProgress("SR-2026-01", 100, "op", W3Demo.Day(6, 3)).IsSuccess);
            Assert.Equal(100, r.ProgressPct);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidProgress, b.SetProgress("SR-2026-01", -1, "op", W3Demo.Day(6, 3)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidProgress, b.SetProgress("SR-2026-01", 101, "op", W3Demo.Day(6, 3)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.SetProgress("SR-2026-01", 50, " ", W3Demo.Day(6, 3)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNotFound, b.SetProgress("SR-2026-99", 50, "op", W3Demo.Day(6, 3)).ErrorCode);
            Assert.Equal(100, r.ProgressPct);
            Assert.Equal(n + 3, audit.Entries.Count);
            Assert.Equal("safetyrec.progress", audit.Entries.Last().Action);
            Assert.Equal("60%", audit.Entries[n + 2].BeforeValueSummary);
        }

        [Theory]
        [InlineData(S.Draft)]
        [InlineData(S.Issued)]
        [InlineData(S.Implemented)]
        [InlineData(S.NotAdopted)]
        [InlineData(S.Closed)]
        public void D02_Progress_RejectedOutsideResponded(S state)
        {
            SafetyRecommendationBoard b = BoardAt(state, out InMemoryInvestigationAuditSink audit);
            int before = b.Get("SR-2026-01").ProgressPct;
            int n = audit.Entries.Count;
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, b.SetProgress("SR-2026-01", 40, "op", W3Demo.Day(6, 10)).ErrorCode);
            Assert.Equal(before, b.Get("SR-2026-01").ProgressPct);
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void D02_EnteringImplemented_SetsProgress100_AndVerificationNote()
        {
            SafetyRecommendationBoard b = BoardAt(S.Responded, out _);
            b.SetProgress("SR-2026-01", 35, "op", W3Demo.Day(6, 3));
            b.MarkImplemented("SR-2026-01", "op", W3Demo.Day(6, 4), "现场核实（虚构）");
            SafetyRecommendation r = b.Get("SR-2026-01");
            Assert.Equal(100, r.ProgressPct);
            Assert.Equal("现场核实（虚构）", r.VerificationNote);
            Assert.Equal("已开始修订 SMS（虚构）", r.ResponseSummary);
            Assert.Equal("CASE-2026-LM01", r.CaseId);
            b.Close("SR-2026-01", "op", W3Demo.Day(6, 5), "关闭核实（虚构）");
            Assert.Equal("关闭核实（虚构）", r.VerificationNote);
            Assert.Equal(100, r.ProgressPct);
        }

        [Fact]
        public void D02_NotAdopted_KeepsProgress_AndResponseSummaryEmptyBeforeReply()
        {
            SafetyRecommendationBoard b = BoardAt(S.Issued, out _);
            Assert.Equal(string.Empty, b.Get("SR-2026-01").ResponseSummary);
            b.RecordResponse("SR-2026-01", "p", "不同意", "op", W3Demo.Day(6, 3));
            b.SetProgress("SR-2026-01", 20, "op", W3Demo.Day(6, 3));
            b.MarkNotAdopted("SR-2026-01", "op", W3Demo.Day(6, 4), "理由（虚构）");
            Assert.Equal(20, b.Get("SR-2026-01").ProgressPct);
            Assert.Equal(string.Empty, b.Get("SR-2026-01").VerificationNote);
        }

        [Theory]
        [InlineData(S.Draft, KanbanColumn.Draft, "草拟")]
        [InlineData(S.Issued, KanbanColumn.Issued, "已发布")]
        [InlineData(S.Responded, KanbanColumn.InProgress, "落实中")]
        [InlineData(S.Implemented, KanbanColumn.Closed, "已关闭")]
        [InlineData(S.NotAdopted, KanbanColumn.Closed, "已关闭")]
        [InlineData(S.Closed, KanbanColumn.Closed, "已关闭")]
        public void D02_KanbanMapping(S status, KanbanColumn column, string label)
        {
            Assert.Equal(column, SafetyRecommendationBoard.ToKanbanColumn(status));
            Assert.Equal(label, SafetyRecommendationBoard.KanbanLabel(column));
            SafetyRecommendationBoard b = BoardAt(status, out _);
            Assert.Equal(column, b.Get("SR-2026-01").Column);
            Assert.Single(b.ByKanbanColumn(column));
        }

        [Fact]
        public void D02_CaseIdFormat_IsValidated()
        {
            var b = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidCaseId, b.CreateDraft("SR-2026-01", "t", "a", new[] { "N" }, W3Demo.Day(8, 1), "op", W3Demo.Day(6, 1), caseId: "案件 1").ErrorCode);
            Assert.Equal(string.Empty, b.CreateDraft("SR-2026-02", "t", "a", new[] { "N" }, W3Demo.Day(8, 1), "op", W3Demo.Day(6, 1)).Value.CaseId);
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        public void Clarification3_EmptyRecommendationId_IsRejected(string id)
        {
            var b = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidId, b.CreateDraft(id, "t", "a", new[] { "N" }, W3Demo.Day(8, 1), "op", W3Demo.Day(6, 1)).ErrorCode);
            Assert.Empty(b.All);
        }

        // ---------- D03 证据：案件号、保密、需复核 ----------

        [Fact]
        public void D03_EvidenceItem_CaseIdAndConfidentiality_RoundTripThroughLedger()
        {
            var l = new CustodyLedger();
            var item = new EvidenceItem("EV-006", "询问笔录 IR-01…IR-06（虚构）", "询问室", "调查员 A（虚构）", W3Demo.Day(5, 19), Sha, "testimony/ir.zip", "CASE-2026-LM01", EvidenceConfidentiality.Restricted);
            Assert.True(l.Register(item, "op", W3Demo.Day(5, 19)).IsSuccess);
            Assert.True(l.Get("EV-006").IsRestricted);
            Assert.Contains("\"case_id\":\"CASE-2026-LM01\"", l.JsonLines[0]);
            Assert.Contains("\"confidentiality\":\"Restricted\"", l.JsonLines[0]);
            CustodyLedger r = CustodyLedger.Load(l.JsonLines).Value;
            Assert.Equal("CASE-2026-LM01", r.Get("EV-006").CaseId);
            Assert.Equal(EvidenceConfidentiality.Restricted, r.Get("EV-006").Confidentiality);
        }

        [Fact]
        public void D03_DefaultFields_KeepLegacyLineFormat()
        {
            var l = new CustodyLedger();
            l.Register(new EvidenceItem("EV-001", "t", "s", "x", W3Demo.Day(5, 18), Sha), "op", W3Demo.Day(5, 18));
            Assert.DoesNotContain("case_id", l.JsonLines[0]);
            Assert.DoesNotContain("confidentiality", l.JsonLines[0]);
            Assert.Equal(EvidenceConfidentiality.Normal, l.Get("EV-001").Confidentiality);
        }

        [Fact]
        public void D03_InvalidCaseId_IsRejected()
        {
            var l = new CustodyLedger();
            Assert.Equal(CustodyLedger.ErrInvalidCaseId, l.Register(new EvidenceItem("EV-001", "t", "s", "x", W3Demo.Day(5, 18), Sha, null, "a b"), "op", W3Demo.Day(5, 18)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidCaseId, l.Register(new EvidenceItem("EV-001", "t", "s", "x", W3Demo.Day(5, 18), Sha, null, "AB"), "op", W3Demo.Day(5, 18)).ErrorCode);
        }

        [Fact]
        public void D03_NeedsReview_IsAppendOnlyAnnotation_AndStatusIsDerived()
        {
            var l = new CustodyLedger();
            l.Register(new EvidenceItem("EV-005", "车钟纸本（虚构）", "机舱", "x", W3Demo.Day(5, 19), Sha), "op", W3Demo.Day(5, 19));
            Assert.Equal(EvidenceStatus.Unverified, l.StatusOf("EV-005"));
            l.Verify("EV-005", "op", W3Demo.Day(5, 20), Sha);
            Assert.Equal(EvidenceStatus.Verified, l.StatusOf("EV-005"));

            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.MarkNeedsReview("EV-005", "调查员 A（虚构）", W3Demo.Day(5, 21), " ").ErrorCode);
            CustodyEvent mark = l.MarkNeedsReview("EV-005", "调查员 A（虚构）", W3Demo.Day(5, 21), "纸本字迹模糊").Value;
            Assert.Equal(CustodyEventKind.Review, mark.Kind);
            Assert.Equal(EvidenceStatus.NeedsReview, l.StatusOf("EV-005"));
            Assert.True(l.IsMarkedNeedsReview("EV-005"));
            Assert.Equal(CustodyLedger.ErrNoReviewChange, l.MarkNeedsReview("EV-005", "op", W3Demo.Day(5, 21), "again").ErrorCode);

            AuditRecord rec = AuditRecord.FromJsonLine(l.JsonLines.Last());
            Assert.Equal(CustodyEvent.ActionReview, rec.Action);
            Assert.Equal("NeedsReview", rec.AfterValueSummary);

            Assert.True(l.ResolveNeedsReview("EV-005", "op", W3Demo.Day(5, 22), "已与电子记录核对").IsSuccess);
            Assert.Equal(EvidenceStatus.Verified, l.StatusOf("EV-005"));
            Assert.Equal(CustodyLedger.ErrNoReviewChange, l.ResolveNeedsReview("EV-005", "op", W3Demo.Day(5, 22), "x").ErrorCode);
            Assert.Equal(CustodyLedger.ErrUnknownEvidence, l.MarkNeedsReview("EV-404", "op", W3Demo.Day(5, 22), "x").ErrorCode);
            Assert.Null(l.StatusOf("EV-404"));

            CustodyLedger re = CustodyLedger.Load(l.JsonLines).Value;
            Assert.Equal(EvidenceStatus.Verified, re.StatusOf("EV-005"));
            l.MarkNeedsReview("EV-005", "op", W3Demo.Day(5, 23), "再查");
            Assert.Equal(EvidenceStatus.NeedsReview, CustodyLedger.Load(l.JsonLines).Value.StatusOf("EV-005"));
        }

        [Fact]
        public void D03_Status_MismatchAndResetAfterChange()
        {
            var l = new CustodyLedger();
            l.Register(new EvidenceItem("EV-001", "t", "s", "x", W3Demo.Day(5, 18), Sha), "op", W3Demo.Day(5, 18));
            l.Verify("EV-001", "op", W3Demo.Day(5, 19), Sha2);
            Assert.Equal(EvidenceStatus.Mismatch, l.StatusOf("EV-001"));
            l.RecordChange("EV-001", "op", W3Demo.Day(5, 20), Sha2, "派生");
            Assert.Equal(EvidenceStatus.Unverified, l.StatusOf("EV-001"));
        }

        // ---------- D05 编号格式 ----------

        [Theory]
        [InlineData("EV-001", true)]
        [InlineData("EV-1234", true)]
        [InlineData("EV-01", false)]
        [InlineData("ev-001", false)]
        [InlineData("EV-00A", false)]
        [InlineData("NOT-EV", false)]
        [InlineData(" EV-001", false)]
        public void D05_EvidenceIdPattern(string id, bool ok)
        {
            var l = new CustodyLedger();
            Result<CustodyEvent> r = l.Register(new EvidenceItem(id, "t", "s", "x", W3Demo.Day(5, 18), Sha), "op", W3Demo.Day(5, 18));
            Assert.Equal(ok, r.IsSuccess);
            if (!ok)
            {
                Assert.Equal(CustodyLedger.ErrInvalidId, r.ErrorCode);
            }
        }

        [Theory]
        [InlineData("IR-03", true)]
        [InlineData("IR-100", true)]
        [InlineData("IR-3", false)]
        [InlineData("ir-03", false)]
        [InlineData("NOT-A-VALID-ID", false)]
        [InlineData("", false)]
        [InlineData(null, false)]
        public void D05_InterviewRecordIdPattern(string id, bool ok)
        {
            var who = new Interviewee("P", "n", "r", "a");
            if (ok)
            {
                Assert.Equal(id, new InterviewRecord(id, who, W3Demo.Day(5, 19)).RecordId);
            }
            else
            {
                Assert.Throws<ArgumentException>(() => new InterviewRecord(id, who, W3Demo.Day(5, 19)));
            }
        }

        // ---------- D04 笔录签字、案件号、陈述复核与修改 ----------

        [Fact]
        public void D04_Record_SignedAndCaseId()
        {
            var who = new Interviewee("P", "n", "r", "a");
            var ir = new InterviewRecord("IR-03", who, W3Demo.Day(5, 19), caseId: "CASE-2026-LM01");
            Assert.Equal("CASE-2026-LM01", ir.CaseId);
            Assert.False(ir.Signed);
            ir.MarkSigned();
            Assert.True(ir.Signed);
            Assert.True(new InterviewRecord("IR-04", who, W3Demo.Day(5, 19), signed: true).Signed);
            Assert.Throws<ArgumentException>(() => new InterviewRecord("IR-05", who, W3Demo.Day(5, 19), caseId: "x y"));
            Assert.Equal(string.Empty, new InterviewRecord("IR-06", who, W3Demo.Day(5, 19)).CaseId);
        }

        private static (InterviewRecord ir, InMemoryInvestigationAuditSink audit) WithStatement(StatementOrigin origin = StatementOrigin.Agent)
        {
            InterviewRecord ir = W3Demo.Ir03();
            ir.AddStatement("S-03-3", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), ir.Locate(2, QaField.Answer, "左舵 20 度").Value, W3Demo.At(14, 23), origin);
            return (ir, new InMemoryInvestigationAuditSink());
        }

        [Fact]
        public void D04_NewStatement_IsDraft_WithOrigin()
        {
            var (ir, _) = WithStatement();
            Statement st = ir.GetStatement("S-03-3");
            Assert.Equal(StatementReviewStatus.Draft, st.ReviewStatus);
            Assert.Equal(StatementOrigin.Agent, st.ExtractedBy);
            Assert.Equal(1, st.Revision);
            var (ir2, _) = WithStatement(StatementOrigin.Investigator);
            Assert.Equal(StatementReviewStatus.Draft, ir2.GetStatement("S-03-3").ReviewStatus);
            Assert.Equal(StatementOrigin.Investigator, ir2.GetStatement("S-03-3").ExtractedBy);
            Assert.Null(ir.GetStatement("nope"));
        }

        [Fact]
        public void D04_ModifyStatement_ProducesModifiedRevision_WithAudit()
        {
            var (ir, audit) = WithStatement();
            SourceSpan span = ir.Locate(2, QaField.Answer, "左舵 20 度").Value;
            Statement m = ir.ModifyStatement("S-03-3", "左舵约 20°（修正）", StatementClaim.ScalarValue(15, "deg"), span, W3Demo.At(14, 23), "调查员 A（虚构）", W3Demo.Day(5, 20), audit).Value;
            Assert.Equal(StatementReviewStatus.Modified, m.ReviewStatus);
            Assert.Equal(2, m.Revision);
            Assert.Equal(15, m.Claim.Scalar);
            Assert.Equal("左舵 20 度", m.Quote);
            Assert.Same(m, ir.GetStatement("S-03-3"));
            Assert.Single(ir.Statements);
            InvestigationAuditEntry a = audit.Entries.Single();
            Assert.Equal(InterviewRecord.ActionStatementModify, a.Action);
            Assert.StartsWith("r1", a.BeforeValueSummary);
            Assert.StartsWith("r2", a.AfterValueSummary);
            Assert.Equal(a.ToJsonLine(), AuditRecord.FromJsonLine(a.ToJsonLine()).ToJsonLine());
            Assert.Equal(3, ir.ModifyStatement("S-03-3", "再改", StatementClaim.ScalarValue(16, "deg"), span, null, "inv", W3Demo.Day(5, 20), audit).Value.Revision);
        }

        [Fact]
        public void D04_ModifyStatement_Rejections()
        {
            var (ir, audit) = WithStatement();
            SourceSpan span = ir.Locate(2, QaField.Answer, "左舵 20 度").Value;
            Assert.Equal(InterviewRecord.ErrStatementNotFound, ir.ModifyStatement("S-X", "s", StatementClaim.Occurrence(true), span, null, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.ModifyStatement("S-03-3", "s", null, span, null, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.ModifyStatement("S-03-3", "s", StatementClaim.Occurrence(true), span, null, " ", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Equal(InterviewRecord.ErrSpanOutOfRange, ir.ModifyStatement("S-03-3", "s", StatementClaim.Occurrence(true), new SourceSpan(9, QaField.Answer, 0, 1), null, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Throws<ArgumentNullException>(() => ir.ModifyStatement("S-03-3", "s", StatementClaim.Occurrence(true), span, null, "inv", W3Demo.Day(5, 20), null));
            Assert.Empty(audit.Entries);
            Assert.True(ir.ReviewStatement("S-03-3", StatementReviewStatus.Confirmed, "inv", W3Demo.Day(5, 20), audit).IsSuccess);
            Assert.Equal(InterviewRecord.ErrNotEditable, ir.ModifyStatement("S-03-3", "s", StatementClaim.Occurrence(true), span, null, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
        }

        [Fact]
        public void D04_ReviewStatement_ConfirmRejectRules()
        {
            var (ir, audit) = WithStatement();
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.ReviewStatement("S-03-3", StatementReviewStatus.Modified, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.ReviewStatement("S-03-3", StatementReviewStatus.Rejected, "inv", W3Demo.Day(5, 20), audit, " ").ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.ReviewStatement("S-03-3", StatementReviewStatus.Confirmed, "", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Equal(InterviewRecord.ErrStatementNotFound, ir.ReviewStatement("S-X", StatementReviewStatus.Confirmed, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
            Statement r = ir.ReviewStatement("S-03-3", StatementReviewStatus.Rejected, "调查员 A（虚构）", W3Demo.Day(5, 20), audit, "原文不支持").Value;
            Assert.Equal(StatementReviewStatus.Rejected, r.ReviewStatus);
            Assert.Equal("调查员 A（虚构）", r.ReviewedBy);
            Assert.Equal(W3Demo.Day(5, 20), r.ReviewedUtc);
            Assert.Equal(InterviewRecord.ErrNotEditable, ir.ReviewStatement("S-03-3", StatementReviewStatus.Confirmed, "inv", W3Demo.Day(5, 20), audit).ErrorCode);
            Assert.Single(audit.Entries);
            Assert.Equal(InterviewRecord.ActionStatementReview, audit.Entries[0].Action);
        }

        // ---------- D06 征求意见 caseId / Waived / 草案哈希 ----------

        private static readonly ConsultationParty[] Parties =
        {
            new ConsultationParty("FLAG-A", "船旗国 A（虚构）"),
            new ConsultationParty("FLAG-B", "船旗国 B（虚构）"),
        };

        [Fact]
        public void D06_CaseIdAndDraftSha256()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT-2026-LM01", audit, "CASE-2026-LM01");
            Assert.Equal("CASE-2026-LM01", c.CaseId);
            Assert.Equal(Consultation.ErrInvalidSha256, c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op", null, "abc").ErrorCode);
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op", null, Sha.ToUpperInvariant()).Value;
            Assert.Equal(Sha, r.DraftSha256);
            Assert.Contains(Sha, audit.Entries.Last().AfterValueSummary);
            Assert.Throws<ArgumentException>(() => new Consultation("r", audit, "a b"));
            Assert.Equal(string.Empty, new Consultation("r", audit).CaseId);
        }

        [Fact]
        public void D06_Waived_CountsAsSettled_AndIsExclusiveWithReply()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT", audit);
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op").Value;
            Assert.Equal(Consultation.ErrInvalidArgument, c.WaiveReply(1, "FLAG-B", "op", W3Demo.Day(6, 25), " ").ErrorCode);
            Assert.Equal(Consultation.ErrUnknownParty, c.WaiveReply(1, "X", "op", W3Demo.Day(6, 25), "r").ErrorCode);
            Assert.Equal(Consultation.ErrRoundNotFound, c.WaiveReply(2, "FLAG-B", "op", W3Demo.Day(6, 25), "r").ErrorCode);
            Assert.True(c.WaiveReply(1, "FLAG-B", "op", W3Demo.Day(6, 25), "书面声明不提意见").IsSuccess);
            Assert.Equal(ReplyStatus.Waived, r.StatusOf("FLAG-B", W3Demo.Day(8, 1)));
            Assert.True(r.IsWaived("FLAG-B"));
            Assert.Equal(Consultation.ErrDuplicateReply, c.RecordReply(1, "FLAG-B", W3Demo.Day(6, 26), "t", null, "op").ErrorCode);
            Assert.Equal(Consultation.ErrDuplicateReply, c.WaiveReply(1, "FLAG-B", "op", W3Demo.Day(6, 26), "r").ErrorCode);
            c.RecordReply(1, "FLAG-A", W3Demo.Day(6, 27), "t", null, "op");
            Assert.Equal(Consultation.ErrDuplicateReply, c.WaiveReply(1, "FLAG-A", "op", W3Demo.Day(6, 28), "r").ErrorCode);
            Assert.True(r.AllReplied);
            Assert.True(c.CloseRound(1, "op", W3Demo.Day(6, 28)).IsSuccess);
            Assert.Equal(Consultation.ErrRoundClosed, c.WaiveReply(1, "FLAG-A", "op", W3Demo.Day(6, 29), "r").ErrorCode);
            Assert.Contains(audit.Entries, e => e.Action == "consultation.waive");
        }

        [Fact]
        public void Clarification2_CloseAllowedAtDeadlineInstant()
        {
            var c = new Consultation("RPT", new InMemoryInvestigationAuditSink());
            ConsultationRound r = c.OpenRound("v1", Parties, W3Demo.Day(6, 20), "op").Value;
            Assert.Equal(Consultation.ErrCannotClose, c.CloseRound(1, "op", r.DeadlineUtc.AddTicks(-1)).ErrorCode);
            Assert.True(c.CloseRound(1, "op", r.DeadlineUtc).IsSuccess);
        }
    }
}
