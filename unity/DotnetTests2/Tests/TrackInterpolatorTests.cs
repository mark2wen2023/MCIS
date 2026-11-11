using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Xunit;

namespace Mcis.Pure.Tests
{
    /// <summary>
    /// TrackInterpolator、ShipTrack 与 TrackTimeAligner 单元测试（Hermite 节点精确通过、匀速直线误差 &lt; 0.5m、转向平滑、有限差分回退、缺口外推与双船时间对齐）。
    /// </summary>
    public sealed class TrackInterpolatorTests
    {
        private static readonly GeoCoord Origin = new GeoCoord(113.7050, 22.2600, 0.0);

        private static TrackSample MakeSample(
            double timeSec,
            double eastM,
            double northM,
            float sogMps,
            float cogDeg,
            float hdgDeg)
        {
            EnuPosition enu = new EnuPosition(eastM, northM, 0.0);
            GeoCoord geo = GeoMath.EnuToWgs84(enu, Origin);
            Double2 vel = !float.IsNaN(cogDeg) && !float.IsNaN(sogMps)
                ? HermiteMath.VelocityFromSogCog(sogMps, cogDeg)
                : Double2.Zero;
            return new TrackSample(
                new SimTime(timeSec), geo, enu, vel, sogMps, cogDeg, hdgDeg, 0.0f,
                SampleProvenance.Measured, TimeQuality.ExactTagBlock, false, null);
        }

        [Fact]
        public void Hermite_PassesExactlyThroughNodes_AndUniformLinearTrackErrorBelowHalfMeter()
        {
            double speedMps = 6.0; // ~11.66 kn
            double cogDeg = 35.0;
            Double2 v = HermiteMath.VelocityFromSogCog(speedMps, cogDeg);

            List<TrackSample> waypoints = new List<TrackSample>();
            for (int i = 0; i <= 5; i++)
            {
                double t = i * 10.0;
                waypoints.Add(MakeSample(t, v.X * t, v.Y * t, (float)speedMps, (float)cogDeg, (float)cogDeg));
            }

            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack track = interpolator.BuildFromDrawnWaypoints(
                "vessel_linear", waypoints, InterpolationMode.CubicHermite, 60.0, GapPolicy.ConnectDashed, new LocalEnuGeoConverter(Origin));

            // 1. 节点精确通过
            for (int i = 0; i < waypoints.Count; i++)
            {
                TrackSample atNode = track.SampleAt(waypoints[i].Time);
                Assert.Equal(SampleProvenance.Measured, atNode.Provenance);
                Assert.True(atNode.EnuCenter.HorizontalDistanceTo(waypoints[i].EnuCenter) < 1e-9);
            }

            // 2. 任意中间时刻匀速直线航迹插值误差 < 0.5m（实际远小于 1mm）
            double[] testTimes = { 2.3, 7.5, 14.8, 25.0, 38.9, 46.1 };
            foreach (double t in testTimes)
            {
                TrackSample sampled = track.SampleAt(new SimTime(t));
                EnuPosition expected = new EnuPosition(v.X * t, v.Y * t, 0.0);
                double errorM = sampled.EnuCenter.HorizontalDistanceTo(expected);
                Assert.True(errorM < 0.5, $"Linear track interpolation error {errorM}m >= 0.5m at t={t}s");
                Assert.True(errorM < 1e-6);
                Assert.Equal(speedMps, sampled.SogMps, 4);
                Assert.Equal(cogDeg, sampled.CogDeg, 3);
            }
        }

