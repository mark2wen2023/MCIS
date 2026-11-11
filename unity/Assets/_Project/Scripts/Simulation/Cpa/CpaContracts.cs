using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Cpa
{
    /// <summary>
    /// 全时段预计算的 CPA 时间序列与极值结果（对应 ARCHITECTURE.md 5.3.7 节）。
    /// 支持 O(1) 索引 / 二分查找与线性插值查询，结果与回放方向无关。
    /// </summary>
    public sealed class CpaTimeSeries
    {
        /// <summary>本船与目标船配对键。</summary>
        public CpaPairKey Pair { get; }

        /// <summary>固定预计算采样步长（秒）。</summary>
        public double StepSeconds { get; }

        /// <summary>序列起始仿真时间。</summary>
        public SimTime StartTime { get; }

        /// <summary>序列结束仿真时间。</summary>
        public SimTime EndTime { get; }

        /// <summary>按时间升序排列的预计算 CPA 样本序列。</summary>
        public IReadOnlyList<CpaResult> Samples { get; }

        /// <summary>全时段内预测 DCPA 最小的样本点。</summary>
        public CpaResult MinDcpaSample { get; }

        /// <summary>全时段内两船实际距离（CurrentDistance）最小的样本点。</summary>
        public CpaResult MinDistanceSample { get; }

        /// <summary>全时段最小实际距离对应的仿真时刻。</summary>
        public SimTime MinDistanceTime
        {
            get { return MinDistanceSample.Time; }
        }

        /// <summary>全时段最小实际距离（海里）。</summary>
        public double MinDistanceNm
        {
            get { return MinDistanceSample.CurrentDistanceNm; }
        }

        /// <summary>经滞回确认后的非安全风险持续区间列表。</summary>
        public IReadOnlyList<(SimTime Start, SimTime End, RiskLevel Level)> RiskIntervals { get; }

        /// <summary>构造 CPA 预计算时间序列。</summary>
        public CpaTimeSeries(
            CpaPairKey pair,
            double stepSeconds,
            IReadOnlyList<CpaResult> samples,
            CpaResult minDcpaSample,
            CpaResult minDistanceSample,
            IReadOnlyList<(SimTime Start, SimTime End, RiskLevel Level)> riskIntervals)
        {
            Pair = pair;
            StepSeconds = stepSeconds > 0.0 ? stepSeconds : 1.0;
            Samples = samples ?? Array.Empty<CpaResult>();
            MinDcpaSample = minDcpaSample;
            MinDistanceSample = minDistanceSample;
            RiskIntervals = riskIntervals ?? Array.Empty<(SimTime, SimTime, RiskLevel)>();

            if (Samples.Count > 0)
            {
                StartTime = Samples[0].Time;
                EndTime = Samples[Samples.Count - 1].Time;
            }
            else
            {
                StartTime = SimTime.Zero;
                EndTime = SimTime.Zero;
            }
        }

        /// <summary>查询任意仿真时间（秒）的 CPA 结果（O(1) 索引/二分查找 + 线性插值）。</summary>
        public CpaResult GetAt(double timeSeconds)
        {
            return GetAt(new SimTime(timeSeconds));
        }

        /// <summary>查询任意仿真时间的 CPA 结果（O(1) 索引/二分查找 + 线性插值）。</summary>
        public CpaResult GetAt(SimTime time)
        {
            int count = Samples.Count;
            if (count == 0)
            {
                return default;
            }
            if (count == 1 || time <= Samples[0].Time)
            {
                return Samples[0];
            }
            if (time >= Samples[count - 1].Time)
            {
                return Samples[count - 1];
            }

            int lo = FindBracketIndex(time.Seconds);
            CpaResult s0 = Samples[lo];
            CpaResult s1 = Samples[lo + 1];

            double t0 = s0.Time.Seconds;
            double t1 = s1.Time.Seconds;
            if (Math.Abs(time.Seconds - t0) <= 1e-9)
            {
                return s0;
            }
            if (Math.Abs(time.Seconds - t1) <= 1e-9)
            {
                return s1;
            }

            double dt = t1 - t0;
            if (dt <= 1e-12)
            {
                return s0;
            }

            double alpha = (time.Seconds - t0) / dt;
            return InterpolateResult(s0, s1, time, alpha);
        }

        private int FindBracketIndex(double targetSeconds)
        {
            int count = Samples.Count;
            double offset = targetSeconds - Samples[0].Time.Seconds;
            int approx = (int)Math.Floor(offset / StepSeconds);
            if (approx >= 0 && approx < count - 1)
            {
                double a = Samples[approx].Time.Seconds;
                double b = Samples[approx + 1].Time.Seconds;
                if (targetSeconds >= a - 1e-9 && targetSeconds <= b + 1e-9)
                {
                    return approx;
                }
            }

            int lo = 0;
            int hi = count - 2;
            while (lo <= hi)
            {
                int mid = lo + ((hi - lo) >> 1);
                double midStart = Samples[mid].Time.Seconds;
                double midEnd = Samples[mid + 1].Time.Seconds;
                if (targetSeconds < midStart)
                {
                    hi = mid - 1;
                }
                else if (targetSeconds > midEnd)
                {
                    lo = mid + 1;
                }
                else
                {
                    return mid;
                }
            }

            return Math.Max(0, Math.Min(count - 2, lo));
        }

        private static CpaResult InterpolateResult(CpaResult s0, CpaResult s1, SimTime time, double alpha)
        {
            double distM = Lerp(s0.CurrentDistanceM, s1.CurrentDistanceM, alpha);
            double clearanceM = Lerp(s0.HullClearanceM, s1.HullClearanceM, alpha);
            double bearingDeg = LerpAngleDeg(s0.TrueBearingDeg, s1.TrueBearingDeg, alpha);
            double relCourseDeg = LerpAngleDeg(s0.RelativeCourseDeg, s1.RelativeCourseDeg, alpha);
            double relSpeedMps = Lerp(s0.RelativeSpeedMps, s1.RelativeSpeedMps, alpha);
            double dcpaM = Lerp(s0.DcpaM, s1.DcpaM, alpha);

            bool isDegenerate = s0.IsDegenerate || s1.IsDegenerate;
            double tcpaSec = isDegenerate
                ? double.PositiveInfinity
                : Lerp(s0.TcpaSec, s1.TcpaSec, alpha);
            bool isDiverging = !isDegenerate && tcpaSec < 0.0;

            EnuPosition ownCpa = new EnuPosition(
                Lerp(s0.OwnCpaEnu.EastM, s1.OwnCpaEnu.EastM, alpha),
                Lerp(s0.OwnCpaEnu.NorthM, s1.OwnCpaEnu.NorthM, alpha),
                Lerp(s0.OwnCpaEnu.UpM, s1.OwnCpaEnu.UpM, alpha));
            EnuPosition targetCpa = new EnuPosition(
                Lerp(s0.TargetCpaEnu.EastM, s1.TargetCpaEnu.EastM, alpha),
                Lerp(s0.TargetCpaEnu.NorthM, s1.TargetCpaEnu.NorthM, alpha),
                Lerp(s0.TargetCpaEnu.UpM, s1.TargetCpaEnu.UpM, alpha));

            return new CpaResult(
                s0.Pair, time, distM, clearanceM, bearingDeg, relCourseDeg,
                relSpeedMps, dcpaM, tcpaSec, ownCpa, targetCpa,
                isDiverging, isDegenerate, s0.RiskLevel);
        }

        private static double Lerp(double a, double b, double t)
        {
            return a + (b - a) * t;
        }

        private static double LerpAngleDeg(double aDeg, double bDeg, double t)
        {
            double diff = ((bDeg - aDeg + 540.0) % 360.0) - 180.0;
            double res = (aDeg + diff * t) % 360.0;
            return res < 0.0 ? res + 360.0 : res;
        }
    }
}
