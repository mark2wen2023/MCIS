using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    /// <summary>边界补充测试（变异验证后补）。全部为虚构合成数据。</summary>
    public class W5EdgeTests
    {
        private static InterviewRecord One(string answer)
        {
            var r = Empty();
            Ok(r.AddTurn("问？", answer, Day19(9, 5)));
            return r;
        }

        [Fact]
        public void Parser_EqualTimestamps_AreNotTimeOrderError()
        {
            var p = TranscriptParser.Parse("[05:00] 问：甲？\n答：乙。\n[05:00] 问：丙？\n答：丁。");
            Assert.True(p.IsValid);
            Assert.Empty(p.Issues);
        }

        [Theory]
        [InlineData("[00:60] 问：甲？\n答：乙。")]
        [InlineData("[01:00:60] 问：甲？\n答：乙。")]
        public void Parser_Second60_IsInvalid(string text)
        {
            Assert.Contains(TranscriptParser.Parse(text).Issues, i => i.Code == InterviewCompareErrors.InvalidTimestamp);
        }

        [Fact]
        public void Parser_Boundary_59_59_IsValid()
        {
            var p = TranscriptParser.Parse("[1:59:59] 问：甲？\n答：乙。");
            Assert.True(p.IsValid);
            Assert.Equal(new TimeSpan(1, 59, 59), p.Turns[0].Offset);
        }

        [Fact]
        public void ApplyTo_TurnExactlyAtRecordStart_Accepted()
        {
            var r = Empty();
            var p = TranscriptParser.Parse("[00:00] 问：甲？\n答：乙。", new TranscriptParseOptions { RecordingStartUtc = r.StartUtc });
            Ok(TranscriptParser.ApplyTo(p, r));
            Assert.Equal(r.StartUtc, r.GetTurn(1).Utc);
        }

        [Fact]
        public void Extractor_LookaheadBoundary_IsInclusive_SameDay()
        {
            var r = One("15:27 报告。");
            var c = ClaimCandidateExtractor.Extract(r, new CandidateOptions { AnchorLocal = At(14, 27) }).Single();
            Assert.Equal(At(15, 27).ToUniversalTime(), c.Utc);
        }

        [Fact]
        public void Extractor_Hedges_Yue_And_Zuoyou()
        {
            var c = ClaimCandidateExtractor.Extract(One("距离约 3 海里，左舵 20 度左右，航速 12 节。"), new CandidateOptions { AnchorLocal = At(14, 27) }).ToList();
            Assert.Equal(new[] { true, true, false }, c.Select(x => x.Approximate));
        }

        [Fact]
        public void Extractor_Hour24_NotATime()
        {
            var c = ClaimCandidateExtractor.Extract(One("24:10 和 23:59 两个时刻。"), new CandidateOptions { AnchorLocal = At(14, 27) }).ToList();
            Assert.Equal(new[] { "23:59" }, c.Select(x => x.Text));
        }

        [Fact]
        public void Highlighter_OverlapTakesStrongestMark_RegardlessOfOrder()
        {
            var r = Small(out var reg, out _);
            Ok(r.AddStatement("S4", StatementKind.Operation, "Mary.helm", "开始左舵", StatementClaim.Occurrence(true), Ok(r.Locate(1, QaField.Answer, "开始左舵，左舵")), At(14, 23)));
            Ok(reg.Submit(new CrossCheckResult("S1", "IR-09", CrossCheckOutcome.Contradictory, 45, "s", "a", "b", "x", "r"), "系统", Day19(10, 0)));
            Ok(reg.Submit(new CrossCheckResult("S4", "IR-09", CrossCheckOutcome.Contradictory, null, "", "a", "b", "x", "r"), "系统", Day19(10, 0)));
            Ok(reg.Confirm("S4", "调查员甲", Day19(11, 0)));
            var seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer, reg).Single(s => s.Text == "开始左舵");
            Assert.Equal(new[] { "S1", "S4" }, seg.StatementIds);
            Assert.Equal(ContradictionMark.Confirmed, seg.Contradiction);
        }

        [Fact]
        public void View_EntryFromOtherRecord_TreatedAsUnchecked()
        {
            var r = Small(out var reg, out _);
            Ok(reg.Submit(new CrossCheckResult("S1", "IR-77", CrossCheckOutcome.Contradictory, 60, "s", "a", "b", "x", "r"), "系统", Day19(10, 0)));
            var row = InterviewComparisonView.Rows(r, reg)[0];
            Assert.Null(row.Outcome);
            Assert.Null(row.State);
            Assert.Equal(3, InterviewComparisonView.Summarize(r, reg).UncheckedCount);
        }

        [Fact]
        public void Roster_Consistent_WithUncheckedSuffix()
        {
            var r = Empty();
            Ok(r.AddTurn("问？", "14:19 拉半速，14:21 停车。", null));
            Ok(r.AddStatement("S1", StatementKind.Time, "Mary.telegraph_half", "14:19 半速", StatementClaim.EventTime(At(14, 19)), Ok(r.Locate(1, QaField.Answer, "14:19"))));
            Ok(r.AddStatement("S2", StatementKind.Time, "Mary.telegraph_stop", "14:21 停车", StatementClaim.EventTime(At(14, 21)), Ok(r.Locate(1, QaField.Answer, "14:21"))));
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            Ok(reg.Submit(new StatementCrossChecker().Check(r.GetStatement("S1"), new DictSource().Add("Mary.telegraph_half", DataObservation.EventAt(At(14, 19, 8), "VDR"))), "系统", Day19(10, 0)));
            Ok(reg.Confirm("S1", "调查员甲", Day19(11, 0)));
            var e = InterviewComparisonView.Roster(r, reg);
            Assert.Equal(RosterStatus.Consistent, e.Status);
            Assert.Equal("一致 · 1 条未比对", e.Label);
        }

        [Fact]
        public void Chart_AxisIncludesObservedTime_OutsideStatementRange()
        {
            var r = Empty();
            Ok(r.AddTurn("问？", "14:23 左舵。", null));
            Ok(r.AddStatement("S1", StatementKind.Time, "Mary.helm_left", "14:23 左舵", StatementClaim.EventTime(At(14, 23)), Ok(r.Locate(1, QaField.Answer, "14:23"))));
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            Ok(reg.Submit(new StatementCrossChecker().Check(r.GetStatement("S1"), new DictSource().Add("Mary.helm_left", DataObservation.EventAt(At(14, 21, 50), "VDR 舵角"))), "系统", Day19(10, 0)));
            var ch = InterviewComparisonView.Chart(r, reg);
            Assert.Equal(At(14, 21), ch.AxisStartUtc);
            Assert.Equal(At(14, 23), ch.AxisEndUtc);
        }
    }
}
