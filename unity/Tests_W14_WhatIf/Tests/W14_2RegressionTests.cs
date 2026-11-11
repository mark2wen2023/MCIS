using System;
using System.Collections.Generic;
using System.Linq;
using Xunit;
using Mcis.Domain.Common;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Mcis.Simulation.WhatIf.Demo;

namespace Mcis.Tests.W14
{
    /// <summary>W14.2 回归：D03 船首对船首、D04 全程全局最小净距、D05 对比表“临界”。</summary>
    public class W14_2RegressionTests
    {
        private const double Kn = 1852.0 / 3600.0;

        // ---------- 共用构造 ----------

        /// <summary>本船静止、首向北（中心原点）；他船首向西从东侧驶来，中心沿 north=offsetNorth 横撞。</summary>
        private static WhatIfSetup TSetup(double offsetNorth, double ownDisplacement = 9000.0, double tgtDisplacement = 9000.0)
        {
            WhatIfVessel own = WhatIfVessel.FromStates("Own", TestUtil.Params(loaM: 120, beamM: 16, displacementTons: ownDisplacement),
                new[] { new KinematicState(0, 0, 0, 0, 0), new KinematicState(80, 0, 0, 0, 0) }, "Own");
            double v = 12 * Kn;
            WhatIfVessel tgt = WhatIfVessel.FromStates("Tgt", TestUtil.Params(loaM: 100, beamM: 16, displacementTons: tgtDisplacement),
                new[] { new KinematicState(0, 400, offsetNorth, 270, 12), new KinematicState(80, 400 - v * 80, offsetNorth, 270, 12) }, "Tgt");
            return new WhatIfSetup(new[] { own, tgt }, "Own", "Tgt", 0, 80);
        }

        private static WhatIfVessel Straight(string id, double e0, double n0, double hdg, double kn, double loa, double beam, double end)
        {
            double rad = hdg * Math.PI / 180.0;
            double d = kn * Kn * end;
            return WhatIfVessel.FromStates(id, TestUtil.Params(loaM: loa, beamM: beam),
                new[]
                {
                    new KinematicState(0, e0, n0, hdg, kn),
                    new KinematicState(end, e0 + Math.Sin(rad) * d, n0 + Math.Cos(rad) * d, hdg, kn)
                }, id);
        }

        private static double Bow(CounterfactualTrack track, double t, EnuPosition contact)
        {
            KinematicState s = track.SampleAt(t);
            double rad = s.HeadingDeg * Math.PI / 180.0;
            double be = s.EastM + Math.Sin(rad) * track.LoaM * 0.5;
            double bn = s.NorthM + Math.Cos(rad) * track.LoaM * 0.5;
            return Math.Sqrt((be - contact.EastM) * (be - contact.EastM) + (bn - contact.NorthM) * (bn - contact.NorthM));
        }

        private static double BruteMinClearance(ScenarioResult r, string a, string b, double from, double to, double step)
        {
            CounterfactualTrack ta = r.Tracks[a];
            CounterfactualTrack tb = r.Tracks[b];
            double best = double.PositiveInfinity;
            for (double t = from; t <= to + 1e-9; t += step)
            {
                double c = OrientedBoundingBox.Clearance(Box(ta, t), Box(tb, t));
                if (c < best) best = c;
            }
            return best;
        }

        private static OrientedBoundingBox Box(CounterfactualTrack track, double t)
        {
            KinematicState s = track.SampleAt(t);
            return OrientedBoundingBox.FromVessel(new EnuPosition(s.EastM, s.NorthM, 0), s.HeadingDeg, (float)track.LoaM, (float)track.BeamM);
        }

        private static ScenarioResult Synthetic(string id, bool collision, double clearanceM, double safeM = double.NaN)
        {
            ScenarioVerdict verdict = collision
                ? ScenarioVerdict.Collision
                : clearanceM < (double.IsNaN(safeM) ? 185.2 : safeM) ? ScenarioVerdict.NearMiss : ScenarioVerdict.Avoided;
            return new ScenarioResult(id, id, id, null, null, 0.1, 10, 0.05, collision ? 0.0 : clearanceM, collision,
                collision ? (double?)5.0 : null, collision ? "T+5s" : "—", verdict, ScenarioResult.VerdictToText(verdict),
                null, null, null, null, null, double.NaN, safeM);
        }

