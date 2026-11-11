using System;
using System.Linq;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>候选抽取：钟点、X 点、距离、舵角、航速、时长、约数词、跨日。样例为中文真实口语（虚构情节）。</summary>
    public class CandidateExtractorAcceptanceTests
    {
        private static InterviewRecord SpokenScene()
        {
            return WithTurns(
                ("你什么时候第一次在雷达上看到对方？", "大概 14:17 左右，在 3 号浮标北面，距离差不多 3 海里。"),
                ("后来车钟和航速呢？", "14:19 前后我把车钟拉到半速，当时航速大概 8 节。"),
                ("你怎么用的舵？大概什么时候？", "就在 14:23 才开始左舵，左舵 20 度，还鸣了一长声。过了大约 14:23 半，船长也上来了。"),
                ("离那灯浮还有多远？这段操作用了多久？", "离灯浮大约 2 链，前后持续了大约 3 分钟。"),
                ("你什么时候下的驾驶台？休息了多久？", "23 点半我才下去，睡了大概 2 小时。"));
        }

        [Fact]
        public void Extracts_SpokenChinese_TimesDistancesAnglesSpeedsDurations_WithHedges()
        {
            InterviewRecord rec = SpokenScene();
            var all = ClaimCandidateExtractor.Extract(rec, Options());
            Assert.NotEmpty(all);
            foreach (var c in all)
            {
                AssertSpanMatches(rec, c);
            }

            var t1417 = Require(all, CandidateKind.Time, "14:17");
            Assert.Equal(new TimeSpan(14, 17, 0), t1417.LocalTimeOfDay);
            Assert.Equal(At(5, 18, 14, 17).ToUniversalTime(), t1417.Utc);
            Assert.True(t1417.Approximate); // 「大概 … 左右」

            var t1419 = Require(all, CandidateKind.Time, "14:19");
            Assert.True(t1419.Approximate); // 「14:19 前后」
            Assert.Equal(new TimeSpan(14, 19, 0), t1419.LocalTimeOfDay);

            var t1423 = all.Single(c => c.Kind == CandidateKind.Time && c.Text == "14:23");
            Assert.False(t1423.Approximate); // 「就在 14:23」，不是约数词
            Assert.Equal(At(5, 18, 14, 23).ToUniversalTime(), t1423.Utc);

            var half = Require(all, CandidateKind.Time, "14:23 半");
            Assert.Equal(new TimeSpan(14, 23, 30), half.LocalTimeOfDay);
            Assert.Equal(At(5, 18, 14, 23, 30).ToUniversalTime(), half.Utc);
            Assert.True(half.Approximate); // 「大约 14:23 半」

            var distNm = Require(all, CandidateKind.Distance, "3 海里");
            Assert.Equal(3.0, distNm.Value);
            Assert.Equal("nm", distNm.Unit);
            Assert.True(distNm.Approximate); // 「差不多 3 海里」

            var chain = Require(all, CandidateKind.Distance, "2 链");
            Assert.Equal(0.2, chain.Value); // 1 链 = 0.1 海里
            Assert.Equal("nm", chain.Unit);
            Assert.True(chain.Approximate); // 「大约 2 链」

            var rudder = Require(all, CandidateKind.Angle, "左舵 20 度");
            Assert.Equal(20.0, rudder.Value);
            Assert.Equal("deg", rudder.Unit);
            Assert.Equal("左", rudder.Side);
            Assert.False(rudder.Approximate);

            var speed = Require(all, CandidateKind.Speed, "8 节");
            Assert.Equal(8.0, speed.Value);
            Assert.Equal("kn", speed.Unit);
            Assert.True(speed.Approximate); // 「大概 8 节」

            var durMin = Require(all, CandidateKind.Duration, "3 分钟");
            Assert.Equal(3.0, durMin.Value);
            Assert.Equal("min", durMin.Unit);
            Assert.True(durMin.Approximate);

            var durH = Require(all, CandidateKind.Duration, "2 小时");
            Assert.Equal(2.0, durH.Value);
            Assert.Equal("h", durH.Unit);
            Assert.True(durH.Approximate); // 「睡了大概 2 小时」
        }

        [Fact]
        public void CrossDay_ChineseDian_RollsBackWhenLaterThanAnchorPlusLookahead()
        {
            InterviewRecord rec = SpokenScene();
            var all = ClaimCandidateExtractor.Extract(rec, Options());
            var dian = Require(all, CandidateKind.Time, "23 点半");
            Assert.Equal(new TimeSpan(23, 30, 0), dian.LocalTimeOfDay);
            // 锚点 14:27，默认前瞻 1 小时；23:30 晚于 15:27，回滚到前一天
            Assert.Equal(At(5, 17, 23, 30).ToUniversalTime(), dian.Utc);
        }

        [Fact]
        public void ChineseDian_Variants_AndLookaheadBoundaryInclusive()
        {
            InterviewRecord rec = WithTurns(
                ("几点的事？", "14 点我在驾驶台，14 点 30 分改了航向，大约 15 点半靠近了灯浮。"));
            var all = ClaimCandidateExtractor.Extract(rec, Options());

            var h14 = all.Single(c => c.Kind == CandidateKind.Time && c.Text == "14 点");
            Assert.Equal(new TimeSpan(14, 0, 0), h14.LocalTimeOfDay);
            Assert.Equal(At(5, 18, 14, 0).ToUniversalTime(), h14.Utc);

            var h1430 = Require(all, CandidateKind.Time, "14 点 30 分");
            Assert.Equal(new TimeSpan(14, 30, 0), h1430.LocalTimeOfDay);

            var h1530 = Require(all, CandidateKind.Time, "15 点半");
            Assert.Equal(new TimeSpan(15, 30, 0), h1530.LocalTimeOfDay);
            // 15:30 > 14:27+1h=15:27，回滚
            Assert.Equal(At(5, 17, 15, 30).ToUniversalTime(), h1530.Utc);
            Assert.True(h1530.Approximate);

            // 刚好等于锚点 + 前瞻：仍算当天
            InterviewRecord edge = WithTurns(("几点？", "15:27 我还在驾驶台。"));
            var atBound = Require(ClaimCandidateExtractor.Extract(edge, Options()), CandidateKind.Time, "15:27");
            Assert.Equal(At(5, 18, 15, 27).ToUniversalTime(), atBound.Utc);

            InterviewRecord over = WithTurns(("几点？", "15:27:01 已经过了。"));
            // 15:27:01 只有在能解析秒时才会回滚；「15:27:01」是 hh:mm:ss
            var past = Require(ClaimCandidateExtractor.Extract(over, Options()), CandidateKind.Time, "15:27:01");
            Assert.Equal(At(5, 17, 15, 27, 1).ToUniversalTime(), past.Utc);
        }

        [Fact]
        public void Hedges_ImmediateOnly_YueZuoyouDagai()
        {
            InterviewRecord rec = WithTurns(
                ("距离和舵角？", "约 4 海里，右舵 10 度左右，速度 6 kn，持续 5 分钟左右。"));
            var all = ClaimCandidateExtractor.Extract(rec, Options());
            Assert.True(Require(all, CandidateKind.Distance, "4 海里").Approximate);
            Assert.True(Require(all, CandidateKind.Angle, "右舵 10 度").Approximate);
            Assert.Equal("右", Require(all, CandidateKind.Angle, "右舵 10 度").Side);
            Assert.False(Require(all, CandidateKind.Speed, "6 kn").Approximate);
            Assert.True(Require(all, CandidateKind.Duration, "5 分钟").Approximate);
        }

        [Fact]
        public void DoesNotExtract_BuoyNumber_HalfSpeed_OrChineseNumeralHours()
        {
            InterviewRecord rec = WithTurns(
                ("周围有什么？当时状态如何？", "在 3 号浮标北面，我把车钟拉到半速，中间大概睡了不到两个小时。"));
            var all = ClaimCandidateExtractor.Extract(rec, Options());
            Assert.DoesNotContain(all, c => c.Kind == CandidateKind.Time);
            Assert.DoesNotContain(all, c => c.Text.Contains("半速") || c.Text.Contains("3 号"));
            // 「两个小时」不是阿拉伯数字，按现规则不抽；记下供裁定，不算本包缺陷。
            Assert.DoesNotContain(all, c => c.Kind == CandidateKind.Duration);
        }

        [Fact]
        public void Questions_OnlyWhenRequested_AndToClaimFeedsAddStatement()
        {
            InterviewRecord rec = WithTurns(("当时航速是 12 节吗？", "没有，大概 8 节。"));
            var answersOnly = ClaimCandidateExtractor.Extract(rec, Options());
            Assert.DoesNotContain(answersOnly, c => c.Text.Contains("12"));
            Assert.Contains(answersOnly, c => c.Text.Contains("8 节"));

            var both = ClaimCandidateExtractor.Extract(rec, Options(includeQuestions: true));
            Assert.Contains(both, c => c.Span.Field == QaField.Question && c.Text.Contains("12 节"));

            var speed = Require(answersOnly, CandidateKind.Speed, "8 节");
            SourceSpan span = speed.Span;
            Ok(rec.AddStatement("S-spd", speed.SuggestedKind, "Mary.speed", speed.Text, speed.ToClaim(), span));
            Assert.Equal(8.0, rec.GetStatement("S-spd").Claim.Scalar);
            Assert.Equal("kn", rec.GetStatement("S-spd").Claim.Unit);
        }

        [Fact]
        public void Spans_AreUtf16Offsets_OrderedAndNonOverlapping()
        {
            InterviewRecord rec = SpokenScene();
            var all = ClaimCandidateExtractor.Extract(rec, Options());
            foreach (var group in all.GroupBy(c => (c.Span.Round, c.Span.Field)))
            {
                var list = group.OrderBy(c => c.Span.Start).ToList();
                for (int i = 1; i < list.Count; i++)
                {
                    Assert.True(list[i].Span.Start >= list[i - 1].Span.Start + list[i - 1].Span.Length,
                        "重叠：" + list[i - 1].Text + " / " + list[i].Text);
                }
            }
        }

        [Fact]
        public void NullRecord_ReturnsEmptyReadOnly_NullOptions_Throws()
        {
            var empty = ClaimCandidateExtractor.Extract(null, Options());
            Assert.Empty(empty);
            Assert.Throws<NotSupportedException>(() => ((System.Collections.Generic.IList<ClaimCandidate>)empty).Add(null));
            Assert.Throws<ArgumentNullException>(() => ClaimCandidateExtractor.Extract(NewRecord(), null));
        }
    }
}
