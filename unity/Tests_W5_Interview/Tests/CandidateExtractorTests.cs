using System;
using System.Linq;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    public class CandidateExtractorTests
    {
        private static CandidateOptions Opt() { return new CandidateOptions { AnchorLocal = At(14, 27) }; }

        private static InterviewRecord One(string answer, string question = "问？")
        {
            var r = Empty();
            Ok(r.AddTurn(question, answer, Day19(9, 5)));
            return r;
        }

        [Fact]
        public void Times_HhMm_Seconds_Half_AndApproximate()
        {
            var r = One("大概 14:17 左右看到，14:19:08 拉半速，船长 14:23 半才上来。");
            var c = ClaimCandidateExtractor.Extract(r, Opt()).Where(x => x.Kind == CandidateKind.Time).ToList();
            Assert.Equal(new[] { "14:17", "14:19:08", "14:23 半" }, c.Select(x => x.Text));
            Assert.Equal(At(14, 17).ToUniversalTime(), c[0].Utc);
            Assert.Equal(TimeSpan.Zero, c[0].Utc.Value.Offset);
            Assert.True(c[0].Approximate);
            Assert.Equal(At(14, 19, 8).ToUniversalTime(), c[1].Utc);
            Assert.False(c[1].Approximate);
            Assert.Equal(At(14, 23, 30).ToUniversalTime(), c[2].Utc);
            Assert.All(c, x => Assert.Equal(ClaimValueType.EventTime, x.ValueType));
            Assert.All(c, x => Assert.Equal(StatementKind.Time, x.SuggestedKind));
        }

        [Fact]
        public void Times_ChineseDian_AndDayRollback_ByAnchor()
        {
            var r = One("前一天晚上 22 点才下来，0 点又接班，14 点半在驾驶台。");
            var c = ClaimCandidateExtractor.Extract(r, Opt()).Where(x => x.Kind == CandidateKind.Time).ToList();
            Assert.Equal(new[] { "22 点", "0 点", "14 点半" }, c.Select(x => x.Text));
            Assert.Equal(new DateTimeOffset(2026, 5, 17, 22, 0, 0, Cst).ToUniversalTime(), c[0].Utc); // 晚于锚点+1h → 前一天
            Assert.Equal(At(0, 0).ToUniversalTime(), c[1].Utc);
            Assert.Equal(At(14, 30).ToUniversalTime(), c[2].Utc);
            Assert.Equal(new TimeSpan(22, 0, 0), c[0].LocalTimeOfDay);
        }

        [Fact]
        public void Lookahead_Configurable()
        {
            var r = One("15:10 报告。");
            Assert.Equal(At(15, 10).ToUniversalTime(), ClaimCandidateExtractor.Extract(r, Opt()).Single().Utc);
            var tight = new CandidateOptions { AnchorLocal = At(14, 27), Lookahead = TimeSpan.Zero };
            Assert.Equal(new DateTimeOffset(2026, 5, 17, 15, 10, 0, Cst).ToUniversalTime(), ClaimCandidateExtractor.Extract(r, tight).Single().Utc);
        }

        [Fact]
        public void Scalars_DistanceAngleSpeedDuration_WithUnitsAndSide()
        {
            var r = One("距离差不多 3 海里，能见度 1.5 nm，相距 800 米、2 链，左舵 20 度，右满舵 35°，航速 13.5 节，矢量设成 3 分钟。");
            var c = ClaimCandidateExtractor.Extract(r, Opt());
            Assert.DoesNotContain(c, x => x.Kind == CandidateKind.Time);
            var d = c.Where(x => x.Kind == CandidateKind.Distance).ToList();
            Assert.Equal(new[] { 3.0, 1.5, 800.0, 0.2 }, d.Select(x => x.Value.Value));
            Assert.Equal(new[] { "nm", "nm", "m", "nm" }, d.Select(x => x.Unit));
            Assert.True(d[0].Approximate);
            Assert.Equal(StatementKind.Observation, d[0].SuggestedKind);
            var a = c.Where(x => x.Kind == CandidateKind.Angle).ToList();
            Assert.Equal(new[] { "左舵 20 度", "右满舵 35°" }, a.Select(x => x.Text));
            Assert.Equal(new[] { "左", "右" }, a.Select(x => x.Side));
            Assert.Equal(new[] { 20.0, 35.0 }, a.Select(x => x.Value.Value));
            Assert.All(a, x => Assert.Equal("deg", x.Unit));
            Assert.Equal(StatementKind.Operation, a[0].SuggestedKind);
            var s = Assert.Single(c, x => x.Kind == CandidateKind.Speed);
            Assert.Equal(13.5, s.Value);
            Assert.Equal("kn", s.Unit);
            var m = Assert.Single(c, x => x.Kind == CandidateKind.Duration);
            Assert.Equal(3.0, m.Value);
            Assert.Equal("min", m.Unit);
            Assert.All(c, x => Assert.Equal(ClaimValueType.Scalar, x.ValueType));
        }

        [Fact]
        public void Spans_ResolveToTheSameText_InRecord_OrderedNonOverlapping()
        {
            var r = One("在 14:23 才开始左舵，左舵 20 度，约 3 海里。");
            Ok(r.AddTurn("第二问？", "14:20 VTS 呼叫，航速 9.5 kn。", Day19(9, 6)));
            var c = ClaimCandidateExtractor.Extract(r, Opt());
            Assert.Equal(5, c.Count);
            foreach (var x in c)
            {
                Assert.Equal(x.Text, Ok(r.ResolveSpan(x.Span)));
                Assert.Equal(QaField.Answer, x.Span.Field);
            }

            for (int i = 1; i < c.Count; i++)
            {
                var p = c[i - 1].Span; var q = c[i].Span;
                Assert.True(p.Round < q.Round || (p.Round == q.Round && p.Start + p.Length <= q.Start));
            }
        }

        [Fact]
        public void NoFalsePositives_OnNonQuantities()
        {
            var r = One("在 3 号浮标北面，能见度不好，没有叫船长，第 2 次报警，1.5 倍，IR-03 号笔录。");
            Assert.Empty(ClaimCandidateExtractor.Extract(r, Opt()));
        }

        [Fact]
        public void Questions_OnlyWhenRequested()
        {
            var r = One("好的。", "你 14:20 在干什么？");
            Assert.Empty(ClaimCandidateExtractor.Extract(r, Opt()));
            var c = ClaimCandidateExtractor.Extract(r, new CandidateOptions { AnchorLocal = At(14, 27), IncludeQuestions = true });
            Assert.Equal(QaField.Question, Assert.Single(c).Span.Field);
        }

        [Fact]
        public void NullRecord_EmptyList_AndReadOnly()
        {
            Assert.Empty(ClaimCandidateExtractor.Extract(null, Opt()));
            var c = ClaimCandidateExtractor.Extract(One("14:20 呼叫。"), Opt());
            Assert.Throws<NotSupportedException>(() => ((System.Collections.IList)c).Clear());
            Assert.Throws<ArgumentNullException>(() => ClaimCandidateExtractor.Extract(One("x"), null));
        }

        [Fact]
        public void Candidate_ToClaim_FeedsW3AddStatement()
        {
            var r = One("在 14:23 才开始左舵，左舵 20 度。");
            var c = ClaimCandidateExtractor.Extract(r, Opt());
            var t = c.First(x => x.Kind == CandidateKind.Time);
            var st = Ok(r.AddStatement("S1", t.SuggestedKind, "Mary.helm_left", t.Text, t.ToClaim(), t.Span));
            Assert.Equal(At(14, 23).ToUniversalTime(), st.Claim.Time);
            Assert.Equal(StatementReviewStatus.Draft, st.ReviewStatus);
            var a = c.First(x => x.Kind == CandidateKind.Angle).ToClaim();
            Assert.Equal(20.0, a.Scalar);
            Assert.Equal("deg", a.Unit);
        }
    }
}
