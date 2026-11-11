using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class Yangze22AcceptanceTests
    {
        [Fact]
        public void ReportedScenarioNumbers_MatchAnnouncement()
        {
            Yangze22Result result = RunDefault();
            ScenarioResult s0 = result.Find("S0");
            ScenarioResult y1 = result.Find("Y1");
            ScenarioResult y5 = result.Find("Y5");
            ScenarioResult both = result.Find("Y1+Y5");
            ScenarioResult y4 = result.Find("Y4");

            Assert.Equal(ScenarioVerdict.Collision, s0.Verdict);
            Assert.True(s0.TcSeconds.HasValue);
            // SimTime 0 = 21:58:30；默认截断+天线后 22:02:00.12 = 210.12 s
            Assert.InRange(s0.TcSeconds.Value, 209.8, 210.5);
            Assert.StartsWith("22:02:00.", s0.TcLocalText);
            Assert.NotNull(s0.Geometry);
            Assert.Equal(Yangze22Case.VegaDreamId, s0.Geometry.StrikingVesselId);
            Assert.Equal(Yangze22Case.Yangze22Id, s0.Geometry.StruckVesselId);
            Assert.Equal("右舷", s0.Geometry.StruckSide);
            Assert.InRange(s0.Geometry.CollisionAngleDeg, 68.5, 69.5);
            Assert.InRange(s0.Geometry.ContactFromStruckBowM, 90.0, 103.0);

            Assert.Equal(ScenarioVerdict.NearMiss, y1.Verdict);
            Assert.False(y1.Collision);
            Assert.InRange(y1.MinClearanceM, 183.0, 186.0);

            Assert.Equal(ScenarioVerdict.Avoided, y5.Verdict);
            Assert.False(y5.Collision);
            Assert.InRange(y5.MinClearanceM, 230.0, 250.0);

            Assert.Equal(ScenarioVerdict.Avoided, both.Verdict);
            Assert.False(both.Collision);
            // 全程全局最小：上轮独立核算 292.4 m，本轮 C# 原样跑 292.45 m。窗口按独立值设定。
            Assert.InRange(both.MinClearanceM, 290.0, 295.0);

            Assert.Equal(ScenarioVerdict.NearMiss, y4.Verdict);
            Assert.False(y4.Collision);
            Assert.InRange(y4.MinClearanceM, 25.0, 40.0);
        }

        [Fact]
        public void EveryResult_HasDisclaimerAndSourcedValues()
        {
            Yangze22Result result = RunDefault();
            Assert.All(result.Results, r =>
            {
                Assert.Equal(WhatIfAssumptions.DisclaimerText, r.Disclaimer);
                Assert.Contains("仅供分析参考", r.Disclaimer);
                Assert.NotEmpty(r.Assumptions);
                Assert.NotEmpty(r.Inputs);
                Assert.All(r.Inputs, v =>
                {
                    Assert.False(string.IsNullOrWhiteSpace(v.Name));
                    Assert.False(string.IsNullOrWhiteSpace(v.Reference));
                    Assert.True(Enum.IsDefined(typeof(ValueSource), v.Source));
                    Assert.NotEqual(ValueSource.Fictional, v.Source);
                });
            });
            Assert.Contains(result.Original.Inputs, v => v.Name.Contains("船长") && v.Source == ValueSource.ReportDirect);
            Assert.Contains(result.Original.Inputs, v => v.Name.Contains("K") && v.Source == ValueSource.Estimated);
        }

        [Fact]
        public void S0_IndependentGeometry_AgreesOnAngleAndSide()
        {
            Yangze22Result result = RunDefault();
            ScenarioResult s0 = result.Original;
            CollisionGeometry g = s0.Geometry;
            Assert.NotNull(g);
            KinematicState striking = s0.Tracks[g.StrikingVesselId].SampleAt(g.TcSeconds);
            KinematicState struck = s0.Tracks[g.StruckVesselId].SampleAt(g.TcSeconds);
            double angle = W14AccFixture.AcuteHeadingAngleDeg(striking.HeadingDeg, struck.HeadingDeg);
            Assert.InRange(Math.Abs(g.CollisionAngleDeg - angle), 0.0, 0.15);
            Assert.Equal("右舷", W14AccFixture.IndependentStruckSide(struck,
                W14AccFixture.ClosestPointContact(
                    W14AccFixture.BoxOf(striking, s0.Tracks[g.StrikingVesselId].LoaM, s0.Tracks[g.StrikingVesselId].BeamM),
                    W14AccFixture.BoxOf(struck, s0.Tracks[g.StruckVesselId].LoaM, s0.Tracks[g.StruckVesselId].BeamM))));
        }

        [Fact]
        public void S0_DeviationFromReport_IsAsDisclosed()
        {
            Yangze22Inputs inputs = W14AccFixture.LoadYangzeInputs();
            Yangze22Result result = Yangze22Case.Run(W14AccFixture.ReadYangzeTrackLines(), inputs);
            double reportTc = (inputs.CollisionTimeBeijing - inputs.SimEpochLocal).TotalSeconds;
            Assert.Equal(204.0, reportTc);
            ScenarioResult s0 = result.Original;
            Assert.True(s0.Collision);
            double late = s0.TcSeconds.Value - reportTc;
            // 默认设定（截断 + VEGA 0.375L）比报告晚约 6.1 s；敏感性区间约 4.8–7.5 s
            Assert.InRange(late, 5.5, 7.0);
            Assert.InRange(s0.Geometry.CollisionAngleDeg, 68.5, 69.5);
            Assert.InRange(Math.Abs(s0.Geometry.CollisionAngleDeg - 70.0), 0.5, 1.5);
            Assert.Contains("偏差", result.OriginalDeviation);
            Assert.Contains("70", result.OriginalDeviation);

            // 报告时刻尚未接触；默认设定下真实净距约 30 m（敏感性 23–37 m）
            double clearAtReport = OrientedBoundingBox.Clearance(
                s0.Tracks[Yangze22Case.Yangze22Id].ToBodyState(reportTc).Obb,
                s0.Tracks[Yangze22Case.VegaDreamId].ToBodyState(reportTc).Obb);
            Assert.True(clearAtReport > 0.0,
                "报告时刻 t=204 s 的 OBB 应尚未接触，净距=" + clearAtReport);
            Assert.InRange(clearAtReport, 23.0, 37.0);
        }

        [Fact]
        public void DroppingPostCollisionPoints_ChangesS0ContactTime()
        {
            // W14.1：默认已截断。比较截断开 / 关（其余默认，含天线改正）。
            string[] lines = W14AccFixture.ReadYangzeTrackLines();
            Yangze22Result truncated = Yangze22Case.Run(lines, W14AccFixture.LoadYangzeInputs(300.0, true));
            Yangze22Result full = Yangze22Case.Run(lines, W14AccFixture.LoadYangzeInputs(300.0, false));

            Assert.True(truncated.Original.Collision);
            Assert.True(full.Original.Collision);

            KinematicState fullAfter = full.Original.Tracks[Yangze22Case.Yangze22Id].SampleAt(230);
            KinematicState trimAfter = truncated.Original.Tracks[Yangze22Case.Yangze22Id].SampleAt(230);
            double de = fullAfter.EastM - trimAfter.EastM;
            double dn = fullAfter.NorthM - trimAfter.NorthM;
            double moved = Math.Sqrt(de * de + dn * dn);
            Assert.True(moved > 5.0,
                "截断开/关时 t=230 s 的 YANGZE 22 位置应不同，实际位移差 " + moved.ToString("F1") + " m");

            Assert.True(Math.Abs(full.Original.TcSeconds.Value - truncated.Original.TcSeconds.Value) > 1.0,
                "截断开/关时 S0 接触时刻应不同：开=" + truncated.Original.TcSeconds +
                " 关=" + full.Original.TcSeconds);
        }

        [Fact]
        public void ReasonableAntennaOffset_CanReduceReportTimeClearance()
        {
            // 不改被测代码：在 S0 航迹上按船首向施加“天线相对船中心”偏移，观察报告时刻净距。
            Yangze22Result result = RunDefault();
            ScenarioResult s0 = result.Original;
            const double reportTc = 204.0;
            KinematicState y0 = s0.Tracks[Yangze22Case.Yangze22Id].SampleAt(reportTc);
            KinematicState v0 = s0.Tracks[Yangze22Case.VegaDreamId].SampleAt(reportTc);
            double loaY = s0.Tracks[Yangze22Case.Yangze22Id].LoaM;
            double beamY = s0.Tracks[Yangze22Case.Yangze22Id].BeamM;
            double loaV = s0.Tracks[Yangze22Case.VegaDreamId].LoaM;
            double beamV = s0.Tracks[Yangze22Case.VegaDreamId].BeamM;
            double baseClear = OrientedBoundingBox.Clearance(
                W14AccFixture.BoxOf(y0, loaY, beamY),
                W14AccFixture.BoxOf(v0, loaV, beamV));

            double bestClear = baseClear;
            double bestY = 0, bestV = 0;
            bool contact = false;
            // 天线多在居住舱、船中偏后：forwardOfCenter 为负。扫描 -0.40L ~ +0.10L。
            foreach (double yFrac in new[] { -0.40, -0.35, -0.30, -0.25, -0.20, -0.15, -0.10, 0.0, 0.10 })
            {
                foreach (double vFrac in new[] { -0.40, -0.35, -0.30, -0.25, -0.20, -0.15, -0.10, 0.0, 0.10 })
                {
                    KinematicState y = W14AccFixture.ShiftAntennaToCenter(y0, yFrac * loaY, 0);
                    KinematicState v = W14AccFixture.ShiftAntennaToCenter(v0, vFrac * loaV, 0);
                    double c = OrientedBoundingBox.Clearance(
                        W14AccFixture.BoxOf(y, loaY, beamY),
                        W14AccFixture.BoxOf(v, loaV, beamV));
                    if (c < bestClear)
                    {
                        bestClear = c;
                        bestY = yFrac;
                        bestV = vFrac;
                    }
                    if (c <= 0.0) contact = true;
                }
            }

            Assert.True(bestClear < baseClear - 5.0 || contact,
                "合理天线偏移应能缩小报告时刻净距或促成接触。基准=" +
                baseClear.ToString("F1") + " m，最佳=" + bestClear.ToString("F1") +
                " m（YANGZE fwd=" + bestY + "L，VEGA fwd=" + bestV + "L）");
        }

        [Fact]
        public void EvaluationIsDeterministic()
        {
            Yangze22Inputs inputs = W14AccFixture.LoadYangzeInputs();
            string[] lines = W14AccFixture.ReadYangzeTrackLines();
            Yangze22Result a = Yangze22Case.Run(lines, inputs);
            Yangze22Result b = Yangze22Case.Run(lines, inputs);
            Assert.Equal(a.Original.TcSeconds, b.Original.TcSeconds);
            Assert.Equal(a.Find("Y1").MinClearanceM, b.Find("Y1").MinClearanceM);
            Assert.Equal(a.OriginalDeviation, b.OriginalDeviation);
        }

        [Fact]
        public void Y1AndY5_QualitativeDirectionMatchesRealCases()
        {
            Yangze22Result result = RunDefault();
            Assert.True(result.Find("Y1").MinClearanceM > result.Find("S0").MinClearanceM);
            Assert.NotEqual(ScenarioVerdict.Collision, result.Find("Y1").Verdict);
            Assert.NotEqual(ScenarioVerdict.Collision, result.Find("Y5").Verdict);
            Assert.NotEqual(ScenarioVerdict.Collision, result.Find("Y1+Y5").Verdict);
        }

        private static Yangze22Result RunDefault()
        {
            return Yangze22Case.Run(W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
        }

        private static string[] TrimAfterReportCollision()
        {
            DateTimeOffset cut = new DateTimeOffset(2024, 12, 30, 22, 1, 54, TimeSpan.FromHours(8));
            List<string> kept = new List<string>();
            string[] lines = W14AccFixture.ReadYangzeTrackLines();
            kept.Add(lines[0]);
            for (int i = 1; i < lines.Length; i++)
            {
                string line = lines[i];
                if (string.IsNullOrWhiteSpace(line) || line.StartsWith("#", StringComparison.Ordinal))
                {
                    kept.Add(line);
                    continue;
                }
                // 简单按 ISO 时间字段过滤：保留 <= 22:01:54 的数据行。
                int first = line.IndexOf("2024-12-30T", StringComparison.Ordinal);
                if (first < 0)
                {
                    kept.Add(line);
                    continue;
                }
                int end = line.IndexOf(',', first);
                string token = end > first ? line.Substring(first, end - first) : line.Substring(first);
                DateTimeOffset time;
                if (DateTimeOffset.TryParse(token, out time) && time > cut)
                {
                    continue;
                }
                kept.Add(line);
            }
            return kept.ToArray();
        }
    }
}
