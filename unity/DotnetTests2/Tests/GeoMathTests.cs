using System;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Xunit;

namespace Mcis.Pure.Tests
{
    /// <summary>
    /// M3 Mcis.Domain.Geo（GeoMath 与 LocalEnuGeoConverter）单元测试。
    /// </summary>
    public class GeoMathTests
    {
        [Fact]
        public void KnownPoints_Wgs84ToEcef_And_Reverse_MatchExactValues()
        {
            // 赤道本初子午线交点 (0°, 0°, 0m) -> (6378137, 0, 0)
            Double3 eqPrime = GeoMath.Wgs84ToEcef(new GeoCoord(0.0, 0.0, 0.0));
            Assert.Equal(6378137.0, eqPrime.X, 6);
            Assert.Equal(0.0, eqPrime.Y, 9);
            Assert.Equal(0.0, eqPrime.Z, 9);

            // 赤道东经 90° (90°, 0°, 100m) -> (0, 6378237, 0)
            Double3 eqEast90 = GeoMath.Wgs84ToEcef(new GeoCoord(90.0, 0.0, 100.0));
            Assert.Equal(0.0, eqEast90.X, 6);
            Assert.Equal(6378137.0 + 100.0, eqEast90.Y, 6);
            Assert.Equal(0.0, eqEast90.Z, 9);

            // 北极点 (0°, 90°, 0m) -> (0, 0, b)
            Double3 northPole = GeoMath.Wgs84ToEcef(new GeoCoord(0.0, 90.0, 0.0));
            Assert.Equal(0.0, northPole.X, 6);
            Assert.Equal(0.0, northPole.Y, 6);
            Assert.Equal(GeoMath.SemiMinorAxisB, northPole.Z, 6);

            GeoCoord northBack = GeoMath.EcefToWgs84(northPole);
            Assert.Equal(90.0, northBack.LatDeg, 9);
            Assert.Equal(0.0, northBack.HeightM, 6);

            // 南极点 (0°, -90°, 250m) -> (0, 0, -(b + 250))
            Double3 southPole = GeoMath.Wgs84ToEcef(new GeoCoord(0.0, -90.0, 250.0));
            Assert.Equal(0.0, southPole.X, 6);
            Assert.Equal(0.0, southPole.Y, 6);
            Assert.Equal(-(GeoMath.SemiMinorAxisB + 250.0), southPole.Z, 6);

            GeoCoord southBack = GeoMath.EcefToWgs84(southPole);
            Assert.Equal(-90.0, southBack.LatDeg, 9);
            Assert.Equal(250.0, southBack.HeightM, 6);
        }

        [Theory]
        // 肇庆西江段与珠江口海域多点
        [InlineData(112.4651, 23.0472, 8.5)]
        [InlineData(113.7633, 22.3614, 0.0)]
        [InlineData(113.5500, 22.1500, -15.0)]
        [InlineData(114.1694, 22.2855, 50.0)]
        // 赤道与低纬（含负高程 -100m 与高空 8000m）
        [InlineData(0.0, 0.0, 0.0)]
        [InlineData(120.5, 0.0, -100.0)]
        [InlineData(-78.4678, -0.1807, 2850.0)]
        // 中高纬与南北两极附近高纬（含 -100m 至 8000m 高程）
        [InlineData(86.9250, 27.9881, 8000.0)]
        [InlineData(18.9553, 69.6492, -50.0)]
        [InlineData(15.6397, 89.9950, 120.0)]
        [InlineData(-135.0000, -89.9990, 2800.0)]
        [InlineData(179.9999, -45.123456, 500.0)]
        [InlineData(-179.9999, 45.123456, -100.0)]
        public void Wgs84_Ecef_RoundTrip_ErrorWithin1e9DegAnd1Mm(double lonDeg, double latDeg, double heightM)
        {
            GeoCoord original = new GeoCoord(lonDeg, latDeg, heightM);
            Double3 ecef = GeoMath.Wgs84ToEcef(original);
            GeoCoord recovered = GeoMath.EcefToWgs84(ecef);
            Double3 ecefRecovered = GeoMath.Wgs84ToEcef(recovered);

            Assert.True(Math.Abs(recovered.LonDeg - original.LonDeg) < 1e-9,
                $"Lon error too large: {Math.Abs(recovered.LonDeg - original.LonDeg)}");
            Assert.True(Math.Abs(recovered.LatDeg - original.LatDeg) < 1e-9,
                $"Lat error too large: {Math.Abs(recovered.LatDeg - original.LatDeg)}");
            Assert.True(Math.Abs(recovered.HeightM - original.HeightM) < 1e-3,
                $"Height error too large: {Math.Abs(recovered.HeightM - original.HeightM)} m");
            Assert.True((ecefRecovered - ecef).Length < 1e-3,
                $"ECEF position error too large: {(ecefRecovered - ecef).Length} m");
        }

