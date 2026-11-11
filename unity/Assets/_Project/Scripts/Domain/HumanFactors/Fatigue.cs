using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;

namespace Mcis.Domain.HumanFactors
{
    /// <summary>疲劳指标计算参数。</summary>
    public sealed class FatigueRules
    {
        /// <summary>人体节律低谷起始（本日 02:00，船时）。</summary>
        public TimeSpan CircadianLowStart { get; set; }

        /// <summary>人体节律低谷结束（本日 06:00，船时）。半开区间 [Start, End)。</summary>
        public TimeSpan CircadianLowEnd { get; set; }

        /// <summary>回看窗口长度，默认 24h。</summary>
        public TimeSpan Lookback { get; set; }

        /// <summary>D01：连续清醒向前追溯最近一次睡眠结束的上限，默认 7 天；超出报“>7d 无睡眠记录”。</summary>
        public TimeSpan MaxContinuousAwakeLookback { get; set; }

        public FatigueRules()
        {
            MaxContinuousAwakeLookback = TimeSpan.FromDays(7);
            CircadianLowStart = TimeSpan.FromHours(2);
            CircadianLowEnd = TimeSpan.FromHours(6);
            Lookback = TimeSpan.FromHours(24);
        }
    }

    /// <summary>连续清醒时长的确定程度（W18-D01）。</summary>
    public enum ContinuousAwakeStatus
    {
        /// <summary>由记录确定（含事发时在睡 = 0）。</summary>
        Measured = 0,

        /// <summary>覆盖了整个追溯上限（默认 7 天）仍无睡眠：“>7d 无睡眠记录”，ContinuousAwake = null。</summary>
        NoSleepWithinLimit = 1,

        /// <summary>记录覆盖不足（排班代理记录短或未覆盖到事发），无法确定，ContinuousAwake = null。</summary>
        InsufficientCoverage = 2
    }

    /// <summary>事发时刻的疲劳指标快照。</summary>
    public sealed class FatigueIndicators
    {
        /// <summary>事发时刻（UTC 瞬时）。</summary>
        public DateTimeOffset IncidentUtc { get; }

        /// <summary>事发时刻换算到船时（或事发时刻自身 Offset）。</summary>
        public DateTimeOffset IncidentLocal { get; }

        /// <summary>实际采用的本地时区偏移。</summary>
        public TimeSpan LocalOffset { get; }

        /// <summary>事发前回看窗口内累计清醒时长（只计记录覆盖内的时间；覆盖外计入 UnknownLast24h，D03）。</summary>
        public TimeSpan AwakeLast24h { get; }

        /// <summary>事发前回看窗口内累计睡眠时长。</summary>
        public TimeSpan SleepLast24h { get; }

        /// <summary>
        /// 距最近一次睡眠结束的连续清醒时长（至事发），向前追溯至 MaxContinuousAwakeLookback（默认 7 天），不受 24h 回看限制；
        /// 事发时在睡则 0；无法确定时为 null，原因见 <see cref="ContinuousAwakeStatus"/>。
        /// </summary>
        public TimeSpan? ContinuousAwake { get; }

        /// <summary>事发前回看窗口内累计休息时长（来自排班；无排班时以睡眠为代理）。</summary>
        public TimeSpan RestLast24h { get; }

        /// <summary>
        /// 事发前 7 天窗口内累计休息时长。若排班记录不足 7 天，只统计记录窗口内的部分
        /// （不外推、不补全——见 FatigueCalculator.Compute 注释）。
        /// </summary>
        public TimeSpan RestLast7d { get; }

        /// <summary>事发前回看窗口内最长连续休息段。</summary>
        public TimeSpan LongestRestLast24h { get; }

        /// <summary>事发时（按本地时间）是否处于节律低谷 [02:00, 06:00)。</summary>
        public bool InCircadianLow { get; }

        /// <summary>睡眠是否用休息段代理（未提供 sleepPeriods，改用排班休息段）。</summary>
        public bool SleepIsRestProxy { get; }

        /// <summary>D01：连续清醒的确定程度。</summary>
        public ContinuousAwakeStatus ContinuousAwakeStatus { get; }

        /// <summary>D01：给人读的说明，如 "&gt;7d 无睡眠记录"；Measured 时为空串。</summary>
        public string ContinuousAwakeNote { get; }

        /// <summary>D03：回看窗口内有记录覆盖的起止（显式睡眠列表视为完整覆盖；排班代理 = 记录 ∩ 回看窗口）。</summary>
        public DateTimeOffset CoverageStart { get; }
        public DateTimeOffset CoverageEnd { get; }

        /// <summary>D03：回看窗口内无记录的时长（既不算清醒也不算睡眠）。</summary>
        public TimeSpan UnknownLast24h { get; }

