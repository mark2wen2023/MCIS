using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    /// <summary>
    /// W2.1 返修回归（D08/D09/D10、行长裁定与冲突 JSON 合同写盘）。
    /// 所有演示数据均为虚构。
    /// </summary>
    public sealed class W21RegressionTests
    {
        private const string Source = "MARY-VDR";
        private const string SixFifteenUnix = "1779084900"; // 2026-05-18 06:15:00 UTC（虚构）

        private static readonly DateTimeOffset Epoch =
            new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);

        private static VdrImportOptions Options()
        {
            return new VdrImportOptions
            {
                SourceId = Source,
                CaseEpochUtc = Epoch
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

        private static string Rmc(string time, string date)
        {
            return Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "GPRMC,{0},A,3006.0000,N,12203.6000,E,12.0,45.0,{1},,,A",
                time,
                date));
        }

        private static string RmcOfLength(int targetLength)
        {
            string body = "GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A";
            int pad = targetLength - (body.Length + 4) - 1; // 额外字段 ",XXX"
            Assert.True(pad >= 1);
            return Nmea(body + "," + new string('P', pad));
        }

        private static string Ttm(int targetNumber, double distance, double bearing, string unit, string name)
        {
            return Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "RATTM,{0:00},{1:0.00},{2:0.0},{3},0.0,000.0,T,0.00,0.0,N,{4},T,,061500.00",
                targetNumber,
                distance,
                bearing,
                unit,
                name));
        }

        private static VdrImportResult Import(params string[] lines)
        {
            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, Options());
            Assert.True(result.IsSuccess, result.ErrorMessage);
            return result.Value;
        }

        private static double[] SogTimes(VdrImportResult result)
        {
            Track sog = result.Tracks.FirstOrDefault(t => t.Kind == TrackKind.SpeedOverGround);
            return sog == null ? new double[0] : sog.Samples.Select(s => s.Time.Seconds).ToArray();
        }

        private static Track Constant(
            string id,
            string source,
            TrackKind kind,
            double start,
            double end,
            double value,
            string text = null)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (double t = start; t <= end + 1e-9; t += 1.0)
            {
                samples.Add(TimelineSample.Scalar(new SimTime(t), value, text));
            }

            return new Track(id, source, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        // -------------------- D08 时间源优先级 --------------------

        [Fact]
        public void D08_LogPrefixPlusValidTagBlock_TagBlockWins_NoInvalidWarning()
        {
            string line = "2026-05-18T06:15:30.000Z," +
                          TagBlock("c:" + SixFifteenUnix) +
                          Rmc("061450.00", "180526");

            VdrImportResult result = Import(line);

            Assert.Equal(new[] { 900.0 }, SogTimes(result));
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_logprefix_invalid");
        }

        [Fact]
        public void D08_LogPrefixPlusInvalidTagBlock_FallsBackToPrefix_WithWarning()
        {
            string line = "2026-05-18T06:15:30.000Z,\\c:" + SixFifteenUnix + "*00\\" +
                          Rmc("061450.00", "180526");

            VdrImportResult result = Import(line);

            Assert.Equal(new[] { 930.0 }, SogTimes(result));
            VdrDiagnostic diagnostic = Assert.Single(
                result.Diagnostics,
                d => d.Code == "vdr_tagblock_invalid");
            Assert.Equal(DiagnosticSeverity.Warning, diagnostic.Severity);
            Assert.Contains("日志前缀", diagnostic.Message);
        }

        [Fact]
        public void D08_InvalidPrefixPlusInvalidTagBlock_BothDiagnostics_SentenceTime()
        {
            string line = "not-a-time,\\c:" + SixFifteenUnix + "*00\\" +
                          Rmc("061450.00", "180526");

            VdrImportResult result = Import(line);

            Assert.Equal(new[] { 890.0 }, SogTimes(result));
            Assert.Single(result.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
            Assert.Single(result.Diagnostics, d => d.Code == "vdr_logprefix_invalid");
            Assert.Equal(
                DiagnosticSeverity.Warning,
                result.Diagnostics.First(d => d.Code == "vdr_logprefix_invalid").Severity);
            Assert.Contains(
                "回落到句内时间",
                result.Diagnostics.First(d => d.Code == "vdr_tagblock_invalid").Message);
        }

        [Fact]
        public void D08_InvalidPrefixOnly_FallsBackToSentence_WithWarning()
        {
            string line = "not-a-time," + Rmc("061450.00", "180526");

            VdrImportResult result = Import(line);

            Assert.Equal(new[] { 890.0 }, SogTimes(result));
            VdrDiagnostic diagnostic = Assert.Single(
                result.Diagnostics,
                d => d.Code == "vdr_logprefix_invalid");
            Assert.Equal(DiagnosticSeverity.Warning, diagnostic.Severity);
            Assert.Contains("not-a-time", diagnostic.Message);
            Assert.Contains("回落到句内时间", diagnostic.Message);
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }

        [Fact]
        public void D08_TagBlockBeforeLogPrefix_IsAlsoRecognized()
        {
            string line = TagBlock("c:" + SixFifteenUnix) +
                          "2026-05-18T06:15:30.000Z," +
                          Rmc("061450.00", "180526");

            VdrImportResult result = Import(line);

            Assert.Equal(new[] { 900.0 }, SogTimes(result));
            Assert.DoesNotContain(result.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }

        // -------------------- D09 相对方位 --------------------

        [Fact]
        public void D09_RelativeBearingWithoutHeading_IsKeptRelative_WithDiagnostic()
        {
            VdrImportResult result = Import(
                "2026-05-18T06:15:00.000Z," + Ttm(1, 1.2, 30.0, "R", "LILY"));

            Track trueBearing = result.Tracks.FirstOrDefault(
                t => t.Id == Source + "/TTM01/TargetBearing");
            Assert.True(
                trueBearing == null || trueBearing.Samples.Count == 0,
                "相对方位无船首向时不得写入真方位轨。");

            Track relative = Assert.Single(
                result.Tracks,
                t => t.Id == Source + "/TTM01/TargetBearing/REL");
            Assert.Equal(TrackKind.TargetBearing, relative.Kind);
            Assert.Equal(BearingReference.Relative, relative.BearingReference);
            Assert.Single(relative.Samples);
            Assert.Equal(30.0, relative.Samples[0].Value, 9);

            VdrDiagnostic diagnostic = Assert.Single(
                result.Diagnostics,
                d => d.Code == "vdr_relative_bearing_no_heading");
            Assert.Equal(DiagnosticSeverity.Warning, diagnostic.Severity);
            Assert.Contains("真方位 NotAvailable", diagnostic.Message);
            Assert.Contains("30", diagnostic.Message);
            Assert.Contains("第 1 行", diagnostic.Message);
        }

        [Fact]
        public void D09_HeadingThenRelativeBearing_ConvertsToTrueBearing()
        {
            VdrImportResult result = Import(
                "2026-05-18T06:15:00.000Z," + Nmea("GPHDT,45.0,T"),
                "2026-05-18T06:15:10.000Z," + Ttm(1, 1.2, 30.0, "R", "LILY"));

            Track trueBearing = Assert.Single(
                result.Tracks,
                t => t.Id == Source + "/TTM01/TargetBearing");
            Assert.Equal(BearingReference.True, trueBearing.BearingReference);
            Assert.Single(trueBearing.Samples);
            Assert.Equal(75.0, trueBearing.Samples[0].Value, 9);
            Assert.DoesNotContain(
                result.Tracks,
                t => t.Id == Source + "/TTM01/TargetBearing/REL");
            Assert.DoesNotContain(
                result.Diagnostics,
                d => d.Code == "vdr_relative_bearing_no_heading");
        }

        [Fact]
        public void D09_RelativeBeforeHeading_IsNotBackfilled_WhenHeadingAppears()
        {
            VdrImportResult result = Import(
                "2026-05-18T06:15:00.000Z," + Ttm(1, 1.2, 30.0, "R", "LILY"),
                "2026-05-18T06:15:10.000Z," + Nmea("GPHDT,45.0,T"),
                "2026-05-18T06:15:20.000Z," + Ttm(1, 1.2, 30.0, "R", "LILY"));

            Track relative = Assert.Single(
                result.Tracks,
                t => t.Id == Source + "/TTM01/TargetBearing/REL");
            Assert.Single(relative.Samples);
            Assert.Equal(900.0, relative.Samples[0].Time.Seconds, 9);
            Assert.Equal(30.0, relative.Samples[0].Value, 9);

            Track trueBearing = Assert.Single(
                result.Tracks,
                t => t.Id == Source + "/TTM01/TargetBearing");
            Assert.Single(trueBearing.Samples);
            Assert.Equal(920.0, trueBearing.Samples[0].Time.Seconds, 9);
            Assert.Equal(75.0, trueBearing.Samples[0].Value, 9);
        }

        [Fact]
        public void D09_TrackTransforms_PreserveBearingReference()
        {
            Track relative = new Track(
                "A/TTM01/TargetBearing/REL",
                "A",
                TrackKind.TargetBearing,
                "°",
                new[] { TimelineSample.Scalar(new SimTime(0), 30.0) },
                null,
                null,
                BearingReference.Relative);

            Assert.Equal(BearingReference.Relative, relative.WithTimeShift(5.0).BearingReference);
            Assert.Equal(
                BearingReference.Relative,
                relative.WithCalibration(CalibrationStatus.Calibrated, -2.0).BearingReference);

            Track trueTrack = Constant(
                "B/TTM01/TargetBearing", "B", TrackKind.TargetBearing, 0, 1, 10.0);
            Assert.Equal(BearingReference.True, trueTrack.BearingReference);
        }

        [Fact]
        public void D09_ConflictDetector_SkipsRelativeTrack_AndReportsNotAvailable()
        {
            Track trueTrack = Constant(
                "A/TTM01/TargetBearing", "A", TrackKind.TargetBearing, 0, 10, 30.0, "LILY");
            Track relative = new Track(
                "B/TTM01/TargetBearing/REL",
                "B",
                TrackKind.TargetBearing,
                "°",
                new[] { TimelineSample.Scalar(new SimTime(0), 30.0, "LILY") },
                null,
                null,
                BearingReference.Relative);

            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(
                new MultiTrackTimeline(new[] { trueTrack, relative }));

            Assert.Empty(result.Conflicts);
            Assert.DoesNotContain(
                result.Conflicts,
                c => c.TrackIdA == relative.Id || c.TrackIdB == relative.Id);

            ConflictDiagnostic diagnostic = Assert.Single(
                result.Diagnostics,
                d => d.TrackId == relative.Id);
            Assert.Equal(ConflictDiagnostic.NotAvailableCode, diagnostic.Code);
            Assert.Equal("bearing_relative_no_heading", diagnostic.Reason);
            Assert.Contains("真方位", diagnostic.Message);
        }

        // -------------------- D10 NaN / ±∞ --------------------

        [Theory]
        [InlineData("NaN")]
        [InlineData("+Inf")]
        [InlineData("-Inf")]
        public void D10_ScalarNonFinite_EmitsInvalidNumberNotAvailable(string token)
        {
            double bad;
            switch (token)
            {
                case "NaN":
                    bad = double.NaN;
                    break;
                case "+Inf":
                    bad = double.PositiveInfinity;
                    break;
                default:
                    bad = double.NegativeInfinity;
                    break;
            }

            Track a = Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 1.0);
            Track b = new Track(
                "B/SOG",
                "B",
                TrackKind.SpeedOverGround,
                "kn",
                new[]
                {
                    TimelineSample.Scalar(new SimTime(0), bad),
                    TimelineSample.Scalar(new SimTime(10), bad)
                });

            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(
                new MultiTrackTimeline(new[] { a, b }));

            Assert.Empty(result.Conflicts);
            ConflictDiagnostic diagnostic = Assert.Single(result.Diagnostics);
            Assert.Equal(ConflictDiagnostic.NotAvailableCode, diagnostic.Code);
            Assert.Equal(ConflictDiagnostic.InvalidNumberReason, diagnostic.Reason);
            Assert.True(diagnostic.Range.HasValue);
            Assert.Equal(0.0, diagnostic.Range.Value.Start.Seconds, 9);
            Assert.Equal(10.0, diagnostic.Range.Value.End.Seconds, 9);
            Assert.Contains(a.Id, diagnostic.Message);
            Assert.Contains(b.Id, diagnostic.Message);
            Assert.Contains(ConflictDiagnostic.InvalidNumberReason, diagnostic.Message);
        }

        [Fact]
        public void D10_PartialNaN_BreaksConflictRun_AndMergesInvalidRange()
        {
            List<TimelineSample> bSamples = new List<TimelineSample>();
            for (int t = 0; t <= 20; t++)
            {
                if (t == 11)
                {
                    // 制造 10s..11s 的连续无效区间（10s 为 NaN，11s 由相邻 NaN 插值得到）。
                    continue;
                }

                bSamples.Add(TimelineSample.Scalar(
                    new SimTime(t),
                    t == 10 ? double.NaN : 5.0));
            }

            Track a = Constant("A/HDG", "A", TrackKind.Heading, 0, 20, 0.0);
            Track b = new Track(
                "B/HDG",
                "B",
                TrackKind.Heading,
                "°",
                bSamples);

            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(
                new MultiTrackTimeline(new[] { a, b }));

            Assert.Equal(2, result.Conflicts.Count);
            Assert.Equal(0.0, result.Conflicts[0].Range.Start.Seconds, 9);
            Assert.Equal(9.0, result.Conflicts[0].Range.End.Seconds, 9);
            Assert.Equal(12.0, result.Conflicts[1].Range.Start.Seconds, 9);
            Assert.Equal(20.0, result.Conflicts[1].Range.End.Seconds, 9);

            ConflictDiagnostic diagnostic = Assert.Single(result.Diagnostics);
            Assert.Equal(ConflictDiagnostic.InvalidNumberReason, diagnostic.Reason);
            Assert.True(diagnostic.Range.HasValue);
            Assert.Equal(10.0, diagnostic.Range.Value.Start.Seconds, 9);
            Assert.Equal(11.0, diagnostic.Range.Value.End.Seconds, 9);
            Assert.Contains("inv_invalid_number", diagnostic.Message);
        }

        // -------------------- 行长裁定：>80（不含 CRLF）告警 --------------------

        [Theory]
        [InlineData(80, false)]
        [InlineData(81, true)]
        [InlineData(82, true)]
        [InlineData(83, true)]
        public void LineLength_Over80ExcludingCrLf_Warns_ButStillParses(int length, bool expectWarning)
        {
            string sentence = RmcOfLength(length);
            Assert.Equal(length, sentence.Length);

            VdrImportResult result = Import("2026-05-18T06:15:00.000Z," + sentence);

            Assert.Single(SogTimes(result));
            List<VdrDiagnostic> warnings = result.Diagnostics
                .Where(d => d.Code == "vdr_line_too_long")
                .ToList();
            Assert.Equal(expectWarning ? 1 : 0, warnings.Count);
            if (expectWarning)
            {
                Assert.Equal(DiagnosticSeverity.Warning, warnings[0].Severity);
                Assert.Contains("不含 CRLF", warnings[0].Message);
                Assert.Contains("上限 80", warnings[0].Message);
            }
        }

        // -------------------- 冲突 JSON 合同写盘 --------------------

        [Fact]
        public void Json_Unresolved_ContainsResolvedByAndResolvedAtNull_AllKeysInContract()
        {
            TimelineConflict conflict = CreateConflict();
            string json = ConflictJsonWriter.ToJson(conflict);

            using JsonDocument document = JsonDocument.Parse(json);
            JsonElement root = document.RootElement;

            Assert.Equal("Open", root.GetProperty("status").GetString());
            Assert.Equal("RuleEngine", root.GetProperty("detectedBy").GetString());
            Assert.Equal(JsonValueKind.Null, root.GetProperty("vesselId").ValueKind);
            Assert.Equal(JsonValueKind.Null, root.GetProperty("caseId").ValueKind);
            Assert.Equal(JsonValueKind.Null, root.GetProperty("resolvedBy").ValueKind);
            Assert.Equal(JsonValueKind.Null, root.GetProperty("resolvedAt").ValueKind);
            Assert.False(root.TryGetProperty("resolution", out _));
            Assert.Equal(conflict.PeakTime.Seconds, root.GetProperty("timeSec").GetDouble(), 9);
            Assert.Equal(conflict.MaxDifference, root.GetProperty("delta").GetDouble(), 9);
            Assert.Equal(conflict.Unit, root.GetProperty("deltaUnit").GetString());

            AssertTopLevelKeysInContract(root);
            AssertObservationKeysInContract(root.GetProperty("a"));
            AssertObservationKeysInContract(root.GetProperty("b"));
        }

        [Fact]
        public void Json_Resolved_WritesResolutionResolvedByAndIsoResolvedAtWithOffset()
        {
            DateTimeOffset resolvedAt =
                new DateTimeOffset(2026, 5, 20, 10, 0, 0, TimeSpan.FromHours(8));
            TimelineConflict conflict = CreateConflict()
                .WithCaseId("CASE-W21")
                .WithResolution(
                    ConflictStatus.AcceptedAsIs,
                    "待定·采信 AIS",
                    "调查员甲",
                    resolvedAt);

            using JsonDocument document = JsonDocument.Parse(
                ConflictJsonWriter.ToJson(conflict));
            JsonElement root = document.RootElement;

            Assert.Equal("CASE-W21", root.GetProperty("caseId").GetString());
            Assert.Equal("AcceptedAsIs", root.GetProperty("status").GetString());
            Assert.Equal("待定·采信 AIS", root.GetProperty("resolution").GetString());
            Assert.Equal("调查员甲", root.GetProperty("resolvedBy").GetString());
            string text = root.GetProperty("resolvedAt").GetString();
            Assert.EndsWith("+08:00", text);
            DateTimeOffset parsed = DateTimeOffset.Parse(
                text,
                CultureInfo.InvariantCulture);
            Assert.Equal(resolvedAt, parsed);
            AssertTopLevelKeysInContract(root);
        }

        [Fact]
        public void Json_NonFiniteDeltaIsNull_AndStringsAreEscaped()
        {
            TimelineConflict conflict = new TimelineConflict(
                "C-01",
                TrackKind.SpeedOverGround,
                "SpeedOverGround",
                "A",
                "A/SOG",
                "B",
                "B/SOG",
                new TimeRange(new SimTime(0), new SimTime(1)),
                new SimTime(0),
                1.0,
                2.0,
                double.NaN,
                0.3,
                "kn",
                "quote\" back\\slash\nnext-line");

            using JsonDocument document = JsonDocument.Parse(
                ConflictJsonWriter.ToJson(conflict));
            JsonElement root = document.RootElement;

            Assert.Equal(JsonValueKind.Null, root.GetProperty("delta").ValueKind);
            Assert.Equal(
                "quote\" back\\slash\nnext-line",
                root.GetProperty("summary").GetString());
        }

        [Fact]
        public void Json_Array_And_StatusEnum_MatchContract()
        {
            TimelineConflict first = CreateConflict();
            TimelineConflict second = CreateConflict().WithCaseId("CASE-W21");

            using JsonDocument array = JsonDocument.Parse(
                ConflictJsonWriter.ToJsonArray(new[] { first, second }));
            Assert.Equal(2, array.RootElement.GetArrayLength());

            using JsonDocument schema = JsonDocument.Parse(File.ReadAllText(FindContractFile()));
            HashSet<string> contractStatuses = schema.RootElement
                .GetProperty("properties")
                .GetProperty("status")
                .GetProperty("enum")
                .EnumerateArray()
                .Select(x => x.GetString())
                .ToHashSet(StringComparer.Ordinal);
            HashSet<string> enumNames = Enum.GetNames(typeof(ConflictStatus))
                .ToHashSet(StringComparer.Ordinal);

            Assert.True(
                contractStatuses.SetEquals(enumNames),
                "ConflictStatus 与合同 status 枚举不一致：合同=[" +
                string.Join(", ", contractStatuses) + "]，实现=[" +
                string.Join(", ", enumNames) + "]。");
        }

        private static TimelineConflict CreateConflict()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0)
            });
            return Assert.Single(ConflictDetector.Detect(timeline));
        }

        private static void AssertTopLevelKeysInContract(JsonElement root)
        {
            using JsonDocument schema = JsonDocument.Parse(File.ReadAllText(FindContractFile()));
            HashSet<string> keys = schema.RootElement
                .GetProperty("properties")
                .EnumerateObject()
                .Select(p => p.Name)
                .ToHashSet(StringComparer.Ordinal);

            foreach (JsonProperty property in root.EnumerateObject())
            {
                Assert.Contains(property.Name, keys);
            }

            foreach (string required in schema.RootElement
                .GetProperty("required")
                .EnumerateArray()
                .Select(x => x.GetString()))
            {
                Assert.True(
                    root.TryGetProperty(required, out _),
                    "合同必填键缺失：" + required);
            }
        }

        private static void AssertObservationKeysInContract(JsonElement observation)
        {
            using JsonDocument schema = JsonDocument.Parse(File.ReadAllText(FindContractFile()));
            HashSet<string> keys = schema.RootElement
                .GetProperty("$defs")
                .GetProperty("observation")
                .GetProperty("properties")
                .EnumerateObject()
                .Select(p => p.Name)
                .ToHashSet(StringComparer.Ordinal);

            foreach (JsonProperty property in observation.EnumerateObject())
            {
                Assert.Contains(property.Name, keys);
            }
        }

        private static string FindContractFile()
        {
            string directory = AppContext.BaseDirectory;
            for (int i = 0; i < 12 && !string.IsNullOrEmpty(directory); i++)
            {
                string candidate = Path.Combine(
                    directory,
                    "contracts",
                    "schemas",
                    "conflict.schema.json");
                if (File.Exists(candidate))
                {
                    return candidate;
                }

                DirectoryInfo parent = Directory.GetParent(directory);
                directory = parent == null ? null : parent.FullName;
            }

            throw new FileNotFoundException(
                "找不到 contracts/schemas/conflict.schema.json（从 AppContext.BaseDirectory 向上查找）。");
        }
    }
}
