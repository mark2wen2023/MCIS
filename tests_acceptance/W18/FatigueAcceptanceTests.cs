using System;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    /// <summary>疲劳指标（连续清醒、24h 清醒/睡眠、节律低谷、时区）验收。示例数据·虚构。</summary>
    public sealed class FatigueAcceptanceTests
    {
        private static readonly DateTimeOffset Incident = HM(38, 24); // 第 2 天 14:24 船时

        private static FatigueIndicators Ok(DateTimeOffset incident, TimeSpan? offset, (DateTimeOffset, DateTimeOffset)[] sleep, WorkRestSchedule s = null, FatigueRules rules = null)
        {
            var r = FatigueCalculator.Compute(incident, offset, sleep, s, rules);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        /// <summary>睡 23:00–07:00（8h），14:24 事发 → 连续清醒 7h24m；24h 内睡 8h、清醒 16h。</summary>
        [Fact]
        public void ContinuousAwake_And_24hAwake_Basic()
        {
            var f = Ok(Incident, Ship, new[] { P(23, 31) });
            Assert.Equal(new TimeSpan(7, 24, 0), f.ContinuousAwake);
            Assert.Equal(TimeSpan.FromHours(8), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(16), f.AwakeLast24h);
            Assert.False(f.SleepIsRestProxy);
        }

        /// <summary>多段睡眠取最近结束者；回看窗口边界裁剪：窗口起点前开始的睡眠只计窗口内部分。</summary>
        [Fact]
        public void ContinuousAwake_UsesLatestSleep_And24hClipsAtWindowStart()
        {
            // 窗口 [14:24 前一日, 14:24]：第一段 [10:00,16:24) 只计 2h；第二段 [31,33) 2h
            var f = Ok(Incident, Ship, new[] { P(H(10), HM(16, 24)), P(31, 33) });
            Assert.Equal(TimeSpan.FromHours(4), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(20), f.AwakeLast24h);
            Assert.Equal(new TimeSpan(5, 24, 0), f.ContinuousAwake);
        }

        [Fact]
        public void ContinuousAwake_AsleepAtIncident_IsZero()
        {
            var f = Ok(Incident, Ship, new[] { P(H(36), H(40)) });
            Assert.Equal(TimeSpan.Zero, f.ContinuousAwake);
        }

        /// <summary>睡眠恰在事发时刻结束（半开区间 [s,e)）→ 连续清醒 0。</summary>
        [Fact]
        public void ContinuousAwake_SleepEndsExactlyAtIncident_IsZero()
        {
            var f = Ok(Incident, Ship, new[] { P(H(30), Incident) });
            Assert.Equal(TimeSpan.Zero, f.ContinuousAwake);
        }

        /// <summary>
        /// 连续清醒超过 24h：有睡眠记录，最近一次睡眠在事发前 30h 结束 → 连续清醒应为 30h（可由记录确定），
        /// 不应返回 null（"无法确认"）。24h 以上清醒是疲劳判断最关键的指标。
        /// </summary>
        [Fact]
        public void W18_D01_ContinuousAwakeBeyondLookback_IsKnownNotNull()
        {
            var f = Ok(Incident, Ship, new[] { P(Incident.AddHours(-38), Incident.AddHours(-30)) });
            Assert.Equal(TimeSpan.FromHours(24), f.AwakeLast24h);
            Assert.Equal(TimeSpan.FromHours(30), f.ContinuousAwake);
        }

        /// <summary>B7：空列表与 null 同等，回退到排班代理；无排班时 hf_empty_input。
        /// 显式 sleepRecordComplete=true 才表示确认无睡眠：ContinuousAwake=null（NoSleepWithinLimit），24h 清醒 24h。</summary>
        [Fact]
        public void NoSleepAtAll_ContinuousAwakeNull()
        {
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(Incident, Ship, new (DateTimeOffset, DateTimeOffset)[0]).ErrorCode);
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(Incident, Ship, null).ErrorCode);

            var s = WorkRestSchedule.FromRest(T0, H(48), new[] { P(23, 31), P(34, 36) }).Value;
            var proxied = Ok(Incident, Ship, new (DateTimeOffset, DateTimeOffset)[0], s);
            var viaNull = Ok(Incident, Ship, null, s);
            Assert.True(proxied.SleepIsRestProxy);
            Assert.Equal(viaNull.ContinuousAwake, proxied.ContinuousAwake);
            Assert.Equal(viaNull.SleepLast24h, proxied.SleepLast24h);

            var r = FatigueCalculator.Compute(Incident, Ship, new (DateTimeOffset, DateTimeOffset)[0], null, null, sleepRecordComplete: true);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            var f = r.Value;
            Assert.Null(f.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, f.ContinuousAwakeStatus);
            Assert.Equal(TimeSpan.FromHours(24), f.AwakeLast24h);
            Assert.False(f.SleepIsRestProxy);
        }

        // ---------- 节律低谷 [02:00, 06:00) 船时 ----------

        [Theory]
        [InlineData(1, 59, false)]
        [InlineData(2, 0, true)]
        [InlineData(5, 59, true)]
        [InlineData(6, 0, false)]
        [InlineData(14, 24, false)]
        public void CircadianLow_HalfOpenBoundaries(int h, int m, bool low)
        {
            var f = Ok(HM(24 + h, m), Ship, new[] { P(10, 12) });
            Assert.Equal(low, f.InCircadianLow);
        }

        /// <summary>偏移优先用传入的船时偏移：UTC 18:30 + 船时 +8 → 02:30 低谷；同一时刻按自身 UTC 偏移 → 18:30 非低谷。</summary>
        [Fact]
        public void TimeZone_PassedOffsetTakesPrecedence()
        {
            var inst = new DateTimeOffset(2026, 5, 11, 18, 30, 0, TimeSpan.Zero);
            var sleep = new[] { P(inst.AddHours(-10), inst.AddHours(-4)) };
            var a = Ok(inst, TimeSpan.FromHours(8), sleep);
            Assert.True(a.InCircadianLow);
            Assert.Equal(TimeSpan.FromHours(8), a.LocalOffset);
            Assert.Equal(new TimeSpan(2, 30, 0), a.IncidentLocal.TimeOfDay);
            var b = Ok(inst, null, sleep);
            Assert.False(b.InCircadianLow);
            Assert.Equal(TimeSpan.Zero, b.LocalOffset);
            // 时长与偏移无关
            Assert.Equal(a.ContinuousAwake, b.ContinuousAwake);
            Assert.Equal(a.SleepLast24h, b.SleepLast24h);
        }

        /// <summary>未传偏移时取事发时刻自带偏移（+08:00 03:00 → 低谷）。</summary>
        [Fact]
        public void TimeZone_FallsBackToIncidentOffset()
        {
            Assert.True(Ok(HM(27, 0), null, new[] { P(10, 12) }).InCircadianLow);
        }

        [Fact]
        public void TimeZone_OffsetRange()
        {
            var sleep = new[] { P(10, 12) };
            Assert.True(FatigueCalculator.Compute(Incident, TimeSpan.FromHours(14), sleep).IsSuccess);
            Assert.True(FatigueCalculator.Compute(Incident, TimeSpan.FromHours(-14), sleep).IsSuccess);
            Assert.Equal("hf_invalid_offset", FatigueCalculator.Compute(Incident, new TimeSpan(14, 1, 0), sleep).ErrorCode);
            Assert.Equal("hf_invalid_offset", FatigueCalculator.Compute(Incident, new TimeSpan(-14, -1, 0), sleep).ErrorCode);
        }

        /// <summary>非整分钟偏移（如 +08:00:30）应返回 hf_invalid_offset，而不是抛出 ArgumentException（Result 约定：失败不抛异常）。</summary>
        [Fact]
        public void W18_D02_SubMinuteOffset_ReturnsErrorNotThrow()
        {
            var ex = Record.Exception(() => FatigueCalculator.Compute(Incident, new TimeSpan(8, 0, 30), new[] { P(10, 12) }));
            Assert.Null(ex);
            Assert.Equal("hf_invalid_offset", FatigueCalculator.Compute(Incident, new TimeSpan(8, 0, 30), new[] { P(10, 12) }).ErrorCode);
        }

        // ---------- 代理 / 输入 ----------

        [Fact]
        public void Proxy_NoSleep_UsesScheduleRest()
        {
            var s = WorkRestSchedule.FromRest(T0, H(48), new[] { P(23, 31), P(34, 36) }).Value;
            var f = Ok(Incident, Ship, null, s);
            Assert.True(f.SleepIsRestProxy);
            Assert.Equal(TimeSpan.FromHours(10), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(10), f.RestLast24h);
            Assert.Equal(TimeSpan.FromHours(8), f.LongestRestLast24h);
            Assert.Equal(new TimeSpan(2, 24, 0), f.ContinuousAwake);
        }

        [Fact]
        public void Input_Errors()
        {
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(Incident, Ship, null, null).ErrorCode);
            Assert.Equal("hf_overlap", FatigueCalculator.Compute(Incident, Ship, new[] { P(10, 14), P(13, 15) }).ErrorCode);
            Assert.Equal("hf_invalid_interval", FatigueCalculator.Compute(Incident, Ship, new[] { P(10, 10) }).ErrorCode);
            Assert.Equal("hf_invalid_rules", FatigueCalculator.Compute(Incident, Ship, new[] { P(10, 12) }, null, new FatigueRules { Lookback = TimeSpan.Zero }).ErrorCode);
            Assert.Equal("hf_invalid_rules", FatigueCalculator.Compute(Incident, Ship, new[] { P(10, 12) }, null, new FatigueRules { CircadianLowStart = TimeSpan.FromHours(25) }).ErrorCode);
        }

        [Fact]
        public void Input_UnorderedSleep_SameAsOrdered()
        {
            var a = Ok(Incident, Ship, new[] { P(15, 20), P(23, 31) });
            var b = Ok(Incident, Ship, new[] { P(23, 31), P(15, 20) });
            Assert.Equal(a.ContinuousAwake, b.ContinuousAwake);
            Assert.Equal(a.SleepLast24h, b.SleepLast24h);
        }

        /// <summary>RestLast7d 只统计记录内部分（已接受：不外推）。7 天以上记录时为完整 7 天之和。</summary>
        [Fact]
        public void RestLast7d_FullRecord()
        {
            var rest = Enumerable.Range(0, 9).Select(d => P(d * 24 + 1, d * 24 + 12)).ToArray();
            var s = WorkRestSchedule.FromRest(T0, H(9 * 24), rest).Value;
            var f = Ok(H(8 * 24 + 14), Ship, null, s);
            Assert.Equal(TimeSpan.FromHours(77), f.RestLast7d);
        }

        /// <summary>
        /// 以排班代理睡眠且排班只覆盖事发前 12h（其中休 4h）时，记录外 12h 不应被当作"清醒"计入 AwakeLast24h（20h），
        /// 或至少应输出覆盖范围/截断标记（与 SleepIsRestProxy 同理）；RestLast7d 同样缺少"记录不足 7 天"标记。
        /// </summary>
        [Fact]
        public void W18_D03_UnrecordedTimeNotCountedAsAwake_OrCoverageFlagged()
        {
            var s = WorkRestSchedule.FromRest(Incident.AddHours(-12), Incident, new[] { P(Incident.AddHours(-10), Incident.AddHours(-6)) }).Value;
            var f = Ok(Incident, Ship, null, s);
            bool hasCoverage = typeof(FatigueIndicators).GetProperties().Any(p => p.Name.Contains("Coverage") || p.Name.Contains("Truncated") || p.Name.Contains("Covered"));
            Assert.True(hasCoverage || f.AwakeLast24h <= TimeSpan.FromHours(8), "AwakeLast24h=" + f.AwakeLast24h);
        }

        [Fact]
        public void Determinism()
        {
            var sleep = new[] { P(23, 31), P(15, 20) };
            var a = Ok(Incident, Ship, sleep);
            var b = Ok(Incident, Ship, sleep.Reverse().ToArray());
            Assert.Equal(
                string.Join("|", a.AwakeLast24h, a.SleepLast24h, a.ContinuousAwake, a.RestLast24h, a.RestLast7d, a.LongestRestLast24h, a.InCircadianLow, a.IncidentLocal),
                string.Join("|", b.AwakeLast24h, b.SleepLast24h, b.ContinuousAwake, b.RestLast24h, b.RestLast7d, b.LongestRestLast24h, b.InCircadianLow, b.IncidentLocal));
        }
    }
}
