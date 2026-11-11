using System;
using System.Linq;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    public class HighlighterTests
    {
        [Fact]
        public void Segments_CoverWholeText_InOrder_WithKinds()
        {
            var r = Small(out var reg, out _);
            string text = r.GetTurn(1).Answer;
            var seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer);
            Assert.Equal(text, string.Concat(seg.Select(s => s.Text)));
            int pos = 0;
            foreach (var s in seg) { Assert.Equal(pos, s.Start); Assert.Equal(text.Substring(s.Start, s.Length), s.Text); pos += s.Length; }
            var tagged = seg.Where(s => !s.IsPlain).ToList();
            Assert.Equal(new[] { "14:23 开始左舵", "左舵 20 度", "鸣了一长声" }, tagged.Select(s => s.Text));
            Assert.Equal(new[] { StatementKind.Time }, tagged[0].Kinds);
            Assert.Equal(new[] { "S1" }, tagged[0].StatementIds);
            Assert.All(seg, s => Assert.Equal(ContradictionMark.None, s.Contradiction));
            Assert.All(seg.Where(s => s.IsPlain), s => Assert.Empty(s.StatementIds));
        }

        [Fact]
        public void OverlappingStatements_SplitAtBoundaries()
        {
            var r = Small(out _, out _);
            // S4 与 S1、S2 重叠：“开始左舵，左舵”
            Ok(r.AddStatement("S4", StatementKind.Operation, "Mary.helm", "开始左舵", StatementClaim.Occurrence(true), Ok(r.Locate(1, QaField.Answer, "开始左舵，左舵")), At(14, 23)));
            var seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer).Where(s => !s.IsPlain).ToList();
            Assert.Equal(new[] { "14:23 ", "开始左舵", "，", "左舵", " 20 度", "鸣了一长声" }, seg.Select(s => s.Text));
            Assert.Equal(new[] { "S1", "S4" }, seg[1].StatementIds);
            Assert.Equal(new[] { StatementKind.Time, StatementKind.Operation }, seg[1].Kinds);
            Assert.Equal(new[] { "S2", "S4" }, seg[3].StatementIds);
            Assert.Equal(new[] { StatementKind.Operation }, seg[3].Kinds); // 去重
        }

        [Fact]
        public void Contradiction_PendingThenConfirmed_DismissedIsNone_RejectedStatementHidden()
        {
            var r = Small(out var reg, out var audit);
            SubmitAll(r, reg);
            var seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer, reg).Where(s => !s.IsPlain).ToList();
            Assert.Equal(new[] { ContradictionMark.Pending, ContradictionMark.None, ContradictionMark.Pending }, seg.Select(s => s.Contradiction));
            Ok(reg.Confirm("S1", "调查员甲", Day19(11, 0)));
            Ok(reg.Dismiss("S3", "调查员甲", Day19(11, 0), "音频通道缺失（虚构）"));
            seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer, reg).Where(s => !s.IsPlain).ToList();
            Assert.Equal(new[] { ContradictionMark.Confirmed, ContradictionMark.None, ContradictionMark.None }, seg.Select(s => s.Contradiction));
            Ok(r.ReviewStatement("S2", StatementReviewStatus.Rejected, "调查员甲", Day19(11, 1), audit, "抽取错误（虚构）"));
            Assert.Equal(2, TranscriptHighlighter.Segments(r, 1, QaField.Answer, reg).Count(s => !s.IsPlain));
        }

        [Fact]
        public void RegisterEntry_FromOtherRecord_Ignored()
        {
            var r = Small(out var reg, out _);
            Ok(reg.Submit(new CrossCheckResult("S1", "IR-77", CrossCheckOutcome.Contradictory, 60, "s", "a", "b", "x", "r"), "系统", Day19(10, 0)));
            var seg = TranscriptHighlighter.Segments(r, 1, QaField.Answer, reg);
            Assert.All(seg, s => Assert.Equal(ContradictionMark.None, s.Contradiction));
        }

        [Fact]
        public void UnknownRound_OrNullRecord_Empty_PlainTurn_SingleSegment()
        {
            var r = Small(out _, out _);
            Assert.Empty(TranscriptHighlighter.Segments(r, 9, QaField.Answer));
            Assert.Empty(TranscriptHighlighter.Segments(null, 1, QaField.Answer));
            var q = TranscriptHighlighter.Segments(r, 1, QaField.Question);
            Assert.True(Assert.Single(q).IsPlain);
            Assert.Throws<NotSupportedException>(() => ((System.Collections.IList)q).Clear());
        }
    }
}
