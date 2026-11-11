using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Domain.Common;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    /// <summary>W14.1 复测补测：OBB 真实距离、接触点、天线、截断、DCPA、全程最小净距，以及三项架构师裁定。</summary>
    public class W14_1RetestTests
    {
        private const double SafeM = 185.2;

        [Fact]
        public void ObbSeparatedDistance_MatchesBruteForce_IncludingRotatedAndParallel()
        {
            OrientedBoundingBox[] boxes = new[]
            {
                Box(0, 0, 0, 120, 20),
                Box(200, 40, 0, 100, 16),
                Box(80, 90, 35, 90, 18),
                Box(-30, 150, 90, 70, 14),
                Box(40, -80, 17, 110, 22),
                Box(15, 25, 63, 60, 12)
            };
            double worst = 0.0;
            int compared = 0;
            for (int i = 0; i < boxes.Length; i++)
            {
                for (int j = i + 1; j < boxes.Length; j++)
                {
                    double clearance = OrientedBoundingBox.Clearance(boxes[i], boxes[j]);
                    if (clearance <= 0.0) continue;
                    double brute = BruteForceSeparation(boxes[i], boxes[j]);
                    worst = Math.Max(worst, Math.Abs(clearance - brute));
                    compared++;
                }
            }

            // 平行同向错开
            OrientedBoundingBox pa = Box(0, 0, 20, 120, 20);
            OrientedBoundingBox pb = Box(250, 80, 20, 100, 16);
            double parClear = OrientedBoundingBox.Clearance(pa, pb);
            double parBrute = BruteForceSeparation(pa, pb);
            Assert.True(parClear > 0.0);
            worst = Math.Max(worst, Math.Abs(parClear - parBrute));
            compared++;

            // 旋转斜向
            OrientedBoundingBox ra = Box(0, 0, 10, 140, 24);
            OrientedBoundingBox rb = Box(90, 70, 55, 80, 16);
            double rotClear = OrientedBoundingBox.Clearance(ra, rb);
            if (rotClear > 0.0)
            {
                worst = Math.Max(worst, Math.Abs(rotClear - BruteForceSeparation(ra, rb)));
                compared++;
            }

            Assert.True(compared >= 3, "应有足够的分离样本，实际 " + compared);
            Assert.True(worst < 0.05, "暴力采样与 Clearance 最大差=" + worst.ToString("F4") + " m");
        }

        [Fact]
        public void ObbOverlap_ClearanceIsNegativePenetration()
        {
            // 两船均向北、中心东西对齐、南北相距 40 m。沿 SAT 轴的最小平移量是横向：
            // 半宽各 10 m、横向投影距 0，穿透 20 m（纵向穿透 60 m 更大，不取）。
            OrientedBoundingBox a = Box(0, 0, 0, 100, 20);
            OrientedBoundingBox b = Box(0, 40, 0, 100, 20);
            double clearance = OrientedBoundingBox.Clearance(a, b);
            Assert.True(clearance < 0.0, "重叠时应返回负的穿透深度，实际 " + clearance);
            Assert.InRange(clearance, -25.0, -15.0);

            OrientedBoundingBox c = Box(0, 0, 0, 80, 16);
            OrientedBoundingBox d = Box(5, 5, 30, 80, 16);
            double overlapped = OrientedBoundingBox.Clearance(c, d);
            Assert.True(overlapped < 0.0, "旋转重叠应为负，实际 " + overlapped);
        }

        [Fact]
        public void ContactPoint_IsReasonableForSeparatedAndTBone()
        {
            // 分离：应接近独立最近点对中点
            OrientedBoundingBox a = Box(0, 0, 0, 120, 20);
            OrientedBoundingBox b = Box(0, 200, 90, 100, 16);
            EnuPosition impl = OrientedBoundingBox.ContactPoint(a, b);
            EnuPosition indep = W14AccFixture.ClosestPointContact(a, b);
            double err = Hypot(impl.EastM - indep.EastM, impl.NorthM - indep.NorthM);
            Assert.True(err < 1.0, "分离接触点与独立最近点中点相差 " + err.ToString("F2") + " m");

            // T 型：本船静止、他船从右横撞，接触点应靠近本船右舷而不是两中心中点
            WhatIfVessel own = W14AccFixture.StraightVessel("Own", 0, 0, 0, 0.0, 120, 20, 0, 80);
            WhatIfVessel tgt = W14AccFixture.StraightVessel("Tgt", 400, 0, 270, 12, 100, 16, 0, 80);
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(own, tgt, 0, 80);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.True(result.Collision);
            CollisionGeometry g = result.Geometry;
            Assert.Equal("右舷", g.StruckSide);
            Assert.InRange(g.ContactFromStruckBowM, 40.0, 80.0);

            // 首次接触前一档（仍分离）时，ContactPoint 应与独立最近点对中点一致。
            double before = g.TcSeconds - setup.CollisionPrecisionSec;
            KinematicState ownB = result.Tracks["Own"].SampleAt(before);
            KinematicState tgtB = result.Tracks["Tgt"].SampleAt(before);
            OrientedBoundingBox boxOwn = W14AccFixture.BoxOf(ownB, 120, 20);
            OrientedBoundingBox boxTgt = W14AccFixture.BoxOf(tgtB, 100, 16);
            Assert.True(OrientedBoundingBox.Clearance(boxOwn, boxTgt) > 0.0, "tc-精度处应仍分离");
            EnuPosition implBefore = OrientedBoundingBox.ContactPoint(boxOwn, boxTgt);
            EnuPosition indepBefore = W14AccFixture.ClosestPointContact(boxOwn, boxTgt);
            double contactErr = Hypot(implBefore.EastM - indepBefore.EastM, implBefore.NorthM - indepBefore.NorthM);
            Assert.True(contactErr < 1.0, "分离时 T 型 ContactPoint 与独立最近点相差 " + contactErr.ToString("F2") + " m");
        }

        [Fact]
        public void AntennaOffsets_AreMarkedEstimated()
        {
            Yangze22Result result = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            IReadOnlyList<SourcedValue> inputs = result.Original.Inputs;
            List<SourcedValue> antennas = new List<SourcedValue>();
            foreach (SourcedValue v in inputs)
            {
                if (v.Name != null && v.Name.Contains("天线"))
                {
                    antennas.Add(v);
                }
            }
            Assert.True(antennas.Count >= 4, "两船应各有距船首、距中线两条天线 SourcedValue，实际 " + antennas.Count);
            Assert.All(antennas, v =>
            {
                Assert.Equal(ValueSource.Estimated, v.Source);
                bool marked = (v.Note != null && v.Note.Contains("【估计】")) ||
                              (v.SourceText != null && v.SourceText.Contains("估计"));
                Assert.True(marked, "天线偏移应标【估计】或估计：" + v.Name + " / " + v.Note);
            });
        }

        [Fact]
        public void AntennaSensitivity_ThreeRowsMatchAnnouncedNumbers()
        {
            Yangze22Result result = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            IReadOnlyList<AntennaSensitivityRow> rows = result.AntennaSensitivity;
            Assert.True(rows.Count >= 4, "敏感性应含不改正 + 0.35/0.375/0.40L，实际 " + rows.Count);

            AntennaSensitivityRow none = FindAntenna(rows, 0.0, 0.0);
            AntennaSensitivityRow low = FindAntenna(rows, 0.20, 0.35);
            AntennaSensitivityRow nominal = FindAntenna(rows, 0.20, 0.375);
            AntennaSensitivityRow high = FindAntenna(rows, 0.20, 0.40);
            Assert.NotNull(none);
            Assert.NotNull(low);
            Assert.NotNull(nominal);
            Assert.NotNull(high);

            Assert.True(none.Collision);
            Assert.InRange(none.DelayVsReportSec.Value, 26.0, 26.8);
            Assert.InRange(none.CollisionAngleDeg.Value, 68.5, 69.5);
            Assert.Contains("无碰撞", Y1Summary(none));
            Assert.Contains("218", Y1Summary(none));

            Assert.True(low.Collision);
            Assert.InRange(low.DelayVsReportSec.Value, 7.2, 7.8);
            Assert.InRange(low.CollisionAngleDeg.Value, 68.5, 69.5);
            Assert.Contains("无碰撞", Y1Summary(low));
            Assert.Contains("185.5", Y1Summary(low));

            Assert.True(nominal.Collision);
            Assert.InRange(nominal.DelayVsReportSec.Value, 5.8, 6.5);
            Assert.InRange(nominal.CollisionAngleDeg.Value, 68.5, 69.5);
            Assert.Contains("险情", Y1Summary(nominal));
            Assert.Contains("184.4", Y1Summary(nominal));

            Assert.True(high.Collision);
            Assert.InRange(high.DelayVsReportSec.Value, 4.5, 5.2);
            Assert.InRange(high.CollisionAngleDeg.Value, 68.5, 69.5);
            Assert.Contains("险情", Y1Summary(high));
            Assert.Contains("183.2", Y1Summary(high));
        }

        [Fact]
        public void TruncationCutoff_IsRecordedInAssumptions()
        {
            Yangze22Result truncated = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs(300.0, true));
            Assert.Contains(truncated.Original.Assumptions, a =>
                a != null && (a.Contains("22:01:54") || a.Contains("截断")));

            Yangze22Result open = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs(300.0, false));
            Assert.DoesNotContain(open.Original.Assumptions, a =>
                a != null && a.Contains("真实案例航迹截断"));
        }

        [Fact]
        public void MinDcpaAfterDeviation_ColumnExistsAndIsPopulatedForInterventions()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ComparisonTable table = ScenarioComparison.Build(results);
            string md = table.ToMarkdown();
            Assert.Contains("偏离后最小DCPA", md);

            ScenarioResult s0 = results[0];
            ScenarioResult s1 = results[1];
            Assert.False(s0.MinDcpaAfterDeviationNm.HasValue, "原始情景无偏离，偏离后最小 DCPA 应为空");
            Assert.True(s1.MinDcpaAfterDeviationNm.HasValue, "S1 有偏离，应给出偏离后最小 DCPA");
            Assert.True(s1.MinDcpaAfterDeviationNm.Value >= 0.0);
        }

        [Fact]
        public void ReportedMinClearance_VersusGlobalScan_ForDefaultScenarios()
        {
            // 核对实施方已知问题 3：报出的最小净距是否等于全程全局最小，尤其 Y1 靠近 185.2 m。
            List<string> notes = new List<string>();
            bool anyFlip = false;
            bool anyWorse = false;

            WhatIfSetup demo = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> demoResults = ScenarioEvaluator.EvaluateAll(demo, WhatIfDemoFixture.Scenarios());
            foreach (ScenarioResult r in demoResults)
            {
                if (r.Collision) continue;
                CompareGlobal(r, demo.StartSeconds, demo.EndSeconds, "demo-" + r.ScenarioId, notes, ref anyFlip, ref anyWorse);
            }

            Yangze22Result yangze = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            double start = yangze.Original.Tracks[Yangze22Case.Yangze22Id].States[0].TimeSeconds;
            double end = 300.0;
            foreach (ScenarioResult r in yangze.Results)
            {
                if (r.Collision) continue;
                CompareGlobal(r, start, end, "yangze-" + r.ScenarioId, notes, ref anyFlip, ref anyWorse);
            }

            string path = System.IO.Path.Combine(W14AccFixture.LogsDirectory, "w14.2-retest-global-min-scan.txt");
            System.IO.File.WriteAllLines(path, notes.ToArray());

            // W14.2：最小净距应为全程全局最小，报出值不得明显偏大，也不得翻转结论。
            Assert.False(anyFlip,
                "存在情景因全程最小净距改变结论类别：\n" + string.Join("\n", notes));
            Assert.False(anyWorse,
                "存在情景的全局最小净距明显小于报出值：\n" + string.Join("\n", notes));
        }

        [Fact]
        public void Ruling7a_HeadOnBothBowsClose_ShouldBeBowToBow()
        {
            // 裁定 7a：两船船首到接触点的距离都小于 max(10 m, 0.05L) 时，判为“船首对船首”，不指定单一撞击船。
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.True(s0.Collision);
            CollisionGeometry g = s0.Geometry;
            Assert.NotNull(g);

            KinematicState mary = s0.Tracks[WhatIfDemoFixture.MaryId].SampleAt(g.TcSeconds);
            KinematicState lily = s0.Tracks[WhatIfDemoFixture.LilyId].SampleAt(g.TcSeconds);
            EnuPosition maryBow = W14AccFixture.BowPoint(mary, 120.0);
            EnuPosition lilyBow = W14AccFixture.BowPoint(lily, 98.0);
            double dMary = Hypot(maryBow.EastM - g.ContactPointEnu.EastM, maryBow.NorthM - g.ContactPointEnu.NorthM);
            double dLily = Hypot(lilyBow.EastM - g.ContactPointEnu.EastM, lilyBow.NorthM - g.ContactPointEnu.NorthM);
            double thMary = W14AccFixture.BowToBowThresholdM(120.0);
            double thLily = W14AccFixture.BowToBowThresholdM(98.0);
            Assert.True(dMary < thMary && dLily < thLily,
                "本用例两船船首均应落在阈值内（Mary " + dMary.ToString("F1") + " / " + thMary +
                "，Lily " + dLily.ToString("F1") + " / " + thLily + "）");

            Assert.True(g.IsBowToBow);
            Assert.Equal(ImpactKind.BowToBow, g.Kind);
            Assert.Equal(string.Empty, g.StrikingVesselId);
            Assert.Equal(string.Empty, g.StruckVesselId);
            Assert.Equal(CollisionGeometry.BowToBowText, g.StruckSide);
            Assert.Contains("船首对船首", g.Description);
        }

        [Fact]
        public void Ruling7b_MinClearanceMustBeGlobalMinimum()
        {
            // 裁定 7b：最小净距必须是全程的全局最小值。构造一个 OBB 最小点距中心 CPA 超过 2 s 的情景。
            // 本船静止、首尾向北、船长 300 m；他船沿 x+y=420、航向 135° 以 10 kn 通过。
            // 全局最小净距约 176 m（险情），中心最近点处净距约 185.5 m（无碰撞）。
            WhatIfVessel own = W14AccFixture.StraightVessel("Own", 0, 0, 0, 0.0, 300, 20, 0, 200);
            WhatIfVessel tgt = W14AccFixture.StraightVessel("Tgt", -50, 470, 135, 10, 80, 16, 0, 200);
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(own, tgt, 0, 200, 0.1);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.False(result.Collision, "合成用例不应碰撞，结论=" + result.Verdict + " 净距=" + result.MinClearanceM);

            double globalClear, globalTime;
            W14AccFixture.ScanGlobalMinClearance(
                result.Tracks["Own"], result.Tracks["Tgt"], 0, 200, out globalClear, out globalTime);

            ScenarioVerdict globalVerdict = globalClear < setup.SafeDistanceM
                ? ScenarioVerdict.NearMiss
                : ScenarioVerdict.Avoided;
            bool missed = result.MinClearanceM > globalClear + 1.0;
            bool flipped = result.Verdict != globalVerdict;
            Yangze22Result yangze = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            ScenarioResult both = yangze.Find("Y1+Y5");
            double bothGlobal, bothTime;
            W14AccFixture.ScanGlobalMinClearance(
                both.Tracks[Yangze22Case.Yangze22Id],
                both.Tracks[Yangze22Case.VegaDreamId],
                both.Tracks[Yangze22Case.Yangze22Id].States[0].TimeSeconds,
                300.0, out bothGlobal, out bothTime);
            bool bothMissed = both.MinClearanceM > bothGlobal + 1.0;

            Assert.False(missed,
                "合成用例未抓到窗口外低谷：报出 " + result.MinClearanceM.ToString("F1") +
                " m，全程最小 " + globalClear.ToString("F1") + " m");
            Assert.False(flipped, "合成用例结论与全程最小不一致");
            Assert.False(bothMissed,
                "Y1+Y5 报出 " + both.MinClearanceM.ToString("F1") +
                " m，全程最小 " + bothGlobal.ToString("F1") + " m（t=" + bothTime.ToString("F1") + "）");
            Assert.InRange(result.MinClearanceM, 174.0, 177.0);
            Assert.InRange(both.MinClearanceM, 290.0, 295.0);
        }

        [Fact]
        public void Ruling7c_NearSafeLineOrAntennaCross_ShouldMarkCritical()
        {
            // 裁定 7c：结论离安全线不到 5 m，或天线敏感性区间跨越安全线时，对比表要标“临界”并给出敏感性区间。
            Yangze22Result result = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            ScenarioResult y1 = result.Find("Y1");
            Assert.False(y1.Collision);
            double gap = Math.Abs(y1.MinClearanceM - SafeM);
            Assert.True(gap < 5.0, "Y1 应紧贴安全线，实际净距 " + y1.MinClearanceM.ToString("F1") + " m，差 " + gap.ToString("F1") + " m");

            bool crosses = false;
            foreach (AntennaSensitivityRow row in result.AntennaSensitivity)
            {
                if (row.ScenarioSummaries != null && row.ScenarioSummaries.ContainsKey("Y1"))
                {
                    string s = row.ScenarioSummaries["Y1"];
                    if (s.Contains("无碰撞")) crosses = true;
                    if (s.Contains("险情") || s.Contains("NearMiss")) crosses = crosses || true;
                }
            }
            // 0.35L 无碰撞 185.5、0.375L 险情 184.4，敏感性跨越安全线。
            string y1Low = Y1Summary(FindAntenna(result.AntennaSensitivity, 0.20, 0.35));
            string y1Nom = Y1Summary(FindAntenna(result.AntennaSensitivity, 0.20, 0.375));
            Assert.True(y1Low.Contains("无碰撞") && y1Nom.Contains("险情"),
                "天线敏感性应跨越安全线：0.35L=" + y1Low + " 0.375L=" + y1Nom);

            string md = result.Comparison.ToMarkdown();
            ComparisonRow y1Row = null;
            foreach (ComparisonRow row in result.Comparison.Rows)
            {
                if (row.ScenarioId == "Y1") y1Row = row;
            }
            Assert.NotNull(y1Row);
            Assert.True(y1Row.IsCritical, "Y1 应标临界");
            Assert.Contains("临界", y1Row.DisplayVerdictText);
            Assert.Contains("临界", ExtractRow(md, "Y1"));
            Assert.Contains("183.2", y1Row.SensitivityRangeText);
            Assert.Contains("185.5", y1Row.SensitivityRangeText);
            Assert.DoesNotContain("218.9", y1Row.SensitivityRangeText);
            Assert.DoesNotContain("218", y1Row.SensitivityRangeText);
        }

        private static void CompareGlobal(
            ScenarioResult r,
            double start,
            double end,
            string name,
            List<string> notes,
            ref bool anyFlip,
            ref bool anyWorse)
        {
            CounterfactualTrack own = null;
            CounterfactualTrack tgt = null;
            foreach (KeyValuePair<string, CounterfactualTrack> kv in r.Tracks)
            {
                if (own == null) own = kv.Value;
                else if (tgt == null) tgt = kv.Value;
            }
            double globalClear, globalTime;
            W14AccFixture.ScanGlobalMinClearance(own, tgt, start, end, out globalClear, out globalTime);
            ScenarioVerdict globalVerdict = globalClear < SafeM ? ScenarioVerdict.NearMiss : ScenarioVerdict.Avoided;
            double delta = r.MinClearanceM - globalClear;
            string line = string.Format(
                CultureInfo.InvariantCulture,
                "{0}: reported {1} {2:F2} m @ t={3:F2}; global {4} {5:F2} m @ t={6:F2}; delta={7:F2} m",
                name, r.Verdict, r.MinClearanceM, r.MinDistanceTimeSeconds,
                globalVerdict, globalClear, globalTime, delta);
            notes.Add(line);
            if (r.Verdict != globalVerdict)
            {
                anyFlip = true;
            }
            if (delta > 1.0)
            {
                anyWorse = true;
            }
        }

        private static AntennaSensitivityRow FindAntenna(
            IReadOnlyList<AntennaSensitivityRow> rows, double yangzeAft, double vegaAft)
        {
            foreach (AntennaSensitivityRow row in rows)
            {
                if (Math.Abs(row.YangzeAftOfMidshipRatio - yangzeAft) < 1e-6 &&
                    Math.Abs(row.VegaAftOfMidshipRatio - vegaAft) < 1e-6)
                {
                    return row;
                }
            }
            return null;
        }

        private static string Y1Summary(AntennaSensitivityRow row)
        {
            if (row == null || row.ScenarioSummaries == null || !row.ScenarioSummaries.ContainsKey("Y1"))
            {
                return "";
            }
            return row.ScenarioSummaries["Y1"];
        }

        private static string ExtractRow(string markdown, string scenarioId)
        {
            foreach (string line in markdown.Split('\n'))
            {
                if (line.StartsWith("| " + scenarioId + " ", StringComparison.Ordinal) ||
                    line.StartsWith("|" + scenarioId + " ", StringComparison.Ordinal) ||
                    line.Contains("| " + scenarioId + " |"))
                {
                    return line;
                }
            }
            return "";
        }

        private static OrientedBoundingBox Box(double east, double north, double heading, double loa, double beam)
        {
            return OrientedBoundingBox.FromVessel(new EnuPosition(east, north, 0.0), heading, (float)loa, (float)beam);
        }

        /// <summary>边界密采样的分离距离下界对照（分离时）。</summary>
        private static double BruteForceSeparation(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            Double2[] ca = a.GetCorners();
            Double2[] cb = b.GetCorners();
            List<Double2> pa = DenseBoundary(ca, 80);
            List<Double2> pb = DenseBoundary(cb, 80);
            double best = double.PositiveInfinity;
            for (int i = 0; i < pa.Count; i++)
            {
                for (int j = 0; j < pb.Count; j++)
                {
                    double d = Hypot(pa[i].X - pb[j].X, pa[i].Y - pb[j].Y);
                    if (d < best) best = d;
                }
            }
            return best;
        }

        private static List<Double2> DenseBoundary(Double2[] corners, int perEdge)
        {
            List<Double2> points = new List<Double2>(4 * perEdge);
            for (int i = 0; i < 4; i++)
            {
                Double2 a = corners[i];
                Double2 b = corners[(i + 1) % 4];
                for (int k = 0; k < perEdge; k++)
                {
                    double t = (double)k / perEdge;
                    points.Add(new Double2(a.X + t * (b.X - a.X), a.Y + t * (b.Y - a.Y)));
                }
            }
            return points;
        }

        private static double Hypot(double x, double y)
        {
            return Math.Sqrt(x * x + y * y);
        }
    }
}