        private static string Row(string md, string id)
        {
            return md.Split('\n').FirstOrDefault(l => l.StartsWith("| " + id + " |", StringComparison.Ordinal)) ?? string.Empty;
        }

        // ---------- D03 ----------

        [Fact]
        public void D03_Threshold_IsMax10mOr5PercentLoa()
        {
            Assert.Equal(10.0, CollisionGeometry.BowToBowThresholdM(98.0));
            Assert.Equal(10.0, CollisionGeometry.BowToBowThresholdM(200.0));
            TestUtil.AssertNear(15.0, CollisionGeometry.BowToBowThresholdM(300.0), 1e-12);
        }

        [Fact]
        public void D03_DemoS0_IsBowToBow_WithDisclosedBowDistances()
        {
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(WhatIfDemoFixture.CreateSetup(), WhatIfScenario.Original());
            CollisionGeometry g = s0.Geometry;
            Assert.True(g.IsBowToBow);
            Assert.Equal(string.Empty, g.StrikingVesselId);
            Assert.Equal(string.Empty, g.StruckVesselId);
            // 参考：Mary 距接触点 8.8 m、Lily 6.8 m，阈值均为 10 m。
            double dMary = g.OwnVesselId == WhatIfDemoFixture.MaryId ? g.OwnBowToContactM : g.TargetBowToContactM;
            double dLily = g.OwnVesselId == WhatIfDemoFixture.LilyId ? g.OwnBowToContactM : g.TargetBowToContactM;
            TestUtil.AssertNear(8.8, dMary, 0.1, "Mary 船首距接触点");
            TestUtil.AssertNear(6.8, dLily, 0.1, "Lily 船首距接触点");
            TestUtil.AssertNear(dMary, Bow(s0.Tracks[WhatIfDemoFixture.MaryId], g.TcSeconds, g.ContactPointEnu), 1e-6, "独立复算 Mary");
            TestUtil.AssertNear(dLily, Bow(s0.Tracks[WhatIfDemoFixture.LilyId], g.TcSeconds, g.ContactPointEnu), 1e-6, "独立复算 Lily");
            Assert.Equal(10.0, g.OwnBowToBowThresholdM);
            Assert.Equal(10.0, g.TargetBowToBowThresholdM);
            Assert.Contains("船首对船首", g.Description);
            Assert.Contains("不指定单一撞击船", g.Description);
            Assert.DoesNotContain("船首撞", g.Description);
        }

        [Fact]
        public void D03_TCollisionMidship_ClosestBowStrikes()
        {
            ScenarioResult r = ScenarioEvaluator.Evaluate(TSetup(0.0), WhatIfScenario.Original());
            CollisionGeometry g = r.Geometry;
            Assert.False(g.IsBowToBow);
            Assert.Equal(ImpactKind.BowStrike, g.Kind);
            Assert.Equal("Tgt", g.StrikingVesselId);
            Assert.Equal("Own", g.StruckVesselId);
            Assert.True(g.TargetBowToContactM < g.TargetBowToBowThresholdM);
            Assert.True(g.OwnBowToContactM > g.OwnBowToBowThresholdM);
            Assert.True(g.TargetBowToContactM < g.OwnBowToContactM);
        }

        [Fact]
        public void D03_DisplacementNoLongerDecides()
        {
            // T 型：本船排水量极大也不改变撞击船。
            ScenarioResult heavy = ScenarioEvaluator.Evaluate(TSetup(0.0, ownDisplacement: 500000), WhatIfScenario.Original());
            Assert.Equal("Tgt", heavy.Geometry.StrikingVesselId);
            // 船首对船首：交换排水量量级，仍为船首对船首。
            ScenarioResult light = ScenarioEvaluator.Evaluate(TSetup(0.0, tgtDisplacement: 500000), WhatIfScenario.Original());
            Assert.Equal("Tgt", light.Geometry.StrikingVesselId);
        }

