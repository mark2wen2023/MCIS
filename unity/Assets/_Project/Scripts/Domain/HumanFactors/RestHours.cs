using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Mcis.Core;

namespace Mcis.Domain.HumanFactors
{
    /// <summary>时段种类：工作 / 休息。未标注的时间既不算工作也不算休息（Unknown）。</summary>
    public enum DutyKind
    {
        Work = 0,
        Rest = 1
    }

    /// <summary>B5：工作细分（原型 13 工休图：值班 / 其他工作如装卸、演习 / 休息）。</summary>
    public enum WorkKind
    {
        /// <summary>值班（DutyKind.Work 的默认细分）。</summary>
        Watch = 0,

        /// <summary>其他工作（装卸、演习等）。</summary>
        OtherWork = 1,

        /// <summary>休息。</summary>
        Rest = 2
    }

    /// <summary>一段连续的同种值班/休息时间，半开区间 [Start, End)。</summary>
    public readonly struct DutyInterval
    {
        public DateTimeOffset Start { get; }
        public DateTimeOffset End { get; }
        public DutyKind Kind { get; }

        /// <summary>B5：工作细分；用 DutyKind 构造时 Work → Watch、Rest → Rest。</summary>
        public WorkKind WorkKind { get; }

        public DutyInterval(DateTimeOffset start, DateTimeOffset end, DutyKind kind)
        {
            Start = start;
            End = end;
            Kind = kind;
            WorkKind = kind == DutyKind.Rest ? WorkKind.Rest : WorkKind.Watch;
        }

        public DutyInterval(DateTimeOffset start, DateTimeOffset end, WorkKind workKind)
        {
            Start = start;
            End = end;
            Kind = workKind == WorkKind.Rest ? DutyKind.Rest : DutyKind.Work;
            WorkKind = workKind;
        }

        public override string ToString()
        {
            return (Kind == DutyKind.Work && WorkKind == WorkKind.OtherWork ? "OtherWork" : Kind.ToString()) + " " + Start.UtcDateTime.ToString("yyyy-MM-dd HH:mm 'UTC'", System.Globalization.CultureInfo.InvariantCulture) + " ~ " + End.UtcDateTime.ToString("yyyy-MM-dd HH:mm 'UTC'", System.Globalization.CultureInfo.InvariantCulture);
        }
    }

    /// <summary>
    /// 值班/休息记录窗口。记录内未标注的时段为 Unknown，既不计工作也不计休息。
    /// 所有时长按 UTC 瞬时（绝对时刻）计算，与船时调整、夏令时无关。
    /// </summary>
    public sealed class WorkRestSchedule
    {
        public const string ErrInvalidRecord = "hf_invalid_record";
        public const string ErrEmptyInput = "hf_empty_input";
        public const string ErrInvalidInterval = "hf_invalid_interval";
        public const string ErrOutsideRecord = "hf_outside_record";
        public const string ErrOverlap = "hf_overlap";
        public const string ErrInvalidOffset = "hf_invalid_offset";
        public const string ErrInvalidKind = "hf_invalid_kind";

        private readonly List<DutyInterval> _work;
        private readonly List<DutyInterval> _rest;

        public DateTimeOffset RecordStart { get; }
        public DateTimeOffset RecordEnd { get; }

        private WorkRestSchedule(DateTimeOffset recordStart, DateTimeOffset recordEnd, List<DutyInterval> work, List<DutyInterval> rest)
        {
            RecordStart = recordStart;
            RecordEnd = recordEnd;
            _work = work;
            _rest = rest;
        }

        /// <summary>合并、排序后的工作时段（只合并同一 WorkKind 的相邻段，值班与其他工作不跨类合并）。</summary>
        public IReadOnlyList<DutyInterval> WorkPeriods { get { return _work; } }

        /// <summary>合并、排序后的休息时段。</summary>
        public IReadOnlyList<DutyInterval> RestPeriods { get { return _rest; } }

        /// <summary>直接标注时段创建。未覆盖时间 = Unknown。</summary>
        public static Result<WorkRestSchedule> Create(DateTimeOffset recordStart, DateTimeOffset recordEnd, IEnumerable<DutyInterval> intervals)
        {
            if (recordEnd <= recordStart)
            {
                return Result<WorkRestSchedule>.Fail(ErrInvalidRecord, "记录窗口无效：recordEnd 必须晚于 recordStart");
            }

            if (intervals == null)
            {
                return Result<WorkRestSchedule>.Fail(ErrEmptyInput, "intervals 为空");
            }

            List<DutyInterval> list = intervals.ToList();
            if (list.Count == 0)
            {
                return Result<WorkRestSchedule>.Fail(ErrEmptyInput, "intervals 不能为空");
            }

            for (int i = 0; i < list.Count; i++)
            {
                DutyInterval d = list[i];
                if (d.End <= d.Start)
                {
                    return Result<WorkRestSchedule>.Fail(ErrInvalidInterval, "时段无效（end<=start）：" + d);
                }

                if (!Enum.IsDefined(typeof(DutyKind), d.Kind) || !Enum.IsDefined(typeof(WorkKind), d.WorkKind))
                {
                    return Result<WorkRestSchedule>.Fail(ErrInvalidKind, "未知时段种类：" + d);
                }

                if (d.Start < recordStart || d.End > recordEnd)
                {
                    return Result<WorkRestSchedule>.Fail(ErrOutsideRecord, "时段超出记录窗口：" + d);
                }
            }

            // 任意两个时段（无论种类）重叠即非法；首尾相接（end==start）不算重叠。
            var sorted = list.OrderBy(x => x.Start.UtcDateTime).ThenBy(x => x.End.UtcDateTime).ToList();
            string overlap = FindOverlap(sorted);
            if (overlap != null)
            {
                return Result<WorkRestSchedule>.Fail(ErrOverlap, overlap);
            }

            return Result<WorkRestSchedule>.Ok(new WorkRestSchedule(
                recordStart,
                recordEnd,
                MergeKind(sorted, DutyKind.Work),
                MergeKind(sorted, DutyKind.Rest)));
        }

