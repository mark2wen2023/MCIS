using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Domain.Common;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    /// <summary>W14.2 复测补测：船首对船首口径、全程最小净距、平台稳定性、窄谷、天线临界区间，以及敏感性转储。</summary>
    public class W14_2RetestTests
    {
        [Fact]
        public void BowToBow_StrikingAndStruckIdsAreEmpty_SideIsBowToBow()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ScenarioResult s0 = results[0];
            ScenarioResult s2 = results[2];
            AssertBowToBow(s0.Geometry, "S0");
            AssertBowToBow(s2.Geometry, "S2");
        }

        [Fact]
        public void NonBowToBow_StrikingVesselIsCloserBow()
        {
            // T 型：他船船首横撞本船右舷中部，不应判船首对船首，撞击船为他船。
            WhatIfVessel own = W14AccFixture.StraightVessel("Own", 0, 0, 0, 0.0, 120, 20, 0, 80);
            WhatIfVessel tgt = W14AccFixture.StraightVessel("Tgt", 400, 0, 270, 12, 100, 16, 0, 80);
            ScenarioResult result = ScenarioEvaluator.Evaluate(
                W14AccFixture.TwoShipSetup(own, tgt, 0, 80), WhatIfScenario.Original());
            Assert.True(result.Collision);
            CollisionGeometry g = result.Geometry;
            Assert.False(g.IsBowToBow);
            Assert.Equal("Tgt", g.StrikingVesselId);
            Assert.Equal("Own", g.StruckVesselId);
            Assert.Equal("右舷", g.StruckSide);
            Assert.False(string.IsNullOrEmpty(g.StrikingVesselId));
            Assert.False(string.IsNullOrEmpty(g.StruckVesselId));

            KinematicState ownS = result.Tracks["Own"].SampleAt(g.TcSeconds);
            KinematicState tgtS = result.Tracks["Tgt"].SampleAt(g.TcSeconds);
            double dOwn = Distance(W14AccFixture.BowPoint(ownS, 120), g.ContactPointEnu);
            double dTgt = Distance(W14AccFixture.BowPoint(tgtS, 100), g.ContactPointEnu);
            Assert.True(dTgt < dOwn, "他船船首应更近，实际 Tgt=" + dTgt.ToString("F1") + " Own=" + dOwn.ToString("F1"));
            Assert.True(dTgt < CollisionGeometry.BowToBowThresholdM(100.0) ||
                        dOwn >= CollisionGeometry.BowToBowThresholdM(120.0));

            // YANGZE 22 S0：VEGA 船首撞 YANGZE 右舷，不是船首对船首。
            Yangze22Result yangze = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            CollisionGeometry s0g = yangze.Original.Geometry;
            Assert.False(s0g.IsBowToBow);
            Assert.Equal(Yangze22Case.VegaDreamId, s0g.StrikingVesselId);
            Assert.Equal(Yangze22Case.Yangze22Id, s0g.StruckVesselId);
            Assert.Equal("右舷", s0g.StruckSide);
        }

        [Fact]
        public void SyntheticValleyOutsideOldWindow_IsCaptured()
        {
            WhatIfVessel own = W14AccFixture.StraightVessel("Own", 0, 0, 0, 0.0, 300, 20, 0, 200);
            WhatIfVessel tgt = W14AccFixture.StraightVessel("Tgt", -50, 470, 135, 10, 80, 16, 0, 200);
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(own, tgt, 0, 200, 0.1);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.False(result.Collision);

            double globalClear, globalTime;
            W14AccFixture.ScanGlobalMinClearance(
                result.Tracks["Own"], result.Tracks["Tgt"], 0, 200, out globalClear, out globalTime);
            Assert.InRange(Math.Abs(result.MinClearanceM - globalClear), 0.0, 0.5);
            // 中心 CPA 约在 t=71 s，OBB 最小约在 t=51 s，相差约 20 s，超过旧的 ±2 s 窗口。
            Assert.True(Math.Abs(result.MinClearanceTimeSeconds - result.MinDistanceTimeSeconds) > 2.0 ||
                        Math.Abs(globalTime - result.MinDistanceTimeSeconds) > 2.0,
                "合成用例的 OBB 最小时刻应明显偏离中心 CPA，否则无法核对窗口外低谷");
            Assert.InRange(result.MinClearanceM, 174.0, 177.0);
        }

        [Fact]
        public void ParallelSlidePlateau_ClearanceIsStable()
        {
            // 两艘同向平行滑过：净距在并排时段应是平台，报出值应稳定。
            WhatIfVessel a = W14AccFixture.StraightVessel("A", 0, 0, 0, 8, 120, 20, 0, 200);
            WhatIfVessel b = W14AccFixture.StraightVessel("B", 80, -200, 0, 8, 100, 16, 0, 200);
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(a, b, 0, 200, 0.1);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.False(result.Collision);
            Assert.True(result.MinClearanceM > 0.0);

            CounterfactualTrack ta = result.Tracks["A"];
            CounterfactualTrack tb = result.Tracks["B"];
            double t0 = result.MinClearanceTimeSeconds;
            List<double> nearby = new List<double>();
            for (double t = t0 - 8.0; t <= t0 + 8.0; t += 0.1)
            {
                if (t < setup.StartSeconds || t > setup.EndSeconds) continue;
                nearby.Add(OrientedBoundingBox.Clearance(
                    W14AccFixture.BoxOf(ta.SampleAt(t), ta.LoaM, ta.BeamM),
                    W14AccFixture.BoxOf(tb.SampleAt(t), tb.LoaM, tb.BeamM)));
            }
            nearby.Sort();
            double plat = nearby[0];
            int onPlateau = 0;
            foreach (double c in nearby)
            {
                if (Math.Abs(c - plat) <= 0.15) onPlateau++;
            }
            Assert.True(onPlateau >= 10,
                "并排滑过应形成净距平台，平台采样数=" + onPlateau + "，最小=" + plat.ToString("F3") +
                "，报出=" + result.MinClearanceM.ToString("F3"));
            Assert.InRange(Math.Abs(result.MinClearanceM - plat), 0.0, 0.2);
        }

        [Fact]
        public void UncorrectedAntennaRow_IsExcludedFromCriticalRange()
        {
            Yangze22Result result = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            AntennaSensitivityRow none = null;
            int inRange = 0;
            foreach (AntennaSensitivityRow row in result.AntennaSensitivity)
            {
                if (Math.Abs(row.YangzeAftOfMidshipRatio) < 1e-9 &&
                    Math.Abs(row.VegaAftOfMidshipRatio) < 1e-9)
                {
                    none = row;
                }
                if (row.InEstimateRange) inRange++;
            }
            Assert.NotNull(none);
            Assert.False(none.InEstimateRange, "不改正天线的对照行不得计入临界区间");
            Assert.Equal(3, inRange);

            ComparisonRow y1 = null;
            foreach (ComparisonRow row in result.Comparison.Rows)
            {
                if (row.ScenarioId == "Y1") y1 = row;
            }
            Assert.NotNull(y1);
            Assert.True(y1.IsCritical);
            Assert.Contains("183.2", y1.SensitivityRangeText);
            Assert.Contains("185.5", y1.SensitivityRangeText);
            Assert.DoesNotContain("218", y1.SensitivityRangeText);
            if (y1.Sensitivity != null)
            {
                foreach (SensitivityOutcome o in y1.Sensitivity)
                {
                    Assert.False(o.MinClearanceM > 200.0,
                        "临界区间不应含不改正行的 218.9 m，实际出现 " + o.MinClearanceM.ToString("F1") + " m（" + o.Label + "）");
                }
            }

            foreach (ComparisonRow row in result.Comparison.Rows)
            {
                if (row.ScenarioId == "Y1") continue;
                Assert.False(row.IsCritical, row.ScenarioId + " 不应标临界：" + row.DisplayVerdictText);
            }
        }

        [Fact]
        [Trait("Defect", "W14-D06")]
        public void NarrowValleyShorterThanCoarseStep_IsDocumented()
        {
            // 在持续接近的背景上叠一个宽约 0.2 s 的窄谷，检验 0.5 s 粗扫是否漏检。
            // W14.3：保留原构造，按裁定要求与0.01秒暴扫的绝对差不超过0.1米。
            List<KinematicState> ownStates = new List<KinematicState>();
            List<KinematicState> tgtStates = new List<KinematicState>();
            const double end = 20.0;
            for (double t = 0.0; t <= end + 1e-9; t += 0.1)
            {
                // 本船静止，船长 200 m；他船自北向南，背景横向间距 50 m。
                // 在到达并排平台（净距约 32 m）之前，于 t=6.25 附近约 0.2 s 把横向间距收到近乎相切（净距约 10 m）。
                // 粗采样在 6.0/6.5 仍落在下降段，不是局部极小，0.5 s 粗扫可能漏掉该谷。
                double north = 200.0 - 8.0 * t;
                double east = 50.0;
                double dip = 0.0;
                double dt = t - 6.25;
                if (Math.Abs(dt) <= 0.12)
                {
                    dip = 55.0 * (1.0 - Math.Abs(dt) / 0.12);
                }
                ownStates.Add(new KinematicState(t, 0, 0, 0, 0, 0, 0));
                tgtStates.Add(new KinematicState(t, east - dip, north, 180, 8, 0, 0));
            }
            ManeuverParams pOwn = ManeuverParams.Default(200, 20, 8000);
            ManeuverParams pTgt = ManeuverParams.Default(80, 16, 5000);
            WhatIfVessel own = WhatIfVessel.FromStates("Own", pOwn, ownStates, "Own");
            WhatIfVessel tgt = WhatIfVessel.FromStates("Tgt", pTgt, tgtStates, "Tgt");
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(own, tgt, 0, end, 0.1);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());

            double truth, truthT;
            ScanBrute(result.Tracks["Own"], result.Tracks["Tgt"], 0, end, 0.01, out truth, out truthT);
            double reported = result.Collision ? 0.0 : result.MinClearanceM;
            string path = Path.Combine(W14AccFixture.LogsDirectory, "w14.2-retest-narrow-valley.txt");
            File.WriteAllText(path, string.Format(
                CultureInfo.InvariantCulture,
                "narrow valley: reported={0:F2} m @ t={1:F2}; brute={2:F2} m @ t={3:F2}; missed={4}\n",
                reported, result.MinClearanceTimeSeconds, truth, truthT, Math.Abs(reported - truth) > 0.1));

            // 暴力扫描应能看到窄谷明显低于背景（背景并排时东西间距 80 m 量级）。
            Assert.True(truth < 20.0, "构造的窄谷应明显低于背景平台（约 32 m），暴力最小=" + truth.ToString("F1"));
            if (Math.Abs(reported - truth) > 0.1)
            {
                Assert.Fail(
                    "W14-D06：粗扫 0.5 s 漏掉了宽度约 0.2 s 的净距低谷。报出 " +
                    reported.ToString("F1") + " m（t=" + result.MinClearanceTimeSeconds.ToString("F2") +
                    "），0.01 s 暴力扫描 " + truth.ToString("F1") + " m（t=" + truthT.ToString("F2") +
                    "）。影响：若真实会遇在持续接近的背景上出现短于粗扫步长的近距离脉冲（急转、船首扫过），" +
                    "报出的最小净距可能偏大；YANGZE 与虚构案例经 0.05 s 对照未发现此类漏检。");
            }
        }

        [Fact]
        public void DumpAntennaSensitivityTracksForIndependentCheck()
        {
            string[] lines = W14AccFixture.ReadYangzeTrackLines();
            Yangze22Inputs inputs = W14AccFixture.LoadYangzeInputs();
            Yangze22Result def = Yangze22Case.Run(lines, inputs);
            StringBuilder json = new StringBuilder();
            json.AppendLine("{");
            json.AppendLine("  \"safeM\": 185.2,");
            json.AppendLine("  \"default\": {");
            AppendScenarioBlock(json, def.Results, "    ");
            json.AppendLine(",");
            json.Append("    \"y1Critical\": ").Append(FindRow(def.Comparison, "Y1").IsCritical ? "true" : "false").AppendLine(",");
            json.Append("    \"y1Range\": ").Append(Q(FindRow(def.Comparison, "Y1").SensitivityRangeText)).AppendLine(",");
            json.Append("    \"y1Display\": ").Append(Q(FindRow(def.Comparison, "Y1").DisplayVerdictText)).AppendLine();
            json.AppendLine("  },");
            json.AppendLine("  \"sensitivity\": [");

            double[][] grid =
            {
                new[] { 0.0, 0.0 },
                new[] { 0.20, 0.35 },
                new[] { 0.20, 0.375 },
                new[] { 0.20, 0.40 }
            };
            string[] labels = { "不改正", "0.35L", "0.375L", "0.40L" };
            for (int i = 0; i < grid.Length; i++)
            {
                AntennaSensitivityRow meta = null;
                foreach (AntennaSensitivityRow row in def.AntennaSensitivity)
                {
                    if (Math.Abs(row.YangzeAftOfMidshipRatio - grid[i][0]) < 1e-6 &&
                        Math.Abs(row.VegaAftOfMidshipRatio - grid[i][1]) < 1e-6)
                    {
                        meta = row;
                    }
                }
                Yangze22Study study = Yangze22Case.Build(lines, inputs, grid[i][0], grid[i][1]);
                IReadOnlyList<ScenarioResult> all = study.EvaluateAll();
                json.Append("    {");
                json.Append("\"label\":").Append(Q(labels[i]));
                json.Append(",\"yangzeAft\":").Append(F(grid[i][0]));
                json.Append(",\"vegaAft\":").Append(F(grid[i][1]));
                json.Append(",\"inEstimateRange\":").Append(meta != null && meta.InEstimateRange ? "true" : "false");
                json.AppendLine(",");
                AppendScenarioBlock(json, all, "      ");
                json.AppendLine();
                json.Append("    }");
                if (i < grid.Length - 1) json.Append(",");
                json.AppendLine();
            }
            json.AppendLine("  ]");
            json.AppendLine("}");

            string path = Path.Combine(W14AccFixture.LogsDirectory, "w14.2-retest-sensitivity-dump.json");
            File.WriteAllText(path, json.ToString(), Encoding.UTF8);
            Assert.True(new FileInfo(path).Length > 1000);
        }

        private static void AssertBowToBow(CollisionGeometry g, string name)
        {
            Assert.NotNull(g);
            Assert.True(g.IsBowToBow, name + " 应为船首对船首，实际 " + g.Description);
            Assert.Equal(string.Empty, g.StrikingVesselId);
            Assert.Equal(string.Empty, g.StruckVesselId);
            Assert.Equal(CollisionGeometry.BowToBowText, g.StruckSide);
            Assert.Equal(0.0, g.ContactFromStruckBowM);
        }

        private static ComparisonRow FindRow(ComparisonTable table, string id)
        {
            foreach (ComparisonRow row in table.Rows)
            {
                if (row.ScenarioId == id) return row;
            }
            return null;
        }

        private static void ScanBrute(
            CounterfactualTrack a, CounterfactualTrack b,
            double start, double end, double step,
            out double best, out double bestT)
        {
            best = double.PositiveInfinity;
            bestT = start;
            for (double t = start; t <= end + 1e-9; t += step)
            {
                double c = OrientedBoundingBox.Clearance(
                    W14AccFixture.BoxOf(a.SampleAt(t), a.LoaM, a.BeamM),
                    W14AccFixture.BoxOf(b.SampleAt(t), b.LoaM, b.BeamM));
                if (c < best)
                {
                    best = c;
                    bestT = t;
                }
            }
        }

        private static void AppendScenarioBlock(StringBuilder json, IReadOnlyList<ScenarioResult> results, string indent)
        {
            json.AppendLine(indent + "\"results\": [");
            for (int i = 0; i < results.Count; i++)
            {
                ScenarioResult r = results[i];
                json.Append(indent + "  {");
                json.Append("\"id\":").Append(Q(r.ScenarioId));
                json.Append(",\"verdict\":").Append(Q(r.Verdict.ToString()));
                json.Append(",\"verdictText\":").Append(Q(r.VerdictText));
                json.Append(",\"collision\":").Append(r.Collision ? "true" : "false");
                json.Append(",\"minClearanceM\":").Append(F(r.MinClearanceM));
                json.Append(",\"minClearanceTime\":").Append(F(r.MinClearanceTimeSeconds));
                json.Append(",\"minDistanceTime\":").Append(F(r.MinDistanceTimeSeconds));
                if (r.TcSeconds.HasValue) json.Append(",\"tcSeconds\":").Append(F(r.TcSeconds.Value));
                json.Append(",\"tracks\":{");
                bool firstT = true;
                foreach (KeyValuePair<string, CounterfactualTrack> kv in r.Tracks)
                {
                    if (!firstT) json.Append(",");
                    firstT = false;
                    json.Append(Q(kv.Key)).Append(":{");
                    json.Append("\"loaM\":").Append(F(kv.Value.LoaM));
                    json.Append(",\"beamM\":").Append(F(kv.Value.BeamM));
                    json.Append(",\"samples\":[");
                    bool first = true;
                    double start = kv.Value.States[0].TimeSeconds;
                    double end = kv.Value.States[kv.Value.States.Count - 1].TimeSeconds;
                    for (double t = start; t <= end + 1e-9; t += 1.0)
                    {
                        KinematicState s = kv.Value.SampleAt(t);
                        if (!first) json.Append(",");
                        first = false;
                        json.Append("[").Append(F(s.TimeSeconds)).Append(",")
                            .Append(F(s.EastM)).Append(",")
                            .Append(F(s.NorthM)).Append(",")
                            .Append(F(s.HeadingDeg)).Append("]");
                    }
                    json.Append("]}");
                }
                json.Append("}}");
                if (i < results.Count - 1) json.Append(",");
                json.AppendLine();
            }
            json.Append(indent + "]");
        }

        private static double Distance(EnuPosition a, EnuPosition b)
        {
            double de = a.EastM - b.EastM;
            double dn = a.NorthM - b.NorthM;
            return Math.Sqrt(de * de + dn * dn);
        }

        private static string F(double v)
        {
            return v.ToString("R", CultureInfo.InvariantCulture);
        }

        private static string Q(string s)
        {
            if (s == null) return "null";
            return "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n") + "\"";
        }
    }
}