        [Fact]
        public void D03_ShoulderHit_DecisionFollowsThresholdRule()
        {
            // 他船撞本船船首肩部：结论必须与“两船船首距离都小于阈值”规则一致（独立复算距离）。
            foreach (double offset in new[] { 40.0, 52.0, 58.0, 62.0 })
            {
                ScenarioResult r = ScenarioEvaluator.Evaluate(TSetup(offset), WhatIfScenario.Original());
                Assert.True(r.Collision, "offset=" + offset);
                CollisionGeometry g = r.Geometry;
                double dOwn = Bow(r.Tracks["Own"], g.TcSeconds, g.ContactPointEnu);
                double dTgt = Bow(r.Tracks["Tgt"], g.TcSeconds, g.ContactPointEnu);
                bool expectBowToBow = dOwn < 10.0 && dTgt < 10.0;
                Assert.Equal(expectBowToBow, g.IsBowToBow);
                if (!expectBowToBow)
                {
                    Assert.Equal(dOwn <= dTgt ? "Own" : "Tgt", g.StrikingVesselId);
                }
            }
            Assert.False(ScenarioEvaluator.Evaluate(TSetup(40.0), WhatIfScenario.Original()).Geometry.IsBowToBow);
            Assert.True(ScenarioEvaluator.Evaluate(TSetup(62.0), WhatIfScenario.Original()).Geometry.IsBowToBow);
        }

        [Fact]
        public void D03_ComparisonContactPart_ShowsBowToBow()
        {
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(WhatIfDemoFixture.CreateSetup(), WhatIfDemoFixture.Scenarios());
            string md = ScenarioComparison.Build(results).ToMarkdown();
            Assert.Contains("船首对船首", Row(md, "S0"));
            Assert.Contains("撞击船判定", md);
        }

        [Fact]
        public void D03_YangzeS0_StillVegaStrikesYangzeStarboard()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            CollisionGeometry g = result.Original.Geometry;
            Assert.False(g.IsBowToBow);
            Assert.Equal(Yangze22Case.VegaDreamId, g.StrikingVesselId);
            Assert.Equal("右舷", g.StruckSide);
        }

        // ---------- D04 ----------

        [Fact]
        public void D04_GlobalMinimum_FindsDistantDeeperMinimum()
        {
            // 两个局部极小：t=20 处 5.0，t=170 处 1.0（窄谷），全局应为 1.0。
            Func<double, double> f = t => Math.Min(5.0 + 0.01 * (t - 20) * (t - 20), 1.0 + 4.0 * (t - 170.123) * (t - 170.123));
            double arg;
            double v = ScenarioEvaluator.GlobalMinimum(0, 200, f, 0.5, 0.02, out arg);
            TestUtil.AssertNear(1.0, v, 1e-5, "全局最小值");
            TestUtil.AssertNear(170.123, arg, 2e-3, "全局最小时刻");
        }

        [Fact]
        public void D04_GlobalMinimum_HandlesEndpointsAndConstants()
        {
            double arg;
            TestUtil.AssertNear(0.0, ScenarioEvaluator.GlobalMinimum(0, 10, t => t, 0.5, 0.02, out arg), 1e-12);
            TestUtil.AssertNear(0.0, arg, 1e-12);
            TestUtil.AssertNear(-10.0, ScenarioEvaluator.GlobalMinimum(0, 10, t => -t, 0.5, 0.02, out arg), 1e-12);
            TestUtil.AssertNear(10.0, arg, 1e-12);
            TestUtil.AssertNear(3.0, ScenarioEvaluator.GlobalMinimum(0, 10, t => 3.0, 0.5, 0.02, out arg), 1e-12);
            TestUtil.AssertNear(7.0, ScenarioEvaluator.GlobalMinimum(0, 0.3, t => 7.0 + t, 0.5, 0.02, out arg), 1e-12);
            Assert.Throws<ArgumentOutOfRangeException>(() => ScenarioEvaluator.GlobalMinimum(0, 1, t => t, 0.0, 0.02, out arg));
        }

