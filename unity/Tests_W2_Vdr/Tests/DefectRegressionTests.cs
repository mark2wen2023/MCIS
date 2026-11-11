using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    /// <summary>DEFECTS/W2.md 缺陷 D01–D07 与架构师裁定 1–6 的回归测试（示例数据虚构）。</summary>
    public sealed class DefectRegressionTests
    {
        private static Track Constant(string id, string source, TrackKind kind, double start, double end, double value, string text = null)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (double t = start; t <= end + 1e-9; t += 1.0)
            {
                samples.Add(TestHelpers.S(t, value, text));
            }

            return new Track(id, source, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        private static Track WithMarkers(string id, string source, params (double t, string label)[] markers)
        {
            return new Track(
                id,
                source,
                TrackKind.Other,
                string.Empty,
                new[] { TestHelpers.S(0, 0), TestHelpers.S(1000, 0) },
                markers.Select((m, i) => new EventMarker(id + "#" + i, new SimTime(m.t), "event", m.label, source, id)));
        }

        private static List<AnchorObservation> OutlierAnchors()
        {
            return new List<AnchorObservation>
            {
                new AnchorObservation("k1", "GNSS", new SimTime(0)),
                new AnchorObservation("k2", "GNSS", new SimTime(0)),
                new AnchorObservation("k3", "GNSS", new SimTime(0)),
                new AnchorObservation("k4", "GNSS", new SimTime(0)),
                new AnchorObservation("k1", "A", new SimTime(10)),
                new AnchorObservation("k2", "A", new SimTime(10)),
                new AnchorObservation("k3", "A", new SimTime(10)),
                new AnchorObservation("k4", "A", new SimTime(100))
            };
        }

        // ---------- W2-D01 ----------
        [Theory]
        [InlineData("$GPR")]
        [InlineData("$GPRM")]
        [InlineData("!AIV")]
        [InlineData("!AIVD")]
        [InlineData("$")]
        [InlineData("$,")]
        [InlineData("$GPRM*00")]
        public void W2_D01_TruncatedAddress_ReturnsFalse_NoThrow(string line)
        {
            NmeaSentence sentence;
            string error;
            bool ok = NmeaParser.TryParse(line, out sentence, out error);
            Assert.False(ok);
            Assert.Null(sentence);
            Assert.False(string.IsNullOrEmpty(error));
        }

        [Fact]
        public void W2_D01_TruncatedLineInFile_OnlyDiagnosed_RestImported()
        {
            string[] lines =
            {
                "# 示例数据（虚构）",
                "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea("GPHDT,45.0,T"),
                "2026-05-18T06:15:01.000Z,$GPRM",
                "2026-05-18T06:15:02.000Z,!AIVD",
                "2026-05-18T06:15:03.000Z," + TestHelpers.Nmea("GPHDT,46.0,T")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, TestHelpers.Options("MARY-VDR"));
            Assert.True(result.IsSuccess);
            Track heading = TestHelpers.FindTrack(result.Value, TrackKind.Heading);
            Assert.Equal(2, heading.Samples.Count);
            Assert.Equal(2, result.Value.Diagnostics.Count(d => d.Code == "vdr_parse_error"));
            Assert.Contains(result.Value.Diagnostics, d => d.LineNumber == 3);
            Assert.Contains(result.Value.Diagnostics, d => d.LineNumber == 4);
        }

        // ---------- W2-D02 ----------
        [Fact]
        public void W2_D02_GgaAfterMidnight_RollsDateForward()
        {
            string[] lines =
            {
                TestHelpers.Nmea("GPRMC,235950.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A"),
                TestHelpers.Nmea("GPGGA,000010.00,3006.0100,N,12203.6100,E,1,08,0.9,10.0,M,0.0,M,,")
            };
            VdrImportOptions options = TestHelpers.Options("MARY-VDR");
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, options);
            Assert.True(result.IsSuccess);
            Track position = TestHelpers.FindTrack(result.Value, TrackKind.Position);
            double[] times = position.Samples.Select(s => s.Time.Seconds).ToArray();
            Assert.Equal(new[] { 64790.0, 64810.0 }, times);
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_date_rollover" && d.Severity == DiagnosticSeverity.Info);
        }

        [Fact]
        public void W2_D02_NoRolloverForSmallBackwardStep()
        {
            string[] lines =
            {
                TestHelpers.Nmea("GPRMC,061510.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A"),
                TestHelpers.Nmea("GPGGA,061505.00,3006.0100,N,12203.6100,E,1,08,0.9,10.0,M,0.0,M,,")
            };
            VdrImportOptions options = TestHelpers.Options("MARY-VDR");
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;
            Track position = TestHelpers.FindTrack(VdrNmeaImporter.Import(lines, options).Value, TrackKind.Position);
            Assert.Equal(new[] { 905.0, 910.0 }, position.Samples.Select(s => s.Time.Seconds).ToArray());
        }

        // ---------- W2-D03 / 裁定 3 ----------
        [Fact]
        public void W2_D03_TagBlockChecksum_ValidInvalidMissing()
        {
            string body = TestHelpers.Nmea("GPHDT,45.0,T");
            NmeaSentence s;
            string e;

            Assert.True(NmeaParser.TryParse(TestHelpers.TagBlock("c:1779084900") + body, out s, out e));
            Assert.True(s.HasTagBlock);
            Assert.True(s.TagBlockChecksumValid);
            Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(1779084900), s.TagBlockTimeUtc);

            Assert.True(NmeaParser.TryParse("\\c:1779084900*00\\" + body, out s, out e));
            Assert.True(s.HasTagBlock);
            Assert.False(s.TagBlockChecksumValid);
            Assert.Null(s.TagBlockTimeUtc);

            Assert.True(NmeaParser.TryParse("\\c:1779084900\\" + body, out s, out e));
            Assert.False(s.TagBlockChecksumValid);
            Assert.Null(s.TagBlockTimeUtc);

            string lower = TestHelpers.TagBlock("c:1779084900").ToLowerInvariant();
            Assert.True(NmeaParser.TryParse(lower + body, out s, out e));
            Assert.True(s.TagBlockChecksumValid);
        }

        [Fact]
        public void Ruling3_TimePriority_TagBlockOverPrefixOverSentence()
        {
            // 标签块 06:15:00Z（=900 s），前缀 06:15:05Z（=905 s），句内 06:15:10Z（=910 s）。
            string rmc = TestHelpers.Nmea("GPRMC,061510.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            string withValidTag = TestHelpers.TagBlock("c:1779084900") + rmc;
            Track sog = TestHelpers.FindTrack(
                VdrNmeaImporter.Import(new[] { withValidTag }, TestHelpers.Options("V")).Value,
                TrackKind.SpeedOverGround);
            Assert.Equal(900.0, sog.Samples[0].Time.Seconds, 6);

            Result<VdrImportResult> prefixOnly = VdrNmeaImporter.Import(
                new[] { "2026-05-18T06:15:05.000Z," + rmc }, TestHelpers.Options("V"));
            Assert.Equal(905.0, TestHelpers.FindTrack(prefixOnly.Value, TrackKind.SpeedOverGround).Samples[0].Time.Seconds, 6);

            Result<VdrImportResult> sentenceOnly = VdrNmeaImporter.Import(new[] { rmc }, TestHelpers.Options("V"));
            Assert.Equal(910.0, TestHelpers.FindTrack(sentenceOnly.Value, TrackKind.SpeedOverGround).Samples[0].Time.Seconds, 6);
        }

        [Fact]
        public void Ruling3_InvalidTagBlock_FallsBackAndDiagnoses()
        {
            string rmc = TestHelpers.Nmea("GPRMC,061510.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { "\\c:1779084900*00\\" + rmc }, TestHelpers.Options("V"));
            Assert.True(result.IsSuccess);
            Assert.Equal(910.0, TestHelpers.FindTrack(result.Value, TrackKind.SpeedOverGround).Samples[0].Time.Seconds, 6);
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_tagblock_invalid" && d.Severity == DiagnosticSeverity.Warning);
        }

        [Fact]
        public void Ruling3_ValidTagBlock_ProducesGnssAnchor()
        {
            string rmc = TestHelpers.Nmea("GPRMC,061510.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { TestHelpers.TagBlock("c:1779084913") + rmc }, TestHelpers.Options("V"));
            Assert.Equal(2, result.Value.Anchors.Count);
            Result<IReadOnlyList<ClockOffsetEstimate>> est = ClockOffsetEstimator.Estimate(result.Value.Anchors, "GNSS");
            Assert.Equal(3.0, est.Value.First(x => x.SourceId == "V").OffsetSeconds, 6);
        }

        // ---------- W2-D04 ----------
        [Fact]
        public void W2_D04_ConflictHasContractFields_AndResolution()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0)
            });

            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(timeline, null, "CASE-2026-LM01");
            TimelineConflict c = Assert.Single(result.Conflicts);
            Assert.Equal("CASE-2026-LM01", c.CaseId);
            Assert.Equal(ConflictStatus.Open, c.Status);
            Assert.Equal("待处理", c.StatusText);
            Assert.Equal(c.Id, c.ConflictId);
            Assert.Equal(c.Description, c.Summary);
            Assert.Null(c.Resolution);

            TimelineConflict pending = c.WithResolution(ConflictStatus.PendingInterview, "待询问核实", null, null);
            Assert.Equal("待询问核实", ConflictStatusText.ToChinese(pending.Status));
            Assert.Equal(ConflictStatus.Open, c.Status);

            Assert.Throws<ArgumentException>(() => c.WithResolution(ConflictStatus.Resolved, "采信 AIS", null, null));
            DateTimeOffset at = new DateTimeOffset(2026, 5, 20, 10, 0, 0, TimeSpan.FromHours(8));
            TimelineConflict accepted = c.WithResolution(ConflictStatus.AcceptedAsIs, "待定·采信 AIS", "调查员甲", at);
            Assert.Equal("调查员甲", accepted.ResolvedBy);
            Assert.Equal(at, accepted.ResolvedAt);
            Assert.Equal("CASE-2026-LM01", accepted.CaseId);
            Assert.Equal("按现状采信", accepted.StatusText);
        }

        // ---------- W2-D05 / 裁定 2 ----------
        [Fact]
        public void W2_D05_Median_FlagsOutlier_NonZeroUncertainty()
        {
            ClockOffsetEstimate a = ClockOffsetEstimator.Estimate(OutlierAnchors(), "GNSS", OffsetMethod.Median).Value[1];
            Assert.Equal(10.0, a.OffsetSeconds, 9);
            Assert.Equal(4, a.AnchorCount);
            Assert.Equal(4, a.UsedAnchorCount);
            RejectedAnchor r = Assert.Single(a.RejectedAnchors);
            Assert.Equal("k4", r.EventKey);
            Assert.False(r.ExcludedFromFit);
            Assert.Contains("离群", r.Reason);
            Assert.True(a.UncertaintySeconds > 0.0);
        }

        [Fact]
        public void W2_D05_LeastSquares_ExcludesOutlierBeforeFit()
        {
            ClockOffsetEstimate a = ClockOffsetEstimator.Estimate(OutlierAnchors(), "GNSS", OffsetMethod.LeastSquares).Value[1];
            Assert.Equal(10.0, a.OffsetSeconds, 9);
            Assert.Equal(4, a.AnchorCount);
            Assert.Equal(3, a.UsedAnchorCount);
            Assert.True(Assert.Single(a.RejectedAnchors).ExcludedFromFit);
            Assert.True(a.UncertaintySeconds > 0.0);
        }

        [Fact]
        public void W2_D05_Options_AbsoluteFloorConfigurable()
        {
            ClockOffsetOptions options = new ClockOffsetOptions { OutlierAbsoluteFloorSeconds = 1000.0 };
            ClockOffsetEstimate a = ClockOffsetEstimator.Estimate(OutlierAnchors(), "GNSS", OffsetMethod.LeastSquares, options).Value[1];
            Assert.Empty(a.RejectedAnchors);
            Assert.Equal(32.5, a.OffsetSeconds, 9);
            Assert.NotSame(ClockOffsetOptions.Default, ClockOffsetOptions.Default);
        }

        // ---------- W2-D06 / 裁定 1 ----------
        [Fact]
        public void W2_D06_SpeedEqualToThreshold_NotConflict_SlightlyOverIs()
        {
            Assert.Empty(ConflictDetector.Detect(new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 12.3)
            })));
            Assert.Single(ConflictDetector.Detect(new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 12.31)
            })));
        }

        [Fact]
        public void W2_D06_HeadingEqualToThreshold_NotConflict_SlightlyOverIs()
        {
            Assert.Empty(ConflictDetector.Detect(new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 359.1),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 1.1)
            })));
            Assert.Single(ConflictDetector.Detect(new MultiTrackTimeline(new[]
            {
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 359.1),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 1.11)
            })));
        }

        // ---------- W2-D07 ----------
        [Fact]
        public void W2_D07_Default_IsFreshInstance_NoPollution()
        {
            ConflictThresholds first = ConflictThresholds.Default;
            ConflictThresholds second = ConflictThresholds.Default;
            Assert.NotSame(first, second);
            first.SpeedKn = 100.0;
            Assert.Equal(0.3, ConflictThresholds.Default.SpeedKn, 9);

            Assert.Single(ConflictDetector.Detect(new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0)
            })));
        }

        // ---------- 裁定 4 ----------
        [Fact]
        public void Ruling4_TargetsPairedByName_UnpairedGivesNotAvailable()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("MARY-VDR/TTM01/TargetRange", "MARY-VDR", TrackKind.TargetRange, 0, 10, 1.00, "LILY"),
                Constant("VTS-RADAR/TTM07/TargetRange", "VTS-RADAR", TrackKind.TargetRange, 0, 10, 1.25, "Lily"),
                Constant("MARY-VDR/TTM02/TargetRange", "MARY-VDR", TrackKind.TargetRange, 0, 10, 3.0, "BUOY-3")
            });

            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(timeline);
            TimelineConflict c = Assert.Single(result.Conflicts);
            Assert.Equal(TrackKind.TargetRange, c.Kind);
            Assert.Equal(0.25, c.MaxDifference, 6);
            ConflictDiagnostic d = Assert.Single(result.Diagnostics);
            Assert.Equal("NotAvailable", d.Code);
            Assert.Equal("MARY-VDR/TTM02/TargetRange", d.TrackId);
        }

        [Fact]
        public void Ruling4_NonOverlappingTargetTracks_NotAvailable()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/TTM01/TargetBearing", "A", TrackKind.TargetBearing, 0, 10, 10.0, "LILY"),
                Constant("B/TTM01/TargetBearing", "B", TrackKind.TargetBearing, 100, 110, 30.0, "LILY")
            });
            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(timeline);
            Assert.Empty(result.Conflicts);
            Assert.Contains(result.Diagnostics, x => x.Code == ConflictDiagnostic.NotAvailableCode && x.Kind == TrackKind.TargetBearing);
        }

        // ---------- 裁定 5 ----------
        [Fact]
        public void Ruling5_EventTimeDifference_OverThreshold_IsConflict()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                WithMarkers("MARY-VDR/Events", "MARY-VDR", (540.0, "STOP ENGINE")),
                WithMarkers("MARY-BRIDGE/Events", "MARY-BRIDGE", (605.0, "stop engine"))
            });
            TimelineConflict c = Assert.Single(ConflictDetector.Detect(timeline));
            Assert.Equal(TrackKind.EventTime, c.Kind);
            Assert.Equal("s", c.Unit);
            Assert.Equal(65.0, c.MaxDifference, 6);
            Assert.Equal("MARY-BRIDGE", c.SourceA);
            Assert.Contains("STOP ENGINE", c.Description);
            Assert.Contains("65.0 s", c.Description);
        }

        [Fact]
        public void Ruling5_EventTimeWithinThreshold_NotConflict_AndConfigurable()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                WithMarkers("A/Events", "A", (540.0, "COLLISION")),
                WithMarkers("B/Events", "B", (541.5, "COLLISION"))
            });
            Assert.Empty(ConflictDetector.Detect(timeline));
            Assert.Single(ConflictDetector.Detect(timeline, new ConflictThresholds { EventTimeSeconds = 1.0 }));
        }

        [Fact]
        public void Ruling5_EventAliases_MapToCanonicalName()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                WithMarkers("A/Events", "A", (540.0, "COLLISION")),
                WithMarkers("B/Events", "B", (560.0, "碰撞"))
            });
            Assert.Empty(ConflictDetector.Detect(timeline));

            ConflictThresholds thresholds = new ConflictThresholds();
            thresholds.EventAliases["碰撞"] = "COLLISION";
            Assert.Single(ConflictDetector.Detect(timeline, thresholds));
        }

        // ---------- 裁定 6 ----------
        [Fact]
        public void Ruling6_LongSentence_ParsedWithWarning()
        {
            string longBody = "GPTTM,01,1.25,045.0,T,8.0,225.0,T,0.21,3.5,N,LILY-WITH-A-VERY-LONG-FICTIONAL-TARGET-NAME-XX,T,,061500.00,A";
            string line = "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea(longBody);
            Result<VdrImportResult> result = VdrNmeaImporter.Import(new[] { line }, TestHelpers.Options("V"));
            Assert.True(result.IsSuccess);
            Assert.NotNull(TestHelpers.FindTrack(result.Value, TrackKind.TargetRange));
            VdrDiagnostic d = Assert.Single(result.Value.Diagnostics, x => x.Code == "vdr_line_too_long");
            Assert.Equal(DiagnosticSeverity.Warning, d.Severity);

            NmeaSentence s;
            string e;
            Assert.True(NmeaParser.TryParse(TestHelpers.Nmea("GPHDT,45.0,T"), out s, out e));
            Assert.True(s.SentenceLength <= VdrNmeaImporter.MaxSentenceLength);
        }
    }
}
