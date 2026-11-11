using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Cpa
{
    public sealed partial class CpaService
    {
        private static List<(SimTime Start, SimTime End, RiskLevel Level)> BuildRiskIntervals(IReadOnlyList<CpaResult> samples)
        {
            List<(SimTime Start, SimTime End, RiskLevel Level)> intervals =
                new List<(SimTime, SimTime, RiskLevel)>();
            if (samples == null || samples.Count == 0)
            {
                return intervals;
            }

            RiskLevel current = samples[0].RiskLevel;
            SimTime spanStart = samples[0].Time;

            for (int i = 1; i < samples.Count; i++)
            {
                RiskLevel lvl = samples[i].RiskLevel;
                if (lvl != current)
                {
                    if (current != RiskLevel.Safe)
                    {
                        intervals.Add((spanStart, samples[i].Time, current));
                    }
                    current = lvl;
                    spanStart = samples[i].Time;
                }
            }

            if (current != RiskLevel.Safe)
            {
                intervals.Add((spanStart, samples[samples.Count - 1].Time, current));
            }

            return intervals;
        }

        private void UpdateMarkersForSeries(CpaTimeSeries series)
        {
            string pairTag = series.Pair.OwnVesselId + "->" + series.Pair.TargetVesselId;
            _markers.RemoveAll(m => string.Equals(m.TargetEntityId, pairTag, StringComparison.Ordinal));

            if (series.Samples.Count > 0)
            {
                CpaResult minDist = series.MinDistanceSample;
                _markers.Add(new TimelineMarker(
                    "CPA_MIN_DIST_" + pairTag,
                    minDist.Time,
                    "MinDCPA",
                    string.Format(CultureInfo.InvariantCulture, "最小距离 {0:F2} nm", minDist.CurrentDistanceNm),
                    minDist.RiskLevel,
                    pairTag));

                for (int i = 0; i < series.RiskIntervals.Count; i++)
                {
                    var span = series.RiskIntervals[i];
                    if (span.Level == RiskLevel.Danger)
                    {
                        _markers.Add(new TimelineMarker(
                            string.Format(CultureInfo.InvariantCulture, "CPA_DANGER_{0}_{1}", pairTag, i),
                            span.Start,
                            "CPA_Danger",
                            "进入 CPA 危险区",
                            RiskLevel.Danger,
                            pairTag));
                    }
                }
            }

            _markers.Sort();
            MarkersChanged?.Invoke();
        }
    }
}
