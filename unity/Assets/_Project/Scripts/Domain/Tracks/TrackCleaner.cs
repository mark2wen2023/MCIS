using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 航迹异常点剔除与时间缺口检测器（对应 ARCHITECTURE.md 4.2.4 节与 P1_TASK_A 第 4 条）。
    /// 支持 Unavailable、OutOfRange、DuplicateTimestamp、OutOfOrder、PositionJump/SpeedGate、SpeedJump、CourseJump 等原因码诊断。
    /// </summary>
    public sealed partial class TrackCleaner
    {
        /// <summary>执行 AIS 原始记录序列清洗（实例方法转发）。</summary>
        public TrackCleaningReport Clean(
            IReadOnlyList<AisDecodedRecord> rawRecords,
            DateTimeOffset caseEpochUtc,
            TrackCleaningConfig config = null,
            IGeoConverter geoConverter = null,
            AntennaOffset antennaOffset = default(AntennaOffset),
            string vesselId = null,
            ISet<int> manuallyRestoredLineNumbers = null)
        {
            return CleanAisRecords(
                vesselId ?? "vessel",
                rawRecords,
                antennaOffset,
                caseEpochUtc,
                geoConverter,
                config ?? TrackCleaningConfig.CreateDefault(),
                manuallyRestoredLineNumbers);
        }

        /// <summary>执行 AIS 原始记录序列清洗，输出保留样本、剔除报告及时间缺口列表。</summary>
        public static TrackCleaningReport CleanAisRecords(
            string vesselId,
            IReadOnlyList<AisDecodedRecord> rawRecords,
            AntennaOffset antennaOffset,
            DateTimeOffset caseEpochUtc,
            IGeoConverter geoConverter = null,
            TrackCleaningConfig config = null,
            ISet<int> manuallyRestoredLineNumbers = null)
        {
            TrackCleaningConfig cfg = config ?? TrackCleaningConfig.CreateDefault();
            if (rawRecords == null || rawRecords.Count == 0)
            {
                return new TrackCleaningReport(vesselId, 0, Array.Empty<AisDecodedRecord>(), Array.Empty<TrackSample>(), Array.Empty<RejectedSample>(), Array.Empty<TimeGapSpan>());
            }

            IGeoConverter converter = EnsureGeoConverter(geoConverter, rawRecords);
            List<AisDecodedRecord> keptRecords = new List<AisDecodedRecord>(rawRecords.Count);
            List<TrackSample> cleanedSamples = new List<TrackSample>(rawRecords.Count);
            List<RejectedSample> rejected = new List<RejectedSample>();

            bool hasPrev = false;
            AisDecodedRecord prevRecord = default(AisDecodedRecord);
            TrackSample prevSample = default(TrackSample);
            EnuPosition prevAntennaEnu = EnuPosition.Zero;
            float lastValidHdgDeg = 0.0f;

            for (int i = 0; i < rawRecords.Count; i++)
            {
                AisDecodedRecord rec = rawRecords[i];
                SimTime simTime = SimTime.FromUtc(rec.TimestampUtc, caseEpochUtc);
                GeoCoord rawGeo = new GeoCoord(rec.LonDeg, rec.LatDeg, 0.0);
                bool isRestored = manuallyRestoredLineNumbers != null && manuallyRestoredLineNumbers.Contains(rec.SourceLineNumber);

                RejectReason fieldReason;
                string fieldDetail;
                if (!ValidateFieldAvailabilityAndRange(rec, out fieldReason, out fieldDetail))
                {
                    rejected.Add(new RejectedSample(rec.SourceLineNumber, simTime, rawGeo, rec.SogKn, rec.CogDeg, fieldReason, fieldDetail, false));
                    continue;
                }

                EnuPosition antennaEnu = converter.Wgs84ToEnu(rawGeo);
                if (hasPrev)
                {
                    double dt = simTime - prevSample.Time;
                    if (Math.Abs(dt) <= cfg.DuplicateTimeToleranceSec)
                    {
                        rejected.Add(new RejectedSample(rec.SourceLineNumber, simTime, rawGeo, rec.SogKn, rec.CogDeg,
                            RejectReason.DuplicateTimestamp,
                            string.Format(CultureInfo.InvariantCulture, "Duplicate timestamp at t={0:F3}s", simTime.Seconds), false));
                        continue;
                    }

                    if (dt < -cfg.DuplicateTimeToleranceSec)
                    {
                        rejected.Add(new RejectedSample(rec.SourceLineNumber, simTime, rawGeo, rec.SogKn, rec.CogDeg,
                            RejectReason.OutOfOrder,
                            string.Format(CultureInfo.InvariantCulture, "Out-of-order timestamp t={0:F3}s < prev={1:F3}s", simTime.Seconds, prevSample.Time.Seconds), false));
                        continue;
                    }

                    if (!isRestored)
                    {
                        RejectReason kinematicReason;
                        string kinematicDetail;
                        if (!ValidateKinematicsAgainstPrevious(prevRecord, prevAntennaEnu, rec, antennaEnu, dt, cfg, out kinematicReason, out kinematicDetail))
                        {
                            rejected.Add(new RejectedSample(rec.SourceLineNumber, simTime, rawGeo, rec.SogKn, rec.CogDeg, kinematicReason, kinematicDetail, false));
                            continue;
                        }
                    }
                }
                else if (!isRestored && rec.IsSogValid && rec.SogKn > cfg.MaxSpeedKn)
                {
                    rejected.Add(new RejectedSample(rec.SourceLineNumber, simTime, rawGeo, rec.SogKn, rec.CogDeg,
                        RejectReason.SpeedJump,
                        string.Format(CultureInfo.InvariantCulture, "Reported SOG {0:F1} kn exceeds max {1:F1} kn", rec.SogKn, cfg.MaxSpeedKn), false));
                    continue;
                }

                TrackSample sample = ConvertRecordToSample(rec, simTime, rawGeo, antennaEnu, antennaOffset, converter, cfg.ApplyAntennaOffset, ref lastValidHdgDeg);
                keptRecords.Add(rec);
                cleanedSamples.Add(sample);
                prevRecord = rec;
                prevSample = sample;
                prevAntennaEnu = antennaEnu;
                hasPrev = true;
            }

            IReadOnlyList<TimeGapSpan> gaps = DetectTimeGaps(cleanedSamples, cfg.MovingGapThresholdSec, cfg.AnchoredGapThresholdSec, keptRecords);
            return new TrackCleaningReport(vesselId, rawRecords.Count, keptRecords, cleanedSamples, rejected, gaps);
        }

        private static IGeoConverter EnsureGeoConverter(IGeoConverter provided, IReadOnlyList<AisDecodedRecord> records)
        {
            if (provided != null)
            {
                return provided;
            }
            for (int i = 0; i < records.Count; i++)
            {
                if (records[i].IsPositionValid)
                {
                    return new LocalEnuGeoConverter(new GeoCoord(records[i].LonDeg, records[i].LatDeg, 0.0));
                }
            }
            return new LocalEnuGeoConverter();
        }

        /// <summary>检测清洗后样本序列中的时间缺口列表。</summary>
        public static IReadOnlyList<TimeGapSpan> DetectTimeGaps(
            IReadOnlyList<TrackSample> samples,
            double movingGapThresholdSec = 60.0,
            double anchoredGapThresholdSec = 360.0,
            IReadOnlyList<AisDecodedRecord> keptRecords = null)
        {
            if (samples == null || samples.Count < 2)
            {
                return Array.Empty<TimeGapSpan>();
            }

            List<TimeGapSpan> gaps = new List<TimeGapSpan>();
            for (int i = 0; i < samples.Count - 1; i++)
            {
                double dt = samples[i + 1].Time - samples[i].Time;
                bool isAnchored = keptRecords != null &&
                                  keptRecords.Count == samples.Count &&
                                  (keptRecords[i].NavStatus == 1 || keptRecords[i].NavStatus == 5) &&
                                  (keptRecords[i + 1].NavStatus == 1 || keptRecords[i + 1].NavStatus == 5);
                double threshold = isAnchored ? anchoredGapThresholdSec : movingGapThresholdSec;
                if (dt > threshold)
                {
                    gaps.Add(new TimeGapSpan(samples[i].Time, samples[i + 1].Time, dt, samples[i].EnuCenter, samples[i + 1].EnuCenter));
                }
            }
            return gaps;
        }
    }
}
