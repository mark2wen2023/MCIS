using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Environment
{
    public interface IWeatherBackend
    {
        void ApplyWeather(EnvironmentState state, GeoCoord referenceGeo, DateTimeOffset currentUtc, bool immediate);
        void SetClearVisibilityOverride(bool clearOverride);
    }

    public interface IWaterBackend
    {
        void ApplyWater(EnvironmentState state, double seaLevelOffsetM, bool immediate);
        /// <summary>纯接口占位：引擎适配器返回世界坐标处的水面高度；本纯逻辑实现不采样三维世界。</summary>
        float SampleWaterHeightAt(double worldX, double worldY, double worldZ);
    }

    public interface IEnvironmentBridge : ITimeDriven
    {
        EnvironmentState CurrentState { get; }
        bool IsEvidenceClearMode { get; }

        void SetKeyframes(IReadOnlyList<EnvironmentState> keyframes);
        EnvironmentState SampleAt(SimTime time);
        void ApplyImmediate(EnvironmentState state);
        void SetEvidenceClearMode(bool enabled);

        void RegisterWeatherBackend(IWeatherBackend backend);
        void RegisterWaterBackend(IWaterBackend backend);
    }

    /// <summary>环境关键帧线性/最短角插值，并通过后端适配器驱动天气与水面（纯逻辑核心）。</summary>
    public sealed class EnvironmentBridge : IEnvironmentBridge
    {
        private readonly List<EnvironmentState> _keys = new List<EnvironmentState>();
        private readonly List<IWeatherBackend> _weather = new List<IWeatherBackend>();
        private readonly List<IWaterBackend> _water = new List<IWaterBackend>();
        private EnvironmentState _current;
        private GeoCoord _reference;
        private DateTimeOffset _epoch;
        private double _seaLevelOffsetM;

        public int ExecutionPriority { get { return 10; } }
        public EnvironmentState CurrentState { get { return _current; } }
        public bool IsEvidenceClearMode { get; private set; }

        public EnvironmentBridge(GeoCoord reference, DateTimeOffset caseEpochUtc, double seaLevelOffsetM = 0.0)
        {
            _reference = reference;
            _epoch = caseEpochUtc;
            _seaLevelOffsetM = seaLevelOffsetM;
            _current = DefaultClear(SimTime.Zero);
        }

        public void SetKeyframes(IReadOnlyList<EnvironmentState> keyframes)
        {
            _keys.Clear();
            if (keyframes != null)
            {
                _keys.AddRange(keyframes);
                _keys.Sort((a, b) => a.Time.CompareTo(b.Time));
            }

            if (_keys.Count > 0)
            {
                _current = SampleAt(_keys[0].Time);
            }
        }

        public EnvironmentState SampleAt(SimTime time)
        {
            if (_keys.Count == 0)
            {
                return DefaultClear(time);
            }

            if (time <= _keys[0].Time)
            {
                return WithTime(_keys[0], time);
            }

            if (time >= _keys[_keys.Count - 1].Time)
            {
                return WithTime(_keys[_keys.Count - 1], time);
            }

            int i = 0;
            while (i < _keys.Count - 1 && _keys[i + 1].Time < time)
            {
                i++;
            }

            EnvironmentState a = _keys[i];
            EnvironmentState b = _keys[i + 1];
            double span = b.Time.Seconds - a.Time.Seconds;
            double s = span > 1e-9 ? (time.Seconds - a.Time.Seconds) / span : 0.0;
            return Lerp(a, b, s, time);
        }

        public void ApplyImmediate(EnvironmentState state)
        {
            _current = state;
            PushToBackends(state, true);
        }

        public void SetEvidenceClearMode(bool enabled)
        {
            IsEvidenceClearMode = enabled;
            for (int i = 0; i < _weather.Count; i++)
            {
                _weather[i].SetClearVisibilityOverride(enabled);
            }
        }

        public void RegisterWeatherBackend(IWeatherBackend backend)
        {
            if (backend != null)
            {
                _weather.Add(backend);
            }
        }

        public void RegisterWaterBackend(IWaterBackend backend)
        {
            if (backend != null)
            {
                _water.Add(backend);
            }
        }

        public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            _current = SampleAt(currentTime);
            PushToBackends(_current, isSeek);
        }

        private void PushToBackends(EnvironmentState state, bool immediate)
        {
            EnvironmentState applied = IsEvidenceClearMode
                ? new EnvironmentState(
                    state.Time, state.WeatherPresetId, 10.0f, 0f, state.CloudCoverNormalized,
                    state.WindSpeedMps, state.WindFromDirDeg, state.WaveSignificantHeightM,
                    state.WavePeakPeriodSec, state.WaveFromDirDeg, state.CurrentSpeedKn,
                    state.CurrentToDirDeg, state.TideHeightM)
                : state;

            DateTimeOffset utc = applied.Time.ToUtc(_epoch);
            for (int i = 0; i < _weather.Count; i++)
            {
                _weather[i].ApplyWeather(applied, _reference, utc, immediate);
            }

            for (int i = 0; i < _water.Count; i++)
            {
                _water[i].ApplyWater(applied, _seaLevelOffsetM, immediate);
            }
        }

        internal static EnvironmentState Lerp(EnvironmentState a, EnvironmentState b, double s, SimTime time)
        {
            s = Math.Max(0.0, Math.Min(1.0, s));
            return new EnvironmentState(
                time,
                s < 0.5 ? a.WeatherPresetId : b.WeatherPresetId,
                (float)Linear(a.VisibilityNm, b.VisibilityNm, s),
                (float)Linear(a.RainIntensityMmPerHr, b.RainIntensityMmPerHr, s),
                (float)Linear(a.CloudCoverNormalized, b.CloudCoverNormalized, s),
                (float)Linear(a.WindSpeedMps, b.WindSpeedMps, s),
                (float)HermiteMath.InterpolateAngleDeg(a.WindFromDirDeg, b.WindFromDirDeg, s),
                (float)Linear(a.WaveSignificantHeightM, b.WaveSignificantHeightM, s),
                (float)Linear(a.WavePeakPeriodSec, b.WavePeakPeriodSec, s),
                (float)HermiteMath.InterpolateAngleDeg(a.WaveFromDirDeg, b.WaveFromDirDeg, s),
                (float)Linear(a.CurrentSpeedKn, b.CurrentSpeedKn, s),
                (float)HermiteMath.InterpolateAngleDeg(a.CurrentToDirDeg, b.CurrentToDirDeg, s),
                (float)Linear(a.TideHeightM, b.TideHeightM, s));
        }

        private static EnvironmentState WithTime(EnvironmentState s, SimTime t)
        {
            return new EnvironmentState(
                t, s.WeatherPresetId, s.VisibilityNm, s.RainIntensityMmPerHr, s.CloudCoverNormalized,
                s.WindSpeedMps, s.WindFromDirDeg, s.WaveSignificantHeightM, s.WavePeakPeriodSec,
                s.WaveFromDirDeg, s.CurrentSpeedKn, s.CurrentToDirDeg, s.TideHeightM);
        }

        public static EnvironmentState DefaultClear(SimTime time)
        {
            return new EnvironmentState(time, "Clear", 10f, 0f, 0.1f, 0f, 0f, 0.2f, 4f, 0f, 0f, 0f, 0f);
        }

        private static double Linear(double a, double b, double s)
        {
            return a + (b - a) * s;
        }
    }
}
