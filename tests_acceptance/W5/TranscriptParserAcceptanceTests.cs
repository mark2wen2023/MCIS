using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>转写解析：问/答/Q/A 各种格式、时间戳、全有或全无写入。样例为虚构口语。</summary>
    public class TranscriptParserAcceptanceTests
    {
        [Fact]
        public void Parses_ChineseAndEnglishTags_FullAndHalfWidthColons_WithContinuationAndPreamble()
        {
            const string text =
                "IR-09 询问笔录（示例数据，虚构）\n" +
                "受询问人：二副（虚构）\n" +
                "\n" +
                "问：你什么时候第一次看到对方？\n" +
                "答：大概 14:17 左右，在 3 号浮标北面。\n" +
                "当时距离差不多 3 海里。\n" +
                "Q: What was the visibility like?\n" +
                "A：有雾，能见度大约 1.5 海里。\n" +
                "第3问 问：你采取了什么行动？\n" +
                "答: 我就左舵 20 度，同时鸣了一长声。\n";

            var parsed = TranscriptParser.Parse(text);
            Assert.True(parsed.IsValid, string.Join("；", parsed.Issues.Select(i => i.Code + ":" + i.Message)));
            Assert.Equal("IR-09 询问笔录（示例数据，虚构）\n受询问人：二副（虚构）", parsed.Preamble);
            Assert.Equal(3, parsed.Turns.Count);
            Assert.Equal(1, parsed.Turns[0].Round);
            Assert.Equal("你什么时候第一次看到对方？", parsed.Turns[0].Question);
            Assert.Equal("大概 14:17 左右，在 3 号浮标北面。\n当时距离差不多 3 海里。", parsed.Turns[0].Answer);
            Assert.Equal("What was the visibility like?", parsed.Turns[1].Question);
            Assert.Equal("有雾，能见度大约 1.5 海里。", parsed.Turns[1].Answer);
            Assert.Equal("你采取了什么行动？", parsed.Turns[2].Question);
            Assert.Equal("我就左舵 20 度，同时鸣了一长声。", parsed.Turns[2].Answer);
            Assert.All(parsed.Turns, t => Assert.Null(t.Offset));
            Assert.All(parsed.Turns, t => Assert.Null(t.Utc));
        }

        [Fact]
        public void Timestamps_SquareAndBookBrackets_MmSsAndHms_ConvertWhenStartGiven()
        {
            const string text =
                "笔录（虚构）\n" +
                "[02:00] 第1问 问：第一次发现是什么时候？\n" +
                "答：大概 14:17。\n" +
                "【10:05】问：后来呢？\n" +
                "[10:06] 答：我把车钟拉到半速。\n" +
                "[1:08:00] Q: 以上是否属实？\n" +
                "A: 属实。\n";

            var start = At(5, 19, 9, 30);
            var parsed = TranscriptParser.Parse(text, new TranscriptParseOptions { RecordingStartUtc = start });
            Assert.True(parsed.IsValid, string.Join("；", parsed.Issues.Select(i => i.Message)));
            Assert.Equal(3, parsed.Turns.Count);
            Assert.Equal(TimeSpan.FromMinutes(2), parsed.Turns[0].Offset);
            Assert.Equal(start + TimeSpan.FromMinutes(2), parsed.Turns[0].Utc);
            // 问行已有【10:05】，答行 [10:06] 不覆盖（缺省才用答行时间戳）
            Assert.Equal(new TimeSpan(0, 10, 5), parsed.Turns[1].Offset);
            Assert.Equal(start + new TimeSpan(0, 10, 5), parsed.Turns[1].Utc);
            Assert.Equal(new TimeSpan(1, 8, 0), parsed.Turns[2].Offset);
            Assert.Equal(start + new TimeSpan(1, 8, 0), parsed.Turns[2].Utc);
        }

        [Fact]
        public void AllOrNone_Timestamps_QuestionWithoutStampFallsBackToAnswer_OrStaysNull()
        {
            var noStamp = TranscriptParser.Parse("问：现在几点？\n答：大约 14 点。\n");
            Assert.True(noStamp.IsValid);
            Assert.Null(noStamp.Turns[0].Offset);

            var onlyAnswer = TranscriptParser.Parse("[03:00] 答：大约 14 点。\n问：能见度呢？\n[03:10] 答：1.5 海里。\n");
            // 先孤立的答是错误；换合法文本：问无戳、答有戳
            onlyAnswer = TranscriptParser.Parse("问：现在几点？\n[03:00] 答：大约 14 点。\n");
            Assert.True(onlyAnswer.IsValid);
            Assert.Equal(TimeSpan.FromMinutes(3), onlyAnswer.Turns[0].Offset);

            var all = TranscriptParser.Parse("[00:00] 问：甲？\n[00:05] 答：乙。\n[00:10] 问：丙？\n[00:15] 答：丁。\n");
            Assert.True(all.IsValid);
            Assert.Equal(TimeSpan.Zero, all.Turns[0].Offset);
            Assert.Equal(TimeSpan.FromSeconds(10), all.Turns[1].Offset);
        }

        [Fact]
        public void ApplyTo_AllOrNothing_AppendsTurnsWithUtc_AndRejectsInvalidOrOutOfOrder()
        {
            InterviewRecord rec = NewRecord("IR-11", At(5, 19, 9, 30));
            var start = rec.StartUtc;
            var good = TranscriptParser.Parse(
                "[00:00] 问：第一次发现？\n答：大概 14:17。\n[02:00] 问：距离呢？\n答：差不多 3 海里。\n",
                new TranscriptParseOptions { RecordingStartUtc = start });
            var added = Ok(TranscriptParser.ApplyTo(good, rec));
            Assert.Equal(2, added.Count);
            Assert.Equal(2, rec.Turns.Count);
            Assert.Equal(start, rec.Turns[0].Utc);
            Assert.Equal(start + TimeSpan.FromMinutes(2), rec.Turns[1].Utc);
            Assert.Equal("第一次发现？", rec.Turns[0].Question);

            // 含错误的解析不得写入
            int n = rec.Turns.Count;
            var bad = TranscriptParser.Parse("答：先有答没有问（虚构）\n");
            Code(InterviewCompareErrors.TranscriptInvalid, TranscriptParser.ApplyTo(bad, rec));
            Assert.Equal(n, rec.Turns.Count);

            // 时间早于已有末轮：整批不写
            var early = TranscriptParser.Parse(
                "[01:00] 问：这轮时间夹在中间？\n答：不该写入。\n",
                new TranscriptParseOptions { RecordingStartUtc = start });
            Assert.True(early.IsValid);
            Code(InterviewCompareErrors.TimeOrder, TranscriptParser.ApplyTo(early, rec));
            Assert.Equal(n, rec.Turns.Count);
        }

        [Fact]
        public void ApplyTo_NullArgs_AndEmptyQa_AreRejected_NothingAppended()
        {
            InterviewRecord rec = NewRecord();
            Code(InterviewCompareErrors.InvalidArgument, TranscriptParser.ApplyTo(null, rec));
            Code(InterviewCompareErrors.InvalidArgument, TranscriptParser.ApplyTo(TranscriptParser.Parse("问：甲？\n答：乙。\n"), null));

            var emptyQa = TranscriptParser.Parse("问：\n答：\n");
            Assert.True(emptyQa.IsValid);
            Code(InterviewCompareErrors.InvalidArgument, TranscriptParser.ApplyTo(emptyQa, rec));
            Assert.Empty(rec.Turns);
        }

        [Fact]
        public void ApplyTo_TurnExactlyAtRecordStart_Accepted()
        {
            InterviewRecord rec = NewRecord("IR-12", At(5, 19, 9, 30));
            var parsed = TranscriptParser.Parse(
                "[00:00] 问：现在开始？\n答：开始了。\n",
                new TranscriptParseOptions { RecordingStartUtc = rec.StartUtc });
            Ok(TranscriptParser.ApplyTo(parsed, rec));
            Assert.Equal(rec.StartUtc, rec.Turns[0].Utc);
        }

        [Theory]
        [InlineData("")]
        [InlineData("   ")]
        [InlineData("这是一段没有问答标记的说明（虚构）")]
        public void EmptyOrNoMarkers_IsEmptyTranscript(string text)
        {
            var parsed = TranscriptParser.Parse(text);
            Assert.False(parsed.IsValid);
            Assert.Contains(parsed.Issues, i => i.Code == InterviewCompareErrors.EmptyTranscript && i.Severity == TranscriptIssueSeverity.Error);
            Assert.Empty(parsed.Turns);
        }

        [Fact]
        public void OrphanAnswer_IsError_MissingAnswer_IsWarningButTurnKept()
        {
            var orphan = TranscriptParser.Parse("答：还没问就先答了（虚构）。\n");
            Assert.False(orphan.IsValid);
            Assert.Contains(orphan.Issues, i => i.Code == InterviewCompareErrors.OrphanAnswer && i.Line == 1);

            var missing = TranscriptParser.Parse("问：你当时在哪？\n问：能见度怎么样？\n答：有雾。\n");
            Assert.True(missing.IsValid, "缺答只是警告，解析仍有效");
            Assert.Contains(missing.Issues, i => i.Code == InterviewCompareErrors.MissingAnswer && i.Severity == TranscriptIssueSeverity.Warning);
            Assert.Equal(2, missing.Turns.Count);
            Assert.Equal(string.Empty, missing.Turns[0].Answer);
            Assert.Equal("有雾。", missing.Turns[1].Answer);
        }

        [Theory]
        [InlineData("[00:60] 问：非法秒？\n答：是。\n")]
        [InlineData("[61:00] 问：非法分？\n答：是。\n")]
        [InlineData("[1:00:60] 问：时分秒非法秒？\n答：是。\n")]
        public void InvalidTimestamp_IsError(string text)
        {
            var parsed = TranscriptParser.Parse(text);
            Assert.False(parsed.IsValid);
            Assert.Contains(parsed.Issues, i => i.Code == InterviewCompareErrors.InvalidTimestamp);
        }

        [Fact]
        public void Timestamp_59_59_IsValid_EqualTimestamps_AreNotTimeOrderError()
        {
            var edge = TranscriptParser.Parse("[00:59:59] 问：边界？\n答：合法。\n");
            Assert.True(edge.IsValid);
            Assert.Equal(new TimeSpan(0, 59, 59), edge.Turns[0].Offset);

            var equal = TranscriptParser.Parse("[03:00] 问：同一秒？\n[03:00] 答：可以。\n");
            Assert.True(equal.IsValid);
            Assert.DoesNotContain(equal.Issues, i => i.Code == InterviewCompareErrors.TimeOrder);
        }

        [Fact]
        public void BackwardTimestamp_IsTimeOrderError()
        {
            var parsed = TranscriptParser.Parse("[05:00] 问：先问？\n答：先答。\n[04:59] 问：倒退？\n答：不行。\n");
            Assert.False(parsed.IsValid);
            Assert.Contains(parsed.Issues, i => i.Code == InterviewCompareErrors.TimeOrder && i.Line == 3);
        }
    }
}
