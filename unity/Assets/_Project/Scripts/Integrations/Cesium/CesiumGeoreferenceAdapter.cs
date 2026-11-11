#if UNITY_5_3_OR_NEWER
using System;
using UnityEngine;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;

#if MCIS_CESIUM
using CesiumForUnity;
using Unity.Mathematics;
#endif

namespace Mcis.Integrations.Cesium
{
    /// <summary>
    /// Cesium for Unity 地理参考适配器（实现 <see cref="IGeoConverter"/>）。
    /// 封装 CesiumGeoreference 原点管理与高精度大地坐标/ECEF/Unity 场景坐标转换。
    /// 当未安装 com.cesium.unity 包或未挂载 CesiumGeoreference 时，自动回退到
    /// 纯 C# 的 <see cref="LocalEnuGeoConverter"/>，确保工程随时可独立编译与运行。
    /// </summary>
    [AddComponentMenu("MCIS/Integrations/Cesium/Cesium Georeference Adapter")]
    public sealed class CesiumGeoreferenceAdapter : MonoBehaviour, IGeoConverter
    {
#if MCIS_CESIUM
        [Tooltip("场景中的 CesiumGeoreference 组件（为空时尝试自动检索）")]
        [SerializeField] private CesiumGeoreference _georeference;
#endif

        [Tooltip("平均海面相对于 WGS84 椭球面的高程偏移（米）")]
        [SerializeField] private double _seaLevelOffsetM = 0.0;

        private readonly LocalEnuGeoConverter _fallback = new LocalEnuGeoConverter();

        /// <inheritdoc />
        public GeoCoord Origin
        {
            get
            {
                SyncOriginFromGeoreference();
                return _fallback.Origin;
            }
        }

        /// <inheritdoc />
        public Double3 OriginEcef
        {
            get
            {
                SyncOriginFromGeoreference();
                return _fallback.OriginEcef;
            }
        }

        /// <inheritdoc />
        public double SeaLevelOffsetM
        {
            get { return _seaLevelOffsetM; }
        }

        private void Awake()
        {
#if MCIS_CESIUM
            if (_georeference == null)
            {
                _georeference = UnityEngine.Object.FindFirstObjectByType<CesiumGeoreference>();
            }
#endif
            SyncOriginFromGeoreference();
        }

        /// <inheritdoc />
        public void SetOrigin(GeoCoord origin, double seaLevelOffsetM = 0.0)
        {
            _seaLevelOffsetM = seaLevelOffsetM;
            _fallback.SetOrigin(origin, seaLevelOffsetM);

#if MCIS_CESIUM
            if (_georeference != null)
            {
                _georeference.latitude = origin.LatDeg;
                _georeference.longitude = origin.LonDeg;
                _georeference.height = origin.AltitudeM;
            }
#endif
        }

        /// <inheritdoc />
        public Double3 Wgs84ToEcef(GeoCoord geo)
        {
            return _fallback.Wgs84ToEcef(geo);
        }

        /// <inheritdoc />
        public GeoCoord EcefToWgs84(Double3 ecef)
        {
            return _fallback.EcefToWgs84(ecef);
        }

        /// <inheritdoc />
        public EnuPosition EcefToEnu(Double3 ecef)
        {
            SyncOriginFromGeoreference();
            return _fallback.EcefToEnu(ecef);
        }

        /// <inheritdoc />
        public Double3 EnuToEcef(EnuPosition enu)
        {
            SyncOriginFromGeoreference();
            return _fallback.EnuToEcef(enu);
        }

        /// <inheritdoc />
        public EnuPosition Wgs84ToEnu(GeoCoord geo)
        {
            SyncOriginFromGeoreference();
            return _fallback.Wgs84ToEnu(geo);
        }

        /// <inheritdoc />
        public GeoCoord EnuToWgs84(EnuPosition enu)
        {
            SyncOriginFromGeoreference();
            return _fallback.EnuToWgs84(enu);
        }

        /// <inheritdoc />
        public Double3 EnuToUnityWorld(EnuPosition enu)
        {
            SyncOriginFromGeoreference();

#if MCIS_CESIUM
            if (_georeference != null)
            {
                Double3 ecef = _fallback.EnuToEcef(enu);
                double3 cesiumEcef = new double3(ecef.X, ecef.Y, ecef.Z);
                double3 unity = _georeference.TransformEarthCenteredEarthFixedPositionToUnityPosition(cesiumEcef);
                return new Double3(unity.x, unity.y + _seaLevelOffsetM, unity.z);
            }
#endif
            return _fallback.EnuToUnityWorld(enu);
        }

        /// <inheritdoc />
        public EnuPosition UnityWorldToEnu(Double3 unityPos)
        {
            SyncOriginFromGeoreference();

#if MCIS_CESIUM
            if (_georeference != null)
            {
                double3 cesiumUnity = new double3(unityPos.X, unityPos.Y - _seaLevelOffsetM, unityPos.Z);
                double3 ecef = _georeference.TransformUnityPositionToEarthCenteredEarthFixed(cesiumUnity);
                Double3 ecefD = new Double3(ecef.x, ecef.y, ecef.z);
                return _fallback.EcefToEnu(ecefD);
            }
#endif
            return _fallback.UnityWorldToEnu(unityPos);
        }

        private void SyncOriginFromGeoreference()
        {
#if MCIS_CESIUM
            if (_georeference != null)
            {
                double lat = _georeference.latitude;
                double lon = _georeference.longitude;
                double h = _georeference.height;
                GeoCoord current = _fallback.Origin;
                if (Math.Abs(lat - current.LatDeg) > 1e-7 ||
                    Math.Abs(lon - current.LonDeg) > 1e-7 ||
                    Math.Abs(h - current.AltitudeM) > 1e-3)
                {
                    _fallback.SetOrigin(new GeoCoord(lat, lon, h), _seaLevelOffsetM);
                }
            }
#endif
        }
    }
}
#endif
