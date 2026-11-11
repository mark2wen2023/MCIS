using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>原文高亮偏移须与 UTF-16 / 中文多字节字符一致，片段拼接覆盖全文。</summary>
    public class HighlighterAcceptanceTests
    {
        [Fact]
        public void Segments_CoverWholeChineseText_OffsetsMatchSource_AndKinds()
        {
            InterviewRecord rec = NewRecord();
            const string answer = "当时能见度大约 1.5 海里，我就把车钟拉到半速，左舵 20 度。";
            Ok(rec.AddTurn("当时情况怎么样？", answer, rec.StartUtc.AddMinutes(2)));

            int iDist = answer.IndexOf("1.5 海里", StringComparison.Ordinal);
            int iRudder = answer.IndexOf("左舵 20 度", StringComparison.Ordinal);
            Assert.True(iDist >= 0 && iRudder > iDist);

            Ok(rec.AddStatement("S-vis", StatementKind.Observation, "Mary.visibility", "能见度 1.5 nm", StatementClaim.ScalarValue(1.5, "nm"),
                new SourceSpan(1, QaField.Answer, iDist, "1.5 海里".Length)));
            Ok(rec.AddStatement("S-rud", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"),
                new SourceSpan(1, QaField.Answer, iRudder, "左舵 20 度".Length)));

            var segs = TranscriptHighlighter.Segments(rec, 1, QaField.Answer);
            Assert.Equal(answer, string.Concat(segs.Select(s => s.Text)));
            Assert.Equal(0, segs[0].Start);
            Assert.Equal(answer.Length, segs.Sum(s => s.Length));
            for (int i = 1; i < segs.Count; i++)
            {
                Assert.Equal(segs[i - 1].Start + segs[i - 1].Length, segs[i].Start);
            }

            var vis = segs.Single(s => s.Text == "1.5 海里");
            Assert.Equal(iDist, vis.Start);
            Assert.Equal("1.5 海里".Length, vis.Length);
            Assert.Contains("S-vis", vis.StatementIds);
            Assert.Contains(StatementKind.Observation, vis.Kinds);
            Assert.False(vis.IsPlain);

            var rud = segs.Single(s => s.Text == "左舵 20 度");
            Assert.Equal(iRudder, rud.Start);
            Assert.Contains("S-rud", rud.StatementIds);
            Assert.Contains(StatementKind.Operation, rud.Kinds);

            Assert.Contains(segs, s => s.IsPlain && s.Text.Contains("半速"));
        }

        [Fact]
        public void Offsets_RemainAccurate_WithSurrogatePairEmoji()
        {
            InterviewRecord rec = NewRecord();
            // 👍 占两个 UTF-16 码元；下标必须按 char，不能按「可见字符」计。
            const string answer = "我在雷达上看见一个👍，距离大概 3 海里。";
            Ok(rec.AddTurn("看见什么了？", answer, rec.StartUtc.AddMinutes(2)));
            Assert.Equal(2, "👍".Length);
            int start = answer.IndexOf("3 海里", StringComparison.Ordinal);
            Assert.Equal(answer.IndexOf('3'), start);
            Ok(rec.AddStatement("S-d", StatementKind.Observation, "Mary.range", "3 nm", StatementClaim.ScalarValue(3, "nm"),
                new SourceSpan(1, QaField.Answer, start, "3 海里".Length)));

            var segs = TranscriptHighlighter.Segments(rec, 1, QaField.Answer);
            Assert.Equal(answer, string.Concat(segs.Select(s => s.Text)));
            var hit = segs.Single(s => s.StatementIds.Contains("S-d"));
            Assert.Equal(start, hit.Start);
            Assert.Equal("3 海里", hit.Text);
            Assert.Contains("👍", string.Concat(segs.Select(s => s.Text)));
        }

        [Fact]
        public void Overlap_SplitsAtBoundaries_RejectedStatementNotHighlighted()
        {
            InterviewRecord rec = NewRecord();
            const string answer = "14:23 才开始左舵 20 度。";
            Ok(rec.AddTurn("怎么用舵？", answer, rec.StartUtc.AddMinutes(2)));
            int iTime = answer.IndexOf("14:23 才开始左舵", StringComparison.Ordinal);
            int iRudder = answer.IndexOf("左舵 20 度", StringComparison.Ordinal);
            Ok(rec.AddStatement("S-t", StatementKind.Time, "Mary.helm_start", "14:23 开始左舵", StatementClaim.EventTime(At(5, 18, 14, 23)),
                new SourceSpan(1, QaField.Answer, iTime, "14:23 才开始左舵".Length)));
            Ok(rec.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"),
                new SourceSpan(1, QaField.Answer, iRudder, "左舵 20 度".Length)));

            var segs = TranscriptHighlighter.Segments(rec, 1, QaField.Answer);
            Assert.Equal(answer, string.Concat(segs.Select(s => s.Text)));
            var overlap = segs.Single(s => s.Text == "左舵");
            Assert.Contains("S-t", overlap.StatementIds);
            Assert.Contains("S-r", overlap.StatementIds);

            var audit = new InMemoryInvestigationAuditSink();
            Ok(rec.ReviewStatement("S-r", StatementReviewStatus.Rejected, Investigator, At(5, 19, 10, 0), audit, "不是这句话（虚构）"));
            var after = TranscriptHighlighter.Segments(rec, 1, QaField.Answer);
            Assert.Equal(answer, string.Concat(after.Select(s => s.Text)));
            Assert.DoesNotContain(after.SelectMany(s => s.StatementIds), id => id == "S-r");
        }

        [Fact]
        public void ContradictionMark_PendingThenConfirmed_DismissedIsNone()
        {
            InterviewRecord rec = NewRecord();
            const string answer = "当时距离差不多 3 海里。";
            Ok(rec.AddTurn("距离？", answer, rec.StartUtc.AddMinutes(2)));
            SourceSpan span = Ok(rec.Locate(1, QaField.Answer, "3 海里"));
            Ok(rec.AddStatement("S-d", StatementKind.Observation, "Mary.range", "3 nm", StatementClaim.ScalarValue(3, "nm"), span));
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            Ok(reg.Submit(new CrossCheckResult("S-d", rec.RecordId, CrossCheckOutcome.Contradictory, 2.1, "nm", "3 nm", "5.1 nm", "AIS（虚构）", "|Δ|≤0.1"), Agent, At(5, 19, 10, 0)));

            Assert.Equal(ContradictionMark.Pending, TranscriptHighlighter.Segments(rec, 1, QaField.Answer, reg).Single(s => !s.IsPlain).Contradiction);
            Ok(reg.Confirm("S-d", Investigator, At(5, 19, 10, 5)));
            Assert.Equal(ContradictionMark.Confirmed, TranscriptHighlighter.Segments(rec, 1, QaField.Answer, reg).Single(s => !s.IsPlain).Contradiction);

            // 另建一条已驳回的矛盾，标记应为 None
            InterviewRecord rec2 = NewRecord("IR-10");
            Ok(rec2.AddTurn("距离？", answer, rec2.StartUtc.AddMinutes(2)));
            Ok(rec2.AddStatement("S-e", StatementKind.Observation, "Mary.range", "3 nm", StatementClaim.ScalarValue(3, "nm"), Ok(rec2.Locate(1, QaField.Answer, "3 海里"))));
            var audit2 = new InMemoryInvestigationAuditSink();
            var reg2 = new CrossCheckRegister(audit2);
            Ok(reg2.Submit(new CrossCheckResult("S-e", rec2.RecordId, CrossCheckOutcome.Contradictory, 2.1, "nm", "3 nm", "5.1 nm", "AIS（虚构）", "|Δ|≤0.1"), Agent, At(5, 19, 10, 0)));
            Ok(reg2.Dismiss("S-e", Investigator, At(5, 19, 10, 5), "数据源有误（虚构）"));
            Assert.Equal(ContradictionMark.None, TranscriptHighlighter.Segments(rec2, 1, QaField.Answer, reg2).Single(s => !s.IsPlain).Contradiction);
        }

        [Fact]
        public void NullRecordOrUnknownRound_Empty_PlainTurn_SingleSegment()
        {
            Assert.Empty(TranscriptHighlighter.Segments(null, 1, QaField.Answer));
            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("有没有雾？", "有雾，当时什么都看不清。", rec.StartUtc.AddMinutes(2)));
            Assert.Empty(TranscriptHighlighter.Segments(rec, 9, QaField.Answer));
            var segs = TranscriptHighlighter.Segments(rec, 1, QaField.Answer);
            Assert.Single(segs);
            Assert.True(segs[0].IsPlain);
            Assert.Equal("有雾，当时什么都看不清。", segs[0].Text);
        }
    }
}