        /// <summary>只给工作时段，其余自动填为休息（补集）。</summary>
        public static Result<WorkRestSchedule> FromWork(DateTimeOffset recordStart, DateTimeOffset recordEnd, IEnumerable<(DateTimeOffset Start, DateTimeOffset End)> work)
        {
            return FromKind(recordStart, recordEnd, work, DutyKind.Work);
        }

        /// <summary>只给休息时段，其余自动填为工作（补集）。</summary>
        public static Result<WorkRestSchedule> FromRest(DateTimeOffset recordStart, DateTimeOffset recordEnd, IEnumerable<(DateTimeOffset Start, DateTimeOffset End)> rest)
        {
            return FromKind(recordStart, recordEnd, rest, DutyKind.Rest);
        }

        private static Result<WorkRestSchedule> FromKind(DateTimeOffset recordStart, DateTimeOffset recordEnd, IEnumerable<(DateTimeOffset Start, DateTimeOffset End)> given, DutyKind kind)
        {
            if (recordEnd <= recordStart)
            {
                return Result<WorkRestSchedule>.Fail(ErrInvalidRecord, "记录窗口无效：recordEnd 必须晚于 recordStart");
            }

            if (given == null)
            {
                return Result<WorkRestSchedule>.Fail(ErrEmptyInput, "输入为空");
            }

            var list = given.Select(p => new DutyInterval(p.Start, p.End, kind)).ToList();
            if (list.Count == 0)
            {
                return Result<WorkRestSchedule>.Fail(ErrEmptyInput, "输入不能为空");
            }

            // 补集策略：给定时段排序合并后，记录窗口内的空隙补为另一类。
            // 给定时段仍必须在记录窗口内（手工校验，与 Create 一致）。
            var sorted = list.OrderBy(x => x.Start.UtcDateTime).ToList();

            for (int i = 0; i < list.Count; i++)
            {
                DutyInterval d = list[i];
                if (d.End <= d.Start)
                {
                    return Result<WorkRestSchedule>.Fail(ErrInvalidInterval, "时段无效（end<=start）：" + d);
                }

                if (d.Start < recordStart || d.End > recordEnd)
                {
                    return Result<WorkRestSchedule>.Fail(ErrOutsideRecord, "时段超出记录窗口：" + d);
                }
            }

            string overlap = FindOverlap(sorted);
            if (overlap != null)
            {
                return Result<WorkRestSchedule>.Fail(ErrOverlap, overlap);
            }

            var merged = MergeKind(sorted, kind);
            var complement = new List<DutyInterval>();
            DutyKind other = kind == DutyKind.Work ? DutyKind.Rest : DutyKind.Work;
            DateTimeOffset cur = recordStart;
            for (int i = 0; i < merged.Count; i++)
            {
                if (merged[i].Start > cur)
                {
                    complement.Add(new DutyInterval(cur, merged[i].Start, other));
                }

                if (merged[i].End > cur)
                {
                    cur = merged[i].End;
                }
            }

            if (cur < recordEnd)
            {
                complement.Add(new DutyInterval(cur, recordEnd, other));
            }

            var both = new List<DutyInterval>();
            both.AddRange(merged);
            both.AddRange(complement);
            both = both.OrderBy(x => x.Start.UtcDateTime).ToList();
            var work = kind == DutyKind.Work ? merged : MergeKind(both, DutyKind.Work);
            var rest = kind == DutyKind.Rest ? merged : MergeKind(both, DutyKind.Rest);
            return Result<WorkRestSchedule>.Ok(new WorkRestSchedule(recordStart, recordEnd, work, rest));
        }

        /// <summary>已按起点排序的时段中，任一段与此前任一段重叠（首尾相接不算）→ 返回描述；否则 null。</summary>
        private static string FindOverlap(List<DutyInterval> sorted)
        {
            int maxIdx = -1;
            for (int i = 0; i < sorted.Count; i++)
            {
                if (maxIdx >= 0 && sorted[i].Start < sorted[maxIdx].End)
                {
                    return "时段重叠：" + sorted[maxIdx] + " 与 " + sorted[i];
                }

                if (maxIdx < 0 || sorted[i].End > sorted[maxIdx].End)
                {
                    maxIdx = i;
                }
            }

            return null;
        }

        /// <summary>合并相邻（首尾相接）的同种类时段（工作段只合并同一 WorkKind），并按时间排序。</summary>
        private static List<DutyInterval> MergeKind(List<DutyInterval> sortedAll, DutyKind kind)
        {
            var selected = sortedAll.Where(x => x.Kind == kind).ToList();
            var merged = new List<DutyInterval>();
            for (int i = 0; i < selected.Count; i++)
            {
                DutyInterval d = selected[i];
                DutyInterval last = merged.Count > 0 ? merged[merged.Count - 1] : default(DutyInterval);
                if (merged.Count > 0 && d.Start <= last.End && d.WorkKind == last.WorkKind)
                {
                    if (d.End > last.End)
                    {
                        merged[merged.Count - 1] = new DutyInterval(last.Start, d.End, last.WorkKind);
                    }
                }
                else
                {
                    merged.Add(new DutyInterval(d.Start, d.End, d.WorkKind));
                }
            }

            return merged;
        }

        /// <summary>记录窗口内未标注（Unknown）的时段，按时间排序。</summary>
        public IReadOnlyList<(DateTimeOffset Start, DateTimeOffset End)> UnknownPeriods()
        {
            var all = _work.Concat(_rest).OrderBy(x => x.Start.UtcDateTime).ToList();
            var gaps = new List<(DateTimeOffset, DateTimeOffset)>();
            DateTimeOffset cur = RecordStart;
            foreach (DutyInterval d in all)
            {
                if (d.Start > cur)
                {
                    gaps.Add((cur, d.Start));
                }

                if (d.End > cur)
                {
                    cur = d.End;
                }
            }

            if (cur < RecordEnd)
            {
                gaps.Add((cur, RecordEnd));
            }

            return gaps;
        }

