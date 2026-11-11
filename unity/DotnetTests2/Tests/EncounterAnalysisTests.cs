using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Fixtures;
using Mcis.Simulation.Analysis;
using Mcis.Simulation.Cpa;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class EncounterAnalysisTests
    {
        [Fact]
        public void Analyzer_ExtractsFirstWarningDanger_MinDistance_AndCollision()
        {
            var geo = LilyMaryDemo.CreateGeo();
            var lily = LilyMaryDemo.BuildLilyTrack(geo);
            var mary = LilyMaryDemo.BuildMaryTrack(geo);
            var cpa = new CpaService(lily, mary, 1.0, RiskThresholds.Default);
            var series = cpa.PrecomputeSeries(LilyMaryDemo.LilyId, LilyMaryDemo.MaryId, 1.0);
            Assert.True(series.Samples.Count > 10);

            var report = EncounterAnalyzer.Analyze(series, LilyMaryDemo.CollisionTime, new IShipTrack[] { lily, mary });
            Assert.True(report.MinDistance.HasValue);
            Assert.Equal("MinDistance", report.MinDistance.Value.Kind);
            Assert.True(report.Collision.HasValue);
            Assert.Equal(LilyMaryDemo.CollisionTime.Seconds, report.Collision.Value.Time.Seconds, 3);
            Assert.Equal(0, report.RejectedStats.TotalRejected);
            Assert.True(report.RejectedStats.TotalCleaned > 0);

            // 开头应处于安全，随后才转入警告、危险，最近距离不晚于 tc。
            Assert.Equal(RiskLevel.Safe, series.Samples[0].RiskLevel);
            Assert.True(series.Samples[0].DcpaNm >= 1.0 || series.Samples[0].TcpaMin >= 12.0);
            Assert.True(report.FirstWarning.HasValue, "应出现首次警告");
            Assert.True(report.FirstDanger.HasValue, "应出现首次危险");
            Assert.InRange(report.FirstWarning.Value.Time.Seconds, 120.0, 400.0);
            Assert.True(report.FirstDanger.Value.Time.Seconds > report.FirstWarning.Value.Time.Seconds + 30.0);
            Assert.True(report.FirstDanger.Value.Time.Seconds < LilyMaryDemo.CollisionTime.Seconds);
            Assert.True(report.MinDistance.Value.Time.Seconds <= LilyMaryDemo.CollisionTime.Seconds + 1.0);
        }

        [Fact]
        public void RejectedStatistics_GroupsByReason_AndCountsRestored()
        {
            var rejected = new[]
            {
                new RejectedSample(1, SimTime.Zero, default, 0f, 0f, RejectReason.SpeedGate, "快", false),
                new RejectedSample(2, new SimTime(1), default, 0f, 0f, RejectReason.SpeedGate, "快", true),
                new RejectedSample(3, new SimTime(2), default, 0f, 0f, RejectReason.Hampel, "离群", false)
            };
            var track = new ShipTrack("x", new TrackSample[] { }, rejected, new TimeGapSpan[] { }, InterpolationMode.Linear, GapPolicy.ConnectDashed, null);
            var stats = RejectedPointStatistics.FromTracks(new IShipTrack[] { track });
            Assert.Equal(3, stats.TotalRejected);
            Assert.Equal(1, stats.ManuallyRestored);
            Assert.Contains(stats.ByReason, r => r.Reason == RejectReason.SpeedGate && r.Count == 2);
        }
    }
}
