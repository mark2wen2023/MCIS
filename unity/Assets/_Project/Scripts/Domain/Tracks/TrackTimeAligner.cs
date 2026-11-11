using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 同一仿真时刻下两艘船的对齐采样点配对。
    /// </summary>
    public readonly struct AlignedSamplePair
    {
        /// <summary>统一时间轴上的仿真时刻。</summary>
        public SimTime Time { get; }

        /// <summary>第一艘船在该时刻的采样状态。</summary>
        public TrackSample First { get; }

        /// <summary>第二艘船在该时刻的采样状态。</summary>
        public TrackSample Second { get; }

        /// <summary>构造对齐采样点配对。</summary>
        public AlignedSamplePair(SimTime time, TrackSample first, TrackSample second)
        {
            Time = time;
            First = first;
            Second = second;
        }
    }

    /// <summary>
    /// 两船航迹在统一时间轴上的重采样对齐结果（对应 ARCHITECTURE.md 4.2.3 节与 P1_TASK_A 第 4 条）。
    /// </summary>
    public sealed class AlignedTrackResult
    {
        /// <summary>对齐区间起始仿真时间。</summary>
        public SimTime StartTime { get; }

        /// <summary>对齐区间结束仿真时间。</summary>
        public SimTime EndTime { get; }

        /// <summary>重采样时间步长（秒）。</summary>
        public double StepSeconds { get; }

        /// <summary>是否存在有效的公共时间区间。</summary>
        public bool HasValidOverlap { get; }

        /// <summary>统一时间轴采样时刻序列。</summary>
        public IReadOnlyList<SimTime> Timestamps { get; }

        /// <summary>第一艘船在统一时间轴上的重采样点序列。</summary>
        public IReadOnlyList<TrackSample> FirstTrackSamples { get; }

        /// <summary>第二艘船在统一时间轴上的重采样点序列。</summary>
        public IReadOnlyList<TrackSample> SecondTrackSamples { get; }

        /// <summary>逐时刻双船同步采样对序列。</summary>
        public IReadOnlyList<AlignedSamplePair> Pairs { get; }

        /// <summary>构造双船时间对齐结果。</summary>
        public AlignedTrackResult(
            SimTime startTime,
            SimTime endTime,
            double stepSeconds,
            bool hasValidOverlap,
            IReadOnlyList<SimTime> timestamps,
            IReadOnlyList<TrackSample> firstTrackSamples,
            IReadOnlyList<TrackSample> secondTrackSamples,
            IReadOnlyList<AlignedSamplePair> pairs)
        {
            StartTime = startTime;
            EndTime = endTime;
            StepSeconds = stepSeconds;
            HasValidOverlap = hasValidOverlap;
            Timestamps = timestamps ?? Array.Empty<SimTime>();
            FirstTrackSamples = firstTrackSamples ?? Array.Empty<TrackSample>();
            SecondTrackSamples = secondTrackSamples ?? Array.Empty<TrackSample>();
            Pairs = pairs ?? Array.Empty<AlignedSamplePair>();
        }
    }

    /// <summary>
    /// 航迹时间轴对齐与等步长重采样工具。
    /// </summary>
    public static class TrackTimeAligner
    {
        /// <summary>
        /// 将两条航迹重采样到统一时间轴（默认取两船公共重叠时间区间 [max(Start), min(End)]）。
        /// </summary>
        public static AlignedTrackResult AlignTwoTracks(
            IShipTrack firstTrack,
            IShipTrack secondTrack,
            double stepSeconds = 1.0,
            bool overlapOnly = true)
        {
            if (firstTrack == null || secondTrack == null ||
                firstTrack.CleanedSamples.Count == 0 || secondTrack.CleanedSamples.Count == 0)
            {
                return new AlignedTrackResult(SimTime.Zero, SimTime.Zero, stepSeconds, false, null, null, null, null);
            }

            double step = stepSeconds > 1e-6 ? stepSeconds : 1.0;
            double startSec = overlapOnly
                ? Math.Max(firstTrack.StartTime.Seconds, secondTrack.StartTime.Seconds)
                : Math.Min(firstTrack.StartTime.Seconds, secondTrack.StartTime.Seconds);
            double endSec = overlapOnly
                ? Math.Min(firstTrack.EndTime.Seconds, secondTrack.EndTime.Seconds)
                : Math.Max(firstTrack.EndTime.Seconds, secondTrack.EndTime.Seconds);

            if (endSec < startSec - 1e-9)
            {
                return new AlignedTrackResult(
                    new SimTime(startSec), new SimTime(endSec), step, false, null, null, null, null);
            }

            List<SimTime> times = BuildUniformTimeGrid(startSec, endSec, step);
            List<TrackSample> firstSamples = new List<TrackSample>(times.Count);
            List<TrackSample> secondSamples = new List<TrackSample>(times.Count);
            List<AlignedSamplePair> pairs = new List<AlignedSamplePair>(times.Count);

            for (int i = 0; i < times.Count; i++)
            {
                SimTime t = times[i];
                TrackSample s1 = firstTrack.SampleAt(t);
                TrackSample s2 = secondTrack.SampleAt(t);
                firstSamples.Add(s1);
                secondSamples.Add(s2);
                pairs.Add(new AlignedSamplePair(t, s1, s2));
            }

            return new AlignedTrackResult(
                new SimTime(startSec),
                new SimTime(endSec),
                step,
                true,
                times,
                firstSamples,
                secondSamples,
                pairs);
        }

        /// <summary>在给定起止时间区间内按固定步长重采样单条航迹。</summary>
        public static IReadOnlyList<TrackSample> ResampleTrack(
            IShipTrack track,
            SimTime startTime,
            SimTime endTime,
            double stepSeconds = 1.0)
        {
            if (track == null || track.CleanedSamples.Count == 0 || endTime.Seconds < startTime.Seconds - 1e-9)
            {
                return Array.Empty<TrackSample>();
            }

            double step = stepSeconds > 1e-6 ? stepSeconds : 1.0;
            List<SimTime> times = BuildUniformTimeGrid(startTime.Seconds, endTime.Seconds, step);
            List<TrackSample> result = new List<TrackSample>(times.Count);
            for (int i = 0; i < times.Count; i++)
            {
                result.Add(track.SampleAt(times[i]));
            }
            return result;
        }

        private static List<SimTime> BuildUniformTimeGrid(double startSec, double endSec, double stepSec)
        {
            List<SimTime> times = new List<SimTime>();
            double span = Math.Max(0.0, endSec - startSec);
            int steps = (int)Math.Floor(span / stepSec + 1e-9);
            for (int i = 0; i <= steps; i++)
            {
                double t = startSec + i * stepSec;
                if (t > endSec)
                {
                    t = endSec;
                }
                times.Add(new SimTime(t));
            }
            if (times.Count == 0 || Math.Abs(times[times.Count - 1].Seconds - endSec) > 1e-6)
            {
                times.Add(new SimTime(endSec));
            }
            return times;
        }
    }
}
