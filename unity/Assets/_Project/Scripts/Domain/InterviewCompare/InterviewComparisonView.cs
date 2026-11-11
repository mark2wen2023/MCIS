using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using Mcis.Domain.Interview;

namespace Mcis.Domain.InterviewCompare
{
    public enum RosterStatus : byte
    {
        NotChecked = 0,
        Consistent = 1,
        Pending = 2,
        Contradictions = 3,
    }

    /// <summary>左侧受询问人列表的一行。矛盾数只计“已确认”的矛盾（合同：只有 Confirmed 才计入）。</summary>
    public sealed class RosterEntry
    {
        public string RecordId { get; internal set; }
        public string Name { get; internal set; }
        public string Role { get; internal set; }
        public string Affiliation { get; internal set; }
        public DateTimeOffset StartUtc { get; internal set; }
        public double? DurationMinutes { get; internal set; }
        public bool Signed { get; internal set; }
        public int StatementCount { get; internal set; }
        public int ConfirmedContradictions { get; internal set; }
        public int PendingCount { get; internal set; }
        public int UncheckedCount { get; internal set; }

        /// <summary>W5.1：比对结论已过期（陈述改版后未重新比对）的条数。</summary>
        public int StaleCount { get; internal set; }

        public RosterStatus Status { get; internal set; }
        public string Label { get; internal set; }

        /// <summary>如 “IR-03 · 05-19 09:30 · 68 min · 已签字”；时间按给定船时偏移显示。</summary>
        public string Subtitle(TimeSpan shipOffset)
        {
            string s = RecordId + " · " + StartUtc.ToOffset(shipOffset).ToString("MM-dd HH:mm", CultureInfo.InvariantCulture);
            if (DurationMinutes.HasValue)
            {
                s += " · " + Math.Round(DurationMinutes.Value).ToString(CultureInfo.InvariantCulture) + " min";
            }

            return Signed ? s + " · 已签字" : s;
        }
    }

    /// <summary>交叉比对表的一行（陈述 / 数据（来源） / 结论）。</summary>
    public sealed class ComparisonRow
    {
        public string StatementId { get; internal set; }
        public string Citation { get; internal set; }
        public string Summary { get; internal set; }
        public string Quote { get; internal set; }
        public StatementKind Kind { get; internal set; }
        public StatementReviewStatus ReviewStatus { get; internal set; }
        public CrossCheckOutcome? Outcome { get; internal set; }
        public CrossCheckState? State { get; internal set; }
        public string DataDisplay { get; internal set; }
        public double? Delta { get; internal set; }
        public string DeltaUnit { get; internal set; }
        public string Rule { get; internal set; }

        /// <summary>结论为矛盾且未被驳回（待确认或已确认），且未过期。</summary>
        public bool IsContradiction { get; internal set; }

        /// <summary>W5.1 D01：比对结论已过期（陈述改版后未重新比对），页面显示「需重新比对」。</summary>
        public bool IsStale { get; internal set; }

        /// <summary>比对时的陈述版本；未比对为 null。</summary>
        public int? StatementVersion { get; internal set; }

        /// <summary>陈述当前版本（Statement.Revision）。</summary>
        public int StatementRevision { get; internal set; }
    }

    public sealed class ComparisonSummary
    {
        public int StatementCount { get; internal set; }

        /// <summary>未驳回的矛盾（待确认 + 已确认），对应原型页眉 “7 条陈述 · 3 条矛盾”。</summary>
        public int ContradictionCount { get; internal set; }

        public int ConfirmedContradictionCount { get; internal set; }
        public int PendingCount { get; internal set; }
        public int UncheckedCount { get; internal set; }

        /// <summary>W5.1：过期结论条数。过期条目不计入矛盾数、已确认矛盾数和待确认数。</summary>
        public int StaleCount { get; internal set; }

        /// <summary>“7 条陈述 · 3 条矛盾”，有过期结论时追加 “ · N 条需重新比对”。</summary>
        public string HeaderText { get; internal set; }
    }

    /// <summary>时间轴上的一个点：陈述时刻 vs 数据时刻。</summary>
    public sealed class TimeChartPoint
    {
        public string StatementId { get; internal set; }
        public string Summary { get; internal set; }
        public DateTimeOffset StatementUtc { get; internal set; }

        /// <summary>仅时刻类陈述且已比对时有值 = 陈述时刻 − Δ。</summary>
        public DateTimeOffset? ObservedUtc { get; internal set; }

        public double? DeltaSeconds { get; internal set; }
        public CrossCheckOutcome? Outcome { get; internal set; }
        public string Note { get; internal set; }

        /// <summary>W5.1：结论过期时为 true，此时不给数据时刻与结论。</summary>
        public bool IsStale { get; internal set; }
    }

    public sealed class TimeChart
    {
        public IReadOnlyList<TimeChartPoint> Points { get; internal set; }

        /// <summary>全部时刻向下取整到整分；无点时为 null。</summary>
        public DateTimeOffset? AxisStartUtc { get; internal set; }

