using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class EndToEndTests
    {
        private sealed class Dataset
        {
            public List<Track> Tracks { get; } = new List<Track>();
            public List<AnchorObservation> Anchors { get; } = new List<AnchorObservation>();
            public List<VdrDiagnostic> Diagnostics { get; } = new List<VdrDiagnostic>();
        }

        private static Dataset LoadAllSamples()
        {
            Dataset dataset = new Dataset();

            Result<VdrImportResult> mary = VdrNmeaImporter.Import(
                TestHelpers.ReadSampleLines("mary_vdr.nmea"),
                TestHelpers.Options("MARY-VDR"));
            Assert.True(mary.IsSuccess, mary.ErrorMessage);

            Result<VdrImportResult> lily = VdrNmeaImporter.Import(
                TestHelpers.ReadSampleLines("lily_svdr.nmea"),
                TestHelpers.Options("LILY-SVDR"));
            Assert.True(lily.IsSuccess, lily.ErrorMessage);

            VdrCsvMapping vtsMapping = new VdrCsvMapping
            {
                TimeColumn = "time_utc",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping
                    {
                        Column = "sog_kn",
                        Kind = TrackKind.SpeedOverGround
                    },
                    new VdrCsvColumnMapping
                    {
                        Column = "cog_deg",
                        Kind = TrackKind.CourseOverGround
                    }
                }
            };
            Result<VdrImportResult> vts = VdrCsvImporter.Import(
                TestHelpers.ReadSampleLines("vts_ais.csv"),
                vtsMapping,
                TestHelpers.Options("VTS-AIS"));
            Assert.True(vts.IsSuccess, vts.ErrorMessage);

            VdrCsvMapping bridgeMapping = new VdrCsvMapping
            {
                TimeColumn = "time_local",
                TimeFormat = "yyyy-MM-dd HH:mm:ss",
                TimeZoneOffset = TimeSpan.FromHours(8),
                EventColumn = "event",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping
                    {
                        Column = "telegraph",
                        Kind = TrackKind.EngineTelegraph,
                        MarkChanges = true,
                        TextValues = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                        {
                            { "STOP", 0 },
                            { "HALF AHEAD", 3 },
                            { "FULL AHEAD", 4 },
                            { "SLOW AHEAD", 2 },
                            { "FULL ASTERN", -4 }
                        }
                    },
                    new VdrCsvColumnMapping
                    {
                        Column = "rudder_deg",
                        Kind = TrackKind.RudderAngle
                    }
                }
            };
            Result<VdrImportResult> bridge = VdrCsvImporter.Import(
                TestHelpers.ReadSampleLines("mary_telegraph_rudder.csv"),
                bridgeMapping,
                TestHelpers.Options("MARY-BRIDGE"));
            Assert.True(bridge.IsSuccess, bridge.ErrorMessage);

            Result<VdrImportResult> media = VdrMediaManifestImporter.Import(
                TestHelpers.ReadSampleLines("mary_media_manifest.csv"),
                TestHelpers.Options("MARY-MEDIA"));
            Assert.True(media.IsSuccess, media.ErrorMessage);

            foreach (VdrImportResult part in new[] { mary.Value, lily.Value, vts.Value, bridge.Value, media.Value })
            {
                dataset.Tracks.AddRange(part.Tracks);
                dataset.Anchors.AddRange(part.Anchors);
                dataset.Diagnostics.AddRange(part.Diagnostics);
            }

            return dataset;
        }

        [Fact]
        public void Samples_HaveFictionalHeader()
        {
            string[] files =
            {
                "mary_vdr.nmea",
                "lily_svdr.nmea",
                "vts_ais.csv",
                "mary_telegraph_rudder.csv",
                "mary_media_manifest.csv"
            };

            foreach (string file in files)
            {
                Assert.True(File.Exists(Path.Combine(TestHelpers.SamplesDirectory, file)), file);
                string first = File.ReadLines(Path.Combine(TestHelpers.SamplesDirectory, file)).First();
                Assert.Contains("示例数据（虚构）", first);
            }
        }

        [Fact]
        public void GnssAnchors_EstimateExpectedClockOffsets()
        {
            Dataset dataset = LoadAllSamples();
            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(dataset.Anchors, "GNSS", OffsetMethod.Median);

            Assert.True(result.IsSuccess, result.ErrorMessage);
            ClockOffsetEstimate mary = result.Value.First(e => e.SourceId == "MARY-VDR");
            ClockOffsetEstimate lily = result.Value.First(e => e.SourceId == "LILY-SVDR");

            Assert.True(mary.AnchorCount > 10);
            Assert.True(lily.AnchorCount > 10);
            Assert.Equal(3.2, mary.OffsetSeconds, 1);
            Assert.True(Math.Abs(mary.OffsetSeconds - 3.2) < 0.1);
            Assert.True(Math.Abs(lily.OffsetSeconds - (-1.5)) < 0.1);
            Assert.True(double.IsNaN(mary.UncertaintySeconds) || mary.UncertaintySeconds < 0.1);
        }

        [Fact]
        public void Calibration_AlignsMaryAndLilyToTrueTime()
        {
            Dataset dataset = LoadAllSamples();
            IReadOnlyList<ClockOffsetEstimate> estimates =
                ClockOffsetEstimator.Estimate(dataset.Anchors, "GNSS").Value;

            MultiTrackTimeline calibrated =
                TimelineCalibrator.Apply(dataset.Tracks, estimates);

            Track maryPosition = calibrated.Find("MARY-VDR/Position");
            GeoCoord maryStart;
            Assert.True(maryPosition.TryGetPositionAt(new SimTime(900), out maryStart));

            Track maryCourse = calibrated.Find("MARY-VDR/CourseOverGround");
            double course;
            Assert.True(maryCourse.TryGetValueAt(new SimTime(900), out course));
            Assert.Equal(45.0, course, 6);

            Track vtsCourse = calibrated.Find("VTS-AIS/CourseOverGround");
            double vts;
            Assert.True(vtsCourse.TryGetValueAt(new SimTime(900), out vts));
            Assert.Equal(45.0, vts, 6);

            Track lilyCourse = calibrated.Find("LILY-SVDR/CourseOverGround");
            double lilyValue;
            Assert.True(lilyCourse.TryGetValueAt(new SimTime(900), out lilyValue));
            Assert.Equal(225.0, lilyValue, 6);
        }

        [Fact]
        public void CalibratedTimeline_DetectsCourseAndSpeedConflicts()
        {
            Dataset dataset = LoadAllSamples();
            IReadOnlyList<ClockOffsetEstimate> estimates =
                ClockOffsetEstimator.Estimate(dataset.Anchors, "GNSS").Value;
            MultiTrackTimeline calibrated =
                TimelineCalibrator.Apply(dataset.Tracks, estimates);

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(calibrated);
            Assert.NotEmpty(conflicts);

            TimelineConflict course = conflicts.FirstOrDefault(c =>
                c.Kind == TrackKind.CourseOverGround &&
                c.SourceA == "MARY-VDR" &&
                c.SourceB == "VTS-AIS");
            Assert.NotNull(course);
            Assert.True(course.MaxDifference > 2.4);
            Assert.True(course.Range.Start.Seconds >= 1300.0);
            Assert.True(course.Range.Start.Seconds <= 1320.0);
            Assert.Contains("MARY-VDR", course.Description);
            Assert.Contains("VTS-AIS", course.Description);

            TimelineConflict speed = conflicts.FirstOrDefault(c =>
                c.Kind == TrackKind.SpeedOverGround &&
                c.SourceA == "MARY-VDR" &&
                c.SourceB == "VTS-AIS");
            Assert.NotNull(speed);
            Assert.True(speed.MaxDifference > 0.39);
            Assert.True(speed.Range.Start.Seconds >= 1370.0);
            Assert.True(speed.Range.Start.Seconds <= 1380.0);

            Assert.Equal(conflicts.Count, conflicts.Select(c => c.Id).Distinct().Count());
            Assert.Equal("C-01", conflicts[0].Id);
        }

        [Theory]
        [InlineData(900.0)]
        [InlineData(1200.0)]
        [InlineData(1320.0)]
        [InlineData(1440.0)]
        [InlineData(1560.0)]
        public void TimelineScrub_ManyTracksHaveValueOrMedia(double seconds)
        {
            Dataset dataset = LoadAllSamples();
            IReadOnlyList<ClockOffsetEstimate> estimates =
                ClockOffsetEstimator.Estimate(dataset.Anchors, "GNSS").Value;
            MultiTrackTimeline calibrated =
                TimelineCalibrator.Apply(dataset.Tracks, estimates);

            TimelineSnapshot snapshot = calibrated.QueryAt(new SimTime(seconds));
            int active = snapshot.Values.Count(v =>
                v.HasValue || v.HasPosition || v.ActiveMedia.Count > 0);

            Assert.True(active >= 8, "t=" + seconds + " active=" + active);
        }

        [Fact]
        public void TimelineMarkers_IncludeTelegraphChangesAndMedia()
        {
            Dataset dataset = LoadAllSamples();
            IReadOnlyList<ClockOffsetEstimate> estimates =
                ClockOffsetEstimator.Estimate(dataset.Anchors, "GNSS").Value;
            MultiTrackTimeline calibrated =
                TimelineCalibrator.Apply(dataset.Tracks, estimates);

            IReadOnlyList<EventMarker> markers = calibrated.MarkersIn(
                new TimeRange(new SimTime(900), new SimTime(1620)));

            Assert.Contains(markers, m => m.Kind == "change");
            Assert.Contains(markers, m => m.Kind == "media");
            Assert.Contains(markers, m => m.Kind == "event" && m.Label == "COLLISION");
        }
    }
}
