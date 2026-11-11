using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Cpa;
using Xunit;

namespace Mcis.Pure.Tests
{
    /// <summary>
    /// M5 CpaService 单元测试：覆盖全时段预计算、正向与反向逐点/插值查询一致性、
    /// 风险分级滞回（立即升级、越过阈值×(1+裕度)并保持 N 秒才降级）以及最小距离时刻查询。
    /// </summary>
    public sealed class CpaServiceTests
    {
        [Fact]
        public void ForwardAndReversePlaybackQueries_ProduceIdenticalResults()
        {
            // 两船在 t = [0, 900s] (15 min) 内从远到近再远离，中间经历 Safe -> Warning -> Danger -> Safe
            // 本船：从 (0, 0) 向北 12 kn (0.0033333 nm/s)
            // 目标船：在 t = 540s (9 min) 处与本船最近，正横距离 0.15 nm，向南 12 kn
            double voKn = 12.0;
            double vtKn = 12.0;
            double minTimeSec = 540.0;
            double minPassDistNm = 0.15;

            Func<double, VesselMotionState> ownSampler = tSec =>
            {
                double northNm = voKn * (tSec / 3600.0);
                return new VesselMotionState(0.0, northNm, voKn, 0.0, tSec);
            };

            Func<double, VesselMotionState> targetSampler = tSec =>
            {
                double northAtMin = voKn * (minTimeSec / 3600.0);
                double northNm = northAtMin + vtKn * ((minTimeSec - tSec) / 3600.0);
                return new VesselMotionState(minPassDistNm, northNm, vtKn, 180.0, tSec);
            };

            RiskThresholds thresholds = new RiskThresholds(
                "Test", dangerDcpaNm: 0.3, dangerTcpaMin: 6.0,
                warningDcpaNm: 1.0, warningTcpaMin: 12.0,
                hysteresisSeconds: 3.0, downgradeMarginRatio: 0.1);

            CpaService service = new CpaService(
                ownSampler, targetSampler,
                startTimeSeconds: 0.0, endTimeSeconds: 900.0,
                stepSeconds: 1.0, thresholds: thresholds);

            // 构造包含整数网格点与非整数插值点的查询序列
            List<double> queryTimes = new List<double>();
            for (double t = 0.0; t <= 900.0; t += 0.37)
            {
                queryTimes.Add(Math.Round(t, 4));
            }
            queryTimes.Add(540.0);
            queryTimes.Add(900.0);

            // 正向逐点查询
            CpaResult[] forwardResults = new CpaResult[queryTimes.Count];
            for (int i = 0; i < queryTimes.Count; i++)
            {
                forwardResults[i] = service.GetAt(queryTimes[i]);
            }

            // 反向逐点查询
            for (int i = queryTimes.Count - 1; i >= 0; i--)
            {
                CpaResult rev = service.GetAt(queryTimes[i]);
                CpaResult fwd = forwardResults[i];

                Assert.Equal(fwd.RiskLevel, rev.RiskLevel);
                Assert.Equal(fwd.CurrentDistanceNm, rev.CurrentDistanceNm, 12);
                Assert.Equal(fwd.DcpaNm, rev.DcpaNm, 12);
                Assert.Equal(fwd.TcpaMin, rev.TcpaMin, 12);
            }
        }

        [Fact]
        public void MinimumDistanceTimeQuery_FindsExactClosestMoment()
        {
            // 本船静止于原点，目标船在东侧 0.25 nm 处从北向南以 18 kn 匀速通过，t = 300s 时正东通过
            double passTimeSec = 300.0;
            double speedKn = 18.0; // 0.005 nm/s

            Func<double, VesselMotionState> ownSampler = t =>
                new VesselMotionState(0.0, 0.0, 0.0, 0.0, t);

            Func<double, VesselMotionState> targetSampler = t =>
            {
                double northNm = (passTimeSec - t) * (speedKn / 3600.0);
                return new VesselMotionState(0.25, northNm, speedKn, 180.0, t);
            };

            CpaService service = new CpaService(
                ownSampler, targetSampler,
                startTimeSeconds: 0.0, endTimeSeconds: 600.0, stepSeconds: 1.0);

            SimTime minTime = service.GetMinDistanceTime();
            CpaResult minSample = service.GetMinDistanceSample();

            Assert.Equal(passTimeSec, minTime.Seconds, 6);
            Assert.Equal(0.25, minSample.CurrentDistanceNm, 6);
        }

