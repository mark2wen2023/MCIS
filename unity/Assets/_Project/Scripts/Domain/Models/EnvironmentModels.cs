using Mcis.Core;

namespace Mcis.Domain.Models
{
    /// <summary>环境与水文气象状态（物理量，与插件解耦，对应 ARCHITECTURE 4.7 节）。</summary>
    public readonly struct EnvironmentState
    {
        public SimTime Time { get; }
        public string WeatherPresetId { get; }
        public float VisibilityNm { get; }
        public float RainIntensityMmPerHr { get; }
        public float CloudCoverNormalized { get; }
        public float WindSpeedMps { get; }
        public float WindFromDirDeg { get; }
        public float WaveSignificantHeightM { get; }
        public float WavePeakPeriodSec { get; }
        public float WaveFromDirDeg { get; }
        public float CurrentSpeedKn { get; }
        public float CurrentToDirDeg { get; }
        public float TideHeightM { get; }

        public EnvironmentState(
            SimTime time,
            string weatherPresetId,
            float visibilityNm,
            float rainIntensityMmPerHr,
            float cloudCoverNormalized,
            float windSpeedMps,
            float windFromDirDeg,
            float waveSignificantHeightM,
            float wavePeakPeriodSec,
            float waveFromDirDeg,
            float currentSpeedKn,
            float currentToDirDeg,
            float tideHeightM)
        {
            Time = time;
            WeatherPresetId = weatherPresetId ?? "Clear";
            VisibilityNm = visibilityNm;
            RainIntensityMmPerHr = rainIntensityMmPerHr;
            CloudCoverNormalized = cloudCoverNormalized;
            WindSpeedMps = windSpeedMps;
            WindFromDirDeg = windFromDirDeg;
            WaveSignificantHeightM = waveSignificantHeightM;
            WavePeakPeriodSec = wavePeakPeriodSec;
            WaveFromDirDeg = waveFromDirDeg;
            CurrentSpeedKn = currentSpeedKn;
            CurrentToDirDeg = currentToDirDeg;
            TideHeightM = tideHeightM;
        }
    }
}
