using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Tracks;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class ManualDrawnTrackTests
    {
        [Fact]
        public void AllocateTime_BySpeed_OneNauticalMileAtTenKnots_TakesSixMinutes()
        {
            var origin = new GeoCoord(113.705, 22.260, 0.0);
            var geo = new LocalEnuGeoConverter(origin, 0.0);
            // 沿北向 1 海里 = 1852 m
            var start = new EnuPosition(0, 0, 0);
            var end = new EnuPosition(0, 1852.0, 0);
            var wps = new[]
            {
                new ManualDrawnWaypoint(start, null, 10f, 0f),
                new ManualDrawnWaypoint(end, null, 10f, 0f)
            };
            var track = new ManualDrawnTrackBuilder().Build("drawn", wps, geo, InterpolationMode.CatmullRom, 10.0, 1.0, SimTime.Zero);
            Assert.InRange(track.EndTime.Seconds, 359.0, 361.0);
            var mid = track.SampleAt(new SimTime(180.0));
            Assert.Equal(SampleProvenance.ManualDrawn, mid.Provenance);
            Assert.InRange(mid.EnuCenter.NorthM, 900.0, 950.0);
            Assert.True(mid.SogMps > 4.0);
        }

        [Fact]
        public void ExplicitTimes_AreHonored_AndProvenanceIsManualDrawn()
        {
            var geo = new LocalEnuGeoConverter(new GeoCoord(113.7, 22.26, 0), 0);
            var wps = new[]
            {
                new ManualDrawnWaypoint(new EnuPosition(0, 0, 0), new SimTime(10), 8f, 90f),
                new ManualDrawnWaypoint(new EnuPosition(400, 0, 0), new SimTime(50), 8f, 90f)
            };
            var track = new ManualDrawnTrackBuilder().Build("v", wps, geo, InterpolationMode.CubicHermite, 8.0, 1.0, SimTime.Zero);
            Assert.Equal(10.0, track.StartTime.Seconds, 6);
            Assert.Equal(50.0, track.EndTime.Seconds, 6);
            foreach (var s in track.CleanedSamples)
            {
                Assert.Equal(SampleProvenance.ManualDrawn, s.Provenance);
            }
        }

        [Fact]
        public void LessThanTwoPoints_Throws()
        {
            var geo = new LocalEnuGeoConverter(new GeoCoord(0, 0, 0), 0);
            Assert.Throws<ArgumentException>(() =>
                new ManualDrawnTrackBuilder().Build("v", new[] { new ManualDrawnWaypoint(new EnuPosition(0, 0, 0)) }, geo));
        }
    }
}