        [Fact]
        public void Hysteresis_UpgradesImmediately_AndDowngradesOnlyAfterMarginAndHoldDuration()
        {
            // 配置：Danger DCPA < 0.3 nm, TCPA < 6 min；Warning DCPA < 1.0 nm, TCPA < 12 min
            // 裕度 10% (Danger 降级需 DCPA >= 0.33 nm；Warning 降级需 DCPA >= 1.10 nm)，保持时长 N = 3.0 s
            RiskThresholds thresholds = new RiskThresholds(
                "HysteresisTest",
                dangerDcpaNm: 0.3, dangerTcpaMin: 6.0,
                warningDcpaNm: 1.0, warningTcpaMin: 12.0,
                hysteresisSeconds: 3.0, downgradeMarginRatio: 0.1);

            // 固定本船在原点静止，目标船在北侧 1.0 nm 向南航速 15 kn (TCPA ≈ 4 min < 6 min)，
            // 通过改变目标船东向偏移东坐标 EastNm 直接精确控制各时刻的瞬时 DCPA = EastNm
            Func<double, VesselMotionState> ownSampler = t =>
                new VesselMotionState(0.0, 0.0, 0.0, 0.0, t);

            Func<double, VesselMotionState> targetSampler = t =>
            {
                double desiredDcpaNm;
                if (t < 1.0) desiredDcpaNm = 1.50;      // t=0: Safe (1.50 >= 1.0)
                else if (t < 2.0) desiredDcpaNm = 0.80; // t=1: 立即升级 Warning (0.80 < 1.0)
                else if (t < 4.0) desiredDcpaNm = 0.20; // t=2,3: 立即升级 Danger (0.20 < 0.3)
                else if (t < 7.0) desiredDcpaNm = 0.31; // t=4,5,6: 0.30 < 0.31 < 0.33 (未越过 0.3*(1+0.1)=0.33 裕度，保持 Danger)
                else if (t < 9.0) desiredDcpaNm = 0.40; // t=7,8: 越过 0.33 但仅保持 2s < 3s，仍保持 Danger
                else if (t < 10.0) desiredDcpaNm = 0.25;// t=9: 回落到 0.25，计时器清零，仍为 Danger
                else if (t < 14.0) desiredDcpaNm = 0.50;// t=10,11,12,13: 越过 0.33，在 t=10(1s), t=11(2s) 仍 Danger，t=12(3s) 降级为 Warning
                else desiredDcpaNm = 1.20;              // t=14..18: 越过 Warning 裕度 1.10，满 3s 后在 t=16 降级为 Safe

                return new VesselMotionState(desiredDcpaNm, 1.0, 15.0, 180.0, t);
            };

            CpaService service = new CpaService(
                ownSampler, targetSampler,
                startTimeSeconds: 0.0, endTimeSeconds: 18.0,
                stepSeconds: 1.0, thresholds: thresholds);

            Assert.Equal(RiskLevel.Safe, service.GetAt(0.0).RiskLevel);
            // 立即升级
            Assert.Equal(RiskLevel.Warning, service.GetAt(1.0).RiskLevel);
            Assert.Equal(RiskLevel.Danger, service.GetAt(2.0).RiskLevel);

            // 未越过 0.33 nm 裕度带，不降级
            Assert.Equal(RiskLevel.Danger, service.GetAt(4.0).RiskLevel);
            Assert.Equal(RiskLevel.Danger, service.GetAt(6.0).RiskLevel);

            // 越过裕度但未满 3s 且中途回落，不降级
            Assert.Equal(RiskLevel.Danger, service.GetAt(8.0).RiskLevel);
            Assert.Equal(RiskLevel.Danger, service.GetAt(9.0).RiskLevel);

            // 从 t=10 起连续越过 0.33 nm：t=10 (累计1s), t=11 (累计2s) 仍为 Danger；t=12 (累计3s) 降级为 Warning
            Assert.Equal(RiskLevel.Danger, service.GetAt(10.0).RiskLevel);
            Assert.Equal(RiskLevel.Danger, service.GetAt(11.0).RiskLevel);
            Assert.Equal(RiskLevel.Warning, service.GetAt(12.0).RiskLevel);
            Assert.Equal(RiskLevel.Warning, service.GetAt(13.0).RiskLevel);

            // 从 t=14 起越过 1.10 nm：t=14 (累计1s), t=15 (累计2s) 仍为 Warning；t=16 (累计3s) 降级为 Safe
            Assert.Equal(RiskLevel.Warning, service.GetAt(14.0).RiskLevel);
            Assert.Equal(RiskLevel.Warning, service.GetAt(15.0).RiskLevel);
            Assert.Equal(RiskLevel.Safe, service.GetAt(16.0).RiskLevel);
            Assert.Equal(RiskLevel.Safe, service.GetAt(18.0).RiskLevel);
        }

        [Fact]
        public void TrackSampleDelegateAndMarkers_WorkWithICpaServiceContract()
        {
            double mps10Kn = 10.0 * CpaCalculator.MetersPerSecondPerKnot;
            Func<double, TrackSample> ownTrackSampler = t => new TrackSample(
                new SimTime(t), new GeoCoord(113.7, 21.78),
                new EnuPosition(0.0, t * mps10Kn), new Double2(0.0, mps10Kn),
                (float)mps10Kn, 0f, 0f, 0f, SampleProvenance.Interpolated, TimeQuality.ExactTagBlock, false);

            Func<double, TrackSample> targetTrackSampler = t => new TrackSample(
                new SimTime(t), new GeoCoord(113.71, 21.79),
                new EnuPosition(200.0, (120.0 - t) * mps10Kn), new Double2(0.0, -mps10Kn),
                (float)mps10Kn, 180f, 180f, 0f, SampleProvenance.Interpolated, TimeQuality.ExactTagBlock, false);

            CpaService service = new CpaService(
                ownTrackSampler, targetTrackSampler, 0.0, 120.0, 1.0,
                RiskThresholds.Default, "Lily", "Mary");

            service.EvaluateTime(new SimTime(60.0), new SimTime(59.0), false);
            CpaResult? current = service.GetCurrentPairResult("Lily", "Mary");
            Assert.True(current.HasValue);
            Assert.Equal(60.0, service.GetMinDistanceTime().Seconds, 6);
            Assert.Equal(200.0, service.GetMinDistanceSample().CurrentDistanceM, 6);
            Assert.NotEmpty(service.GetMarkers());
        }
    }
}
