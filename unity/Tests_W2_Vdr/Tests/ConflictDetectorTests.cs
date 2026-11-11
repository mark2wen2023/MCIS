using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class ConflictDetectorTests
    {
        private static Track Constant(
            string id,
            string source,
            TrackKind kind,
            double start,
            double end,
            double value,
            double step = 10.0)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (double t = start; t <= end + 1e-9; t += step)
            {
                samples.Add(TestHelpers.S(t, value));
            }

            return new Track(id, source, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        private static Track Samples(
            string id,
            string source,
            TrackKind kind,
            params TimelineSample[] samples)
        {
            return new Track(id, source, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        [Fact]
        public void Heading_2Point5Degrees_IsConflict()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 2.5)
            });

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);
            Assert.Single(conflicts);

            TimelineConflict conflict = conflicts[0];
            Assert.Equal("C-01", conflict.Id);
            Assert.Equal(TrackKind.Heading, conflict.Kind);
            Assert.Equal("Heading", conflict.Quantity);
            Assert.Equal("A", conflict.SourceA);
            Assert.Equal("B", conflict.SourceB);
            Assert.Equal(0.0, conflict.Range.Start.Seconds, 9);
            Assert.Equal(10.0, conflict.Range.End.Seconds, 9);
            Assert.Equal(2.5, conflict.MaxDifference, 9);
            Assert.Equal(2.0, conflict.Threshold, 9);
            Assert.Equal(0.0, conflict.ValueA, 9);
            Assert.Equal(2.5, conflict.ValueB, 9);
            Assert.Equal("°", conflict.Unit);
            Assert.Contains("A", conflict.Description);
            Assert.Contains("B", conflict.Description);
            Assert.Contains("2.5", conflict.Description);
        }

        [Fact]
        public void Heading_1Point5Degrees_IsNotConflict()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 1.5)
            });

            Assert.Empty(ConflictDetector.Detect(timeline));
        }

        [Theory]
        [InlineData(1.0, false)]
        [InlineData(1.5, true)]
        public void Heading_AcrossZero_UsesShortestArc(double bValue, bool expected)
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 359.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, bValue)
            });

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);
            Assert.Equal(expected ? 1 : 0, conflicts.Count);
            if (expected)
            {
                Assert.Equal(2.5, conflicts[0].MaxDifference, 9);
            }
        }

        [Theory]
        [InlineData(12.4, true)]
        [InlineData(12.2, false)]
        public void Speed_ThresholIsStrict(double bValue, bool expected)
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, bValue)
            });

            Assert.Equal(expected ? 1 : 0, ConflictDetector.Detect(timeline).Count);
        }

        [Fact]
        public void CustomThreshold_OverridesDefault()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 12.15)
            });

            Assert.Empty(ConflictDetector.Detect(timeline));

            ConflictThresholds thresholds = new ConflictThresholds { SpeedKn = 0.1 };
            Assert.Single(ConflictDetector.Detect(timeline, thresholds));
        }

        [Fact]
        public void ContinuousExceedance_MergesIntoOneRange()
        {
            List<TimelineSample> b = new List<TimelineSample>();
            for (int t = 0; t <= 100; t += 10)
            {
                double value = (t >= 20 && t <= 60) ? 3.0 : 0.0;
                b.Add(TestHelpers.S(t, value));
            }

            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 100, 0.0),
                Samples("B/HDG", "B", TrackKind.Heading, b.ToArray())
            });

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);
            Assert.Single(conflicts);
            Assert.True(conflicts[0].Range.Start.Seconds > 10.0);
            Assert.True(conflicts[0].Range.Start.Seconds < 20.0);
            Assert.True(conflicts[0].Range.End.Seconds > 50.0);
            Assert.True(conflicts[0].Range.End.Seconds < 70.0);
            Assert.Equal(3.0, conflicts[0].MaxDifference, 9);
        }

        [Fact]
        public void MinDuration_FiltersShortConflict()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Samples(
                    "B/HDG", "B", TrackKind.Heading,
                    TestHelpers.S(0, 5.0),
                    TestHelpers.S(2, 5.0),
                    TestHelpers.S(3, 0.0),
                    TestHelpers.S(10, 0.0))
            });

            ConflictThresholds strict = new ConflictThresholds { MinDurationSeconds = 5.0 };
            Assert.Empty(ConflictDetector.Detect(timeline, strict));

            ConflictThresholds loose = new ConflictThresholds { MinDurationSeconds = 1.0 };
            Assert.Single(ConflictDetector.Detect(timeline, loose));
        }

        [Fact]
        public void Position_UsesHaversineMeters()
        {
            Track a = TestHelpers.PositionTrack(
                "A/POS", "A",
                TestHelpers.P(0, 122.0, 30.0),
                TestHelpers.P(10, 122.0, 30.0));
            Track b = TestHelpers.PositionTrack(
                "B/POS", "B",
                TestHelpers.P(0, 122.0, 30.001),
                TestHelpers.P(10, 122.0, 30.001));

            MultiTrackTimeline timeline = new MultiTrackTimeline(new[] { a, b });
            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);

            Assert.Single(conflicts);
            Assert.True(conflicts[0].MaxDifference > 110.0);
            Assert.True(conflicts[0].MaxDifference < 112.0);
            Assert.True(double.IsNaN(conflicts[0].ValueA));
            Assert.True(double.IsNaN(conflicts[0].ValueB));
            Assert.Contains("m", conflicts[0].Description);
        }

        [Fact]
        public void Position_WithinThreshold_NoConflict()
        {
            Track a = TestHelpers.PositionTrack(
                "A/POS", "A",
                TestHelpers.P(0, 122.0, 30.0),
                TestHelpers.P(10, 122.0, 30.0));
            Track b = TestHelpers.PositionTrack(
                "B/POS", "B",
                TestHelpers.P(0, 122.0, 30.0002),
                TestHelpers.P(10, 122.0, 30.0002));

            MultiTrackTimeline timeline = new MultiTrackTimeline(new[] { a, b });
            Assert.Empty(ConflictDetector.Detect(timeline));
        }

        [Fact]
        public void Results_AreNumberedInStartTimeOrder()
        {
            Track headingA = Constant("A/HDG", "A", TrackKind.Heading, 0, 100, 0.0);
            Track headingB = Samples(
                "B/HDG", "B", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(20, 0.0),
                TestHelpers.S(30, 3.0), TestHelpers.S(40, 3.0),
                TestHelpers.S(50, 0.0), TestHelpers.S(100, 0.0));

            Track courseA = Constant("A/COG", "A", TrackKind.CourseOverGround, 0, 100, 0.0);
            Track courseB = Samples(
                "B/COG", "B", TrackKind.CourseOverGround,
                TestHelpers.S(0, 0.0), TestHelpers.S(10, 3.0),
                TestHelpers.S(20, 3.0), TestHelpers.S(30, 0.0),
                TestHelpers.S(100, 0.0));

            Track speedA = Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 100, 0.0);
            Track speedB = Samples(
                "B/SOG", "B", TrackKind.SpeedOverGround,
                TestHelpers.S(0, 0.0), TestHelpers.S(10, 0.0),
                TestHelpers.S(20, 0.5), TestHelpers.S(30, 0.5),
                TestHelpers.S(40, 0.0), TestHelpers.S(100, 0.0));

            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                headingA, courseA, speedA, headingB, courseB, speedB
            });

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);
            Assert.Equal(3, conflicts.Count);
            Assert.Equal("C-01", conflicts[0].Id);
            Assert.Equal(TrackKind.CourseOverGround, conflicts[0].Kind);
            Assert.Equal("C-02", conflicts[1].Id);
            Assert.Equal(TrackKind.SpeedOverGround, conflicts[1].Kind);
            Assert.Equal("C-03", conflicts[2].Id);
            Assert.Equal(TrackKind.Heading, conflicts[2].Kind);

            Assert.True(conflicts[0].Range.Start < conflicts[1].Range.Start);
            Assert.True(conflicts[1].Range.Start < conflicts[2].Range.Start);
        }

        [Fact]
        public void TargetKinds_AreComparedByTargetKey_Ruling4()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/TR", "A", TrackKind.TargetRange, 0, 10, 1.0),
                Constant("B/TR", "B", TrackKind.TargetRange, 0, 10, 2.0),
                Constant("A/TB", "A", TrackKind.TargetBearing, 0, 10, 10.0),
                Constant("B/TB", "B", TrackKind.TargetBearing, 0, 10, 20.0)
            });

            // 裁定 4：目标量有阈值就要比（旧行为是跳过）。同目标键 TR/TB 跨源配对。
            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);
            Assert.Equal(2, conflicts.Count);
            Assert.Contains(conflicts, c => c.Kind == TrackKind.TargetRange);
            Assert.Contains(conflicts, c => c.Kind == TrackKind.TargetBearing);
        }

        [Fact]
        public void For_ReturnsNullForUnsupportedKinds()
        {
            ConflictThresholds thresholds = new ConflictThresholds();
            Assert.Null(thresholds.For(TrackKind.EngineTelegraph));
            Assert.Null(thresholds.For(TrackKind.Other));
            Assert.Null(thresholds.For(TrackKind.Audio));
            Assert.Equal(2.0, thresholds.For(TrackKind.Heading).Value, 9);
            Assert.Equal(0.3, thresholds.For(TrackKind.SpeedOverGround).Value, 9);
        }

        [Fact]
        public void SameSourceTracks_AreNotCompared()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/HDG1", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("A/HDG2", "A", TrackKind.Heading, 0, 10, 10.0)
            });

            Assert.Empty(ConflictDetector.Detect(timeline));
        }
    }
}