        /// <summary>
        /// B5：按船时日历日（shipOffset，整分钟、±14h）统计每日休息/值班/其他工作/未标注时长。
        /// 首尾两天若只部分落在记录内，IsPartialDay=true，Covered 为记录内时长。时长按 UTC 瞬时计。
        /// </summary>
        public Result<IReadOnlyList<DailyDutyTotal>> DailyTotals(TimeSpan shipOffset)
        {
            if (shipOffset > TimeSpan.FromHours(14) || shipOffset < TimeSpan.FromHours(-14) || shipOffset.Ticks % TimeSpan.TicksPerMinute != 0)
            {
                return Result<IReadOnlyList<DailyDutyTotal>>.Fail(ErrInvalidOffset, "船时偏移须为整分钟且在 ±14h 内：" + shipOffset);
            }

            var unknown = UnknownPeriods().Select(u => new DutyInterval(u.Start, u.End, DutyKind.Work)).ToList();
            var list = new List<DailyDutyTotal>();
            DateTime day = RecordStart.ToOffset(shipOffset).Date;
            while (true)
            {
                var dayStart = new DateTimeOffset(day, shipOffset);
                DateTimeOffset dayEnd = dayStart.AddDays(1);
                if (dayStart >= RecordEnd)
                {
                    break;
                }

                DateTimeOffset from = dayStart > RecordStart ? dayStart : RecordStart;
                DateTimeOffset to = dayEnd < RecordEnd ? dayEnd : RecordEnd;
                list.Add(new DailyDutyTotal(
                    day,
                    from,
                    to,
                    Sum(_rest, from, to),
                    Sum(_work.Where(w => w.WorkKind != WorkKind.OtherWork).ToList(), from, to),
                    Sum(_work.Where(w => w.WorkKind == WorkKind.OtherWork).ToList(), from, to),
                    Sum(unknown, from, to),
                    from > dayStart || to < dayEnd));
                day = day.AddDays(1);
            }

            return Result<IReadOnlyList<DailyDutyTotal>>.Ok(list);
        }

        private static TimeSpan Sum(IReadOnlyList<DutyInterval> periods, DateTimeOffset from, DateTimeOffset to)
        {
            TimeSpan sum = TimeSpan.Zero;
            foreach (DutyInterval p in periods)
            {
                DateTimeOffset lo = p.Start > from ? p.Start : from;
                DateTimeOffset hi = p.End < to ? p.End : to;
                if (hi > lo)
                {
                    sum += hi - lo;
                }
            }

            return sum;
        }
    }

    /// <summary>B5：一个船时日历日的工休合计。</summary>
    public sealed class DailyDutyTotal
    {
        /// <summary>船时日期（Kind=Unspecified）。</summary>
        public DateTime LocalDate { get; }

        /// <summary>该日落在记录内的起止（UTC 瞬时）。</summary>
        public DateTimeOffset From { get; }
        public DateTimeOffset To { get; }

        public TimeSpan Rest { get; }
        public TimeSpan Watch { get; }
        public TimeSpan OtherWork { get; }
        public TimeSpan Unknown { get; }

        /// <summary>该日在记录内的时长（= Rest + Watch + OtherWork + Unknown）。</summary>
        public TimeSpan Covered { get { return To - From; } }

        /// <summary>该日只部分落在记录内（记录首/末日）。</summary>
        public bool IsPartialDay { get; }

        public DailyDutyTotal(DateTime localDate, DateTimeOffset from, DateTimeOffset to, TimeSpan rest, TimeSpan watch, TimeSpan otherWork, TimeSpan unknown, bool isPartialDay)
        {
            LocalDate = localDate;
            From = from;
            To = to;
            Rest = rest;
            Watch = watch;
            OtherWork = otherWork;
            Unknown = unknown;
            IsPartialDay = isPartialDay;
        }
    }

    /// <summary>
    /// 工休标准阈值（可配置）。默认值即公约值；条款出处：
    /// STCW A-VIII/1 与 MLC 2006 标准 A2.3。
    /// </summary>
    public sealed class RestHourRules
    {
        public const string ErrInvalidRules = "hf_invalid_rules";

        /// <summary>任何 24h 内最低休息 10h。（STCW A-VIII/1 §2.1；MLC A2.3 §5(b)(i)）</summary>
        public TimeSpan MinRestPer24h { get; set; }

        /// <summary>任何 7 天内最低休息 77h。（STCW A-VIII/1 §2.2；MLC A2.3 §5(b)(ii)）</summary>
        public TimeSpan MinRestPer7d { get; set; }

        /// <summary>任何 24h 内休息段最多 2 段。（STCW A-VIII/1 §3；MLC A2.3 §6）</summary>
        public int MaxRestPeriodsPer24h { get; set; }

        /// <summary>任一休息段最短 6h。（STCW A-VIII/1 §3；MLC A2.3 §6）</summary>
        public TimeSpan MinLongestRestPeriod { get; set; }

        /// <summary>相邻两个休息段之间的间隔最长 14h。（STCW A-VIII/1 §3；MLC A2.3 §6）</summary>
        public TimeSpan MaxIntervalBetweenRest { get; set; }

        /// <summary>任何 24h 内最长工作 14h。（MLC A2.3 §5(a)(i)；STCW §2 的对偶表述）</summary>
        public TimeSpan MaxWorkPer24h { get; set; }

        /// <summary>任何 7 天内最长工作 72h。（MLC A2.3 §5(a)(ii)）</summary>
        public TimeSpan MaxWorkPer7d { get; set; }

        /// <summary>
        /// 是否同时校验 MLC 工作时长上限（Work24h/Work7d）。MLC A2.3 §5 规定成员国在“最长工作时间”(a)
        /// 与“最短休息时间”(b) 中择一立法；STCW A-VIII/1 只规定休息。默认 true（同时校验，便于调查列出全部超限）；
        /// 用 FromRest/FromWork 补集记录时，满足 77h 休息的排班必然对应 91h 工作，会同时触发 Work7d——
        /// 按船旗国采用的体系可关闭。
        /// </summary>
        public bool ApplyWorkHourLimits { get; set; }

