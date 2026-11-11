using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Text.RegularExpressions;
using Mcis.Domain.Interview;

namespace Mcis.Domain.InterviewCompare
{
    public enum CandidateKind : byte
    {
        Time = 0,
        Distance = 1,
        Angle = 2,
        Speed = 3,
        Duration = 4,
    }

    public sealed class CandidateOptions
    {
        /// <summary>事故参照时刻（船时，带偏移）。笔录里的钟点按此日期与偏移落地。</summary>
        public DateTimeOffset AnchorLocal { get; set; }

        /// <summary>钟点落地后若晚于 AnchorLocal + Lookahead，则视为前一天。默认 1 小时。</summary>
        public TimeSpan Lookahead { get; set; } = TimeSpan.FromHours(1);

        /// <summary>是否也从“问”里抽取（默认只抽“答”）。</summary>
        public bool IncludeQuestions { get; set; }
    }

    /// <summary>规则抽取的陈述候选（仅供调查员/代理挑选，不自动入笔录）。</summary>
    public sealed class ClaimCandidate
    {
        public SourceSpan Span { get; }
        public string Text { get; }
        public CandidateKind Kind { get; }
        public StatementKind SuggestedKind { get; }
        public ClaimValueType ValueType { get; }

        /// <summary>时间候选落地后的 UTC（Offset = 0）。</summary>
        public DateTimeOffset? Utc { get; }

        /// <summary>时间候选的钟点（船时）。</summary>
        public TimeSpan? LocalTimeOfDay { get; }

        public double? Value { get; }
        public string Unit { get; }

        /// <summary>舵角方向：“左”/“右”/空。</summary>
        public string Side { get; }

        /// <summary>前有“大概/大约/约/差不多”或后有“左右/前后”。</summary>
        public bool Approximate { get; }

        internal ClaimCandidate(SourceSpan span, string text, CandidateKind kind, DateTimeOffset? utc, TimeSpan? tod, double? value, string unit, string side, bool approximate)
        {
            Span = span;
            Text = text;
            Kind = kind;
            SuggestedKind = kind == CandidateKind.Time ? StatementKind.Time
                : kind == CandidateKind.Angle || kind == CandidateKind.Speed ? StatementKind.Operation
                : StatementKind.Observation;
            ValueType = kind == CandidateKind.Time ? ClaimValueType.EventTime : ClaimValueType.Scalar;
            Utc = utc;
            LocalTimeOfDay = tod;
            Value = value;
            Unit = unit ?? string.Empty;
            Side = side ?? string.Empty;
            Approximate = approximate;
        }

        /// <summary>转成 W3 的 StatementClaim，可直接交给 InterviewRecord.AddStatement。</summary>
        public StatementClaim ToClaim()
        {
            return Kind == CandidateKind.Time ? StatementClaim.EventTime(Utc.Value) : StatementClaim.ScalarValue(Value.Value, Unit);
        }
    }

    /// <summary>
    /// 确定性的数量/时刻候选抽取器（正则规则，不调用 LLM）。识别：钟点（14:23、14:23:30、14:23 半、14 点、14 点 30 分、14 点半）、
    /// 距离（海里/nm/链/公里/千米/米）、舵角（[左|右][满]舵 N 度/°）、航速（节/kn/kt）、时长（分钟/小时）。
    /// 重叠时起点靠前者优先，起点相同取更长者。
    /// </summary>
    public static class ClaimCandidateExtractor
    {
        private const string Num = @"(?<v>[0-9]+(?:\.[0-9]+)?)";

        private static readonly Regex Clock = new Regex(@"(?<![0-9:.])(?<h>[0-9]{1,2}):(?<m>[0-9]{2})(?::(?<s>[0-9]{2}))?(?![0-9:])(?:\s*(?<half>半)(?![速舵]))?", RegexOptions.CultureInvariant);
        private static readonly Regex Dian = new Regex(@"(?<![0-9.])(?<h>[0-9]{1,2})\s*点(?:\s*(?<m>[0-9]{1,2})\s*分(?!钟)|(?<half>半)(?![速舵]))?", RegexOptions.CultureInvariant);
        private static readonly Regex Distance = new Regex(@"(?<![0-9.])" + Num + @"\s*(?<u>海里|浬|nm|NM|链|公里|千米|米(?!/))(?![A-Za-z])", RegexOptions.CultureInvariant);
        private static readonly Regex Angle = new Regex(@"(?:(?<side>左|右)\s*(?:满舵|舵)?\s*)?(?<![0-9.])" + Num + @"\s*(?:度|°)", RegexOptions.CultureInvariant);
        private static readonly Regex Speed = new Regex(@"(?<![0-9.])" + Num + @"\s*(?<u>节|kn|kts|kt)(?![A-Za-z])", RegexOptions.CultureInvariant);
        private static readonly Regex Duration = new Regex(@"(?<![0-9.])" + Num + @"\s*(?<u>分钟|小时)", RegexOptions.CultureInvariant);

