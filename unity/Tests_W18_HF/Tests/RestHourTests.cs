using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Xunit;

namespace Mcis.W18.HF.Tests
{
    /// <summary>工休校验边界测试（全部虚构数据；时间按 UTC 瞬时）。</summary>
    public class RestHourTests
    {
        internal static readonly DateTimeOffset T0 = new DateTimeOffset(2026, 3, 1, 0, 0, 0, TimeSpan.Zero);

        /// <summary>T0 + hours，按整分钟取整（避免 1/60 小时的浮点误差）。</summary>
        internal static DateTimeOffset H(double hours) { return T0.AddMinutes((long)Math.Round(hours * 60)); }

        /// <summary>按天重复的休息段（相对每天 00:00 的小时数）。</summary>
        private static List<(DateTimeOffset, DateTimeOffset)> Daily(int days, params (double s, double e)[] pattern)
        {
            var list = new List<(DateTimeOffset, DateTimeOffset)>();
            for (int d = 0; d < days; d++)
            {
                foreach (var p in pattern)
                {
                    list.Add((H(d * 24 + p.s), H(d * 24 + p.e)));
                }
            }

            return list;
        }

        private static RestHourReport Check(WorkRestSchedule s, RestHourRules rules = null)
        {
            var r = new RestHourChecker(rules).Check(s);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        private static WorkRestSchedule FromRest(double recordHours, List<(DateTimeOffset, DateTimeOffset)> rest)
        {
            var r = WorkRestSchedule.FromRest(T0, H(recordHours), rest);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        private static IEnumerable<RestHourViolation> Of(RestHourReport rep, RestRule rule)
        {
            return rep.Violations.Where(v => v.Rule == rule);
        }

        // ---------- 10h / 24h ----------

        [Fact]
        public void Rest24h_Exactly10h_6Plus4_IsCompliant()
        {
            // 单窗口（记录恰 24h）与多日排班：6+4 均合规（拆分规则按完整休息段判定，W18.1 复裁）。
            var one = Check(FromRest(24, Daily(1, (8, 14), (18, 22))));
            Assert.True(one.IsCompliant, string.Join("; ", one.Violations.Select(v => v.Detail)));
            var rep = Check(FromRest(72, Daily(3, (8, 14), (18, 22))));
            Assert.True(rep.IsCompliant, string.Join("; ", rep.Violations.Select(v => v.Detail)));
            Assert.Equal(TimeSpan.FromHours(30), rep.TotalRest);
            Assert.Equal(TimeSpan.FromHours(42), rep.TotalWork);
        }

        [Fact]
        public void Rest24h_9h59m_Violates_WithWindowAndValues()
        {
            var rep = Check(FromRest(72, Daily(3, (8, 14), (18, 22 - 1.0 / 60))));
            var v = Assert.Single(Of(rep, RestRule.Rest24h));
            Assert.Equal(TimeSpan.FromMinutes(599), v.Actual);
            Assert.Equal(TimeSpan.FromHours(10), v.Limit);
            Assert.Equal(TimeSpan.FromHours(24), v.WindowEnd - v.WindowStart);
            Assert.Contains("STCW A-VIII/1", v.Clause);
            Assert.Contains("9h59m", v.Detail);
            // 互补：工作 14h01m 也超 MLC 上限。
            Assert.Single(Of(rep, RestRule.Work24h));
        }

        [Fact]
        public void Rest24h_CrossDay_DetectedInNonMidnightWindow_WithExactRange()
        {
            // 两个日历日各 10h 休息（00–10、14–24 第二天的 38–48），但跨日的 24h 窗口几乎没有休息。
            var rep = Check(FromRest(48, new List<(DateTimeOffset, DateTimeOffset)> { (H(0), H(10)), (H(38), H(48)) }));
            var v = Assert.Single(Of(rep, RestRule.Rest24h));
            Assert.Equal(TimeSpan.Zero, v.Actual);
            Assert.Equal(H(10), v.WindowStart);
            Assert.Equal(H(34), v.WindowEnd);
            // 起点 ∈ (00:00, 24:00) 的窗口都不足 10h；端点本身恰好 10h（合规，开区间）。
            Assert.Equal(H(0), v.ViolatingFrom);
            Assert.Equal(H(24), v.ViolatingTo);
            // 间隔 28h 也违规。
            var iv = Assert.Single(Of(rep, RestRule.RestInterval));
            Assert.Equal(TimeSpan.FromHours(28), iv.Actual);
        }

        [Fact]
        public void Rest24h_RecordShorterThanWindow_NotEvaluated()
        {
            var rep = Check(FromRest(20, new List<(DateTimeOffset, DateTimeOffset)> { (H(1), H(3)) }));
            Assert.Empty(Of(rep, RestRule.Rest24h));
            Assert.Empty(Of(rep, RestRule.Rest7d));
        }

        // ---------- 6h 单段 / 至多两段 ----------

        [Fact]
        public void LongestRest_Exactly6h_IsCompliant_5h59m_Violates()
        {
            // 单窗口（记录恰 24h）检验 6h 边界；多日排班见 W18_1Tests（完整休息段口径）。
            Assert.Empty(Of(Check(FromRest(24, Daily(1, (8, 14), (18, 22)))), RestRule.LongestRest));

            var rep = Check(FromRest(24, Daily(1, (8, 14 - 1.0 / 60), (18, 22 + 1.0 / 60))));
            Assert.Empty(Of(rep, RestRule.Rest24h)); // 总量仍 10h
            var v = Of(rep, RestRule.LongestRest).First();
            Assert.Equal(TimeSpan.FromMinutes(359), v.Actual);
            Assert.Equal(TimeSpan.FromHours(6), v.Limit);
            Assert.True(v.ViolatingFrom <= v.WindowStart && v.WindowStart <= v.ViolatingTo); // B1：连续违规的任意窗口归为一组
        }

        [Fact]
        public void ThreePeriods_4_3_3_ViolatesSplitAndLongest()
        {
            var rep = Check(FromRest(72, Daily(3, (6, 10), (14, 17), (20, 23))));
            Assert.Empty(Of(rep, RestRule.Rest24h));
            var split = Of(rep, RestRule.RestSplit).ToList();
            Assert.NotEmpty(split);
            Assert.All(split, v => Assert.Equal(TimeSpan.FromHours(7), v.Actual)); // 完整段：最长两段 4+3
            Assert.NotEmpty(Of(rep, RestRule.LongestRest));
            W18_1Tests.AssertMatchesBruteForce(rep, 72, Enumerable.Range(0, 3).SelectMany(d => new[] { (d * 24 + 6.0, d * 24 + 10.0), (d * 24 + 14.0, d * 24 + 17.0), (d * 24 + 20.0, d * 24 + 23.0) }));
        }

        [Fact]
        public void ThreePeriods_6_2_2_ViolatesSplitOnly()
        {
            // 单窗口（记录恰 24h）：6+2+2 → 只有 RestSplit。
            var one = Check(FromRest(24, Daily(1, (6, 12), (15, 17), (20, 22))));
            Assert.NotEmpty(Of(one, RestRule.RestSplit));
            Assert.Empty(Of(one, RestRule.LongestRest));
            Assert.Empty(Of(one, RestRule.Rest24h));

            // 72h：按完整休息段仍只有 RestSplit（最长段 6h），与参考实现一致。
            var rep = Check(FromRest(72, Daily(3, (6, 12), (15, 17), (20, 22))));
            Assert.NotEmpty(Of(rep, RestRule.RestSplit));
            Assert.Empty(Of(rep, RestRule.LongestRest));
            Assert.Empty(Of(rep, RestRule.Rest24h));
            W18_1Tests.AssertMatchesBruteForce(rep, 72, Enumerable.Range(0, 3).SelectMany(d => new[] { (d * 24 + 6.0, d * 24 + 12.0), (d * 24 + 15.0, d * 24 + 17.0), (d * 24 + 20.0, d * 24 + 22.0) }));
        }

        [Fact]
        public void ThreePeriods_6_4_1_TopTwoReach10h_IsCompliant()
        {
            var rep = Check(FromRest(24, Daily(1, (6, 12), (15, 19), (21, 22)))); // 单窗口
            Assert.Empty(Of(rep, RestRule.RestSplit));
            Assert.Empty(Of(rep, RestRule.LongestRest));
        }

        [Fact]
        public void ThreePeriods_TotalUnder10h_ReportedOnlyAsRest24h()
        {
            var rep = Check(FromRest(72, Daily(3, (6, 10), (14, 16), (20, 23))));
            Assert.NotEmpty(Of(rep, RestRule.Rest24h));
            Assert.Empty(Of(rep, RestRule.RestSplit));
        }

        [Fact]
        public void RestStartingAtRecordStart_IsTruncated_NotAnAnchor()
        {
            // 00:00–03:00 可能是更长休息被记录起点截断，不作锚点。若误作锚点，[00:00, 24:00) 内为 3+6+3
            // （总 12h、最长两段 9h）→ 会误报 RestSplit。其余锚点均为 6+4。
            var rest = new List<(DateTimeOffset, DateTimeOffset)>
            {
                (H(0), H(3)), (H(11), H(17)), (H(21), H(25)), (H(35), H(41)), (H(45), H(49)), (H(59), H(65))
            };
            var rep = Check(FromRest(72, rest), new RestHourRules { ApplyWorkHourLimits = false });
            // 首段触及记录起点：乐观视图视为足够长，不因首段被误判；6+4 本身合规。
            Assert.DoesNotContain(rep.Violations, v => (v.Rule == RestRule.RestSplit || v.Rule == RestRule.LongestRest) && v.WindowStart == H(0));
            Assert.DoesNotContain(rep.Violations, v => (v.Rule == RestRule.RestSplit || v.Rule == RestRule.LongestRest) && v.ViolatingFrom == H(0) && v.ViolatingTo == H(0));
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.RestSplit || v.Rule == RestRule.LongestRest);
        }

        // ---------- 14h 间隔 ----------

        [Fact]
        public void RestInterval_Exactly14h_IsCompliant_14h01m_Violates()
        {
            var ok = Check(FromRest(48, new List<(DateTimeOffset, DateTimeOffset)> { (H(2), H(10)), (H(24), H(34)) }));
            Assert.Empty(Of(ok, RestRule.RestInterval));

            var bad = Check(FromRest(48, new List<(DateTimeOffset, DateTimeOffset)> { (H(2), H(10)), (H(24 + 1.0 / 60), H(34)) }));
            var v = Assert.Single(Of(bad, RestRule.RestInterval));
            Assert.Equal(TimeSpan.FromMinutes(14 * 60 + 1), v.Actual);
            Assert.Equal(H(10), v.WindowStart);
            Assert.Equal(H(24 + 1.0 / 60), v.WindowEnd);
        }

        // ---------- 77h / 7d ----------

        [Fact]
        public void Rest7d_Exactly77h_IsCompliant_76h59m_Violates()
        {
            var rules = new RestHourRules { ApplyWorkHourLimits = false };
            var ok = Check(FromRest(168, Daily(7, (8, 14), (18, 23))), rules);
            Assert.Empty(Of(ok, RestRule.Rest7d));
            Assert.Empty(Of(ok, RestRule.Rest24h)); // 此处只验 77h 边界

            var rest = Daily(7, (8, 14), (18, 23));
            rest[13] = (rest[13].Item1, rest[13].Item2.AddMinutes(-1));
            var bad = Check(FromRest(168, rest), rules);
            var v = Assert.Single(Of(bad, RestRule.Rest7d));
            Assert.Equal(TimeSpan.FromMinutes(77 * 60 - 1), v.Actual);
            Assert.Contains("76h59m", v.Detail);
            Assert.Equal(TimeSpan.FromDays(7), v.WindowEnd - v.WindowStart);
        }

        [Fact]
        public void WorkLimits_DefaultOn_ComplementOf77hRest_TripsWork7d()
        {
            // MLC A2.3 §5 (a)/(b) 二选一；默认同时校验时 77h 休息的补集 91h 工作超 72h。
            var rep = Check(FromRest(168, Daily(7, (8, 14), (18, 23))));
            var v = Assert.Single(Of(rep, RestRule.Work7d));
            Assert.Equal(TimeSpan.FromHours(91), v.Actual);
        }

        // ---------- MLC 工作上限 ----------

        [Fact]
        public void Work24h_Exactly14h_IsCompliant_14h01m_Violates()
        {
            var ok = WorkRestSchedule.Create(T0, H(24), new[] { new DutyInterval(H(0), H(14), DutyKind.Work) }).Value;
            Assert.Empty(Of(Check(ok), RestRule.Work24h));

            var bad = WorkRestSchedule.Create(T0, H(24), new[] { new DutyInterval(H(0), H(14 + 1.0 / 60), DutyKind.Work) }).Value;
            var v = Assert.Single(Of(Check(bad), RestRule.Work24h));
            Assert.Equal(TimeSpan.FromMinutes(14 * 60 + 1), v.Actual);
            Assert.Equal(TimeSpan.FromHours(14), v.Limit);
            Assert.Contains("MLC", v.Clause);
        }

        [Fact]
        public void Work7d_Exactly72h_IsCompliant_72h01m_Violates()
        {
            var work = new List<DutyInterval>();
            for (int d = 0; d < 6; d++) work.Add(new DutyInterval(H(d * 24 + 8), H(d * 24 + 20), DutyKind.Work)); // 6×12 = 72
            var ok = WorkRestSchedule.Create(T0, H(168), work).Value;
            Assert.Empty(Of(Check(ok), RestRule.Work7d));

            work.Add(new DutyInterval(H(6 * 24 + 8), H(6 * 24 + 8 + 1.0 / 60), DutyKind.Work));
            var bad = WorkRestSchedule.Create(T0, H(168), work).Value;
            var v = Assert.Single(Of(Check(bad), RestRule.Work7d));
            Assert.Equal(TimeSpan.FromMinutes(72 * 60 + 1), v.Actual);
        }

        // ---------- Unknown / 构造校验 ----------

        [Fact]
        public void UnlabelledTime_IsUnknown_NotRestNotWork()
        {
            var s = WorkRestSchedule.Create(T0, H(24), new[] { new DutyInterval(H(0), H(8), DutyKind.Work) }).Value;
            var rep = Check(s);
            Assert.Equal(TimeSpan.Zero, rep.TotalRest);
            Assert.Equal(TimeSpan.FromHours(8), rep.TotalWork);
            Assert.Equal(TimeSpan.FromHours(16), rep.TotalUnknown);
            // B2：Unknown 全当休息则合规 → 只报数据不足，不报违规。
            Assert.Empty(Of(rep, RestRule.Rest24h));
            Assert.Single(rep.InsufficientData, v => v.Rule == RestRule.Rest24h);
            Assert.Empty(Of(rep, RestRule.Work24h));
            Assert.False(rep.IsConclusive);
        }

        [Fact]
        public void FromWork_FillsComplementAsRest()
        {
            var s = WorkRestSchedule.FromWork(T0, H(24), new[] { (H(8), H(12)), (H(20), H(24)) }).Value;
            Assert.Equal(2, s.RestPeriods.Count);
            Assert.Equal(H(0), s.RestPeriods[0].Start);
            Assert.Equal(H(8), s.RestPeriods[0].End);
            Assert.Equal(TimeSpan.Zero, Check(s).TotalUnknown);
        }

        [Fact]
        public void AdjacentSameKindPeriods_AreMerged()
        {
            var s = FromRest(48, new List<(DateTimeOffset, DateTimeOffset)> { (H(8), H(11)), (H(11), H(14)) });
            var r = Assert.Single(s.RestPeriods);
            Assert.Equal(TimeSpan.FromHours(6), r.End - r.Start);
        }

        [Fact]
        public void EmptyInput_Fails()
        {
            Assert.Equal("hf_empty_input", WorkRestSchedule.FromRest(T0, H(24), new (DateTimeOffset, DateTimeOffset)[0]).ErrorCode);
            Assert.Equal("hf_empty_input", WorkRestSchedule.FromRest(T0, H(24), null).ErrorCode);
            Assert.Equal("hf_empty_input", WorkRestSchedule.Create(T0, H(24), new DutyInterval[0]).ErrorCode);
            Assert.Equal("hf_empty_input", WorkRestSchedule.Create(T0, H(24), null).ErrorCode);
            Assert.Equal("hf_empty_input", new RestHourChecker().Check(null).ErrorCode);
        }

        [Fact]
        public void OverlappingPeriods_Fail()
        {
            Assert.Equal("hf_overlap", WorkRestSchedule.Create(T0, H(24), new[]
            {
                new DutyInterval(H(0), H(10), DutyKind.Work),
                new DutyInterval(H(5), H(12), DutyKind.Rest)
            }).ErrorCode);
            // 非相邻重叠：长段包住后两段之一。
            Assert.Equal("hf_overlap", WorkRestSchedule.Create(T0, H(24), new[]
            {
                new DutyInterval(H(0), H(10), DutyKind.Work),
                new DutyInterval(H(1), H(2), DutyKind.Rest),
                new DutyInterval(H(3), H(4), DutyKind.Rest)
            }).ErrorCode);
            // 同种类重叠也拒绝（不静默合并）。
            Assert.Equal("hf_overlap", WorkRestSchedule.FromRest(T0, H(24), new[] { (H(0), H(5)), (H(4), H(8)) }).ErrorCode);
        }

        [Fact]
        public void InvalidRecordIntervalAndRules_Fail()
        {
            Assert.Equal("hf_invalid_record", WorkRestSchedule.FromRest(H(5), H(5), new[] { (H(5), H(6)) }).ErrorCode);
            Assert.Equal("hf_invalid_interval", WorkRestSchedule.FromRest(T0, H(24), new[] { (H(6), H(6)) }).ErrorCode);
            Assert.Equal("hf_outside_record", WorkRestSchedule.FromRest(T0, H(24), new[] { (H(20), H(25)) }).ErrorCode);
            var s = FromRest(24, new List<(DateTimeOffset, DateTimeOffset)> { (H(8), H(18)) });
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MinRestPer24h = TimeSpan.Zero }).Check(s).ErrorCode);
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MinLongestRestPeriod = TimeSpan.FromHours(11) }).Check(s).ErrorCode);
            Assert.Equal("hf_invalid_rules", new RestHourChecker(new RestHourRules { MaxRestPeriodsPer24h = 0 }).Check(s).ErrorCode);
        }

        [Fact]
        public void OffsetTimestamps_UseUtcInstants()
        {
            // 同一组瞬时用 +08:00 表示，结果与 UTC 表示一致。
            var cn = TimeSpan.FromHours(8);
            var rest = Daily(3, (8, 14), (18, 22)).Select(p => (p.Item1.ToOffset(cn), p.Item2.ToOffset(cn))).ToList();
            var s = WorkRestSchedule.FromRest(T0.ToOffset(cn), H(72).ToOffset(cn), rest).Value;
            var a = Check(s);
            var b = Check(FromRest(72, Daily(3, (8, 14), (18, 22))));
            Assert.Equal(b.Violations.Select(v => v.Rule + "|" + v.WindowStart.UtcTicks + "|" + v.ViolatingFrom.UtcTicks + "|" + v.ViolatingTo.UtcTicks + "|" + v.Actual),
                a.Violations.Select(v => v.Rule + "|" + v.WindowStart.UtcTicks + "|" + v.ViolatingFrom.UtcTicks + "|" + v.ViolatingTo.UtcTicks + "|" + v.Actual));
            var s1 = WorkRestSchedule.FromRest(T0.ToOffset(cn), H(24).ToOffset(cn), Daily(1, (8, 14), (18, 22)).Select(p => (p.Item1.ToOffset(cn), p.Item2.ToOffset(cn))).ToList()).Value;
            Assert.True(Check(s1).IsCompliant);
        }

        [Fact]
        public void ConfigurableRules_ChangeThresholds()
        {
            var s = FromRest(72, Daily(3, (8, 14), (18, 22)));
            var rep = Check(s, new RestHourRules { MinRestPer24h = TimeSpan.FromHours(11), ApplyWorkHourLimits = false });
            Assert.NotEmpty(Of(rep, RestRule.Rest24h));
        }
    }
}
