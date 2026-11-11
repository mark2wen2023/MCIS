using System;
using Mcis.Core;
using Mcis.Domain.Models;
using Mcis.Fixtures;
using Mcis.Simulation.Environment;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class EnvironmentBridgeTests
    {
        [Fact]
        public void SampleAt_InterpolatesVisibilityAndShortestAngle()
        {
            var bridge = new EnvironmentBridge(LilyMaryDemo.Origin, LilyMaryDemo.CaseEpochUtc);
            var a = new EnvironmentState(SimTime.Zero, "Clear", 10f, 0f, 0f, 0f, 10f, 0.2f, 4f, 10f, 0f, 350f, 0f);
            var b = new EnvironmentState(new SimTime(100), "HeavyFog", 2f, 4f, 1f, 8f, 50f, 0.8f, 5f, 50f, 2f, 20f, 1f);
            bridge.SetKeyframes(new[] { a, b });
            var mid = bridge.SampleAt(new SimTime(50));
            Assert.InRange(mid.VisibilityNm, 5.9f, 6.1f);
            // 350° → 20° 最短弧为 +30°，中点应为 5°（或 365→5）
            Assert.InRange(mid.CurrentToDirDeg, 4.0f, 6.0f);
        }

        private sealed class FakeWeather : IWeatherBackend
        {
            public int Applies;
            public bool? Clear;
            public void ApplyWeather(EnvironmentState state, Mcis.Domain.Common.GeoCoord referenceGeo, DateTimeOffset currentUtc, bool immediate)
            {
                Applies++;
            }
            public void SetClearVisibilityOverride(bool clearOverride) { Clear = clearOverride; }
        }

        [Fact]
        public void EvidenceClearMode_NotifiesBackend()
        {
            var bridge = new EnvironmentBridge(LilyMaryDemo.Origin, LilyMaryDemo.CaseEpochUtc);
            var w = new FakeWeather();
            bridge.RegisterWeatherBackend(w);
            bridge.SetEvidenceClearMode(true);
            Assert.True(w.Clear.HasValue && w.Clear.Value);
            bridge.EvaluateTime(new SimTime(1), SimTime.Zero, true);
            Assert.True(w.Applies > 0);
        }
    }
}
