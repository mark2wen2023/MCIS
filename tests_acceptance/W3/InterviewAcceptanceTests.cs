using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>
    /// 验收重点②：容差边界（刚好等于/略超）、单位与时区、矛盾须人工确认且驳回须理由、审计写入。
    /// 对照原型 10 与 contracts/interview.schema.json。
    /// </summary>
    public class InterviewAcceptanceTests
    {
        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        private static CrossCheckResult CheckScalar(double claimed, string claimedUnit, double observed, string observedUnit, double tol)
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Statement st = W3AccFixture.AddScalar(rec, "S-dist", "Lily.range", "3 海里", claimed, claimedUnit, W3AccFixture.Cst(5, 18, 14, 17));
            var src = new W3AccFixture.MapSource();
            src.BySubject["Lily.range"] = DataObservation.ScalarValue(observed, observedUnit, "AIS 14:17（虚构）", W3AccFixture.Cst(5, 18, 14, 17));
            var checker = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("Lily.range", tol));
            return checker.Check(st, src);
        }

        [Fact]
        public void Scalar_ExactlyAtTolerance_IsConsistent()
        {
            // 陈述 3.0 nm，数据 2.5 nm，容差 0.5 → 刚好等于
            CrossCheckResult r = CheckScalar(3.0, "nm", 2.5, "nm", 0.5);
            Assert.Equal(CrossCheckOutcome.Consistent, r.Outcome);
            Assert.Equal(0.5, r.Delta);
        }

        [Fact]
        public void Scalar_SlightlyOverTolerance_IsContradictory()
        {
            // 差 0.50001 > 容差 0.5
            CrossCheckResult r = CheckScalar(3.00001, "nm", 2.5, "nm", 0.5);
            Assert.Equal(CrossCheckOutcome.Contradictory, r.Outcome);
            Assert.True(r.Delta.HasValue && r.Delta.Value > 0.5);
        }

        [Fact]
        public void EventTime_ExactlyAtTolerance_IsConsistent()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            DateTimeOffset claimed = W3AccFixture.Cst(5, 18, 14, 23, 0);
            Statement st = W3AccFixture.AddEvent(rec, "S-helm", "Mary.rudder_start", "14:23 才开始左舵", claimed);
            var src = new W3AccFixture.MapSource();
            src.BySubject["Mary.rudder_start"] = DataObservation.EventAt(claimed.AddSeconds(-30), "VDR 舵角（虚构）");
            var checker = new StatementCrossChecker(new CrossCheckTolerance { TimeSeconds = 30 });
            CrossCheckResult r = checker.Check(st, src);
            Assert.Equal(CrossCheckOutcome.Consistent, r.Outcome);
            Assert.Equal(30.0, r.Delta);
            Assert.Equal("s", r.DeltaUnit);
        }

        [Fact]
        public void EventTime_SlightlyOverTolerance_IsContradictory()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            DateTimeOffset claimed = W3AccFixture.Cst(5, 18, 14, 23, 0);
            Statement st = W3AccFixture.AddEvent(rec, "S-helm", "Mary.rudder_start", "14:23 才开始左舵", claimed);
            var src = new W3AccFixture.MapSource();
            src.BySubject["Mary.rudder_start"] = DataObservation.EventAt(claimed.AddSeconds(-30.001), "VDR 舵角（虚构）");
            var checker = new StatementCrossChecker(new CrossCheckTolerance { TimeSeconds = 30 });
            CrossCheckResult r = checker.Check(st, src);
            Assert.Equal(CrossCheckOutcome.Contradictory, r.Outcome);
        }

        [Fact]
        public void EventTime_EquivalentAcrossTimeZones_IsConsistent()
        {
            // 原型时间线 14:22:15（UTC+8）≡ 06:22:15Z
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            DateTimeOffset claimedCst = W3AccFixture.Cst(5, 18, 14, 22, 15);
            DateTimeOffset observedUtc = W3AccFixture.Utc(5, 18, 6, 22, 15);
            Statement st = W3AccFixture.AddEvent(rec, "S-tz", "Mary.rudder_start", "14:23 才开始左舵", claimedCst);
            var src = new W3AccFixture.MapSource();
            src.BySubject["Mary.rudder_start"] = DataObservation.EventAt(observedUtc, "VDR 舵角 UTC（虚构）");
            var checker = new StatementCrossChecker(new CrossCheckTolerance { TimeSeconds = 0 });
            CrossCheckResult r = checker.Check(st, src);
            Assert.Equal(CrossCheckOutcome.Consistent, r.Outcome);
            Assert.Equal(0.0, r.Delta);
        }

        [Fact]
        public void Position_ExactlyAtTolerance_IsConsistent_SlightlyOverIsNot()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            var origin = new GeoCoord(113.70, 21.80);
            // 沿纬度方向偏移一个可测量的距离，再用该距离作为容差（刚好等于）。
            var nearby = new GeoCoord(113.70, 21.801666);
            double d = StatementCrossChecker.HaversineMeters(origin, nearby);
            Assert.True(d > 0);

            SourceSpan span = rec.Locate(1, QaField.Answer, "3 号浮标北面").Value;
            Statement st = rec.AddStatement("S-pos", StatementKind.Position, "Mary.position", "3 号浮标北面", StatementClaim.At(origin), span, W3AccFixture.Cst(5, 18, 14, 17)).Value;
            var src = new W3AccFixture.MapSource();
            src.BySubject["Mary.position"] = DataObservation.At(nearby, "AIS（虚构）", W3AccFixture.Cst(5, 18, 14, 17));

            var exact = new StatementCrossChecker(new CrossCheckTolerance { PositionMeters = d });
            Assert.Equal(CrossCheckOutcome.Consistent, exact.Check(st, src).Outcome);

            var under = new StatementCrossChecker(new CrossCheckTolerance { PositionMeters = d - 0.01 });
            Assert.Equal(CrossCheckOutcome.Contradictory, under.Check(st, src).Outcome);
        }

        [Fact]
        public void Occurrence_Mismatch_IsContradictory()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Statement st = W3AccFixture.AddOccurrence(rec, "S-horn", "Mary.whistle", "鸣了一长声", true);
            var src = new W3AccFixture.MapSource();
            src.BySubject["Mary.whistle"] = DataObservation.Occurrence(false, "VDR 音频（虚构）");
            CrossCheckResult r = new StatementCrossChecker().Check(st, src);
            Assert.Equal(CrossCheckOutcome.Contradictory, r.Outcome);
        }

        [Fact]
        public void Statement_WithoutSourceSpan_IsRejected()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            var bad = rec.AddStatement("S-x", StatementKind.Time, "Mary.x", "无出处", StatementClaim.EventTime(W3AccFixture.Cst(5, 18, 14, 23)), new SourceSpan(99, QaField.Answer, 0, 3));
            Assert.False(bad.IsSuccess);
            Assert.Equal(InterviewRecord.ErrSpanOutOfRange, bad.ErrorCode);
        }

        [Fact]
        public void Contradiction_RequiresHumanConfirm_WritesAudit_AndDismissNeedsReason()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Statement st = W3AccFixture.AddScalar(rec, "S-dist", "Lily.range", "3 海里", 3.0, "nm", W3AccFixture.Cst(5, 18, 14, 17));
            var src = new W3AccFixture.MapSource();
            src.BySubject["Lily.range"] = DataObservation.ScalarValue(5.1, "nm", "AIS 14:17（虚构）", W3AccFixture.Cst(5, 18, 14, 17));
            CrossCheckResult result = new StatementCrossChecker().Check(st, src);
            Assert.Equal(CrossCheckOutcome.Contradictory, result.Outcome);

            var audit = new InMemoryInvestigationAuditSink();
            var register = new CrossCheckRegister(audit);
            CrossCheckEntry entry = register.Submit(result, "比对流程（虚构）", W3AccFixture.Cst(5, 19, 11, 0)).Value;
            Assert.Equal(CrossCheckState.PendingConfirmation, entry.State);
            Assert.False(entry.IsEffective);
            Assert.Equal("interview.crosscheck.submit", audit.Entries.Last().Action);
            Assert.Equal(InvestigationAuditCategories.Interview, audit.Entries.Last().Category);

            Mcis.Core.Result<CrossCheckEntry> noReason = register.Dismiss("S-dist", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 11, 5), "  ");
            Assert.False(noReason.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, noReason.ErrorCode);
            Assert.Equal(CrossCheckState.PendingConfirmation, register.Get("S-dist").State);
            Assert.Single(audit.Entries);

            AssertOk(register.Confirm("S-dist", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 11, 10), "已核对 AIS"));
            Assert.True(register.Get("S-dist").IsEffective);
            Assert.Equal(CrossCheckState.Confirmed, register.Get("S-dist").State);
            Assert.Equal(CrossCheckRegister.ActionConfirm, audit.Entries.Last().Action);
            Assert.Contains("S-dist", audit.Entries.Last().CommandName, StringComparison.Ordinal);

            // 另一条用于驳回
            Statement horn = W3AccFixture.AddOccurrence(rec, "S-horn", "Mary.whistle", "鸣了一长声", true);
            src.BySubject["Mary.whistle"] = DataObservation.Occurrence(false, "VDR 音频（虚构）");
            CrossCheckEntry hornEntry = register.Submit(new StatementCrossChecker().Check(horn, src), "比对流程（虚构）", W3AccFixture.Cst(5, 19, 11, 20)).Value;
            Assert.False(hornEntry.IsEffective);
            AssertOk(register.Dismiss("S-horn", W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 11, 21), "声号通道当时故障，改以车钟记录为准（虚构）"));
            Assert.Equal(CrossCheckState.Dismissed, register.Get("S-horn").State);
            Assert.False(register.Get("S-horn").IsEffective);
            Assert.Equal(CrossCheckRegister.ActionDismiss, audit.Entries.Last().Action);
            Assert.Contains("声号通道当时故障", audit.Entries.Last().AfterValueSummary, StringComparison.Ordinal);
        }

        [Fact]
        public void W3_D01_ConsistentAndUnverifiable_MustRemainPendingUntilConfirmed()
        {
            // 依据：ARCHITECTURE §15.3 / §15.5（智能体输出为草稿，经人工确认后才生效）；
            // 原型 screenshots/1440/10-interview-1440.png（“草稿状态，待调查员确认”“结论须经逐条确认后才进入分析”）；
            // contracts/schemas/interview.schema.json reviewStatus: Draft→Confirmed。
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Statement ok = W3AccFixture.AddScalar(rec, "S-vis", "env.visibility", "1.5 海里", 1.5, "nm", W3AccFixture.Cst(5, 18, 14, 19));
            var src = new W3AccFixture.MapSource();
            src.BySubject["env.visibility"] = DataObservation.ScalarValue(1.5, "nm", "VTS（虚构）");
            CrossCheckResult consistent = new StatementCrossChecker().Check(ok, src);
            Assert.Equal(CrossCheckOutcome.Consistent, consistent.Outcome);

            var audit = new InMemoryInvestigationAuditSink();
            var register = new CrossCheckRegister(audit);
            CrossCheckEntry entry = register.Submit(consistent, "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)).Value;

            Assert.False(entry.IsEffective,
                "一致/无法核实的抽取结果也应为草稿，须调查员确认后才进入分析；实现在 Submit 时即 Effective。");
            Assert.Equal(CrossCheckState.PendingConfirmation, entry.State);
            Mcis.Core.Result<CrossCheckEntry> confirm = register.Confirm("S-vis", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 11, 5), null);
            Assert.True(confirm.IsSuccess, "一致项也应能被调查员确认并写入审计。");
            Assert.True(register.Get("S-vis").IsEffective);
            Assert.Contains(audit.Entries, e => e.Action == CrossCheckRegister.ActionConfirm);
        }

        [Fact]
        public void W3_D04_Statement_HasReviewStatusAndModifyPath()
        {
            // 原型 10 有「修改」；schema statement.reviewStatus 含 Draft/Confirmed/Rejected/Modified，extractedBy 区分 Agent/Investigator。
            Type st = typeof(Statement);
            Assert.NotNull(st.GetProperty("ReviewStatus"));
            Assert.NotNull(st.GetProperty("ExtractedBy"));
            Type rec = typeof(InterviewRecord);
            bool hasModify = rec.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                .Any(m => m.Name.IndexOf("Modif", StringComparison.OrdinalIgnoreCase) >= 0
                          || m.Name.IndexOf("Revise", StringComparison.OrdinalIgnoreCase) >= 0
                          || m.Name.IndexOf("UpdateStatement", StringComparison.OrdinalIgnoreCase) >= 0);
            Assert.True(hasModify, "领域模型应支持对陈述草稿的修改路径（原型「修改」按钮 / reviewStatus=Modified）。");
        }

        [Fact]
        public void W3_D04_InterviewRecord_SupportsSignedAndCaseId()
        {
            // 原型 10：IR-03 卡片标注「已签字」；contracts/interview.schema.json 必填 caseId，可选 signed。
            Type t = typeof(InterviewRecord);
            Assert.NotNull(t.GetProperty("Signed"));
            Assert.NotNull(t.GetProperty("CaseId"));
        }

        [Fact]
        public void W3_D05_InterviewRecordId_MustMatchIRPattern()
        {
            // contracts/interview.schema.json: recordId pattern ^IR-[0-9]{2,}$
            var person = new Interviewee("P-X", "（虚构）", "船长", "Mary 轮（虚构）");
            bool threw = false;
            try
            {
                var rec = new InterviewRecord("NOT-A-VALID-ID", person, W3AccFixture.Cst(5, 19, 9, 30));
                Assert.Fail("构造非法笔录编号 " + rec.RecordId + " 应被拒绝，实际已接受。");
            }
            catch (ArgumentException)
            {
                threw = true;
            }

            Assert.True(threw, "recordId 须符合 IR-xx（至少两位数字）。");
        }

        [Fact]
        public void DurationMinutes_SupportsScreenshotDuration()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Assert.NotNull(rec.DurationMinutes);
            Assert.Equal(68, rec.DurationMinutes.Value, 3);
        }
    }
}
