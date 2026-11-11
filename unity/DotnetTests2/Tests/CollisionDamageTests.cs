using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Fixtures;
using Mcis.Simulation.Damage;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class CollisionDamageTests
    {
        [Fact]
        public void ObbClearance_SeparatedAlignedShips_EqualsCenterDistanceMinusHalfLengths()
        {
            var a = new OrientedBoundingBox(new EnuPosition(0, 0, 0), 0.0, 50.0, 10.0);
            var b = new OrientedBoundingBox(new EnuPosition(0, 200.0, 0), 0.0, 50.0, 10.0);
            double c = OrientedBoundingBox.Clearance(a, b);
            Assert.InRange(c, 99.5, 100.5);
        }

        [Fact]
        public void ObbClearance_CornerToCorner_IsTrueEuclideanDistance()
        {
            // W14.1：分离时返回两矩形真实最小距离（旧 SAT 轴间隙为 2 m）。
            var a = new OrientedBoundingBox(new EnuPosition(0, 0, 0), 0.0, 1.0, 1.0);
            var b = new OrientedBoundingBox(new EnuPosition(4, 5, 0), 0.0, 1.0, 1.0);
            Assert.Equal(Math.Sqrt(13.0), OrientedBoundingBox.Clearance(a, b), 9);
        }

        [Fact]
        public void ObbContact_TCollision_IsOnStruckSideNotCenterMidpoint()
        {
            var a = new OrientedBoundingBox(new EnuPosition(0, 0, 0), 0.0, 60.0, 10.0);
            var b = new OrientedBoundingBox(new EnuPosition(59.8, 20, 0), 270.0, 50.0, 8.0);
            EnuPosition c = OrientedBoundingBox.ApproximateContact(a, b);
            Assert.Equal(9.9, c.EastM, 6);
            Assert.Equal(20.0, c.NorthM, 6);
        }

        [Fact]
        public void ObbClearance_Overlapping_IsNegative()
        {
            var a = new OrientedBoundingBox(new EnuPosition(0, 0, 0), 90.0, 80.0, 15.0);
            var b = new OrientedBoundingBox(new EnuPosition(20, 0, 0), 0.0, 80.0, 15.0);
            Assert.True(OrientedBoundingBox.Clearance(a, b) < 0.0);
        }

        [Fact]
        public void BinarySearch_FirstContact_WithinPrecision()
        {
            // 两艘 100m 长（半长 50m）、20m 宽的船沿北向相向：A 从 y=-400 以 10 m/s 向北，B 从 y=400 以 10 m/s 向南。
            // 中心距 = 800 - 20 t；OBB 接触当中心距 = 50+50 = 100 → t = 35 s。
            Func<double, CollisionBodyState> a = t => Body("A", 0, -400 + 10 * t, 0, 0, 10, 100, 20, 10000);
            Func<double, CollisionBodyState> b = t => Body("B", 0, 400 - 10 * t, 180, 0, -10, 100, 20, 10000);
            var tc = CollisionDetector.FindFirstContactTime(a, b, SimTime.Zero, new SimTime(60), 0.05, 1.0);
            Assert.True(tc.HasValue);
            Assert.InRange(tc.Value.Seconds, 34.95, 35.05);
            Assert.True(OrientedBoundingBox.Clearance(a(tc.Value.Seconds).Obb, b(tc.Value.Seconds).Obb) <= 0.0);
            Assert.True(OrientedBoundingBox.Clearance(a(tc.Value.Seconds - 0.05).Obb, b(tc.Value.Seconds - 0.05).Obb) > 0.0);
        }

        [Fact]
        public void EquivalentEnergy_HeadOnEqualMass_IsHalfMuVnSquared()
        {
            // 纵向相对，v_n = 10 m/s，各 1000 t，纵向 C_added=0.05 → m' = 1.05e6 kg，m_eq = 0.525e6，E = 0.5*0.525e6*100 = 2.625e7 J
            var a = Body("A", 0, 0, 0, 0, 5, 100, 20, 1000);
            var b = Body("B", 0, 50, 180, 0, -5, 100, 20, 1000);
            var assess = DamageModel.Assess(a, b);
            Assert.InRange(assess.RelativeNormalSpeedMps, 9.5, 10.5);
            Assert.InRange(assess.EnergyMJ, 20.0, 40.0);
            Assert.True(assess.Severity >= DamageSeverity.Minor);
        }

        [Fact]
        public void OrificeFlow_MatchesFormula_AndBakeIsDeterministic()
        {
            double q = FloodingModel.OrificeFlowM3PerSec(0.60, 6.4, 2.5);
            double expected = 0.60 * 6.4 * Math.Sqrt(2.0 * 9.81 * 2.5);
            Assert.Equal(expected, q, 9);

            var lily = LilyMaryDemo.CreateLily();
            var ev = new CollisionEvent(
                "t", new SimTime(10), "mary", "vessel_lily", false,
                LilyMaryDemo.Origin, new EnuPosition(0, 0, 0), Double3.Zero,
                70f, 5.8f, 312.0, DamageSeverity.SevereFlooding, 6.4f, 2.5f);
            var state = new CollisionBodyState("vessel_lily", new EnuPosition(0, 0, 0), 179, Double2.Zero, lily.LoaM, lily.BeamM, lily.DisplacementTons, false);
            var t1 = DamageBakeTrack.BakeFlooding("vessel_lily", ev, lily, state, new SimTime(20), 10);
            var t2 = DamageBakeTrack.BakeFlooding("vessel_lily", ev, lily, state, new SimTime(20), 10);
            Assert.Equal(t1.Keyframes.Count, t2.Keyframes.Count);
            var s1 = t1.SampleAt(new SimTime(15.05));
            var s2 = t2.SampleAt(new SimTime(15.05));
            Assert.Equal(s1.FloodedWaterMassTons, s2.FloodedWaterMassTons, 6);
            Assert.True(s1.FloodedWaterMassTons > 0);
            Assert.True(s1.SinkHeaveM > 0);

            var profile = new ScriptedSinkProfile("vessel_lily", new SimTime(10), 100, 22f, 3f, 2.1f);
            var baked = DamageBakeTrack.BakeScripted(profile, state, 10);
            var mid = baked.SampleAt(new SimTime(60));
            Assert.InRange(mid.RollDeg, 5.0, 22.0);
            var end = baked.SampleAt(new SimTime(110));
            Assert.Equal(22.0, end.RollDeg, 3);
            Assert.Equal(2.1, end.SinkHeaveM, 3);
        }

        private static CollisionBodyState Body(
            string id, double e, double n, double hdg, double ve, double vn, float loa, float beam, float tons)
        {
            return new CollisionBodyState(id, new EnuPosition(e, n, 0), hdg, new Double2(ve, vn), loa, beam, tons, false);
        }
    }
}