        [Fact]
        public void D04_ObliquePass_ReportsGlobalNotCenterCpaWindow()
        {
            // 与验收 Ruling7b 同构：长船静止，他船斜向掠过船首；OBB 最小点距中心 CPA 约 20 s。
            WhatIfVessel own = Straight("Own", 0, 0, 0, 0.0, 300, 20, 200);
            WhatIfVessel tgt = Straight("Tgt", -50, 470, 135, 10, 80, 16, 200);
            WhatIfSetup setup = new WhatIfSetup(new[] { own, tgt }, "Own", "Tgt", 0, 200);
            ScenarioResult r = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.False(r.Collision);
            double brute = BruteMinClearance(r, "Own", "Tgt", 0, 200, 0.01);
            Assert.InRange(r.MinClearanceM, brute - 0.05, brute + 0.01);
            TestUtil.AssertNear(175.8, r.MinClearanceM, 0.3, "全程最小（验收 175.8 m）");
            Assert.Equal(ScenarioVerdict.NearMiss, r.Verdict);
            // 本船船首角点到他船舷侧（沿航向滑过）的距离在一段时间内为常数，最小值是平台，时刻不唯一（验收报 50.9 s）；
            // 只校验报出时刻处的净距等于报出值，且该时刻在平台内。
            double atReported = OrientedBoundingBox.Clearance(Box(r.Tracks["Own"], r.MinClearanceTimeSeconds), Box(r.Tracks["Tgt"], r.MinClearanceTimeSeconds));
            TestUtil.AssertNear(r.MinClearanceM, atReported, 1e-9, "报出时刻净距");
            Assert.InRange(r.MinClearanceTimeSeconds, 40.0, 60.0);
            Assert.True(Math.Abs(r.MinClearanceTimeSeconds - r.MinDistanceTimeSeconds) > 2.0, "最小净距时刻不在中心 CPA ±2 s 内");
        }

        [Fact]
        public void D04_CollisionClearanceTime_IsContactTime()
        {
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(WhatIfDemoFixture.CreateSetup(), WhatIfScenario.Original());
            Assert.Equal(0.0, s0.MinClearanceM);
            Assert.Equal(s0.TcSeconds.Value, s0.MinClearanceTimeSeconds);
            TestUtil.AssertNear(185.2, s0.SafeDistanceM, 1e-9);
        }

