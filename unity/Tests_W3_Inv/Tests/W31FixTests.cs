using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.Recommendations;
using Xunit;

namespace Mcis.W3.Tests
{
    /// <summary>W3.1：D07–D10 + UpdateDraft + confirmedInBatch 序列化（示例数据·虚构）。</summary>
    public class W31FixTests
    {
        private sealed class FailOnNthSink : IInvestigationAuditSink
        {
            private readonly int _failAt;
            public int Calls;
            public readonly List<InvestigationAuditEntry> Written = new List<InvestigationAuditEntry>();

            public FailOnNthSink(int failAt) { _failAt = failAt; }

            public void Append(InvestigationAuditEntry entry)
            {
                Calls++;
                if (Calls == _failAt)
                {
                    throw new System.IO.IOException("audit unavailable (simulated)");
                }

                Written.Add(entry);
            }
        }

        private static CrossCheckResult Consistent(string id)
        {
            return new CrossCheckResult(id, "IR-03", CrossCheckOutcome.Consistent, 0, "nm", "3 nm", "3 nm", "AIS（虚构）", "|Δ|≤0.1");
        }

        // ---------- D07 ----------

        [Fact]
        public void D07_BatchAuditFailureMidway_RollsBackAll_AndWritesAbortRecord()
        {
            var sink = new FailOnNthSink(5); // 3 次 Submit；批量第 2 条审计失败
            var reg = new CrossCheckRegister(sink);
            foreach (var id in new[] { "S-1", "S-2", "S-3" })
            {
                Assert.True(reg.Submit(Consistent(id), "智能体（虚构）", W3Demo.Day(5, 19, 11)).IsSuccess);
            }

            Result<IReadOnlyList<CrossCheckEntry>> r = reg.ConfirmConsistentBatch(new[] { "S-1", "S-2", "S-3" }, "调查员甲", W3Demo.Day(5, 19, 12));
            Assert.False(r.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            Assert.All(reg.Entries, e => Assert.Equal(CrossCheckState.PendingConfirmation, e.State));
            Assert.All(reg.Entries, e => Assert.False(e.ConfirmedInBatch));
            Assert.All(reg.Entries, e => Assert.Null(e.DecidedBy));
            // 已预写的 1 条批量审计之后，追加一条作废记录
            Assert.Equal(CrossCheckRegister.ActionBatchAbort, sink.Written.Last().Action);
        }

        [Fact]
        public void D07_BatchSucceeds_WhenAuditHealthy_AndAuditBeforeStateChange()
        {
            var sink = new FailOnNthSink(int.MaxValue);
            var reg = new CrossCheckRegister(sink);
            reg.Submit(Consistent("S-1"), "a", W3Demo.Day(5, 19, 11));
            reg.Submit(Consistent("S-2"), "a", W3Demo.Day(5, 19, 11));
            var r = reg.ConfirmConsistentBatch(new[] { "S-1", "S-2" }, "调查员甲", W3Demo.Day(5, 19, 12));
            Assert.True(r.IsSuccess);
            Assert.All(reg.Entries, e => Assert.True(e.IsEffective && e.ConfirmedInBatch));
            Assert.Equal(2, sink.Written.Count(w => w.Action == CrossCheckRegister.ActionBatchConfirm));
        }

        // ---------- D08 ----------

        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        [InlineData(double.NegativeInfinity)]
        public void D08_NonFiniteClaim_RejectedOnAdd(double bad)
        {
            InterviewRecord ir = W3Demo.Ir03();
            SourceSpan span = ir.Locate(1, QaField.Answer, "3 海里").Value;
            var r = ir.AddStatement("S-x", StatementKind.Observation, "q", "3 海里", StatementClaim.ScalarValue(bad, "nm"), span);
            Assert.Equal("inv_invalid_number", r.ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidNumber, r.ErrorCode);
            Assert.Empty(ir.Statements);
        }

        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        public void D08_NonFinitePositionClaim_Rejected(double bad)
        {
            InterviewRecord ir = W3Demo.Ir03();
            SourceSpan span = ir.Locate(1, QaField.Answer, "3 号浮标北面").Value;
            var r = ir.AddStatement("S-p", StatementKind.Position, "Mary.position_1417", "3 号浮标北面", StatementClaim.At(new Mcis.Domain.Common.GeoCoord(bad, 21.8)), span);
            Assert.Equal("inv_invalid_number", r.ErrorCode);
        }

        [Fact]
        public void D08_NonFiniteClaim_RejectedOnModify()
        {
            InterviewRecord ir = W3Demo.Ir03();
            SourceSpan span = ir.Locate(1, QaField.Answer, "3 海里").Value;
            ir.AddStatement("S-x", StatementKind.Observation, "q", "3 海里", StatementClaim.ScalarValue(3, "nm"), span);
            var r = ir.ModifyStatement("S-x", "3 海里", StatementClaim.ScalarValue(double.NaN, "nm"), span, null, "调查员甲", W3Demo.Day(5, 20), new InMemoryInvestigationAuditSink());
            Assert.Equal("inv_invalid_number", r.ErrorCode);
            Assert.Equal(3.0, ir.GetStatement("S-x").Claim.Scalar);
        }

        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        [InlineData(double.NegativeInfinity)]
        public void D08_NonFiniteObservation_IsUnverifiable(double bad)
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = ir.AddStatement("S-x", StatementKind.Observation, "q", "3 海里", StatementClaim.ScalarValue(3, "nm"), ir.Locate(1, QaField.Answer, "3 海里").Value).Value;
            var src = new FakeDataSource().Set("q", DataObservation.ScalarValue(bad, "nm", "AIS（虚构）"));
            CrossCheckResult r = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("q", 0.1)).Check(s, src);
            Assert.Equal(CrossCheckOutcome.Unverifiable, r.Outcome);
            Assert.Contains("无效数值", r.Rule);
        }

