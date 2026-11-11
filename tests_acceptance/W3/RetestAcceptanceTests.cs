using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.Recommendations;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>
    /// W3 复测（2026-11-11，Codex）新增验收：批量确认全有或全无、陈述复核状态机、EV-/IR- 编号、单位换算、
    /// 保管链旧行字节不变。全部为虚构数据。依据：DEFECTS/W3.md 架构师裁定 D01–D06 与澄清；contracts/CONTRACTS.md §custody。
    /// </summary>
    public class RetestAcceptanceTests
    {
        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        private static CrossCheckResult R(string sid, CrossCheckOutcome o)
        {
            return new CrossCheckResult(sid, "IR-03", o, 0.0, "s", "声称（虚构）", "数据（虚构）", "VDR（虚构）", "rule");
        }

        private static CrossCheckRegister Seeded(out InMemoryInvestigationAuditSink audit)
        {
            audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            AssertOk(reg.Submit(R("S-c1", CrossCheckOutcome.Consistent), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.Submit(R("S-c2", CrossCheckOutcome.Consistent), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.Submit(R("S-c3", CrossCheckOutcome.Consistent), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.Submit(R("S-x1", CrossCheckOutcome.Contradictory), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.Submit(R("S-u1", CrossCheckOutcome.Unverifiable), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            return reg;
        }

        private static void AssertAllPending(CrossCheckRegister reg)
        {
            foreach (CrossCheckEntry e in reg.Entries)
            {
                Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
                Assert.False(e.IsEffective, e.Result.StatementId + " 不应生效");
                Assert.False(e.ConfirmedInBatch);
            }

            Assert.Empty(reg.Effective());
        }

        // ---------------- D01 / ConfirmConsistentBatch ----------------

        [Fact]
        public void D01_EveryOutcome_IsPendingAfterSubmit_NothingEffectiveUntilConfirmed()
        {
            CrossCheckRegister reg = Seeded(out _);
            AssertAllPending(reg);
            Assert.Equal(5, reg.Pending().Count);
            Assert.Equal(3, reg.PendingConsistent().Count);
        }

        [Fact]
        public void Batch_AllConsistent_ConfirmsAll_OneAuditEach()
        {
            CrossCheckRegister reg = Seeded(out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            var res = reg.ConfirmConsistentBatch(new[] { "S-c1", "S-c2", "S-c3" }, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "一致项批量确认（虚构）");
            AssertOk(res);
            Assert.Equal(3, res.Value.Count);
            foreach (string id in new[] { "S-c1", "S-c2", "S-c3" })
            {
                CrossCheckEntry e = reg.Get(id);
                Assert.True(e.IsEffective);
                Assert.True(e.ConfirmedInBatch);
                Assert.Equal(W3AccFixture.OpA, e.DecidedBy);
            }

            // W3.2 改写：两阶段提交后多一条 batch_commit（n+3 → n+4），末行是提交行，前面是 batch_confirm，且共用同一 batchId。
            Assert.Equal(n + 4, audit.Entries.Count);
            var added = audit.Entries.Skip(n).ToList();
            Assert.Equal(3, added.Count(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.Equal(CrossCheckRegister.ActionBatchCommit, added[added.Count - 1].Action);
            Assert.Equal("interview.crosscheck.batch_commit", added[added.Count - 1].Action);
            Assert.Equal("S-c1,S-c2,S-c3", added[added.Count - 1].AfterValueSummary);
            string batchId = CrossCheckRegister.BatchIdOf(added[0]);
            Assert.False(string.IsNullOrEmpty(batchId));
            Assert.Equal(32, batchId.Length);
            Assert.All(added, a => Assert.Equal(batchId, CrossCheckRegister.BatchIdOf(a)));
            // 矛盾、无法核实仍待逐条确认
            Assert.False(reg.Get("S-x1").IsEffective);
            Assert.False(reg.Get("S-u1").IsEffective);
            Assert.Equal(2, reg.Pending().Count);
        }

        [Theory]
        [InlineData("S-x1", 0)]   // 矛盾项在批首
        [InlineData("S-x1", 1)]   // 在批中
        [InlineData("S-x1", 3)]   // 在批尾
        [InlineData("S-u1", 1)]   // 无法核实项也须逐条确认
        [InlineData("S-u1", 3)]
        public void Batch_WithNonConsistentItem_RejectedWhole_NoPartialWrite(string bad, int position)
        {
            CrossCheckRegister reg = Seeded(out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            var ids = new List<string> { "S-c1", "S-c2", "S-c3" };
            ids.Insert(position, bad);
            var res = reg.ConfirmConsistentBatch(ids, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0));
            Assert.False(res.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrBatchNotConsistent, res.ErrorCode);
            Assert.Equal(n, audit.Entries.Count);
            AssertAllPending(reg);
        }

        [Fact]
        public void Batch_WithUnknownOrAlreadyDecided_RejectedWhole_NoPartialWrite()
        {
            CrossCheckRegister reg = Seeded(out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            var unknown = reg.ConfirmConsistentBatch(new[] { "S-c1", "S-c2", "S-NOPE" }, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0));
            Assert.False(unknown.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrNotFound, unknown.ErrorCode);
            Assert.Equal(n, audit.Entries.Count);
            AssertAllPending(reg);

            AssertOk(reg.Confirm("S-c3", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 1)));
            n = audit.Entries.Count;
            var decided = reg.ConfirmConsistentBatch(new[] { "S-c1", "S-c2", "S-c3" }, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 2));
            Assert.False(decided.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrNotPending, decided.ErrorCode);
            Assert.Equal(n, audit.Entries.Count);
            Assert.False(reg.Get("S-c1").IsEffective);
            Assert.False(reg.Get("S-c2").IsEffective);
            Assert.False(reg.Get("S-c3").ConfirmedInBatch);
        }

        [Fact]
        public void Batch_EmptyOrNoInvestigator_Rejected()
        {
            CrossCheckRegister reg = Seeded(out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            Assert.False(reg.ConfirmConsistentBatch(Array.Empty<string>(), W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)).IsSuccess);
            Assert.False(reg.ConfirmConsistentBatch(null, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)).IsSuccess);
            Assert.False(reg.ConfirmConsistentBatch(new[] { "S-c1" }, " ", W3AccFixture.Cst(5, 19, 12, 0)).IsSuccess);
            Assert.Equal(n, audit.Entries.Count);
            AssertAllPending(reg);
        }

        [Fact]
        public void Batch_DuplicateIds_ConfirmedOnce_AuditedOnce()
        {
            CrossCheckRegister reg = Seeded(out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            AssertOk(reg.ConfirmConsistentBatch(new[] { "S-c1", "S-c1", "S-c2" }, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)));
            // W3.2 改写：去重后 2 条 batch_confirm + 1 条 batch_commit（n+2 → n+3）。
            Assert.Equal(n + 3, audit.Entries.Count);
            var added = audit.Entries.Skip(n).ToList();
            Assert.Equal(2, added.Count(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.Equal(CrossCheckRegister.ActionBatchCommit, added[added.Count - 1].Action);
            Assert.Equal("S-c1,S-c2", added[added.Count - 1].AfterValueSummary);
        }

        // W3-D07 原「中途审计失败」用例已扩展为 W31RetestAcceptanceTests.D07_*（首条/中间/末条/abort 亦失败）。

        // ---------------- D04 Statement 复核状态 ----------------

        private static InterviewRecord RecWithStatement(out Statement st)
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            st = W3AccFixture.AddScalar(rec, "S-rud", "Mary.rudder_angle", "左舵 20 度", 20, "deg", W3AccFixture.Cst(5, 18, 14, 23));
            return rec;
        }

        [Fact]
        public void Statement_NewIsDraft_AgentByDefault_InvestigatorWhenGiven()
        {
            InterviewRecord rec = RecWithStatement(out Statement st);
            Assert.Equal(StatementReviewStatus.Draft, st.ReviewStatus);
            Assert.Equal(StatementOrigin.Agent, st.ExtractedBy);
            Assert.Equal(1, st.Revision);
            SourceSpan span = W3AccFixture.Find(rec, "鸣了一长声");
            Statement byInv = rec.AddStatement("S-horn", StatementKind.Operation, "Mary.horn", "鸣一长声", StatementClaim.Occurrence(true), span, null, StatementOrigin.Investigator).Value;
            Assert.Equal(StatementReviewStatus.Draft, byInv.ReviewStatus);
            Assert.Equal(StatementOrigin.Investigator, byInv.ExtractedBy);
        }

        [Fact]
        public void Statement_LegalFlow_Draft_Modified_Modified_Confirmed()
        {
            InterviewRecord rec = RecWithStatement(out Statement st);
            var audit = new InMemoryInvestigationAuditSink();
            SourceSpan span = st.Span;
            Statement m1 = rec.ModifyStatement("S-rud", "左舵 15 度（修正）", StatementClaim.ScalarValue(15, "deg"), span, st.ReferenceUtc, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit).Value;
            Assert.Equal(StatementReviewStatus.Modified, m1.ReviewStatus);
            Assert.Equal(2, m1.Revision);
            Statement m2 = rec.ModifyStatement("S-rud", "左舵 18 度（再修正）", StatementClaim.ScalarValue(18, "deg"), span, st.ReferenceUtc, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 1), audit).Value;
            Assert.Equal(3, m2.Revision);
            Statement c = rec.ReviewStatement("S-rud", StatementReviewStatus.Confirmed, W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 12, 2), audit).Value;
            Assert.Equal(StatementReviewStatus.Confirmed, c.ReviewStatus);
            Assert.Equal(W3AccFixture.OpB, c.ReviewedBy);
            Assert.Equal(3, c.Revision);
            Assert.Same(c, rec.GetStatement("S-rud"));
            Assert.Equal(3, audit.Entries.Count);
            Assert.Equal(InterviewRecord.ActionStatementReview, audit.Entries.Last().Action);
        }

        [Fact]
        public void Statement_Draft_Rejected_RequiresReason()
        {
            InterviewRecord rec = RecWithStatement(out _);
            var audit = new InMemoryInvestigationAuditSink();
            var noReason = rec.ReviewStatement("S-rud", StatementReviewStatus.Rejected, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit, " ");
            Assert.False(noReason.IsSuccess);
            Assert.Empty(audit.Entries);
            Assert.Equal(StatementReviewStatus.Draft, rec.GetStatement("S-rud").ReviewStatus);
            AssertOk(rec.ReviewStatement("S-rud", StatementReviewStatus.Rejected, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit, "与录音不符（虚构）"));
            Assert.Equal(StatementReviewStatus.Rejected, rec.GetStatement("S-rud").ReviewStatus);
            Assert.Single(audit.Entries);
        }

        [Theory]
        [InlineData(StatementReviewStatus.Confirmed)]
        [InlineData(StatementReviewStatus.Rejected)]
        public void Statement_FinalStates_CannotBeModifiedOrReReviewed(StatementReviewStatus final)
        {
            InterviewRecord rec = RecWithStatement(out Statement st);
            var audit = new InMemoryInvestigationAuditSink();
            AssertOk(rec.ReviewStatement("S-rud", final, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit, "理由（虚构）"));
            Statement frozen = rec.GetStatement("S-rud");
            int n = audit.Entries.Count;

            var mod = rec.ModifyStatement("S-rud", "改", StatementClaim.ScalarValue(1, "deg"), st.Span, null, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 13, 0), audit);
            Assert.False(mod.IsSuccess);
            Assert.Equal(InterviewRecord.ErrNotEditable, mod.ErrorCode);
            foreach (StatementReviewStatus again in new[] { StatementReviewStatus.Confirmed, StatementReviewStatus.Rejected })
            {
                var rv = rec.ReviewStatement("S-rud", again, W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 13, 1), audit, "再次（虚构）");
                Assert.False(rv.IsSuccess, final + " → " + again + " 应被拒");
                Assert.Equal(InterviewRecord.ErrNotEditable, rv.ErrorCode);
            }

            Assert.Same(frozen, rec.GetStatement("S-rud"));
            Assert.Equal(final, rec.GetStatement("S-rud").ReviewStatus);
            Assert.Equal(n, audit.Entries.Count);
        }

        [Theory]
        [InlineData(StatementReviewStatus.Draft)]
        [InlineData(StatementReviewStatus.Modified)]
        public void Statement_ReviewDecision_MustBeConfirmedOrRejected(StatementReviewStatus decision)
        {
            InterviewRecord rec = RecWithStatement(out _);
            var audit = new InMemoryInvestigationAuditSink();
            var r = rec.ReviewStatement("S-rud", decision, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit, "x");
            Assert.False(r.IsSuccess);
            Assert.Empty(audit.Entries);
            Assert.Equal(StatementReviewStatus.Draft, rec.GetStatement("S-rud").ReviewStatus);
        }

        [Fact]
        public void Statement_Modify_InvalidSpanOrUnknownId_Rejected_NoChange()
        {
            InterviewRecord rec = RecWithStatement(out Statement st);
            var audit = new InMemoryInvestigationAuditSink();
            var badSpan = rec.ModifyStatement("S-rud", "x", StatementClaim.ScalarValue(1, "deg"), new SourceSpan(3, QaField.Answer, 9999, 5), null, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit);
            Assert.False(badSpan.IsSuccess);
            var unknown = rec.ModifyStatement("S-none", "x", StatementClaim.ScalarValue(1, "deg"), st.Span, null, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit);
            Assert.Equal(InterviewRecord.ErrStatementNotFound, unknown.ErrorCode);
            var unknownReview = rec.ReviewStatement("S-none", StatementReviewStatus.Confirmed, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), audit);
            Assert.Equal(InterviewRecord.ErrStatementNotFound, unknownReview.ErrorCode);
            Assert.Same(st, rec.GetStatement("S-rud"));
            Assert.Empty(audit.Entries);
        }

        // ---------------- D05 编号正则 ----------------

        [Theory]
        [InlineData("EV-001", true)]
        [InlineData("EV-123", true)]
        [InlineData("EV-0001", true)]
        [InlineData("EV-999999", true)]
        [InlineData("EV-01", false)]
        [InlineData("EV-1", false)]
        [InlineData("EV-", false)]
        [InlineData("ev-001", false)]
        [InlineData("EV001", false)]
        [InlineData("EV-00a", false)]
        [InlineData(" EV-001", false)]
        [InlineData("EV-001 ", false)]
        [InlineData("", false)]
        [InlineData(null, false)]
        [InlineData("EV-\u0660\u0661\u0662", false)]   // 阿拉伯-印度数字
        [InlineData("EV-\uff10\uff10\uff11", false)]   // 全角数字
        public void EvidenceId_Pattern(string id, bool ok)
        {
            Assert.Equal(ok, EvidenceItem.IsValidId(id));
            var ledger = new CustodyLedger();
            var res = ledger.Register(new EvidenceItem(id, "t（虚构）", "s（虚构）", W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40), W3AccFixture.ShaMaryVdr), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40));
            Assert.Equal(ok, res.IsSuccess);
            Assert.Equal(ok ? 1 : 0, ledger.JsonLines.Count);
        }

        [Fact]
        public void EvidenceId_TrailingNewline_IsRejected()
        {
            // .NET 正则 `$` 会匹配字符串末尾的 \n 之前；"EV-001\n" 不是合法 evidenceRef。
            Assert.False(EvidenceItem.IsValidId("EV-001\n"), "EvidenceItem.IsValidId(\"EV-001\\n\") 返回 true");
            var ledger = new CustodyLedger();
            var res = ledger.Register(new EvidenceItem("EV-001\n", "t（虚构）", "s（虚构）", W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40), W3AccFixture.ShaMaryVdr), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40));
            Assert.False(res.IsSuccess, "Register 接受了带换行的证据编号 \"EV-001\\n\"");
        }

        [Theory]
        [InlineData("IR-03", true)]
        [InlineData("IR-10", true)]
        [InlineData("IR-123", true)]
        [InlineData("IR-3", false)]
        [InlineData("ir-03", false)]
        [InlineData("IR03", false)]
        [InlineData("IR-03 ", false)]
        [InlineData(" IR-03", false)]
        [InlineData("IR-0a", false)]
        [InlineData("", false)]
        [InlineData(null, false)]
        [InlineData("IR-\uff10\uff13", false)]
        public void InterviewRecordId_Pattern(string id, bool ok)
        {
            var person = new Interviewee("P-X", "（虚构）", "船长", "Mary 轮（虚构）");
            bool accepted;
            try
            {
                new InterviewRecord(id, person, W3AccFixture.Cst(5, 19, 9, 30));
                accepted = true;
            }
            catch (ArgumentException)
            {
                accepted = false;
            }

            Assert.Equal(ok, accepted);
        }

        [Fact]
        public void InterviewRecordId_TrailingNewline_IsRejected()
        {
            var person = new Interviewee("P-X", "（虚构）", "船长", "Mary 轮（虚构）");
            bool accepted;
            try
            {
                new InterviewRecord("IR-03\n", person, W3AccFixture.Cst(5, 19, 9, 30));
                accepted = true;
            }
            catch (ArgumentException)
            {
                accepted = false;
            }

            Assert.False(accepted, "InterviewRecord 接受了带换行的编号 \"IR-03\\n\"");
        }

        [Theory]
        [InlineData("SR-2026-01\n")]
        [InlineData("SR-2026-\u0660\u0661")]
        [InlineData("SR-\u0662\u0660\u0662\u0666-01")]
        public void RecommendationId_NewlineOrNonAsciiDigits_IsRejected(string id)
        {
            Assert.False(SafetyRecommendationBoard.IsValidId(id), "IsValidId 接受了 " + id.Replace("\n", "\\n"));
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        public void RecommendationId_Empty_IsRejected(string id)
        {
            var b = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            Assert.False(b.CreateDraft(id, "t（虚构）", "a（虚构）", new[] { "N" }, W3AccFixture.Cst(8, 1, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(6, 1, 0, 0)).IsSuccess);
            Assert.Empty(b.All);
        }

        // ---------------- UnitConversion ----------------

        [Theory]
        [InlineData(1.0, "kn", "m/s", 1852.0 / 3600.0)]
        [InlineData(10.0, "m/s", "kn", 10.0 * 3600.0 / 1852.0)]
        [InlineData(3.0, "nm", "m", 5556.0)]
        [InlineData(1852.0, "m", "nm", 1.0)]
        [InlineData(180.0, "deg", "rad", Math.PI)]
        [InlineData(90.0, "°", "rad", Math.PI / 2)]
        [InlineData(Math.PI, "rad", "°", 180.0)]
        [InlineData(180.0, "s", "min", 3.0)]
        [InlineData(2.5, "min", "s", 150.0)]
        [InlineData(5.0, "KN", "kt", 5.0)]
        public void UnitConversion_KnownPairs(double v, string from, string to, double expected)
        {
            Assert.True(UnitConversion.TryConvert(v, from, to, out double r), from + "→" + to);
            Assert.Equal(expected, r, 9);
            Assert.True(UnitConversion.AreCompatible(from, to));
        }

        [Theory]
        [InlineData("furlong", "m")]
        [InlineData("kn", "foo")]
        [InlineData("", "kn")]
        [InlineData(null, "m")]
        [InlineData("kn", "m")]     // 量纲不同
        [InlineData("deg", "s")]
        public void UnitConversion_UnknownOrIncompatible_Fails(string from, string to)
        {
            Assert.False(UnitConversion.TryConvert(1.0, from, to, out _));
        }

        private static CrossCheckResult CheckScalar(double claimed, string claimedUnit, double observed, string observedUnit, double tol)
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Statement st = W3AccFixture.AddScalar(rec, "S-q", "q.subject", "3 海里", claimed, claimedUnit, W3AccFixture.Cst(5, 18, 14, 17));
            var src = new W3AccFixture.MapSource();
            src.BySubject["q.subject"] = DataObservation.ScalarValue(observed, observedUnit, "AIS（虚构）", W3AccFixture.Cst(5, 18, 14, 17));
            return new StatementCrossChecker(new CrossCheckTolerance().SetScalar("q.subject", tol)).Check(st, src);
        }

        [Theory]
        [InlineData(10.0, "kn", 5.144444, "m/s", 0.01, CrossCheckOutcome.Consistent)]
        [InlineData(10.0, "kn", 6.0, "m/s", 0.5, CrossCheckOutcome.Contradictory)]
        [InlineData(5.144444, "m/s", 10.0, "kn", 0.001, CrossCheckOutcome.Consistent)]
        [InlineData(3.0, "nm", 5556.0, "m", 0.01, CrossCheckOutcome.Consistent)]
        [InlineData(3.0, "nm", 5800.0, "m", 0.1, CrossCheckOutcome.Contradictory)]
        [InlineData(5556.0, "m", 3.0, "nm", 1.0, CrossCheckOutcome.Consistent)]
        [InlineData(20.0, "°", 0.3490659, "rad", 0.01, CrossCheckOutcome.Consistent)]
        [InlineData(20.0, "deg", 0.5, "rad", 1.0, CrossCheckOutcome.Contradictory)]
        [InlineData(3.0, "min", 180.0, "s", 0.0, CrossCheckOutcome.Consistent)]
        [InlineData(3.0, "min", 200.0, "s", 0.1, CrossCheckOutcome.Contradictory)]
        [InlineData(10.0, "kn", 10.0, "furlong/fortnight", 100.0, CrossCheckOutcome.Unverifiable)]
        [InlineData(10.0, "zz", 10.0, "kn", 100.0, CrossCheckOutcome.Unverifiable)]
        public void CrossCheck_ConvertsKnownUnits_OnlyUnknownIsUnverifiable(double claimed, string cu, double observed, string ou, double tol, CrossCheckOutcome expected)
        {
            CrossCheckResult r = CheckScalar(claimed, cu, observed, ou, tol);
            Assert.Equal(expected, r.Outcome);
            if (expected != CrossCheckOutcome.Unverifiable)
            {
                Assert.Equal(cu, r.DeltaUnit);
                Assert.Contains("换算", r.Rule, StringComparison.Ordinal);
            }
        }

        [Theory]
        [InlineData("m·s⁻¹")]
        public void UnitConversion_MetresPerSecond_ScientificNotation_IsKnown(string unit)
        {
            // 裁定原文写作「kn/m·s⁻¹」；m·s⁻¹ 是 m/s 的标准记法（SI），应视为已知单位。
            Assert.True(UnitConversion.TryConvert(1.0, "kn", unit, out double r), "单位记法 " + unit + " 未被识别为 m/s");
            Assert.Equal(1852.0 / 3600.0, r, 9);
        }

        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        [InlineData(double.NegativeInfinity)]
        public void EmptyNumber_ClaimedNaNOrInfinity_NotAllowed(double bad)
        {
            // 裁定：空数字不允许。陈述取值为 NaN/∞ 时，要么登记即拒绝，要么比对判无法核实；绝不可判一致/矛盾进入分析。
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            SourceSpan span = W3AccFixture.Find(rec, "3 海里");
            var added = rec.AddStatement("S-nan", StatementKind.Observation, "q.subject", "3 海里", StatementClaim.ScalarValue(bad, "nm"), span);
            if (!added.IsSuccess)
            {
                return;
            }

            var src = new W3AccFixture.MapSource();
            src.BySubject["q.subject"] = DataObservation.ScalarValue(3.0, "nm", "AIS（虚构）");
            CrossCheckResult r = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("q.subject", 0.1)).Check(added.Value, src);
            Assert.True(r.Outcome == CrossCheckOutcome.Unverifiable,
                "陈述值 " + bad + " 被登记且比对结论为 " + r.Outcome + "（应拒绝登记或判无法核实）");
        }

        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        public void EmptyNumber_ObservedNaNOrInfinity_IsUnverifiable(double bad)
        {
            CrossCheckResult r = CheckScalar(3.0, "nm", bad, "nm", 0.1);
            Assert.True(r.Outcome == CrossCheckOutcome.Unverifiable, "数据值 " + bad + " 比对结论为 " + r.Outcome + "（应为无法核实）");
        }

        // ---------------- 保管链旧行字节不变 ----------------

        private const string Sha1 = W3AccFixture.ShaMaryVdr;

        [Fact]
        public void Custody_LegacyDefaultRegisterLine_MatchesContractByteForByte()
        {
            // contracts/CONTRACTS.md：7 标准键 → seq, evidence_id, sha256, detail → Register 的 title, source, extracted_by, extracted_utc, path
            // → 非默认时才有 case_id / confidentiality → prev。默认字段的登记行必须保持旧格式（无新键）。
            var ledger = new CustodyLedger();
            DateTimeOffset t = new DateTimeOffset(2026, 5, 18, 10, 40, 0, TimeSpan.Zero);
            AssertOk(ledger.Register(new EvidenceItem("EV-001", "T（虚构）", "S（虚构）", "X", t, Sha1, "raw/vdr/mary.zip"), "op", t));
            string expected =
                "{\"utc\":\"2026-05-18T10:40:00Z\",\"operator\":\"op\",\"action\":\"custody.register\",\"category\":\"Custody\",\"command\":\"登记证据 EV-001\",\"before\":\"\",\"after\":\"" + Sha1 + "\"," +
                "\"seq\":1,\"evidence_id\":\"EV-001\",\"sha256\":\"" + Sha1 + "\",\"detail\":\"\",\"title\":\"T（虚构）\",\"source\":\"S（虚构）\",\"extracted_by\":\"X\",\"extracted_utc\":\"2026-05-18T10:40:00Z\",\"path\":\"raw/vdr/mary.zip\"," +
                "\"prev\":\"0000000000000000000000000000000000000000000000000000000000000000\"}";
            Assert.Equal(expected, ledger.JsonLines[0]);
        }

        [Fact]
        public void Custody_ExistingLines_ByteIdentical_AfterNewOperations()
        {
            var sink = new W3AccFixture.LineSink();
            var ledger = new CustodyLedger(sink);
            AssertOk(ledger.Register(W3AccFixture.MaryVdr(), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40)));
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 18, 19, 0), "只读回放"));
            AssertOk(ledger.Verify("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 19, 5), W3AccFixture.ShaMaryVdr));
            string[] legacy = ledger.JsonLines.ToArray();

            // 新功能操作：带案件号+受限的登记、需复核标注/解除、变更、失配校验
            AssertOk(ledger.Register(new EvidenceItem("EV-006", "Lily 轮船员体检记录（虚构）", "Lily 轮公司（虚构）", W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 10, 0), W3AccFixture.ShaOther, "raw/hr/lily.pdf", W3AccFixture.CaseId, EvidenceConfidentiality.Restricted), W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 10, 0)));
            AssertOk(ledger.MarkNeedsReview("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 11, 0), "需复核纸本（虚构）"));
            AssertOk(ledger.RecordChange("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), W3AccFixture.ShaDerived, "脱敏副本（虚构）"));
            AssertOk(ledger.Verify("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 13, 0), W3AccFixture.ShaOther));
            AssertOk(ledger.ResolveNeedsReview("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 14, 0), "已核对纸本（虚构）"));

            for (int i = 0; i < legacy.Length; i++)
            {
                Assert.Equal(legacy[i], ledger.JsonLines[i]);
                Assert.Equal(legacy[i], sink.Lines[i]);
            }

            Assert.Equal(ledger.JsonLines.ToArray(), sink.Lines.ToArray());
            Assert.DoesNotContain("case_id", legacy[0], StringComparison.Ordinal);
            Assert.DoesNotContain("confidentiality", legacy[0], StringComparison.Ordinal);
            Assert.Equal(EvidenceStatus.Mismatch, ledger.StatusOf("EV-001"));

            // 旧行 + 新行整体可重载，状态一致
            var loaded = CustodyLedger.Load(sink.Lines);
            AssertOk(loaded);
            Assert.Equal(ledger.JsonLines.ToArray(), loaded.Value.JsonLines.ToArray());
            Assert.Equal(EvidenceStatus.Mismatch, loaded.Value.StatusOf("EV-001"));
            Assert.Equal(W3AccFixture.CaseId, loaded.Value.Get("EV-006").CaseId);
            Assert.True(loaded.Value.Get("EV-006").IsRestricted);
            Assert.Equal(1, loaded.Value.AccessCount("EV-001"));
        }

        [Fact]
        public void Custody_LoadedLegacyLines_StayByteIdentical_WhenAppendingNewEvents()
        {
            CustodyLedger first = new CustodyLedger();
            AssertOk(first.Register(W3AccFixture.MaryVdr(), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40)));
            AssertOk(first.Register(W3AccFixture.LilyVdr(), W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 10, 5)));
            string[] legacy = first.JsonLines.ToArray();

            var sink = new W3AccFixture.LineSink();
            CustodyLedger reopened = CustodyLedger.Load(legacy, sink).Value;
            Assert.Empty(sink.Lines); // 重载不应回写旧行
            AssertOk(reopened.MarkNeedsReview("EV-002", W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 9, 0), "需复核（虚构）"));
            Assert.Single(sink.Lines);
            Assert.Equal(legacy, reopened.JsonLines.Take(2).ToArray());
            Assert.True(reopened.IsMarkedNeedsReview("EV-002"));

            var all = legacy.Concat(sink.Lines).ToList();
            CustodyLedger again = CustodyLedger.Load(all).Value;
            Assert.Equal(EvidenceStatus.NeedsReview, again.StatusOf("EV-002"));
        }

        [Theory]
        [InlineData("\"confidentiality\":\"Restricted\"", "\"confidentiality\":\"Normal\"")]
        [InlineData(",\"confidentiality\":\"Restricted\"", "")]
        [InlineData("\"case_id\":\"CASE-2026-LN01\"", "\"case_id\":\"CASE-2026-XX99\"")]
        public void Custody_TamperingNewFields_IsDetected(string from, string to)
        {
            var ledger = new CustodyLedger();
            AssertOk(ledger.Register(new EvidenceItem("EV-006", "体检记录（虚构）", "Lily 轮公司（虚构）", W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 10, 0), W3AccFixture.ShaOther, null, W3AccFixture.CaseId, EvidenceConfidentiality.Restricted), W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 10, 0)));
            AssertOk(ledger.RecordAccess("EV-006", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 11, 0), "查阅（虚构）"));
            var lines = ledger.JsonLines.ToList();
            Assert.Contains(from, lines[0], StringComparison.Ordinal);
            lines[0] = lines[0].Replace(from, to);
            Assert.False(CustodyLedger.Load(lines).IsSuccess);
        }

        [Fact]
        public void Custody_TamperingReviewFlag_IsDetected()
        {
            var ledger = new CustodyLedger();
            AssertOk(ledger.Register(W3AccFixture.MaryVdr(), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40)));
            AssertOk(ledger.MarkNeedsReview("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 11, 0), "需复核（虚构）"));
            var lines = ledger.JsonLines.ToList();
            Assert.Contains("needs_review", lines[1], StringComparison.Ordinal);
            lines[1] = lines[1].Replace("\"result\":\"needs_review\"", "\"result\":\"cleared\"");
            Assert.False(CustodyLedger.Load(lines).IsSuccess);
        }

        // ---------------- 征求意见：到期限时刻即可关闭（澄清2）+ Waived ----------------

        [Fact]
        public void Consultation_CloseAtExactDeadline_AndWaivedCountsAsSettled()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var c = new Consultation("RPT-2026-LN01", audit, W3AccFixture.CaseId);
            DateTimeOffset opened = W3AccFixture.Cst(6, 1, 10, 0);
            var parties = new[] { new ConsultationParty("P-LILY", "Lily 轮公司（虚构）"), new ConsultationParty("P-MARY", "Mary 轮公司（虚构）") };
            ConsultationRound r = c.OpenRound("v1", parties, opened, W3AccFixture.OpA).Value;
            Assert.Equal(opened.AddDays(30), r.DeadlineUtc);
            AssertOk(c.RecordReply(1, "P-LILY", opened.AddDays(3), "意见（虚构）", new[] { "c1（虚构）" }, W3AccFixture.OpA));
            Assert.False(c.WaiveReply(1, "P-LILY", W3AccFixture.OpA, opened.AddDays(4), "x").IsSuccess); // 已回复不可再放弃
            Assert.False(c.WaiveReply(1, "P-MARY", W3AccFixture.OpA, opened.AddDays(4), " ").IsSuccess); // 须理由
            AssertOk(c.WaiveReply(1, "P-MARY", W3AccFixture.OpA, opened.AddDays(4), "书面声明放弃（虚构）"));
            Assert.Equal(ReplyStatus.Waived, r.StatusOf("P-MARY", opened.AddDays(40)));
            Assert.False(c.RecordReply(1, "P-MARY", opened.AddDays(5), "迟到（虚构）", new string[0], W3AccFixture.OpA).IsSuccess);
            Assert.True(r.AllReplied);
            AssertOk(c.CloseRound(1, W3AccFixture.OpA, opened.AddDays(5)));

            var c2 = new Consultation("RPT-2026-LN02", new InMemoryInvestigationAuditSink());
            ConsultationRound r2 = c2.OpenRound("v1", parties, opened, W3AccFixture.OpA).Value;
            Assert.False(c2.CloseRound(1, W3AccFixture.OpA, r2.DeadlineUtc.AddTicks(-1)).IsSuccess);
            AssertOk(c2.CloseRound(1, W3AccFixture.OpA, r2.DeadlineUtc));
        }
    }
}
