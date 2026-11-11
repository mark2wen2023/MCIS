using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class CollisionGeometryAcceptanceTests
    {
        [Fact]
        public void HeadOnCollisionTime_MatchesAnalyticWithinPrecision()
        {
            // 两船对驶，解析接触时刻：中心距 1000 m，半长各 50 m，合速度 20 kn。
            const double loa = 100.0;
            const double beam = 20.0;
            const double speed = 10.0;
            WhatIfVessel northbound = W14AccFixture.StraightVessel("N", 0, 0, 0, speed, loa, beam, 0, 200);
            WhatIfVessel southbound = W14AccFixture.StraightVessel("S", 0, 1000, 180, speed, loa, beam, 0, 200);
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(northbound, southbound, 0, 200);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());

            double closingMps = 2.0 * speed * W14AccFixture.MpsPerKnot;
            double analytic = (1000.0 - loa) / closingMps;
            Assert.True(result.Collision, "对驶应碰撞");
            Assert.NotNull(result.TcSeconds);
            Assert.InRange(result.TcSeconds.Value, analytic, analytic + setup.CollisionPrecisionSec + 1e-3);

            CollisionBodyState At(double t, WhatIfVessel v)
            {
                CounterfactualTrack track = result.Tracks[v.Id];
                return track.ToBodyState(t);
            }
            double tc = result.TcSeconds.Value;
            double clearTc = OrientedBoundingBox.Clearance(At(tc, northbound).Obb, At(tc, southbound).Obb);
            double clearBefore = OrientedBoundingBox.Clearance(
                At(tc - setup.CollisionPrecisionSec, northbound).Obb,
                At(tc - setup.CollisionPrecisionSec, southbound).Obb);
            Assert.True(clearTc <= 0.0, "tc 处应已接触，净距=" + clearTc);
            Assert.True(clearBefore > 0.0, "tc-0.05 s 处不应接触，净距=" + clearBefore);
        }

        [Fact]
        public void IndependentGeometry_AgreesOnAngleSideAndBowDistance_ForTBone()
        {
            // 本船向北，他船从右向左撞本船右舷中部附近。
            WhatIfVessel own = W14AccFixture.StraightVessel("Own", 0, 0, 0, 0.0, 120, 20, 0, 80);
            WhatIfVessel tgt = W14AccFixture.StraightVessel("Tgt", 400, 0, 270, 12, 100, 16, 0, 80);
            WhatIfSetup setup = W14AccFixture.TwoShipSetup(own, tgt, 0, 80);
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.True(result.Collision);
            CollisionGeometry g = result.Geometry;
            Assert.NotNull(g);

            KinematicState ownS = result.Tracks["Own"].SampleAt(g.TcSeconds);
            KinematicState tgtS = result.Tracks["Tgt"].SampleAt(g.TcSeconds);
            double independentAngle = W14AccFixture.AcuteHeadingAngleDeg(ownS.HeadingDeg, tgtS.HeadingDeg);
            Assert.InRange(Math.Abs(g.CollisionAngleDeg - independentAngle), 0.0, 0.2);
            Assert.InRange(g.CollisionAngleDeg, 85.0, 95.0);

            // 撞击船应为船首更近接触点的那一艘（他船）。
            Assert.Equal("Tgt", g.StrikingVesselId);
            Assert.Equal("Own", g.StruckVesselId);
            Assert.Equal("右舷", g.StruckSide);

            EnuPosition closest = W14AccFixture.ClosestPointContact(
                W14AccFixture.BoxOf(ownS, 120, 20),
                W14AccFixture.BoxOf(tgtS, 100, 16));
            string sideByClosest = W14AccFixture.IndependentStruckSide(ownS, closest);
            Assert.Equal("右舷", sideByClosest);
            double fromBowClosest = W14AccFixture.IndependentContactFromBowM(ownS, 120, closest);
            // 独立最近点接触部位应在船中附近；允许与中点近似法有偏差，但量级应合理。
            Assert.InRange(fromBowClosest, 20.0, 100.0);
            Assert.InRange(g.ContactFromStruckBowM, 0.0, 120.0);
        }

        [Fact]
        [Trait("Category", "KnownDefect")]
        [Trait("Defect", "W14-D01")]
        public void ApproximateContact_MidpointMayDivergeFromTrueContact()
        {
            // 记录实现使用两中心连线中点作为接触点，与独立最近点的偏差。
            WhatIfVessel own = W14AccFixture.StraightVessel("Own", 0, 0, 0, 0.0, 120, 20, 0, 80);
            WhatIfVessel tgt = W14AccFixture.StraightVessel("Tgt", 400, 0, 270, 12, 100, 16, 0, 80);
            ScenarioResult result = ScenarioEvaluator.Evaluate(
                W14AccFixture.TwoShipSetup(own, tgt, 0, 80), WhatIfScenario.Original());
            CollisionGeometry g = result.Geometry;
            KinematicState ownS = result.Tracks["Own"].SampleAt(g.TcSeconds);
            KinematicState tgtS = result.Tracks["Tgt"].SampleAt(g.TcSeconds);
            EnuPosition closest = W14AccFixture.ClosestPointContact(
                W14AccFixture.BoxOf(ownS, 120, 20),
                W14AccFixture.BoxOf(tgtS, 100, 16));
            double de = g.ContactPointEnu.EastM - closest.EastM;
            double dn = g.ContactPointEnu.NorthM - closest.NorthM;
            double err = Math.Sqrt(de * de + dn * dn);
            double fromBowImpl = g.ContactFromStruckBowM;
            double fromBowTrue = W14AccFixture.IndependentContactFromBowM(ownS, 120, closest);
            // 中点法在 T 型碰撞上通常偏差几十米；若超过 15 m 记为一般缺陷。
            if (err > 15.0 || Math.Abs(fromBowImpl - fromBowTrue) > 15.0)
            {
                Assert.Fail(
                    "W14-contact-approx：ApproximateContact 为两中心中点，与独立最近点相差 " +
                    err.ToString("F1") + " m；距船首 实现 " + fromBowImpl.ToString("F1") +
                    " m / 独立 " + fromBowTrue.ToString("F1") + " m");
            }
        }

        [Fact]
        public void DemoS0_IndependentGeometry_AgreesOnSide()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            Assert.True(s0.Collision);
            CollisionGeometry g = s0.Geometry;
            Assert.NotNull(g);

            if (g.IsBowToBow)
            {
                Assert.Equal(string.Empty, g.StrikingVesselId);
                Assert.Equal(string.Empty, g.StruckVesselId);
                Assert.Equal(CollisionGeometry.BowToBowText, g.StruckSide);
                KinematicState mary = s0.Tracks[WhatIfDemoFixture.MaryId].SampleAt(g.TcSeconds);
                KinematicState lily = s0.Tracks[WhatIfDemoFixture.LilyId].SampleAt(g.TcSeconds);
                double angle = W14AccFixture.AcuteHeadingAngleDeg(mary.HeadingDeg, lily.HeadingDeg);
                Assert.InRange(Math.Abs(g.CollisionAngleDeg - angle), 0.0, 0.2);

                EnuPosition maryBow = W14AccFixture.BowPoint(mary, 120.0);
                EnuPosition lilyBow = W14AccFixture.BowPoint(lily, 98.0);
                double dMary = Distance(maryBow, g.ContactPointEnu);
                double dLily = Distance(lilyBow, g.ContactPointEnu);
                Assert.True(dMary < CollisionGeometry.BowToBowThresholdM(120.0));
                Assert.True(dLily < CollisionGeometry.BowToBowThresholdM(98.0));
                Assert.Contains("船首对船首", g.Description);
                return;
            }

            KinematicState striking = s0.Tracks[g.StrikingVesselId].SampleAt(g.TcSeconds);
            KinematicState struck = s0.Tracks[g.StruckVesselId].SampleAt(g.TcSeconds);
            double loaStruck = g.StruckVesselId == WhatIfDemoFixture.MaryId ? 120.0 : 98.0;
            double beamStruck = g.StruckVesselId == WhatIfDemoFixture.MaryId ? 20.0 : 16.0;
            double loaStrike = g.StrikingVesselId == WhatIfDemoFixture.MaryId ? 120.0 : 98.0;
            double beamStrike = g.StrikingVesselId == WhatIfDemoFixture.MaryId ? 20.0 : 16.0;

            double angleSingle = W14AccFixture.AcuteHeadingAngleDeg(striking.HeadingDeg, struck.HeadingDeg);
            Assert.InRange(Math.Abs(g.CollisionAngleDeg - angleSingle), 0.0, 0.2);

            EnuPosition closest = W14AccFixture.ClosestPointContact(
                W14AccFixture.BoxOf(striking, loaStrike, beamStrike),
                W14AccFixture.BoxOf(struck, loaStruck, beamStruck));
            Assert.Equal(W14AccFixture.IndependentStruckSide(struck, closest), g.StruckSide);

            EnuPosition strikeBow = W14AccFixture.BowPoint(striking, loaStrike);
            EnuPosition struckBow = W14AccFixture.BowPoint(struck, loaStruck);
            double dStrike = Distance(strikeBow, closest);
            double dStruck = Distance(struckBow, closest);
            if (Math.Abs(dStrike - dStruck) > 0.5)
            {
                string expected = dStrike < dStruck ? g.StrikingVesselId : g.StruckVesselId;
                Assert.Equal(expected, g.StrikingVesselId);
            }
        }

        [Fact]
        public void SatClearance_CanUnderestimateTrueSeparation()
        {
            // W14.1：分离时 Clearance 改为真实欧氏最小距离，应与独立点-边穷举一致。
            WhatIfVessel a = W14AccFixture.StraightVessel("A", 0, 0, 20, 10, 120, 20, 0, 200);
            WhatIfVessel b = W14AccFixture.StraightVessel("B", 250, 80, 20, 10, 100, 16, 0, 200);
            double maxAbsError = 0.0;
            int compared = 0;
            for (double t = 0; t <= 200; t += 2)
            {
                OrientedBoundingBox ba = W14AccFixture.BoxOf(a.SampleAt(t), 120, 20);
                OrientedBoundingBox bb = W14AccFixture.BoxOf(b.SampleAt(t), 100, 16);
                double clearance = OrientedBoundingBox.Clearance(ba, bb);
                double truth = W14AccFixture.TrueObbDistance(ba, bb);
                if (clearance > 0.0 && truth > 0.0)
                {
                    compared++;
                    maxAbsError = Math.Max(maxAbsError, Math.Abs(clearance - truth));
                }
            }
            Assert.True(compared > 0, "应有分离采样用于核对真实净距");
            Assert.True(maxAbsError < 0.05,
                "分离时 Clearance 应等于真实净距，最大差=" + maxAbsError.ToString("F4") + " m");
        }

        private static double Distance(EnuPosition a, EnuPosition b)
        {
            double de = a.EastM - b.EastM;
            double dn = a.NorthM - b.NorthM;
            return Math.Sqrt(de * de + dn * dn);
        }
    }
}
