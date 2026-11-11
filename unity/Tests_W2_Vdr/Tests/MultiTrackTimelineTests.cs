using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class MultiTrackTimelineTests
    {
        private static MultiTrackTimeline BuildTimeline()
        {
            Track headingA = new Track(
                "A/Heading", "A", TrackKind.Heading, "°",
                new[] { TestHelpers.S(0, 10.0, "ten"), TestHelpers.S(10, 20.0, "twenty") },
                new[]
                {
                    new EventMarker("e2", new SimTime(8), "change", "later", "A", "A/Heading"),
                    new EventMarker("e1", new SimTime(2), "change", "earlier", "A", "A/Heading")
                });

            Track headingB = TestHelpers.ScalarTrack(
                "B/Heading", "B", TrackKind.Heading,
                TestHelpers.S(5, 12.0), TestHelpers.S(15, 22.0));

            Track position = TestHelpers.PositionTrack(
                "A/Position", "A",
                TestHelpers.P(0, 122.0, 30.0),
                TestHelpers.P(10, 122.01, 30.01));

            MediaItem media = new MediaItem(
                "m1", TrackKind.Audio, "CH1", "a.wav",
                new TimeRange(new SimTime(0), new SimTime(10)));
            Track audio = new Track(
                "A/Audio/CH1", "A", TrackKind.Audio, string.Empty,
                new TimelineSample[0],
                new[] { new EventMarker("e3", new SimTime(1), "media", "a.wav", "A", "A/Audio/CH1") },
                new[] { media });

            return new MultiTrackTimeline(new[] { headingA, headingB, position, audio });
        }

        [Fact]
        public void Find_OfKind_FromSource_Work()
        {
            MultiTrackTimeline timeline = BuildTimeline();
            Assert.NotNull(timeline.Find("A/Heading"));
            Assert.Null(timeline.Find("missing"));
            Assert.Equal(2, Count(timeline.OfKind(TrackKind.Heading)));
            Assert.Equal(3, Count(timeline.FromSource("A")));
        }

        [Fact]
        public void Range_IsUnionOfTracks()
        {
            MultiTrackTimeline timeline = BuildTimeline();
            Assert.Equal(0.0, timeline.Range.Start.Seconds, 9);
            Assert.Equal(15.0, timeline.Range.End.Seconds, 9);
        }

        [Fact]
        public void QueryAt_ReturnsScalarPositionTextAndMedia()
        {
            MultiTrackTimeline timeline = BuildTimeline();
            TimelineSnapshot snapshot = timeline.QueryAt(new SimTime(5));

            Assert.Equal(5.0, snapshot.Time.Seconds, 9);
            Assert.Equal(4, snapshot.Values.Count);

            TrackValue headingA = FindValue(snapshot, "A/Heading");
            Assert.True(headingA.HasValue);
            Assert.Equal(15.0, headingA.Value, 9);
            Assert.Equal("ten", headingA.Text);
            Assert.False(headingA.HasPosition);

            TrackValue position = FindValue(snapshot, "A/Position");
            Assert.False(position.HasValue);
            Assert.True(position.HasPosition);
            Assert.Equal(122.005, position.Position.LonDeg, 9);
            Assert.Equal(30.005, position.Position.LatDeg, 9);

            TrackValue audio = FindValue(snapshot, "A/Audio/CH1");
            Assert.False(audio.HasValue);
            Assert.Single(audio.ActiveMedia);
            Assert.Equal("m1", audio.ActiveMedia[0].Id);
        }

        [Fact]
        public void QueryAt_OutsideRange_HasNoValue()
        {
            MultiTrackTimeline timeline = BuildTimeline();
            TimelineSnapshot snapshot = timeline.QueryAt(new SimTime(100));
            TrackValue heading = FindValue(snapshot, "A/Heading");
            Assert.False(heading.HasValue);
            Assert.False(heading.HasPosition);
            Assert.True(double.IsNaN(heading.Value));
        }

        [Fact]
        public void MarkersIn_MergesAndSorts()
        {
            MultiTrackTimeline timeline = BuildTimeline();
            IReadOnlyList<EventMarker> markers = timeline.MarkersIn(
                new TimeRange(new SimTime(0), new SimTime(10)));

            Assert.Equal(3, markers.Count);
            Assert.Equal("e3", markers[0].Id);
            Assert.Equal("e1", markers[1].Id);
            Assert.Equal("e2", markers[2].Id);
        }

        private static int Count(IEnumerable<Track> tracks)
        {
            int count = 0;
            foreach (Track track in tracks)
            {
                count++;
            }

            return count;
        }

        private static TrackValue FindValue(TimelineSnapshot snapshot, string trackId)
        {
            for (int i = 0; i < snapshot.Values.Count; i++)
            {
                if (snapshot.Values[i].TrackId == trackId)
                {
                    return snapshot.Values[i];
                }
            }

            throw new InvalidOperationException("Track not found: " + trackId);
        }
    }
}
