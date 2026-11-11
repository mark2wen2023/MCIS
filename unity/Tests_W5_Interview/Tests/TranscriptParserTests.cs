using System;
using System.Linq;
using Mcis.Domain.InterviewCompare;
using Mcis.Domain.Interview;
using Xunit;
using static Mcis.W5.Tests.W5Fx;

namespace Mcis.W5.Tests
{
    public class TranscriptParserTests
    {
        [Fact]
        public void Parses_QaPairs_FullAndHalfWidthColons_Continuation_Preamble()
        {
            string text = "IR-03 询问笔录（虚构）\n询问人：调查员 A\n\n问：你什么时候第一次看到 Lily 轮？\n答: 大概 14:17 左右，\n  在 3 号浮标北面。\r\nQ：能见度？\nA：有雾。\n";
            var p = TranscriptParser.Parse(text);
            Assert.True(p.IsValid, string.Join(";", p.Issues.Select(i => i.Code)));
            Assert.Empty(p.Issues);
            Assert.Equal("IR-03 询问笔录（虚构）\n询问人：调查员 A", p.Preamble);
            Assert.Equal(2, p.Turns.Count);
            Assert.Equal("你什么时候第一次看到 Lily 轮？", p.Turns[0].Question);
            Assert.Equal("大概 14:17 左右，\n在 3 号浮标北面。", p.Turns[0].Answer);
            Assert.Equal(4, p.Turns[0].QuestionLine);
            Assert.Equal("有雾。", p.Turns[1].Answer);
            Assert.Equal(new[] { 1, 2 }, p.Turns.Select(t => t.Round));
            Assert.Null(p.Turns[0].Offset);
            Assert.Null(p.Turns[0].Utc);
        }

        [Fact]
        public void RoundPrefix_AndTimestamps_GiveOffsetsAndUtc()
        {
            string text = "[00:30] 第1问 问：甲？\n答：乙。\n[01:02:05] 问：丙？\n[01:02:20] 答：丁。";
            var p = TranscriptParser.Parse(text, new TranscriptParseOptions { RecordingStartUtc = Day19(9, 30) });
            Assert.True(p.IsValid);
            Assert.Equal(TimeSpan.FromSeconds(30), p.Turns[0].Offset);
            Assert.Equal(Day19(9, 30, 30), p.Turns[0].Utc);
            Assert.Equal(new TimeSpan(1, 2, 5), p.Turns[1].Offset);
            Assert.Equal(Day19(10, 32, 5), p.Turns[1].Utc);
            Assert.Equal("甲？", p.Turns[0].Question);
        }

        [Fact]
        public void AnswerTimestamp_UsedWhenQuestionHasNone()
        {
            var p = TranscriptParser.Parse("问：甲？\n[02:00] 答：乙。");
            Assert.Equal(TimeSpan.FromMinutes(2), p.Turns[0].Offset);
        }

        [Fact]
        public void QuestionWithoutAnswer_IsWarning_TurnKept()
        {
            var p = TranscriptParser.Parse("问：甲？\n问：乙？\n答：丙。\n问：丁？");
            Assert.True(p.IsValid);
            Assert.Equal(3, p.Turns.Count);
            Assert.Equal(string.Empty, p.Turns[0].Answer);
            Assert.Equal(string.Empty, p.Turns[2].Answer);
            var w = p.Issues.Where(i => i.Code == InterviewCompareErrors.MissingAnswer).ToList();
            Assert.Equal(new[] { 1, 4 }, w.Select(i => i.Line));
            Assert.All(w, i => Assert.Equal(TranscriptIssueSeverity.Warning, i.Severity));
        }