        [Fact]
        public void D04_AllDemoScenarios_MatchBruteForceScan()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            foreach (ScenarioResult r in ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios()).Where(x => !x.Collision))
            {
                double brute = BruteMinClearance(r, setup.OwnVesselId, setup.TargetVesselId, setup.StartSeconds, setup.EndSeconds, 0.05);
                Assert.InRange(r.MinClearanceM, brute - 0.5, brute + 1e-6);
            }
        }

        [Fact]
        public void D04_Yangze_AllScenariosGlobal_AndReferenceValues()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            foreach (ScenarioResult r in result.Results.Where(x => !x.Collision))
            {
                double end = r.Tracks[Yangze22Case.Yangze22Id].States.Last().TimeSeconds;
                double brute = BruteMinClearance(r, Yangze22Case.Yangze22Id, Yangze22Case.VegaDreamId, 0, end, 0.05);
                Assert.InRange(r.MinClearanceM, brute - 0.5, brute + 1e-6);
            }
            // 参考值（验收全程扫描）：Y1+Y5 292.4 m、Y4 29.8 m；不为对齐参考调参，容差覆盖扫描步长差异。
            TestUtil.AssertNear(292.4, result.Find("Y1+Y5").MinClearanceM, 0.5, "Y1+Y5 全程最小");
            TestUtil.AssertNear(29.8, result.Find("Y4").MinClearanceM, 0.3, "Y4 全程最小");
            Assert.Equal(ScenarioVerdict.Avoided, result.Find("Y1+Y5").Verdict);
            Assert.Equal(ScenarioVerdict.NearMiss, result.Find("Y4").Verdict);
        }

        // ---------- D05 ----------

        [Fact]
        public void D05_Yangze_Y1MarkedCriticalWithAntennaRange()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            ComparisonRow y1 = result.Comparison.Rows.First(r => r.ScenarioId == "Y1");
            Assert.True(y1.IsCritical);
            Assert.Equal(3, y1.Sensitivity.Count);
            Assert.Contains("VEGA 0.35L", y1.SensitivityRangeText);
            Assert.Contains("VEGA 0.40L", y1.SensitivityRangeText);
            Assert.Contains("跨越安全线", y1.CriticalReason);
            Assert.Contains("距安全线", y1.CriticalReason);
            string md = result.Comparison.ToMarkdown();
            string row = Row(md, "Y1");
            Assert.Contains("险情（临界）", row);
            Assert.Contains("VEGA 0.35L 无碰撞", row);
            Assert.Contains("Y1 临界：", md);
            // 其他情景离安全线远且敏感性不跨线，不标临界。
            foreach (string id in new[] { "S0", "Y5", "Y1+Y5", "Y4" })
            {
                Assert.False(result.Comparison.Rows.First(r => r.ScenarioId == id).IsCritical, id);
                Assert.DoesNotContain("临界", Row(md, id));
            }
        }

        [Fact]
        public void D05_MarginRule_UsesConfiguredSafeLine()
        {
            ScenarioResult s0 = Synthetic("S0", true, 0.0);
            ComparisonTable t = ScenarioComparison.Build(new[]
            {
                s0,
                Synthetic("A", false, 181.0),           // 差 4.2 → 临界
                Synthetic("B", false, 189.0),           // 差 3.8 → 临界（无碰撞侧）
                Synthetic("C", false, 179.0),           // 差 6.2 → 否
                Synthetic("D", false, 197.0, 200.0),    // 配置安全线 200：差 3 → 临界
                Synthetic("E", false, 185.0, 200.0),    // 配置安全线 200：差 15 → 否
            });
            Assert.False(t.Rows[0].IsCritical);
            Assert.True(t.Rows[1].IsCritical);
            Assert.True(t.Rows[2].IsCritical);
            Assert.False(t.Rows[3].IsCritical);
            Assert.True(t.Rows[4].IsCritical);
            Assert.Equal(200.0, t.Rows[4].SafeDistanceM);
            Assert.False(t.Rows[5].IsCritical);
            Assert.Equal("—", t.Rows[1].SensitivityRangeText);
            Assert.Equal("无碰撞（临界）", t.Rows[2].DisplayVerdictText);
            Assert.Equal("险情", t.Rows[3].DisplayVerdictText);
        }

        [Fact]
        public void D05_SensitivityCrossing_AloneMarksCritical()
        {
            ScenarioResult s0 = Synthetic("S0", true, 0.0);
            Dictionary<string, IReadOnlyList<SensitivityOutcome>> sens = new Dictionary<string, IReadOnlyList<SensitivityOutcome>>
            {
                { "A", new[] { new SensitivityOutcome("lo", false, ScenarioVerdict.NearMiss, 150.0), new SensitivityOutcome("hi", false, ScenarioVerdict.Avoided, 260.0) } },
                { "B", new[] { new SensitivityOutcome("lo", false, ScenarioVerdict.Avoided, 220.0), new SensitivityOutcome("hi", false, ScenarioVerdict.Avoided, 260.0) } },
                { "S0", new[] { new SensitivityOutcome("x", false, ScenarioVerdict.Avoided, 200.0) } },
            };
            ComparisonTable t = ScenarioComparison.Build(new[] { s0, Synthetic("A", false, 240.0), Synthetic("B", false, 240.0) }, sens);
            Assert.True(t.Rows[1].IsCritical);
            Assert.Contains("150.0–260.0", t.Rows[1].SensitivityRangeText);
            Assert.False(t.Rows[2].IsCritical);
            Assert.Contains("220.0–260.0", t.Rows[2].SensitivityRangeText);
            // 碰撞按 0 m 计，敏感性中出现无碰撞也算跨线。
            Assert.True(t.Rows[0].IsCritical);
            Assert.Equal("碰撞（临界）", t.Rows[0].DisplayVerdictText);
        }

        [Fact]
        public void D05_InvalidMargin_Throws()
        {
            ScenarioResult s0 = Synthetic("S0", true, 0.0);
            Assert.Throws<ArgumentOutOfRangeException>(() => ScenarioComparison.Build(new[] { s0 }, null, -1.0));
            Assert.Throws<ArgumentOutOfRangeException>(() => ScenarioComparison.Build(new[] { s0 }, null, double.NaN));
        }

        [Fact]
        public void D05_AntennaRows_ExposeOutcomes_ControlRowExcluded()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            Assert.Equal(4, result.AntennaSensitivity.Count);
            Assert.False(result.AntennaSensitivity[0].InEstimateRange);
            Assert.True(result.AntennaSensitivity.Skip(1).All(r => r.InEstimateRange));
            foreach (AntennaSensitivityRow row in result.AntennaSensitivity)
            {
                Assert.True(row.ScenarioOutcomes.ContainsKey("Y1"));
                Assert.Contains(row.ScenarioOutcomes["Y1"].MinClearanceM.ToString("F1", System.Globalization.CultureInfo.InvariantCulture), row.ScenarioSummaries["Y1"]);
            }
            IReadOnlyDictionary<string, IReadOnlyList<SensitivityOutcome>> map = Yangze22Case.ToComparisonSensitivity(result.AntennaSensitivity);
            Assert.Equal(3, map["Y1"].Count);
            Assert.DoesNotContain(map["Y1"], o => o.Label == "天线不改正");
        }
    }
}
