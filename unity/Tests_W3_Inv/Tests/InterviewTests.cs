using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Audit;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.W3.Tests
{
    public class InterviewRecordTests
    {
        [Fact]
        public void Turns_AreNumberedSequentially_WithOriginalText()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Assert.Equal(new[] { 1, 2, 3 }, ir.Turns.Select(t => t.Round));
            Assert.StartsWith("大概 14:17", ir.GetTurn(1).Answer);
            Assert.Equal("Mary 轮", ir.Interviewee.Affiliation);
            Assert.Equal(15, ir.DurationMinutes);
            Assert.Null(ir.GetTurn(0));
            Assert.Null(ir.GetTurn(4));
        }

        [Fact]
        public void AddTurn_RejectsEmptyAndTimeRegression()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.AddTurn("", "", null).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.AddTurn("q", "a", W3Demo.Day(5, 19, 9, 41)).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.AddTurn("q", "a", W3Demo.Day(5, 19, 9, 0)).ErrorCode);
            Assert.True(ir.AddTurn("补问", "无", null).IsSuccess);
            Assert.True(ir.AddTurn("q", "a", W3Demo.Day(5, 19, 9, 50)).IsSuccess);
            Assert.Equal(5, ir.Turns.Count);
        }

        [Fact]
        public void Constructor_ValidatesRequiredFields()
        {
            var who = new Interviewee("P", "n", "r", "a");
            Assert.Throws<ArgumentException>(() => new InterviewRecord(" ", who, W3Demo.Day(5, 19)));
            Assert.Throws<ArgumentNullException>(() => new InterviewRecord("IR-01", null, W3Demo.Day(5, 19)));
            Assert.Null(new InterviewRecord("IR-01", who, W3Demo.Day(5, 19)).DurationMinutes);
        }

        [Fact]
        public void Locate_AndResolveSpan_PointToOriginalFragment()
        {
            InterviewRecord ir = W3Demo.Ir03();
            SourceSpan span = ir.Locate(2, QaField.Answer, "在 14:23 才开始左舵").Value;
            Assert.Equal(2, span.Round);
            Assert.Equal("在 14:23 才开始左舵", ir.ResolveSpan(span).Value);
            SourceSpan q = ir.Locate(1, QaField.Question, "雷达").Value;
            Assert.Equal("雷达", ir.ResolveSpan(q).Value);
            Assert.False(ir.Locate(2, QaField.Answer, "右舵").IsSuccess);
            Assert.False(ir.Locate(9, QaField.Answer, "x").IsSuccess);
            Assert.False(ir.Locate(1, QaField.Answer, "").IsSuccess);
        }

        [Theory]
        [InlineData(9, 0, 1)]
        [InlineData(1, -1, 2)]
        [InlineData(1, 0, 0)]
        [InlineData(1, 0, 10000)]
        [InlineData(1, 30, 1000)]
        public void ResolveSpan_RejectsOutOfRange(int round, int start, int length)
        {
            Assert.Equal(InterviewRecord.ErrSpanOutOfRange, W3Demo.Ir03().ResolveSpan(new SourceSpan(round, QaField.Answer, start, length)).ErrorCode);
        }

        [Fact]
        public void AddStatement_RequiresValidSourceAndUniqueId()
        {
            InterviewRecord ir = W3Demo.Ir03();
            SourceSpan span = ir.Locate(2, QaField.Answer, "左舵 20 度").Value;
            Result<Statement> ok = ir.AddStatement("S-03-3", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), span, W3Demo.At(14, 23));
            Assert.True(ok.IsSuccess);
            Assert.Equal("左舵 20 度", ok.Value.Quote);
            Assert.Equal("IR-03", ok.Value.RecordId);
            Assert.Equal(InterviewRecord.ErrDuplicateStatement, ir.AddStatement("S-03-3", StatementKind.Operation, "x", "", StatementClaim.Occurrence(true), span).ErrorCode);
            Assert.Equal(InterviewRecord.ErrSpanOutOfRange, ir.AddStatement("S-03-9", StatementKind.Operation, "x", "", StatementClaim.Occurrence(true), new SourceSpan(7, QaField.Answer, 0, 1)).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.AddStatement("S-03-8", StatementKind.Operation, "", "", StatementClaim.Occurrence(true), span).ErrorCode);
            Assert.Equal(InterviewRecord.ErrInvalidArgument, ir.AddStatement("S-03-7", StatementKind.Operation, "x", "", null, span).ErrorCode);
            Assert.Single(ir.Statements);
        }
    }

    public class StatementCrossCheckerTests
    {
        private static Statement Add(InterviewRecord ir, string id, StatementKind kind, string subject, StatementClaim claim, int round, string fragment, DateTimeOffset? at = null)
        {
            Result<Statement> r = ir.AddStatement(id, kind, subject, fragment, claim, ir.Locate(round, QaField.Answer, fragment).Value, at);
            Assert.True(r.IsSuccess, r.ToString());
            return r.Value;
        }

        [Fact]
        public void EventTime_OutsideTolerance_IsContradiction_WithSignedDelta()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S-03-2", StatementKind.Time, "Mary.port_helm_start", StatementClaim.EventTime(W3Demo.At(14, 23)), 2, "在 14:23 才开始左舵");
            CrossCheckResult r = new StatementCrossChecker().Check(s, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Contradictory, r.Outcome);
            Assert.Equal(45.0, r.Delta.Value, 6);
            Assert.Equal("s", r.DeltaUnit);
            Assert.Equal("VDR 舵角（虚构）", r.SourceLabel);
            Assert.Contains("30", r.Rule);
        }

        [Fact]
        public void EventTime_WithinTolerance_IsConsistent_AndNegativeDeltaKept()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S-03-5", StatementKind.Time, "VTS.call_mary", StatementClaim.EventTime(W3Demo.At(14, 20)), 3, "VTS 在 14:20 叫过我们");
            CrossCheckResult r = new StatementCrossChecker().Check(s, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Consistent, r.Outcome);
            Assert.Equal(-12.0, r.Delta.Value, 6);
        }

        [Fact]
        public void EventTime_ExactlyAtTolerance_IsConsistent()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Time, "VTS.call_mary", StatementClaim.EventTime(W3Demo.At(14, 20, 42)), 3, "VTS 在 14:20 叫过我们");
            Assert.Equal(CrossCheckOutcome.Consistent, new StatementCrossChecker().Check(s, FakeDataSource.LilyMary()).Outcome);
            var strict = new StatementCrossChecker(new CrossCheckTolerance { TimeSeconds = 29.9 });
            Assert.Equal(CrossCheckOutcome.Contradictory, strict.Check(s, FakeDataSource.LilyMary()).Outcome);
        }

        [Fact]
        public void Scalar_UsesPerSubjectTolerance()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement range = Add(ir, "S-03-1", StatementKind.Observation, "Mary.radar_first_sighting_range", StatementClaim.ScalarValue(3, "nm"), 1, "距离差不多 3 海里", W3Demo.At(14, 17));
            Statement rudder = Add(ir, "S-03-3", StatementKind.Operation, "Mary.rudder_angle", StatementClaim.ScalarValue(20, "deg"), 2, "左舵 20 度", W3Demo.At(14, 23));
            var checker = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("Mary.radar_first_sighting_range", 0.5));
            CrossCheckResult r1 = checker.Check(range, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Contradictory, r1.Outcome);
            Assert.Equal(-2.1, r1.Delta.Value, 6);
            Assert.Equal("nm", r1.DeltaUnit);
            Assert.Equal(CrossCheckOutcome.Consistent, checker.Check(rudder, FakeDataSource.LilyMary()).Outcome);
            var loose = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("Mary.radar_first_sighting_range", 2.1));
            Assert.Equal(CrossCheckOutcome.Consistent, loose.Check(range, FakeDataSource.LilyMary()).Outcome);
            Assert.Throws<ArgumentOutOfRangeException>(() => new CrossCheckTolerance().SetScalar("x", -1));
        }

        [Fact]
        public void Scalar_UnknownUnit_IsUnverifiable()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Observation, "Mary.radar_first_sighting_range", StatementClaim.ScalarValue(30, "链"), 1, "距离差不多 3 海里");
            CrossCheckResult r = new StatementCrossChecker().Check(s, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Unverifiable, r.Outcome);
            Assert.Null(r.Delta);
            Assert.Contains("未知单位", r.Rule);
        }

        [Fact]
        public void Scalar_DifferentDimension_IsUnverifiable()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Observation, "Mary.radar_first_sighting_range", StatementClaim.ScalarValue(3, "kn"), 1, "距离差不多 3 海里");
            CrossCheckResult r = new StatementCrossChecker().Check(s, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Unverifiable, r.Outcome);
            Assert.Contains("量纲不同", r.Rule);
        }

        [Theory]
        [InlineData(5.1, "nm", 9445.2, "m", 0.0, true)]            // nm ↔ m（1 nm = 1852 m）
        [InlineData(9445.2, "m", 5.1, "nm", 0.0, true)]
        [InlineData(10.0, "kn", 5.144444444444445, "m/s", 0.0, true)] // kn ↔ m/s
        [InlineData(5.0, "m/s", 10.0, "kn", 0.1, false)]           // 5 m/s ≈ 9.719 kn，差 0.28 m/s > 0.1
        [InlineData(20.0, "deg", 0.3490658503988659, "rad", 0.0, true)] // ° ↔ rad
        [InlineData(20.0, "°", 0.40, "rad", 1.0, false)]            // 0.40 rad ≈ 22.9°，差 2.9° > 1°
        [InlineData(2.0, "min", 120.0, "s", 0.0, true)]            // s ↔ min
        [InlineData(90.0, "s", 1.0, "min", 30.0, true)]
        [InlineData(90.0, "s", 1.0, "min", 29.0, false)]
        [InlineData(10.0, "kt", 10.0, "KN", 0.0, true)]            // 别名、大小写
        [InlineData(3.0, "海里", 3.0, "nmi", 0.0, true)]
        public void Scalar_KnownUnits_AreConverted(double claimed, string cu, double observed, string ou, double tol, bool consistent)
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Observation, "X.value", StatementClaim.ScalarValue(claimed, cu), 1, "距离差不多 3 海里");
            var src = new FakeDataSource().Set("X.value", DataObservation.ScalarValue(observed, ou, "虚构"));
            CrossCheckResult r = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("X.value", tol)).Check(s, src);
            Assert.Equal(consistent ? CrossCheckOutcome.Consistent : CrossCheckOutcome.Contradictory, r.Outcome);
            Assert.Equal(cu, r.DeltaUnit);
        }

        [Fact]
        public void Scalar_Conversion_DeltaIsInStatementUnit_AndRuleExplainsConversion()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Observation, "X.value", StatementClaim.ScalarValue(3, "nm"), 1, "距离差不多 3 海里");
            var src = new FakeDataSource().Set("X.value", DataObservation.ScalarValue(9445.2, "m", "AIS（虚构）"));
            CrossCheckResult r = new StatementCrossChecker(new CrossCheckTolerance().SetScalar("X.value", 0.5)).Check(s, src);
            Assert.Equal(CrossCheckOutcome.Contradictory, r.Outcome);
            Assert.Equal(-2.1, r.Delta.Value, 9);
            Assert.Equal("nm", r.DeltaUnit);
            Assert.Contains("换算为 5.1 nm", r.Rule);
            Assert.Contains("9445.2 m", r.ObservedText);
        }

        [Fact]
        public void UnitConversion_Api()
        {
            Assert.Equal("kn", UnitConversion.Canonical(" Knots "));
            Assert.Null(UnitConversion.Canonical("furlong"));
            Assert.True(UnitConversion.AreCompatible("nm", "m"));
            Assert.False(UnitConversion.AreCompatible("nm", "s"));
            Assert.False(UnitConversion.TryConvert(1, "nm", null, out _));
            Assert.True(UnitConversion.TryConvert(1, "h", "min", out double m));
            Assert.Equal(60, m, 9);
        }

        [Fact]
        public void Occurrence_Mismatch_IsContradiction()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S-03-4", StatementKind.Operation, "Mary.long_blast", StatementClaim.Occurrence(true), 2, "鸣了一长声", W3Demo.At(14, 23));
            CrossCheckResult r = new StatementCrossChecker().Check(s, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Contradictory, r.Outcome);
            Assert.Null(r.Delta);
            Assert.Equal("发生", r.ClaimedText);
            Assert.Equal("未发生", r.ObservedText);
        }

        [Fact]
        public void Position_ComparesGreatCircleDistance()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement near = Add(ir, "P1", StatementKind.Position, "Mary.position_1417", StatementClaim.At(new GeoCoord(113.7000, 21.8010)), 1, "在 3 号浮标北面");
            Statement far = Add(ir, "P2", StatementKind.Position, "Mary.position_1417", StatementClaim.At(new GeoCoord(113.7000, 21.8100)), 1, "3 号浮标");
            var checker = new StatementCrossChecker();
            CrossCheckResult rn = checker.Check(near, FakeDataSource.LilyMary());
            CrossCheckResult rf = checker.Check(far, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Consistent, rn.Outcome);
            Assert.InRange(rn.Delta.Value, 110, 112);
            Assert.Equal(CrossCheckOutcome.Contradictory, rf.Outcome);
            Assert.InRange(rf.Delta.Value, 1105, 1120);
            Assert.Equal("m", rf.DeltaUnit);
        }

        [Fact]
        public void MissingData_IsUnverifiable()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Observation, "Lily.unknown_subject", StatementClaim.Occurrence(true), 1, "出港");
            CrossCheckResult r = new StatementCrossChecker().Check(s, FakeDataSource.LilyMary());
            Assert.Equal(CrossCheckOutcome.Unverifiable, r.Outcome);
            Assert.Null(r.Delta);
            Assert.Equal("无数据", r.ObservedText);
        }

        [Fact]
        public void TypeMismatch_AndNullObservation_AreUnverifiable()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Operation, "Mary.port_helm_start", StatementClaim.ScalarValue(20, "deg"), 2, "左舵 20 度");
            Assert.Equal(CrossCheckOutcome.Unverifiable, new StatementCrossChecker().Check(s, FakeDataSource.LilyMary()).Outcome);
            Assert.Equal(CrossCheckOutcome.Unverifiable, new StatementCrossChecker().Check(s, new NullSource()).Outcome);
        }

        [Fact]
        public void Query_CarriesSubjectTypeAndReferenceTime()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Add(ir, "S-03-3", StatementKind.Operation, "Mary.rudder_angle", StatementClaim.ScalarValue(20, "deg"), 2, "左舵 20 度", W3Demo.At(14, 23));
            var src = FakeDataSource.LilyMary();
            new StatementCrossChecker().CheckAll(ir, src);
            Assert.Single(src.Queries);
            Assert.Equal("Mary.rudder_angle", src.Queries[0].Subject);
            Assert.Equal(ClaimValueType.Scalar, src.Queries[0].ValueType);
            Assert.Equal(W3Demo.At(14, 23), src.Queries[0].ReferenceUtc);
        }

        [Fact]
        public void Checker_IsDeterministic()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Add(ir, "S-03-2", StatementKind.Time, "Mary.port_helm_start", StatementClaim.EventTime(W3Demo.At(14, 23)), 2, "在 14:23 才开始左舵");
            Add(ir, "S-03-4", StatementKind.Operation, "Mary.long_blast", StatementClaim.Occurrence(true), 2, "鸣了一长声");
            var a = new StatementCrossChecker().CheckAll(ir, FakeDataSource.LilyMary());
            var b = new StatementCrossChecker().CheckAll(ir, FakeDataSource.LilyMary());
            Assert.Equal(a.Select(x => (x.Outcome, x.Delta, x.Rule, x.ObservedText)), b.Select(x => (x.Outcome, x.Delta, x.Rule, x.ObservedText)));
        }

        [Fact]
        public void Check_RejectsNullArguments()
        {
            var c = new StatementCrossChecker();
            Assert.Throws<ArgumentNullException>(() => c.Check(null, FakeDataSource.LilyMary()));
            Assert.Throws<ArgumentNullException>(() => c.CheckAll(null, FakeDataSource.LilyMary()));
            InterviewRecord ir = W3Demo.Ir03();
            Statement s = Add(ir, "S", StatementKind.Operation, "Mary.long_blast", StatementClaim.Occurrence(true), 2, "鸣了一长声");
            Assert.Throws<ArgumentNullException>(() => c.Check(s, null));
        }

        private sealed class NullSource : IStatementDataSource
        {
            public DataObservation Query(StatementQuery query) { return null; }
        }
    }

    public class CrossCheckRegisterTests
    {
        private static (CrossCheckRegister reg, InMemoryInvestigationAuditSink audit, CrossCheckResult contra, CrossCheckResult consistent, CrossCheckResult unverifiable) Setup()
        {
            InterviewRecord ir = W3Demo.Ir03();
            Statement s2 = ir.AddStatement("S-03-2", StatementKind.Time, "Mary.port_helm_start", "14:23 左舵", StatementClaim.EventTime(W3Demo.At(14, 23)), ir.Locate(2, QaField.Answer, "在 14:23 才开始左舵").Value).Value;
            Statement s3 = ir.AddStatement("S-03-3", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), ir.Locate(2, QaField.Answer, "左舵 20 度").Value).Value;
            Statement s9 = ir.AddStatement("S-03-9", StatementKind.Observation, "Lily.unknown", "出港", StatementClaim.Occurrence(true), ir.Locate(1, QaField.Answer, "出港").Value).Value;
            var checker = new StatementCrossChecker();
            var src = FakeDataSource.LilyMary();
            var audit = new InMemoryInvestigationAuditSink();
            return (new CrossCheckRegister(audit), audit, checker.Check(s2, src), checker.Check(s3, src), checker.Check(s9, src));
        }

        [Fact]
        public void Contradiction_IsPendingUntilConfirmed_ThenEffective_WithAudit()
        {
            var (reg, audit, contra, _, _) = Setup();
            CrossCheckEntry e = reg.Submit(contra, "比对流程", W3Demo.Day(5, 20)).Value;
            Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
            Assert.False(e.IsEffective);
            Assert.Empty(reg.EffectiveContradictions());
            Assert.Single(reg.Pending());

            CrossCheckEntry c = reg.Confirm("S-03-2", "调查员 A（虚构）", W3Demo.Day(5, 20, 10, 5), "与 VDR 舵角一致认定").Value;
            Assert.Equal(CrossCheckState.Confirmed, c.State);
            Assert.True(c.IsEffective);
            Assert.Equal("调查员 A（虚构）", c.DecidedBy);
            Assert.Equal(W3Demo.Day(5, 20, 10, 5), c.DecidedUtc);
            Assert.Single(reg.EffectiveContradictions());
            Assert.Empty(reg.Pending());

            Assert.Equal(2, audit.Entries.Count);
            InvestigationAuditEntry a = audit.Entries[1];
            Assert.Equal(CrossCheckRegister.ActionConfirm, a.Action);
            Assert.Equal("Interview", a.Category);
            Assert.Equal("调查员 A（虚构）", a.OperatorName);
            Assert.Contains("S-03-2", a.CommandName);
            Assert.Contains("PendingConfirmation", a.BeforeValueSummary);
            Assert.Contains("Δ=45 s", a.BeforeValueSummary);
            Assert.StartsWith("Confirmed", a.AfterValueSummary);
            AuditRecord parsed = AuditRecord.FromJsonLine(a.ToJsonLine());
            Assert.Equal(a.AfterValueSummary, parsed.AfterValueSummary);
        }

        [Fact]
        public void D01_AllOutcomes_StartPending_AndBecomeEffectiveOnlyAfterConfirm()
        {
            var (reg, audit, contra, consistent, unverifiable) = Setup();
            foreach (var r in new[] { contra, consistent, unverifiable })
            {
                CrossCheckEntry e = reg.Submit(r, "flow", W3Demo.Day(5, 20)).Value;
                Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
                Assert.False(e.IsEffective);
            }

            Assert.Empty(reg.Effective());
            Assert.Equal(3, reg.Pending().Count);
            Assert.True(reg.Confirm("S-03-9", "inv", W3Demo.Day(5, 20, 10, 0)).IsSuccess);
            Assert.True(reg.Get("S-03-9").IsEffective);
            Assert.Equal(CrossCheckRegister.ActionConfirm, audit.Entries.Last().Action);
            Assert.Single(reg.Effective());
            Assert.Empty(reg.EffectiveContradictions());
        }

        [Fact]
        public void D01_BatchConfirm_OnlyConsistent_AllOrNothing_AuditPerItem()
        {
            InterviewRecord ir = W3Demo.Ir03();
            var src = FakeDataSource.LilyMary();
            var checker = new StatementCrossChecker();
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            Statement a = ir.AddStatement("S-A", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), ir.Locate(2, QaField.Answer, "左舵 20 度").Value).Value;
            Statement b = ir.AddStatement("S-B", StatementKind.Time, "VTS.call_mary", "VTS 14:20", StatementClaim.EventTime(W3Demo.At(14, 20)), ir.Locate(3, QaField.Answer, "VTS 在 14:20 叫过我们").Value).Value;
            Statement c = ir.AddStatement("S-C", StatementKind.Time, "Mary.port_helm_start", "14:23 左舵", StatementClaim.EventTime(W3Demo.At(14, 23)), ir.Locate(2, QaField.Answer, "在 14:23 才开始左舵").Value).Value;
            Statement u = ir.AddStatement("S-U", StatementKind.Observation, "Lily.unknown", "出港", StatementClaim.Occurrence(true), ir.Locate(1, QaField.Answer, "出港").Value).Value;
            foreach (Statement st in new[] { a, b, c, u })
            {
                reg.Submit(checker.Check(st, src), "flow", W3Demo.Day(5, 20));
            }

            Assert.Equal(new[] { "S-A", "S-B" }, reg.PendingConsistent().Select(e => e.Result.StatementId));
            int before = audit.Entries.Count;

            // 混入矛盾项 → 整批拒绝，不改状态、不写审计
            Assert.Equal(CrossCheckRegister.ErrBatchNotConsistent, reg.ConfirmConsistentBatch(new[] { "S-A", "S-C" }, "inv", W3Demo.Day(5, 21)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrBatchNotConsistent, reg.ConfirmConsistentBatch(new[] { "S-U" }, "inv", W3Demo.Day(5, 21)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrNotFound, reg.ConfirmConsistentBatch(new[] { "S-A", "S-404" }, "inv", W3Demo.Day(5, 21)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.ConfirmConsistentBatch(new string[0], "inv", W3Demo.Day(5, 21)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.ConfirmConsistentBatch(new[] { "S-A" }, " ", W3Demo.Day(5, 21)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.ConfirmConsistentBatch(null, "inv", W3Demo.Day(5, 21)).ErrorCode);
            Assert.False(reg.Get("S-A").IsEffective);
            Assert.Equal(before, audit.Entries.Count);

            IReadOnlyList<CrossCheckEntry> done = reg.ConfirmConsistentBatch(new[] { "S-A", "S-B", "S-A" }, "调查员 A（虚构）", W3Demo.Day(5, 21), "批量核对").Value;
            Assert.Equal(2, done.Count);
            Assert.All(done, e => { Assert.True(e.IsEffective); Assert.True(e.ConfirmedInBatch); Assert.Equal("调查员 A（虚构）", e.DecidedBy); });
            Assert.Equal(before + 3, audit.Entries.Count); // W3.2：2 条 batch_confirm + 1 条 batch_commit
            Assert.Equal(new[] { CrossCheckRegister.ActionBatchConfirm, CrossCheckRegister.ActionBatchConfirm, CrossCheckRegister.ActionBatchCommit }, audit.Entries.Skip(before).Select(e => e.Action));
            Assert.Equal(CrossCheckRegister.ErrNotPending, reg.ConfirmConsistentBatch(new[] { "S-A" }, "inv", W3Demo.Day(5, 21)).ErrorCode);

            // 矛盾与无法核实须逐条确认
            Assert.True(reg.Confirm("S-C", "inv", W3Demo.Day(5, 21)).IsSuccess);
            Assert.True(reg.Dismiss("S-U", "inv", W3Demo.Day(5, 21), "数据源缺失").IsSuccess);
            Assert.Single(reg.EffectiveContradictions());
            Assert.Equal(3, reg.Effective().Count);
        }

        [Fact]
        public void Confirm_RejectsEmptyInvestigator_Unknown_AndRepeat_WithoutAudit()
        {
            var (reg, audit, contra, _, _) = Setup();
            reg.Submit(contra, "flow", W3Demo.Day(5, 20));
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Confirm("S-03-2", " ", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrNotFound, reg.Confirm("S-XX", "inv", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S-03-2").State);
            Assert.Single(audit.Entries);
            Assert.True(reg.Confirm("S-03-2", "inv", W3Demo.Day(5, 20)).IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrNotPending, reg.Confirm("S-03-2", "inv", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrNotPending, reg.Dismiss("S-03-2", "inv", W3Demo.Day(5, 20), "r").ErrorCode);
            Assert.Equal(2, audit.Entries.Count);
        }

        [Fact]
        public void Dismiss_RequiresReason_AndIsNotEffective()
        {
            var (reg, audit, contra, _, _) = Setup();
            reg.Submit(contra, "flow", W3Demo.Day(5, 20));
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Dismiss("S-03-2", "inv", W3Demo.Day(5, 20), "").ErrorCode);
            CrossCheckEntry e = reg.Dismiss("S-03-2", "inv", W3Demo.Day(5, 20), "VDR 舵角通道钟差未校正").Value;
            Assert.Equal(CrossCheckState.Dismissed, e.State);
            Assert.False(e.IsEffective);
            Assert.Empty(reg.EffectiveContradictions());
            Assert.Equal(CrossCheckRegister.ActionDismiss, audit.Entries.Last().Action);
            Assert.Contains("钟差", audit.Entries.Last().AfterValueSummary);
        }

        [Fact]
        public void Submit_RejectsDuplicatesAndInvalid()
        {
            var (reg, audit, contra, _, _) = Setup();
            Assert.True(reg.Submit(contra, "flow", W3Demo.Day(5, 20)).IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrDuplicate, reg.Submit(contra, "flow", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Submit(null, "flow", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Submit(contra, "", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Single(audit.Entries);
            Assert.Throws<ArgumentNullException>(() => new CrossCheckRegister(null));
        }

        [Fact]
        public void AuditFailure_LeavesStateUnchanged()
        {
            var (_, _, contra, _, _) = Setup();
            var sink = new FlakySink();
            var reg = new CrossCheckRegister(sink);
            reg.Submit(contra, "flow", W3Demo.Day(5, 20));
            sink.Fail = true;
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, reg.Confirm("S-03-2", "inv", W3Demo.Day(5, 20)).ErrorCode); // W3.2：不再抛异常
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S-03-2").State);
        }

        private sealed class FlakySink : IInvestigationAuditSink
        {
            public bool Fail;

            public void Append(InvestigationAuditEntry entry)
            {
                if (Fail)
                {
                    throw new InvalidOperationException("audit unavailable (simulated)");
                }
            }
        }
    }
}