        /// <summary>D03：回看窗口未被记录完整覆盖。</summary>
        public bool Truncated { get; }

        /// <summary>D03：7 天窗口未被记录完整覆盖（RestLast7d 只是记录内部分之和）。</summary>
        public bool RestLast7dTruncated { get; }

        public FatigueIndicators(
            DateTimeOffset incidentUtc,
            DateTimeOffset incidentLocal,
            TimeSpan localOffset,
            TimeSpan awakeLast24h,
            TimeSpan sleepLast24h,
            TimeSpan? continuousAwake,
            TimeSpan restLast24h,
            TimeSpan restLast7d,
            TimeSpan longestRestLast24h,
            bool inCircadianLow,
            bool sleepIsRestProxy)
        {
            IncidentUtc = incidentUtc;
            IncidentLocal = incidentLocal;
            LocalOffset = localOffset;
            AwakeLast24h = awakeLast24h;
            SleepLast24h = sleepLast24h;
            ContinuousAwake = continuousAwake;
            RestLast24h = restLast24h;
            RestLast7d = restLast7d;
            LongestRestLast24h = longestRestLast24h;
            InCircadianLow = inCircadianLow;
            SleepIsRestProxy = sleepIsRestProxy;
            ContinuousAwakeStatus = continuousAwake.HasValue ? ContinuousAwakeStatus.Measured : ContinuousAwakeStatus.InsufficientCoverage;
            ContinuousAwakeNote = string.Empty;
            CoverageStart = incidentUtc - (awakeLast24h + sleepLast24h);
            CoverageEnd = incidentUtc;
            UnknownLast24h = TimeSpan.Zero;
        }

        public FatigueIndicators(
            DateTimeOffset incidentUtc,
            DateTimeOffset incidentLocal,
            TimeSpan localOffset,
            TimeSpan awakeLast24h,
            TimeSpan sleepLast24h,
            TimeSpan? continuousAwake,
            TimeSpan restLast24h,
            TimeSpan restLast7d,
            TimeSpan longestRestLast24h,
            bool inCircadianLow,
            bool sleepIsRestProxy,
            ContinuousAwakeStatus continuousAwakeStatus,
            string continuousAwakeNote,
            DateTimeOffset coverageStart,
            DateTimeOffset coverageEnd,
            TimeSpan unknownLast24h,
            bool truncated,
            bool restLast7dTruncated)
            : this(incidentUtc, incidentLocal, localOffset, awakeLast24h, sleepLast24h, continuousAwake, restLast24h, restLast7d, longestRestLast24h, inCircadianLow, sleepIsRestProxy)
        {
            ContinuousAwakeStatus = continuousAwakeStatus;
            ContinuousAwakeNote = continuousAwakeNote ?? string.Empty;
            CoverageStart = coverageStart;
            CoverageEnd = coverageEnd;
            UnknownLast24h = unknownLast24h;
            Truncated = truncated;
            RestLast7dTruncated = restLast7dTruncated;
        }
    }

    /// <summary>疲劳指标计算器。全部按 UTC 瞬时计算时长；节律低谷按船时（本地钟面）判断。</summary>
    public static class FatigueCalculator
    {
        public const string ErrEmptyInput = "hf_empty_input";
        public const string ErrInvalidOffset = "hf_invalid_offset";
        public const string ErrOverlap = "hf_overlap";
        public const string ErrInvalidInterval = "hf_invalid_interval";
        public const string ErrInvalidRules = "hf_invalid_rules";

