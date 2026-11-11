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
    /// <summary>W14.1 回归：OBB 真实净距（暴力采样对照）与接触点。</summary>
    public class ObbClearanceRegressionTests
    {
        private static OrientedBoundingBox Box(double e, double n, double hdg, double halfL, double halfB)
        {
            return new OrientedBoundingBox(new EnuPosition(e, n, 0.0), hdg, halfL, halfB);
        }

        /// <summary>两矩形边界各边等距采样后点对最小距离（只用于分离情形对照）。</summary>
        private static double BruteForce(OrientedBoundingBox a, OrientedBoundingBox b, int perEdge, out double spacing)
        {
            Double2[] pa = Sample(a.GetCorners(), perEdge, out double sa);
            Double2[] pb = Sample(b.GetCorners(), perEdge, out double sb);
            spacing = sa + sb;
            double best = double.PositiveInfinity;
            for (int i = 0; i < pa.Length; i++)
            {
                for (int j = 0; j < pb.Length; j++)
                {
                    double dx = pa[i].X - pb[j].X;
                    double dy = pa[i].Y - pb[j].Y;
                    double d2 = dx * dx + dy * dy;
                    if (d2 < best) best = d2;
                }
            }
            return Math.Sqrt(best);
        }

        private static Double2[] Sample(Double2[] corners, int perEdge, out double maxSpacing)
        {
            List<Double2> pts = new List<Double2>(corners.Length * perEdge);
            maxSpacing = 0.0;
            for (int k = 0; k < corners.Length; k++)
            {
                Double2 p0 = corners[k];
                Double2 p1 = corners[(k + 1) % corners.Length];
                maxSpacing = Math.Max(maxSpacing, (p1 - p0).Length / perEdge);
                for (int i = 0; i < perEdge; i++)
                {
                    pts.Add(p0 + (p1 - p0) * (i / (double)perEdge));
                }
            }
            return pts.ToArray();
        }

        private static bool SatSeparated(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            a.GetAxes(out Double2 af, out Double2 asb);
            b.GetAxes(out Double2 bf, out Double2 bsb);
            Double2 d = new Double2(b.Center.EastM - a.Center.EastM, b.Center.NorthM - a.Center.NorthM);
            foreach (Double2 axis in new[] { af, asb, bf, bsb })
            {
                double proj = Math.Abs(Double2.Dot(d, axis));
                double ra = a.HalfLengthM * Math.Abs(Double2.Dot(af, axis)) + a.HalfBeamM * Math.Abs(Double2.Dot(asb, axis));
                double rb = b.HalfLengthM * Math.Abs(Double2.Dot(bf, axis)) + b.HalfBeamM * Math.Abs(Double2.Dot(bsb, axis));
                if (proj - (ra + rb) > 0.0) return true;
            }
            return false;
        }

        [Fact]
        public void CornerToCorner_Squares_IsSqrt13_NotSatGap2()
        {
            // REQUESTS.md 反例：边长 2 m 的正方形，中心 (0,0) 与 (4,5)。旧 SAT 返回 2 m。
            double c = OrientedBoundingBox.Clearance(Box(0, 0, 0, 1, 1), Box(4, 5, 0, 1, 1));
            TestUtil.AssertNear(Math.Sqrt(13.0), c, 1e-9, "角对角净距");
        }

        [Fact]
        public void ParallelFaces_EqualsFaceGap()
        {
            TestUtil.AssertNear(100.0, OrientedBoundingBox.Clearance(Box(0, 0, 0, 50, 10), Box(0, 200, 0, 50, 10)), 1e-9);
        }

        [Fact]
        public void PerpendicularT_FaceGap()
        {
            // A 首向 0（半长 60、半宽 10）；B 首向 270，船首在 A 右舷外 20 m。
            double c = OrientedBoundingBox.Clearance(Box(0, 0, 0, 60, 10), Box(10 + 20 + 50, 20, 270, 50, 8));
            TestUtil.AssertNear(20.0, c, 1e-9);
        }

        [Fact]
        public void Touching_IsZero_AndOverlap_KeepsSatPenetrationConvention()
        {
            Assert.Equal(0.0, OrientedBoundingBox.Clearance(Box(0, 0, 0, 50, 10), Box(0, 100, 0, 50, 10)), 9);
            // 首尾相叠 5 m：沿首尾轴的最小平移穿透 = 5 m，返回 −5。
            TestUtil.AssertNear(-5.0, OrientedBoundingBox.Clearance(Box(0, 0, 0, 50, 10), Box(0, 95, 0, 50, 10)), 1e-9);
            // 原有交叉重叠用例仍为负。
            Assert.True(OrientedBoundingBox.Clearance(Box(0, 0, 90, 80, 15), Box(20, 0, 0, 80, 15)) < 0.0);
        }

        [Fact]
        public void RandomSeparatedPairs_MatchBruteForceSampling()
        {
            Random rng = new Random(20261111);
            int checkedCount = 0;
            for (int k = 0; k < 400 && checkedCount < 40; k++)
            {
                OrientedBoundingBox a = Box(0, 0, rng.NextDouble() * 360.0, 20 + rng.NextDouble() * 140, 4 + rng.NextDouble() * 22);
                OrientedBoundingBox b = Box(
                    (rng.NextDouble() - 0.5) * 700, (rng.NextDouble() - 0.5) * 700,
                    rng.NextDouble() * 360.0, 20 + rng.NextDouble() * 140, 4 + rng.NextDouble() * 22);
                if (!SatSeparated(a, b))
                {
                    continue;
                }
                double c = OrientedBoundingBox.Clearance(a, b);
                double brute = BruteForce(a, b, 300, out double spacing);
                Assert.True(c > 0.0);
                Assert.True(brute >= c - 1e-6, "精确净距不应大于采样点对距离：c=" + c + " brute=" + brute);
                Assert.True(brute - c <= spacing + 1e-6, "精确净距与暴力采样相差超过采样间距：c=" + c + " brute=" + brute + " spacing=" + spacing);
                checkedCount++;
            }
            Assert.True(checkedCount >= 40);
        }

        [Fact]
        public void SignInvariant_PositiveIffSatSeparated()
        {
            Random rng = new Random(7);
            for (int k = 0; k < 2000; k++)
            {
                OrientedBoundingBox a = Box(0, 0, rng.NextDouble() * 360.0, 10 + rng.NextDouble() * 100, 3 + rng.NextDouble() * 15);
                OrientedBoundingBox b = Box(
                    (rng.NextDouble() - 0.5) * 250, (rng.NextDouble() - 0.5) * 250,
                    rng.NextDouble() * 360.0, 10 + rng.NextDouble() * 100, 3 + rng.NextDouble() * 15);
                Assert.Equal(SatSeparated(a, b), OrientedBoundingBox.Clearance(a, b) > 0.0);
            }
        }

        [Fact]
        public void TContact_UsesPenetrationCentroid_NotCenterMidpoint()
        {
            // A 静止首向 0（L120 B20）；B 首向 270 从右舷横撞，船首面已进入 A 右舷 0.2 m，船首中心在 A 中点前 20 m。
            OrientedBoundingBox a = Box(0, 0, 0, 60, 10);
            OrientedBoundingBox b = Box(10 - 0.2 + 50, 20, 270, 50, 8);
            EnuPosition contact = OrientedBoundingBox.ContactPoint(a, b);
            TestUtil.AssertNear(9.9, contact.EastM, 1e-6, "接触点东向");
            TestUtil.AssertNear(20.0, contact.NorthM, 1e-6, "接触点北向");
            EnuPosition approx = OrientedBoundingBox.ApproximateContact(a, b);
            Assert.Equal(contact.EastM, approx.EastM);
            Assert.Equal(contact.NorthM, approx.NorthM);
            // 旧中点法为 (29.9, 10)，与真实接触相差 >20 m。
            double midE = 0.5 * (a.Center.EastM + b.Center.EastM);
            double midN = 0.5 * (a.Center.NorthM + b.Center.NorthM);
            Assert.True(Math.Sqrt((midE - contact.EastM) * (midE - contact.EastM) + (midN - contact.NorthM) * (midN - contact.NorthM)) > 20.0);
        }

        [Fact]
        public void SeparatedContact_IsMidpointOfClosestPair()
        {
            EnuPosition contact = OrientedBoundingBox.ContactPoint(Box(0, 0, 0, 1, 1), Box(4, 5, 0, 1, 1));
            TestUtil.AssertNear(2.0, contact.EastM, 1e-9);
            TestUtil.AssertNear(2.5, contact.NorthM, 1e-9);
        }

        [Fact]
        public void EvaluatorTContact_FromBowMatchesGeometry()
        {
            // 与验收 ApproximateContact_MidpointMayDivergeFromTrueContact 同构：本船静止，他船从右舷横撞。
            WhatIfVessel own = WhatIfVessel.FromStates("Own", TestUtil.Params(loaM: 120, beamM: 20),
                new[] { new KinematicState(0, 0, 0, 0, 0), new KinematicState(80, 0, 0, 0, 0) }, "Own");
            double v = 12 * 1852.0 / 3600.0;
            WhatIfVessel tgt = WhatIfVessel.FromStates("Tgt", TestUtil.Params(loaM: 100, beamM: 16),
                new[] { new KinematicState(0, 400, 0, 270, 12), new KinematicState(80, 400 - v * 80, 0, 270, 12) }, "Tgt");
            WhatIfSetup setup = new WhatIfSetup(new[] { own, tgt }, "Own", "Tgt", 0, 80);
            ScenarioResult r = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.True(r.Collision);
            Assert.Equal("Tgt", r.Geometry.StrikingVesselId);
            Assert.Equal("右舷", r.Geometry.StruckSide);
            // 他船沿本船中点横线驶来，接触点应在本船舯部（距船首约 60 m），不再是两中心中点。
            TestUtil.AssertNear(60.0, r.Geometry.ContactFromStruckBowM, 1.0, "距船首");
            TestUtil.AssertNear(10.0, r.Geometry.ContactPointEnu.EastM, 0.5, "接触点在本船右舷线上");
        }
    }

    /// <summary>W14.1 回归：重算情景、截断、天线、偏离后 DCPA、锚转首衰减。</summary>
    public class W14_1ScenarioRegressionTests
    {
        [Fact]
        public void DemoS1S3_TrueClearance_StillNearMiss()
        {
            IReadOnlyList<ScenarioResult> results =
                ScenarioEvaluator.EvaluateAll(WhatIfDemoFixture.CreateSetup(), WhatIfDemoFixture.Scenarios());
            ScenarioResult s1 = results.First(r => r.ScenarioId == "S1");
            ScenarioResult s3 = results.First(r => r.ScenarioId == "S3");
            TestUtil.AssertNear(130.4, s1.MinClearanceM, 0.5, "S1 真实净距（验收独立值 130.4–130.5 m）");
            TestUtil.AssertNear(58.8, s3.MinClearanceM, 0.5, "S3 真实净距（验收独立值 58.8 m）");
            Assert.Equal(ScenarioVerdict.NearMiss, s1.Verdict);
            Assert.Equal(ScenarioVerdict.NearMiss, s3.Verdict);
            Assert.Equal(ScenarioVerdict.Collision, results.First(r => r.ScenarioId == "S0").Verdict);
            Assert.Equal(ScenarioVerdict.Collision, results.First(r => r.ScenarioId == "S2").Verdict);
        }

        [Fact]
        public void MinDcpaAfterDeviation_NullForOriginal_AndNotBelowFullPeriod()
        {
            IReadOnlyList<ScenarioResult> results =
                ScenarioEvaluator.EvaluateAll(WhatIfDemoFixture.CreateSetup(), WhatIfDemoFixture.Scenarios());
            Assert.Null(results.First(r => r.ScenarioId == "S0").MinDcpaAfterDeviationNm);
            foreach (ScenarioResult r in results.Where(r => r.ScenarioId != "S0"))
            {
                Assert.True(r.MinDcpaAfterDeviationNm.HasValue, r.ScenarioId);
                Assert.True(r.MinDcpaAfterDeviationNm.Value >= r.MinDcpaNm - 1e-12, r.ScenarioId);
            }
            string md = ScenarioComparison.Build(results).ToMarkdown();
            Assert.Contains("偏离后最小DCPA(nm)", md);
        }

        [Fact]
        public void MinDcpaAfterDeviation_IgnoresSamplesBeforeDivergence()
        {
            // 早期小 DCPA 在偏离前，偏离后两船背离：偏离后最小值应大于全时段最小值。
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s1 = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[1]);
            double divergeTime = s1.Tracks.Values.Where(t => t.Diverged).Min(t => t.DivergeTimeSeconds);
            double expected = s1.Cpa.Samples.Where(x => x.Time.Seconds >= divergeTime - 1e-9).Min(x => x.DcpaNm);
            Assert.Equal(expected, s1.MinDcpaAfterDeviationNm.Value, 12);
        }

        [Fact]
        public void AnchorYawFactor_DecaysToZeroWithSpeed()
        {
            Assert.Equal(1.0, NomotoSimulator.AnchorYawSpeedFactor(6.0, 0.0, 2.0));
            Assert.Equal(1.0, NomotoSimulator.AnchorYawSpeedFactor(2.0, 0.0, 2.0));
            Assert.Equal(0.5, NomotoSimulator.AnchorYawSpeedFactor(1.0, 0.0, 2.0), 12);
            Assert.Equal(0.0, NomotoSimulator.AnchorYawSpeedFactor(0.0, 0.0, 2.0));
            Assert.Equal(0.0, NomotoSimulator.AnchorYawSpeedFactor(0.3, 0.3, 2.0));
            Assert.Contains(new AnchorParams(fullYawSpeedKn: 0.0).Validate(), e => e.Contains("转首满值航速"));
            Assert.Equal(AnchorParams.DefaultFullYawSpeedKn, AnchorParams.Default(70000).FullYawSpeedKn);
        }

        [Fact]
        public void AnchorYaw_StopsAfterShipStops()
        {
            AnchorParams anchor = new AnchorParams(0.0, 0.5, 0.5, 20.0);
            ManeuverParams parameters = TestUtil.Params(anchor: anchor);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                new KinematicState(0.0, 0.0, 0.0, 90.0, 4.0), parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Starboard) },
                120.0, 0.1);
            KinematicState stop = states.First(s => s.SpeedKn <= 0.05);
            KinematicState last = TestUtil.LastState(states);
            double drift = Math.Abs(KinematicState.NormalizeDeg180(last.HeadingDeg - stop.HeadingDeg));
            Assert.True(drift < 0.01, "停船后航向不应继续偏转，实际 " + drift + "°");
            Assert.True(KinematicState.NormalizeDeg180(stop.HeadingDeg - 90.0) > 1.0, "有航速时右锚仍应向右转首");
        }

        [Fact]
        public void Yangze22_Default_TruncatesAndCorrectsAntenna_AssumptionsAndInputs()
        {
            Yangze22Study study = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            Assert.Contains(study.Setup.CaseAssumptions, a => a.Contains("截断") && a.Contains("22:01:54") && a.Contains("t=204 s"));
            Assert.Contains(study.Setup.CaseAssumptions, a => a.Contains("GNSS 天线") && a.Contains("【估计】"));
            SourcedValue yAnt = study.Inputs.First(v => v.Name == "YANGZE 22 GNSS 天线距船首");
            SourcedValue vAnt = study.Inputs.First(v => v.Name == "VEGA DREAM GNSS 天线距船首");
            Assert.Equal(ValueSource.Estimated, yAnt.Source);
            Assert.Equal(ValueSource.Estimated, vAnt.Source);
            Assert.Contains("【估计】", yAnt.Note);
            Assert.Contains("【估计】", vAnt.Note);
            TestUtil.AssertNear(225.0 * 0.70, yAnt.Value, 1.0, "YANGZE 天线距船首 = 0.5L+0.20L");
            Assert.Contains(study.Inputs, v => v.Name == "YANGZE 22 GNSS 天线距中线（右舷为正）" && v.Value == 0.0);

            ScenarioResult s0 = study.EvaluateAll()[0];
            Assert.Contains(s0.Assumptions, a => a.Contains("截断"));
            Assert.Contains(s0.Assumptions, a => a.Contains("GNSS 天线"));
        }

        [Fact]
        public void Yangze22_TruncationIsConfigurable_AndChangesPostCollisionTrack()
        {
            Yangze22Study on = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs(true), 0.0, 0.0);
            Yangze22Study off = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs(false), 0.0, 0.0);
            Assert.Contains(off.Setup.CaseAssumptions, a => a.Contains("未截断"));
            KinematicState a = on.Setup.FindVessel(Yangze22Case.Yangze22Id).SampleAt(230.0);
            KinematicState b = off.Setup.FindVessel(Yangze22Case.Yangze22Id).SampleAt(230.0);
            double shift = Math.Sqrt((a.EastM - b.EastM) * (a.EastM - b.EastM) + (a.NorthM - b.NorthM) * (a.NorthM - b.NorthM));
            Assert.True(shift > 1.0, "截断后 t=230 s 的 YANGZE 22 位置应改变，实际 " + shift + " m");
            // 截断点之前完全一致。
            KinematicState a0 = on.Setup.FindVessel(Yangze22Case.Yangze22Id).SampleAt(150.0);
            KinematicState b0 = off.Setup.FindVessel(Yangze22Case.Yangze22Id).SampleAt(150.0);
            Assert.Equal(a0.EastM, b0.EastM, 9);
            Assert.Equal(a0.NorthM, b0.NorthM, 9);
        }

        [Fact]
        public void AntennaToCenter_ShiftsAlongHeading()
        {
            IReadOnlyList<KinematicState> c = Yangze22Case.AntennaToCenter(
                new[] { new KinematicState(0, 100, 200, 90, 10) }, 200.0, 140.0, 2.0);
            // 首向 90（向东）；天线在中点后 40 m、右舷 2 m → 船中心在天线东 40 m、北 2 m。
            TestUtil.AssertNear(140.0, c[0].EastM, 1e-9);
            TestUtil.AssertNear(202.0, c[0].NorthM, 1e-9);
        }

        [Fact]
        public void Yangze22_ExplicitAntennaInputIsUsed()
        {
            Yangze22Inputs baseInputs = Yangze22CaseTests.LoadInputs();
            List<Yangze22VesselInput> vessels = baseInputs.Vessels.Select(v => new Yangze22VesselInput(
                v.VesselId, v.Name, v.LoaM, v.BeamM, v.GrossTonnage, v.DimensionReference,
                antennaFromBowM: new SourcedValue(v.Name + " GNSS 天线距船首", v.LoaM * 0.5, "m", ValueSource.ReportDirect, "测试：假定报告给出"))).ToList();
            Yangze22Inputs inputs = new Yangze22Inputs(vessels, baseInputs.RudderOrders, baseInputs.CollisionLocation,
                baseInputs.CollisionTimeBeijing, baseInputs.SimEpochLocal, baseInputs.ReportCollisionAngleDeg,
                baseInputs.ReportContactText, baseInputs.CollisionReference, baseInputs.ReportYangze22HeadingDeg,
                baseInputs.ReportVegaDreamHeadingDeg, baseInputs.ReportYangze22SpeedKn, baseInputs.ReportVegaDreamSpeedKn, 300.0);
            Yangze22Study explicitMid = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), inputs);
            Yangze22Study zeroOverride = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), baseInputs, 0.0, 0.0);
            Assert.Contains(explicitMid.Inputs, v => v.Name == "VEGA DREAM GNSS 天线距船首" && v.Source == ValueSource.ReportDirect);
            KinematicState a = explicitMid.Setup.FindVessel(Yangze22Case.VegaDreamId).SampleAt(200.0);
            KinematicState b = zeroOverride.Setup.FindVessel(Yangze22Case.VegaDreamId).SampleAt(200.0);
            Assert.Equal(b.EastM, a.EastM, 9);
            Assert.Equal(b.NorthM, a.NorthM, 9);
        }

        [Fact]
        public void Yangze22_RecomputedScenarios_W14_1()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            ScenarioResult s0 = result.Find("S0");
            Assert.True(s0.Collision);
            // 截断 + 天线名义值（YANGZE 0.20L、VEGA 0.375L）：tc≈210.1 s（22:02:00.1），比报告晚约 6 s；碰撞角≈69°。
            Assert.InRange(s0.TcSeconds.Value, 209.0, 211.5);
            Assert.InRange(s0.Geometry.CollisionAngleDeg, 68.0, 70.0);
            Assert.Equal(Yangze22Case.VegaDreamId, s0.Geometry.StrikingVesselId);
            Assert.Equal("右舷", s0.Geometry.StruckSide);
            Assert.InRange(s0.Geometry.ContactFromStruckBowM, 85.0, 110.0);

            ScenarioResult y5 = result.Find("Y5");
            Assert.Equal(ScenarioVerdict.Avoided, y5.Verdict);
            Assert.True(y5.MinClearanceM > 185.2);
            Assert.Equal(ScenarioVerdict.Avoided, result.Find("Y1+Y5").Verdict);
            ScenarioResult y4 = result.Find("Y4");
            Assert.Equal(ScenarioVerdict.NearMiss, y4.Verdict);
            Assert.InRange(y4.MinClearanceM, 25.0, 40.0);
            // Y1 名义值约 184 m，紧贴 185.2 m 安全线（对天线位置敏感，见 AntennaSensitivity）。
            ScenarioResult y1 = result.Find("Y1");
            Assert.False(y1.Collision);
            Assert.InRange(y1.MinClearanceM, 175.0, 195.0);

            Assert.Contains("22:01:54", string.Join("", result.Original.Assumptions));
            Assert.Contains("未为对齐报告调整任何模型参数", result.OriginalDeviation);
        }

        [Fact]
        public void Yangze22_NoAntennaNoTruncation_ReproducesAcceptanceTrueClearance()
        {
            // 只修 OBB 净距（不截断、天线不改正）时对照验收独立值：Y5 362.9、Y1 219.0、Y4 46.1 m。
            Yangze22Study study = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs(false), 0.0, 0.0);
            IReadOnlyList<ScenarioResult> results = study.EvaluateAll();
            ScenarioResult s0 = results.First(r => r.ScenarioId == "S0");
            Assert.InRange(s0.TcSeconds.Value, 242.0, 243.0);
            ScenarioResult y5 = results.First(r => r.ScenarioId == "Y5");
            Assert.Equal(ScenarioVerdict.Avoided, y5.Verdict);
            // 与 362.9 m 的差来自锚转首随航速衰减（W14.1 第 5 项）以及采样网格。
            Assert.InRange(y5.MinClearanceM, 350.0, 370.0);
            TestUtil.AssertNear(219.0, results.First(r => r.ScenarioId == "Y1").MinClearanceM, 1.0, "Y1");
            TestUtil.AssertNear(46.1, results.First(r => r.ScenarioId == "Y4").MinClearanceM, 1.0, "Y4");
        }

        [Fact]
        public void Yangze22_AntennaSensitivity_Range()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            Assert.Equal(4, result.AntennaSensitivity.Count);
            AntennaSensitivityRow none = result.AntennaSensitivity[0];
            AntennaSensitivityRow low = result.AntennaSensitivity[1];
            AntennaSensitivityRow nominal = result.AntennaSensitivity[2];
            AntennaSensitivityRow high = result.AntennaSensitivity[3];
            Assert.Equal(0.35, low.VegaAftOfMidshipRatio);
            Assert.Equal(0.40, high.VegaAftOfMidshipRatio);
            Assert.True(none.Collision && low.Collision && nominal.Collision && high.Collision);
            // 只截断不改正天线：约晚 26 s；VEGA 天线越靠后，接触越早。
            Assert.InRange(none.DelayVsReportSec.Value, 25.0, 28.0);
            Assert.True(high.DelayVsReportSec.Value < nominal.DelayVsReportSec.Value);
            Assert.True(nominal.DelayVsReportSec.Value < low.DelayVsReportSec.Value);
            // 验收参考：0.40L 约晚 4.8 s，碰撞角约 69°。
            Assert.InRange(high.DelayVsReportSec.Value, 4.0, 6.0);
            foreach (AntennaSensitivityRow row in result.AntennaSensitivity)
            {
                Assert.InRange(row.CollisionAngleDeg.Value, 68.0, 70.0);
                Assert.True(row.ClearanceAtReportTimeM > 0.0, "报告时刻仍未接触：" + row);
                Assert.True(row.ScenarioSummaries.ContainsKey("Y1"));
            }
            Assert.Equal(nominal.TcSeconds, result.Original.TcSeconds);
        }
    }
}