        public RestHourRules()
        {
            ApplyWorkHourLimits = true;
            MinRestPer24h = TimeSpan.FromHours(10);
            MinRestPer7d = TimeSpan.FromHours(77);
            MaxRestPeriodsPer24h = 2;
            MinLongestRestPeriod = TimeSpan.FromHours(6);
            MaxIntervalBetweenRest = TimeSpan.FromHours(14);
            MaxWorkPer24h = TimeSpan.FromHours(14);
            MaxWorkPer7d = TimeSpan.FromHours(72);
        }

        /// <summary>非法（任一阈值为负或 0、6h 大于 10h 等）→ hf_invalid_rules。</summary>
        public Result<bool> Validate()
        {
            if (MinRestPer24h <= TimeSpan.Zero || MinRestPer7d <= TimeSpan.Zero ||
                MinLongestRestPeriod <= TimeSpan.Zero || MaxIntervalBetweenRest <= TimeSpan.Zero ||
                MaxWorkPer24h <= TimeSpan.Zero || MaxWorkPer7d <= TimeSpan.Zero)
            {
                return Result<bool>.Fail(ErrInvalidRules, "阈值必须为正");
            }

            if (MaxRestPeriodsPer24h < 1)
            {
                return Result<bool>.Fail(ErrInvalidRules, "MaxRestPeriodsPer24h 必须 >= 1");
            }

            if (MinLongestRestPeriod > MinRestPer24h)
            {
                return Result<bool>.Fail(ErrInvalidRules, "MinLongestRestPeriod 不能大于 MinRestPer24h");
            }

            if (MaxWorkPer24h >= TimeSpan.FromHours(24) || MaxWorkPer7d >= TimeSpan.FromDays(7) || MinRestPer24h > TimeSpan.FromHours(24) || MinRestPer7d > TimeSpan.FromDays(7))
            {
                return Result<bool>.Fail(ErrInvalidRules, "阈值超出对应窗口长度");
            }

            return Result<bool>.Ok(true);
        }
    }

    /// <summary>触犯的具体工休规则。</summary>
    public enum RestRule
    {
        /// <summary>任何 24h 内休息 ≥ 10h。</summary>
        Rest24h = 0,

        /// <summary>任何 7 天内休息 ≥ 77h。</summary>
        Rest7d = 1,

        /// <summary>任何 24h 内休息 ≤ 2 段且最长段 ≥ 6h（拆分约束；总休息足够但两段凑不够时报）。</summary>
        RestSplit = 2,

        /// <summary>任一休息段 ≥ 6h。</summary>
        LongestRest = 3,

        /// <summary>相邻休息段之间的间隔 ≤ 14h。</summary>
        RestInterval = 4,

        /// <summary>任何 24h 内工作 ≤ 14h。</summary>
        Work24h = 5,

        /// <summary>任何 7 天内工作 ≤ 72h。</summary>
        Work7d = 6
    }

    /// <summary>一条工休违规。</summary>
    public sealed class RestHourViolation
    {
        public RestRule Rule { get; }
        public DateTimeOffset WindowStart { get; }
        public DateTimeOffset WindowEnd { get; }
        public TimeSpan Actual { get; }
        public TimeSpan Limit { get; }

        /// <summary>
        /// 违规窗口起点的范围。滚动窗口（总量规则）：端点处累计量恰等于限值（本身合规，开区间），
        /// 但若端点是记录首/末可评估起点则为闭端点；拆分规则（RestSplit/LongestRest）：一组相邻违规对齐窗口的首/末起点（闭）；
        /// RestInterval：两者相等。
        /// </summary>
        public DateTimeOffset ViolatingFrom { get; }
        public DateTimeOffset ViolatingTo { get; }

        /// <summary>条款出处，如 "STCW A-VIII/1 §2.1 / MLC A2.3 §5(b)(i)"。</summary>
        public string Clause { get; }

        /// <summary>人读的细节描述。</summary>
        public string Detail { get; }

        public RestHourViolation(
            RestRule rule,
            DateTimeOffset windowStart,
            DateTimeOffset windowEnd,
            TimeSpan actual,
            TimeSpan limit,
            DateTimeOffset violatingFrom,
            DateTimeOffset violatingTo,
            string clause,
            string detail)
        {
            Rule = rule;
            WindowStart = windowStart;
            WindowEnd = windowEnd;
            Actual = actual;
            Limit = limit;
            ViolatingFrom = violatingFrom;
            ViolatingTo = violatingTo;
            Clause = clause ?? string.Empty;
            Detail = detail ?? string.Empty;
        }
    }

    /// <summary>工休校验的判定口径（W18.1 复裁，Gemini bot 2026-11-11 21:25；依据 STCW A-VIII/1 与 MLC 2006 标准 A2.3 的通行解释）。</summary>
    public static class RestHourAssumptions
    {
        /// <summary>总量规则口径。</summary>
        public const string TotalRuleStrictAnyWindow =
            "总量规则：任意 24h 内休息不少于 10h、任意 7d 内不少于 77h（工作上限同理），按严格的任意窗口判定，窗口截断的休息按窗口内长度计。";

        /// <summary>拆分规则口径（裁定原文要求写明“拆分规则按完整休息段判定，不是严格的任意窗口”）。</summary>
        public const string SplitRuleByFullSegment =
            "拆分规则按完整休息段判定，不是严格的任意窗口：休息至多分成两段，其中一段不少于 6h；只在休息段起止点对齐的 24h 窗口上评估，与窗口相交的休息段按全长计，不按窗口截断。因此每天 6h+4h、每天连续 10h 均判合规。";

        /// <summary>间隔规则口径。</summary>
        public const string IntervalRule = "间隔规则：相邻两段休息之间的间隔不超过 14h（按完整休息段的终点到下一段起点）。";

        /// <summary>未标注与记录边界。</summary>
        public const string UnknownAndRecordEdges =
            "未标注时段与被记录首尾截断的休息段：结论取决于它们时列为“数据不足”（乐观视图仍违规才列为违规）。";

        /// <summary>W18.2：记录边界额外候选窗口及不确定性披露。</summary>
        public const string SplitRecordEdges =
            "拆分规则另评估记录首窗口和记录尾−24h 窗口；被记录边界截断的休息段按可见长度计，并标注数据不足。";

