using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Cpa
{
    /// <summary>
    /// CPA 全时段预计算、正向滞回状态机与任意时刻插值查询服务（对应 ARCHITECTURE.md 4.6 与 5.3.7 节）。
    /// 纯 C# 实现，不依赖 UnityEngine。
    /// </summary>
    public sealed partial class CpaService : ICpaService
    {
        private sealed class VesselEntry
        {
            public string VesselId { get; }
            public SimTime StartTime { get; }
            public SimTime EndTime { get; }
            public Func<double, VesselMotionState> StateSampler { get; }
            public IShipTrack Track { get; }

            public VesselEntry(
                string vesselId,
                SimTime startTime,
                SimTime endTime,
                Func<double, VesselMotionState> stateSampler,
                IShipTrack track = null)
            {
                VesselId = vesselId;
                StartTime = startTime;
                EndTime = endTime;
                StateSampler = stateSampler;
                Track = track;
            }
        }

        private readonly Dictionary<string, VesselEntry> _vessels =
            new Dictionary<string, VesselEntry>(StringComparer.Ordinal);
        private readonly List<string> _vesselOrder = new List<string>();
        private readonly Dictionary<CpaPairKey, CpaTimeSeries> _seriesCache =
            new Dictionary<CpaPairKey, CpaTimeSeries>();
        private readonly List<TimelineMarker> _markers = new List<TimelineMarker>();

        private string _ownVesselId;
        private string _primaryTargetVesselId;
        private RiskThresholds _thresholds = RiskThresholds.Default;
        private double _defaultStepSeconds = 1.0;
        private SimTime _currentTime = SimTime.Zero;
        private bool _useRawSogCog;

        /// <inheritdoc />
        public int ExecutionPriority
        {
            get { return 30; }
        }

        /// <inheritdoc />
        public string OwnVesselId
        {
            get { return _ownVesselId; }
        }

        /// <summary>主目标船标识（双船模式下自动记录第二艘船）。</summary>
        public string PrimaryTargetVesselId
        {
            get { return _primaryTargetVesselId; }
        }

        /// <inheritdoc />
        public RiskThresholds Thresholds
        {
            get { return _thresholds; }
        }

        /// <inheritdoc />
        public bool UseRawSogCog
        {
            get { return _useRawSogCog; }
            set
            {
                if (_useRawSogCog != value)
                {
                    _useRawSogCog = value;
                    RebuildAllCachedSeries();
                }
            }
        }

        /// <summary>主配对预计算时间序列。</summary>
        public CpaTimeSeries PrimarySeries
        {
            get
            {
                if (string.IsNullOrEmpty(_ownVesselId) || string.IsNullOrEmpty(_primaryTargetVesselId))
                {
                    return null;
                }
                return GetOrBuildSeries(_ownVesselId, _primaryTargetVesselId, _defaultStepSeconds);
            }
        }

        /// <inheritdoc />
        public event Action MarkersChanged;

        /// <summary>构造空的 CPA 服务实例。</summary>
        public CpaService(RiskThresholds? thresholds = null, double defaultStepSeconds = 1.0)
        {
            _thresholds = thresholds ?? RiskThresholds.Default;
            _defaultStepSeconds = defaultStepSeconds > 0.0 ? defaultStepSeconds : 1.0;
        }

        /// <summary>
        /// 使用两船运动状态采样委托构造并立即按固定步长正向预计算全时段 CPA 序列。
        /// </summary>
        public CpaService(
            Func<double, VesselMotionState> ownSampler,
            Func<double, VesselMotionState> targetSampler,
            double startTimeSeconds,
            double endTimeSeconds,
            double stepSeconds = 1.0,
            RiskThresholds? thresholds = null,
            string ownVesselId = "Own",
            string targetVesselId = "Target")
            : this(thresholds, stepSeconds)
        {
            if (ownSampler == null) throw new ArgumentNullException(nameof(ownSampler));
            if (targetSampler == null) throw new ArgumentNullException(nameof(targetSampler));

            ConfigurePair(
                ownSampler, targetSampler,
                startTimeSeconds, endTimeSeconds,
                stepSeconds, ownVesselId, targetVesselId);
        }

        /// <summary>
        /// 使用两船 TrackSample 采样委托构造并预计算 CPA 序列。
        /// </summary>
        public CpaService(
            Func<double, TrackSample> ownSampleFunc,
            Func<double, TrackSample> targetSampleFunc,
            double startTimeSeconds,
            double endTimeSeconds,
            double stepSeconds = 1.0,
            RiskThresholds? thresholds = null,
            string ownVesselId = "Own",
            string targetVesselId = "Target")
            : this(
                t => VesselMotionState.FromTrackSample(ownSampleFunc(t), false),
                t => VesselMotionState.FromTrackSample(targetSampleFunc(t), false),
                startTimeSeconds, endTimeSeconds, stepSeconds, thresholds, ownVesselId, targetVesselId)
        {
        }

        /// <summary>
        /// 使用两条 IShipTrack 航迹构造并预计算 CPA 序列。
        /// </summary>
        public CpaService(
            IShipTrack ownTrack,
            IShipTrack targetTrack,
            double stepSeconds = 1.0,
            RiskThresholds? thresholds = null)
            : this(thresholds, stepSeconds)
        {
            if (ownTrack == null) throw new ArgumentNullException(nameof(ownTrack));
            if (targetTrack == null) throw new ArgumentNullException(nameof(targetTrack));

            RegisterTrack(ownTrack);
            RegisterTrack(targetTrack);
            _ownVesselId = ownTrack.VesselId;
            _primaryTargetVesselId = targetTrack.VesselId;
            PrecomputeSeries(_ownVesselId, _primaryTargetVesselId, _defaultStepSeconds);
        }

        /// <summary>
        /// 通过 ITrackInterpolator 构建两条航迹并预计算 CPA 序列的适配重载。
        /// </summary>
        public static CpaService CreateFromInterpolator(
            ITrackInterpolator interpolator,
            string ownVesselId,
            IReadOnlyList<TrackSample> ownWaypoints,
            string targetVesselId,
            IReadOnlyList<TrackSample> targetWaypoints,
            InterpolationMode mode = InterpolationMode.CubicHermite,
            double stepSeconds = 1.0,
            RiskThresholds? thresholds = null)
        {
            if (interpolator == null) throw new ArgumentNullException(nameof(interpolator));
            IShipTrack ownTrack = interpolator.BuildFromDrawnWaypoints(ownVesselId, ownWaypoints, mode);
            IShipTrack targetTrack = interpolator.BuildFromDrawnWaypoints(targetVesselId, targetWaypoints, mode);
            return new CpaService(ownTrack, targetTrack, stepSeconds, thresholds);
        }

        /// <summary>
        /// 通过 ITrackInterpolator 从原始 AIS 记录构建两条航迹并预计算 CPA 序列的适配重载。
        /// </summary>
        public static CpaService CreateFromInterpolator(
            ITrackInterpolator interpolator,
            string ownVesselId,
            IReadOnlyList<AisDecodedRecord> ownAisRecords,
            AntennaOffset ownAntenna,
            string targetVesselId,
            IReadOnlyList<AisDecodedRecord> targetAisRecords,
            AntennaOffset targetAntenna,
            DateTimeOffset caseEpochUtc,
            IGeoConverter geoConverter,
            TrackCleaningConfig cleaningConfig = null,
            double stepSeconds = 1.0,
            RiskThresholds? thresholds = null)
        {
            if (interpolator == null) throw new ArgumentNullException(nameof(interpolator));
            TrackCleaningConfig cfg = cleaningConfig ?? TrackCleaningConfig.CreateDefault();
            IShipTrack ownTrack = interpolator.BuildFromAisRecords(
                ownVesselId, ownAisRecords, ownAntenna, caseEpochUtc, geoConverter, cfg);
            IShipTrack targetTrack = interpolator.BuildFromAisRecords(
                targetVesselId, targetAisRecords, targetAntenna, caseEpochUtc, geoConverter, cfg);
            return new CpaService(ownTrack, targetTrack, stepSeconds, thresholds);
        }
    }
}
