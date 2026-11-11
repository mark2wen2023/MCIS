#if UNITY_5_3_OR_NEWER
// ---------------------------------------------------------------------------
// NWH Dynamic Water Physics 2 / 水面系统适配器。
// 本文件依赖 UnityEngine 与 DWP2 API，在本开发盒子上【未编译验证】。
// 未安装 DWP2 时请不要把本文件纳入编译（或保留 MCIS_DWP2 宏关闭）。
// ---------------------------------------------------------------------------
using Mcis.Domain.Models;
using Mcis.Simulation.Environment;
using UnityEngine;

namespace Mcis.Integrations.Dwp2
{
    /// <summary>将浪高、周期、浪向、潮流映射到 DWP2 / 水面渲染（示意实现，未编译验证）。</summary>
    public sealed class Dwp2WaterBackend : MonoBehaviour, IWaterBackend
    {
        [SerializeField] private bool _logMapping = true;

        public void ApplyWater(EnvironmentState state, double seaLevelOffsetM, bool immediate)
        {
#if MCIS_DWP2
            // 示意映射（ARCHITECTURE 4.7）：
            // WaveSignificantHeightM / WavePeakPeriodSec / WaveFromDirDeg → 水面波谱
            // CurrentSpeedKn / CurrentToDirDeg → DWP2 Flow 区域速度矢量
            // TideHeightM + seaLevelOffsetM → 水面基准高程
#else
            if (_logMapping)
            {
                Debug.Log(string.Format(
                    "Dwp2WaterBackend (未连接 DWP2)：Hs={0:F2}m Tp={1:F1}s current={2:F1}kn seaLevel={3:F2} immediate={4}",
                    state.WaveSignificantHeightM, state.WavePeakPeriodSec, state.CurrentSpeedKn, seaLevelOffsetM, immediate));
            }
#endif
        }

        public float SampleWaterHeightAt(double worldX, double worldY, double worldZ)
        {
#if MCIS_DWP2
            // 通过 WaterDataProvider 采样世界坐标处水面高度
            return (float)worldY;
#else
            return (float)worldY;
#endif
        }
    }
}
#endif