        public static List<string> CreateDefaultList()
        {
            return new List<string> { TotalRuleStrictAnyWindow, SplitRuleByFullSegment, IntervalRule, UnknownAndRecordEdges, SplitRecordEdges };
        }
    }

    /// <summary>
    /// 工休校验报告。B2：Violations = 把 Unknown 全当休息（工作规则则全当非工作）仍违规；
    /// InsufficientData = 结论取决于 Unknown（或被记录边界截断的休息段）的窗口。
    /// </summary>
    public sealed class RestHourReport
    {
        public IReadOnlyList<RestHourViolation> Violations { get; }

        /// <summary>B2：数据不足（Unknown 决定结论）的条目；Actual 为把 Unknown 计为不利一方时的值。</summary>
        public IReadOnlyList<RestHourViolation> InsufficientData { get; }

        /// <summary>确定合规：既无违规也无数据不足。</summary>
        public bool IsCompliant { get { return Violations.Count == 0 && InsufficientData.Count == 0; } }

        /// <summary>有确定违规。</summary>
        public bool HasViolations { get { return Violations.Count > 0; } }

        /// <summary>结论不依赖 Unknown（无数据不足条目）。</summary>
        public bool IsConclusive { get { return InsufficientData.Count == 0; } }

        /// <summary>记录窗口内休息/工作/未标注总时长（按 UTC 瞬时）。</summary>
        public TimeSpan TotalRest { get; }
        public TimeSpan TotalWork { get; }
        public TimeSpan TotalUnknown { get; }

        /// <summary>判定口径说明（只读，见 <see cref="RestHourAssumptions"/>）；报告与页面说明须原样展示。</summary>
        public IReadOnlyList<string> Assumptions { get; } = RestHourAssumptions.CreateDefaultList().AsReadOnly();

        public RestHourReport(IReadOnlyList<RestHourViolation> violations, TimeSpan totalRest, TimeSpan totalWork, TimeSpan totalUnknown)
        {
            Violations = violations ?? new RestHourViolation[0];
            InsufficientData = new RestHourViolation[0];
            TotalRest = totalRest;
            TotalWork = totalWork;
            TotalUnknown = totalUnknown;
        }

        public RestHourReport(IReadOnlyList<RestHourViolation> violations, IReadOnlyList<RestHourViolation> insufficientData, TimeSpan totalRest, TimeSpan totalWork, TimeSpan totalUnknown)
            : this(violations, totalRest, totalWork, totalUnknown)
        {
            InsufficientData = insufficientData ?? new RestHourViolation[0];
        }
    }

    /// <summary>
    /// 按 STCW A-VIII/1 与 MLC 2006 标准 A2.3 校验 <see cref="WorkRestSchedule"/>。
    /// 滚动窗口评估不用固定步长：窗口内累计量随窗口起点 t 分段线性，极值只出现在 t 或 t+L
    /// 落在时段边界处，因此候选起点取每个边界 b 的 {b, b−L} ∪ {recordStart, recordEnd−L}，
    /// 相邻候选点之间线性，把连续违规的候选点归组输出一条违规（总量规则）。拆分规则按完整休息段、只在对齐窗口上判定，见 <see cref="RestHourAssumptions"/>。
    /// B2：分别在“乐观视图”（Unknown 计为休息、不计工作）与“悲观视图”（Unknown 计为工作、不计休息；
    /// 被记录首尾截断的休息段按观测长度）上评估：乐观视图仍违规 → Violation；仅悲观视图违规 → InsufficientData。
    /// </summary>
    public sealed class RestHourChecker
    {
        private readonly RestHourRules _rules;

        /// <summary>一次评估所用的视图：记录窗口 + 休息段（已合并）+ 工作段；Optimistic 时触及记录首尾的休息段视为可能更长。</summary>
        private sealed class View
        {
            public DateTimeOffset RecordStart;
            public DateTimeOffset RecordEnd;
            public List<DutyInterval> Rest;
            public List<DutyInterval> Work;
            public bool Optimistic;
        }

        public RestHourChecker(RestHourRules rules = null)
        {
            _rules = rules ?? new RestHourRules();
        }

        public Result<RestHourReport> Check(WorkRestSchedule s)
        {
            if (s == null)
            {
                return Result<RestHourReport>.Fail(WorkRestSchedule.ErrEmptyInput, "schedule 为空");
            }

            Result<bool> rulesOk = _rules.Validate();
            if (!rulesOk.IsSuccess)
            {
                return Result<RestHourReport>.Fail(rulesOk.ErrorCode, rulesOk.ErrorMessage);
            }

            var unknown = s.UnknownPeriods().Select(u => new DutyInterval(u.Start, u.End, DutyKind.Rest)).ToList();
            var optimistic = new View
            {
                RecordStart = s.RecordStart,
                RecordEnd = s.RecordEnd,
                Rest = MergeAll(s.RestPeriods.Concat(unknown)),
                Work = s.WorkPeriods.ToList(),
                Optimistic = true
            };
            var pessimistic = new View
            {
                RecordStart = s.RecordStart,
                RecordEnd = s.RecordEnd,
                Rest = s.RestPeriods.ToList(),
                Work = s.WorkPeriods.Concat(unknown.Select(u => new DutyInterval(u.Start, u.End, DutyKind.Work))).OrderBy(x => x.Start.UtcDateTime).ToList(),
                Optimistic = false
            };

            List<RestHourViolation> violations = Evaluate(optimistic, alignedWith: pessimistic);
            var insufficient = new List<RestHourViolation>();
            foreach (RestHourViolation p in Evaluate(pessimistic, includeSplit: false))
            {
                if (!violations.Any(o => o.Rule == p.Rule && Overlaps(o, p)))
                {
                    insufficient.Add(new RestHourViolation(p.Rule, p.WindowStart, p.WindowEnd, p.Actual, p.Limit, p.ViolatingFrom, p.ViolatingTo, p.Clause,
                        "数据不足：结论取决于未标注时段或被记录边界截断的休息段（按不利情形）——" + p.Detail));
                }
            }

            // Split rules must classify each aligned window before grouping. A pessimistic-only
            // edge window can overlap the time span of a definite group without being definite.
            // The existing whole-group overlap policy is retained only for rolling/interval rules.
            var uncertainSplit = new List<RestHourViolation>();
            CheckSplit(pessimistic, uncertainSplit, optimistic, alignedWith: optimistic);
            foreach (RestHourViolation p in uncertainSplit)
            {
                insufficient.Add(new RestHourViolation(p.Rule, p.WindowStart, p.WindowEnd, p.Actual, p.Limit,
                    p.ViolatingFrom, p.ViolatingTo, p.Clause,
                    "数据不足：结论取决于未标注时段或被记录边界截断的休息段（按不利情形）——" + p.Detail));
            }

            TimeSpan totalRest = SumKind(s.RestPeriods, s.RecordStart, s.RecordEnd);
            TimeSpan totalWork = SumKind(s.WorkPeriods, s.RecordStart, s.RecordEnd);
            TimeSpan total = s.RecordEnd - s.RecordStart;
            var report = new RestHourReport(violations, insufficient, totalRest, totalWork, total - totalRest - totalWork);
            return Result<RestHourReport>.Ok(report);
        }