        [Fact]
        public void Hermite_TurningTrack_SmoothArcAndShortestAngleAcrossNorth()
        {
            // 等速圆周转向：半径 R = 500m，线速度 v = 5 m/s，角速度 ω = 0.01 rad/s
            // t=0 时位于 (-500, 0) 朝北 (COG=0°)，顺时针转向东
            double radius = 500.0;
            double speed = 5.0;
            double omega = speed / radius;
            List<TrackSample> samples = new List<TrackSample>();

            for (int i = 0; i <= 6; i++)
            {
                double t = i * 10.0;
                double theta = omega * t; // 真北顺时针航向弧度
                double east = -radius * Math.Cos(theta);
                double north = radius * Math.Sin(theta);
                float cogDeg = (float)(theta * GeoMath.RadToDeg);
                float hdgDeg = i == 0 ? 355.0f : (float)HermiteMath.NormalizeAngleDeg(355.0 + i * 4.0);
                samples.Add(MakeSample(t, east, north, (float)speed, cogDeg, hdgDeg));
            }

            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack hermiteTrack = interpolator.BuildFromDrawnWaypoints("turn_h", samples, InterpolationMode.CubicHermite);
            IShipTrack linearTrack = interpolator.BuildFromDrawnWaypoints("turn_l", samples, InterpolationMode.Linear);

            // 在第 1 段中点 t=5s 比较 Hermite 与真实圆弧误差，并确认优于线性插值
            double midT = 5.0;
            double midTheta = omega * midT;
            EnuPosition exactArcMid = new EnuPosition(-radius * Math.Cos(midTheta), radius * Math.Sin(midTheta), 0.0);

            TrackSample hMid = hermiteTrack.SampleAt(new SimTime(midT));
            TrackSample lMid = linearTrack.SampleAt(new SimTime(midT));
            double hermiteErr = hMid.EnuCenter.HorizontalDistanceTo(exactArcMid);
            double linearErr = lMid.EnuCenter.HorizontalDistanceTo(exactArcMid);

            Assert.True(hermiteErr < 0.05);
            Assert.True(hermiteErr < linearErr * 0.1);
            // 验证跨越 360°/0° 的船首向最短角插值（355° -> 359° 中点为 357°，第 2 段 359° -> 3° 中点为 1°）
            TrackSample seg2Mid = hermiteTrack.SampleAt(new SimTime(15.0));
            Assert.Equal(1.0, seg2Mid.HdgDeg, 2);
        }

        [Fact]
        public void Hermite_WhenSogCogMissing_FallsBackToCatmullRomFiniteDifference()
        {
            List<TrackSample> waypoints = new List<TrackSample>
            {
                MakeSample(0.0, 0.0, 0.0, float.NaN, float.NaN, 0.0f),
                MakeSample(10.0, 0.0, 60.0, float.NaN, float.NaN, 0.0f),
                MakeSample(20.0, 0.0, 120.0, float.NaN, float.NaN, 0.0f)
            };

            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack track = interpolator.BuildFromDrawnWaypoints("catmull", waypoints, InterpolationMode.CubicHermite);

            TrackSample mid = track.SampleAt(new SimTime(10.0));
            TrackSample quarter = track.SampleAt(new SimTime(5.0));
            Assert.Equal(60.0, mid.EnuCenter.NorthM, 5);
            Assert.Equal(30.0, quarter.EnuCenter.NorthM, 5);
            Assert.Equal(6.0, quarter.SogMps, 3);
        }

        [Fact]
        public void GapDetection_AndExtrapolationPolicies_BehaveAsConfigured()
        {
            List<TrackSample> waypoints = new List<TrackSample>
            {
                MakeSample(0.0, 0.0, 0.0, 5.0f, 90.0f, 90.0f),
                MakeSample(10.0, 50.0, 0.0, 5.0f, 90.0f, 90.0f),
                MakeSample(130.0, 650.0, 0.0, 5.0f, 90.0f, 90.0f) // 120s > 60s gap
            };

            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack dashedTrack = interpolator.BuildFromDrawnWaypoints(
                "dashed", waypoints, InterpolationMode.CubicHermite, 60.0, GapPolicy.ConnectDashed);
            IShipTrack drTrack = interpolator.BuildFromDrawnWaypoints(
                "dr", waypoints, InterpolationMode.CubicHermite, 60.0, GapPolicy.DeadReckon);
            IShipTrack hiddenTrack = interpolator.BuildFromDrawnWaypoints(
                "hide", waypoints, InterpolationMode.CubicHermite, 60.0, GapPolicy.HideVessel);

            Assert.Single(dashedTrack.TimeGaps);
            Assert.Equal(120.0, dashedTrack.TimeGaps[0].DurationSeconds, 5);

            SimTime inGapTime = new SimTime(70.0);
            TimeGapSpan gap;
            Assert.True(dashedTrack.IsInTimeGap(inGapTime, out gap));

            TrackSample dashedSample = dashedTrack.SampleAt(inGapTime);
            Assert.Equal(SampleProvenance.LowConfidence, dashedSample.Provenance);
            Assert.True(dashedSample.IsInterpolatedAcrossGap);

            TrackSample drSample = drTrack.SampleAt(inGapTime);
            Assert.Equal(SampleProvenance.DeadReckoned, drSample.Provenance);
            Assert.True(drSample.IsInterpolatedAcrossGap);
            Assert.Equal(350.0, drSample.EnuCenter.EastM, 3);

            TrackSample hiddenSample;
            Assert.False(hiddenTrack.TrySampleAt(inGapTime, out hiddenSample));
            Assert.Equal(SampleProvenance.Rejected, hiddenSample.Provenance);

            // 边界外拒绝外推
            TrackSample beforeStart;
            Assert.False(dashedTrack.TrySampleAt(new SimTime(-5.0), out beforeStart));
            Assert.Equal(SampleProvenance.Rejected, beforeStart.Provenance);
        }

