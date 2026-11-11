using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Xunit;

namespace Mcis.W18.HF.Tests
{
    /// <summary>W18.2 D08: synthetic schedules, not real crew records.</summary>
    public sealed class W18_2Tests
    {
        private static readonly DateTimeOffset T0 = new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero);

        private static RestHourReport Report(int durationMinutes, params (int, int)[] rests)
        {
            var schedule = WorkRestSchedule.FromRest(T0, T0.AddMinutes(durationMinutes),
                rests.Select(p => (T0.AddMinutes(p.Item1), T0.AddMinutes(p.Item2))));
            Assert.True(schedule.IsSuccess, schedule.ErrorCode);
            var result = new RestHourChecker(new RestHourRules { ApplyWorkHourLimits = false }).Check(schedule.Value);
            Assert.True(result.IsSuccess, result.ErrorCode);
            return result.Value;
        }

        private static bool Contains(RestHourViolation item, RestRule rule, int minute)
        {
            DateTimeOffset at = T0.AddMinutes(minute);
            return item.Rule == rule && item.ViolatingFrom <= at && at <= item.ViolatingTo;
        }

        [Fact]
        public void TailTruncatedRestWindowRemainsInsufficientBesideDefiniteViolation()
        {
            var report = Report(2880, (240, 600), (2521, 2880));
            Assert.Contains(report.Violations, v => Contains(v, RestRule.LongestRest, 600));
            var uncertain = Assert.Single(report.InsufficientData, v => Contains(v, RestRule.LongestRest, 1440));
            Assert.Equal(TimeSpan.FromMinutes(359), uncertain.Actual);
            Assert.DoesNotContain(report.Violations, v => Contains(v, RestRule.LongestRest, 1440));
        }

        [Fact]
        public void HeadTruncatedRestWindowRemainsVisible()
        {
            var report = Report(2880, (0, 359), (2280, 2640));
            Assert.Contains(report.InsufficientData, v => Contains(v, RestRule.LongestRest, 0));
            Assert.DoesNotContain(report.Violations, v => Contains(v, RestRule.LongestRest, 0));
            Assert.Contains(report.Violations, v => v.Rule == RestRule.LongestRest);
        }

        [Fact]
        public void SplitPeriodsAlsoKeepEdgeUncertaintyApartFromDefiniteGroups()
        {
            var report = Report(2880, (120, 360), (600, 840), (1080, 1320),
                (1560, 1800), (2040, 2280), (2640, 2880));
            Assert.Contains(report.Violations, v => Contains(v, RestRule.RestSplit, 0));
            Assert.Contains(report.InsufficientData, v => Contains(v, RestRule.RestSplit, 1440));
            Assert.DoesNotContain(report.Violations, v => Contains(v, RestRule.RestSplit, 1440));
        }

        [Fact]
        public void CompleteSixHoursAtEdgeDoesNotInventUncertainty()
        {
            var report = Report(2880, (240, 600), (2520, 2880));
            Assert.DoesNotContain(report.InsufficientData, v => Contains(v, RestRule.LongestRest, 1440));
            Assert.DoesNotContain(report.Violations, v => Contains(v, RestRule.LongestRest, 1440));
        }

        [Fact]
        public void SingleTwentyFourHourRecordDoesNotDuplicateItsEdgeWindow()
        {
            var report = Report(1440, (0, 359), (600, 900), (1081, 1440));
            var only = Assert.Single(report.InsufficientData, v => v.Rule == RestRule.LongestRest);
            Assert.Equal(T0, only.ViolatingFrom);
            Assert.Equal(T0, only.ViolatingTo);
            Assert.DoesNotContain(report.Violations, v => v.Rule == RestRule.LongestRest);
        }