        private List<RestHourViolation> Evaluate(View v, bool includeSplit = true, View alignedWith = null)
        {
            var violations = new List<RestHourViolation>();
            CheckRolling(v, DutyKind.Rest, TimeSpan.FromHours(24), _rules.MinRestPer24h, RestRule.Rest24h, "STCW A-VIII/1 §2.1 / MLC A2.3 §5(b)(i)", violations);
            CheckRolling(v, DutyKind.Rest, TimeSpan.FromDays(7), _rules.MinRestPer7d, RestRule.Rest7d, "STCW A-VIII/1 §2.2 / MLC A2.3 §5(b)(ii)", violations);
            if (_rules.ApplyWorkHourLimits)
            {
                CheckRolling(v, DutyKind.Work, TimeSpan.FromHours(24), _rules.MaxWorkPer24h, RestRule.Work24h, "MLC A2.3 §5(a)(i)", violations);
                CheckRolling(v, DutyKind.Work, TimeSpan.FromDays(7), _rules.MaxWorkPer7d, RestRule.Work7d, "MLC A2.3 §5(a)(ii)", violations);
            }

            if (includeSplit)
            {
                CheckSplit(v, violations, alignedWith: alignedWith);
            }
            CheckIntervals(v, violations);
            return violations;
        }

        /// <summary>两条违规影响的时间跨度 [ViolatingFrom, ViolatingTo + 窗口长) 是否相交。</summary>
        private static bool Overlaps(RestHourViolation a, RestHourViolation b)
        {
            DateTimeOffset aEnd = a.ViolatingTo + (a.WindowEnd - a.WindowStart);
            DateTimeOffset bEnd = b.ViolatingTo + (b.WindowEnd - b.WindowStart);
            return a.ViolatingFrom < bEnd && b.ViolatingFrom < aEnd;
        }

        private static List<DutyInterval> MergeAll(IEnumerable<DutyInterval> rests)
        {
            var merged = new List<DutyInterval>();
            foreach (DutyInterval d in rests.OrderBy(x => x.Start.UtcDateTime))
            {
                if (merged.Count > 0 && d.Start <= merged[merged.Count - 1].End)
                {
                    if (d.End > merged[merged.Count - 1].End)
                    {
                        merged[merged.Count - 1] = new DutyInterval(merged[merged.Count - 1].Start, d.End, DutyKind.Rest);
                    }
                }
                else
                {
                    merged.Add(new DutyInterval(d.Start, d.End, DutyKind.Rest));
                }
            }

            return merged;
        }

        /// <summary>滚动窗口规则（Rest24h/Rest7d/Work24h/Work7d）。</summary>
        private void CheckRolling(
            View s,
            DutyKind kind,
            TimeSpan windowLength,
            TimeSpan limit,
            RestRule rule,
            string clause,
            List<RestHourViolation> outViolations)
        {
            TimeSpan recordLength = s.RecordEnd - s.RecordStart;
            if (recordLength < windowLength)
            {
                return; // 记录短于窗口长度时不评估该规则。
            }

            IReadOnlyList<DutyInterval> periods = kind == DutyKind.Rest ? s.Rest : s.Work;

            // 候选起点：所有状态切换点 b 的 {b, b−24h, b−7d} ∪ {recordStart, recordEnd−L}（L ∈ {24h, 7d}），裁剪、去重、排序。
            DateTimeOffset last = s.RecordEnd - windowLength;
            var candidates = new SortedSet<DateTimeOffset>();
            candidates.Add(s.RecordStart);
            candidates.Add(last);
            // W18.1 / D06：覆盖所有状态切换点（休息、工作段起止）b 的 {b, b−24h, b−7d}；
            // 累计量只在本类时段边界 b 与 b−L 处改变斜率，多出的锚点无害。
            foreach (DateTimeOffset b in Boundaries(s))
            {
                AddCandidate(candidates, b, s.RecordStart, last);
                AddCandidate(candidates, b - TimeSpan.FromHours(24), s.RecordStart, last);
                AddCandidate(candidates, b - TimeSpan.FromDays(7), s.RecordStart, last);
            }

            bool isRest = kind == DutyKind.Rest;
            var cand = new List<DateTimeOffset>(candidates);
            var amounts = new List<TimeSpan>(cand.Count);
            for (int i = 0; i < cand.Count; i++)
            {
                amounts.Add(SumKind(periods, cand[i], cand[i] + windowLength));
            }

            // 相邻候选点之间累计量线性变化：连续违规的候选点归为一组；组两端与相邻合规候选点之间
            // 线性插值求“累计量 == 限值”的起点，作为违规起点范围的（开）端点；
            // 组从记录首个候选点开始（或到最后一个候选点结束）时，端点即该候选点（闭）。
            int g = -1;
            for (int i = 0; i <= cand.Count; i++)
            {
                bool violates = i < cand.Count && (isRest ? amounts[i] < limit : amounts[i] > limit);
                if (violates && g < 0)
                {
                    g = i;
                }
                else if (!violates && g >= 0)
                {
                    int worst = g;
                    for (int k = g + 1; k < i; k++)
                    {
                        if (isRest ? amounts[k] < amounts[worst] : amounts[k] > amounts[worst])
                        {
                            worst = k;
                        }
                    }

                    DateTimeOffset from = g == 0 ? cand[0] : Crossing(cand[g - 1], amounts[g - 1], cand[g], amounts[g], limit);
                    DateTimeOffset to = i == cand.Count ? cand[i - 1] : Crossing(cand[i - 1], amounts[i - 1], cand[i], amounts[i], limit);
                    EmitRolling(outViolations, rule, clause, from, to, cand[worst], amounts[worst], windowLength, limit, isRest);
                    g = -1;
                }
            }
        }

