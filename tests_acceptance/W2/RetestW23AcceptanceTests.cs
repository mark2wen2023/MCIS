using System;
using System.Collections.Generic;
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

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// W2.3 预写验收（2026-11-11，实施方尚未交付）。依据 DEFECTS/W2.md「架构师裁定（Gemini bot，2026-11-11 20:39）」：
    /// ① 时间源差 &gt; 2.0 + 1e-6；② 诊断时间差保留 3 位小数；③ 写盘用共享 caseId 校验器，不合格 → conflict_case_id_invalid；
    /// ④ 位置类 deltaUnit 写 m（速度 kn、时间 s）。预写时会失败的用例曾标 KnownDefect；W2.3 复测（2026-11-11）全部通过后已去除。演示数据全部虚构。
    /// </summary>
    public class W23TimeSourceToleranceTests
    {
        private const string TagUnix = "1779084900"; // 06:15:00Z
        private static readonly string Rmc = W2AccFixture.Rmc("061450.00", "180526");

        internal static VdrImportResult Run(string prefixTime, string tagBody = "c:" + TagUnix)
        {
            Result<VdrImportResult> r = VdrNmeaImporter.Import(
                new[] { "2026-05-18T" + prefixTime + "," + W2AccFixture.TagBlock(tagBody) + Rmc },
                W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        // 差 ±2.0000005 s（5 tick）在 1e-6 容差内，不报。
        [Theory]
        [InlineData("06:15:02.0000005Z")]
        [InlineData("06:14:57.9999995Z")]
        public void WithinTolerance_NoMismatch(string prefixTime)
        {
            VdrImportResult r = Run(prefixTime);
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == "vdr_timesource_mismatch");
        }

        // 差 ±2.000002 s 超出容差，报一条 Info；标签块仍胜出。
        [Theory]
        [InlineData("06:15:02.0000020Z")]
        [InlineData("06:14:57.9999980Z")]
        public void BeyondTolerance_ReportsInfo_TagWins(string prefixTime)
        {
            VdrImportResult r = Run(prefixTime);
            VdrDiagnostic d = Assert.Single(r.Diagnostics, x => x.Code == "vdr_timesource_mismatch");
            Assert.Equal(DiagnosticSeverity.Info, d.Severity);
            Track sog = Assert.Single(r.Tracks, t => t.Kind == TrackKind.SpeedOverGround);
            Assert.Equal(900.0, sog.Samples[0].Time.Seconds, 9);
        }

        [Theory]
        [InlineData("06:15:02.000Z")]
        [InlineData("06:14:58.000Z")]
        public void ExactlyTwoSeconds_StillNoMismatch(string prefixTime)
        {
            Assert.DoesNotContain(Run(prefixTime).Diagnostics, d => d.Code == "vdr_timesource_mismatch");
        }

        // 诊断文字里的时间差保留 3 位小数；不绑定整句文案。
        // 用负向后顾排除时间戳中的「02.500」之类片段（前一字符为数字、冒号或点时不算）。
        [Theory]
        [InlineData("06:15:02.500Z", "2.500")]
        [InlineData("06:15:02.0004Z", "2.000")]
        [InlineData("06:16:00.000Z", "60.000")]
        [InlineData("06:14:57.500Z", "2.500")]
        public void MessageDelta_HasThreeDecimals(string prefixTime, string expected)
        {
            AssertDeltaText(prefixTime, expected);
        }

        // 小数部分本身就需要 3 位时，当前实现已满足（预写时通过，不标 KnownDefect）。
        [Theory]
        [InlineData("06:15:02.0006Z", "2.001")]
        [InlineData("06:15:02.123Z", "2.123")]
        public void MessageDelta_ThreeSignificantDecimals_AlreadyOk(string prefixTime, string expected)
        {
            AssertDeltaText(prefixTime, expected);
        }

        private static void AssertDeltaText(string prefixTime, string expected)
        {
            VdrDiagnostic d = Assert.Single(Run(prefixTime).Diagnostics, x => x.Code == "vdr_timesource_mismatch");
            Regex delta = new Regex(@"(?<![\d:.])-?" + Regex.Escape(expected) + @"(?!\d)", RegexOptions.CultureInvariant);
            Assert.True(delta.IsMatch(d.Message), "诊断文字应含 3 位小数时间差「" + expected + "」：" + d.Message);
        }
    }

    public class W23CaseIdFormatTests : IDisposable
    {
        private readonly string _dir = Path.Combine(Path.GetTempPath(), "w23-acc-" + Guid.NewGuid().ToString("N"));

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

        // 口径：合同 common.schema.json#/$defs/caseId（minLength 3，pattern ^[A-Za-z0-9._-]+$，按 ECMA 语义 $ 为串尾）
        // 与共享校验器 EvidenceItem.IsValidCaseId（\A[A-Za-z0-9._-]{3,}\z，CultureInvariant）一致。
        public static IEnumerable<object[]> Invalid()
        {
            foreach (string s in new[]
            {
                "AB", "a", "案件01", "CASE 01", "CASE/01", "CASE:01", "CASE#01", " CASE-01", "CASE-01 ",
                "CASE-01\n", "\tCASE-01", "ＣＡＳＥ01", "CASE-0１", "CASÉ-01", "CASE-01\u200B"
            })
            {
                yield return new object[] { s };
            }
        }

        public static IEnumerable<object[]> Valid()
        {
            foreach (string s in new[] { "abc", "ABC", "123", "CASE-2026-LN01", "a.b_c-1", "...", "---", "YANGZE22.2026_01" })
            {
                yield return new object[] { s };
            }
        }

        public static IEnumerable<object[]> Blank()
        {
            foreach (string s in new[] { null, "", "   ", "\t", "\n", "\u3000" })
            {
                yield return new object[] { s };
            }
        }

        [Theory]
        [MemberData(nameof(Invalid))]
        public void Oracle_InvalidSamples_RejectedBySharedValidatorAndContract(string caseId)
        {
            Assert.False(EvidenceItem.IsValidCaseId(caseId), "共享校验器应拒：" + caseId);
            Assert.False(ContractCaseIdOk(caseId), "合同应拒：" + caseId);
        }

        [Theory]
        [MemberData(nameof(Valid))]
        public void Oracle_ValidSamples_AcceptedBySharedValidatorAndContract(string caseId)
        {
            Assert.True(EvidenceItem.IsValidCaseId(caseId));
            Assert.True(ContractCaseIdOk(caseId));
        }

        private static bool ContractCaseIdOk(string caseId)
        {
            Dictionary<string, object> obj = JsonSerializer.Deserialize<Dictionary<string, object>>(
                ConflictJsonWriter.ToJson(Detect(W2AccFixture.CaseId)[0]));
            obj["caseId"] = caseId;
            return MiniSchema.Validate(JsonSerializer.Serialize(obj)).Count == 0;
        }

        [Theory]
        [MemberData(nameof(Invalid))]
        public void InvalidFormat_TryToJsonAndArray_ReturnInvalidCode(string caseId)
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(caseId);
            Assert.Equal(2, conflicts.Count); // 检测阶段不拦
            Result<string> one = ConflictJsonWriter.TryToJson(conflicts[0]);
            Assert.False(one.IsSuccess, "不合格 caseId 不应序列化成功：" + caseId);
            Assert.Equal("conflict_case_id_invalid", one.ErrorCode);
            Result<string> many = ConflictJsonWriter.TryToJsonArray(conflicts);
            Assert.False(many.IsSuccess);
            Assert.Equal("conflict_case_id_invalid", many.ErrorCode);
        }

        [Theory]
        [MemberData(nameof(Invalid))]
        public void InvalidFormat_TryWrite_NoFileNoDirectory(string caseId)
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(caseId);
            string single = Path.Combine(_dir, "new", "one.json");
            string array = Path.Combine(_dir, "new2", "all.json");
            Result<bool> r1 = ConflictJsonWriter.TryWrite(single, conflicts[0]);
            Result<bool> r2 = ConflictJsonWriter.TryWrite(array, conflicts);
            Assert.Equal("conflict_case_id_invalid", r1.ErrorCode);
            Assert.Equal("conflict_case_id_invalid", r2.ErrorCode);
            Assert.False(r1.IsSuccess || r2.IsSuccess);
            Assert.False(Directory.Exists(_dir), "拒绝写盘时不应创建目录或文件");
        }

        [Fact]
        public void InvalidFormat_ExistingFileUntouched()
        {
            Directory.CreateDirectory(_dir);
            string path = Path.Combine(_dir, "time-alignment.json");
            File.WriteAllText(path, "[\"旧内容\"]", new UTF8Encoding(false));
            DateTime before = File.GetLastWriteTimeUtc(path);
            Result<bool> r = ConflictJsonWriter.TryWrite(path, Detect("案件 01"));
            Assert.False(r.IsSuccess);
            Assert.Equal("conflict_case_id_invalid", r.ErrorCode);
            Assert.Equal("[\"旧内容\"]", File.ReadAllText(path));
            Assert.Equal(before, File.GetLastWriteTimeUtc(path));
        }

        [Fact]
        public void MixedArray_OneInvalid_RejectsWhole()
        {
            List<TimelineConflict> mixed = Detect(W2AccFixture.CaseId).ToList();
            mixed[1] = mixed[1].WithCaseId("CASE 01");
            string path = Path.Combine(_dir, "mixed.json");
            Result<bool> r = ConflictJsonWriter.TryWrite(path, mixed);
            Assert.False(r.IsSuccess);
            Assert.Equal("conflict_case_id_invalid", r.ErrorCode);
            Assert.False(File.Exists(path));
        }

        [Theory]
        [MemberData(nameof(Blank))]
        public void Blank_StillMissingCode(string caseId)
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(caseId);
            Assert.Equal("conflict_case_id_missing", ConflictJsonWriter.TryToJson(conflicts[0]).ErrorCode);
            Assert.Equal("conflict_case_id_missing", ConflictJsonWriter.TryToJsonArray(conflicts).ErrorCode);
            Assert.Equal("conflict_case_id_missing", ConflictJsonWriter.TryWrite(Path.Combine(_dir, "x", "b.json"), conflicts).ErrorCode);
            Assert.False(Directory.Exists(_dir));
        }

        [Theory]
        [MemberData(nameof(Valid))]
        public void ValidFormat_TryWrite_FilePassesContract(string caseId)
        {
            IReadOnlyList<TimelineConflict> conflicts = Detect(caseId);
            string path = Path.Combine(_dir, "ok", "time-alignment.json");
            Result<bool> r = ConflictJsonWriter.TryWrite(path, conflicts);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            JsonElement arr = JsonDocument.Parse(File.ReadAllText(path)).RootElement;
            Assert.Equal(2, arr.GetArrayLength());
            foreach (JsonElement e in arr.EnumerateArray())
            {
                List<string> errors = MiniSchema.Validate(e.GetRawText());
                Assert.True(errors.Count == 0, string.Join("\n", errors));
                Assert.Equal(caseId, e.GetProperty("caseId").GetString());
            }
        }
    }

    public class W23PositionUnitTests : IDisposable
    {
        private readonly string _dir = Path.Combine(Path.GetTempPath(), "w23-pos-" + Guid.NewGuid().ToString("N"));

        public void Dispose()
        {
            if (Directory.Exists(_dir))
            {
                Directory.Delete(_dir, true);
            }
        }

        private static Track Pos(string id, string src, TrackKind kind, double lon, string name = null)
        {
            return new Track(id, src, kind, null, Enumerable.Range(0, 11).Select(t =>
                TimelineSample.AtPosition(new SimTime(t), new GeoCoord(lon, 30.1, 0.0), name)).ToArray());
        }

        private static string WriteAndRead(string dir, TrackKind kind)
        {
            string name = kind == TrackKind.TargetPosition ? "LILY" : null;
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                Pos("A/" + kind, "MARY-VDR", kind, 122.060, name),
                Pos("B/" + kind, "VTS-AIS", kind, 122.070, name)
            });
            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.DetectWithDiagnostics(tl, null, W2AccFixture.CaseId).Conflicts;
            Assert.Single(conflicts);
            string path = Path.Combine(dir, kind + ".json");
            Result<bool> r = ConflictJsonWriter.TryWrite(path, conflicts);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return File.ReadAllText(path);
        }

        // 裁定：位置类 deltaUnit 统一为 m（速度 kn、时间 s）。
        [Theory]
        [InlineData(TrackKind.Position)]
        [InlineData(TrackKind.TargetPosition)]
        public void PositionDeltaUnit_OnDisk_IsMeters_AndFilePassesContract(TrackKind kind)
        {
            JsonElement e = JsonDocument.Parse(WriteAndRead(_dir, kind)).RootElement[0];
            Assert.Empty(MiniSchema.Validate(e.GetRawText()));
            Assert.Equal("m", e.GetProperty("deltaUnit").GetString());
            Assert.True(e.GetProperty("delta").GetDouble() > 900.0); // 0.01° 经度 @30.1°N ≈ 962 m
        }

        [Fact]
        public void SpeedAndEventUnits_OnDisk_KnAndS()
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/SOG", "MARY-VDR", TrackKind.SpeedOverGround, 0, 10, 12.0),
                W2AccFixture.Constant("B/SOG", "VTS-AIS", TrackKind.SpeedOverGround, 0, 10, 13.0),
                new Track("A/EVT", "MARY-VDR", TrackKind.Other, null, new TimelineSample[0],
                    new[] { new EventMarker("e1", new SimTime(100), "event", "COLLISION", "MARY-VDR", "A/EVT") }),
                new Track("B/EVT", "VTS-AIS", TrackKind.Other, null, new TimelineSample[0],
                    new[] { new EventMarker("e2", new SimTime(110), "event", "COLLISION", "VTS-AIS", "B/EVT") })
            });
            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.DetectWithDiagnostics(tl, null, W2AccFixture.CaseId).Conflicts;
            string path = Path.Combine(_dir, "mix.json");
            Assert.True(ConflictJsonWriter.TryWrite(path, conflicts).IsSuccess);
            JsonElement arr = JsonDocument.Parse(File.ReadAllText(path)).RootElement;
            foreach (JsonElement e in arr.EnumerateArray())
            {
                Assert.Empty(MiniSchema.Validate(e.GetRawText()));
            }

            Assert.Contains(arr.EnumerateArray(), x => x.GetProperty("trackKind").GetString() == "SpeedOverGround" && x.GetProperty("deltaUnit").GetString() == "kn");
            Assert.Contains(arr.EnumerateArray(), x => x.GetProperty("trackKind").GetString() == "EventTime" && x.GetProperty("deltaUnit").GetString() == "s");
        }

        // 写盘的 deltaUnit 不得为空串（全种类，位置类为 W2.3 修复点）。
        [Fact]
        public void NoEmptyDeltaUnit_ForAnyComparableKind()
        {
            List<string> empty = new List<string>();
            foreach (TrackKind kind in new[] { TrackKind.Position, TrackKind.TargetPosition })
            {
                JsonElement e = JsonDocument.Parse(WriteAndRead(_dir, kind)).RootElement[0];
                if (string.IsNullOrEmpty(e.GetProperty("deltaUnit").GetString()))
                {
                    empty.Add(kind.ToString());
                }
            }

            Assert.True(empty.Count == 0, "deltaUnit 为空串的种类：" + string.Join(",", empty));
        }
    }
}
