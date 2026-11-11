using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    /// <summary>
    /// W2.2 小改项：caseId 拒写、角度 deltaUnit 写 "deg"、时间源相差 &gt;2 s 的 Info 诊断。
    /// 所有演示数据均为虚构。
    /// </summary>
    public sealed class W22Tests
    {
        private const string Source = "MARY-VDR";
        private const string CaseId = "CASE-W22";
        private const string SixFifteenUnix = "1779084900"; // 2026-05-18 06:15:00 UTC

        private static readonly DateTimeOffset Epoch =
            new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);

        private static VdrImportOptions Options(VdrTimeBasis basis = VdrTimeBasis.LogPrefix)
        {
            return new VdrImportOptions
            {
                SourceId = Source,
                CaseEpochUtc = Epoch,
                TimeBasis = basis
            };
        }

        private static string Nmea(string body)
        {
            int checksum = 0;
            for (int i = 0; i < body.Length; i++)
            {
                checksum ^= body[i];
            }

            return "$" + body + "*" + checksum.ToString("X2", CultureInfo.InvariantCulture);
        }

        private static string TagBlock(string content)
        {
            int checksum = 0;
            for (int i = 0; i < content.Length; i++)
            {
                checksum ^= content[i];
            }

            return "\\" + content + "*" + checksum.ToString("X2", CultureInfo.InvariantCulture) + "\\";
        }

        private static string Rmc()
        {
            return Nmea("GPRMC,061450.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
        }

        private static string Line(string prefixUtc, string tagUnix, string sentence)
        {
            return prefixUtc + "," + TagBlock("c:" + tagUnix) + sentence;
        }

        private static VdrImportResult Import(string line, VdrTimeBasis basis = VdrTimeBasis.LogPrefix)
        {
            Result<VdrImportResult> result = VdrNmeaImporter.Import(new[] { line }, Options(basis));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            return result.Value;
        }

        private static Track Constant(
            string id,
            string source,
            TrackKind kind,
            double start,
            double end,
            double value)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (double t = start; t <= end + 1e-9; t += 1.0)
            {
                samples.Add(TimelineSample.Scalar(new SimTime(t), value));
            }

            return new Track(id, source, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        private static TimelineConflict DetectOne(Track a, Track b, string caseId = CaseId)
        {
            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(
                new MultiTrackTimeline(new[] { a, b }),
                null,
                caseId);
            return Assert.Single(result.Conflicts);
        }

        private static string TempPath(string fileName)
        {
            string directory = Path.Combine(
                Path.GetTempPath(),
                "mcis-w22-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture));
            Directory.CreateDirectory(directory);
            return Path.Combine(directory, fileName);
        }

        private static void DeleteBeside(string path)
        {
            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory) && Directory.Exists(directory))
            {
                Directory.Delete(directory, true);
            }
        }

        // -------------------- 1. caseId 为空拒绝写盘 --------------------

        [Fact]
        public void Detection_StillAllowsEmptyCaseId()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 5.0),
                null);

            Assert.Null(conflict.CaseId);
            Assert.Equal("C-01", conflict.Id);
        }

        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("   ")]
        [InlineData("\t")]
        public void TryToJson_WhenCaseIdMissing_FailsAndDoesNotEmitJson(string caseId)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                caseId);

            Result<string> result = ConflictJsonWriter.TryToJson(conflict);

            Assert.False(result.IsSuccess);
            Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, result.ErrorCode);
            Assert.Contains("conflict_case_id_missing", result.ErrorMessage);
            Assert.Null(result.Value);
        }

        [Fact]
        public void TryToJson_WhenCaseIdPresent_ReturnsContractJson()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0));

            Result<string> result = ConflictJsonWriter.TryToJson(conflict);

            Assert.True(result.IsSuccess, result.ErrorMessage);
            using JsonDocument document = JsonDocument.Parse(result.Value);
            Assert.Equal(CaseId, document.RootElement.GetProperty("caseId").GetString());
            Assert.Equal("kn", document.RootElement.GetProperty("deltaUnit").GetString());
        }

        [Fact]
        public void TryToJsonArray_WhenAnyCaseIdMissing_RejectsEntireArray()
        {
            TimelineConflict missing = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                null);
            TimelineConflict present = DetectOne(
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 5.0));

            Result<string> result = ConflictJsonWriter.TryToJsonArray(new[] { present, missing });

            Assert.False(result.IsSuccess);
            Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, result.ErrorCode);
            Assert.Null(result.Value);
        }

        [Fact]
        public void TryToJsonArray_EmptyOrNull_WritesEmptyArray()
        {
            Result<string> empty = ConflictJsonWriter.TryToJsonArray(new TimelineConflict[0]);
            Result<string> none = ConflictJsonWriter.TryToJsonArray(null);

            Assert.True(empty.IsSuccess, empty.ErrorMessage);
            Assert.True(none.IsSuccess, none.ErrorMessage);
            Assert.Equal("[]", empty.Value);
            Assert.Equal("[]", none.Value);
        }

        [Fact]
        public void TryWrite_WhenCaseIdMissing_DoesNotCreateFile()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                "  ");
            string path = TempPath("time-alignment.json");

            try
            {
                Result<bool> result = ConflictJsonWriter.TryWrite(path, conflict);

                Assert.False(result.IsSuccess);
                Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, result.ErrorCode);
                Assert.False(File.Exists(path));
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        [Fact]
        public void TryWrite_WhenCaseIdMissing_DoesNotChangeExistingFile()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                null);
            string path = TempPath("time-alignment.json");
            const string sentinel = "DO-NOT-TOUCH";

            try
            {
                File.WriteAllText(path, sentinel, new UTF8Encoding(false));
                Result<bool> result = ConflictJsonWriter.TryWrite(path, conflict);

                Assert.False(result.IsSuccess);
                Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, result.ErrorCode);
                Assert.Equal(sentinel, File.ReadAllText(path, new UTF8Encoding(false)));
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        [Fact]
        public void TryWrite_WhenCaseIdPresent_WritesUtf8File()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 5.0));
            string path = TempPath("time-alignment.json");

            try
            {
                Result<bool> result = ConflictJsonWriter.TryWrite(path, conflict);

                Assert.True(result.IsSuccess, result.ErrorMessage);
                Assert.True(result.Value);
                Assert.True(File.Exists(path));

                using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path, new UTF8Encoding(false)));
                JsonElement root = document.RootElement;
                Assert.Equal(CaseId, root.GetProperty("caseId").GetString());
                Assert.Equal("deg", root.GetProperty("deltaUnit").GetString());
                Assert.DoesNotContain("°", root.GetProperty("deltaUnit").GetString());
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        // -------------------- 2. 角度 deltaUnit 写 deg --------------------

        [Theory]
        [InlineData(TrackKind.Heading, 0.0, 5.0, "deg")]
        [InlineData(TrackKind.CourseOverGround, 10.0, 20.0, "deg")]
        [InlineData(TrackKind.RudderAngle, 0.0, 10.0, "deg")]
        [InlineData(TrackKind.TargetBearing, 30.0, 40.0, "deg")]
        [InlineData(TrackKind.RateOfTurn, 0.0, 12.0, "deg/min")]
        [InlineData(TrackKind.SpeedOverGround, 12.0, 13.0, "kn")]
        public void Json_DeltaUnit_UsesAsciiDegForAngularKinds(
            TrackKind kind,
            double valueA,
            double valueB,
            string expectedUnit)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/" + kind, "A", kind, 0, 10, valueA),
                Constant("B/" + kind, "B", kind, 0, 10, valueB));

            string json = ConflictJsonWriter.ToJson(conflict);
            using JsonDocument document = JsonDocument.Parse(json);
            string unit = document.RootElement.GetProperty("deltaUnit").GetString();

            Assert.Equal(expectedUnit, unit);
            Assert.DoesNotContain("°", unit);
        }

        [Fact]
        public void Json_EventTime_DeltaUnitRemainsSeconds()
        {
            Track evA = new Track(
                "A/EVT",
                "A",
                TrackKind.Other,
                null,
                new TimelineSample[0],
                new[] { new EventMarker("e1", new SimTime(100), "event", "STOP ENGINE", "A", "A/EVT") });
            Track evB = new Track(
                "B/EVT",
                "B",
                TrackKind.Other,
                null,
                new TimelineSample[0],
                new[] { new EventMarker("e2", new SimTime(165), "event", "STOP ENGINE", "B", "B/EVT") });

            TimelineConflict conflict = Assert.Single(
                ConflictDetector.DetectWithDiagnostics(
                    new MultiTrackTimeline(new[] { evA, evB }),
                    null,
                    CaseId).Conflicts);

            using JsonDocument document = JsonDocument.Parse(ConflictJsonWriter.ToJson(conflict));
            Assert.Equal("EventTime", document.RootElement.GetProperty("trackKind").GetString());
            Assert.Equal("s", document.RootElement.GetProperty("deltaUnit").GetString());
        }

        // -------------------- 3. vdr_timesource_mismatch --------------------

        [Fact]
        public void TimeSource_DifferenceGreaterThanTwoSeconds_EmitsInfoOnce_AndKeepsTagBlock()
        {
            // 前缀 06:15:30，标签块 06:15:00，相差 30 s。
            VdrImportResult result = Import(Line("2026-05-18T06:15:30.000Z", SixFifteenUnix, Rmc()));

            Track sog = Assert.Single(result.Tracks, t => t.Kind == TrackKind.SpeedOverGround);
            Assert.Equal(900.0, sog.Samples[0].Time.Seconds, 9);

            VdrDiagnostic diagnostic = Assert.Single(
                result.Diagnostics,
                d => d.Code == "vdr_timesource_mismatch");
            Assert.Equal(DiagnosticSeverity.Info, diagnostic.Severity);
            Assert.Equal(1, diagnostic.LineNumber);
            Assert.Contains("30", diagnostic.Message);
            Assert.Contains("2", diagnostic.Message);
            Assert.Equal(
                DiagnosticSeverity.Info,
                VdrDiagnostic.DefaultSeverityFor("vdr_timesource_mismatch"));
            Assert.Single(result.Diagnostics);
        }

        [Theory]
        [InlineData("2026-05-18T06:15:02.000Z", false)]
        [InlineData("2026-05-18T06:15:01.999Z", false)]
        [InlineData("2026-05-18T06:15:00.000Z", false)]
        [InlineData("2026-05-18T06:15:02.001Z", true)]
        [InlineData("2026-05-18T06:15:03.000Z", true)]
        public void TimeSource_ThresholdIsStrictlyGreaterThanTwoSeconds(string prefixUtc, bool expectMismatch)
        {
            VdrImportResult result = Import(Line(prefixUtc, SixFifteenUnix, Rmc()));
            int count = result.Diagnostics.Count(d => d.Code == "vdr_timesource_mismatch");
            Assert.Equal(expectMismatch ? 1 : 0, count);
            if (expectMismatch)
            {
                Assert.Equal(
                    DiagnosticSeverity.Info,
                    result.Diagnostics.First(d => d.Code == "vdr_timesource_mismatch").Severity);
            }

            Track sog = Assert.Single(result.Tracks, t => t.Kind == TrackKind.SpeedOverGround);
            Assert.Equal(900.0, sog.Samples[0].Time.Seconds, 9);
        }

        [Fact]
        public void TimeSource_OnlyPrefixValid_DoesNotEmitMismatch()
        {
            VdrImportResult result = Import("2026-05-18T06:15:30.000Z," + Rmc());
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
        }

        [Fact]
        public void TimeSource_OnlyTagBlockValid_DoesNotEmitMismatch()
        {
            VdrImportResult result = Import(TagBlock("c:" + SixFifteenUnix) + Rmc());
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
        }

        [Fact]
        public void TimeSource_InvalidTagWithValidPrefix_DoesNotEmitMismatch()
        {
            string line = "2026-05-18T06:15:30.000Z,\\c:" + SixFifteenUnix + "*00\\" + Rmc();
            VdrImportResult result = Import(line);

            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            Assert.Contains(result.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }

        [Fact]
        public void TimeSource_UnsupportedSentence_StillEmitsMismatchWhenBothValid()
        {
            string line = Line(
                "2026-05-18T06:15:30.000Z",
                SixFifteenUnix,
                Nmea("GPMWV,045.0,T,,,10.0,N,,"));
            VdrImportResult result = Import(line);

            Assert.Contains(result.Diagnostics, d => d.Code == "vdr_unsupported");
            VdrDiagnostic diagnostic = Assert.Single(
                result.Diagnostics,
                d => d.Code == "vdr_timesource_mismatch");
            Assert.Equal(DiagnosticSeverity.Info, diagnostic.Severity);
        }

        [Fact]
        public void TimeSource_GnssSentenceTimeBasis_StillEmitsMismatchWhenDeviceTimesDiffer()
        {
            VdrImportResult result = Import(
                Line("2026-05-18T06:15:30.000Z", SixFifteenUnix, Rmc()),
                VdrTimeBasis.GnssSentenceTime);

            Assert.Single(result.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            Track sog = Assert.Single(result.Tracks, t => t.Kind == TrackKind.SpeedOverGround);
            // 句内 GNSS 时间优先：RMC 06:14:50 → 890 s。
            Assert.Equal(890.0, sog.Samples[0].Time.Seconds, 9);
        }
    }
}
