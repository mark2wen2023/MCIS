using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 可连续按时间求值的单船航迹实现（支持线性、三次 Hermite、Catmull-Rom 插值及时间缺口策略）。
    /// </summary>
    public sealed partial class ShipTrack : IShipTrack
    {
        private readonly List<TrackSample> _samples;
        private readonly List<RejectedSample> _rejected;
        private readonly List<TimeGapSpan> _gaps;
        private readonly Double2[] _nodeTangents;
        private readonly IGeoConverter _geoConverter;
        private readonly InterpolationMode _mode;
        private readonly GapPolicy _gapPolicy;

        /// <inheritdoc />
        public string VesselId { get; }

        /// <inheritdoc />
        public SimTime StartTime { get; }

        /// <inheritdoc />
        public SimTime EndTime { get; }

        /// <inheritdoc />
        public IReadOnlyList<TrackSample> CleanedSamples
        {
            get { return _samples; }
        }

        /// <inheritdoc />
        public IReadOnlyList<RejectedSample> RejectedSamples
        {
            get { return _rejected; }
        }

        /// <inheritdoc />
        public IReadOnlyList<TimeGapSpan> TimeGaps
        {
            get { return _gaps; }
        }

        /// <summary>当前使用的插值算法模式。</summary>
        public InterpolationMode InterpolationMode
        {
            get { return _mode; }
        }

        /// <summary>当前使用的时间缺口策略。</summary>
        public GapPolicy GapPolicy
        {
            get { return _gapPolicy; }
        }

        /// <summary>构造单船航迹实例。</summary>
        public ShipTrack(
            string vesselId,
            IReadOnlyList<TrackSample> cleanedSamples,
            IReadOnlyList<RejectedSample> rejectedSamples = null,
            IReadOnlyList<TimeGapSpan> timeGaps = null,
            InterpolationMode mode = InterpolationMode.CubicHermite,
            GapPolicy gapPolicy = GapPolicy.ConnectDashed,
            IGeoConverter geoConverter = null)
        {
            VesselId = vesselId ?? string.Empty;
            _mode = mode;
            _gapPolicy = gapPolicy;
            _samples = NormalizeAndSortSamples(cleanedSamples, ref geoConverter);
            _geoConverter = geoConverter ?? new LocalEnuGeoConverter();
            _rejected = rejectedSamples != null ? new List<RejectedSample>(rejectedSamples) : new List<RejectedSample>();
            _gaps = timeGaps != null ? new List<TimeGapSpan>(timeGaps) : new List<TimeGapSpan>();

            if (_samples.Count > 0)
            {
                StartTime = _samples[0].Time;
                EndTime = _samples[_samples.Count - 1].Time;
            }
            else
            {
                StartTime = SimTime.Zero;
                EndTime = SimTime.Zero;
            }

            _nodeTangents = PrecomputeNodeTangents(_samples, _mode);
        }

        /// <inheritdoc />
        public bool IsInTimeGap(SimTime time, out TimeGapSpan gap)
        {
            for (int i = 0; i < _gaps.Count; i++)
            {
                TimeGapSpan g = _gaps[i];
                if (time.Seconds > g.StartTime.Seconds + 1e-7 && time.Seconds < g.EndTime.Seconds - 1e-7)
                {
                    gap = g;
                    return true;
                }
            }
            gap = default(TimeGapSpan);
            return false;
        }

        /// <inheritdoc />
        public TrackSample SampleAt(SimTime time)
        {
            TrackSample sample;
            TrySampleAt(time, out sample);
            return sample;
        }

        /// <inheritdoc />
        public bool TrySampleAt(SimTime time, out TrackSample sample)
        {
            if (_samples.Count == 0)
            {
                sample = default(TrackSample);
                return false;
            }

            if (_samples.Count == 1)
            {
                bool exact = Math.Abs(time - _samples[0].Time) <= 1e-7;
                sample = exact ? _samples[0] : CloneWithTimeAndProvenance(_samples[0], time, SampleProvenance.Rejected);
                return exact;
            }

            if (time.Seconds < StartTime.Seconds - 1e-7)
            {
                sample = CloneWithTimeAndProvenance(_samples[0], time, SampleProvenance.Rejected);
                return false;
            }

            if (time.Seconds > EndTime.Seconds + 1e-7)
            {
                sample = CloneWithTimeAndProvenance(_samples[_samples.Count - 1], time, SampleProvenance.Rejected);
                return false;
            }

            int idx = FindSegmentIndex(time);
            TrackSample s0 = _samples[idx];
            TrackSample s1 = _samples[idx + 1];

            if (Math.Abs(time - s0.Time) <= 1e-7)
            {
                sample = s0;
                return true;
            }
            if (Math.Abs(time - s1.Time) <= 1e-7)
            {
                sample = s1;
                return true;
            }

            TimeGapSpan activeGap;
            bool inGap = IsInTimeGap(time, out activeGap);
            if (inGap && _gapPolicy == GapPolicy.HideVessel)
            {
                sample = CloneWithTimeAndProvenance(s0, time, SampleProvenance.Rejected);
                return false;
            }

            sample = EvaluateSegment(idx, s0, s1, time, inGap);
            return true;
        }
    }
}
