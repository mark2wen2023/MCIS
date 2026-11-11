using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class TrackTests
    {
        [Fact]
        public void TimeRange_InvalidOrder_Throws()
        {
            Assert.Throws<ArgumentException>(() =>
                new TimeRange(new SimTime(10), new SimTime(5)));
        }

        [Fact]
        public void TimeRange_BasicOperations()
        {
            TimeRange range = new TimeRange(new SimTime(10), new SimTime(20));
            Assert.Equal(10.0, range.DurationSeconds, 9);
            Assert.True(range.Contains(new SimTime(10)));
            Assert.True(range.Contains(new SimTime(20)));
            Assert.False(range.Contains(new SimTime(20.1)));

            TimeRange other = new TimeRange(new SimTime(15), new SimTime(25));
            Assert.True(range.Overlaps(other));

            TimeRange intersection;
            Assert.True(range.Intersect(other, out intersection));
            Assert.Equal(15.0, intersection.Start.Seconds, 9);
            Assert.Equal(20.0, intersection.End.Seconds, 9);

            TimeRange staticIntersection;
            Assert.True(TimeRange.Intersect(range, other, out staticIntersection));
            Assert.Equal(15.0, staticIntersection.Start.Seconds, 9);

            TimeRange union = range.Union(other);
            Assert.Equal(10.0, union.Start.Seconds, 9);
            Assert.Equal(25.0, union.End.Seconds, 9);

            TimeRange shifted = range.Shift(3.5);
            Assert.Equal(13.5, shifted.Start.Seconds, 9);
            Assert.Equal(23.5, shifted.End.Seconds, 9);
        }

        [Fact]
        public void TimeRange_DisjointIntersect_ReturnsFalse()
        {
            TimeRange first = new TimeRange(new SimTime(0), new SimTime(1));
            TimeRange second = new TimeRange(new SimTime(2), new SimTime(3));
            TimeRange intersection;
            Assert.False(first.Intersect(second, out intersection));
        }


        [Fact]
        public void TrackKindInfo_ClassifiesKinds()
        {
            Assert.True(TrackKindInfo.IsAngular(TrackKind.CourseOverGround));
            Assert.True(TrackKindInfo.IsAngular(TrackKind.Heading));
            Assert.True(TrackKindInfo.IsAngular(TrackKind.TargetBearing));
            Assert.False(TrackKindInfo.IsAngular(TrackKind.RudderAngle));

            Assert.True(TrackKindInfo.IsStep(TrackKind.EngineTelegraph));
            Assert.False(TrackKindInfo.IsStep(TrackKind.SpeedOverGround));

            Assert.True(TrackKindInfo.IsMedia(TrackKind.Audio));
            Assert.True(TrackKindInfo.IsMedia(TrackKind.RadarImage));
            Assert.True(TrackKindInfo.IsMedia(TrackKind.EcdisImage));
            Assert.False(TrackKindInfo.IsMedia(TrackKind.Position));

            Assert.Equal("kn", TrackKindInfo.DefaultUnit(TrackKind.SpeedOverGround));
            Assert.Equal("°", TrackKindInfo.DefaultUnit(TrackKind.Heading));
            Assert.Equal("nm", TrackKindInfo.DefaultUnit(TrackKind.TargetRange));
        }

        [Fact]
        public void TargetPosition_IsPositionKind()
        {
            Track track = new Track(
                "A/TLL01/TargetPosition", "A", TrackKind.TargetPosition, string.Empty,
                new[] { TestHelpers.P(0, 122.0, 30.0), TestHelpers.P(10, 122.01, 30.01) });

            double value;
            Assert.False(track.TryGetValueAt(new SimTime(5), out value));

            GeoCoord position;
            Assert.True(track.TryGetPositionAt(new SimTime(5), out position));
            Assert.Equal(122.005, position.LonDeg, 9);
        }

        [Fact]
        public void Track_Scalar_LinearInterpolation()
        {
            Track track = TestHelpers.ScalarTrack(
                "A/SOG", "A", TrackKind.SpeedOverGround,
                TestHelpers.S(0, 10.0), TestHelpers.S(10, 20.0));

            double value;
            Assert.True(track.TryGetValueAt(new SimTime(5), out value));
            Assert.Equal(15.0, value, 9);
            Assert.True(track.TryGetValueAt(new SimTime(10), out value));
            Assert.Equal(20.0, value, 9);
            Assert.False(track.TryGetValueAt(new SimTime(-0.1), out value));
            Assert.False(track.TryGetValueAt(new SimTime(10.1), out value));
        }

        [Fact]
        public void Track_Angular_CrossesZeroByShortestArc()
        {
            Track track = TestHelpers.ScalarTrack(
                "A/HDG", "A", TrackKind.Heading,
                TestHelpers.S(0, 350.0), TestHelpers.S(10, 10.0));

            double value;
            Assert.True(track.TryGetValueAt(new SimTime(5), out value));
            Assert.Equal(0.0, value, 9);
            Assert.True(track.TryGetValueAt(new SimTime(2.5), out value));
            Assert.Equal(355.0, value, 9);

            Assert.Equal(20.0, AngleMath.AbsoluteDiff(350.0, 10.0), 9);
            Assert.Equal(0.0, AngleMath.Normalize360(360.0), 9);
            Assert.Equal(359.0, AngleMath.Normalize360(-1.0), 9);
        }

        [Fact]
        public void Track_Step_KeepsPreviousValueAndText()
        {
            Track track = TestHelpers.ScalarTrack(
                "A/Telegraph", "A", TrackKind.EngineTelegraph,
                TestHelpers.S(0, 0.0, "STOP"),
                TestHelpers.S(10, 4.0, "FULL AHEAD"),
                TestHelpers.S(20, -4.0, "FULL ASTERN"));

            double value;
            TimelineSample sample;
            Assert.True(track.TryGetValueAt(new SimTime(5), out value));
            Assert.Equal(0.0, value, 9);
            Assert.True(track.TryGetSampleAt(new SimTime(5), out sample));
            Assert.Equal("STOP", sample.Text);

            Assert.True(track.TryGetValueAt(new SimTime(15), out value));
            Assert.Equal(4.0, value, 9);
            Assert.True(track.TryGetSampleAt(new SimTime(15), out sample));
            Assert.Equal("FULL AHEAD", sample.Text);

            Assert.True(track.TryGetValueAt(new SimTime(20), out value));
            Assert.Equal(-4.0, value, 9);

            Assert.False(track.TryGetValueAt(new SimTime(20.5), out value));
            Assert.False(track.TryGetSampleAt(new SimTime(-0.5), out sample));
        }

        [Fact]
        public void Track_Position_InterpolatesAndScalarQueryFails()
        {
            Track track = TestHelpers.PositionTrack(
                "A/Position", "A",
                TestHelpers.P(0, 122.0, 30.0),
                TestHelpers.P(10, 122.01, 30.01));

            double value;
            Assert.False(track.TryGetValueAt(new SimTime(5), out value));

            GeoCoord position;
            Assert.True(track.TryGetPositionAt(new SimTime(5), out position));
            Assert.Equal(122.005, position.LonDeg, 9);
            Assert.Equal(30.005, position.LatDeg, 9);
            Assert.False(track.TryGetPositionAt(new SimTime(11), out position));

            TimelineSample sample;
            Assert.True(track.TryGetSampleAt(new SimTime(5), out sample));
            Assert.True(sample.HasPosition);
        }

        [Fact]
        public void Track_MarkersAndMedia_QueryByRange()
        {
            EventMarker early = new EventMarker("e1", new SimTime(2), "change", "a", "A", "A/X");
            EventMarker late = new EventMarker("e2", new SimTime(15), "change", "b", "A", "A/X");
            MediaItem media = new MediaItem(
                "m1",
                TrackKind.Audio,
                "CH1",
                "a.wav",
                new TimeRange(new SimTime(5), new SimTime(12)),
                new Dictionary<string, string> { { "note", "test" } });

            Track track = new Track(
                "A/Audio/CH1", "A", TrackKind.Audio, string.Empty,
                new TimelineSample[0], new[] { late, early }, new[] { media });

            IReadOnlyList<EventMarker> markers = track.MarkersIn(
                new TimeRange(new SimTime(0), new SimTime(10)));
            Assert.Single(markers);
            Assert.Equal("e1", markers[0].Id);

            IReadOnlyList<MediaItem> atStart = track.MediaAt(new SimTime(5));
            Assert.Single(atStart);
            IReadOnlyList<MediaItem> atEnd = track.MediaAt(new SimTime(12));
            Assert.Single(atEnd);
            Assert.Empty(track.MediaAt(new SimTime(4.9)));

            Assert.True(track.HasData);
            Assert.Equal(2.0, track.Range.Start.Seconds, 9);
            Assert.Equal(15.0, track.Range.End.Seconds, 9);
        }

        [Fact]
        public void Track_Empty_RangeAndHasData()
        {
            Track track = new Track("A/Other", "A", TrackKind.Other, null, null);
            Assert.False(track.HasData);
            Assert.Equal(0.0, track.Range.Start.Seconds, 9);
            Assert.Equal(0.0, track.Range.End.Seconds, 9);
            Assert.Equal(string.Empty, track.Unit);
        }

        [Fact]
        public void Track_Samples_AreStablySorted()
        {
            Track track = TestHelpers.ScalarTrack(
                "A/X", "A", TrackKind.Other,
                TestHelpers.S(10, 2.0),
                TestHelpers.S(0, 1.0),
                TestHelpers.S(10, 3.0),
                TestHelpers.S(5, 4.0));

            Assert.Equal(0.0, track.Samples[0].Time.Seconds, 9);
            Assert.Equal(5.0, track.Samples[1].Time.Seconds, 9);
            Assert.Equal(10.0, track.Samples[2].Time.Seconds, 9);
            Assert.Equal(2.0, track.Samples[2].Value, 9);
            Assert.Equal(3.0, track.Samples[3].Value, 9);
        }

        [Fact]
        public void Track_WithTimeShift_ShiftsSamplesMarkersMedia()
        {
            EventMarker marker = new EventMarker("e1", new SimTime(12), "change", "x", "A", "A/X");
            MediaItem media = new MediaItem(
                "m1",
                TrackKind.RadarImage,
                "X",
                "r.png",
                new TimeRange(new SimTime(10), new SimTime(20)));
            Track track = new Track(
                "A/X", "A", TrackKind.Heading, "°",
                new[] { TestHelpers.S(0, 0.0), TestHelpers.S(10, 90.0) },
                new[] { marker },
                new[] { media });

            Track shifted = track.WithTimeShift(5.0);

            Assert.Equal(5.0, shifted.Samples[0].Time.Seconds, 9);
            Assert.Equal(15.0, shifted.Samples[1].Time.Seconds, 9);
            Assert.Equal(17.0, shifted.Markers[0].Time.Seconds, 9);
            Assert.Equal(15.0, shifted.Media[0].Range.Start.Seconds, 9);
            Assert.Equal(25.0, shifted.Media[0].Range.End.Seconds, 9);

            double value;
            Assert.False(shifted.TryGetValueAt(new SimTime(4), out value));
            Assert.True(shifted.TryGetValueAt(new SimTime(5), out value));
            Assert.Equal(0.0, value, 9);

            // Original unchanged.
            Assert.Equal(0.0, track.Samples[0].Time.Seconds, 9);
        }
    }
}