        /// <summary>
        /// 计算事发时刻的疲劳指标。
        /// 时区：shipLocalOffset 给出时按该船时偏移判断节律低谷与 IncidentLocal；为 null 时用 incident 自身的 Offset。
        /// offset 必须是整分钟且在 ±14h 内，否则 hf_invalid_offset（D02，不抛异常）。
        /// 睡眠来源（B7）：sleepPeriods 为 null 或空列表 → 用 schedule 休息段代理（SleepIsRestProxy=true），两者都无 → hf_empty_input；
        /// 仅当 sleepRecordComplete=true 时空列表才表示“确认无睡眠”。非空的显式睡眠列表视为完整记录（覆盖整个追溯范围）。
        /// 覆盖（D03）：排班代理时覆盖 = 记录窗口 ∩ 回看窗口；覆盖外时间计入 UnknownLast24h，不计清醒，并置 Truncated。
        /// RestLast7d 只统计记录内部分（不外推），记录不足 7 天时 RestLast7dTruncated=true。
        /// 连续清醒（D01）：追溯到最近一次睡眠结束，不受 24h 限制，上限 MaxContinuousAwakeLookback（默认 7 天）。
        /// </summary>
        public static Result<FatigueIndicators> Compute(
            DateTimeOffset incident,
            TimeSpan? shipLocalOffset,
            IEnumerable<(DateTimeOffset Start, DateTimeOffset End)> sleepPeriods,
            WorkRestSchedule schedule = null,
            FatigueRules rules = null,
            bool sleepRecordComplete = false)
        {
            FatigueRules r = rules ?? new FatigueRules();
            if (r.Lookback <= TimeSpan.Zero || r.CircadianLowStart < TimeSpan.Zero || r.CircadianLowStart >= TimeSpan.FromDays(1) ||
                r.CircadianLowEnd < TimeSpan.Zero || r.CircadianLowEnd > TimeSpan.FromDays(1) || r.MaxContinuousAwakeLookback <= TimeSpan.Zero)
            {
                return Result<FatigueIndicators>.Fail(ErrInvalidRules, "疲劳参数无效");
            }

            TimeSpan offset = shipLocalOffset ?? incident.Offset;
            if (offset > TimeSpan.FromHours(14) || offset < TimeSpan.FromHours(-14))
            {
                return Result<FatigueIndicators>.Fail(ErrInvalidOffset, "时区偏移超出 ±14h：" + offset);
            }

            if (offset.Ticks % TimeSpan.TicksPerMinute != 0)
            {
                return Result<FatigueIndicators>.Fail(ErrInvalidOffset, "时区偏移须为整分钟：" + offset); // W18-D02
            }

            List<(DateTimeOffset Start, DateTimeOffset End)> given = sleepPeriods == null ? null : sleepPeriods.ToList();
            bool sleepIsRestProxy = given == null || (given.Count == 0 && !sleepRecordComplete); // B7：空列表 = null
            if (sleepIsRestProxy && schedule == null)
            {
                return Result<FatigueIndicators>.Fail(ErrEmptyInput, "sleepPeriods 与 schedule 均为空（空睡眠列表视同未提供，确认无睡眠请传 sleepRecordComplete=true）");
            }

            // 睡眠段：外部给出，或用排班休息段代理。
            var sleep = new List<DutyInterval>();
            if (!sleepIsRestProxy)
            {
                var sorted = given.OrderBy(p => p.Start.UtcDateTime).ToList();
                DateTimeOffset? maxEnd = null;
                for (int i = 0; i < sorted.Count; i++)
                {
                    if (sorted[i].End <= sorted[i].Start)
                    {
                        return Result<FatigueIndicators>.Fail(ErrInvalidInterval, "睡眠段无效（end<=start）");
                    }

                    // 与此前任一段重叠（首尾相接不算）。
                    if (maxEnd.HasValue && sorted[i].Start < maxEnd.Value)
                    {
                        return Result<FatigueIndicators>.Fail(ErrOverlap, "睡眠段重叠");
                    }

                    if (!maxEnd.HasValue || sorted[i].End > maxEnd.Value)
                    {
                        maxEnd = sorted[i].End;
                    }

                    sleep.Add(new DutyInterval(sorted[i].Start, sorted[i].End, DutyKind.Rest));
                }
            }
            else
            {
                sleep.AddRange(schedule.RestPeriods);
            }

            DateTimeOffset windowStart = incident - r.Lookback;
            DateTimeOffset traceStart = incident - r.MaxContinuousAwakeLookback;

            // 覆盖范围（D03）：显式睡眠列表视为完整；排班代理 = 记录窗口。
            DateTimeOffset recStart = sleepIsRestProxy ? schedule.RecordStart : DateTimeOffset.MinValue;
            DateTimeOffset recEnd = sleepIsRestProxy ? schedule.RecordEnd : DateTimeOffset.MaxValue;
            DateTimeOffset covStart = Max(windowStart, recStart);
            DateTimeOffset covEnd = Min(incident, recEnd);
            if (covEnd < covStart)
            {
                covEnd = covStart; // 记录与回看窗口不相交：覆盖为空。
            }

            TimeSpan covered = covEnd - covStart;
            TimeSpan sleepLast = SumOverlap(sleep, covStart, covEnd);
            TimeSpan awakeLast = covered - sleepLast;
            TimeSpan unknownLast = r.Lookback - covered;

            // 连续清醒（D01）。
            TimeSpan? continuousAwake = null;
            ContinuousAwakeStatus caStatus;
            string caNote = string.Empty;
            bool incidentCovered = recEnd >= incident && recStart <= incident;
            DateTimeOffset? latestEnd = null;
            bool asleep = false;
            for (int i = 0; i < sleep.Count; i++)
            {
                DutyInterval p = sleep[i];
                if (p.Start <= incident && p.End > incident)
                {
                    asleep = true;
                    break;
                }

                if (p.End <= incident && p.End >= traceStart && (latestEnd == null || p.End > latestEnd.Value))
                {
                    latestEnd = p.End;
                }
            }

            if (asleep)
            {
                continuousAwake = TimeSpan.Zero;
                caStatus = ContinuousAwakeStatus.Measured;
            }
            else if (!incidentCovered)
            {
                caStatus = ContinuousAwakeStatus.InsufficientCoverage;
                caNote = "记录未覆盖到事发时刻（记录止于 " + recEnd.UtcDateTime.ToString("yyyy-MM-dd HH:mm'Z'", System.Globalization.CultureInfo.InvariantCulture) + "）";
            }
            else if (latestEnd.HasValue)
            {
                continuousAwake = incident - latestEnd.Value;
                caStatus = ContinuousAwakeStatus.Measured;
            }
            else if (recStart <= traceStart)
            {
                caStatus = ContinuousAwakeStatus.NoSleepWithinLimit;
                caNote = ">" + FormatSpan(r.MaxContinuousAwakeLookback) + " 无睡眠记录";
            }
            else
            {
                caStatus = ContinuousAwakeStatus.InsufficientCoverage;
                caNote = "记录只覆盖事发前 " + FormatSpan(incident - recStart) + "，其中无睡眠，无法确定连续清醒";
            }

            // 休息指标：有排班用排班；无排班用睡眠段作代理。
            IReadOnlyList<DutyInterval> restSource = schedule != null ? schedule.RestPeriods : sleep;
            DateTimeOffset sevenStart = incident - TimeSpan.FromDays(7);
            DateTimeOffset sevenFrom = sevenStart < windowStart ? sevenStart : windowStart;
            bool rest7Truncated = false;
            if (schedule != null && (sevenFrom < schedule.RecordStart || schedule.RecordEnd < incident))
            {
                rest7Truncated = true;
                if (sevenFrom < schedule.RecordStart)
                {
                    sevenFrom = schedule.RecordStart; // 记录不足 7 天：只统计记录内部分，不外推。
                }
            }

            TimeSpan restLast24h = SumOverlap(restSource, windowStart, incident);
            TimeSpan restLast7d = SumOverlap(restSource, sevenFrom, incident);
            TimeSpan longestRest24h = LongestOverlap(restSource, windowStart, incident);

            DateTimeOffset local = incident.ToOffset(offset);
            TimeSpan tod = local.TimeOfDay;
            bool inLow = r.CircadianLowStart < r.CircadianLowEnd
                ? tod >= r.CircadianLowStart && tod < r.CircadianLowEnd
                : r.CircadianLowStart == r.CircadianLowEnd
                    ? false
                    : tod >= r.CircadianLowStart || tod < r.CircadianLowEnd; // 跨零点区间。

            var indicators = new FatigueIndicators(
                incident,
                local,
                offset,
                awakeLast,
                sleepLast,
                continuousAwake,
                restLast24h,
                restLast7d,
                longestRest24h,
                inLow,
                sleepIsRestProxy,
                caStatus,
                caNote,
                covStart,
                covEnd,
                unknownLast,
                unknownLast > TimeSpan.Zero,
                rest7Truncated);
            return Result<FatigueIndicators>.Ok(indicators);
        }

