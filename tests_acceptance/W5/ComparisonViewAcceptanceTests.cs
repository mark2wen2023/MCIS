using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>比对视图：行、表头、名单、时间对照。口径见 REQUESTS.md（名单只计已确认矛盾，表头计未驳回矛盾）。</summary>
    public class ComparisonViewAcceptanceTests
    {
        private static InterviewRecord Scene(out CrossCheckRegister reg, out InMemoryInvestigationAuditSink audit)
        {
            InterviewRecord rec = NewRecord("IR-13", At(5, 19, 9, 30), signed: true);
            Ok(rec.AddTurn("第一次发现？", "大概 14:17，距离差不多 3 海里。", At(5, 19, 9, 32)));
            Ok(rec.AddTurn("什么时候用舵？", "14:23 才开始左舵。", At(5, 19, 9, 40)));
            Ok(rec.AddTurn("鸣笛了吗？", "我鸣放了一长声。", At(5, 19, 9, 42)));
            Ok(rec.AddStatement("S1", StatementKind.Observation, "Mary.range", "首次发现距离 3 nm", StatementClaim.ScalarValue(3, "nm"), Ok(rec.Locate(1, QaField.Answer, "3 海里")), At(5, 18, 14, 17)));
            Ok(rec.AddStatement("S2", StatementKind.Time, "Mary.helm", "14:23 才开始左舵", StatementClaim.EventTime(At(5, 18, 14, 23)), Ok(rec.Locate(2, QaField.Answer, "14:23 才开始左舵"))));
            Ok(rec.AddStatement("S3", StatementKind.Operation, "Mary.horn", "鸣放一长声", StatementClaim.Occurrence(true), Ok(rec.Locate(3, QaField.Answer, "鸣放了一长声")), At(5, 18, 14, 21)));
            audit = new InMemoryInvestigationAuditSink();
            reg = new CrossCheckRegister(audit);
            return rec;
        }

        private static void Submit(CrossCheckRegister reg, InterviewRecord rec)
        {
            Ok(reg.Submit(new CrossCheckResult("S1", rec.RecordId, CrossCheckOutcome.Contradictory, -2.1, "nm", "3 nm", "5.1 nm", "AIS（虚构）", "|Δ|≤0.1 nm"), Agent, At(5, 19, 10, 0)));
            Ok(reg.Submit(new CrossCheckResult("S2", rec.RecordId, CrossCheckOutcome.Contradictory, 45, "s", "14:23", "14:22:15", "VDR（虚构）", "|Δ|≤30 s"), Agent, At(5, 19, 10, 0)));
            Ok(reg.Submit(new CrossCheckResult("S3", rec.RecordId, CrossCheckOutcome.Contradictory, null, "", "有声号", "无声号", "VDR 音频（虚构）", "有无一致"), Agent, At(5, 19, 10, 0)));
        }

        [Fact]
        public void RowsAndHeader_BeforeCheck_AreUnchecked_HeaderCountsStatements()
        {
            InterviewRecord rec = Scene(out CrossCheckRegister reg, out _);
            var rows = InterviewComparisonView.Rows(rec, reg);
            Assert.Equal(3, rows.Count);
            Assert.All(rows, r =>
            {
                Assert.Null(r.Outcome);
                Assert.Null(r.State);
                Assert.False(r.IsContradiction);
                Assert.Equal(string.Empty, r.DataDisplay);
            });
            Assert.Equal("IR-13 第 1 问", rows[0].Citation);
            Assert.Equal("首次发现距离 3 nm", rows[0].Summary);

            var sum = InterviewComparisonView.Summarize(rec, reg);
            Assert.Equal(3, sum.StatementCount);
            Assert.Equal(0, sum.ContradictionCount);
            Assert.Equal(3, sum.UncheckedCount);
            Assert.Equal("3 条陈述 · 0 条矛盾", sum.HeaderText);
        }

        [Fact]
        public void RowsAndHeader_AfterSubmit_HeaderCountsDraftContradictions_RosterCountsOnlyConfirmed()
        {
            InterviewRecord rec = Scene(out CrossCheckRegister reg, out _);
            Submit(reg, rec);

            var sum = InterviewComparisonView.Summarize(rec, reg);
            Assert.Equal("3 条陈述 · 3 条矛盾", sum.HeaderText); // 原型页眉：未驳回（待确认+已确认）
            Assert.Equal(3, sum.ContradictionCount);
            Assert.Equal(0, sum.ConfirmedContradictionCount);
            Assert.Equal(3, sum.PendingCount);

            var roster = InterviewComparisonView.Roster(rec, reg);
            Assert.Equal(RosterStatus.Pending, roster.Status);
            Assert.Equal("3 条待确认", roster.Label);
            Assert.Equal(0, roster.ConfirmedContradictions);
            Assert.Equal("IR-13", roster.RecordId);
            Assert.True(roster.Signed);
            Assert.Contains("IR-13 · 05-19 09:30", roster.Subtitle(Cst));
            Assert.Contains("已签字", roster.Subtitle(Cst));

            var rows = InterviewComparisonView.Rows(rec, reg);
            Assert.All(rows, r => Assert.True(r.IsContradiction));
            Assert.Equal("5.1 nm (AIS（虚构）)", rows[0].DataDisplay);
            Assert.Equal(-2.1, rows[0].Delta);
        }

        [Fact]
        public void Roster_AfterConfirmingContradictions_ShowsConfirmedCount_AndPendingSuffix()
        {
            InterviewRecord rec = Scene(out CrossCheckRegister reg, out _);
            Submit(reg, rec);
            Ok(reg.Confirm("S1", Investigator, At(5, 19, 11, 0)));
            Ok(reg.Confirm("S2", Investigator, At(5, 19, 11, 1)));
            // S3 仍待确认

            var sum = InterviewComparisonView.Summarize(rec, reg);
            Assert.Equal("3 条陈述 · 3 条矛盾", sum.HeaderText);
            Assert.Equal(2, sum.ConfirmedContradictionCount);
            Assert.Equal(1, sum.PendingCount);

            var roster = InterviewComparisonView.Roster(rec, reg);
            Assert.Equal(RosterStatus.Contradictions, roster.Status);
            Assert.Equal("2 处矛盾 · 1 条待确认", roster.Label);
            Assert.Equal(2, roster.ConfirmedContradictions);
        }

        [Fact]
        public void RejectedStatements_AreExcluded_DismissedContradiction_NotInHeader()
        {
            InterviewRecord rec = Scene(out CrossCheckRegister reg, out var audit);
            Submit(reg, rec);
            Ok(rec.ReviewStatement("S3", StatementReviewStatus.Rejected, Investigator, At(5, 19, 11, 0), audit, "不是这句话（虚构）"));
            Ok(reg.Dismiss("S3", Investigator, At(5, 19, 11, 0), "不是这句话（虚构）"));

            var rows = InterviewComparisonView.Rows(rec, reg);
            Assert.Equal(2, rows.Count);
            Assert.DoesNotContain(rows, r => r.StatementId == "S3");
            var sum = InterviewComparisonView.Summarize(rec, reg);
            Assert.Equal("2 条陈述 · 2 条矛盾", sum.HeaderText);
        }

        [Fact]
        public void TimeChart_PlotsStatementVersusObserved_AndAxisRoundsToWholeMinutes()
        {
            InterviewRecord rec = Scene(out CrossCheckRegister reg, out _);
            Submit(reg, rec);
            var chart = InterviewComparisonView.Chart(rec, reg);
            // S1 有 ReferenceUtc，S2 是 EventTime，S3 有 ReferenceUtc
            Assert.Equal(3, chart.Points.Count);
            var helm = chart.Points.Single(p => p.StatementId == "S2");
            Assert.Equal(At(5, 18, 14, 23), helm.StatementUtc);
            Assert.Equal(45.0, helm.DeltaSeconds);
            Assert.Equal(At(5, 18, 14, 22, 15), helm.ObservedUtc); // 陈述 − Δ
            Assert.Equal(CrossCheckOutcome.Contradictory, helm.Outcome);

            Assert.Equal(At(5, 18, 14, 17), chart.AxisStartUtc); // 向下取整到 14:17
            // 最晚是 14:23，向上取整仍为 14:23（整分）
            Assert.Equal(At(5, 18, 14, 23), chart.AxisEndUtc);
        }

        [Fact]
        public void TimeChart_AxisIncludesObservedTime_OutsideStatementRange_AndUncheckedNote()
        {
            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("几点开始转向？", "大约 14:20 开始转向。", rec.StartUtc.AddMinutes(2)));
            Ok(rec.AddStatement("S-t", StatementKind.Time, "Mary.turn", "14:20 开始转向", StatementClaim.EventTime(At(5, 18, 14, 20, 40)), Ok(rec.Locate(1, QaField.Answer, "14:20"))));
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            // 未比对
            var uncheckedChart = InterviewComparisonView.Chart(rec, reg);
            Assert.Equal("未比对", uncheckedChart.Points[0].Note);
            Assert.Null(uncheckedChart.Points[0].ObservedUtc);

            Ok(reg.Submit(new CrossCheckResult("S-t", rec.RecordId, CrossCheckOutcome.Contradictory, 100, "s", "14:20:40", "14:19:00", "VDR（虚构）", "|Δ|≤30 s"), Agent, At(5, 19, 10, 0)));
            var chart = InterviewComparisonView.Chart(rec, reg);
            Assert.Equal(At(5, 18, 14, 19), chart.Points[0].ObservedUtc);
            Assert.Equal(At(5, 18, 14, 19), chart.AxisStartUtc); // 观测时刻更早，向下取整
            Assert.Equal(At(5, 18, 14, 21), chart.AxisEndUtc);   // 14:20:40 向上取整到 14:21
        }

        [Fact]
        public void Roster_Consistent_WhenAllConfirmedNoContradiction_EntryFromOtherRecordIgnored()
        {
            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("航速？", "当时航速 8 节。", rec.StartUtc.AddMinutes(2)));
            Ok(rec.AddStatement("S-s", StatementKind.Operation, "Mary.speed", "航速 8 kn", StatementClaim.ScalarValue(8, "kn"), Ok(rec.Locate(1, QaField.Answer, "8 节"))));
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            Ok(reg.Submit(new CrossCheckResult("S-s", rec.RecordId, CrossCheckOutcome.Consistent, 0, "kn", "8 kn", "8 kn", "VDR（虚构）", "|Δ|≤0.5"), Agent, At(5, 19, 10, 0)));
            Ok(reg.Confirm("S-s", Investigator, At(5, 19, 10, 5)));
            // 同名但属于另一份笔录的条目应被忽略
            InterviewRecord other = NewRecord("IR-14");
            Ok(reg.Submit(new CrossCheckResult("S-x", other.RecordId, CrossCheckOutcome.Contradictory, 1, "kn", "x", "y", "AIS（虚构）", "r"), Agent, At(5, 19, 10, 0)));

            var roster = InterviewComparisonView.Roster(rec, reg);
            Assert.Equal(RosterStatus.Consistent, roster.Status);
            Assert.Equal("一致", roster.Label);
            Assert.Equal(0, roster.ConfirmedContradictions);
        }

        [Fact]
        public void NullRecord_RowsEmpty_RosterThrows_MultiRosterSkipsNull()
        {
            Assert.Empty(InterviewComparisonView.Rows(null, null));
            Assert.Equal("0 条陈述 · 0 条矛盾", InterviewComparisonView.Summarize(null, null).HeaderText);
            Assert.Throws<ArgumentNullException>(() => InterviewComparisonView.Roster((InterviewRecord)null, null));
            var list = InterviewComparisonView.Roster(new InterviewRecord[] { null, NewRecord() }, new CrossCheckRegister(new InMemoryInvestigationAuditSink()));
            Assert.Single(list);
        }
    }
}