        /// <summary>两点 (a, va)、(b, vb) 间线性插值求累计量等于 limit 的起点；退化时取 b。</summary>
        private static DateTimeOffset Crossing(DateTimeOffset a, TimeSpan va, DateTimeOffset b, TimeSpan vb, TimeSpan limit)
        {
            long dv = vb.Ticks - va.Ticks;
            if (dv == 0)
            {
                return b;
            }

            double ratio = (double)(limit.Ticks - va.Ticks) / dv;
            if (ratio < 0)
            {
                ratio = 0;
            }

            if (ratio > 1)
            {
                ratio = 1;
            }

            return a + TimeSpan.FromTicks((long)Math.Round((b - a).Ticks * ratio));
        }

        private static void AddCandidate(SortedSet<DateTimeOffset> candidates, DateTimeOffset t, DateTimeOffset min, DateTimeOffset max)
        {
            if (t < min)
            {
                t = min;
            }

            if (t > max)
            {
                t = max;
            }

            candidates.Add(t);
        }

        private void EmitRolling(
            List<RestHourViolation> outViolations,
            RestRule rule,
            string clause,
            DateTimeOffset violatingFrom,
            DateTimeOffset violatingTo,
            DateTimeOffset worstStart,
            TimeSpan worstAmount,
            TimeSpan windowLength,
            TimeSpan limit,
            bool isRest)
        {
            string detail = string.Format(
                isRest ? "最差窗口 {0} ~ {1} 休息 {2}，低于下限 {3}；违规窗口起点范围 {4} ~ {5}"
                       : "最差窗口 {0} ~ {1} 工作 {2}，超过上限 {3}；违规窗口起点范围 {4} ~ {5}",
                Utc(worstStart), Utc(worstStart + windowLength), Hm(worstAmount), Hm(limit), Utc(violatingFrom), Utc(violatingTo));
            outViolations.Add(new RestHourViolation(
                rule,
                worstStart,
                worstStart + windowLength,
                worstAmount,
                limit,
                violatingFrom,
                violatingTo,
                clause,
                detail));
        }

        /// <summary>
        /// 拆分约束（RestSplit / LongestRest），W18.1 复裁（方案 C 规范化）：按<b>完整休息段</b>判定，不是严格的任意窗口。
        /// 只评估起点对齐休息段起止点的 24h 窗口：候选起点 = 各休息段起点与终点（裁剪到 [recordStart, recordEnd−24h]）∪ {recordStart, recordEnd−24h}；
        /// 与窗口相交的休息段一律按全长计（不按窗口截断）。LongestRest：最长段 &lt; MinLongestRestPeriod；
        /// RestSplit：相交段总长 ≥ MinRestPer24h 但最长 MaxRestPeriodsPer24h 段之和不足（总量不足由严格的 Rest24h 报）。
        /// 乐观视图下触及记录首/尾的休息段真实长度未知，视为足够长；悲观视图按观测长度。
        /// 候选起点按时间排序后，相邻的违规窗口归为一组：ViolatingFrom/To = 组内首/末窗口起点，最差窗口取值最小者（同值取最早）。
        /// </summary>
        private void CheckSplit(View s, List<RestHourViolation> outViolations, View optimistic = null, View alignedWith = null)
        {
            TimeSpan windowLength = TimeSpan.FromHours(24);
            DateTimeOffset last = s.RecordEnd - windowLength;
            if (last < s.RecordStart)
            {
                return;
            }

            var starts = new SortedSet<DateTimeOffset> { s.RecordStart, last };
            // Unknown intervals may merge/split rest periods differently between views.
            // Use their union so neither emitted group can bridge an opposite-class window.
            IEnumerable<DutyInterval> alignedRests = alignedWith == null ? s.Rest : s.Rest.Concat(alignedWith.Rest);
            foreach (DutyInterval p in alignedRests)
            {
                AddCandidate(starts, p.Start, s.RecordStart, last);
                AddCandidate(starts, p.End, s.RecordStart, last);
            }

            var pts = new List<DateTimeOffset>(starts);
            var stats = new List<SplitStats>(pts.Count);
            foreach (DateTimeOffset t in pts)
            {
                stats.Add(Stats(s, t, windowLength));
            }

            // In the uncertain pass, compare optimistic and pessimistic statistics at the
            // exact same candidate start, not the overlapping span of their emitted groups.
            var optimisticStats = optimistic == null ? null : pts.Select(t => Stats(optimistic, t, windowLength)).ToList();
            bool optimisticHasRest = optimistic != null && optimistic.Rest.Count > 0;
            bool hasRest = s.Rest.Count > 0;
            TimeSpan minLongest = _rules.MinLongestRestPeriod;
            TimeSpan minRest = _rules.MinRestPer24h;
            EmitAlignedGroups(pts, stats, windowLength, RestRule.LongestRest, minLongest,
                st => hasRest && st.Longest < minLongest,
                st => st.Longest,
                (st, t) => string.Format("窗口 {0} ~ {1}（对齐休息段起止点，相交段按完整长度计）：最长休息段 {2}，低于最短单段 {3}", Utc(t), Utc(t + windowLength), Hm(st.Longest), Hm(minLongest)),
                outViolations,
                i => optimisticStats == null || !(optimisticHasRest && optimisticStats[i].Longest < minLongest));
            EmitAlignedGroups(pts, stats, windowLength, RestRule.RestSplit, minRest,
                st => st.Total >= minRest && st.TopN < minRest,
                st => st.TopN,
                (st, t) => string.Format("窗口 {0} ~ {1}（对齐休息段起止点，相交段按完整长度计）：休息段合计 {2} 充足但最长 {4} 段之和 {3} 不足 {5}", Utc(t), Utc(t + windowLength), Hm(st.Total), Hm(st.TopN), _rules.MaxRestPeriodsPer24h, Hm(minRest)),
                outViolations,
                i => optimisticStats == null || !(optimisticStats[i].Total >= minRest && optimisticStats[i].TopN < minRest));
        }