        private static DateTimeOffset Max(DateTimeOffset a, DateTimeOffset b)
        {
            return a > b ? a : b;
        }

        private static DateTimeOffset Min(DateTimeOffset a, DateTimeOffset b)
        {
            return a < b ? a : b;
        }

        private static string FormatSpan(TimeSpan t)
        {
            if (t.Ticks % TimeSpan.TicksPerDay == 0)
            {
                return ((long)t.TotalDays).ToString(System.Globalization.CultureInfo.InvariantCulture) + "d";
            }

            return ((long)Math.Round(t.TotalMinutes) / 60).ToString(System.Globalization.CultureInfo.InvariantCulture) + "h" +
                   ((long)Math.Round(t.TotalMinutes) % 60).ToString("00", System.Globalization.CultureInfo.InvariantCulture) + "m";
        }

        private static TimeSpan SumOverlap(IReadOnlyList<DutyInterval> periods, DateTimeOffset from, DateTimeOffset to)
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

        private static TimeSpan LongestOverlap(IReadOnlyList<DutyInterval> periods, DateTimeOffset from, DateTimeOffset to)
        {
            TimeSpan best = TimeSpan.Zero;
            for (int i = 0; i < periods.Count; i++)
            {
                DutyInterval p = periods[i];
                if (p.End <= from || p.Start >= to)
                {
                    continue;
                }

                DateTimeOffset lo = p.Start > from ? p.Start : from;
                DateTimeOffset hi = p.End < to ? p.End : to;
                TimeSpan len = hi - lo;
                if (len > best)
                {
                    best = len;
                }
            }

            return best;
        }
    }
}
