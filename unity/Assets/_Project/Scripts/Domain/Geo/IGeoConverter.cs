using System;
using Mcis.Domain.Common;

namespace Mcis.Domain.Geo
{
    /// <summary>
    /// 双精度大地坐标与局部切平面转换接口，作为领域层与 CesiumGeoreference 的桥梁。
    /// 对应 ARCHITECTURE.md 第 5.3.4 节。
    /// 说明：为保持 Mcis.Domain 纯 C#（noEngineReferences，兼容 dotnet 测试），
    /// 接口中的三维向量统一使用领域层纯 C# 结构 Double3 替代 Unity.Mathematics.double3/float3；
    /// 与 UnityEngine.Vector3 及 CesiumGeoreference 组件的桥接由 Simulation/Adapter 层负责。
    /// </summary>
    public interface IGeoConverter
    {
        /// <summary>当前局部切平面 ENU 原点的大地坐标。</summary>
        GeoCoord Origin { get; }

        /// <summary>当前 ENU 原点对应的 ECEF 坐标（米）。</summary>
        Double3 OriginEcef { get; }

        /// <summary>平均海面相对于 WGS84 椭球面的高程修正（米）。</summary>
        double SeaLevelOffsetM { get; }

        /// <summary>设置局部切平面原点与海面高程修正。</summary>
        void SetOrigin(GeoCoord origin, double seaLevelOffsetM = 0.0);

        /// <summary>WGS84 大地坐标转 ECEF 地心地固坐标。</summary>
        Double3 Wgs84ToEcef(GeoCoord geo);

        /// <summary>ECEF 地心地固坐标转 WGS84 大地坐标。</summary>
        GeoCoord EcefToWgs84(Double3 ecef);

        /// <summary>ECEF 坐标转当前原点下的局部 ENU 坐标。</summary>
        EnuPosition EcefToEnu(Double3 ecef);

        /// <summary>当前原点下的局部 ENU 坐标转 ECEF 坐标。</summary>
        Double3 EnuToEcef(EnuPosition enu);

        /// <summary>WGS84 大地坐标直接转当前原点下的局部 ENU 坐标。</summary>
        EnuPosition Wgs84ToEnu(GeoCoord geo);

        /// <summary>当前原点下的局部 ENU 坐标直接转 WGS84 大地坐标。</summary>
        GeoCoord EnuToWgs84(EnuPosition enu);

        /// <summary>ENU (东e, 北n, 天u) 映射至 Unity 世界坐标 (x=e, y=u+SeaLevelOffsetM, z=n)。</summary>
        Double3 EnuToUnityWorld(EnuPosition enu);

        /// <summary>Unity 世界坐标 (x=e, y=u+SeaLevelOffsetM, z=n) 还原为局部 ENU 坐标。</summary>
        EnuPosition UnityWorldToEnu(Double3 unityPos);
    }

    /// <summary>
    /// 基于 GeoMath 的纯 C# 局部切平面坐标转换器实现。
    /// 缓存原点 ECEF 与旋转矩阵三角函数分量，支持高频航迹点批量转换。
    /// </summary>
    public sealed class LocalEnuGeoConverter : IGeoConverter
    {
        private GeoCoord _origin;
        private Double3 _originEcef;
        private double _seaLevelOffsetM;
        private double _sinLat;
        private double _cosLat;
        private double _sinLon;
        private double _cosLon;

        /// <inheritdoc />
        public GeoCoord Origin
        {
            get { return _origin; }
        }

        /// <inheritdoc />
        public Double3 OriginEcef
        {
            get { return _originEcef; }
        }

        /// <inheritdoc />
        public double SeaLevelOffsetM
        {
            get { return _seaLevelOffsetM; }
        }

        /// <summary>
        /// 使用默认原点 (0°, 0°, 0m) 构造坐标转换器。
        /// </summary>
        public LocalEnuGeoConverter()
        {
            SetOrigin(new GeoCoord(0.0, 0.0, 0.0), 0.0);
        }

        /// <summary>
        /// 使用指定原点与海面高程偏移构造坐标转换器。
        /// </summary>
        public LocalEnuGeoConverter(GeoCoord origin, double seaLevelOffsetM = 0.0)
        {
            SetOrigin(origin, seaLevelOffsetM);
        }

        /// <inheritdoc />
        public void SetOrigin(GeoCoord origin, double seaLevelOffsetM = 0.0)
        {
            _origin = origin;
            _seaLevelOffsetM = seaLevelOffsetM;
            _originEcef = GeoMath.Wgs84ToEcef(origin);

            double latRad = origin.LatDeg * GeoMath.DegToRad;
            double lonRad = origin.LonDeg * GeoMath.DegToRad;
            _sinLat = Math.Sin(latRad);
            _cosLat = Math.Cos(latRad);
            _sinLon = Math.Sin(lonRad);
            _cosLon = Math.Cos(lonRad);
        }

        /// <inheritdoc />
        public Double3 Wgs84ToEcef(GeoCoord geo)
        {
            return GeoMath.Wgs84ToEcef(geo);
        }

        /// <inheritdoc />
        public GeoCoord EcefToWgs84(Double3 ecef)
        {
            return GeoMath.EcefToWgs84(ecef);
        }

        /// <inheritdoc />
        public EnuPosition EcefToEnu(Double3 ecef)
        {
            double dx = ecef.X - _originEcef.X;
            double dy = ecef.Y - _originEcef.Y;
            double dz = ecef.Z - _originEcef.Z;

            double east = -_sinLon * dx + _cosLon * dy;
            double north = -_sinLat * _cosLon * dx - _sinLat * _sinLon * dy + _cosLat * dz;
            double up = _cosLat * _cosLon * dx + _cosLat * _sinLon * dy + _sinLat * dz;

            return new EnuPosition(east, north, up);
        }

        /// <inheritdoc />
        public Double3 EnuToEcef(EnuPosition enu)
        {
            double e = enu.EastM;
            double n = enu.NorthM;
            double u = enu.UpM;

            double dx = -_sinLon * e - _sinLat * _cosLon * n + _cosLat * _cosLon * u;
            double dy = _cosLon * e - _sinLat * _sinLon * n + _cosLat * _sinLon * u;
            double dz = _cosLat * n + _sinLat * u;

            return new Double3(_originEcef.X + dx, _originEcef.Y + dy, _originEcef.Z + dz);
        }

        /// <inheritdoc />
        public EnuPosition Wgs84ToEnu(GeoCoord geo)
        {
            return EcefToEnu(GeoMath.Wgs84ToEcef(geo));
        }

        /// <inheritdoc />
        public GeoCoord EnuToWgs84(EnuPosition enu)
        {
            return GeoMath.EcefToWgs84(EnuToEcef(enu));
        }

        /// <inheritdoc />
        public Double3 EnuToUnityWorld(EnuPosition enu)
        {
            return GeoMath.EnuToUnity(enu, _seaLevelOffsetM);
        }

        /// <inheritdoc />
        public EnuPosition UnityWorldToEnu(Double3 unityPos)
        {
            return GeoMath.UnityToEnu(unityPos, _seaLevelOffsetM);
        }
    }
}