        [Fact]
        public void D08_UnitConversion_RejectsNonFinite()
        {
            Assert.False(UnitConversion.TryConvert(double.NaN, "kn", "m/s", out _));
            Assert.False(UnitConversion.TryConvert(double.PositiveInfinity, "nm", "m", out _));
        }

        // ---------- D09 ----------

        [Theory]
        [InlineData("EV-001\n")]
        [InlineData("EV-001\r\n")]
        [InlineData("EV-\u0660\u0660\u0661")]
        public void D09_EvidenceId_NewlineOrNonAsciiDigits_Rejected(string id)
        {
            Assert.False(EvidenceItem.IsValidId(id));
        }

        [Theory]
        [InlineData("CASE-1\n")]
        public void D09_CaseId_TrailingNewline_Rejected(string id)
        {
            Assert.False(EvidenceItem.IsValidCaseId(id));
        }

        [Fact]
        public void D09_InterviewRecordId_TrailingNewline_Rejected()
        {
            var who = new Interviewee("P", "n", "r", "a");
            Assert.Throws<ArgumentException>(() => new InterviewRecord("IR-03\n", who, W3Demo.Day(5, 19)));
            Assert.Throws<ArgumentException>(() => new InterviewRecord("IR-\u0660\u0663", who, W3Demo.Day(5, 19)));
        }

        [Theory]
        [InlineData("SR-2026-01\n")]
        [InlineData("SR-2026-\u0660\u0661")]
        [InlineData("SR-\u0662\u0660\u0662\u0666-01")]
        [InlineData("SR-2026-\uff10\uff11")]
        public void D09_RecommendationId_Rejected(string id)
        {
            Assert.False(SafetyRecommendationBoard.IsValidId(id));
        }

        [Fact]
        public void D09_ValidIdsStillAccepted()
        {
            Assert.True(EvidenceItem.IsValidId("EV-001"));
            Assert.True(EvidenceItem.IsValidCaseId("CASE-2026-LM01"));
            Assert.True(SafetyRecommendationBoard.IsValidId("SR-2026-01"));
            Assert.True(SafetyRecommendationBoard.IsValidId("SR-2026-123"));
        }

        // ---------- D10 ----------

        [Theory]
        [InlineData("m·s⁻¹")]
        [InlineData("m⋅s⁻¹")]
        [InlineData("m s⁻¹")]
        [InlineData("m.s-1")]
        [InlineData("m s-1")]
        [InlineData("m/s")]
        [InlineData("mps")]
        [InlineData("MPS")]
        public void D10_MetresPerSecondAliases_AreKnown(string unit)
        {
            Assert.True(UnitConversion.IsKnown(unit), unit);
            Assert.True(UnitConversion.TryConvert(1.0, "kn", unit, out double r));
            Assert.Equal(1852.0 / 3600.0, r, 9);
        }

        // ---------- UpdateDraft ----------

