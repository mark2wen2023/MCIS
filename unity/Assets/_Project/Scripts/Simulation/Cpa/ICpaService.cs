using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Cpa
{
    /// <summary>
    /// 负责本船与目标船配对的 DCPA/TCPA 预计算、风险分级滞回、任意时刻插值查询与最小距离时刻查询的服务接口（对应 ARCHITECTURE.md 5.3.7 节）。
    /// </summary>
    public interface ICpaService : ITimeDriven, ITimelineMarkerProvider
    {
        /// <summary>当前指定本船标识。</summary>
        string OwnVesselId { get; }

        /// <summary>当前风险分级与滞回阈值配置。</summary>
        RiskThresholds Thresholds { get; }

        /// <summary>false = 使用插值轨迹导数速度（默认平滑），true = 使用原始报告 SOG/COG。</summary>
        bool UseRawSogCog { get; set; }

        /// <summary>设置本船标识。</summary>
        void SetOwnVessel(string vesselId);

        /// <summary>更新风险分级与滞回阈值配置并重新计算缓存序列。</summary>
        void SetThresholds(RiskThresholds thresholds);

        /// <summary>获取指定两船在当前时钟时刻的 CPA 计算结果。</summary>
        CpaResult? GetCurrentPairResult(string ownVesselId, string targetVesselId);

        /// <summary>获取本船与所有目标船在当前时钟时刻的 CPA 结果列表。</summary>
        IReadOnlyList<CpaResult> GetCurrentResultsForOwnVessel();

        /// <summary>获取指定时刻所有活动船舶配对的 CPA 结果列表。</summary>
        IReadOnlyList<CpaResult> GetAllActivePairsAt(SimTime time);

        /// <summary>按固定步长（默认 1.0 秒）全时段正向预计算指定配对的 CPA 序列、滞回风险等级与最小距离极值点。</summary>
        CpaTimeSeries PrecomputeSeries(string ownVesselId, string targetVesselId, double stepSeconds = 1.0);

        /// <summary>查询主配对在指定仿真时间的 CPA 结果（二分/索引查询 + 线性插值）。</summary>
        CpaResult GetAt(SimTime time);

        /// <summary>查询主配对在指定仿真时间（秒）的 CPA 结果（二分/索引查询 + 线性插值）。</summary>
        CpaResult GetAt(double timeSeconds);

        /// <summary>获取主配对在全时段内的最小实际距离样本。</summary>
        CpaResult GetMinDistanceSample();

        /// <summary>获取主配对在全时段内的最小实际距离时刻。</summary>
        SimTime GetMinDistanceTime();
    }
}
