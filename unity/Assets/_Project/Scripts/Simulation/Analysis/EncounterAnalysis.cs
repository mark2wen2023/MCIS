using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Cpa;

namespace Mcis.Simulation.Analysis
{
    /// <summary>全时段分析中的关键时刻。</summary>
    public readonly struct AnalysisKeyMoment
    {
        public string Kind { get; }
        public SimTime Time { get; }
        public string Label { get; }
        public CpaResult? Sample { get; }

        public AnalysisKeyMoment(string kind, SimTime time, string label, CpaResult? sample = null)
        {
            Kind = kind ?? string.Empty;
            Time = time;
            Label = label ?? string.Empty;
            Sample = sample;
        }
    }

    /// <summary>按剔除原因汇总的计数。</summary>
    public readonly struct RejectReasonCount
    {
        public RejectReason Reason { get; }
        public int Count { get; }

        public RejectReasonCount(RejectReason reason, int count)
        {
            Reason = reason;
            Count = count;
        }
    }

    /// <summary>航迹清洗剔除点统计。</summary>
    public sealed class RejectedPointStatistics
    {
        public int TotalCleaned { get; }
        public int TotalRejected { get; }
        public int ManuallyRestored { get; }
        public IReadOnlyList<RejectReasonCount> ByReason { get; }

        public RejectedPointStatistics(
            int totalCleaned,
            int totalRejected,
            int manuallyRestored,
            IReadOnlyList<RejectReasonCount> byReason)
        {
            TotalCleaned = totalCleaned;
            TotalRejected = totalRejected;
            ManuallyRestored = manuallyRestored;
            ByReason = byReason ?? Array.Empty<RejectReasonCount>();
        }

        public static RejectedPointStatistics FromTracks(IEnumerable<IShipTrack> tracks)
        {
            int cleaned = 0;
            int rejected = 0;
            int restored = 0;
            var map = new Dictionary<RejectReason, int>();
            if (tracks != null)
            {
                foreach (IShipTrack track in tracks)
                {
                    if (track == null)
                    {
                        continue;
                    }

                    cleaned += track.CleanedSamples != null ? track.CleanedSamples.Count : 0;
                    if (track.RejectedSamples == null)
                    {
                        continue;
                    }

                    for (int i = 0; i < track.RejectedSamples.Count; i++)
                    {
                        RejectedSample s = track.RejectedSamples[i];
                        rejected++;
                        if (s.IsManuallyRestored)
                        {
                            restored++;
                        }

                        int n;
                        map.TryGetValue(s.Reason, out n);
                        map[s.Reason] = n + 1;
                    }
                }
            }

            var list = new List<RejectReasonCount>();
            foreach (KeyValuePair<RejectReason, int> kv in map)
            {
                list.Add(new RejectReasonCount(kv.Key, kv.Value));
            }

            list.Sort((a, b) => b.Count.CompareTo(a.Count));
            return new RejectedPointStatistics(cleaned, rejected, restored, list);
        }
    }

    /// <summary>全时段距离 / DCPA / TCPA 序列及关键时刻提取报告。</summary>
    public sealed class EncounterAnalysisReport
    {
        public CpaTimeSeries Series { get; }
        public IReadOnlyList<AnalysisKeyMoment> KeyMoments { get; }
        public AnalysisKeyMoment? FirstWarning { get; }
        public AnalysisKeyMoment? FirstDanger { get; }
        public AnalysisKeyMoment? MinDistance { get; }
        public AnalysisKeyMoment? Collision { get; }
        public RejectedPointStatistics RejectedStats { get; }

        public EncounterAnalysisReport(
            CpaTimeSeries series,
            IReadOnlyList<AnalysisKeyMoment> keyMoments,
            AnalysisKeyMoment? firstWarning,
            AnalysisKeyMoment? firstDanger,
            AnalysisKeyMoment? minDistance,
            AnalysisKeyMoment? collision,
            RejectedPointStatistics rejectedStats)
        {
            Series = series;
            KeyMoments = keyMoments ?? Array.Empty<AnalysisKeyMoment>();
            FirstWarning = firstWarning;
            FirstDanger = firstDanger;
            MinDistance = minDistance;
            Collision = collision;
            RejectedStats = rejectedStats;
        }
    }

    /// <summary>基于已预计算 CPA 序列提取首次警告/危险、最近距离与碰撞时刻，并汇总剔除点。</summary>
    public static class EncounterAnalyzer
    {
        public static EncounterAnalysisReport Analyze(
            CpaTimeSeries series,
            SimTime? collisionTime = null,
            IEnumerable<IShipTrack> tracks = null)
        {
            var moments = new List<AnalysisKeyMoment>();
            AnalysisKeyMoment? firstWarning = null;
            AnalysisKeyMoment? firstDanger = null;
            AnalysisKeyMoment? minDistance = null;

            if (series != null && series.Samples != null && series.Samples.Count > 0)
            {
                // 若已给出首次接触 tc，最近距离只在 tc 及以前的样本中提取，避免碰撞后船体交叠把“最近距离”推到 tc 之后。
                CpaResult min = series.MinDistanceSample;
                bool have = false;
                for (int i = 0; i < series.Samples.Count; i++)
                {
                    CpaResult s = series.Samples[i];
                    if (collisionTime.HasValue && s.Time.Seconds > collisionTime.Value.Seconds + 1e-9)
                    {
                        continue;
                    }

                    if (!have || s.CurrentDistanceM < min.CurrentDistanceM)
                    {
                        min = s;
                        have = true;
                    }
                }

                if (collisionTime.HasValue)
                {
                    CpaResult atTc = series.GetAt(collisionTime.Value);
                    if (!have || atTc.CurrentDistanceM < min.CurrentDistanceM)
                    {
                        min = atTc;
                        have = true;
                    }
                }

                minDistance = new AnalysisKeyMoment("MinDistance", min.Time, "最近距离", min);
                moments.Add(minDistance.Value);

                for (int i = 0; i < series.Samples.Count; i++)
                {
                    CpaResult s = series.Samples[i];
                    CpaResult? prev = i > 0 ? series.Samples[i - 1] : (CpaResult?)null;
                    if (s.RiskLevel >= RiskLevel.Warning &&
                        (!prev.HasValue || prev.Value.RiskLevel < RiskLevel.Warning) &&
                        !firstWarning.HasValue)
                    {
                        firstWarning = new AnalysisKeyMoment("FirstWarning", s.Time, "首次警告", s);
                        moments.Add(firstWarning.Value);
                    }

                    if (s.RiskLevel >= RiskLevel.Danger &&
                        (!prev.HasValue || prev.Value.RiskLevel < RiskLevel.Danger) &&
                        !firstDanger.HasValue)
                    {
                        firstDanger = new AnalysisKeyMoment("FirstDanger", s.Time, "首次危险", s);
                        moments.Add(firstDanger.Value);
                    }
                }
            }

            AnalysisKeyMoment? collision = null;
            if (collisionTime.HasValue)
            {
                CpaResult? sample = null;
                if (series != null)
                {
                    sample = series.GetAt(collisionTime.Value);
                }

                collision = new AnalysisKeyMoment("Collision", collisionTime.Value, "首次接触 tc", sample);
                moments.Add(collision.Value);
            }

            moments.Sort((a, b) => a.Time.CompareTo(b.Time));
            RejectedPointStatistics stats = RejectedPointStatistics.FromTracks(tracks);
            return new EncounterAnalysisReport(series, moments, firstWarning, firstDanger, minDistance, collision, stats);
        }
    }
}
