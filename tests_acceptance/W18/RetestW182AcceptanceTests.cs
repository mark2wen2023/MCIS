using System;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    // Independently authored synthetic acceptance fixtures; no real crew data.
    public sealed class RetestW182AcceptanceTests
    {
        private static bool At(RestHourViolation v, RestRule rule, double hour) =>
            v.Rule == rule && v.ViolatingFrom <= H(hour) && H(hour) <= v.ViolatingTo;

        [Fact]
        public void HeadEdgeUncertaintySurvivesNeighbouringDefiniteViolation()
        {
            var rep = Check(Rest(48, P(T0, T0.AddMinutes(359)), P(38, 44)), RestOnly());
            Assert.Contains(rep.InsufficientData, v => At(v, RestRule.LongestRest, 0));
            Assert.DoesNotContain(rep.Violations, v => At(v, RestRule.LongestRest, 0));
            Assert.Contains(rep.Violations, v => v.Rule == RestRule.LongestRest);
        }

        [Fact]
        public void UnknownTailIsNotLostInDefiniteGroup()
        {
            var input = WorkRestSchedule.Create(T0, H(48), new[] {
                new DutyInterval(T0, H(4), DutyKind.Work),
                new DutyInterval(H(4), H(10), DutyKind.Rest),
                new DutyInterval(H(10), H(42).AddMinutes(1), DutyKind.Work)
            });
            Assert.True(input.IsSuccess);
            var rep = Check(input.Value, RestOnly());
            Assert.Contains(rep.InsufficientData, v => At(v, RestRule.LongestRest, 24));
            Assert.DoesNotContain(rep.Violations, v => At(v, RestRule.LongestRest, 24));
            Assert.Contains(rep.Violations, v => At(v, RestRule.LongestRest, 10));
        }

        [Fact]
        public void SplitRuleTailRemainsInsufficientAlongsideDefiniteWindows()
        {
            var rep = Check(Rest(48, P(2,6), P(10,14), P(18,22), P(26,30), P(34,38), P(44,48)), RestOnly());
            Assert.Contains(rep.Violations, v => At(v, RestRule.RestSplit, 0));
            Assert.Contains(rep.InsufficientData, v => At(v, RestRule.RestSplit, 24));
            Assert.DoesNotContain(rep.Violations, v => At(v, RestRule.RestSplit, 24));
        }

        [Fact]
        public void RecordEdgeDisclosureMatchesArchitectureRulingExactly()
        {
            var rep = Check(Rest(24, P(1,11)), RestOnly());
            Assert.Contains("拆分规则另评估记录首窗口和记录尾−24h 窗口；被记录边界截断的休息段按可见长度计，并标注数据不足。", rep.Assumptions);
        }
    }
}
