using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class ManualAnchorTests
    {
        private static SimTime S(double seconds)
        {
            return new SimTime(seconds);
        }

        private static AnchorObservation Anchor(string key, string source, double time)
        {
            return new AnchorObservation(key, source, S(time));
        }

        [Fact]
        public void ManualAnchor_ValidatesArguments()
        {
            Assert.Throws<ArgumentException>(() =>
                new ManualAnchor("", "A", S(0), "B", S(1)));
            Assert.Throws<ArgumentException>(() =>
                new ManualAnchor(null, "A", S(0), "B", S(1)));
            Assert.Throws<ArgumentException>(() =>
                new ManualAnchor("k", "", S(0), "B", S(1)));
            Assert.Throws<ArgumentException>(() =>
                new ManualAnchor("k", "A", S(0), null, S(1)));
            Assert.Throws<ArgumentException>(() =>
                new ManualAnchor("k", "A", S(0), "A", S(1)));
        }

        [Fact]
        public void ManualAnchor_FromUtc_ConvertsToSimTime()
        {
            DateTimeOffset epoch = new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);
            ManualAnchor anchor = ManualAnchor.FromUtc(
                "BRIDGE-FULL-ASTERN",
                "MARY-BRIDGE",
                epoch.AddMinutes(23).AddSeconds(30),
                "MARY-VDR",
                epoch.AddMinutes(23).AddSeconds(33.2),
                epoch,
                "调查员甲确认",
                "调查员甲");

            Assert.Equal("BRIDGE-FULL-ASTERN", anchor.EventKey);
            Assert.Equal("MARY-BRIDGE", anchor.SourceA);
            Assert.Equal(1410.0, anchor.TimeA.Seconds, 9);
            Assert.Equal("MARY-VDR", anchor.SourceB);
            Assert.Equal(1413.2, anchor.TimeB.Seconds, 9);
            Assert.Equal("调查员甲确认", anchor.Note);
            Assert.Equal("调查员甲", anchor.Investigator);
        }

        [Fact]
        public void ToObservations_ProducesTwoManualPrefixedObservations()
        {
            ManualAnchor anchor = new ManualAnchor(
                "VHF-START", "MARY-MEDIA", S(900), "MARY-VDR", S(903.2), "VHF 开始");
            IReadOnlyList<AnchorObservation> observations =
                ManualAnchors.ToObservations(new[] { anchor });

            Assert.Equal(2, observations.Count);
            Assert.Equal("MANUAL:VHF-START", observations[0].EventKey);
            Assert.Equal("MARY-MEDIA", observations[0].SourceId);
            Assert.Equal(900.0, observations[0].Timestamp.Seconds, 9);
            Assert.Equal(AnchorOrigin.Manual, observations[0].Origin);
            Assert.Equal("VHF 开始", observations[0].Note);
            Assert.Equal("MANUAL:VHF-START", observations[1].EventKey);
            Assert.Equal("MARY-VDR", observations[1].SourceId);
            Assert.Equal(903.2, observations[1].Timestamp.Seconds, 9);
            Assert.Equal(AnchorOrigin.Manual, observations[1].Origin);
        }

        [Fact]
        public void Merge_CombinesAutomaticAndManual()
        {
            List<AnchorObservation> automatic = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 100)
            };
            ManualAnchor manual = new ManualAnchor(
                "m1", "MARY-BRIDGE", S(200), "MARY-VDR", S(203));

            IReadOnlyList<AnchorObservation> merged =
                ManualAnchors.Merge(automatic, new[] { manual });

            Assert.Equal(3, merged.Count);
            Assert.Equal(AnchorOrigin.Automatic, merged[0].Origin);
            Assert.Equal("k1", merged[0].EventKey);
            Assert.Equal("MANUAL:m1", merged[1].EventKey);
            Assert.Equal(AnchorOrigin.Manual, merged[1].Origin);
        }

        [Fact]
        public void ManualAnchors_EstimateOffsetThroughVdr()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>();
            for (int i = 0; i < 3; i++)
            {
                anchors.Add(Anchor("g" + i, "GNSS", 100 + i * 10));
                anchors.Add(Anchor("g" + i, "MARY-VDR", 103.2 + i * 10));
            }

            ManualAnchor manual = new ManualAnchor(
                "BRIDGE-FULL-ASTERN", "MARY-BRIDGE", S(200), "MARY-VDR", S(203.2));
            IReadOnlyList<AnchorObservation> merged =
                ManualAnchors.Merge(anchors, new[] { manual });

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(merged, "GNSS", OffsetMethod.Median);
            Assert.True(result.IsSuccess, result.ErrorMessage);

            ClockOffsetEstimate vdr = result.Value.First(e => e.SourceId == "MARY-VDR");
            Assert.Equal(3.2, vdr.OffsetSeconds, 9);
            Assert.Null(vdr.ViaSourceId);
            Assert.Equal(0, vdr.ManualAnchorCount);
            Assert.Equal(CalibrationStatus.Calibrated, vdr.Status);

            ClockOffsetEstimate bridge = result.Value.First(e => e.SourceId == "MARY-BRIDGE");
            Assert.Equal(0.0, bridge.OffsetSeconds, 9);
            Assert.Equal("MARY-VDR", bridge.ViaSourceId);
            Assert.Equal(1, bridge.AnchorCount);
            Assert.Equal(1, bridge.ManualAnchorCount);
            Assert.True(double.IsNaN(bridge.UncertaintySeconds));
            Assert.Equal(CalibrationStatus.Calibrated, bridge.Status);
        }

        [Fact]
        public void ManualAndAutomaticAnchors_SameSource_AreCountedTogether()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 100),
                Anchor("k2", "GNSS", 110),
                Anchor("k3", "GNSS", 120),
                Anchor("k1", "A", 105),
                Anchor("k2", "A", 115),
                Anchor("k3", "A", 125)
            };

            ManualAnchor manual = new ManualAnchor(
                "FIELD-CHECK", "A", S(200), "GNSS", S(198));
            IReadOnlyList<AnchorObservation> merged =
                ManualAnchors.Merge(anchors, new[] { manual });

            ClockOffsetEstimate estimate = ClockOffsetEstimator
                .Estimate(merged, "GNSS", OffsetMethod.Median)
                .Value
                .First(e => e.SourceId == "A");

            Assert.Equal(5.0, estimate.OffsetSeconds, 9);
            Assert.Equal(4, estimate.AnchorCount);
            Assert.Equal(1, estimate.ManualAnchorCount);
        }

        [Fact]
        public void IndirectChain_ComposesOffsetAndUncertainty()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>();
            for (int i = 0; i < 3; i++)
            {
                anchors.Add(Anchor("g" + i, "GNSS", 100 + i * 10));
                anchors.Add(Anchor("g" + i, "MARY-VDR", 103.2 + i * 10));
            }

            List<ManualAnchor> manual = new List<ManualAnchor>();
            for (int i = 0; i < 3; i++)
            {
                manual.Add(new ManualAnchor(
                    "b" + i,
                    "MARY-BRIDGE",
                    S(500 + i * 10),
                    "MARY-VDR",
                    S(503.2 + i * 10)));
            }

            IReadOnlyList<AnchorObservation> merged =
                ManualAnchors.Merge(anchors, manual);
            ClockOffsetEstimate bridge = ClockOffsetEstimator
                .Estimate(merged, "GNSS", OffsetMethod.Median)
                .Value
                .First(e => e.SourceId == "MARY-BRIDGE");

            Assert.Equal(0.0, bridge.OffsetSeconds, 9);
            // 两段各取不确定度下限 0.001 s（裁定 2），平方和开方合成 = √2 × 0.001 s。
            Assert.Equal(Math.Sqrt(2.0) * 0.001, bridge.UncertaintySeconds, 9);
            Assert.Equal("MARY-VDR", bridge.ViaSourceId);
            Assert.Equal(3, bridge.AnchorCount);
            Assert.Equal(3, bridge.ManualAnchorCount);
            Assert.Equal(CalibrationStatus.Calibrated, bridge.Status);
        }

        [Fact]
        public void IndirectChain_NaNUncertaintyPropagates()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("g1", "GNSS", 100),
                Anchor("g2", "GNSS", 110),
                Anchor("g3", "GNSS", 120),
                Anchor("g1", "MARY-VDR", 103.2),
                Anchor("g2", "MARY-VDR", 113.2),
                Anchor("g3", "MARY-VDR", 123.2)
            };
            ManualAnchor manual = new ManualAnchor(
                "b1", "MARY-BRIDGE", S(500), "MARY-VDR", S(503.2));

            ClockOffsetEstimate bridge = ClockOffsetEstimator
                .Estimate(ManualAnchors.Merge(anchors, new[] { manual }), "GNSS")
                .Value
                .First(e => e.SourceId == "MARY-BRIDGE");

            Assert.Equal(0.0, bridge.OffsetSeconds, 9);
            Assert.True(double.IsNaN(bridge.UncertaintySeconds));
        }

        [Fact]
        public void DirectAnchors_TakePriorityOverIndirect()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("g1", "GNSS", 0),
                Anchor("g2", "GNSS", 10),
                Anchor("g3", "GNSS", 20),
                Anchor("g1", "A", 10),
                Anchor("g2", "A", 20),
                Anchor("g3", "A", 30),
                Anchor("g1", "B", 20),
                Anchor("g2", "B", 30),
                Anchor("g3", "B", 40),
                Anchor("ab1", "A", 100),
                Anchor("ab2", "A", 110),
                Anchor("ab3", "A", 120),
                Anchor("ab1", "B", 105),
                Anchor("ab2", "B", 115),
                Anchor("ab3", "B", 125)
            };

            ClockOffsetEstimate b = ClockOffsetEstimator
                .Estimate(anchors, "GNSS")
                .Value
                .First(e => e.SourceId == "B");

            Assert.Equal(20.0, b.OffsetSeconds, 9);
            Assert.Null(b.ViaSourceId);
            Assert.Equal(3, b.AnchorCount);
        }

        [Fact]
        public void CircularAnchorGraph_TerminatesDeterministically()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("ga", "GNSS", 0),
                Anchor("ga", "A", 10),
                Anchor("ab", "A", 100),
                Anchor("ab", "B", 105),
                Anchor("bc", "B", 200),
                Anchor("bc", "C", 205),
                Anchor("ca", "C", 300),
                Anchor("ca", "A", 302)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS");

            Assert.True(result.IsSuccess);
            Assert.Equal(4, result.Value.Count);
            foreach (ClockOffsetEstimate estimate in result.Value)
            {
                Assert.False(double.IsNaN(estimate.OffsetSeconds), estimate.SourceId);
            }
        }

        [Fact]
        public void BreadthFirst_ChoosesOrdinalIntermediateAtSameHop()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("ga", "GNSS", 0),
                Anchor("ga", "A", 10),
                Anchor("gb", "GNSS", 0),
                Anchor("gb", "B", 20),
                Anchor("shared", "A", 100),
                Anchor("shared", "B", 110),
                Anchor("shared", "C", 105)
            };

            ClockOffsetEstimate c = ClockOffsetEstimator
                .Estimate(anchors, "GNSS")
                .Value
                .First(e => e.SourceId == "C");

            Assert.Equal("A", c.ViaSourceId);
            Assert.Equal(15.0, c.OffsetSeconds, 9);
        }

        [Fact]
        public void ManualAnchorCsvImporter_ParsesSampleRows()
        {
            Result<IReadOnlyList<ManualAnchor>> result = ManualAnchorCsvImporter.Import(
                TestHelpers.ReadSampleLines("manual_anchors.csv"),
                TestHelpers.Epoch);

            Assert.True(result.IsSuccess, result.ErrorMessage);
            Assert.Equal(2, result.Value.Count);

            ManualAnchor bridge = result.Value[0];
            Assert.Equal("BRIDGE-FULL-ASTERN", bridge.EventKey);
            Assert.Equal("MARY-BRIDGE", bridge.SourceA);
            Assert.Equal(1410.0, bridge.TimeA.Seconds, 9);
            Assert.Equal("MARY-VDR", bridge.SourceB);
            Assert.Equal(1413.2, bridge.TimeB.Seconds, 9);
            Assert.Equal("调查员甲", bridge.Investigator);

            ManualAnchor media = result.Value[1];
            Assert.Equal("MEDIA-VHF-CH16-START", media.EventKey);
            Assert.Equal("MARY-MEDIA", media.SourceA);
            Assert.Equal(900.0, media.TimeA.Seconds, 9);
            Assert.Equal(903.2, media.TimeB.Seconds, 9);
        }

        [Fact]
        public void ManualAnchorCsvImporter_MissingColumn_Fails()
        {
            Result<IReadOnlyList<ManualAnchor>> result = ManualAnchorCsvImporter.Import(
                new[] { "event_key,source_a,time_a_utc", "k,A,2026-05-18T06:00:00Z" },
                TestHelpers.Epoch);

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_manual_anchor_missing_column", result.ErrorCode);
        }

        [Fact]
        public void EndToEnd_ManualAnchorsCalibrateBridgeAndMedia()
        {
            List<Track> tracks;
            List<AnchorObservation> anchors;
            LoadSampleDataset(out tracks, out anchors);

            Result<IReadOnlyList<ManualAnchor>> manualResult = ManualAnchorCsvImporter.Import(
                TestHelpers.ReadSampleLines("manual_anchors.csv"),
                TestHelpers.Epoch);
            Assert.True(manualResult.IsSuccess, manualResult.ErrorMessage);

            IReadOnlyList<AnchorObservation> merged =
                ManualAnchors.Merge(anchors, manualResult.Value);
            Result<IReadOnlyList<ClockOffsetEstimate>> estimates =
                ClockOffsetEstimator.Estimate(merged, "GNSS", OffsetMethod.Median);
            Assert.True(estimates.IsSuccess, estimates.ErrorMessage);

            CalibrationResult calibration =
                TimelineCalibrator.Calibrate(tracks, estimates.Value);

            SourceCalibration bridge = calibration.Sources
                .First(s => s.SourceId == "MARY-BRIDGE");
            Assert.Equal(CalibrationStatus.Calibrated, bridge.Status);
            Assert.Equal(0.0, bridge.OffsetSeconds, 6);
            Assert.Equal("MARY-VDR", bridge.ViaSourceId);
            Assert.Equal(1, bridge.ManualAnchorCount);
            Assert.Contains("已校准", bridge.Description);
            Assert.Contains("经 MARY-VDR 间接", bridge.Description);

            SourceCalibration media = calibration.Sources
                .First(s => s.SourceId == "MARY-MEDIA");
            Assert.Equal(CalibrationStatus.Calibrated, media.Status);
            Assert.Equal(0.0, media.OffsetSeconds, 6);
            Assert.Equal("MARY-VDR", media.ViaSourceId);

            SourceCalibration vts = calibration.Sources
                .First(s => s.SourceId == "VTS-AIS");
            Assert.Equal(CalibrationStatus.Uncalibrated, vts.Status);
            Assert.Contains("VTS-AIS", vts.Description);
            Assert.Contains("未校准", vts.Description);
            Assert.Contains("VTS-AIS", calibration.UncalibratedSources);
            Assert.False(calibration.AllCalibrated);

            Track bridgeTrack = calibration.Timeline.Find("MARY-BRIDGE/EngineTelegraph");
            Assert.NotNull(bridgeTrack);
            Assert.Equal(CalibrationStatus.Calibrated, bridgeTrack.CalibrationStatus);
            Assert.Equal(0.0, bridgeTrack.AppliedOffsetSeconds, 6);

            Track mediaTrack = calibration.Timeline.Find("MARY-MEDIA/Audio/CH16");
            Assert.NotNull(mediaTrack);
            Assert.Equal(CalibrationStatus.Calibrated, mediaTrack.CalibrationStatus);

            IReadOnlyList<TimelineConflict> conflicts =
                ConflictDetector.Detect(calibration.Timeline);
            TimelineConflict course = conflicts.FirstOrDefault(c =>
                c.Kind == TrackKind.CourseOverGround &&
                c.SourceA == "MARY-VDR" &&
                c.SourceB == "VTS-AIS");
            Assert.NotNull(course);
            Assert.True(course.InvolvesUncalibrated);
            Assert.Equal(CalibrationStatus.Calibrated, course.CalibrationStatusA);
            Assert.Equal(CalibrationStatus.Uncalibrated, course.CalibrationStatusB);
            Assert.EndsWith(
                "（含未校准来源：VTS-AIS，差异可能由钟差引起）",
                course.Description);
        }

        [Fact]
        public void VtsAis_AsReference_WorksWhenItHasAnchors()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>();
            for (int i = 0; i < 3; i++)
            {
                anchors.Add(Anchor("v" + i, "VTS-AIS", 100 + i * 10));
                anchors.Add(Anchor("v" + i, "MARY-VDR", 103.2 + i * 10));
            }

            ManualAnchor manual = new ManualAnchor(
                "BRIDGE-VHF", "MARY-BRIDGE", S(200), "MARY-VDR", S(203.2));
            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(
                    ManualAnchors.Merge(anchors, new[] { manual }),
                    "VTS-AIS");

            Assert.True(result.IsSuccess, result.ErrorMessage);
            ClockOffsetEstimate reference = result.Value[0];
            Assert.Equal("VTS-AIS", reference.SourceId);
            Assert.True(reference.IsReference);
            Assert.Equal(CalibrationStatus.Reference, reference.Status);

            ClockOffsetEstimate vdr = result.Value.First(e => e.SourceId == "MARY-VDR");
            Assert.Equal(3.2, vdr.OffsetSeconds, 9);
            Assert.Null(vdr.ViaSourceId);

            ClockOffsetEstimate bridge = result.Value.First(e => e.SourceId == "MARY-BRIDGE");
            Assert.Equal(0.0, bridge.OffsetSeconds, 9);
            Assert.Equal("MARY-VDR", bridge.ViaSourceId);
        }

        [Fact]
        public void VtsAis_AsReferenceWithoutAnchors_Fails()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("g1", "GNSS", 0),
                Anchor("g1", "MARY-VDR", 3.2)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "VTS-AIS");

            Assert.False(result.IsSuccess);
            Assert.Equal("timeline_no_reference", result.ErrorCode);
        }

        private static void LoadSampleDataset(
            out List<Track> tracks,
            out List<AnchorObservation> anchors)
        {
            tracks = new List<Track>();
            anchors = new List<AnchorObservation>();

            Result<VdrImportResult> mary = VdrNmeaImporter.Import(
                TestHelpers.ReadSampleLines("mary_vdr.nmea"),
                TestHelpers.Options("MARY-VDR"));
            Assert.True(mary.IsSuccess, mary.ErrorMessage);

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

            foreach (VdrImportResult part in new[]
                     {
                         mary.Value, vts.Value, bridge.Value, media.Value
                     })
            {
                tracks.AddRange(part.Tracks);
                anchors.AddRange(part.Anchors);
            }
        }
    }
}
