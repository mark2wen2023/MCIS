using System;
using System.Linq;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    public class ComparisonViewTests
    {
        [Fact]
        public void Rows_BeforeCheck_AreUnchecked()
        {
            var r = Small(out var reg, out _);
            var rows = InterviewComparisonView.Rows(r, reg);
            Assert.Equal(new[] { "S1", "S2", "S3" }, rows.Select(x => x.StatementId));
            Assert.All(rows, x => Assert.Null(x.Outcome));
            Assert.All(rows, x => Assert.Null(x.State));
            Assert.Equal("IR-09 第 1 问", rows[0].Citation);
            Assert.Equal("14:23 开始左舵", rows[0].Summary);
            Assert.Equal(string.Empty, rows[0].DataDisplay);
            var s = InterviewComparisonView.Summarize(r, reg);
            Assert.Equal(3, s.StatementCount);
            Assert.Equal(3, s.UncheckedCount);
            Assert.Equal(0, s.ContradictionCount);
            Assert.Equal("3 条陈述 · 0 条矛盾", s.HeaderText);
        }

        [Fact]
        public void Rows_AfterCheck_ShowDataAndVerdict_SummaryCountsDraftsAndConfirmed()
        {
            var r = Small(out var reg, out _);
            SubmitAll(r, reg);
            var rows = InterviewComparisonView.Rows(r, reg);
            Assert.Equal(new CrossCheckOutcome?[] { CrossCheckOutcome.Contradictory, CrossCheckOutcome.Consistent, CrossCheckOutcome.Contradictory }, rows.Select(x => x.Outcome));
            Assert.All(rows, x => Assert.Equal(CrossCheckState.PendingConfirmation, x.State));
            Assert.Equal(45.0, rows[0].Delta);
            Assert.Equal("s", rows[0].DeltaUnit);
            Assert.EndsWith("(VDR 舵角)", rows[0].DataDisplay);
            Assert.True(rows[0].IsContradiction);
            Assert.False(rows[1].IsContradiction);
            var s = InterviewComparisonView.Summarize(r, reg);
            Assert.Equal(2, s.ContradictionCount);
            Assert.Equal(0, s.ConfirmedContradictionCount);
            Assert.Equal(3, s.PendingCount);
            Assert.Equal(0, s.UncheckedCount);
            Assert.Equal("3 条陈述 · 2 条矛盾", s.HeaderText);
            Ok(reg.Confirm("S1", "调查员甲", Day19(11, 0)));
            Ok(reg.Dismiss("S3", "调查员甲", Day19(11, 0), "数据源有误（虚构）"));
            s = InterviewComparisonView.Summarize(r, reg);
            Assert.Equal(1, s.ContradictionCount);
            Assert.Equal(1, s.ConfirmedContradictionCount);
            Assert.Equal(1, s.PendingCount);
            Assert.False(InterviewComparisonView.Rows(r, reg)[2].IsContradiction);
        }

        [Fact]
        public void RejectedStatements_Excluded_NullRegister_Tolerated()
        {
            var r = Small(out var reg, out var audit);
            Ok(r.ReviewStatement("S3", StatementReviewStatus.Rejected, "调查员甲", Day19(11, 0), audit, "非陈述（虚构）"));
            Assert.Equal(new[] { "S1", "S2" }, InterviewComparisonView.Rows(r, null).Select(x => x.StatementId));
            Assert.Equal(2, InterviewComparisonView.Summarize(r, null).StatementCount);
            Assert.Empty(InterviewComparisonView.Rows(null, reg));
        }

        [Fact]
        public void Roster_StatusLabelSubtitle()
        {
            var r = Small(out var reg, out _);
            var e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(RosterStatus.NotChecked, e.Status);
            Assert.Equal("未比对", e.Label);
            SubmitAll(r, reg);
            e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(RosterStatus.Pending, e.Status);
            Assert.Equal("3 条待确认", e.Label);
            Ok(reg.Confirm("S1", "调查员甲", Day19(11, 0)));
            e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(RosterStatus.Contradictions, e.Status);
            Assert.Equal(1, e.ConfirmedContradictions);
            Assert.Equal("1 处矛盾 · 2 条待确认", e.Label);
            Ok(reg.Confirm("S2", "调查员甲", Day19(11, 0)));
            Ok(reg.Confirm("S3", "调查员甲", Day19(11, 0)));
            e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal("2 处矛盾", e.Label);
            Assert.Equal("IR-09 · 05-19 09:00 · 6 min", e.Subtitle(Cst));
            Assert.Equal("虚构证人", e.Name);
            Assert.Equal("水手", e.Role);
            Assert.Equal("Mary 轮", e.Affiliation);
            Assert.Equal(3, e.StatementCount);
            r.MarkSigned();
            Assert.EndsWith(" · 已签字", InterviewComparisonView.Roster(r, reg).Subtitle(Cst));
        }

        [Fact]
        public void Roster_Consistent_WhenAllConfirmedNoContradiction()
        {
            var r = Empty();
            Ok(r.AddTurn("问？", "14:19 拉半速。", null));
            Ok(r.AddStatement("S1", StatementKind.Time, "Mary.telegraph_half", "14:19 半速", StatementClaim.EventTime(At(14, 19)), Ok(r.Locate(1, QaField.Answer, "14:19"))));
            var reg = new CrossCheckRegister(new Mcis.Domain.Evidence.InMemoryInvestigationAuditSink());
            Ok(reg.Submit(new StatementCrossChecker().Check(r.GetStatement("S1"), new DictSource().Add("Mary.telegraph_half", DataObservation.EventAt(At(14, 19, 8), "VDR"))), "系统", Day19(10, 0)));
            Ok(reg.Confirm("S1", "调查员甲", Day19(11, 0)));
            var e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(RosterStatus.Consistent, e.Status);
            Assert.Equal("一致", e.Label);
            Assert.Equal("IR-09 · 05-19 09:00", e.Subtitle(Cst)); // 无时长
            var list = InterviewComparisonView.Roster(new[] { r, Small(out _, out _) }, reg);
            Assert.Equal(2, list.Count);
        }

        [Fact]
        public void TimeChart_StatementVsData_PointsAndAxis()
        {
            var r = Small(out var reg, out _);
            SubmitAll(r, reg);
            var ch = InterviewComparisonView.Chart(r, reg);
            Assert.Equal(new[] { "S2", "S3", "S1" }, ch.Points.Select(p => p.StatementId)); // 按陈述时刻排序（14:22:15, 14:22:15, 14:23）
            var s1 = ch.Points.Single(p => p.StatementId == "S1");
            Assert.Equal(At(14, 23), s1.StatementUtc);
            Assert.Equal(At(14, 22, 15), s1.ObservedUtc);
            Assert.Equal(45.0, s1.DeltaSeconds);
            Assert.Equal(CrossCheckOutcome.Contradictory, s1.Outcome);
            var s3 = ch.Points.Single(p => p.StatementId == "S3");
            Assert.Null(s3.ObservedUtc);
            Assert.Contains("VDR 音频", s3.Note);
            Assert.Equal(At(14, 22), ch.AxisStartUtc);
            Assert.Equal(At(14, 23), ch.AxisEndUtc);
            Assert.Throws<NotSupportedException>(() => ((System.Collections.IList)ch.Points).Clear());
        }

        [Fact]
        public void TimeChart_Unchecked_AndEmpty()
        {
            var r = Small(out var reg, out _);
            var ch = InterviewComparisonView.Chart(r, reg);
            Assert.All(ch.Points, p => Assert.Null(p.Outcome));
            Assert.All(ch.Points, p => Assert.Equal("未比对", p.Note));
            var empty = InterviewComparisonView.Chart(Empty(), reg);
            Assert.Empty(empty.Points);
            Assert.Null(empty.AxisStartUtc);
            Assert.Null(empty.AxisEndUtc);
        }

        [Fact]
        public void TimeChart_AxisRoundsOutward_ToWholeMinutes()
        {
            var r = Empty();
            Ok(r.AddTurn("问？", "14:19:08 半速。", null));
            Ok(r.AddStatement("S1", StatementKind.Time, "x", "半速", StatementClaim.EventTime(At(14, 19, 8)), Ok(r.Locate(1, QaField.Answer, "14:19:08"))));
            var ch = InterviewComparisonView.Chart(r, null);
            Assert.Equal(At(14, 19), ch.AxisStartUtc);
            Assert.Equal(At(14, 20), ch.AxisEndUtc);
        }
    }
}