        /// <summary>全部时刻向上取整到整分；无点时为 null。</summary>
        public DateTimeOffset? AxisEndUtc { get; internal set; }
    }

    /// <summary>
    /// 询问笔录比对页（#interview）的页面视图模型，纯函数，只读 W3 的 InterviewRecord / CrossCheckRegister。
    /// 已驳回（Rejected）的陈述不出现；登记簿中属于其他笔录的同名条目忽略。
    /// </summary>
    public static class InterviewComparisonView
    {
        public static IReadOnlyList<ComparisonRow> Rows(InterviewRecord record, CrossCheckRegister register)
        {
            var rows = new List<ComparisonRow>();
            if (record == null)
            {
                return new ReadOnlyCollection<ComparisonRow>(rows);
            }

            foreach (Statement s in Visible(record))
            {
                CrossCheckEntry e = EntryOf(record, register, s.StatementId);
                bool stale = e != null && e.IsStale(record);
                rows.Add(new ComparisonRow
                {
                    StatementId = s.StatementId,
                    Citation = record.RecordId + " 第 " + s.Span.Round.ToString(CultureInfo.InvariantCulture) + " 问",
                    Summary = s.Summary,
                    Quote = s.Quote,
                    Kind = s.Kind,
                    ReviewStatus = s.ReviewStatus,
                    Outcome = e?.Result.Outcome,
                    State = e?.State,
                    DataDisplay = e == null ? string.Empty : DataText(e.Result),
                    Delta = e?.Result.Delta,
                    DeltaUnit = e == null ? string.Empty : e.Result.DeltaUnit,
                    Rule = e == null ? string.Empty : e.Result.Rule,
                    IsContradiction = !stale && IsLiveContradiction(e),
                    IsStale = stale,
                    StatementVersion = e?.StatementVersion,
                    StatementRevision = s.Revision,
                });
            }

            return new ReadOnlyCollection<ComparisonRow>(rows);
        }

        public static ComparisonSummary Summarize(InterviewRecord record, CrossCheckRegister register)
        {
            var sum = new ComparisonSummary();
            if (record != null)
            {
                foreach (Statement s in Visible(record))
                {
                    CrossCheckEntry e = EntryOf(record, register, s.StatementId);
                    sum.StatementCount++;
                    if (e == null)
                    {
                        sum.UncheckedCount++;
                        continue;
                    }

                    if (e.IsStale(record))
                    {
                        sum.StaleCount++;
                        continue;
                    }

                    if (IsLiveContradiction(e))
                    {
                        sum.ContradictionCount++;
                    }

                    if (e.IsEffective && e.Result.Outcome == CrossCheckOutcome.Contradictory)
                    {
                        sum.ConfirmedContradictionCount++;
                    }

                    if (e.State == CrossCheckState.PendingConfirmation)
                    {
                        sum.PendingCount++;
                    }
                }
            }

            sum.HeaderText = sum.StatementCount.ToString(CultureInfo.InvariantCulture) + " 条陈述 · " + sum.ContradictionCount.ToString(CultureInfo.InvariantCulture) + " 条矛盾"
                + (sum.StaleCount > 0 ? " · " + StaleText(sum.StaleCount) : string.Empty);
            return sum;
        }

        public static RosterEntry Roster(InterviewRecord record, CrossCheckRegister register)
        {
            if (record == null)
            {
                throw new ArgumentNullException(nameof(record));
            }

            ComparisonSummary s = Summarize(record, register);
            var r = new RosterEntry
            {
                RecordId = record.RecordId,
                Name = record.Interviewee.Name,
                Role = record.Interviewee.Role,
                Affiliation = record.Interviewee.Affiliation,
                StartUtc = record.StartUtc,
                DurationMinutes = record.DurationMinutes,
                Signed = record.Signed,
                StatementCount = s.StatementCount,
                ConfirmedContradictions = s.ConfirmedContradictionCount,
                PendingCount = s.PendingCount,
                UncheckedCount = s.UncheckedCount,
                StaleCount = s.StaleCount,
            };
            string open = (s.PendingCount > 0 ? " · " + s.PendingCount.ToString(CultureInfo.InvariantCulture) + " 条待确认" : string.Empty)
                + (s.StaleCount > 0 ? " · " + StaleText(s.StaleCount) : string.Empty);
            if (s.ConfirmedContradictionCount > 0)
            {
                r.Status = RosterStatus.Contradictions;
                r.Label = s.ConfirmedContradictionCount.ToString(CultureInfo.InvariantCulture) + " 处矛盾" + open;
            }
            else if (open.Length > 0)
            {
                r.Status = RosterStatus.Pending;
                r.Label = open.Substring(3);
            }
            else if (s.StatementCount > s.UncheckedCount)
            {
                r.Status = RosterStatus.Consistent;
                r.Label = s.UncheckedCount > 0 ? "一致 · " + s.UncheckedCount.ToString(CultureInfo.InvariantCulture) + " 条未比对" : "一致";
            }
            else
            {
                r.Status = RosterStatus.NotChecked;
                r.Label = "未比对";
            }

            return r;
        }