        private struct SplitStats
        {
            public TimeSpan Longest;
            public TimeSpan TopN;
            public TimeSpan Total;
        }

        /// <summary>状态切换点：休息段与工作段的起止（未标注段的边界必然是二者之一或记录首尾）。</summary>
        private static IEnumerable<DateTimeOffset> Boundaries(View s)
        {
            foreach (DutyInterval p in s.Rest.Concat(s.Work))
            {
                yield return p.Start;
                yield return p.End;
            }
        }

        /// <summary>与窗口 [wStart, wStart+L) 相交的休息段（按完整长度；乐观视图下触及记录首尾的段视为足够长）。</summary>
        private SplitStats Stats(View s, DateTimeOffset wStart, TimeSpan windowLength)
        {
            DateTimeOffset wEnd = wStart + windowLength;
            var lengths = new List<TimeSpan>();
            TimeSpan sum = TimeSpan.Zero;
            foreach (DutyInterval p in s.Rest)
            {
                if (p.End <= wStart || p.Start >= wEnd)
                {
                    continue;
                }

                bool openAtRecordEdge = p.Start <= s.RecordStart || p.End >= s.RecordEnd;
                TimeSpan len = s.Optimistic && openAtRecordEdge ? windowLength : p.End - p.Start;
                lengths.Add(len);
                sum += len;
            }

            lengths.Sort((x, y) => y.CompareTo(x));
            TimeSpan top = TimeSpan.Zero;
            for (int k = 0; k < lengths.Count && k < _rules.MaxRestPeriodsPer24h; k++)
            {
                top += lengths[k];
            }

            return new SplitStats { Longest = lengths.Count > 0 ? lengths[0] : TimeSpan.Zero, TopN = top, Total = sum };
        }

        private void EmitAlignedGroups(
            List<DateTimeOffset> pts,
            List<SplitStats> stats,
            TimeSpan windowLength,
            RestRule rule,
            TimeSpan limit,
            Func<SplitStats, bool> violates,
            Func<SplitStats, TimeSpan> value,
            Func<SplitStats, DateTimeOffset, string> detail,
            List<RestHourViolation> outViolations,
            Func<int, bool> includeWindow)
        {
            int g = -1;
            for (int i = 0; i <= pts.Count; i++)
            {
                bool v = i < pts.Count && violates(stats[i]) && includeWindow(i);
                if (v && g < 0)
                {
                    g = i;
                }
                else if (!v && g >= 0)
                {
                    int worst = g;
                    for (int k = g + 1; k < i; k++)
                    {
                        if (value(stats[k]) < value(stats[worst]))
                        {
                            worst = k;
                        }
                    }

                    DateTimeOffset from = pts[g];
                    DateTimeOffset to = pts[i - 1];
                    outViolations.Add(new RestHourViolation(
                        rule, pts[worst], pts[worst] + windowLength, value(stats[worst]), limit,
                        from, to,
                        "STCW A-VIII/1 §3 / MLC A2.3 §6",
                        detail(stats[worst], pts[worst]) + string.Format("；违规对齐窗口起点 {0} ~ {1}", Utc(from), Utc(to))));
                    g = -1;
                }
            }
        }

        /// <summary>相邻两个休息段之间的间隔 > MaxIntervalBetweenRest → 违规；刚好等于 → 合规。</summary>
        private void CheckIntervals(View s, List<RestHourViolation> outViolations)
        {
            for (int i = 1; i < s.Rest.Count; i++)
            {
                DutyInterval prev = s.Rest[i - 1];
                DutyInterval next = s.Rest[i];
                TimeSpan gap = next.Start - prev.End;
                if (gap > _rules.MaxIntervalBetweenRest)
                {
                    string detail = string.Format(
                        "休息段 {0} 结束到下一段 {1} 开始间隔 {2}，超过上限 {3}",
                        Utc(prev.End), Utc(next.Start), Hm(gap), Hm(_rules.MaxIntervalBetweenRest));
                    outViolations.Add(new RestHourViolation(
                        RestRule.RestInterval, prev.End, next.Start, gap, _rules.MaxIntervalBetweenRest,
                        prev.End, prev.End,
                        "STCW A-VIII/1 §3 / MLC A2.3 §6", detail));
                }
            }
        }

        private static string Hm(TimeSpan t)
        {
            long minutes = (long)Math.Round(t.TotalMinutes);
            return (minutes / 60) + "h" + (minutes % 60).ToString("00") + "m";
        }

        private static string Utc(DateTimeOffset t)
        {
            return t.UtcDateTime.ToString("yyyy-MM-dd HH:mm'Z'", System.Globalization.CultureInfo.InvariantCulture);
        }

        private static TimeSpan SumKind(IReadOnlyList<DutyInterval> periods, DateTimeOffset from, DateTimeOffset to)
        {
            TimeSpan sum = TimeSpan.Zero;
            for (int i = 0; i < periods.Count; i++)
            {
                DutyInterval p = periods[i];
                if (p.End <= from || p.Start >= to)
                {
                    continue;
                }

                DateTimeOffset lo = p.Start > from ? p.Start : from;
                DateTimeOffset hi = p.End < to ? p.End : to;
                if (hi > lo)
                {
                    sum += hi - lo;
                }
            }

            return sum;
        }
    }
}