        [Fact]
        public void UnknownTailWindowIsNotSwallowedByEarlierDefiniteGroup()
        {
            var schedule = WorkRestSchedule.Create(T0, T0.AddHours(48), new[]
            {
                new DutyInterval(T0, T0.AddHours(4), DutyKind.Work),
                new DutyInterval(T0.AddHours(4), T0.AddHours(10), DutyKind.Rest),
                new DutyInterval(T0.AddHours(10), T0.AddMinutes(2521), DutyKind.Work)
            });
            Assert.True(schedule.IsSuccess, schedule.ErrorCode);
            var result = new RestHourChecker(new RestHourRules { ApplyWorkHourLimits = false }).Check(schedule.Value);
            Assert.True(result.IsSuccess, result.ErrorCode);
            var report = result.Value;
            Assert.Contains(report.Violations, v => Contains(v, RestRule.LongestRest, 600));
            Assert.Contains(report.InsufficientData, v => Contains(v, RestRule.LongestRest, 1440));
            Assert.DoesNotContain(report.Violations, v => Contains(v, RestRule.LongestRest, 1440));
        }

        [Fact]
        public void RandomUnknownSchedulesClassifyEveryCommonAlignedWindow()
        {
            var random = new Random(18208);
            for (int trial = 0; trial < 120; trial++)
            {
                var states = Enumerable.Range(0, 48).Select(_ => random.Next(3)).ToArray();
                states[0] = 1; // Rest; 0=Work, 2=Unknown.
                states[47] = 2;
                var entries = Enumerable.Range(0, 48).Where(i => states[i] != 2)
                    .Select(i => new DutyInterval(T0.AddHours(i), T0.AddHours(i + 1),
                        states[i] == 1 ? DutyKind.Rest : DutyKind.Work));
                var schedule = WorkRestSchedule.Create(T0, T0.AddHours(48), entries);
                Assert.True(schedule.IsSuccess, schedule.ErrorCode);
                var checkedSchedule = new RestHourChecker(new RestHourRules { ApplyWorkHourLimits = false }).Check(schedule.Value);
                Assert.True(checkedSchedule.IsSuccess, checkedSchedule.ErrorCode);
                var report = checkedSchedule.Value;
                var observed = ReferenceRests(states, false);
                var optimistic = ReferenceRests(states, true);
                var starts = new SortedSet<int> { 0, 24 };
                foreach (var segment in observed.Concat(optimistic))
                {
                    starts.Add(Math.Max(0, Math.Min(24, segment.Start)));
                    starts.Add(Math.Max(0, Math.Min(24, segment.End)));
                }
                foreach (int start in starts)
                {
                    foreach (RestRule rule in new[] { RestRule.LongestRest, RestRule.RestSplit })
                    {
                        bool definite = ReferenceViolation(optimistic, start, true, rule);
                        bool uncertain = ReferenceViolation(observed, start, false, rule) && !definite;
                        Assert.Equal(definite, report.Violations.Any(v => Contains(v, rule, start * 60)));
                        Assert.Equal(uncertain, report.InsufficientData.Any(v => Contains(v, rule, start * 60)));
                    }
                }
            }
        }

        private static List<(int Start, int End)> ReferenceRests(int[] states, bool optimistic)
        {
            var result = new List<(int Start, int End)>();
            int from = -1;
            for (int hour = 0; hour <= states.Length; hour++)
            {
                bool rest = hour < states.Length && (states[hour] == 1 || optimistic && states[hour] == 2);
                if (rest && from < 0) from = hour;
                if (!rest && from >= 0) { result.Add((from, hour)); from = -1; }
            }
            return result;
        }

        private static bool ReferenceViolation(List<(int Start, int End)> rests, int start, bool optimistic, RestRule rule)
        {
            var lengths = rests.Where(p => p.Start < start + 24 && p.End > start)
                .Select(p => optimistic && (p.Start == 0 || p.End == 48) ? 24 : p.End - p.Start)
                .OrderByDescending(n => n).ToList();
            if (rule == RestRule.LongestRest)
                return rests.Count > 0 && (lengths.Count == 0 || lengths[0] < 6);
            return lengths.Sum() >= 10 && lengths.Take(2).Sum() < 10;
        }

        [Fact]
        public void AssumptionsIncludeTheExactRecordEdgeRuling()
        {
            var report = Report(1440, (60, 660));
            Assert.Contains("拆分规则另评估记录首窗口和记录尾−24h 窗口；被记录边界截断的休息段按可见长度计，并标注数据不足。", report.Assumptions);
        }
    }
}
