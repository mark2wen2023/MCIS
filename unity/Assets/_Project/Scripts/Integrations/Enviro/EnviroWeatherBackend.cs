#if UNITY_5_3_OR_NEWER
// ---------------------------------------------------------------------------
// Enviro 3 天气适配器。本文件依赖 UnityEngine 与 Enviro 3 API，
// 在本开发盒子上【未编译验证】。请在已安装 Enviro 3 的 Unity 6.0 工程中联调。
// 未安装 Enviro 3 时，请不要把本文件纳入编译（或保留 MCIS_ENVIRO 宏关闭）。
// ---------------------------------------------------------------------------
using System;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Simulation.Environment;
using UnityEngine;

namespace Mcis.Integrations.Enviro
{
    /// <summary>将 EnvironmentState 映射到 Enviro 3（示意实现，未编译验证）。</summary>
    public sealed class EnviroWeatherBackend : MonoBehaviour, IWeatherBackend
    {
        [SerializeField] private bool _logMapping = true;

        public void ApplyWeather(EnvironmentState state, GeoCoord referenceGeo, DateTimeOffset currentUtc, bool immediate)
        {
#if MCIS_ENVIRO
            // 示意映射（ARCHITECTURE 4.7）：
            // VisibilityNm → Enviro fog / visibility
            // WindSpeedMps / WindFromDirDeg → Enviro wind
            // CloudCoverNormalized / RainIntensityMmPerHr / WeatherPresetId → Enviro weather type
            // currentUtc + referenceGeo → Enviro time / location
            // immediate = true 时跳过平滑渐变
#else
            if (_logMapping)
            {
                Debug.Log(string.Format(
                    "EnviroWeatherBackend (未连接 Enviro 3)：t={0:F1}s vis={1:F2}nm wind={2:F1}m/s from {3:F0}° rain={4:F1} immediate={5}",
                    state.Time.Seconds, state.VisibilityNm, state.WindSpeedMps, state.WindFromDirDeg,
                    state.RainIntensityMmPerHr, immediate));
            }
#endif
        }

        public void SetClearVisibilityOverride(bool clearOverride)
        {
#if MCIS_ENVIRO
            // 证据清晰模式：关闭雨雾遮挡
#else
            if (_logMapping)
            {
                Debug.Log("EnviroWeatherBackend 证据清晰模式 = " + clearOverride);
            }
#endif
        }
    }
}
#endif
