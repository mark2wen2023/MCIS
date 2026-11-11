using System;
using Mcis.Domain.Common;

namespace Mcis.Domain.Geo
{
    /// <summary>
    /// WGS84 大地坐标、ECEF 地心地固坐标、局部切平面 ENU 与 Unity 局部左手系之间的双精度纯数学转换。
    /// 对应 ARCHITECTURE.md 第 4.3 节。不引用 UnityEngine 或 Unity.Mathematics。
    /// </summary>
    public static class GeoMath
    {
        /// <summary>WGS84 椭球长半轴 a（米）。</summary>
        public const double SemiMajorAxisA = 6378137.0;

        /// <summary>WGS84 椭球扁率倒数 1/f。</summary>
        public const double InverseFlattening = 298.257223563;

        /// <summary>WGS84 椭球扁率 f = 1 / 298.257223563。</summary>
        public const double FlatteningF = 1.0 / InverseFlattening;

        /// <summary>WGS84 椭球短半轴 b = a(1 - f)（米）。</summary>
        public const double SemiMinorAxisB = SemiMajorAxisA * (1.0 - FlatteningF);

        /// <summary>第一偏心率平方 e^2 = f(2 - f)。</summary>
        public const double EccentricitySquared = FlatteningF * (2.0 - FlatteningF);

        /// <summary>第二偏心率平方 e'^2 = e^2 / (1 - e^2)。</summary>
        public const double SecondEccentricitySquared = EccentricitySquared / (1.0 - EccentricitySquared);

        /// <summary>角度转弧度系数。</summary>
        public const double DegToRad = Math.PI / 180.0;

        /// <summary>弧度转角度系数。</summary>
        public const double RadToDeg = 180.0 / Math.PI;

        /// <summary>
        /// 将 WGS84 大地坐标（经度、纬度、椭球高）转换为 ECEF 地心地固直角坐标（米）。
        /// </summary>
        public static Double3 Wgs84ToEcef(GeoCoord geo)
        {
            return Wgs84ToEcef(geo.LonDeg, geo.LatDeg, geo.HeightM);
        }

        /// <summary>
        /// 将 WGS84 大地坐标（经度、纬度、椭球高）转换为 ECEF 地心地固直角坐标（米）。
        /// </summary>
        public static Double3 Wgs84ToEcef(double lonDeg, double latDeg, double heightM = 0.0)
        {
            double latRad = latDeg * DegToRad;
            double lonRad = lonDeg * DegToRad;

            double sinLat = Math.Sin(latRad);
            double cosLat = Math.Cos(latRad);
            double sinLon = Math.Sin(lonRad);
            double cosLon = Math.Cos(lonRad);

            double n = SemiMajorAxisA / Math.Sqrt(1.0 - EccentricitySquared * sinLat * sinLat);

            double x = (n + heightM) * cosLat * cosLon;
            double y = (n + heightM) * cosLat * sinLon;
            double z = (n * (1.0 - EccentricitySquared) + heightM) * sinLat;

            return new Double3(x, y, z);
        }

        /// <summary>
        /// 将 ECEF 地心地固直角坐标（米）转换为 WGS84 大地坐标（Bowring 迭代法，双精度亚毫米级）。
        /// </summary>
        public static GeoCoord EcefToWgs84(Double3 ecef)
        {
            return EcefToWgs84(ecef.X, ecef.Y, ecef.Z);
        }

        /// <summary>
        /// 将 ECEF 地心地固直角坐标（米）转换为 WGS84 大地坐标（Bowring 迭代法，双精度亚毫米级）。
        /// </summary>
        public static GeoCoord EcefToWgs84(double x, double y, double z)
        {
            double p = Math.Sqrt(x * x + y * y);
            if (p < 1e-12)
            {
                double poleLatDeg = z >= 0.0 ? 90.0 : -90.0;
                double poleHeightM = Math.Abs(z) - SemiMinorAxisB;
                return new GeoCoord(0.0, poleLatDeg, poleHeightM);
            }

            double lonRad = Math.Atan2(y, x);
            double beta = Math.Atan2(SemiMajorAxisA * z, SemiMinorAxisB * p);
            double latRad = 0.0;

            for (int i = 0; i < 6; i++)
            {
                double sinBeta = Math.Sin(beta);
                double cosBeta = Math.Cos(beta);

                double num = z + SecondEccentricitySquared * SemiMinorAxisB * sinBeta * sinBeta * sinBeta;
                double den = p - EccentricitySquared * SemiMajorAxisA * cosBeta * cosBeta * cosBeta;
                double nextLatRad = Math.Atan2(num, den);

                beta = Math.Atan2((1.0 - FlatteningF) * Math.Sin(nextLatRad), Math.Cos(nextLatRad));
                if (Math.Abs(nextLatRad - latRad) < 1e-15)
                {
                    latRad = nextLatRad;
                    break;
                }
                latRad = nextLatRad;
            }

            double sinLat = Math.Sin(latRad);
            double cosLat = Math.Cos(latRad);
            double n = SemiMajorAxisA / Math.Sqrt(1.0 - EccentricitySquared * sinLat * sinLat);
            double heightM = p * cosLat + (z + EccentricitySquared * n * sinLat) * sinLat - n;

            return new GeoCoord(lonRad * RadToDeg, latRad * RadToDeg, heightM);
        }

