using System;
using System.Linq;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    /// <summary>原型页 10（#interview）的虚构演示数据端到端：解析 → 候选 → 陈述 → 比对 → 页面视图。</summary>
    public class DemoTests
    {
        [Fact]
        public void Demo_IsLabelledFictional_SixRecords()
        {
            Assert.Contains("虚构", InterviewCompareDemo.Disclaimer);
            var recs = InterviewCompareDemo.Records();
            Assert.Equal(new[] { "IR-01", "IR-02", "IR-03", "IR-04", "IR-05", "IR-06" }, recs.Select(x => x.RecordId));
            Assert.All(recs, x => Assert.Equal(InterviewCompareDemo.CaseId, x.CaseId));
        }

        [Fact]
        public void Demo_IR03_TranscriptParsesAndApplies()
        {
            var p = TranscriptParser.Parse(InterviewCompareDemo.Ir03Transcript, new TranscriptParseOptions { RecordingStartUtc = InterviewCompareDemo.Ir03StartUtc });
            Assert.True(p.IsValid, string.Join(";", p.Issues.Select(i => i.Code)));
            Assert.Equal(7, p.Turns.Count);
            var ir03 = InterviewCompareDemo.Ir03();
            Assert.Equal(7, ir03.Turns.Count);
            Assert.Equal(68.0, ir03.DurationMinutes);
            Assert.True(ir03.Signed);
        }

        [Fact]
        public void Demo_IR03_PrototypeTable_SevenStatementsThreeContradictions()
        {
            var ir03 = InterviewCompareDemo.Ir03();
            var reg = InterviewCompareDemo.CheckedRegister(ir03, out _);
            var rows = InterviewComparisonView.Rows(ir03, reg);
            Assert.Equal(7, rows.Count);
            Assert.Equal(new[] { true, false, true, false, true, false, false }, rows.Select(x => x.IsContradiction));
            Assert.Equal("7 条陈述 · 3 条矛盾", InterviewComparisonView.Summarize(ir03, reg).HeaderText);
            var helm = rows.Single(x => x.Summary.Contains("左舵") && x.IsContradiction);
            Assert.Equal(45.0, helm.Delta);
            Assert.Contains("VDR", helm.DataDisplay);
            Assert.All(rows, x => Assert.Equal(StatementReviewStatus.Draft, x.ReviewStatus));
            Assert.Equal(new[] { "IR-03 第 1 问", "IR-03 第 2 问" }, rows.Take(2).Select(x => x.Citation));
        }

        [Fact]
        public void Demo_EveryStatementSpan_IsAutoCandidateOrResolvable()
        {
            var ir03 = InterviewCompareDemo.Ir03();
            foreach (var s in ir03.Statements)
            {
                Assert.Equal(s.Quote, Ok(ir03.ResolveSpan(s.Span)));
            }

            var c = ClaimCandidateExtractor.Extract(ir03, new CandidateOptions { AnchorLocal = InterviewCompareDemo.IncidentAnchorLocal });
            var times = ir03.Statements.Where(s => s.Claim.ValueType == ClaimValueType.EventTime).ToList();
            Assert.NotEmpty(times);
            foreach (var s in times)
            {
                Assert.Contains(c, x => x.Kind == CandidateKind.Time && x.Utc == s.Claim.Time && x.Span.Round == s.Span.Round);
            }
        }

        [Fact]
        public void Demo_Roster_MatchesPrototypeAfterConfirmation()
        {
            var roster = InterviewCompareDemo.ConfirmedRoster();
            Assert.Equal(new[] { "1 处矛盾", "一致", "3 处矛盾", "一致", "1 处矛盾", "一致" }, roster.Select(x => x.Label));
            var ir03 = roster.Single(x => x.RecordId == "IR-03");
            Assert.Equal("IR-03 · 05-19 09:30 · 68 min · 已签字", ir03.Subtitle(Cst));
            Assert.Equal("二副", ir03.Role);
        }

        [Fact]
        public void Demo_Chart_HelmPointShows45s()
        {
            var ir03 = InterviewCompareDemo.Ir03();
            var reg = InterviewCompareDemo.CheckedRegister(ir03, out _);
            var ch = InterviewComparisonView.Chart(ir03, reg);
            Assert.Contains(ch.Points, p => p.DeltaSeconds == 45.0 && p.Outcome == CrossCheckOutcome.Contradictory);
            Assert.Contains(ch.Points, p => p.Outcome == CrossCheckOutcome.Contradictory && p.ObservedUtc == null && p.Note.Contains("无声号"));
            Assert.True(ch.AxisStartUtc <= At(14, 17));
            Assert.True(ch.AxisEndUtc >= At(14, 23, 30));
        }

        [Fact]
        public void Demo_IsDeterministic()
        {
            var a = InterviewComparisonView.Rows(InterviewCompareDemo.Ir03(), InterviewCompareDemo.CheckedRegister(InterviewCompareDemo.Ir03(), out _));
            var r2 = InterviewCompareDemo.Ir03();
            var b = InterviewComparisonView.Rows(r2, InterviewCompareDemo.CheckedRegister(r2, out _));
            Assert.Equal(a.Select(x => x.StatementId + x.DataDisplay + x.Outcome), b.Select(x => x.StatementId + x.DataDisplay + x.Outcome));
        }
    }
}