        [Fact]
        public void Enu_DirectionCorrectness_NorthEastUp_MatchesPhysicalSense()
        {
            // 以珠江口桂山岛附近为原点
            GeoCoord origin = new GeoCoord(113.8000, 22.1500, 0.0);
            LocalEnuGeoConverter converter = new LocalEnuGeoConverter(origin, seaLevelOffsetM: -3.5);

            // 原点自身 ENU 应为 (0, 0, 0)
            EnuPosition originEnu = converter.Wgs84ToEnu(origin);
            Assert.True(Math.Abs(originEnu.EastM) < 1e-9);
            Assert.True(Math.Abs(originEnu.NorthM) < 1e-9);
            Assert.True(Math.Abs(originEnu.UpM) < 1e-9);

            // 向正北移动 0.01 度（约 1.11 km）：NorthM > 1000m，|EastM| < 1mm
            GeoCoord northPoint = new GeoCoord(origin.LonDeg, origin.LatDeg + 0.01, origin.HeightM);
            EnuPosition northEnu = converter.Wgs84ToEnu(northPoint);
            Assert.True(northEnu.NorthM > 1100.0 && northEnu.NorthM < 1120.0);
            Assert.True(Math.Abs(northEnu.EastM) < 1e-6);

            // 向正东移动 0.01 度（约 1.03 km）：EastM > 1000m，|NorthM| < 1m（子午线收敛微量）
            GeoCoord eastPoint = new GeoCoord(origin.LonDeg + 0.01, origin.LatDeg, origin.HeightM);
            EnuPosition eastEnu = converter.Wgs84ToEnu(eastPoint);
            Assert.True(eastEnu.EastM > 1020.0 && eastEnu.EastM < 1040.0);
            Assert.True(Math.Abs(eastEnu.NorthM) < 0.2);

            // 垂直升高 50m：UpM ≈ 50m，EastM=0, NorthM=0
            GeoCoord upPoint = new GeoCoord(origin.LonDeg, origin.LatDeg, origin.HeightM + 50.0);
            EnuPosition upEnu = converter.Wgs84ToEnu(upPoint);
            Assert.Equal(50.0, upEnu.UpM, 6);
            Assert.True(Math.Abs(upEnu.EastM) < 1e-6);
            Assert.True(Math.Abs(upEnu.NorthM) < 1e-6);
        }

        [Fact]
        public void Enu_And_UnityLeftHanded_RoundTrip_PreservesCoordinates()
        {
            // 肇庆西江原点
            GeoCoord origin = new GeoCoord(112.4651, 23.0472, 5.0);
            LocalEnuGeoConverter converter = new LocalEnuGeoConverter(origin, seaLevelOffsetM: -2.0);

            EnuPosition[] testEnus = new EnuPosition[]
            {
                new EnuPosition(0.0, 0.0, 0.0),
                new EnuPosition(1523.45, -2840.12, 12.5),
                new EnuPosition(-9850.0, 14200.0, -5.0),
                new EnuPosition(350.25, 890.75, 0.0)
            };

            for (int i = 0; i < testEnus.Length; i++)
            {
                EnuPosition enu = testEnus[i];

                // ENU -> WGS84 -> ENU 往返误差 < 1 mm
                GeoCoord geo = converter.EnuToWgs84(enu);
                EnuPosition enuBack = converter.Wgs84ToEnu(geo);
                Assert.True(Math.Abs(enuBack.EastM - enu.EastM) < 1e-3);
                Assert.True(Math.Abs(enuBack.NorthM - enu.NorthM) < 1e-3);
                Assert.True(Math.Abs(enuBack.UpM - enu.UpM) < 1e-3);

                // ENU -> Unity (x=East, y=Up+SeaLevelOffset, z=North) -> ENU
                Double3 unityPos = converter.EnuToUnityWorld(enu);
                Assert.Equal(enu.EastM, unityPos.X, 9);
                Assert.Equal(enu.UpM + converter.SeaLevelOffsetM, unityPos.Y, 9);
                Assert.Equal(enu.NorthM, unityPos.Z, 9);

                EnuPosition enuFromUnity = converter.UnityWorldToEnu(unityPos);
                Assert.Equal(enu.EastM, enuFromUnity.EastM, 9);
                Assert.Equal(enu.NorthM, enuFromUnity.NorthM, 9);
                Assert.Equal(enu.UpM, enuFromUnity.UpM, 9);

                // 静态方法与实例方法结果完全一致
                EnuPosition staticEnu = GeoMath.Wgs84ToEnu(geo, origin);
                Assert.Equal(enuBack.EastM, staticEnu.EastM, 9);
                Assert.Equal(enuBack.NorthM, staticEnu.NorthM, 9);
                Assert.Equal(enuBack.UpM, staticEnu.UpM, 9);
            }
        }
    }
}
