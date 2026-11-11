using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    /// <summary>
    /// W2.3 小改项：ToJson 注释禁写盘、deltaUnit 不得为空、时间源差容差 1e-6、
    /// 诊断时间差三位小数、TryWrite 用 EvidenceItem.IsValidCaseId 校验格式。
    /// 所有演示数据均为虚构。
    /// </summary>
    public sealed class W23Tests
    {
        private const string Source = "MARY-VDR";
        private const string CaseId = "CASE-W23";
        private const string SixFifteenUnix = "1779084900"; // 2026-05-18 06:15:00 UTC

        private static readonly DateTimeOffset Epoch =
            new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);

        private static VdrImportOptions Options()
        {
            return new VdrImportOptions
            {
                SourceId = Source,
                CaseEpochUtc = Epoch,
                TimeBasis = VdrTimeBasis.LogPrefix
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

        private static string Line(string prefixUtc)
        {
            return prefixUtc + "," + TagBlock("c:" + SixFifteenUnix) + Rmc();
        }

        private static VdrImportResult Import(string line)
        {
            Result<VdrImportResult> result = VdrNmeaImporter.Import(new[] { line }, Options());
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

        private static Track PositionTrack(string id, string source, TrackKind kind, double lon, string name = null)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (int t = 0; t <= 10; t++)
            {
                samples.Add(TimelineSample.AtPosition(new SimTime(t), new GeoCoord(lon, 30.1, 0.0), name));
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

        private static IReadOnlyList<TimelineConflict> DetectMany(string caseId, params Track[] tracks)
        {
            return ConflictDetector.DetectWithDiagnostics(
                new MultiTrackTimeline(tracks),
                null,
                caseId).Conflicts;
        }

        private static string TempPath(string fileName)
        {
            string directory = Path.Combine(
                Path.GetTempPath(),
                "mcis-w23-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture));
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

        private static string FindConflictJsonSource()
        {
            DirectoryInfo dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null)
            {
                string[] candidates =
                {
                    Path.Combine(dir.FullName, "Assets/_Project/Scripts/Domain/Timeline/ConflictJson.cs"),
                    Path.Combine(dir.FullName, "unity/Assets/_Project/Scripts/Domain/Timeline/ConflictJson.cs")
                };
                for (int i = 0; i < candidates.Length; i++)
                {
                    if (File.Exists(candidates[i]))
                    {
                        return candidates[i];
                    }
                }

                dir = dir.Parent;
            }

            throw new FileNotFoundException("找不到 ConflictJson.cs 源文件。");
        }

        // -------------------- 1. ToJson / ToJsonArray XML 注释 --------------------

        [Fact]
        public void ToJsonAndToJsonArray_XmlComments_ForbidDiskWrite()
        {
            string source = File.ReadAllText(FindConflictJsonSource());
            const string required = "不得用于落盘，落盘请用 TryWrite/TryToJson";

            int toJson = source.IndexOf("public static string ToJson(TimelineConflict conflict)", StringComparison.Ordinal);
            int toJsonArray = source.IndexOf("public static string ToJsonArray(IEnumerable<TimelineConflict> conflicts)", StringComparison.Ordinal);
            int tryToJson = source.IndexOf("public static Result<string> TryToJson(TimelineConflict conflict)", StringComparison.Ordinal);
            Assert.True(toJson > 0 && toJsonArray > toJson && tryToJson > toJsonArray);

            string toJsonComment = source.Substring(0, toJson);
            toJsonComment = toJsonComment.Substring(toJsonComment.LastIndexOf("/// <summary>", StringComparison.Ordinal));
            string toJsonArrayComment = source.Substring(toJson, toJsonArray - toJson);
            toJsonArrayComment = toJsonArrayComment.Substring(toJsonArrayComment.LastIndexOf("/// <summary>", StringComparison.Ordinal));

            Assert.Contains(required, toJsonComment);
            Assert.Contains(required, toJsonArrayComment);
        }

        [Fact]
        public void ToJson_StillAllowsEmptyCaseId_ForInMemoryUse()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                null);

            using JsonDocument document = JsonDocument.Parse(ConflictJsonWriter.ToJson(conflict));
            Assert.Equal(JsonValueKind.Null, document.RootElement.GetProperty("caseId").ValueKind);
        }

        // -------------------- 2. deltaUnit 不得为空：m / kn / s / deg --------------------

        [Theory]
        [InlineData(TrackKind.Position, "m")]
        [InlineData(TrackKind.TargetPosition, "m")]
        public void Json_PositionDeltaUnit_IsMeters(TrackKind kind, string expected)
        {
            string name = kind == TrackKind.TargetPosition ? "LILY" : null;
            TimelineConflict conflict = DetectOne(
                PositionTrack("A/" + kind, "A", kind, 122.060, name),
                PositionTrack("B/" + kind, "B", kind, 122.070, name));

            Assert.True(string.IsNullOrEmpty(conflict.Unit), "内存单位保持空串，只在落盘补 m。");

            using JsonDocument memory = JsonDocument.Parse(ConflictJsonWriter.ToJson(conflict));
            Assert.Equal(expected, memory.RootElement.GetProperty("deltaUnit").GetString());
            Assert.True(memory.RootElement.GetProperty("delta").GetDouble() > 900.0);

            string path = TempPath(kind + ".json");
            try
            {
                Result<bool> written = ConflictJsonWriter.TryWrite(path, conflict);
                Assert.True(written.IsSuccess, written.ErrorMessage);
                using JsonDocument disk = JsonDocument.Parse(File.ReadAllText(path, new UTF8Encoding(false)));
                Assert.Equal(expected, disk.RootElement.GetProperty("deltaUnit").GetString());
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        [Fact]
        public void Json_SpeedAndEvent_DeltaUnitsAreKnAndS()
        {
            IReadOnlyList<TimelineConflict> conflicts = DetectMany(
                CaseId,
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                new Track(
                    "A/EVT",
                    "A",
                    TrackKind.Other,
                    null,
                    new TimelineSample[0],
                    new[] { new EventMarker("e1", new SimTime(100), "event", "COLLISION", "A", "A/EVT") }),
                new Track(
                    "B/EVT",
                    "B",
                    TrackKind.Other,
                    null,
                    new TimelineSample[0],
                    new[] { new EventMarker("e2", new SimTime(110), "event", "COLLISION", "B", "B/EVT") }));

            string path = TempPath("mix.json");
            try
            {
                Result<bool> written = ConflictJsonWriter.TryWrite(path, conflicts);
                Assert.True(written.IsSuccess, written.ErrorMessage);
                using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path, new UTF8Encoding(false)));
                JsonElement arr = document.RootElement;
                Assert.Contains(arr.EnumerateArray(), e =>
                    e.GetProperty("trackKind").GetString() == "SpeedOverGround" &&
                    e.GetProperty("deltaUnit").GetString() == "kn");
                Assert.Contains(arr.EnumerateArray(), e =>
                    e.GetProperty("trackKind").GetString() == "EventTime" &&
                    e.GetProperty("deltaUnit").GetString() == "s");
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        [Theory]
        [InlineData(TrackKind.Heading, 0.0, 5.0, "deg")]
        [InlineData(TrackKind.CourseOverGround, 10.0, 20.0, "deg")]
        [InlineData(TrackKind.RudderAngle, 0.0, 10.0, "deg")]
        [InlineData(TrackKind.TargetBearing, 30.0, 40.0, "deg")]
        [InlineData(TrackKind.RateOfTurn, 0.0, 12.0, "deg/min")]
        public void Json_AngularDeltaUnit_RemainsAsciiDeg(
            TrackKind kind,
            double valueA,
            double valueB,
            string expectedUnit)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/" + kind, "A", kind, 0, 10, valueA),
                Constant("B/" + kind, "B", kind, 0, 10, valueB));

            using JsonDocument document = JsonDocument.Parse(ConflictJsonWriter.ToJson(conflict));
            string unit = document.RootElement.GetProperty("deltaUnit").GetString();
            Assert.Equal(expectedUnit, unit);
            Assert.DoesNotContain("°", unit);
        }

        [Fact]
        public void Json_DeltaUnit_IsNeverEmpty_ForComparableKinds()
        {
            List<string> empty = new List<string>();
            foreach (TrackKind kind in new[]
            {
                TrackKind.Position,
                TrackKind.TargetPosition,
                TrackKind.SpeedOverGround,
                TrackKind.Heading,
                TrackKind.EventTime
            })
            {
                TimelineConflict conflict;
                if (kind == TrackKind.Position || kind == TrackKind.TargetPosition)
                {
                    string name = kind == TrackKind.TargetPosition ? "LILY" : null;
                    conflict = DetectOne(
                        PositionTrack("A/" + kind, "A", kind, 122.060, name),
                        PositionTrack("B/" + kind, "B", kind, 122.070, name));
                }
                else if (kind == TrackKind.EventTime)
                {
                    conflict = Assert.Single(DetectMany(
                        CaseId,
                        new Track(
                            "A/EVT",
                            "A",
                            TrackKind.Other,
                            null,
                            new TimelineSample[0],
                            new[] { new EventMarker("e1", new SimTime(100), "event", "COLLISION", "A", "A/EVT") }),
                        new Track(
                            "B/EVT",
                            "B",
                            TrackKind.Other,
                            null,
                            new TimelineSample[0],
                            new[] { new EventMarker("e2", new SimTime(110), "event", "COLLISION", "B", "B/EVT") })));
                }
                else
                {
                    // 航向默认阈值 2°，用 0/10 保证能检出；航速 12/13 kn 即可。
                    double a = kind == TrackKind.Heading ? 0.0 : 12.0;
                    double b = kind == TrackKind.Heading ? 10.0 : 13.0;
                    conflict = DetectOne(
                        Constant("A/" + kind, "A", kind, 0, 10, a),
                        Constant("B/" + kind, "B", kind, 0, 10, b));
                }

                string unit = JsonDocument.Parse(ConflictJsonWriter.ToJson(conflict))
                    .RootElement.GetProperty("deltaUnit").GetString();
                if (string.IsNullOrEmpty(unit))
                {
                    empty.Add(kind.ToString());
                }
            }

            Assert.True(empty.Count == 0, "deltaUnit 为空串的种类：" + string.Join(",", empty));
        }

        // -------------------- 3. 时间源差判定加 1e-6 容差 --------------------

        [Theory]
        [InlineData("2026-05-18T06:15:02.0000005Z")]
        [InlineData("2026-05-18T06:14:57.9999995Z")]
        public void TimeSource_WithinTolerance_NoMismatch(string prefixUtc)
        {
            VdrImportResult result = Import(Line(prefixUtc));
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            Track sog = Assert.Single(result.Tracks, t => t.Kind == TrackKind.SpeedOverGround);
            Assert.Equal(900.0, sog.Samples[0].Time.Seconds, 9);
        }

        [Theory]
        [InlineData("2026-05-18T06:15:02.0000020Z")]
        [InlineData("2026-05-18T06:14:57.9999980Z")]
        public void TimeSource_BeyondTolerance_ReportsInfo_AndTagWins(string prefixUtc)
        {
            VdrImportResult result = Import(Line(prefixUtc));
            VdrDiagnostic diagnostic = Assert.Single(result.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            Assert.Equal(DiagnosticSeverity.Info, diagnostic.Severity);
            Track sog = Assert.Single(result.Tracks, t => t.Kind == TrackKind.SpeedOverGround);
            Assert.Equal(900.0, sog.Samples[0].Time.Seconds, 9);
        }

        [Theory]
        [InlineData("2026-05-18T06:15:02.000Z")]
        [InlineData("2026-05-18T06:14:58.000Z")]
        public void TimeSource_ExactlyTwoSeconds_StillNoMismatch(string prefixUtc)
        {
            Assert.DoesNotContain(Import(Line(prefixUtc)).Diagnostics, d => d.Code == "vdr_timesource_mismatch");
        }

        [Fact]
        public void TimeSource_ToleranceConstant_MatchesConflictDetection()
        {
            Assert.Equal(1e-6, VdrNmeaImporter.TimeSourceMismatchToleranceSeconds, 12);
            Assert.Equal(2.0, VdrNmeaImporter.TimeSourceMismatchThresholdSeconds, 12);
        }

        // -------------------- 4. 诊断文字时间差保留 3 位小数 --------------------

        [Theory]
        [InlineData("2026-05-18T06:15:02.500Z", "2.500")]
        [InlineData("2026-05-18T06:15:02.0004Z", "2.000")]
        [InlineData("2026-05-18T06:16:00.000Z", "60.000")]
        [InlineData("2026-05-18T06:14:57.500Z", "2.500")]
        [InlineData("2026-05-18T06:15:02.0006Z", "2.001")]
        [InlineData("2026-05-18T06:15:02.123Z", "2.123")]
        public void TimeSource_MessageDelta_HasThreeDecimals(string prefixUtc, string expected)
        {
            VdrDiagnostic diagnostic = Assert.Single(
                Import(Line(prefixUtc)).Diagnostics,
                d => d.Code == "vdr_timesource_mismatch");
            Regex delta = new Regex(
                @"(?<![\d:.])-?" + Regex.Escape(expected) + @"(?!\d)",
                RegexOptions.CultureInvariant);
            Assert.True(
                delta.IsMatch(diagnostic.Message),
                "诊断文字应含 3 位小数时间差「" + expected + "」：" + diagnostic.Message);
        }

        // -------------------- 5. 共享 caseId 校验器 --------------------

        public static IEnumerable<object[]> InvalidCaseIds()
        {
            foreach (string value in new[]
            {
                "AB", "a", "案件01", "CASE 01", "CASE/01", "CASE:01", "CASE#01",
                " CASE-01", "CASE-01 ", "CASE-01\n", "\tCASE-01", "ＣＡＳＥ01", "CASE-0１",
                "CASÉ-01", "CASE-01\u200B"
            })
            {
                yield return new object[] { value };
            }
        }

        public static IEnumerable<object[]> ValidCaseIds()
        {
            foreach (string value in new[]
            {
                "abc", "ABC", "123", "CASE-2026-LN01", "a.b_c-1", "...", "---", "YANGZE22.2026_01"
            })
            {
                yield return new object[] { value };
            }
        }

        public static IEnumerable<object[]> BlankCaseIds()
        {
            foreach (string value in new[] { null, "", "   ", "\t", "\n", "\u3000" })
            {
                yield return new object[] { value };
            }
        }

        [Theory]
        [MemberData(nameof(InvalidCaseIds))]
        public void InvalidCaseId_RejectedBySharedValidator(string caseId)
        {
            Assert.False(EvidenceItem.IsValidCaseId(caseId), "共享校验器应拒：" + caseId);
        }

        [Theory]
        [MemberData(nameof(ValidCaseIds))]
        public void ValidCaseId_AcceptedBySharedValidator(string caseId)
        {
            Assert.True(EvidenceItem.IsValidCaseId(caseId));
        }

        [Theory]
        [MemberData(nameof(InvalidCaseIds))]
        public void TryToJson_WhenCaseIdInvalid_ReturnsInvalidCode(string caseId)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                caseId);

            Result<string> one = ConflictJsonWriter.TryToJson(conflict);
            Result<string> many = ConflictJsonWriter.TryToJsonArray(new[] { conflict });

            Assert.False(one.IsSuccess);
            Assert.Equal(ConflictJsonWriter.InvalidCaseIdCode, one.ErrorCode);
            Assert.Contains("conflict_case_id_invalid", one.ErrorMessage);
            Assert.Null(one.Value);
            Assert.False(many.IsSuccess);
            Assert.Equal(ConflictJsonWriter.InvalidCaseIdCode, many.ErrorCode);
        }

        [Theory]
        [MemberData(nameof(InvalidCaseIds))]
        public void TryWrite_WhenCaseIdInvalid_DoesNotCreateFileOrDirectory(string caseId)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                caseId);
            string root = Path.Combine(
                Path.GetTempPath(),
                "mcis-w23-invalid-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture));
            string path = Path.Combine(root, "new", "one.json");

            try
            {
                Result<bool> result = ConflictJsonWriter.TryWrite(path, conflict);
                Assert.False(result.IsSuccess);
                Assert.Equal(ConflictJsonWriter.InvalidCaseIdCode, result.ErrorCode);
                Assert.False(Directory.Exists(root), "拒绝写盘时不应创建目录或文件");
            }
            finally
            {
                if (Directory.Exists(root))
                {
                    Directory.Delete(root, true);
                }
            }
        }

        [Fact]
        public void TryWrite_WhenCaseIdInvalid_DoesNotChangeExistingFile()
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                "案件 01");
            string path = TempPath("time-alignment.json");
            const string sentinel = "[\"旧内容\"]";

            try
            {
                File.WriteAllText(path, sentinel, new UTF8Encoding(false));
                DateTime before = File.GetLastWriteTimeUtc(path);
                Result<bool> result = ConflictJsonWriter.TryWrite(path, conflict);

                Assert.False(result.IsSuccess);
                Assert.Equal(ConflictJsonWriter.InvalidCaseIdCode, result.ErrorCode);
                Assert.Equal(sentinel, File.ReadAllText(path, new UTF8Encoding(false)));
                Assert.Equal(before, File.GetLastWriteTimeUtc(path));
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        [Fact]
        public void TryWriteArray_WhenOneCaseIdInvalid_RejectsWholeArray()
        {
            TimelineConflict valid = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                CaseId);
            TimelineConflict invalid = DetectOne(
                Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 5.0),
                "CASE 01");
            string path = TempPath("mixed.json");

            try
            {
                Result<bool> result = ConflictJsonWriter.TryWrite(path, new[] { valid, invalid });
                Assert.False(result.IsSuccess);
                Assert.Equal(ConflictJsonWriter.InvalidCaseIdCode, result.ErrorCode);
                Assert.False(File.Exists(path));
            }
            finally
            {
                DeleteBeside(path);
            }
        }

        [Theory]
        [MemberData(nameof(BlankCaseIds))]
        public void TryWrite_WhenCaseIdBlank_StillMissingCode(string caseId)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                caseId);
            string root = Path.Combine(
                Path.GetTempPath(),
                "mcis-w23-blank-" + Guid.NewGuid().ToString("N", CultureInfo.InvariantCulture));
            string path = Path.Combine(root, "x", "b.json");

            try
            {
                Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, ConflictJsonWriter.TryToJson(conflict).ErrorCode);
                Assert.Equal(
                    ConflictJsonWriter.MissingCaseIdCode,
                    ConflictJsonWriter.TryToJsonArray(new[] { conflict }).ErrorCode);
                Result<bool> written = ConflictJsonWriter.TryWrite(path, conflict);
                Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, written.ErrorCode);
                Assert.False(Directory.Exists(root));
            }
            finally
            {
                if (Directory.Exists(root))
                {
                    Directory.Delete(root, true);
                }
            }
        }

        [Theory]
        [MemberData(nameof(ValidCaseIds))]
        public void TryWrite_WhenCaseIdValid_WritesFile(string caseId)
        {
            TimelineConflict conflict = DetectOne(
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0),
                caseId);
            string path = TempPath("ok.json");

            try
            {
                Result<bool> result = ConflictJsonWriter.TryWrite(path, conflict);
                Assert.True(result.IsSuccess, result.ErrorMessage);
                using JsonDocument document = JsonDocument.Parse(File.ReadAllText(path, new UTF8Encoding(false)));
                Assert.Equal(caseId, document.RootElement.GetProperty("caseId").GetString());
                Assert.Equal("kn", document.RootElement.GetProperty("deltaUnit").GetString());
            }
            finally
            {
                DeleteBeside(path);
            }
        }
    }
}
