using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// W2.2 复测（2026-11-11）：DEFECTS/W2.md「W2.1 架构师验收」「W2.2 裁定」三项。演示数据全部虚构。
    /// </summary>
    public class W22CaseIdTests : IDisposable
    {
        private readonly string _dir = Path.Combine(Path.GetTempPath(), "w22-acc-" + Guid.NewGuid().ToString("N"));

        public void Dispose()
        {
            if (Directory.Exists(_dir))
            {
                Directory.Delete(_dir, true);
            }
        }

        private static IReadOnlyList<TimelineConflict> Detect(string caseId)
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/SOG", "MARY-VDR", TrackKind.SpeedOverGround, 0, 10, 12.0),
                W2AccFixture.Constant("B/SOG", "VTS-AIS", TrackKind.SpeedOverGround, 0, 10, 13.0),
                W2AccFixture.Constant("A/HDG", "MARY-VDR", TrackKind.Heading, 0, 10, 10.0),
                W2AccFixture.Constant("B/HDG", "VTS-AIS", TrackKind.Heading, 0, 10, 20.0)
            });
            return ConflictDetector.DetectWithDiagnostics(tl, null, caseId).Conflicts;
        }

        public static IEnumerable<object[]> BlankCaseIds()
        {
            yield return new object[] { null };
            yield return new object[] { "" };
            yield return new object[] { "   " };
            yield return new object[] { "\t" };
            yield return new object[] { "\n" };
            yield return new object[] { "\r\n\t " };
            yield return new object[] { "\u3000" };
        }

        [Theory]
        [MemberData(nameof(BlankCaseIds))]
        public void DetectionAllowsBlankCaseId_ButTryToJsonRejects(string caseId)
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(caseId);
            Assert.Equal(2, conflicts.Count);
            Result<string> one = ConflictJsonWriter.TryToJson(conflicts[0]);
            Assert.False(one.IsSuccess);
            Assert.Equal("conflict_case_id_missing", one.ErrorCode);
            Assert.Equal(ConflictJsonWriter.MissingCaseIdCode, one.ErrorCode);
            Result<string> many = ConflictJsonWriter.TryToJsonArray(conflicts);
            Assert.False(many.IsSuccess);
            Assert.Equal("conflict_case_id_missing", many.ErrorCode);
        }

        [Theory]
        [MemberData(nameof(BlankCaseIds))]
        public void TryWrite_Rejects_LeavesNoFile(string caseId)
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(caseId);
            string single = Path.Combine(_dir, "sub", "one.json");
            string array = Path.Combine(_dir, "sub", "all.json");
            Result<bool> r1 = ConflictJsonWriter.TryWrite(single, conflicts[0]);
            Result<bool> r2 = ConflictJsonWriter.TryWrite(array, conflicts);
            Assert.False(r1.IsSuccess);
            Assert.False(r2.IsSuccess);
            Assert.Equal("conflict_case_id_missing", r1.ErrorCode);
            Assert.Equal("conflict_case_id_missing", r2.ErrorCode);
            Assert.False(File.Exists(single));
            Assert.False(File.Exists(array));
            Assert.Empty(Directory.Exists(_dir) ? Directory.GetFiles(_dir, "*", SearchOption.AllDirectories) : new string[0]);
        }

        [Fact]
        public void TryWrite_Rejected_DoesNotTouchExistingFile()
        {
            Directory.CreateDirectory(_dir);
            string path = Path.Combine(_dir, "time-alignment.json");
            File.WriteAllText(path, "[\"旧内容\"]", new UTF8Encoding(false));
            DateTime before = File.GetLastWriteTimeUtc(path);
            Result<bool> r = ConflictJsonWriter.TryWrite(path, Detect(" "));
            Assert.False(r.IsSuccess);
            Assert.Equal("[\"旧内容\"]", File.ReadAllText(path));
            Assert.Equal(before, File.GetLastWriteTimeUtc(path));
        }

        [Fact]
        public void MixedArray_OneBlank_RejectsWholeArray()
        {
            List<TimelineConflict> mixed = Detect(W2AccFixture.CaseId).ToList();
            mixed[1] = mixed[1].WithCaseId("\t");
            string path = Path.Combine(_dir, "mixed.json");
            Result<bool> r = ConflictJsonWriter.TryWrite(path, mixed);
            Assert.False(r.IsSuccess);
            Assert.Equal("conflict_case_id_missing", r.ErrorCode);
            Assert.Contains("C-02", r.ErrorMessage);
            Assert.False(File.Exists(path));
        }

        [Fact]
        public void ValidCaseId_TryWrite_WritesUtf8NoBom_ContractValid()
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(W2AccFixture.CaseId);
            string path = Path.Combine(_dir, "a", "b", "time-alignment.json");
            Result<bool> r = ConflictJsonWriter.TryWrite(path, conflicts);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            byte[] bytes = File.ReadAllBytes(path);
            Assert.False(bytes.Length >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF, "不应带 BOM");
            JsonElement arr = JsonDocument.Parse(Encoding.UTF8.GetString(bytes)).RootElement;
            Assert.Equal(2, arr.GetArrayLength());
            foreach (JsonElement e in arr.EnumerateArray())
            {
                List<string> errors = MiniSchema.Validate(e.GetRawText());
                Assert.True(errors.Count == 0, string.Join("\n", errors));
                Assert.Equal(W2AccFixture.CaseId, e.GetProperty("caseId").GetString());
            }

            string single = Path.Combine(_dir, "one.json");
            Assert.True(ConflictJsonWriter.TryWrite(single, conflicts[0]).IsSuccess);
            Assert.Empty(MiniSchema.Validate(File.ReadAllText(single)));
            Assert.Equal(ConflictJsonWriter.TryToJson(conflicts[0]).Value, File.ReadAllText(single));
        }

        [Fact]
        public void ToJson_InMemoryDebug_StillAllowsNullCaseId()
        {
            string json = ConflictJsonWriter.ToJson(Detect(null)[0]);
            Assert.Equal(JsonValueKind.Null, JsonDocument.Parse(json).RootElement.GetProperty("caseId").ValueKind);
        }
    }

    public class W22DegreeUnitTests
    {
        private static Track Named(string id, string src, TrackKind kind, double v)
        {
            // 目标类轨道按样本 Text（目标名）跨源配对。
            return W2AccFixture.ScalarTrack(id, src, kind,
                Enumerable.Range(0, 11).Select(t => W2AccFixture.S(t, v, "LILY")).ToArray());
        }

        private static TimelineConflict One(TrackKind kind, double a, double b)
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                Named("A/" + kind, "A-SRC", kind, a),
                Named("B/" + kind, "B-SRC", kind, b)
            });
            return Assert.Single(ConflictDetector.DetectWithDiagnostics(tl, null, W2AccFixture.CaseId).Conflicts);
        }

        [Theory]
        [InlineData(TrackKind.Heading, 359.0, 5.0, "deg")]
        [InlineData(TrackKind.CourseOverGround, 10.0, 20.0, "deg")]
        [InlineData(TrackKind.RudderAngle, -5.0, 5.0, "deg")]
        [InlineData(TrackKind.TargetBearing, 10.0, 20.0, "deg")]
        [InlineData(TrackKind.RateOfTurn, 0.0, 10.0, "deg/min")]
        [InlineData(TrackKind.SpeedOverGround, 12.0, 13.0, "kn")]
        [InlineData(TrackKind.TargetRange, 1.0, 2.0, "nm")]
        public void DeltaUnit_OnDisk_IsAscii(TrackKind kind, double a, double b, string expected)
        {
            TimelineConflict c = One(kind, a, b);
            Result<string> json = ConflictJsonWriter.TryToJson(c);
            Assert.True(json.IsSuccess, json.ErrorMessage);
            JsonElement e = JsonDocument.Parse(json.Value).RootElement;
            string unit = e.GetProperty("deltaUnit").GetString();
            Assert.Equal(expected, unit);
            Assert.True(unit.All(ch => ch < 128), "deltaUnit 含非 ASCII：" + unit);
            Assert.Empty(MiniSchema.Validate(json.Value));
        }

        [Fact]
        public void InMemoryUnit_StaysDegreeSign()
        {
            Assert.Equal("°", One(TrackKind.Heading, 0, 10).Unit);
            Assert.Equal("°/min", One(TrackKind.RateOfTurn, 0, 10).Unit);
        }

        [Fact]
        public void EventTime_DeltaUnit_IsSeconds()
        {
            Track a = new Track("A/EVT", "A-SRC", TrackKind.Other, null, new TimelineSample[0],
                new[] { new EventMarker("e1", new SimTime(100), "event", "COLLISION", "A-SRC", "A/EVT") });
            Track b = new Track("B/EVT", "B-SRC", TrackKind.Other, null, new TimelineSample[0],
                new[] { new EventMarker("e2", new SimTime(110), "event", "COLLISION", "B-SRC", "B/EVT") });
            TimelineConflict c = Assert.Single(ConflictDetector.DetectWithDiagnostics(
                new MultiTrackTimeline(new[] { a, b }), null, W2AccFixture.CaseId).Conflicts);
            Assert.Equal("s", JsonDocument.Parse(ConflictJsonWriter.TryToJson(c).Value).RootElement.GetProperty("deltaUnit").GetString());
        }

        // 原 D11 用例（检查整份 JSON 无「°」）。依据 DEFECTS/W2.md「架构师裁定（Gemini bot，2026-11-11 20:39）」：
        // D11 关闭，summary 为人读文字允许出现 °；本用例保留，改为只断言落盘 deltaUnit 为 ASCII deg / deg/min 且不含度号。
        [Theory]
        [InlineData(TrackKind.Heading, "deg")]
        [InlineData(TrackKind.RateOfTurn, "deg/min")]
        [InlineData(TrackKind.TargetBearing, "deg")]
        public void WholeJsonOnDisk_HasNoDegreeSign(TrackKind kind, string expectedUnit)
        {
            string json = ConflictJsonWriter.TryToJson(One(kind, 0.0, 10.0)).Value;
            string unit = JsonDocument.Parse(json).RootElement.GetProperty("deltaUnit").GetString();
            Assert.Equal(expectedUnit, unit);
            Assert.True(
                unit.IndexOf('\u00B0') < 0 && unit.IndexOf('\u00BA') < 0 && unit.IndexOf('\u02DA') < 0 && unit.All(ch => ch < 128),
                "deltaUnit 含度号或非 ASCII：" + unit);
        }
    }

    public class W22TimeSourceMismatchTests
    {
        private const string TagUnix = "1779084900"; // 06:15:00Z
        private static readonly string Rmc = W2AccFixture.Rmc("061450.00", "180526");

        private static VdrImportResult Run(string line)
        {
            Result<VdrImportResult> r = VdrNmeaImporter.Import(new[] { line }, W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        private static double[] Sog(VdrImportResult r)
        {
            Track t = r.Tracks.FirstOrDefault(x => x.Kind == TrackKind.SpeedOverGround);
            return t == null ? new double[0] : t.Samples.Select(s => s.Time.Seconds).ToArray();
        }

        // 前缀 = 06:15:00 + offset；标签块 = 06:15:00。
        [Theory]
        [InlineData("06:15:00.000Z", false)]
        [InlineData("06:15:01.999Z", false)]
        [InlineData("06:15:02.000Z", false)]       // 正好 2 s 不报
        // W2.3 改写：依据 DEFECTS/W2.md「架构师裁定（Gemini bot，2026-11-11 20:39）」①——判定为差 > 2.0 + 1e-6，
        // 正好 2.000001 s 等于门限，不报；必须报警的边界改用 2.00001 s 覆盖。
        [InlineData("06:15:02.0000010Z", false)]   // +2.000001 s = 门限，不报
        [InlineData("06:15:02.0000100Z", true)]    // +2.00001 s，超门限
        [InlineData("06:15:02.001Z", true)]
        [InlineData("06:16:00.000Z", true)]        // 60 s
        [InlineData("07:15:00.000Z", true)]        // 1 h
        [InlineData("06:14:58.000Z", false)]       // −2 s 不报
        [InlineData("06:14:57.9999990Z", false)]   // −2.000001 s = 门限，不报（同上裁定 ①）
        [InlineData("06:14:57.9999900Z", true)]    // −2.00001 s，超门限
        [InlineData("06:14:00.000Z", true)]        // −60 s
        public void Mismatch_ThresholdBothDirections_TagStillWins(string prefixTime, bool expectInfo)
        {
            VdrImportResult r = Run("2026-05-18T" + prefixTime + "," + W2AccFixture.TagBlock("c:" + TagUnix) + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 900.0 }), "标签块应胜出，实际=[" + string.Join(",", Sog(r)) + "]");
            List<VdrDiagnostic> mm = r.Diagnostics.Where(d => d.Code == "vdr_timesource_mismatch").ToList();
            Assert.Equal(expectInfo ? 1 : 0, mm.Count);
            if (expectInfo)
            {
                Assert.Equal(DiagnosticSeverity.Info, mm[0].Severity);
                Assert.Equal(1, mm[0].LineNumber);
            }

            Assert.All(r.Diagnostics, d => Assert.Equal("vdr_timesource_mismatch", d.Code));
        }

        [Fact]
        public void FractionalTagBlock_ComparedPrecisely()
        {
            string tag = W2AccFixture.TagBlock("c:" + TagUnix + ".5"); // 06:15:00.5
            Assert.Empty(Run("2026-05-18T06:15:02.500Z," + tag + Rmc).Diagnostics);
            Assert.Single(Run("2026-05-18T06:15:02.501Z," + tag + Rmc).Diagnostics, d => d.Code == "vdr_timesource_mismatch");
        }

        [Fact]
        public void OnlyOneSideValid_NoMismatch()
        {
            // 无效标签块 + 有效前缀（差 60 s）
            VdrImportResult a = Run("2026-05-18T06:16:00.000Z,\\c:" + TagUnix + "*00\\" + Rmc);
            Assert.DoesNotContain(a.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            Assert.True(Sog(a).SequenceEqual(new[] { 960.0 }));
            // 无效前缀 + 有效标签块
            VdrImportResult b = Run("2026-13-45T99:99:99Z," + W2AccFixture.TagBlock("c:" + TagUnix) + Rmc);
            Assert.DoesNotContain(b.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            // 只有标签块 / 只有前缀（与句内时间相差 >2 s 也不算时间源不一致）
            Assert.Empty(Run(W2AccFixture.TagBlock("c:" + TagUnix) + Rmc).Diagnostics);
            Assert.Empty(Run("2026-05-18T06:20:00.000Z," + Rmc).Diagnostics);
            // 有效校验但无 c: 字段的标签块
            Assert.Empty(Run("2026-05-18T06:20:00.000Z," + W2AccFixture.TagBlock("s:STN01") + Rmc).Diagnostics);
        }

        [Fact]
        public void PlainLines_NoExtraDiagnostics_MultiLineFile()
        {
            string[] lines =
            {
                W2AccFixture.Rmc("061500.00", "180526"),
                "2026-05-18T06:15:01.000Z," + W2AccFixture.Rmc("061501.00", "180526"),
                W2AccFixture.TagBlock("c:1779084902") + W2AccFixture.Rmc("061502.00", "180526"),
                "2026-05-18T06:15:03.000Z," + W2AccFixture.TagBlock("c:1779084903") + W2AccFixture.Rmc("061503.00", "180526"),
                "2026-05-18T06:15:14.000Z," + W2AccFixture.TagBlock("c:1779084904") + W2AccFixture.Rmc("061504.00", "180526")
            };
            Result<VdrImportResult> r = VdrNmeaImporter.Import(lines, W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(r.IsSuccess);
            VdrDiagnostic d = Assert.Single(r.Value.Diagnostics);
            Assert.Equal("vdr_timesource_mismatch", d.Code);
            Assert.Equal(5, d.LineNumber);
        }

        [Fact]
        public void Mismatch_AlsoOnNonGnssSentence_OncePerLine()
        {
            string hdt = W2AccFixture.Nmea("HEHDT,45.0,T");
            VdrImportResult r = Run("2026-05-18T06:16:00.000Z," + W2AccFixture.TagBlock("c:" + TagUnix) + hdt);
            Assert.Single(r.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
            Track h = Assert.Single(r.Tracks, t => t.Kind == TrackKind.Heading);
            Assert.Equal(900.0, h.Samples[0].Time.Seconds, 9);
        }
    }
}
