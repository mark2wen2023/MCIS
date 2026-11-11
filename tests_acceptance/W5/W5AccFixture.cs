using System;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;

namespace Mcis.Acceptance.W5
{
    /// <summary>W5 验收夹具。全部为虚构口语样例（星屿港 Lily × Mary，船时 UTC+8），不读 reports/。</summary>
    internal static class W5AccFixture
    {
        public static readonly TimeSpan Cst = TimeSpan.FromHours(8);
        public const string Investigator = "调查员 A（虚构）";
        public const string Agent = "笔录智能体（虚构）";
        public const string CaseId = "CASE-2026-LM01";

        public static DateTimeOffset At(int month, int day, int hour, int minute, int second = 0)
        {
            return new DateTimeOffset(2026, month, day, hour, minute, second, Cst);
        }

        public static DateTimeOffset IncidentAnchor()
        {
            return At(5, 18, 14, 27);
        }

        public static T Ok<T>(Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static void Code<T>(string expected, Result<T> r)
        {
            Assert.False(r.IsSuccess, "期望失败 " + expected + "，实际成功");
            Assert.Equal(expected, r.ErrorCode);
        }

        public static InterviewRecord NewRecord(string id = "IR-09", DateTimeOffset? start = null, bool signed = false)
        {
            return new InterviewRecord(
                id,
                new Interviewee("P-" + id.Replace("IR-", "W5-"), "证人（虚构）", "二副", "Mary 轮（虚构）"),
                start ?? At(5, 19, 9, 0),
                new[] { Investigator },
                "记录员 B（虚构）",
                "星屿港海事局询问室（虚构）",
                caseId: CaseId,
                signed: signed);
        }

        public static InterviewRecord WithTurns(params (string q, string a)[] turns)
        {
            InterviewRecord r = NewRecord();
            DateTimeOffset t = r.StartUtc;
            foreach (var pair in turns)
            {
                t = t.AddMinutes(2);
                Ok(r.AddTurn(pair.q, pair.a, t));
            }

            return r;
        }

        public static CandidateOptions Options(DateTimeOffset? anchor = null, TimeSpan? lookahead = null, bool includeQuestions = false)
        {
            return new CandidateOptions
            {
                AnchorLocal = anchor ?? IncidentAnchor(),
                Lookahead = lookahead ?? TimeSpan.FromHours(1),
                IncludeQuestions = includeQuestions
            };
        }

        public static ClaimCandidate Require(System.Collections.Generic.IEnumerable<ClaimCandidate> all, CandidateKind kind, string textContains)
        {
            var hits = all.Where(c => c.Kind == kind && c.Text.Contains(textContains)).ToList();
            Assert.True(hits.Count == 1, "期望恰好一条 " + kind + " 含「" + textContains + "」，实际 " + hits.Count + "：" + string.Join("；", hits.Select(c => c.Text)));
            return hits[0];
        }

        public static void AssertSpanMatches(InterviewRecord rec, ClaimCandidate c)
        {
            string field = rec.GetTurn(c.Span.Round).TextOf(c.Span.Field);
            Assert.InRange(c.Span.Start, 0, field.Length);
            Assert.Equal(c.Text, field.Substring(c.Span.Start, c.Span.Length));
        }
    }
}
