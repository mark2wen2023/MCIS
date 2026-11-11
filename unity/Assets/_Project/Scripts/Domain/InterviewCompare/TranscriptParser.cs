using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using Mcis.Core;
using Mcis.Domain.Interview;

namespace Mcis.Domain.InterviewCompare
{
    /// <summary>解析选项。</summary>
    public sealed class TranscriptParseOptions
    {
        /// <summary>录音开始时刻（UTC）。给定时，行首时间戳（相对录音开始）换算为每轮的 UTC。</summary>
        public DateTimeOffset? RecordingStartUtc { get; set; }
    }

    public enum TranscriptIssueSeverity : byte
    {
        Warning = 0,
        Error = 1,
    }

    /// <summary>解析问题（行号从 1 起）。</summary>
    public sealed class TranscriptIssue
    {
        public string Code { get; }
        public int Line { get; }
        public string Message { get; }
        public TranscriptIssueSeverity Severity { get; }

        public TranscriptIssue(string code, int line, string message, TranscriptIssueSeverity severity)
        {
            Code = code;
            Line = line;
            Message = message ?? string.Empty;
            Severity = severity;
        }
    }

    /// <summary>解析得到的一轮问答。</summary>
    public sealed class ParsedTurn
    {
        public int Round { get; }
        public string Question { get; }
        public string Answer { get; }

        /// <summary>相对录音开始的偏移（取“问”行时间戳，缺省取“答”行）。</summary>
        public TimeSpan? Offset { get; }

        /// <summary>RecordingStartUtc + Offset；任一缺失时为 null。</summary>
        public DateTimeOffset? Utc { get; }

        /// <summary>“问”所在行号（从 1 起）。</summary>
        public int QuestionLine { get; }

        public ParsedTurn(int round, string question, string answer, TimeSpan? offset, DateTimeOffset? utc, int questionLine)
        {
            Round = round;
            Question = question ?? string.Empty;
            Answer = answer ?? string.Empty;
            Offset = offset;
            Utc = utc;
            QuestionLine = questionLine;
        }
    }

    public sealed class TranscriptParseResult
    {
        public IReadOnlyList<ParsedTurn> Turns { get; }
        public IReadOnlyList<TranscriptIssue> Issues { get; }

        /// <summary>第一个问答标记之前的文字（标题、询问人等），去首尾空白。</summary>
        public string Preamble { get; }

        /// <summary>没有 Error 级问题。</summary>
        public bool IsValid { get; }

        internal TranscriptParseResult(List<ParsedTurn> turns, List<TranscriptIssue> issues, string preamble)
        {
            Turns = new ReadOnlyCollection<ParsedTurn>(turns);
            Issues = new ReadOnlyCollection<TranscriptIssue>(issues);
            Preamble = preamble ?? string.Empty;
            bool ok = true;
            foreach (var i in issues)
            {
                ok &= i.Severity != TranscriptIssueSeverity.Error;
            }

            IsValid = ok;
        }
    }

    /// <summary>
    /// 录音转写 / PDF 笔录文本 → 问答轮次的确定性解析器（不调用 LLM）。
    /// 行格式：<c>[mm:ss] 第N问 问：……</c> / <c>答：……</c>；标记支持 问/答/Q/A，全角或半角冒号；时间戳支持 [] 或 【】，mm:ss 或 h:mm:ss。
    /// 无标记的非空行视为上一条的续行（以换行连接）。
    /// </summary>
    public static class TranscriptParser
    {
        private static readonly Regex LinePattern = new Regex(
            @"\A\s*(?:[\[【]\s*(?<ts>[0-9]{1,2}(?::[0-9]{1,2}){1,2})\s*[\]】]\s*)?(?:第\s*[0-9]+\s*问\s*)?(?<tag>问|答|Q|A)\s*[:：]\s*(?<text>.*)\z",
            RegexOptions.CultureInvariant);