        [Fact]
        public void AlignTwoTracks_ResamplesOntoUnifiedOverlapTimeline()
        {
            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack trackA = interpolator.BuildFromDrawnWaypoints("vessel_a", new List<TrackSample>
            {
                MakeSample(0.0, 0.0, 0.0, 5.0f, 0.0f, 0.0f),
                MakeSample(30.0, 0.0, 150.0, 5.0f, 0.0f, 0.0f)
            }, InterpolationMode.CubicHermite);

            IShipTrack trackB = interpolator.BuildFromDrawnWaypoints("vessel_b", new List<TrackSample>
            {
                MakeSample(10.0, 100.0, 0.0, 4.0f, 270.0f, 270.0f),
                MakeSample(40.0, -20.0, 0.0, 4.0f, 270.0f, 270.0f)
            }, InterpolationMode.CubicHermite);

            AlignedTrackResult aligned = TrackTimeAligner.AlignTwoTracks(trackA, trackB, 5.0, true);
            Assert.True(aligned.HasValidOverlap);
            Assert.Equal(10.0, aligned.StartTime.Seconds, 6);
            Assert.Equal(30.0, aligned.EndTime.Seconds, 6);
            Assert.Equal(5, aligned.Pairs.Count); // 10, 15, 20, 25, 30
            Assert.Equal(100.0, aligned.Pairs[2].First.EnuCenter.NorthM, 3); // t=20s -> North=100m
            Assert.Equal(60.0, aligned.Pairs[2].Second.EnuCenter.EastM, 3);  // t=20s -> East=100 - 4*10 = 60m
        }

        [Fact]
        public void BuildFromAisRecords_CleansOutliersAndInterpolatesSmoothly()
        {
            DateTimeOffset epoch = new DateTimeOffset(2026, 5, 18, 10, 0, 0, TimeSpan.Zero);
            double vMps = 10.0 * HermiteMath.MetersPerSecondPerKnot;
            GeoCoord p0 = Origin;
            GeoCoord p1 = GeoMath.EnuToWgs84(new EnuPosition(0.0, vMps * 10.0, 0.0), Origin);
            GeoCoord pJump = GeoMath.EnuToWgs84(new EnuPosition(3000.0, vMps * 15.0, 0.0), Origin);
            GeoCoord p2 = GeoMath.EnuToWgs84(new EnuPosition(0.0, vMps * 20.0, 0.0), Origin);

            List<AisDecodedRecord> records = new List<AisDecodedRecord>
            {
                new AisDecodedRecord(1, "!AIVDM", 1, "413990101", epoch, TimeQuality.ExactTagBlock, p0.LonDeg, p0.LatDeg, 10.0f, 0.0f, 511.0f, 0.0f, 0),
                new AisDecodedRecord(2, "!AIVDM", 1, "413990101", epoch.AddSeconds(10), TimeQuality.ExactTagBlock, p1.LonDeg, p1.LatDeg, 10.0f, 0.0f, 511.0f, 0.0f, 0),
                new AisDecodedRecord(3, "!AIVDM", 1, "413990101", epoch.AddSeconds(15), TimeQuality.ExactTagBlock, pJump.LonDeg, pJump.LatDeg, 10.0f, 0.0f, 511.0f, 0.0f, 0),
                new AisDecodedRecord(4, "!AIVDM", 1, "413990101", epoch.AddSeconds(20), TimeQuality.ExactTagBlock, p2.LonDeg, p2.LatDeg, 10.0f, 0.0f, 511.0f, 0.0f, 0)
            };

            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack track = interpolator.BuildFromAisRecords(
                "vessel_ais", records, AntennaOffset.Zero, epoch, new LocalEnuGeoConverter(Origin), TrackCleaningConfig.CreateDefault());

            Assert.Equal(3, track.CleanedSamples.Count);
            Assert.Single(track.RejectedSamples);
            Assert.Equal(RejectReason.PositionJump, track.RejectedSamples[0].Reason);

            TrackSample at15 = track.SampleAt(new SimTime(15.0));
            Assert.Equal(vMps * 15.0, at15.EnuCenter.NorthM, 2);
            Assert.True(at15.HeadingFromCog);
        }
    }
}
