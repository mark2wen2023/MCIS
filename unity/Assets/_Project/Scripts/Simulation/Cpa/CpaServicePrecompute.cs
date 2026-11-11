using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Cpa
{
    public sealed partial class CpaService
    {
        /// <inheritdoc />
        public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            _currentTime = currentTime;
        }

        /// <inheritdoc />
        public IReadOnlyList<TimelineMarker> GetMarkers()
        {
            return _markers;
        }

        private CpaTimeSeries GetOrBuildSeries(string ownVesselId, string targetVesselId, double stepSeconds)
        {
            if (string.IsNullOrEmpty(ownVesselId) || string.IsNullOrEmpty(targetVesselId))
            {
                return null;
            }

            CpaPairKey key = new CpaPairKey(ownVesselId, targetVesselId);
            if (_seriesCache.TryGetValue(key, out CpaTimeSeries cached))
            {
                return cached;
            }

            if (!_vessels.ContainsKey(ownVesselId) || !_vessels.ContainsKey(targetVesselId))
            {
                return null;
            }

            return PrecomputeSeries(ownVesselId, targetVesselId, stepSeconds);
        }

        private void RebuildAllCachedSeries()
        {
            List<(string Own, string Target, double Step)> keys = new List<(string, string, double)>();
            foreach (KeyValuePair<CpaPairKey, CpaTimeSeries> kv in _seriesCache)
            {
                keys.Add((kv.Key.OwnVesselId, kv.Key.TargetVesselId, kv.Value.StepSeconds));
            }

            _seriesCache.Clear();
            _markers.Clear();

            for (int i = 0; i < keys.Count; i++)
            {
                PrecomputeSeries(keys[i].Own, keys[i].Target, keys[i].Step);
            }
        }

        /// <inheritdoc />
        public CpaTimeSeries PrecomputeSeries(string ownVesselId, string targetVesselId, double stepSeconds = 1.0)
        {
            if (!_vessels.TryGetValue(ownVesselId, out VesselEntry ownEntry))
            {
                throw new ArgumentException("未找到本船采样器: " + ownVesselId, nameof(ownVesselId));
            }
            if (!_vessels.TryGetValue(targetVesselId, out VesselEntry targetEntry))
            {
                throw new ArgumentException("未找到目标船采样器: " + targetVesselId, nameof(targetVesselId));
            }

            double step = stepSeconds > 0.0 ? stepSeconds : _defaultStepSeconds;
            double startSec = Math.Max(ownEntry.StartTime.Seconds, targetEntry.StartTime.Seconds);
            double endSec = Math.Min(ownEntry.EndTime.Seconds, targetEntry.EndTime.Seconds);
            if (endSec < startSec)
            {
                startSec = ownEntry.StartTime.Seconds;
                endSec = ownEntry.EndTime.Seconds;
            }

            CpaPairKey pair = new CpaPairKey(ownVesselId, targetVesselId);
            List<double> sampleTimes = BuildSampleTimestamps(startSec, endSec, step);
            List<CpaResult> samples = new List<CpaResult>(sampleTimes.Count);

            RiskLevel activeLevel = RiskLevel.Safe;
            double clearDangerTimerSec = 0.0;
            double clearWarningTimerSec = 0.0;

            CpaResult minDcpaSample = default;
            CpaResult minDistSample = default;
            bool hasMin = false;

            for (int i = 0; i < sampleTimes.Count; i++)
            {
                double tSec = sampleTimes[i];
                double dt = i == 0 ? 0.0 : (tSec - sampleTimes[i - 1]);
                SimTime simTime = new SimTime(tSec);

                VesselMotionState ownState = ownEntry.StateSampler(tSec);
                VesselMotionState targetState = targetEntry.StateSampler(tSec);

                CpaResult rawResult = CpaCalculator.CalculateFromStates(
                    ownState, targetState, pair, simTime, RiskLevel.Safe);

                RiskLevel instantRisk = CpaCalculator.EvaluateInstantRisk(
                    rawResult.DcpaNm, rawResult.TcpaMin, rawResult.IsDegenerate, _thresholds);

                if (i == 0)
                {
                    activeLevel = instantRisk;
                    clearDangerTimerSec = 0.0;
                    clearWarningTimerSec = 0.0;
                }
                else
                {
                    activeLevel = StepHysteresis(
                        activeLevel,
                        instantRisk,
                        rawResult.DcpaNm,
                        rawResult.TcpaMin,
                        rawResult.IsDegenerate,
                        dt,
                        _thresholds,
                        ref clearDangerTimerSec,
                        ref clearWarningTimerSec);
                }

                CpaResult finalSample = rawResult.WithRiskLevel(activeLevel);
                samples.Add(finalSample);

                if (!hasMin || finalSample.DcpaM < minDcpaSample.DcpaM)
                {
                    minDcpaSample = finalSample;
                }
                if (!hasMin || finalSample.CurrentDistanceM < minDistSample.CurrentDistanceM)
                {
                    minDistSample = finalSample;
                }
                hasMin = true;
            }

            List<(SimTime Start, SimTime End, RiskLevel Level)> intervals = BuildRiskIntervals(samples);
            CpaTimeSeries series = new CpaTimeSeries(pair, step, samples, minDcpaSample, minDistSample, intervals);
            _seriesCache[pair] = series;

            UpdateMarkersForSeries(series);
            return series;
        }

        private static List<double> BuildSampleTimestamps(double startSec, double endSec, double step)
        {
            List<double> times = new List<double>();
            double duration = Math.Max(0.0, endSec - startSec);
            int steps = (int)Math.Floor(duration / step + 1e-9);
            for (int i = 0; i <= steps; i++)
            {
                double t = startSec + i * step;
                if (t > endSec) t = endSec;
                times.Add(t);
            }
            if (times.Count == 0 || Math.Abs(times[times.Count - 1] - endSec) > 1e-7)
            {
                times.Add(endSec);
            }
            return times;
        }

        /// <summary>
        /// 滞回状态机单步更新（正向时间推进）：
        /// 1. 升级立即生效（instantRisk &gt; activeLevel 时立即跃迁并清零降级计时器）；
        /// 2. 降级需越过 阈值 × (1 + DowngradeMarginRatio) 并连续保持 HysteresisSeconds 秒。
        /// </summary>
        private static RiskLevel StepHysteresis(
            RiskLevel activeLevel,
            RiskLevel instantRisk,
            double dcpaNm,
            double tcpaMin,
            bool isDegenerate,
            double dtSeconds,
            RiskThresholds thresholds,
            ref double clearDangerTimerSec,
            ref double clearWarningTimerSec)
        {
            if (instantRisk > activeLevel)
            {
                clearDangerTimerSec = 0.0;
                clearWarningTimerSec = 0.0;
                return instantRisk;
            }

            double factor = 1.0 + Math.Max(0.0, thresholds.DowngradeMarginRatio);
            double dangerDcpaExit = thresholds.DangerDcpaNm * factor;
            double dangerTcpaExit = thresholds.DangerTcpaMin * factor;
            double warningDcpaExit = thresholds.WarningDcpaNm * factor;
            double warningTcpaExit = thresholds.WarningTcpaMin * factor;

            bool clearedDanger = isDegenerate || tcpaMin <= 0.0 ||
                                 dcpaNm >= dangerDcpaExit || tcpaMin >= dangerTcpaExit;
            bool clearedWarning = isDegenerate || tcpaMin <= 0.0 ||
                                  dcpaNm >= warningDcpaExit || tcpaMin >= warningTcpaExit;

            clearDangerTimerSec = clearedDanger ? (clearDangerTimerSec + dtSeconds) : 0.0;
            clearWarningTimerSec = clearedWarning ? (clearWarningTimerSec + dtSeconds) : 0.0;

            RiskLevel next = activeLevel;
            if (next == RiskLevel.Danger && clearDangerTimerSec + 1e-9 >= thresholds.HysteresisSeconds)
            {
                next = RiskLevel.Warning;
            }
            if (next == RiskLevel.Warning && clearWarningTimerSec + 1e-9 >= thresholds.HysteresisSeconds)
            {
                next = RiskLevel.Safe;
            }

            return next;
        }
    }
}