        public static TranscriptParseResult Parse(string text, TranscriptParseOptions options = null)
        {
            var turns = new List<ParsedTurn>();
            var issues = new List<TranscriptIssue>();
            if (string.IsNullOrWhiteSpace(text))
            {
                issues.Add(new TranscriptIssue(InterviewCompareErrors.EmptyTranscript, 0, "转写文本为空", TranscriptIssueSeverity.Error));
                return new TranscriptParseResult(turns, issues, string.Empty);
            }

            DateTimeOffset? start = options?.RecordingStartUtc;
            string[] lines = text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            var preamble = new List<string>();
            bool sawMarker = false;
            TimeSpan? lastOffset = null;

            // 当前打开的一轮
            StringBuilder q = null, a = null;
            StringBuilder current = null;
            int qLine = 0;
            TimeSpan? turnOffset = null;
            bool hasAnswer = false;

            void Close()
            {
                if (q == null)
                {
                    return;
                }

                if (!hasAnswer)
                {
                    issues.Add(new TranscriptIssue(InterviewCompareErrors.MissingAnswer, qLine, "第 " + qLine + " 行的问没有答", TranscriptIssueSeverity.Warning));
                }

                DateTimeOffset? utc = start.HasValue && turnOffset.HasValue ? start.Value + turnOffset.Value : (DateTimeOffset?)null;
                turns.Add(new ParsedTurn(turns.Count + 1, q.ToString(), a == null ? string.Empty : a.ToString(), turnOffset, utc, qLine));
                q = null;
                a = null;
                current = null;
                turnOffset = null;
                hasAnswer = false;
            }

            for (int i = 0; i < lines.Length; i++)
            {
                int lineNo = i + 1;
                string raw = lines[i];
                if (raw.Trim().Length == 0)
                {
                    continue;
                }

                Match m = LinePattern.Match(raw);
                if (!m.Success)
                {
                    if (!sawMarker)
                    {
                        preamble.Add(raw.Trim());
                    }
                    else if (current != null)
                    {
                        current.Append('\n').Append(raw.Trim());
                    }

                    continue;
                }

                sawMarker = true;
                TimeSpan? offset = null;
                if (m.Groups["ts"].Success)
                {
                    TimeSpan ts;
                    if (!TryParseOffset(m.Groups["ts"].Value, out ts))
                    {
                        issues.Add(new TranscriptIssue(InterviewCompareErrors.InvalidTimestamp, lineNo, "时间戳非法：" + m.Groups["ts"].Value, TranscriptIssueSeverity.Error));
                    }
                    else
                    {
                        if (lastOffset.HasValue && ts < lastOffset.Value)
                        {
                            issues.Add(new TranscriptIssue(InterviewCompareErrors.TimeOrder, lineNo, "时间戳早于上一条", TranscriptIssueSeverity.Error));
                        }

                        lastOffset = ts;
                        offset = ts;
                    }
                }

                string tag = m.Groups["tag"].Value;
                string body = m.Groups["text"].Value.Trim();
                bool isQuestion = tag == "问" || tag == "Q";
                if (isQuestion)
                {
                    Close();
                    q = new StringBuilder(body);
                    current = q;
                    qLine = lineNo;
                    turnOffset = offset;
                }
                else if (q == null || hasAnswer)
                {
                    issues.Add(new TranscriptIssue(InterviewCompareErrors.OrphanAnswer, lineNo, "答之前没有未回答的问", TranscriptIssueSeverity.Error));
                    current = null;
                }
                else
                {
                    a = new StringBuilder(body);
                    current = a;
                    hasAnswer = true;
                    if (!turnOffset.HasValue)
                    {
                        turnOffset = offset;
                    }
                }
            }

            Close();
            if (!sawMarker)
            {
                issues.Add(new TranscriptIssue(InterviewCompareErrors.EmptyTranscript, 0, "未找到问/答标记", TranscriptIssueSeverity.Error));
                return new TranscriptParseResult(new List<ParsedTurn>(), issues, string.Join("\n", preamble));
            }

            return new TranscriptParseResult(turns, issues, string.Join("\n", preamble));
        }

        /// <summary>
        /// 把解析结果追加到笔录（全有或全无）：先整体预检（有效性、问答非全空、时间不早于笔录开始与已有末轮、单调），全部通过才逐轮 AddTurn。
        /// </summary>
        public static Result<IReadOnlyList<QaTurn>> ApplyTo(TranscriptParseResult parsed, InterviewRecord record)
        {
            if (parsed == null || record == null)
            {
                return Result<IReadOnlyList<QaTurn>>.Fail(InterviewCompareErrors.InvalidArgument, "解析结果与笔录不能为空");
            }

            if (!parsed.IsValid)
            {
                return Result<IReadOnlyList<QaTurn>>.Fail(InterviewCompareErrors.TranscriptInvalid, "解析结果含错误，不能写入");
            }

            DateTimeOffset floor = record.StartUtc;
            for (int i = record.Turns.Count - 1; i >= 0; i--)
            {
                if (record.Turns[i].Utc.HasValue)
                {
                    floor = record.Turns[i].Utc.Value; // W3 AddTurn 保证已有轮次时间 ≥ StartUtc
                    break;
                }
            }

            foreach (var t in parsed.Turns)
            {
                if (t.Question.Trim().Length == 0 && t.Answer.Trim().Length == 0)
                {
                    return Result<IReadOnlyList<QaTurn>>.Fail(InterviewCompareErrors.InvalidArgument, "第 " + t.Round + " 轮问答均为空");
                }

                if (t.Utc.HasValue)
                {
                    if (t.Utc.Value < floor)
                    {
                        return Result<IReadOnlyList<QaTurn>>.Fail(InterviewCompareErrors.TimeOrder, "第 " + t.Round + " 轮时间早于笔录开始或上一轮");
                    }

                    floor = t.Utc.Value;
                }
            }

            var added = new List<QaTurn>();
            foreach (var t in parsed.Turns)
            {
                Result<QaTurn> r = record.AddTurn(t.Question, t.Answer, t.Utc);
                if (!r.IsSuccess)
                {
                    // 预检已覆盖 AddTurn 的全部拒绝条件；此处仅作防御，透传 W3 错误码。
                    return Result<IReadOnlyList<QaTurn>>.Fail(r.ErrorCode, r.ErrorMessage);
                }

                added.Add(r.Value);
            }

            return Result<IReadOnlyList<QaTurn>>.Ok(new ReadOnlyCollection<QaTurn>(added));
        }

        private static bool TryParseOffset(string s, out TimeSpan offset)
        {
            offset = TimeSpan.Zero;
            string[] p = s.Split(':');
            int[] v = new int[p.Length];
            for (int i = 0; i < p.Length; i++)
            {
                v[i] = int.Parse(p[i], NumberStyles.None, CultureInfo.InvariantCulture);
            }

            int h = p.Length == 3 ? v[0] : 0;
            int mi = v[p.Length - 2];
            int se = v[p.Length - 1];
            if (mi > 59 || se > 59)
            {
                return false;
            }

            offset = new TimeSpan(h, mi, se);
            return true;
        }
    }
}
