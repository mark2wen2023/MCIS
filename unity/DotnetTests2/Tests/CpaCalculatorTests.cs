using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Pure.Tests
{
    /// <summary>
    /// M5 CpaCalculator 单元测试：覆盖迎头对遇、交叉相遇、追越、平行同速退化、背向驶离解析解，
    /// 以及 1000 组随机场景下平面向量法与论文 thesis.txt 3.4 节矢量三角形公式法的一致性验证。
    /// </summary>
    public sealed class CpaCalculatorTests
    {
        [Fact]
        public void HeadOnEncounter_AnalyticalSolution_MatchesVectorAndTriangle()
        {
            // 对遇（Head-on）：本船在 (0, 0) 向北 (0°) 12 kn，目标船在正北 4.0 nm (0, 4) 向南 (180°) 8 kn
            // 相对速度 Vr = 20 kn，DCPA = 0 nm，TCPA = (4.0 / 20.0) * 60 = 12.0 min
            Double2 ownPosNm = new Double2(0.0, 0.0);
            Double2 ownVelKn = new Double2(0.0, 12.0);
            Double2 targetPosNm = new Double2(0.0, 4.0);
            Double2 targetVelKn = new Double2(0.0, -8.0);

            CpaResult vec = CpaCalculator.CalculateByVector(ownPosNm, ownVelKn, targetPosNm, targetVelKn);
            CpaResult tri = CpaCalculator.CalculateByTriangle(
                voKn: 12.0, coDeg: 0.0,
                vtKn: 8.0, ctDeg: 180.0,
                azimuthQDeg: 0.0, distanceNm: 4.0);

            Assert.False(vec.IsDegenerate);
            Assert.False(vec.IsDiverging);
            Assert.Equal(4.0, vec.CurrentDistanceNm, 9);
            Assert.Equal(0.0, vec.DcpaNm, 9);
            Assert.Equal(12.0, vec.TcpaMin, 9);

            Assert.Equal(vec.DcpaNm, tri.DcpaNm, 9);
            Assert.Equal(vec.TcpaMin, tri.TcpaMin, 9);
        }

        [Fact]
        public void CrossingEncounter_AnalyticalSolution_MatchesExactValues()
        {
            // 正交交叉相遇（Crossing）：
            // 本船在 (0, 0) 向北 (0°) 10 kn
            // 目标船在 (1.5 nm, 2.0 nm) 向西 (270°) 10 kn
            // r0 = (1.5, 2.0) nm => D = 2.5 nm；v = (-10, -10) kn => |v|² = 200, Vr = 10*sqrt(2) kn
            // r0 · v = -15 - 20 = -35 => TCPA = (35 / 200) * 60 = 10.5 min
            // r(TCPA) = (1.5 - 1.75, 2.0 - 1.75) = (-0.25, 0.25) nm => DCPA = 0.25 * sqrt(2) nm
            Double2 ownPosNm = new Double2(0.0, 0.0);
            Double2 ownVelKn = new Double2(0.0, 10.0);
            Double2 targetPosNm = new Double2(1.5, 2.0);
            Double2 targetVelKn = new Double2(-10.0, 0.0);

            CpaResult vec = CpaCalculator.CalculateByVector(ownPosNm, ownVelKn, targetPosNm, targetVelKn);

            double qDeg = Math.Atan2(1.5, 2.0) * (180.0 / Math.PI);
            CpaResult tri = CpaCalculator.CalculateByTriangle(
                voKn: 10.0, coDeg: 0.0,
                vtKn: 10.0, ctDeg: 270.0,
                azimuthQDeg: qDeg, distanceNm: 2.5);

            double expectedDcpaNm = 0.25 * Math.Sqrt(2.0);
            double expectedTcpaMin = 10.5;

            Assert.Equal(expectedDcpaNm, vec.DcpaNm, 9);
            Assert.Equal(expectedTcpaMin, vec.TcpaMin, 9);
            Assert.Equal(expectedDcpaNm, tri.DcpaNm, 9);
            Assert.Equal(expectedTcpaMin, tri.TcpaMin, 9);
        }

        [Fact]
        public void OvertakingEncounter_AnalyticalSolution_MatchesExactValues()
        {
            // 追越（Overtaking）：
            // 本船在 (0, 0) 向北 (0°) 18 kn；目标船在 (0.2 nm, 1.5 nm) 向北 (0°) 6 kn
            // 相对位置 r0 = (0.2, 1.5) nm，相对速度 v = (0, -12) kn
            // DCPA = 0.2 nm（正横距离），TCPA = (1.5 / 12.0) * 60 = 7.5 min
            Double2 ownPosNm = new Double2(0.0, 0.0);
            Double2 ownVelKn = new Double2(0.0, 18.0);
            Double2 targetPosNm = new Double2(0.2, 1.5);
            Double2 targetVelKn = new Double2(0.0, 6.0);

            CpaResult vec = CpaCalculator.CalculateByVector(ownPosNm, ownVelKn, targetPosNm, targetVelKn);

            double dNm = Math.Sqrt(0.2 * 0.2 + 1.5 * 1.5);
            double qDeg = Math.Atan2(0.2, 1.5) * (180.0 / Math.PI);
            CpaResult tri = CpaCalculator.CalculateByTriangle(
                voKn: 18.0, coDeg: 0.0,
                vtKn: 6.0, ctDeg: 0.0,
                azimuthQDeg: qDeg, distanceNm: dNm);

            Assert.Equal(0.2, vec.DcpaNm, 9);
            Assert.Equal(7.5, vec.TcpaMin, 9);
            Assert.Equal(0.2, tri.DcpaNm, 9);
            Assert.Equal(7.5, tri.TcpaMin, 9);
        }

        [Fact]
        public void ParallelEqualSpeed_DegenerateCase_HandlesZeroRelativeVelocitySafely()
        {
            // 平行同速（|v| = 0 < 0.01 m/s）：两船均以 12 kn 航向 45° 航行，间距 0.8 nm
            VesselMotionState own = new VesselMotionState(0.0, 0.0, 12.0, 45.0);
            VesselMotionState target = new VesselMotionState(0.8, 0.0, 12.0, 45.0);

            CpaResult vec = CpaCalculator.CalculateFromStates(own, target);
            CpaResult tri = CpaCalculator.CalculateByTriangle(12.0, 45.0, 12.0, 45.0, 90.0, 0.8);

            Assert.True(vec.IsDegenerate);
            Assert.False(vec.IsDiverging);
            Assert.Equal(0.8, vec.DcpaNm, 9);
            Assert.Equal(vec.CurrentDistanceM, vec.DcpaM, 9);
            Assert.False(double.IsNaN(vec.TcpaSec));
            Assert.True(double.IsPositiveInfinity(vec.TcpaSec));

            Assert.True(tri.IsDegenerate);
            Assert.Equal(0.8, tri.DcpaNm, 9);
            Assert.True(double.IsPositiveInfinity(tri.TcpaMin));
        }

        [Fact]
        public void DivergingEncounter_NegativeTcpa_SetsIsDivergingTrue()
        {
            // 背向驶离：已过最近会遇点
            Double2 ownPosNm = new Double2(0.0, 0.0);
            Double2 ownVelKn = new Double2(0.0, -10.0);
            Double2 targetPosNm = new Double2(0.3, 1.0);
            Double2 targetVelKn = new Double2(0.0, 10.0);

            CpaResult vec = CpaCalculator.CalculateByVector(ownPosNm, ownVelKn, targetPosNm, targetVelKn);
            Assert.True(vec.IsDiverging);
            Assert.Equal(-3.0, vec.TcpaMin, 9);
            Assert.Equal(0.3, vec.DcpaNm, 9);
        }

        [Fact]
        public void Random1000Scenarios_VectorAndTriangleFormulas_MatchWithin1eMinus6()
        {
            // 随机 1000 个非退化场景（|v| >= 0.1 kn），验证向量法与论文 3.4 节三角公式 DCPA、TCPA 误差 < 1e-6
            Random rng = new Random(20261111);
            int verifiedCount = 0;

            while (verifiedCount < 1000)
            {
                double voKn = rng.NextDouble() * 25.0;
                double coDeg = rng.NextDouble() * 360.0;
                double vtKn = rng.NextDouble() * 25.0;
                double ctDeg = rng.NextDouble() * 360.0;
                double qDeg = rng.NextDouble() * 360.0;
                double distNm = 0.05 + rng.NextDouble() * 15.0;

                double coRad = coDeg * (Math.PI / 180.0);
                double ctRad = ctDeg * (Math.PI / 180.0);
                double qRad = qDeg * (Math.PI / 180.0);

                Double2 ownPosNm = new Double2(rng.NextDouble() * 10.0 - 5.0, rng.NextDouble() * 10.0 - 5.0);
                Double2 targetPosNm = new Double2(
                    ownPosNm.X + distNm * Math.Sin(qRad),
                    ownPosNm.Y + distNm * Math.Cos(qRad));

                Double2 ownVelKn = new Double2(voKn * Math.Sin(coRad), voKn * Math.Cos(coRad));
                Double2 targetVelKn = new Double2(vtKn * Math.Sin(ctRad), vtKn * Math.Cos(ctRad));

                if ((targetVelKn - ownVelKn).Length < 0.1)
                {
                    continue; // 排除 |v| ≈ 0 场景
                }

                CpaResult vec = CpaCalculator.CalculateByVector(ownPosNm, ownVelKn, targetPosNm, targetVelKn);
                CpaResult tri = CpaCalculator.CalculateByTriangle(voKn, coDeg, vtKn, ctDeg, qDeg, distNm);

                Assert.False(vec.IsDegenerate);
                Assert.False(tri.IsDegenerate);
                Assert.True(Math.Abs(vec.DcpaNm - tri.DcpaNm) < 1e-6,
                    $"Scenario #{verifiedCount}: DcpaNm diff = {Math.Abs(vec.DcpaNm - tri.DcpaNm)}");
                Assert.True(Math.Abs(vec.TcpaMin - tri.TcpaMin) < 1e-6,
                    $"Scenario #{verifiedCount}: TcpaMin diff = {Math.Abs(vec.TcpaMin - tri.TcpaMin)}");

                verifiedCount++;
            }

            Assert.Equal(1000, verifiedCount);
        }
    }
}
