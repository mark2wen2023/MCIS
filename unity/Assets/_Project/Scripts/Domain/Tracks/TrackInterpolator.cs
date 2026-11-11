using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 航迹构建与插值器服务实现（对应 ARCHITECTURE.md 4.2.5 与 5.3.3 节）。
    /// 支持从原始 AIS 报文序列或手绘关键点构建支持三次 Hermite、Catmull-Rom、线性插值及缺口检测的 IShipTrack。
    /// </summary>
    public sealed class TrackInterpolator : ITrackInterpolator
    {
        /// <inheritdoc />
        public IShipTrack BuildFromAisRecords(
            string vesselId,
            IReadOnlyList<AisDecodedRecord> rawRecords,
            AntennaOffset antennaOffset,
            DateTimeOffset caseEpochUtc,
            IGeoConverter geoConverter,
            TrackCleaningConfig config,
            ISet<int> manuallyRestoredLineNumbers = null)
        {
            TrackCleaningConfig cfg = config ?? TrackCleaningConfig.CreateDefault();
            TrackCleaningReport report = TrackCleaner.CleanAisRecords(
                vesselId,
                rawRecords,
                antennaOffset,
                caseEpochUtc,
                geoConverter,
                cfg,
                manuallyRestoredLineNumbers);

            return new ShipTrack(
                vesselId,
                report.CleanedSamples,
                report.RejectedSamples,
                report.TimeGaps,
                cfg.InterpolationMode,
                cfg.GapPolicy,
                geoConverter);
        }

        /// <inheritdoc />
        public IShipTrack BuildFromDrawnWaypoints(
            string vesselId,
            IReadOnlyList<TrackSample> manualWaypoints,
            InterpolationMode mode)
        {
            return BuildFromDrawnWaypoints(
                vesselId,
                manualWaypoints,
                mode,
                60.0,
                GapPolicy.ConnectDashed,
                null);
        }

        /// <summary>
        /// 从手绘或离散样本关键点构建航迹（可指定缺口阈值、缺口策略与坐标转换器）。
        /// </summary>
        public IShipTrack BuildFromDrawnWaypoints(
            string vesselId,
            IReadOnlyList<TrackSample> manualWaypoints,
            InterpolationMode mode,
            double gapThresholdSec,
            GapPolicy gapPolicy = GapPolicy.ConnectDashed,
            IGeoConverter geoConverter = null)
        {
            if (manualWaypoints == null || manualWaypoints.Count == 0)
            {
                return new ShipTrack(
                    vesselId,
                    Array.Empty<TrackSample>(),
                    Array.Empty<RejectedSample>(),
                    Array.Empty<TimeGapSpan>(),
                    mode,
                    gapPolicy,
                    geoConverter);
            }

            IGeoConverter converter = geoConverter;
            ShipTrack tempNormalized = new ShipTrack(
                vesselId,
                manualWaypoints,
                Array.Empty<RejectedSample>(),
                Array.Empty<TimeGapSpan>(),
                mode,
                gapPolicy,
                converter);

            IReadOnlyList<TimeGapSpan> gaps = TrackCleaner.DetectTimeGaps(
                tempNormalized.CleanedSamples,
                gapThresholdSec > 0.0 ? gapThresholdSec : 60.0,
                Math.Max(360.0, gapThresholdSec));

            return new ShipTrack(
                vesselId,
                tempNormalized.CleanedSamples,
                Array.Empty<RejectedSample>(),
                gaps,
                mode,
                gapPolicy,
                converter);
        }

        /// <summary>
        /// 将两条船舶航迹按统一固定时间步长对齐重采样（转发至 TrackTimeAligner）。
        /// </summary>
        public AlignedTrackResult AlignTwoTracks(
            IShipTrack firstTrack,
            IShipTrack secondTrack,
            double stepSeconds = 1.0,
            bool overlapOnly = true)
        {
            return TrackTimeAligner.AlignTwoTracks(firstTrack, secondTrack, stepSeconds, overlapOnly);
        }
    }
}