        [Theory]
        [InlineData("答：没有问题就回答。", 1)]
        [InlineData("问：甲？\n答：乙。\n答：又一个答。", 3)]
        public void OrphanAnswer_IsError(string text, int line)
        {
            var p = TranscriptParser.Parse(text);
            Assert.False(p.IsValid);
            var e = Assert.Single(p.Issues, i => i.Code == InterviewCompareErrors.OrphanAnswer);
            Assert.Equal(line, e.Line);
            Assert.Equal(TranscriptIssueSeverity.Error, e.Severity);
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   \n\t")]
        [InlineData("只有标题，没有问答")]
        [InlineData("问题：这不是标记")]
        public void Empty_OrNoMarkers_IsEmptyTranscript(string text)
        {
            var p = TranscriptParser.Parse(text);
            Assert.False(p.IsValid);
            Assert.Equal(InterviewCompareErrors.EmptyTranscript, Assert.Single(p.Issues).Code);
            Assert.Empty(p.Turns);
        }

        [Theory]
        [InlineData("[61:00] 问：甲？\n答：乙。")]
        [InlineData("[00:75] 问：甲？\n答：乙。")]
        [InlineData("[1:60:00] 问：甲？\n答：乙。")]
        public void InvalidTimestamp_IsError(string text)
        {
            var p = TranscriptParser.Parse(text);
            Assert.False(p.IsValid);
            Assert.Contains(p.Issues, i => i.Code == InterviewCompareErrors.InvalidTimestamp && i.Line == 1);
        }

        [Fact]
        public void BackwardTimestamp_IsTimeOrderError()
        {
            var p = TranscriptParser.Parse("[05:00] 问：甲？\n答：乙。\n[04:59] 问：丙？\n答：丁。");
            Assert.False(p.IsValid);
            Assert.Equal(3, Assert.Single(p.Issues, i => i.Code == InterviewCompareErrors.TimeOrder).Line);
        }

        [Fact]
        public void ApplyTo_AppendsAllTurns_WithUtc()
        {
            var r = Empty();
            var p = TranscriptParser.Parse("[00:10] 问：甲？\n答：乙。\n[00:20] 问：丙？\n答：丁。", new TranscriptParseOptions { RecordingStartUtc = Day19(9, 0) });
            var turns = Ok(TranscriptParser.ApplyTo(p, r));
            Assert.Equal(2, turns.Count);
            Assert.Equal(2, r.Turns.Count);
            Assert.Equal("丁。", r.GetTurn(2).Answer);
            Assert.Equal(Day19(9, 0, 20), r.GetTurn(2).Utc);
        }

        [Fact]
        public void ApplyTo_InvalidParse_Rejected_NothingAppended()
        {
            var r = Empty();
            Code(InterviewCompareErrors.TranscriptInvalid, TranscriptParser.ApplyTo(TranscriptParser.Parse("答：孤立。"), r));
            Assert.Empty(r.Turns);
            Code(InterviewCompareErrors.InvalidArgument, TranscriptParser.ApplyTo(null, r));
            Code(InterviewCompareErrors.InvalidArgument, TranscriptParser.ApplyTo(TranscriptParser.Parse("问：甲？\n答：乙。"), null));
        }

        [Fact]
        public void ApplyTo_TimeBeforeRecordOrLastTurn_AllOrNothing()
        {
            var r = Empty(); // StartUtc = 05-19 09:00
            var early = TranscriptParser.Parse("[00:10] 问：甲？\n答：乙。", new TranscriptParseOptions { RecordingStartUtc = Day19(8, 0) });
            Code(InterviewCompareErrors.TimeOrder, TranscriptParser.ApplyTo(early, r));
            Assert.Empty(r.Turns);

            Ok(r.AddTurn("已有？", "已有。", Day19(9, 30)));
            var p = TranscriptParser.Parse("[00:10] 问：甲？\n答：乙。\n[40:00] 问：丙？\n答：丁。", new TranscriptParseOptions { RecordingStartUtc = Day19(9, 0) });
            Code(InterviewCompareErrors.TimeOrder, TranscriptParser.ApplyTo(p, r));
            Assert.Single(r.Turns);
        }

        [Fact]
        public void ApplyTo_EmptyQuestionAndAnswer_Rejected()
        {
            var r = Empty();
            var p = TranscriptParser.Parse("问：\n问：甲？\n答：乙。");
            Assert.True(p.IsValid);
            Code(InterviewCompareErrors.InvalidArgument, TranscriptParser.ApplyTo(p, r));
            Assert.Empty(r.Turns);
        }

        [Fact]
        public void ParsedCollections_AreReadOnly()
        {
            var p = TranscriptParser.Parse("问：甲？\n问：乙？\n答：丙。");
            Assert.Throws<NotSupportedException>(() => ((System.Collections.IList)p.Turns).Clear());
            Assert.Throws<NotSupportedException>(() => ((System.Collections.IList)p.Issues).Clear());
        }
    }
}