        private static (SafetyRecommendationBoard board, InMemoryInvestigationAuditSink audit) Board()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var b = new SafetyRecommendationBoard(audit);
            Assert.True(b.CreateDraft("SR-2026-01", "雾中单向通航（虚构）", "星屿 VTS（虚构）", new[] { "C4" }, W3Demo.Day(8, 1), "调查员甲", W3Demo.Day(6, 1)).IsSuccess);
            return (b, audit);
        }

        [Fact]
        public void UpdateDraft_ChangesFields_AndAudits()
        {
            var (b, audit) = Board();
            var r = b.UpdateDraft("SR-2026-01", "调查员乙", W3Demo.Day(6, 2), title: "雾中单向通航与限速（虚构）", body: "正文（虚构）", causeNodeIds: new[] { "C4", "E4", " " }, dueUtc: W3Demo.Day(9, 1), isInterim: true);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            var rec = b.Get("SR-2026-01");
            Assert.Equal("雾中单向通航与限速（虚构）", rec.Title);
            Assert.Equal("正文（虚构）", rec.Body);
            Assert.Equal("星屿 VTS（虚构）", rec.Addressee); // 未传 → 不变
            Assert.Equal(new[] { "C4", "E4" }, rec.CauseNodeIds);
            Assert.Equal(W3Demo.Day(9, 1), rec.DueUtc);
            Assert.True(rec.IsInterim);
            var last = audit.Entries.Last();
            Assert.Equal("safetyrec.update", last.Action);
            Assert.Equal(SafetyRecommendationBoard.ActionUpdate, last.Action);
            Assert.Contains("雾中单向通航（虚构）", last.BeforeValueSummary);
            Assert.Contains("雾中单向通航与限速（虚构）", last.AfterValueSummary);
        }

        [Fact]
        public void UpdateDraft_OnlyInDraft()
        {
            var (b, audit) = Board();
            b.Issue("SR-2026-01", "调查员甲", W3Demo.Day(6, 3));
            int n = audit.Entries.Count;
            var r = b.UpdateDraft("SR-2026-01", "调查员甲", W3Demo.Day(6, 4), title: "x");
            Assert.Equal(SafetyRecommendationBoard.ErrNotDraft, r.ErrorCode);
            Assert.Equal("雾中单向通航（虚构）", b.Get("SR-2026-01").Title);
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void UpdateDraft_ValidationErrors_NoChangeNoAudit()
        {
            var (b, audit) = Board();
            int n = audit.Entries.Count;
            Assert.Equal(SafetyRecommendationBoard.ErrNotFound, b.UpdateDraft("SR-2026-99", "甲", W3Demo.Day(6, 2), title: "x").ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.UpdateDraft("SR-2026-01", " ", W3Demo.Day(6, 2), title: "x").ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2), title: "  ").ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2), addressee: "").ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrNoCauseLink, b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2), causeNodeIds: new[] { " " }).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2), dueUtc: W3Demo.Day(6, 2)).ErrorCode);
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2)).ErrorCode); // 无任何改动
            Assert.Equal(SafetyRecommendationBoard.ErrInvalidArgument, b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2), title: "雾中单向通航（虚构）").ErrorCode); // 与原值相同
            Assert.Equal(n, audit.Entries.Count);
            Assert.Equal("雾中单向通航（虚构）", b.Get("SR-2026-01").Title);
        }

        [Fact]
        public void UpdateDraft_AuditFailure_LeavesDraftUnchanged()
        {
            var sink = new FailOnNthSink(2); // 第 1 次 create 成功，第 2 次 update 失败
            var b = new SafetyRecommendationBoard(sink);
            b.CreateDraft("SR-2026-01", "t（虚构）", "a（虚构）", new[] { "C4" }, W3Demo.Day(8, 1), "甲", W3Demo.Day(6, 1));
            Assert.Throws<System.IO.IOException>(() => b.UpdateDraft("SR-2026-01", "甲", W3Demo.Day(6, 2), title: "t2"));
            Assert.Equal("t（虚构）", b.Get("SR-2026-01").Title);
        }

        // ---------- confirmedInBatch 序列化 ----------

        [Fact]
        public void CrossCheckEntry_ToJson_UsesContractCamelCaseKeys()
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            reg.Submit(Consistent("S-1"), "a", W3Demo.Day(5, 19, 11));
            string pending = reg.Get("S-1").ToJson();
            Assert.Contains("\"confirmedInBatch\":false", pending);
            Assert.Contains("\"state\":\"PendingConfirmation\"", pending);
            Assert.Contains("\"decidedBy\":null", pending);
            Assert.Contains("\"decidedUtc\":null", pending);
            Assert.DoesNotContain("ConfirmedInBatch", pending);

            reg.ConfirmConsistentBatch(new[] { "S-1" }, "调查员\"甲\"", W3Demo.Day(5, 19, 12));
            string json = reg.Get("S-1").ToJson();
            Assert.StartsWith("{\"statementId\":\"S-1\",\"recordId\":\"IR-03\",\"outcome\":\"Consistent\",\"delta\":0,\"deltaUnit\":\"nm\",", json);
            Assert.Contains("\"confirmedInBatch\":true", json);
            Assert.Contains("\"state\":\"Confirmed\"", json);
            Assert.Contains("\"decidedBy\":\"调查员\\\"甲\\\"\"", json);
            Assert.Contains("\"decidedUtc\":\"2026-05-19T04:00:00.000Z\"", json); // W3.2：毫秒
            Assert.EndsWith("\"confirmedInBatch\":true,\"statementVersion\":1}", json); // W5.1：statementVersion 为最后一键

            // 键集合与契约 crossCheckResult 一致
            var keys = System.Text.RegularExpressions.Regex.Matches(json, "\"([A-Za-z]+)\":").Cast<System.Text.RegularExpressions.Match>().Select(m => m.Groups[1].Value).ToArray();
            Assert.Equal(new[] { "statementId", "recordId", "outcome", "delta", "deltaUnit", "claimedText", "observedText", "sourceLabel", "rule", "state", "decidedBy", "decidedUtc", "note", "confirmedInBatch", "statementVersion" }, keys);
        }

        [Fact]
        public void CrossCheckEntry_ToJson_NullDelta()
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            reg.Submit(new CrossCheckResult("S-9", "IR-03", CrossCheckOutcome.Unverifiable, null, null, "x", "无数据", "虚构", "无数据"), "a", W3Demo.Day(5, 19, 11));
            string json = reg.Get("S-9").ToJson();
            Assert.Contains("\"delta\":null", json);
            Assert.Contains("\"deltaUnit\":\"\"", json);
        }
    }
}
