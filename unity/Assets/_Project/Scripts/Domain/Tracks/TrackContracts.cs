using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 航迹异常点清洗、缺口检测与插值配置参数（对应 ARCHITECTURE.md 5.3.3 节）。
    /// </summary>
    public sealed class TrackCleaningConfig
    {
        /// <summary>最大合理航速门限（节，货船默认 30 kn，高速船 50 kn）。</summary>
        public float MaxSpeedKn { get; }

        /// <summary>相邻点隐含航速相对报告 SOG 的跳点倍率（默认 1.5）。</summary>
        public float SpeedGateMultiplier { get; }

        /// <summary>双向航位推算残差门限（米，默认 50 m）。</summary>
        public float DrResidualThresholdM { get; }

        /// <summary>Hampel 滑动窗口大小（默认 7）。</summary>
        public int HampelWindowSize { get; }

        /// <summary>Hampel 离群判定标准差倍数（默认 3.0）。</summary>
        public float HampelSigmaMultiplier { get; }

        /// <summary>在航状态下的时间缺口阈值（秒，默认 60 s）。</summary>
        public double MovingGapThresholdSec { get; }

        /// <summary>锚泊/系泊状态下的时间缺口阈值（秒，默认 360 s）。</summary>
        public double AnchoredGapThresholdSec { get; }

        /// <summary>插值算法模式。</summary>
        public InterpolationMode InterpolationMode { get; }

        /// <summary>时间缺口处理策略。</summary>
        public GapPolicy GapPolicy { get; }

        /// <summary>是否根据船首向应用 AIS 天线位置偏移修正。</summary>
        public bool ApplyAntennaOffset { get; }

        /// <summary>相邻有效点报告 SOG 突变阈值（节，默认 12.0 kn）。</summary>
        public float MaxSpeedJumpKn { get; }

        /// <summary>报告 SOG 最大允许加速度（节/秒，默认 2.5 kn/s）。</summary>
        public float MaxAccelerationKnPerSec { get; }

        /// <summary>相邻有效点航向突变阈值（度，默认 120.0°）。</summary>
        public float MaxCourseJumpDeg { get; }

        /// <summary>最大允许转向角速度（度/秒，默认 8.0°/s）。</summary>
        public float MaxTurnRateDegPerSec { get; }

        /// <summary>执行航向突变检查的最低航速阈值（节，默认 2.0 kn）。</summary>
        public float MinSpeedForCourseCheckKn { get; }

        /// <summary>重复时间戳判定容差（秒，默认 0.001 s）。</summary>
        public double DuplicateTimeToleranceSec { get; }

        /// <summary>构造航迹清洗与插值配置。</summary>
        public TrackCleaningConfig(
            float maxSpeedKn = 30.0f,
            float speedGateMultiplier = 1.5f,
            float drResidualThresholdM = 50.0f,
            int hampelWindowSize = 7,
            float hampelSigmaMultiplier = 3.0f,
            double movingGapThresholdSec = 60.0,
            double anchoredGapThresholdSec = 360.0,
            InterpolationMode interpolationMode = InterpolationMode.CubicHermite,
            GapPolicy gapPolicy = GapPolicy.ConnectDashed,
            bool applyAntennaOffset = true,
            float maxSpeedJumpKn = 12.0f,
            float maxAccelerationKnPerSec = 2.5f,
            float maxCourseJumpDeg = 120.0f,
            float maxTurnRateDegPerSec = 8.0f,
            float minSpeedForCourseCheckKn = 2.0f,
            double duplicateTimeToleranceSec = 1e-3)
        {
            MaxSpeedKn = maxSpeedKn > 0f ? maxSpeedKn : 30.0f;
            SpeedGateMultiplier = speedGateMultiplier > 0f ? speedGateMultiplier : 1.5f;
            DrResidualThresholdM = drResidualThresholdM > 0f ? drResidualThresholdM : 50.0f;
            HampelWindowSize = hampelWindowSize >= 3 ? hampelWindowSize : 7;
            HampelSigmaMultiplier = hampelSigmaMultiplier > 0f ? hampelSigmaMultiplier : 3.0f;
            MovingGapThresholdSec = movingGapThresholdSec > 0.0 ? movingGapThresholdSec : 60.0;
            AnchoredGapThresholdSec = anchoredGapThresholdSec > 0.0 ? anchoredGapThresholdSec : 360.0;
            InterpolationMode = interpolationMode;
            GapPolicy = gapPolicy;
            ApplyAntennaOffset = applyAntennaOffset;
            MaxSpeedJumpKn = maxSpeedJumpKn > 0f ? maxSpeedJumpKn : 12.0f;
            MaxAccelerationKnPerSec = maxAccelerationKnPerSec > 0f ? maxAccelerationKnPerSec : 2.5f;
            MaxCourseJumpDeg = maxCourseJumpDeg > 0f ? maxCourseJumpDeg : 120.0f;
            MaxTurnRateDegPerSec = maxTurnRateDegPerSec > 0f ? maxTurnRateDegPerSec : 8.0f;
            MinSpeedForCourseCheckKn = minSpeedForCourseCheckKn >= 0f ? minSpeedForCourseCheckKn : 2.0f;
            DuplicateTimeToleranceSec = duplicateTimeToleranceSec >= 0.0 ? duplicateTimeToleranceSec : 1e-3;
        }

        /// <summary>创建标准默认清洗配置。</summary>
        public static TrackCleaningConfig CreateDefault()
        {
            return new TrackCleaningConfig();
        }
    }

    /// <summary>
    /// 可连续按时间求值的单船航迹接口（对应 ARCHITECTURE.md 5.3.3 节）。
    /// </summary>
    public interface IShipTrack
    {
        /// <summary>船舶唯一标识。</summary>
        string VesselId { get; }

        /// <summary>航迹起始仿真时间。</summary>
        SimTime StartTime { get; }

        /// <summary>航迹结束仿真时间。</summary>
        SimTime EndTime { get; }

        /// <summary>清洗后保留的离散样本点列表（按时间升序）。</summary>
        IReadOnlyList<TrackSample> CleanedSamples { get; }

        /// <summary>被异常检测剔除的样本记录列表。</summary>
        IReadOnlyList<RejectedSample> RejectedSamples { get; }

        /// <summary>检测到的时间缺口列表。</summary>
        IReadOnlyList<TimeGapSpan> TimeGaps { get; }

        /// <summary>在指定仿真时间对航迹进行插值采样。</summary>
        TrackSample SampleAt(SimTime time);

        /// <summary>尝试在指定时间采样；若超出时间范围拒绝外推或处于 HideVessel 缺口内则返回 false。</summary>
        bool TrySampleAt(SimTime time, out TrackSample sample);

        /// <summary>判断指定仿真时间是否落在某个时间缺口内。</summary>
        bool IsInTimeGap(SimTime time, out TimeGapSpan gap);
    }

    /// <summary>
    /// 负责将原始 AIS 记录或手绘关键点清洗、构建为可连续求值航迹的服务接口（对应 ARCHITECTURE.md 5.3.3 节）。
    /// </summary>
    public interface ITrackInterpolator
    {
        /// <summary>从原始 AIS 解码记录清洗并构建船舶航迹。</summary>
        IShipTrack BuildFromAisRecords(
            string vesselId,
            IReadOnlyList<AisDecodedRecord> rawRecords,
            AntennaOffset antennaOffset,
            DateTimeOffset caseEpochUtc,
            IGeoConverter geoConverter,
            TrackCleaningConfig config,
            ISet<int> manuallyRestoredLineNumbers = null);

        /// <summary>从手绘或离散关键点构建船舶航迹。</summary>
        IShipTrack BuildFromDrawnWaypoints(
            string vesselId,
            IReadOnlyList<TrackSample> manualWaypoints,
            InterpolationMode mode);
    }
}
