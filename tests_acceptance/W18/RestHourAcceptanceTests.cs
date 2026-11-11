using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    /// <summary>STCW A-VIII/1 §2–3 与 MLC A2.3 §5–6 工休校验验收。示例数据·虚构。</summary>
    public sealed class RestHourAcceptanceTests
    {
        private static (DateTimeOffset, DateTimeOffset)[] Daily(int days, params (double a, double b)[] perDay)
        {
            var l = new List<(DateTimeOffset, DateTimeOffset)>();
            for (int d = 0; d < days; d++)
                foreach (var p in perDay) l.Add(P(d * 24 + p.a, d * 24 + p.b));
            return l.ToArray();
        }

        // ---------- 24h 休息 10h（STCW §2.1 / MLC §5(b)(i)）----------

        /// <summary>恰 10h 休息（6h+4h，工作 14h）→ 合规；工作 14h 恰为 MLC §5(a)(i) 上限 → 合规。</summary>
        [Fact]
        public void Rest24h_Exactly10h_Compliant()
        {
            var r = Check(Rest(24, P(1, 7), P(13, 17)));
            Assert.True(r.IsCompliant, Describe(r));
            Assert.Equal(TimeSpan.FromHours(10), r.TotalRest);
            Assert.Equal(TimeSpan.FromHours(14), r.TotalWork);
        }

        /// <summary>9h59m 休息 → Rest24h 违规，Actual=9h59m、Limit=10h，条款引用 STCW A-VIII/1。</summary>
        [Fact]
        public void Rest24h_9h59m_Violation()
        {
            var r = Check(Rest(24, P(1, 7), P(H(13), HM(16, 59))), RestOnly());
            var v = Assert.Single(Of(r, RestRule.Rest24h));
            Assert.Equal(new TimeSpan(9, 59, 0), v.Actual);
            Assert.Equal(TimeSpan.FromHours(10), v.Limit);
            Assert.Contains("STCW A-VIII/1", v.Clause);
        }

        /// <summary>任意起点的滚动 24h：两个日历日各休 10h（合规），但跨日窗口 [07:00, 次日 07:00) 只有 4h → 必须报 Rest24h，最差窗口不在零点。</summary>
        [Fact]
        public void Rest24h_RollingWindowAcrossCalendarDays()
        {
            var r = Check(Rest(48, P(1, 7), P(18, 22), P(32, 38), P(44, 48)), RestOnly());
            // 存在多段不连续的违规组（[07,08] 起点最差 4h；[12h 附近] 起点另一组 8h），取最差那条
            var v = Of(r, RestRule.Rest24h).OrderBy(x => x.Actual).First();
            Assert.Equal(TimeSpan.FromHours(4), v.Actual);
            Assert.NotEqual(TimeSpan.Zero, v.WindowStart.ToOffset(Ship).TimeOfDay);
            Assert.InRange(v.WindowStart, H(7), H(8));
            Assert.True(v.ViolatingFrom <= v.WindowStart && v.WindowStart <= v.ViolatingTo, Describe(r));
            Assert.Equal(TimeSpan.FromHours(24), v.WindowEnd - v.WindowStart);
        }

        // ---------- 至多两段且一段 ≥6h（§3 / MLC §6）----------

        /// <summary>每日 6h+4h、连续 3 天（锚定窗口可完整评估）→ 合规。</summary>
        [Fact]
        public void Split_6hPlus4h_Compliant()
        {
            var r = Check(Rest(72, Daily(3, (1, 7), (13, 17))), RestOnly());
            Assert.True(r.IsCompliant, Describe(r));
        }

        /// <summary>每日 5h59m+4h01m（总 10h）→ LongestRest 违规（最长段 5h59m &lt; 6h）。</summary>
        [Fact]
        public void Split_5h59mLongest_LongestRestViolation()
        {
            var rest = new List<(DateTimeOffset, DateTimeOffset)>();
            for (int d = 0; d < 3; d++) { rest.Add(P(HM(d * 24 + 1, 0), HM(d * 24 + 6, 59))); rest.Add(P(HM(d * 24 + 12, 59), HM(d * 24 + 17, 0))); }
            var r = Check(Rest(72, rest.ToArray()), RestOnly());
            Assert.NotEmpty(Of(r, RestRule.LongestRest));
            Assert.All(Of(r, RestRule.LongestRest), v => Assert.Equal(new TimeSpan(5, 59, 0), v.Actual));
            Assert.Empty(Of(r, RestRule.Rest24h));
        }

        /// <summary>首尾相接的两段休息（[01,04)+[04,08)）应合并为一段 7h，不得按"两段都 &lt;6h"报 LongestRest。</summary>
        [Fact]
        public void Split_AdjacentRestMergedIntoOnePeriod()
        {
            var iv = new List<DutyInterval>();
            for (int d = 0; d < 3; d++)
            {
                iv.Add(new DutyInterval(H(d * 24 + 1), H(d * 24 + 4), DutyKind.Rest));
                iv.Add(new DutyInterval(H(d * 24 + 4), H(d * 24 + 8), DutyKind.Rest));
                iv.Add(new DutyInterval(H(d * 24 + 8), H(d * 24 + 14), DutyKind.Work));
                iv.Add(new DutyInterval(H(d * 24 + 14), H(d * 24 + 17), DutyKind.Rest));
            }
            var s = WorkRestSchedule.Create(T0, H(72), iv).Value;
            Assert.Equal(6, s.RestPeriods.Count);
            Assert.Empty(Of(Check(s, RestOnly()), RestRule.LongestRest));
        }

        // ---------- 两段间隔 ≤14h（§3）----------

        [Fact]
        public void Interval_Exactly14h_Compliant()
        {
            var r = Check(Rest(48, P(2, 8), P(22, 28), P(42, 48)), RestOnly());
            Assert.Empty(Of(r, RestRule.RestInterval));
        }

        [Fact]
        public void Interval_14h01m_Violation()
        {
            var r = Check(Rest(48, P(2, 8), P(HM(22, 1), H(28)), P(42, 48)), RestOnly());
            var v = Assert.Single(Of(r, RestRule.RestInterval));
            Assert.Equal(new TimeSpan(14, 1, 0), v.Actual);
            Assert.Equal(TimeSpan.FromHours(14), v.Limit);
            Assert.Equal(H(8), v.WindowStart);
        }

        // ---------- 7 天 77h（§2.2 / MLC §5(b)(ii)）----------

        [Fact]
        public void Rest7d_Exactly77h_Compliant()
        {
            var r = Check(Rest(168, Daily(7, (1, 12))), RestOnly());
            Assert.Empty(Of(r, RestRule.Rest7d));
            Assert.Equal(TimeSpan.FromHours(77), r.TotalRest);
        }

        [Fact]
        public void Rest7d_76h59m_Violation()
        {
            var rest = Daily(7, (1, 12)).ToList();
            rest[6] = P(H(145), HM(155, 59));
            var r = Check(Rest(168, rest.ToArray()), RestOnly());
            var v = Assert.Single(Of(r, RestRule.Rest7d));
            Assert.Equal(new TimeSpan(3, 4, 59, 0), v.Actual); // 76h59m
            Assert.Equal(TimeSpan.FromHours(77), v.Limit);
        }

        /// <summary>
        /// 跨周（含周日→周一）滚动 7 天：14 天记录，每日休 12h，第 6–9 天（周日至周三）各只休 10h。
        /// 包含全部 4 个短休日的 7 天窗口休息 76h → Rest7d 违规（只报一条、最差 76h）；起点在 [第2天13:00, 第6天01:00] 的窗口均为 76h，其余 ≥77h；每日 ≥10h 不报 Rest24h；间隔恰 14h 不报。
        /// </summary>
        [Fact]
        public void Rest7d_RollingAcrossWeekBoundary()
        {
            var rest = new List<(DateTimeOffset, DateTimeOffset)>();
            for (int d = 0; d < 14; d++) rest.Add(P(d * 24 + 1, d * 24 + (d >= 6 && d <= 9 ? 11 : 13)));
            var r = Check(Rest(14 * 24, rest.ToArray()), RestOnly());
            var v = Assert.Single(Of(r, RestRule.Rest7d));
            Assert.Equal(TimeSpan.FromHours(76), v.Actual);
            Assert.InRange(v.WindowStart, H(2 * 24 + 13), H(6 * 24 + 1));
            Assert.Empty(Of(r, RestRule.Rest24h));
            Assert.Empty(Of(r, RestRule.RestInterval));
        }

        // ---------- MLC 工时 ----------

        [Fact]
        public void Work24h_Exactly14h_Compliant_14h01m_Violation()
        {
            Assert.Empty(Of(Check(Work(24, P(4, 18))), RestRule.Work24h));
            var v = Assert.Single(Of(Check(Work(24, P(H(4), HM(18, 1)))), RestRule.Work24h));
            Assert.Equal(new TimeSpan(14, 1, 0), v.Actual);
            Assert.Contains("MLC", v.Clause);
        }

        [Fact]
        public void Work7d_Exactly72h_Compliant_72h01m_Violation()
        {
            var work = Daily(6, (8, 20)).ToList();
            Assert.Empty(Of(Check(Work(168, work.ToArray())), RestRule.Work7d));
            work[5] = P(H(128), HM(140, 1));
            var v = Assert.Single(Of(Check(Work(168, work.ToArray())), RestRule.Work7d));
            Assert.Equal(new TimeSpan(3, 0, 1, 0), v.Actual);
        }

        [Fact]
        public void WorkLimits_CanBeDisabled()
        {
            var s = Work(24, P(H(4), HM(18, 1)));
            Assert.Empty(Of(Check(s, RestOnly()), RestRule.Work24h));
        }

        // ---------- 输入校验 / 乱序 / 时区 ----------

        [Fact]
        public void Input_Unordered_IsSortedAndSameAsOrdered()
        {
            var a = Describe(Check(Rest(48, P(1, 7), P(18, 22), P(32, 38), P(44, 48)), RestOnly()));
            var b = Describe(Check(Rest(48, P(44, 48), P(18, 22), P(1, 7), P(32, 38)), RestOnly()));
            Assert.Equal(a, b);
        }

        [Fact]
        public void Input_Overlap_Fails_hf_overlap()
        {
            Assert.Equal("hf_overlap", WorkRestSchedule.FromRest(T0, H(24), new[] { P(1, 7), P(6, 9) }).ErrorCode);
            var iv = new[] { new DutyInterval(H(1), H(7), DutyKind.Rest), new DutyInterval(H(6), H(9), DutyKind.Work) };
            Assert.Equal("hf_overlap", WorkRestSchedule.Create(T0, H(24), iv).ErrorCode);
            // 首尾相接不算重叠
            Assert.True(WorkRestSchedule.FromRest(T0, H(24), new[] { P(1, 7), P(7, 9) }).IsSuccess);
        }

        [Fact]
        public void Input_Empty_Null_Invalid()
        {
            Assert.Equal("hf_empty_input", WorkRestSchedule.FromRest(T0, H(24), new (DateTimeOffset, DateTimeOffset)[0]).ErrorCode);
            Assert.Equal("hf_empty_input", WorkRestSchedule.FromRest(T0, H(24), null).ErrorCode);
            Assert.Equal("hf_empty_input", WorkRestSchedule.Create(T0, H(24), new DutyInterval[0]).ErrorCode);
            Assert.Equal("hf_invalid_record", WorkRestSchedule.FromRest(T0, T0, new[] { P(1, 2) }).ErrorCode);
            Assert.Equal("hf_invalid_record", WorkRestSchedule.FromRest(H(5), T0, new[] { P(1, 2) }).ErrorCode);
            Assert.Equal("hf_invalid_interval", WorkRestSchedule.FromRest(T0, H(24), new[] { P(5, 5) }).ErrorCode);
            Assert.Equal("hf_invalid_interval", WorkRestSchedule.FromRest(T0, H(24), new[] { P(6, 5) }).ErrorCode);
            Assert.Equal("hf_outside_record", WorkRestSchedule.FromRest(T0, H(24), new[] { P(-1, 5) }).ErrorCode);
            Assert.Equal("hf_outside_record", WorkRestSchedule.FromRest(T0, H(24), new[] { P(20, 25) }).ErrorCode);
            Assert.Equal("hf_empty_input", new RestHourChecker().Check(null).ErrorCode);
        }

        [Fact]
        public void Input_InvalidRules_Fails_hf_invalid_rules()
        {
            var s = Rest(24, P(1, 11));
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MinRestPer24h = TimeSpan.Zero }).Check(s).ErrorCode);
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MinLongestRestPeriod = TimeSpan.FromHours(11) }).Check(s).ErrorCode);
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MaxRestPeriodsPer24h = 0 }).Check(s).ErrorCode);
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MaxWorkPer24h = TimeSpan.FromHours(24) }).Check(s).ErrorCode);
        }

        /// <summary>时长按绝对时刻：同一排班分别以 UTC、+08:00、混合偏移表达 → 报告完全相同。</summary>
        [Fact]
        public void TimeZone_SameInstantsDifferentOffsets_SameReport()
        {
            var ship = new[] { P(1, 7), P(18, 22), P(32, 38), P(44, 48) };
            var utc = ship.Select(p => (p.Item1.ToUniversalTime(), p.Item2.ToUniversalTime())).ToArray();
            var mixed = ship.Select((p, i) => (p.Item1.ToOffset(TimeSpan.FromHours(i % 2 == 0 ? -5 : 9.5)), p.Item2)).ToArray();
            string a = Describe(new RestHourChecker(RestOnly()).Check(WorkRestSchedule.FromRest(T0, H(48), ship).Value).Value);
            string b = Describe(new RestHourChecker(RestOnly()).Check(WorkRestSchedule.FromRest(T0.ToUniversalTime(), H(48).ToUniversalTime(), utc).Value).Value);
            string c = Describe(new RestHourChecker(RestOnly()).Check(WorkRestSchedule.FromRest(T0, H(48), mixed).Value).Value);
            Assert.Equal(a, b);
            Assert.Equal(a, c);
        }

        [Fact]
        public void Totals_UnknownTimeReported()
        {
            var iv = new[] { new DutyInterval(H(0), H(8), DutyKind.Work), new DutyInterval(H(8), H(16), DutyKind.Rest) };
            var r = Check(WorkRestSchedule.Create(T0, H(24), iv).Value);
            Assert.Equal(TimeSpan.FromHours(8), r.TotalUnknown);
            Assert.Equal(TimeSpan.FromHours(8), r.TotalRest);
            Assert.Equal(TimeSpan.FromHours(8), r.TotalWork);
        }

        /// <summary>确定性：同输入两次、新建检查器 → 逐字段相同。</summary>
        [Fact]
        public void Determinism_SameInputSameReport()
        {
            var rest = Daily(9, (1, 6), (13, 16)).ToArray();
            string a = Describe(Check(Rest(9 * 24, rest)));
            string b = Describe(Check(Rest(9 * 24, rest.Reverse().ToArray())));
            Assert.Equal(a, b);
            Assert.NotEmpty(Check(Rest(9 * 24, rest)).Violations);
        }
    }
}
