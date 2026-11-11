using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Cpa
{
    public sealed partial class CpaService
    {
        /// <summary>
        /// 配置两船采样委托并立即按固定步长正向预计算全时段 CPA 序列。
        /// </summary>
        public CpaTimeSeries ConfigurePair(
            Func<double, VesselMotionState> ownSampler,
            Func<double, VesselMotionState> targetSampler,
            double startTimeSeconds,
            double endTimeSeconds,
            double stepSeconds = 1.0,
            string ownVesselId = "Own",
            string targetVesselId = "Target")
        {
            if (ownSampler == null) throw new ArgumentNullException(nameof(ownSampler));
            if (targetSampler == null) throw new ArgumentNullException(nameof(targetSampler));

            string ownId = string.IsNullOrEmpty(ownVesselId) ? "Own" : ownVesselId;
            string targetId = string.IsNullOrEmpty(targetVesselId) ? "Target" : targetVesselId;
            _defaultStepSeconds = stepSeconds > 0.0 ? stepSeconds : 1.0;

            SimTime start = new SimTime(Math.Min(startTimeSeconds, endTimeSeconds));
            SimTime end = new SimTime(Math.Max(startTimeSeconds, endTimeSeconds));

            RegisterVesselSampler(ownId, ownSampler, start, end);
            RegisterVesselSampler(targetId, targetSampler, start, end);
            _ownVesselId = ownId;
            _primaryTargetVesselId = targetId;

            return PrecomputeSeries(ownId, targetId, _defaultStepSeconds);
        }

        /// <summary>注册基于委托的单船运动状态采样器。</summary>
        public void RegisterVesselSampler(
            string vesselId,
            Func<double, VesselMotionState> sampler,
            SimTime startTime,
            SimTime endTime)
        {
            if (string.IsNullOrEmpty(vesselId)) throw new ArgumentNullException(nameof(vesselId));
            if (sampler == null) throw new ArgumentNullException(nameof(sampler));

            if (!_vessels.ContainsKey(vesselId))
            {
                _vesselOrder.Add(vesselId);
            }

            _vessels[vesselId] = new VesselEntry(vesselId, startTime, endTime, sampler, null);
            EnsureDefaultPairIds(vesselId);
        }

        /// <summary>注册单船航迹 IShipTrack。</summary>
        public void RegisterTrack(IShipTrack track)
        {
            if (track == null) throw new ArgumentNullException(nameof(track));
            string vesselId = track.VesselId;
            if (!_vessels.ContainsKey(vesselId))
            {
                _vesselOrder.Add(vesselId);
            }

            Func<double, VesselMotionState> sampler = t =>
                VesselMotionState.FromTrackSample(track.SampleAt(new SimTime(t)), _useRawSogCog);

            _vessels[vesselId] = new VesselEntry(vesselId, track.StartTime, track.EndTime, sampler, track);
            EnsureDefaultPairIds(vesselId);
        }

        private void EnsureDefaultPairIds(string newlyAddedId)
        {
            if (string.IsNullOrEmpty(_ownVesselId))
            {
                _ownVesselId = newlyAddedId;
            }
            else if (string.IsNullOrEmpty(_primaryTargetVesselId) &&
                     !string.Equals(_ownVesselId, newlyAddedId, StringComparison.Ordinal))
            {
                _primaryTargetVesselId = newlyAddedId;
            }
        }

        /// <inheritdoc />
        public void SetOwnVessel(string vesselId)
        {
            if (string.IsNullOrEmpty(vesselId)) return;
            _ownVesselId = vesselId;
            if (string.Equals(_primaryTargetVesselId, vesselId, StringComparison.Ordinal))
            {
                _primaryTargetVesselId = null;
                for (int i = 0; i < _vesselOrder.Count; i++)
                {
                    if (!string.Equals(_vesselOrder[i], vesselId, StringComparison.Ordinal))
                    {
                        _primaryTargetVesselId = _vesselOrder[i];
                        break;
                    }
                }
            }
        }

        /// <inheritdoc />
        public void SetThresholds(RiskThresholds thresholds)
        {
            _thresholds = thresholds;
            RebuildAllCachedSeries();
        }

        /// <inheritdoc />
        public CpaResult GetAt(double timeSeconds)
        {
            return GetAt(new SimTime(timeSeconds));
        }

        /// <inheritdoc />
        public CpaResult GetAt(SimTime time)
        {
            CpaTimeSeries series = PrimarySeries;
            if (series == null)
            {
                return default;
            }
            return series.GetAt(time);
        }

        /// <summary>查询指定两船在任意仿真时间的 CPA 结果。</summary>
        public CpaResult GetAt(string ownVesselId, string targetVesselId, SimTime time)
        {
            CpaTimeSeries series = GetOrBuildSeries(ownVesselId, targetVesselId, _defaultStepSeconds);
            return series != null ? series.GetAt(time) : default;
        }

        /// <inheritdoc />
        public CpaResult GetMinDistanceSample()
        {
            CpaTimeSeries series = PrimarySeries;
            return series != null ? series.MinDistanceSample : default;
        }

        /// <inheritdoc />
        public SimTime GetMinDistanceTime()
        {
            CpaTimeSeries series = PrimarySeries;
            return series != null ? series.MinDistanceTime : SimTime.Zero;
        }

        /// <summary>获取主配对在全时段内的最小预测 DCPA 样本。</summary>
        public CpaResult GetMinDcpaSample()
        {
            CpaTimeSeries series = PrimarySeries;
            return series != null ? series.MinDcpaSample : default;
        }

        /// <inheritdoc />
        public CpaResult? GetCurrentPairResult(string ownVesselId, string targetVesselId)
        {
            CpaTimeSeries series = GetOrBuildSeries(ownVesselId, targetVesselId, _defaultStepSeconds);
            return series != null ? series.GetAt(_currentTime) : (CpaResult?)null;
        }

        /// <inheritdoc />
        public IReadOnlyList<CpaResult> GetCurrentResultsForOwnVessel()
        {
            if (string.IsNullOrEmpty(_ownVesselId))
            {
                return Array.Empty<CpaResult>();
            }

            List<CpaResult> list = new List<CpaResult>();
            for (int i = 0; i < _vesselOrder.Count; i++)
            {
                string targetId = _vesselOrder[i];
                if (string.Equals(targetId, _ownVesselId, StringComparison.Ordinal))
                {
                    continue;
                }
                CpaTimeSeries series = GetOrBuildSeries(_ownVesselId, targetId, _defaultStepSeconds);
                if (series != null)
                {
                    list.Add(series.GetAt(_currentTime));
                }
            }
            return list;
        }

        /// <inheritdoc />
        public IReadOnlyList<CpaResult> GetAllActivePairsAt(SimTime time)
        {
            List<CpaResult> list = new List<CpaResult>();
            for (int i = 0; i < _vesselOrder.Count; i++)
            {
                for (int j = i + 1; j < _vesselOrder.Count; j++)
                {
                    string ownId = _vesselOrder[i];
                    string targetId = _vesselOrder[j];
                    CpaTimeSeries series = GetOrBuildSeries(ownId, targetId, _defaultStepSeconds);
                    if (series != null)
                    {
                        list.Add(series.GetAt(time));
                    }
                }
            }
            return list;
        }
    }
}
