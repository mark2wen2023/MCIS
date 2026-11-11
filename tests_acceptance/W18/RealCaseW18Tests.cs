using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    /// <summary>
    /// 真实案例（公开调查报告，Mark 已确认可直接使用）：海力5 / WAN HAI A17 与 YANGZE 22 / VEGA DREAM。
    /// REAL_CASES.md §5：两案均无实际工休记录，工休检查与疲劳计算应返回“数据不足”，
    /// 不得根据丁**白班作息安排凭空判出疲劳/工休违规。
    /// </summary>
    public sealed class RealCaseW18Tests
    {
        private static string CasePath(string folder) => Path.Combine(RepoRoot(), "reports", folder, "case.json");

        [Fact]
        public void Haili5_NoWorkRestRecords_ReturnsInsufficientData()
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(CasePath("haili5")));
            Assert.False(doc.RootElement.GetProperty("isFictionalDemo").GetBoolean());
            var incident = DateTimeOffset.Parse(doc.RootElement.GetProperty("incidentTimeBeijing").GetString());
            Assert.Equal(new DateTimeOffset(2025, 10, 25, 19, 54, 32, TimeSpan.FromHours(8)), incident);

            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(incident, TimeSpan.FromHours(8), null).ErrorCode);
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(incident, TimeSpan.FromHours(8), Array.Empty<(DateTimeOffset, DateTimeOffset)>()).ErrorCode);
            Assert.Equal("hf_empty_input", new RestHourChecker().Check(null).ErrorCode);
        }

        [Fact]
        public void Yangze22_PlannedDayWatchOnly_IsInsufficient_NotAConclusiveViolation()
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(CasePath("yangze22")));
            Assert.False(doc.RootElement.GetProperty("isFictionalDemo").GetBoolean());
            var incident = DateTimeOffset.Parse(doc.RootElement.GetProperty("incidentTimeBeijing").GetString());
            Assert.Equal(new DateTimeOffset(2024, 12, 30, 22, 1, 54, TimeSpan.FromHours(8)), incident);

            var ding = doc.RootElement.GetProperty("personnel").GetProperty("yangze22").EnumerateArray()
                .First(p => p.GetProperty("name").GetString() == "丁**");
            Assert.Equal("白班水手", ding.GetProperty("regularSchedule").GetProperty("type").GetString());
            var atSea = ding.GetProperty("regularSchedule").GetProperty("atSea").EnumerateArray().Select(x => x.GetString()).ToArray();
            Assert.Equal(new[] { "0800-1200", "1300-1700" }, atSea);

            // 无实际睡眠/工休记录 → 疲劳与工休均数据不足
            Assert.Equal("hf_empty_input", FatigueCalculator.Compute(incident, TimeSpan.FromHours(8), null).ErrorCode);
            Assert.Equal("hf_empty_input", new RestHourChecker().Check(null).ErrorCode);

            // 记录取事发前约 46h，只把报告里的白班工作时段标为 Watch，其余保持 Unknown（不是“其余即休息”）
            var recordStart = new DateTimeOffset(2024, 12, 29, 0, 0, 0, TimeSpan.FromHours(8));
            var day = new DateTimeOffset(2024, 12, 30, 0, 0, 0, TimeSpan.FromHours(8));
            var planned = WorkRestSchedule.Create(recordStart, incident, new[]
            {
                new DutyInterval(day.AddHours(8), day.AddHours(12), WorkKind.Watch),
                new DutyInterval(day.AddHours(13), day.AddHours(17), WorkKind.Watch)
            }).Value;
            Assert.True(planned.UnknownPeriods().Count > 0);
            var rep = Check(planned);
            Assert.False(rep.IsConclusive);
            Assert.True(rep.InsufficientData.Count > 0);
            // 不得把作息安排当成实测记录，据此给出已确认的工休违规
            Assert.Empty(rep.Violations);
            Assert.False(rep.HasViolations);
        }
    }
}