        /// <summary>
        /// 将 ECEF 坐标转换为以指定原点为中心的局部切平面 ENU 坐标。
        /// </summary>
        public static EnuPosition EcefToEnu(Double3 ecef, GeoCoord origin)
        {
            Double3 originEcef = Wgs84ToEcef(origin);
            return EcefToEnu(ecef, origin, originEcef);
        }

        /// <summary>
        /// 将 ECEF 坐标转换为以指定原点为中心的局部切平面 ENU 坐标（提供预计算的原点 ECEF）。
        /// </summary>
        public static EnuPosition EcefToEnu(Double3 ecef, GeoCoord origin, Double3 originEcef)
        {
            double latRad = origin.LatDeg * DegToRad;
            double lonRad = origin.LonDeg * DegToRad;
            double sinLat = Math.Sin(latRad);
            double cosLat = Math.Cos(latRad);
            double sinLon = Math.Sin(lonRad);
            double cosLon = Math.Cos(lonRad);

            double dx = ecef.X - originEcef.X;
            double dy = ecef.Y - originEcef.Y;
            double dz = ecef.Z - originEcef.Z;

            double east = -sinLon * dx + cosLon * dy;
            double north = -sinLat * cosLon * dx - sinLat * sinLon * dy + cosLat * dz;
            double up = cosLat * cosLon * dx + cosLat * sinLon * dy + sinLat * dz;

            return new EnuPosition(east, north, up);
        }

        /// <summary>
        /// 将局部切平面 ENU 坐标转换为 ECEF 坐标。
        /// </summary>
        public static Double3 EnuToEcef(EnuPosition enu, GeoCoord origin)
        {
            Double3 originEcef = Wgs84ToEcef(origin);
            return EnuToEcef(enu, origin, originEcef);
        }

        /// <summary>
        /// 将局部切平面 ENU 坐标转换为 ECEF 坐标（提供预计算的原点 ECEF）。
        /// </summary>
        public static Double3 EnuToEcef(EnuPosition enu, GeoCoord origin, Double3 originEcef)
        {
            double latRad = origin.LatDeg * DegToRad;
            double lonRad = origin.LonDeg * DegToRad;
            double sinLat = Math.Sin(latRad);
            double cosLat = Math.Cos(latRad);
            double sinLon = Math.Sin(lonRad);
            double cosLon = Math.Cos(lonRad);

            double e = enu.EastM;
            double n = enu.NorthM;
            double u = enu.UpM;

            double dx = -sinLon * e - sinLat * cosLon * n + cosLat * cosLon * u;
            double dy = cosLon * e - sinLat * sinLon * n + cosLat * sinLon * u;
            double dz = cosLat * n + sinLat * u;

            return new Double3(originEcef.X + dx, originEcef.Y + dy, originEcef.Z + dz);
        }

        /// <summary>
        /// 直接将 WGS84 大地坐标转换为给定原点下的 ENU 坐标。
        /// </summary>
        public static EnuPosition Wgs84ToEnu(GeoCoord geo, GeoCoord origin)
        {
            return EcefToEnu(Wgs84ToEcef(geo), origin);
        }

        /// <summary>
        /// 直接将给定原点下的 ENU 坐标转换为 WGS84 大地坐标。
        /// </summary>
        public static GeoCoord EnuToWgs84(EnuPosition enu, GeoCoord origin)
        {
            return EcefToWgs84(EnuToEcef(enu, origin));
        }

        /// <summary>
        /// 将 ENU 坐标映射至 Unity 左手系世界坐标（x=East, y=Up+seaLevelOffsetM, z=North）。
        /// </summary>
        public static Double3 EnuToUnity(EnuPosition enu, double seaLevelOffsetM = 0.0)
        {
            return new Double3(enu.EastM, enu.UpM + seaLevelOffsetM, enu.NorthM);
        }

        /// <summary>
        /// 将 Unity 左手系世界坐标（x=East, y=Up+seaLevelOffsetM, z=North）还原为 ENU 坐标。
        /// </summary>
        public static EnuPosition UnityToEnu(Double3 unityPos, double seaLevelOffsetM = 0.0)
        {
            return new EnuPosition(unityPos.X, unityPos.Z, unityPos.Y - seaLevelOffsetM);
        }
    }
}
