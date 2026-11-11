using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class CalibrationStatusTests
    {
        [Fact]
        public void CalibrationStatusText_ReturnsChinese()
        {
            Assert.Equal("未校准", CalibrationStatusText.ToChinese(CalibrationStatus.Uncalibrated));
            Assert.Equal("基准", CalibrationStatusText.ToChinese(CalibrationStatus.Reference));
            Assert.Equal("已校准", CalibrationStatusText.ToChinese(CalibrationStatus.Calibrated));
        }

        [Fact]
        public void Track_DefaultsToUncalibrated_AndWithCalibrationReturnsNewObject()
        {
            Track track = TestHelpers.ScalarTrack(
                "A/Heading", "A", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(10, 10.0));

            Assert.Equal(CalibrationStatus.Uncalibrated, track.CalibrationStatus);
            Assert.Equal(0.0, track.AppliedOffsetSeconds, 9);

            Track calibrated = track.WithCalibration(CalibrationStatus.Calibrated, -3.2);

            Assert.NotSame(track, calibrated);
            Assert.Equal(CalibrationStatus.Uncalibrated, track.CalibrationStatus);
            Assert.Equal(0.0, track.AppliedOffsetSeconds, 9);
            Assert.Equal(CalibrationStatus.Calibrated, calibrated.CalibrationStatus);
            Assert.Equal(-3.2, calibrated.AppliedOffsetSeconds, 9);
            Assert.Equal(0.0, calibrated.Samples[0].Time.Seconds, 9);
        }

        [Fact]
        public void Track_WithTimeShift_PreservesCalibration()
        {
            Track track = TestHelpers.ScalarTrack(
                    "A/Heading", "A", TrackKind.Heading, TestHelpers.S(0, 0.0))
                .WithCalibration(CalibrationStatus.Calibrated, -5.0);

            Track shifted = track.WithTimeShift(5.0);

            Assert.Equal(CalibrationStatus.Calibrated, shifted.CalibrationStatus);
            Assert.Equal(-5.0, shifted.AppliedOffsetSeconds, 9);
            Assert.Equal(5.0, shifted.Samples[0].Time.Seconds, 9);
        }

        [Fact]
        public void Calibrate_ProducesStatusesAndChineseDescriptions()
        {
            Track gnss = TestHelpers.ScalarTrack(
                "GNSS/Heading", "GNSS", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(100, 10.0));
            Track mary = TestHelpers.ScalarTrack(
                "MARY-VDR/Heading", "MARY-VDR", TrackKind.Heading,
                TestHelpers.S(3.2, 0.0), TestHelpers.S(103.2, 10.0));
            Track vts = TestHelpers.ScalarTrack(
                "VTS-AIS/Heading", "VTS-AIS", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(100, 10.0));

            List<ClockOffsetEstimate> offsets = new List<ClockOffsetEstimate>
            {
                new ClockOffsetEstimate(
                    "GNSS", "GNSS", 0.0, 0.0, 10,
                    OffsetMethod.Median, true),
                new ClockOffsetEstimate(
                    "MARY-VDR", "GNSS", 3.2, 0.01, 60,
                    0, OffsetMethod.Median, false,
                    new double[0], null, CalibrationStatus.Calibrated),
                new ClockOffsetEstimate(
                    "VTS-AIS", "GNSS", double.NaN, double.NaN, 0,
                    OffsetMethod.Median, false)
            };

            CalibrationResult result = TimelineCalibrator.Calibrate(
                new[] { gnss, mary, vts }, offsets);

            Assert.Equal(3, result.Sources.Count);
            Assert.Equal("GNSS", result.Sources[0].SourceId);
            Assert.Equal("MARY-VDR", result.Sources[1].SourceId);
            Assert.Equal("VTS-AIS", result.Sources[2].SourceId);

            SourceCalibration reference = result.Sources[0];
            Assert.Equal(CalibrationStatus.Reference, reference.Status);
            Assert.Equal("GNSS：基准", reference.Description);

            SourceCalibration calibrated = result.Sources[1];
            Assert.Equal(CalibrationStatus.Calibrated, calibrated.Status);
            Assert.Equal(3.2, calibrated.OffsetSeconds, 9);
            Assert.Equal(0.01, calibrated.UncertaintySeconds, 9);
            Assert.Equal(60, calibrated.AnchorCount);
            Assert.Equal(0, calibrated.ManualAnchorCount);
            Assert.Null(calibrated.ViaSourceId);
            Assert.Equal(
                "MARY-VDR：已校准，偏移 +3.200 s ±0.010 s（锚点 60，人工 0）",
                calibrated.Description);

            SourceCalibration uncalibrated = result.Sources[2];
            Assert.Equal(CalibrationStatus.Uncalibrated, uncalibrated.Status);
            Assert.True(double.IsNaN(uncalibrated.OffsetSeconds));
            Assert.Equal(
                "VTS-AIS：未校准（无共同锚点，按原始时间使用）",
                uncalibrated.Description);

            Assert.Equal(new[] { "VTS-AIS" }, result.UncalibratedSources);
            Assert.False(result.AllCalibrated);

            Track calibratedMary = result.Timeline.Find("MARY-VDR/Heading");
            Assert.Equal(0.0, calibratedMary.Samples[0].Time.Seconds, 9);
            Assert.Equal(CalibrationStatus.Calibrated, calibratedMary.CalibrationStatus);
            Assert.Equal(-3.2, calibratedMary.AppliedOffsetSeconds, 9);

            Track uncalibratedVts = result.Timeline.Find("VTS-AIS/Heading");
            Assert.Equal(0.0, uncalibratedVts.Samples[0].Time.Seconds, 9);
            Assert.Equal(CalibrationStatus.Uncalibrated, uncalibratedVts.CalibrationStatus);
            Assert.Equal(0.0, uncalibratedVts.AppliedOffsetSeconds, 9);
        }

        [Fact]
        public void Calibrate_IndirectSource_DescribesVia()
        {
            Track bridge = TestHelpers.ScalarTrack(
                "MARY-BRIDGE/EngineTelegraph", "MARY-BRIDGE", TrackKind.EngineTelegraph,
                TestHelpers.S(100, -4.0, "FULL ASTERN"));

            ClockOffsetEstimate estimate = new ClockOffsetEstimate(
                "MARY-BRIDGE", "GNSS", 0.0, 0.004, 2, 1,
                OffsetMethod.Median, false, new double[0],
                "MARY-VDR", CalibrationStatus.Calibrated);

            CalibrationResult result = TimelineCalibrator.Calibrate(
                new[] { bridge }, new[] { estimate });

            SourceCalibration source = result.Sources[0];
            Assert.Equal("MARY-VDR", source.ViaSourceId);
            Assert.Equal(1, source.ManualAnchorCount);
            Assert.Contains("已校准（经 MARY-VDR 间接）", source.Description);
            Assert.Contains("偏移 +0.000 s ±0.004 s", source.Description);
            Assert.Contains("锚点 2，人工 1", source.Description);
        }

        [Fact]
        public void Calibrate_AllCalibratedOrReference_IsTrue()
        {
            Track gnss = TestHelpers.ScalarTrack(
                "GNSS/Heading", "GNSS", TrackKind.Heading, TestHelpers.S(0, 0.0));
            Track mary = TestHelpers.ScalarTrack(
                "MARY-VDR/Heading", "MARY-VDR", TrackKind.Heading, TestHelpers.S(0, 0.0));

            CalibrationResult result = TimelineCalibrator.Calibrate(
                new[] { gnss, mary },
                new[]
                {
                    new ClockOffsetEstimate(
                        "GNSS", "GNSS", 0.0, 0.0, 1,
                        OffsetMethod.Median, true),
                    new ClockOffsetEstimate(
                        "MARY-VDR", "GNSS", 3.2, 0.0, 1,
                        OffsetMethod.Median, false)
                });

            Assert.True(result.AllCalibrated);
            Assert.Empty(result.UncalibratedSources);
            Assert.Equal(2, result.Sources.Count);
        }

        [Fact]
        public void Snapshot_TrackValueCarriesCalibrationStatus()
        {
            Track calibratedTrack = TestHelpers.ScalarTrack(
                    "MARY-VDR/SOG", "MARY-VDR", TrackKind.SpeedOverGround,
                    TestHelpers.S(0, 12.0))
                .WithCalibration(CalibrationStatus.Calibrated, -3.2);
            Track uncalibratedTrack = TestHelpers.ScalarTrack(
                "VTS-AIS/SOG", "VTS-AIS", TrackKind.SpeedOverGround,
                TestHelpers.S(0, 12.0));

            MultiTrackTimeline timeline = new MultiTrackTimeline(
                new[] { calibratedTrack, uncalibratedTrack });
            TimelineSnapshot snapshot = timeline.QueryAt(new SimTime(0));

            Assert.Equal(
                CalibrationStatus.Calibrated,
                FindValue(snapshot, "MARY-VDR/SOG").CalibrationStatus);
            Assert.Equal(
                CalibrationStatus.Uncalibrated,
                FindValue(snapshot, "VTS-AIS/SOG").CalibrationStatus);

            Assert.Equal(new[] { "VTS-AIS" }, timeline.UncalibratedSources());
        }

        [Fact]
        public void MultiTrackTimeline_UncalibratedSources_AreDistinctAndSorted()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                TestHelpers.ScalarTrack(
                    "C/HDG", "C", TrackKind.Heading, TestHelpers.S(0, 0.0)),
                TestHelpers.ScalarTrack(
                    "B/HDG1", "B", TrackKind.Heading, TestHelpers.S(0, 0.0)),
                TestHelpers.ScalarTrack(
                    "B/HDG2", "B", TrackKind.Heading, TestHelpers.S(0, 0.0)),
                TestHelpers.ScalarTrack(
                    "A/HDG", "A", TrackKind.Heading, TestHelpers.S(0, 0.0))
                    .WithCalibration(CalibrationStatus.Calibrated, 0.0)
            });

            Assert.Equal(new[] { "B", "C" }, timeline.UncalibratedSources());
        }

        [Fact]
        public void Conflict_InvolvingUncalibrated_AppendsChineseHint()
        {
            Track a = Constant("A/HDG", "A", TrackKind.Heading, 0.0)
                .WithCalibration(CalibrationStatus.Calibrated, 0.0);
            Track b = Constant("B/HDG", "B", TrackKind.Heading, 5.0);

            IReadOnlyList<TimelineConflict> conflicts =
                ConflictDetector.Detect(new MultiTrackTimeline(new[] { a, b }));

            Assert.Single(conflicts);
            TimelineConflict conflict = conflicts[0];
            Assert.True(conflict.InvolvesUncalibrated);
            Assert.Equal(CalibrationStatus.Calibrated, conflict.CalibrationStatusA);
            Assert.Equal(CalibrationStatus.Uncalibrated, conflict.CalibrationStatusB);
            Assert.EndsWith(
                "（含未校准来源：B，差异可能由钟差引起）",
                conflict.Description);
        }

        [Fact]
        public void Conflict_BothCalibrated_HasNoUncalibratedHint()
        {
            Track a = Constant("A/HDG", "A", TrackKind.Heading, 0.0)
                .WithCalibration(CalibrationStatus.Calibrated, 0.0);
            Track b = Constant("B/HDG", "B", TrackKind.Heading, 5.0)
                .WithCalibration(CalibrationStatus.Calibrated, 0.0);

            TimelineConflict conflict = ConflictDetector
                .Detect(new MultiTrackTimeline(new[] { a, b }))
                .Single();

            Assert.False(conflict.InvolvesUncalibrated);
            Assert.DoesNotContain("未校准", conflict.Description);
        }

        [Fact]
        public void Conflict_OldConstructor_KeepsDescriptionAndReferenceDefaults()
        {
            TimelineConflict conflict = new TimelineConflict(
                "C-01",
                TrackKind.Heading,
                "Heading",
                "A",
                "A/HDG",
                "B",
                "B/HDG",
                new TimeRange(new SimTime(0), new SimTime(10)),
                new SimTime(5),
                0.0,
                5.0,
                5.0,
                2.0,
                "°",
                "原描述");

            Assert.Equal("原描述", conflict.Description);
            Assert.False(conflict.InvolvesUncalibrated);
            Assert.Equal(CalibrationStatus.Reference, conflict.CalibrationStatusA);
            Assert.Equal(CalibrationStatus.Reference, conflict.CalibrationStatusB);
        }

        private static Track Constant(
            string id,
            string source,
            TrackKind kind,
            double value)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (int t = 0; t <= 10; t++)
            {
                samples.Add(TestHelpers.S(t, value));
            }

            return new Track(
                id, source, kind, TrackKindInfo.DefaultUnit(kind), samples);
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
