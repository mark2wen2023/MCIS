using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class VdrNmeaImporterTests
    {
        private static string Rmc(
            string time,
            string date,
            double sog,
            double cog,
            string status = "A")
        {
            return TestHelpers.Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "GPRMC,{0},A,3006.0000,N,12203.6000,E,{1:0.0},{2:0.0},{3},,,A",
                time, sog, cog, date).Replace(",A,", "," + status + ","));
        }

        private static string Gga(string time, int quality, double lat = 30.1, double lon = 122.06)
        {
            string latDeg = ((int)lat).ToString("00", CultureInfo.InvariantCulture);
            string latMin = ((lat - (int)lat) * 60.0).ToString("00.0000", CultureInfo.InvariantCulture);
            string lonDeg = ((int)lon).ToString("000", CultureInfo.InvariantCulture);
            string lonMin = ((lon - (int)lon) * 60.0).ToString("00.0000", CultureInfo.InvariantCulture);
            return TestHelpers.Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "GPGGA,{0},{1}{2},N,{3}{4},E,{5},12,0.8,5.0,M,0.0,M,,",
                time, latDeg, latMin, lonDeg, lonMin, quality));
        }

        [Fact]
        public void SampleMary_ImportsAllSupportedSentenceTypes()
        {
            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                TestHelpers.ReadSampleLines("mary_vdr.nmea"),
                TestHelpers.Options("MARY-VDR"));

            Assert.True(result.IsSuccess, result.ErrorMessage);
            VdrImportResult value = result.Value;

            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/Position"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/SpeedOverGround"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/CourseOverGround"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/Heading"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/RateOfTurn"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/RudderAngle"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/TTM01/TargetRange"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/TTM01/TargetBearing"));
            Assert.NotNull(value.Tracks.FirstOrDefault(t => t.Id == "MARY-VDR/TLL01/TargetPosition"));

            Track speed = value.Tracks.First(t => t.Id == "MARY-VDR/SpeedOverGround");
            Assert.Equal(12.0, speed.Samples[0].Value, 9);

            Track course = value.Tracks.First(t => t.Id == "MARY-VDR/CourseOverGround");
            Assert.Equal(45.0, course.Samples[0].Value, 9);

            Track targetRange = value.Tracks.First(t => t.Id == "MARY-VDR/TTM01/TargetRange");
            TimelineSample targetSample;
            Assert.True(targetRange.TryGetSampleAt(targetRange.Samples[0].Time, out targetSample));
            Assert.Equal("LILY", targetSample.Text);

            Track targetPosition = value.Tracks.First(t => t.Id == "MARY-VDR/TLL01/TargetPosition");
            Assert.True(targetPosition.Samples[0].HasPosition);

            Assert.Contains(value.Diagnostics, d => d.Code == "vdr_bad_checksum");
            Assert.Single(value.Diagnostics, d => d.Code == "vdr_unsupported");
            Assert.True(value.Anchors.Count > 0);
            Assert.True(value.LinesRead > 100);
        }

        [Fact]
        public void BadChecksum_IsSkippedByDefault_AndKeptWhenRequested()
        {
            string good = Rmc("061500.00", "180526", 12.0, 45.0);
            int original = Convert.ToInt32(good.Substring(good.Length - 2), 16);
            string bad = good.Substring(0, good.Length - 2) +
                         ((original + 1) % 256).ToString("X2", CultureInfo.InvariantCulture);
            string line = "2026-05-18T06:15:03.200Z," + bad;

            Result<VdrImportResult> skipped =
                VdrNmeaImporter.Import(new[] { line }, TestHelpers.Options("MARY-VDR"));
            Assert.True(skipped.IsSuccess);
            Assert.Empty(skipped.Value.Tracks);
            Assert.Contains(skipped.Value.Diagnostics, d => d.Code == "vdr_bad_checksum");

            VdrImportOptions keep = TestHelpers.Options("MARY-VDR");
            keep.KeepBadChecksum = true;
            Result<VdrImportResult> kept =
                VdrNmeaImporter.Import(new[] { line }, keep);
            Assert.True(kept.IsSuccess);
            Assert.NotEmpty(kept.Value.Tracks);
            Assert.DoesNotContain(kept.Value.Diagnostics, d => d.Code == "vdr_bad_checksum");
        }

        [Fact]
        public void GgaWithoutDate_UsesDefaultDate()
        {
            string line = "2026-05-18T06:16:00.000Z," + Gga("061600", 1);
            VdrImportOptions options = TestHelpers.Options(
                "MARY-VDR",
                new DateTime(2026, 5, 18, 0, 0, 0, DateTimeKind.Utc));

            Result<VdrImportResult> result = VdrNmeaImporter.Import(new[] { line }, options);
            Assert.True(result.IsSuccess);
            Track position = result.Value.Tracks.First(t => t.Kind == TrackKind.Position);
            Assert.Equal(960.0, position.Samples[0].Time.Seconds, 6);
        }

        [Fact]
        public void GgaWithoutDateOrDefault_WritesNoTimeDiagnostic()
        {
            string line = "2026-05-18T06:16:00.000Z," + Gga("061600", 1);

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { line },
                TestHelpers.Options("MARY-VDR"));

            Assert.True(result.IsSuccess);
            Assert.Empty(result.Value.Tracks);
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_no_time");
        }

        [Fact]
        public void RmcDate_UpdatesDateForFollowingGga()
        {
            string[] lines =
            {
                "2026-05-18T06:15:00.000Z," + Gga("061500", 1),
                "2026-05-18T06:20:00.000Z," + Rmc("062000.00", "190526", 12.0, 45.0),
                "2026-05-18T06:21:00.000Z," + Gga("062100", 1)
            };
            VdrImportOptions options = TestHelpers.Options(
                "MARY-VDR",
                new DateTime(2026, 5, 18, 0, 0, 0, DateTimeKind.Utc));
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, options);
            Assert.True(result.IsSuccess);

            Track position = result.Value.Tracks.First(t => t.Kind == TrackKind.Position);
            SimTime expected = SimTime.FromUtc(
                new DateTimeOffset(2026, 5, 19, 6, 21, 0, TimeSpan.Zero),
                TestHelpers.Epoch);
            Assert.Equal(expected.Seconds, position.Samples[2].Time.Seconds, 6);
        }

        [Fact]
        public void UnsupportedType_IsReportedOnlyOnce()
        {
            string[] lines =
            {
                TestHelpers.Nmea("GPMWV,045.0,T,,,10.0,N,,"),
                TestHelpers.Nmea("GPMWV,090.0,T,,,12.0,N,,")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                lines,
                TestHelpers.Options("MARY-VDR"));

            Assert.True(result.IsSuccess);
            Assert.Single(result.Value.Diagnostics, d => d.Code == "vdr_unsupported");
        }

        [Fact]
        public void TimeBasis_LogPrefix_And_GnssSentenceTime()
        {
            string line = "2026-05-18T06:15:05.000Z," + Rmc("061500.00", "180526", 12.0, 45.0);

            VdrImportOptions logPrefix = TestHelpers.Options("MARY-VDR");
            Result<VdrImportResult> prefixResult = VdrNmeaImporter.Import(new[] { line }, logPrefix);
            Track prefixCourse = prefixResult.Value.Tracks.First(t => t.Kind == TrackKind.CourseOverGround);
            Assert.Equal(905.0, prefixCourse.Samples[0].Time.Seconds, 6);

            VdrImportOptions gnss = TestHelpers.Options("MARY-VDR");
            gnss.TimeBasis = VdrTimeBasis.GnssSentenceTime;
            Result<VdrImportResult> gnssResult = VdrNmeaImporter.Import(new[] { line }, gnss);
            Track gnssCourse = gnssResult.Value.Tracks.First(t => t.Kind == TrackKind.CourseOverGround);
            Assert.Equal(900.0, gnssCourse.Samples[0].Time.Seconds, 6);
        }

        [Fact]
        public void MissingPrefix_FallsBackToLastGnssTime()
        {
            string[] lines =
            {
                "2026-05-18T06:15:03.200Z," + Rmc("061500.00", "180526", 12.0, 45.0),
                TestHelpers.Nmea("GPHDT,046.0,T")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                lines,
                TestHelpers.Options("MARY-VDR"));

            Track heading = result.Value.Tracks.First(t => t.Kind == TrackKind.Heading);
            Assert.Equal(900.0, heading.Samples[0].Time.Seconds, 6);
        }

        [Fact]
        public void EmitGnssAnchors_CreatesSourceAndGnssObservations()
        {
            string line = "2026-05-18T06:15:03.200Z," + Rmc("061500.00", "180526", 12.0, 45.0);

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { line },
                TestHelpers.Options("MARY-VDR"));

            Assert.Equal(2, result.Value.Anchors.Count);
            AnchorObservation source = result.Value.Anchors.First(a => a.SourceId == "MARY-VDR");
            AnchorObservation reference = result.Value.Anchors.First(a => a.SourceId == "GNSS");
            Assert.Equal(source.EventKey, reference.EventKey);
            Assert.Equal("GNSS@20260518T061500.000", source.EventKey);
            Assert.Equal(903.2, source.Timestamp.Seconds, 6);
            Assert.Equal(900.0, reference.Timestamp.Seconds, 6);

            VdrImportOptions noAnchors = TestHelpers.Options("MARY-VDR");
            noAnchors.EmitGnssAnchors = false;
            Result<VdrImportResult> withoutAnchors = VdrNmeaImporter.Import(new[] { line }, noAnchors);
            Assert.Empty(withoutAnchors.Value.Anchors);
        }

        [Fact]
        public void GgaQualityZero_IsDiscarded()
        {
            string line = "2026-05-18T06:16:00.000Z," + Gga("061600", 0);
            VdrImportOptions options = TestHelpers.Options(
                "MARY-VDR",
                new DateTime(2026, 5, 18, 0, 0, 0, DateTimeKind.Utc));

            Result<VdrImportResult> result = VdrNmeaImporter.Import(new[] { line }, options);
            Assert.True(result.IsSuccess);
            Assert.Empty(result.Value.Tracks);
        }

        [Fact]
        public void Rsa_RightIsPositive_PortIsNegative()
        {
            string[] lines =
            {
                "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea("GPRSA,12.5,A,,V"),
                "2026-05-18T06:15:10.000Z," + TestHelpers.Nmea("GPRSA,,V,7.5,A")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                lines,
                TestHelpers.Options("MARY-VDR"));

            Track rudder = result.Value.Tracks.First(t => t.Kind == TrackKind.RudderAngle);
            Assert.Equal(2, rudder.Samples.Count);
            Assert.Equal(12.5, rudder.Samples[0].Value, 9);
            Assert.Equal(-7.5, rudder.Samples[1].Value, 9);
        }

        [Fact]
        public void RotWithStatusV_IsIgnored()
        {
            string[] lines =
            {
                "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea("GPROT,20.0,V")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                lines,
                TestHelpers.Options("MARY-VDR"));

            Assert.Empty(result.Value.Tracks);
        }

        [Fact]
        public void Vtg_MapsCourseAndSpeed()
        {
            string line = "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea("GPVTG,123.4,T,,M,12.3,N,22.8,K,A");

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { line },
                TestHelpers.Options("MARY-VDR"));

            Assert.True(result.IsSuccess);
            Assert.Equal(123.4, result.Value.Tracks.First(t => t.Kind == TrackKind.CourseOverGround).Samples[0].Value, 6);
            Assert.Equal(12.3, result.Value.Tracks.First(t => t.Kind == TrackKind.SpeedOverGround).Samples[0].Value, 6);
        }

        [Fact]
        public void Ttm_TargetNumberAndName_AreMapped()
        {
            string line = "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea("RATTM,02,0.52,231.5,T,9.8,045.0,T,0.10,1.2,N,LILY,A,A,061515");

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { line },
                TestHelpers.Options("MARY-VDR"));

            Track range = result.Value.Tracks.First(t => t.Id == "MARY-VDR/TTM02/TargetRange");
            Track bearing = result.Value.Tracks.First(t => t.Id == "MARY-VDR/TTM02/TargetBearing");
            Assert.Equal(0.52, range.Samples[0].Value, 6);
            Assert.Equal(231.5, bearing.Samples[0].Value, 6);
            Assert.Equal("LILY", range.Samples[0].Text);
        }

        [Fact]
        public void Tll_TargetNumberAndPosition_AreMapped()
        {
            string line = "2026-05-18T06:15:00.000Z," + TestHelpers.Nmea("RATLL,03,3006.5000,N,12203.5000,E,LILY,061515");

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { line },
                TestHelpers.Options("MARY-VDR"));

            Track position = result.Value.Tracks.First(t => t.Id == "MARY-VDR/TLL03/TargetPosition");
            Assert.True(position.Samples[0].HasPosition);
            Assert.Equal(30.108333, position.Samples[0].Position.LatDeg, 5);
            Assert.Equal(122.058333, position.Samples[0].Position.LonDeg, 5);
            Assert.Equal("LILY", position.Samples[0].Text);
        }

        [Fact]
        public void ImportText_SplitsLines()
        {
            string text =
                "# comment\r\n" +
                "2026-05-18T06:15:03.200Z," + Rmc("061500.00", "180526", 12.0, 45.0) + "\r\n";

            Result<VdrImportResult> result = VdrNmeaImporter.ImportText(
                text,
                TestHelpers.Options("MARY-VDR"));

            Assert.True(result.IsSuccess);
            Assert.Equal(3, result.Value.LinesRead);
            Assert.NotEmpty(result.Value.Tracks);
        }

        [Fact]
        public void MissingSourceId_Fails()
        {
            VdrImportOptions options = new VdrImportOptions
            {
                CaseEpochUtc = TestHelpers.Epoch
            };

            Result<VdrImportResult> result =
                VdrNmeaImporter.Import(new string[0], options);

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_missing_source", result.ErrorCode);
        }
    }
}