        public static IReadOnlyList<RosterEntry> Roster(IEnumerable<InterviewRecord> records, CrossCheckRegister register)
        {
            var list = new List<RosterEntry>();
            if (records != null)
            {
                foreach (InterviewRecord r in records)
                {
                    if (r != null)
                    {
                        list.Add(Roster(r, register));
                    }
                }
            }

            return new ReadOnlyCollection<RosterEntry>(list);
        }

        public static TimeChart Chart(InterviewRecord record, CrossCheckRegister register)
        {
            var pts = new List<TimeChartPoint>();
            if (record != null)
            {
                foreach (Statement s in Visible(record))
                {
                    DateTimeOffset? at = s.Claim.ValueType == ClaimValueType.EventTime ? s.Claim.Time : s.ReferenceUtc;
                    if (!at.HasValue)
                    {
                        continue;
                    }

                    CrossCheckEntry e = EntryOf(record, register, s.StatementId);
                    var p = new TimeChartPoint { StatementId = s.StatementId, Summary = s.Summary, StatementUtc = at.Value };
                    if (e == null)
                    {
                        p.Note = "未比对";
                    }
                    else if (e.IsStale(record))
                    {
                        p.IsStale = true;
                        p.Note = StaleLabel;
                    }
                    else
                    {
                        p.Outcome = e.Result.Outcome;
                        p.Note = DataText(e.Result);
                        if (s.Claim.ValueType == ClaimValueType.EventTime && e.Result.Delta.HasValue && e.Result.DeltaUnit == "s")
                        {
                            p.DeltaSeconds = e.Result.Delta;
                            p.ObservedUtc = at.Value.AddSeconds(-e.Result.Delta.Value);
                        }
                    }

                    pts.Add(p);
                }
            }

            // 稳定排序：同一时刻保持陈述顺序。
            var ordered = new List<TimeChartPoint>();
            var idx = new List<KeyValuePair<int, TimeChartPoint>>();
            for (int i = 0; i < pts.Count; i++)
            {
                idx.Add(new KeyValuePair<int, TimeChartPoint>(i, pts[i]));
            }

            idx.Sort((a, b) =>
            {
                int c = a.Value.StatementUtc.CompareTo(b.Value.StatementUtc);
                return c != 0 ? c : a.Key.CompareTo(b.Key);
            });
            DateTimeOffset? lo = null, hi = null;
            foreach (var kv in idx)
            {
                ordered.Add(kv.Value);
                foreach (DateTimeOffset? t in new[] { (DateTimeOffset?)kv.Value.StatementUtc, kv.Value.ObservedUtc })
                {
                    if (t.HasValue)
                    {
                        lo = !lo.HasValue || t.Value < lo.Value ? t : lo;
                        hi = !hi.HasValue || t.Value > hi.Value ? t : hi;
                    }
                }
            }

            return new TimeChart
            {
                Points = new ReadOnlyCollection<TimeChartPoint>(ordered),
                AxisStartUtc = lo.HasValue ? FloorMinute(lo.Value) : (DateTimeOffset?)null,
                AxisEndUtc = hi.HasValue ? CeilMinute(hi.Value) : (DateTimeOffset?)null,
            };
        }

        internal static IEnumerable<Statement> Visible(InterviewRecord record)
        {
            foreach (Statement s in record.Statements)
            {
                if (s.ReviewStatus != StatementReviewStatus.Rejected)
                {
                    yield return s;
                }
            }
        }

        internal static CrossCheckEntry EntryOf(InterviewRecord record, CrossCheckRegister register, string statementId)
        {
            CrossCheckEntry e = register?.Get(statementId);
            return e != null && e.Result.RecordId == record.RecordId ? e : null;
        }

        /// <summary>W5.1：过期结论在页面上的标签。</summary>
        public const string StaleLabel = "需重新比对";

        private static string StaleText(int n)
        {
            return n.ToString(CultureInfo.InvariantCulture) + " 条" + StaleLabel;
        }

        private static bool IsLiveContradiction(CrossCheckEntry e)
        {
            return e != null && e.Result.Outcome == CrossCheckOutcome.Contradictory && e.State != CrossCheckState.Dismissed;
        }

        private static string DataText(CrossCheckResult r)
        {
            return r.SourceLabel.Length == 0 ? r.ObservedText : r.ObservedText + " (" + r.SourceLabel + ")";
        }

        private static DateTimeOffset FloorMinute(DateTimeOffset t)
        {
            return new DateTimeOffset(t.Ticks - t.Ticks % TimeSpan.TicksPerMinute, t.Offset);
        }

        private static DateTimeOffset CeilMinute(DateTimeOffset t)
        {
            long rem = t.Ticks % TimeSpan.TicksPerMinute;
            return rem == 0 ? t : new DateTimeOffset(t.Ticks - rem + TimeSpan.TicksPerMinute, t.Offset);
        }
    }
}