        private static readonly string[] HedgeBefore = { "大概", "大约", "差不多", "约" };
        private static readonly string[] HedgeAfter = { "左右", "前后" };

        public static IReadOnlyList<ClaimCandidate> Extract(InterviewRecord record, CandidateOptions options)
        {
            if (options == null)
            {
                throw new ArgumentNullException(nameof(options));
            }

            var all = new List<ClaimCandidate>();
            if (record != null)
            {
                foreach (QaTurn t in record.Turns)
                {
                    if (options.IncludeQuestions)
                    {
                        all.AddRange(FromText(t.Round, QaField.Question, t.Question, options));
                    }

                    all.AddRange(FromText(t.Round, QaField.Answer, t.Answer, options));
                }
            }

            return new ReadOnlyCollection<ClaimCandidate>(all);
        }

        private static List<ClaimCandidate> FromText(int round, QaField field, string text, CandidateOptions o)
        {
            var raw = new List<ClaimCandidate>();
            foreach (Match m in Clock.Matches(text))
            {
                int h = Int(m.Groups["h"].Value), mi = Int(m.Groups["m"].Value);
                int se = m.Groups["s"].Success ? Int(m.Groups["s"].Value) : 0;
                if (h < 24 && mi < 60 && se < 60)
                {
                    var tod = new TimeSpan(h, mi, se) + (m.Groups["half"].Success ? TimeSpan.FromSeconds(30) : TimeSpan.Zero);
                    raw.Add(TimeCandidate(round, field, text, m, tod, o));
                }
            }

            foreach (Match m in Dian.Matches(text))
            {
                int h = Int(m.Groups["h"].Value);
                int mi = m.Groups["m"].Success ? Int(m.Groups["m"].Value) : m.Groups["half"].Success ? 30 : 0;
                if (h < 24 && mi < 60)
                {
                    raw.Add(TimeCandidate(round, field, text, m, new TimeSpan(h, mi, 0), o));
                }
            }

            foreach (Match m in Distance.Matches(text))
            {
                double v = Dbl(m.Groups["v"].Value);
                string u = m.Groups["u"].Value;
                string unit = u == "米" ? "m" : u == "公里" || u == "千米" ? "km" : "nm";
                if (u == "链")
                {
                    v = v / 10.0; // 1 链 = 0.1 海里
                }

                raw.Add(Scalar(round, field, text, m, CandidateKind.Distance, v, unit, null));
            }

            foreach (Match m in Angle.Matches(text))
            {
                raw.Add(Scalar(round, field, text, m, CandidateKind.Angle, Dbl(m.Groups["v"].Value), "deg", m.Groups["side"].Value));
            }

            foreach (Match m in Speed.Matches(text))
            {
                raw.Add(Scalar(round, field, text, m, CandidateKind.Speed, Dbl(m.Groups["v"].Value), "kn", null));
            }

            foreach (Match m in Duration.Matches(text))
            {
                raw.Add(Scalar(round, field, text, m, CandidateKind.Duration, Dbl(m.Groups["v"].Value), m.Groups["u"].Value == "小时" ? "h" : "min", null));
            }

            raw.Sort((a, b) => a.Span.Start != b.Span.Start ? a.Span.Start.CompareTo(b.Span.Start) : b.Span.Length.CompareTo(a.Span.Length));
            var kept = new List<ClaimCandidate>();
            int end = 0;
            foreach (var c in raw)
            {
                if (c.Span.Start >= end)
                {
                    kept.Add(c);
                    end = c.Span.Start + c.Span.Length;
                }
            }

            return kept;
        }

        private static ClaimCandidate TimeCandidate(int round, QaField field, string text, Match m, TimeSpan tod, CandidateOptions o)
        {
            var local = new DateTimeOffset(o.AnchorLocal.Date + tod, o.AnchorLocal.Offset);
            if (local > o.AnchorLocal + o.Lookahead)
            {
                local = local.AddDays(-1);
            }

            return new ClaimCandidate(new SourceSpan(round, field, m.Index, m.Length), m.Value, CandidateKind.Time, local.ToUniversalTime(), tod, null, null, null, IsHedged(text, m));
        }

        private static ClaimCandidate Scalar(int round, QaField field, string text, Match m, CandidateKind kind, double v, string unit, string side)
        {
            return new ClaimCandidate(new SourceSpan(round, field, m.Index, m.Length), m.Value, kind, null, null, v, unit, side, IsHedged(text, m));
        }

        private static bool IsHedged(string text, Match m)
        {
            string before = text.Substring(0, m.Index).TrimEnd();
            string after = text.Substring(m.Index + m.Length).TrimStart();
            foreach (string h in HedgeBefore)
            {
                if (before.EndsWith(h, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            foreach (string h in HedgeAfter)
            {
                if (after.StartsWith(h, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false;
        }

        private static int Int(string s) { return int.Parse(s, NumberStyles.None, CultureInfo.InvariantCulture); }

        private static double Dbl(string s) { return double.Parse(s, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture); }
    }
}
