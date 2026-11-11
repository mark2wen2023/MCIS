using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// W2.1 复测（2026-11-11）：D08–D10 按「架构师复测裁定」，行长确认②，ConflictJsonWriter 合同写盘。演示数据全部虚构。
    /// </summary>
    public class W21TimeSourceTests
    {
        private const string Unix0615 = "1779084900"; // 2026-05-18 06:15:00 UTC → 900 s
        private const string GoodPrefix = "2026-05-18T06:15:30.000Z,"; // 930 s
        private const string BadPrefix = "2026-13-45T99:99:99Z,";
        private static readonly string Rmc = W2AccFixture.Rmc("061450.00", "180526"); // 句内 890 s

        private static string GoodTag() { return W2AccFixture.TagBlock("c:" + Unix0615); }
        private static string BadTag() { return "\\c:" + Unix0615 + "*00\\"; }

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

        private static string Dump(VdrImportResult r)
        {
            return "样本=[" + string.Join(",", Sog(r)) + "] 诊断=" + string.Join(" | ", r.Diagnostics.Select(d => d.Code + ":" + d.Message));
        }

        // D08 裁定：有效标签块 > 有效日志前缀 > 句内时间；回退都要发诊断（含被弃用的时间源）。
        [Fact]
        public void D08_ValidPrefix_ValidTag_UsesTag_NoFallbackDiagnostic()
        {
            VdrImportResult r = Run(GoodPrefix + GoodTag() + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 900.0 }), Dump(r));
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == "vdr_tagblock_invalid" || d.Code == "vdr_logprefix_invalid");
        }

        [Fact]
        public void D08_ValidPrefix_InvalidTag_FallsBackToPrefix_WithWarningNamingPrefix()
        {
            VdrImportResult r = Run(GoodPrefix + BadTag() + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 930.0 }), Dump(r));
            VdrDiagnostic d = Assert.Single(r.Diagnostics, x => x.Code == "vdr_tagblock_invalid");
            Assert.Equal(DiagnosticSeverity.Warning, d.Severity);
            Assert.Equal(1, d.LineNumber);
            Assert.Contains("日志前缀", d.Message);
        }

        [Fact]
        public void D08_InvalidPrefix_InvalidTag_FallsBackToSentence_WithBothDiagnostics()
        {
            VdrImportResult r = Run(BadPrefix + BadTag() + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 890.0 }), Dump(r));
            Assert.Single(r.Diagnostics, x => x.Code == "vdr_tagblock_invalid");
            VdrDiagnostic p = Assert.Single(r.Diagnostics, x => x.Code == "vdr_logprefix_invalid");
            Assert.Equal(DiagnosticSeverity.Warning, p.Severity);
        }

        [Fact]
        public void D08_InvalidPrefix_ValidTag_UsesTag()
        {
            VdrImportResult r = Run(BadPrefix + GoodTag() + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 900.0 }), Dump(r));
        }

        [Fact]
        public void D08_InvalidPrefixOnly_FallsBackToSentence_WithDiagnostic()
        {
            VdrImportResult r = Run(BadPrefix + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 890.0 }), Dump(r));
            Assert.Single(r.Diagnostics, x => x.Code == "vdr_logprefix_invalid");
        }

        [Fact]
        public void D08_PrefixWithSpaceSeparator_AndTag_UsesTag()
        {
            VdrImportResult r = Run("2026-05-18T06:15:30Z " + GoodTag() + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 900.0 }), Dump(r));
        }

        [Fact]
        public void D08_ValidTagWithoutTimeField_FallsBackToPrefix()
        {
            VdrImportResult r = Run(GoodPrefix + W2AccFixture.TagBlock("s:STN01") + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 930.0 }), Dump(r));
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }

        [Fact]
        public void D08_PlainLines_StillNoSpuriousTimeDiagnostics()
        {
            VdrImportResult r = Run(GoodPrefix + Rmc);
            Assert.True(Sog(r).SequenceEqual(new[] { 930.0 }), Dump(r));
            Assert.Empty(r.Diagnostics);
            VdrImportResult bare = Run(Rmc);
            Assert.True(Sog(bare).SequenceEqual(new[] { 890.0 }), Dump(bare));
            Assert.Empty(bare.Diagnostics);
        }

        [Fact]
        public void D08_GnssSentenceTimeBasis_Unchanged()
        {
            VdrImportOptions o = W2AccFixture.Options(W2AccFixture.Mary);
            o.TimeBasis = VdrTimeBasis.GnssSentenceTime;
            Result<VdrImportResult> r = VdrNmeaImporter.Import(new[] { GoodPrefix + GoodTag() + Rmc }, o);
            Assert.True(r.IsSuccess);
            Assert.True(Sog(r.Value).SequenceEqual(new[] { 890.0 }), Dump(r.Value));
        }

        // 行长确认②：CRLF 不计入；ImportText 按 CRLF 拆行后 80 字符不告警、81 告警。
        [Theory]
        [InlineData(80, false)]
        [InlineData(81, true)]
        public void LineLength_CrLfNotCounted_InImportText(int len, bool warn)
        {
            string body = "GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A";
            string sentence = W2AccFixture.Nmea(body + "," + new string('P', len - body.Length - 5));
            Assert.Equal(len, sentence.Length);
            Result<VdrImportResult> r = VdrNmeaImporter.ImportText(
                GoodPrefix + sentence + "\r\n" + GoodPrefix + sentence + "\r\n", W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(r.IsSuccess);
            Assert.Equal(warn ? 2 : 0, r.Value.Diagnostics.Count(d => d.Code == "vdr_line_too_long"));
        }
    }

    public class W21RelativeBearingTests
    {
        private static string Ttm(int no, double brg, string reference, string time)
        {
            return "2026-05-18T06:15:" + time + ".000Z," + W2AccFixture.Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "RATTM,{0:00},1.20,{1:0.0},{2},10.0,90.0,T,0.5,10.0,N,LILY,T,,061500.00,A", no, brg, reference));
        }

        private static string Hdt(double hdg, string time)
        {
            return "2026-05-18T06:15:" + time + ".000Z," + W2AccFixture.Nmea(string.Format(CultureInfo.InvariantCulture, "HEHDT,{0:0.0},T", hdg));
        }

        // D09 裁定：保留相对方位原值，BearingReference=Relative，真方位 NotAvailable 并发诊断；之后有船首向不回填。
        [Fact]
        public void D09_RelativeWithoutHeading_KeptAsRelative_NoBackfill_ThenConvertsAfterHeading()
        {
            Result<VdrImportResult> res = VdrNmeaImporter.Import(new[]
            {
                Ttm(1, 30.0, "R", "00"),
                Hdt(45.0, "05"),
                Ttm(1, 30.0, "R", "10")
            }, W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(res.IsSuccess);
            VdrImportResult r = res.Value;

            Track rel = Assert.Single(r.Tracks, t => t.Kind == TrackKind.TargetBearing && t.BearingReference == BearingReference.Relative);
            Assert.EndsWith("/REL", rel.Id);
            TimelineSample relSample = Assert.Single(rel.Samples);
            Assert.Equal(30.0, relSample.Value, 9);
            Assert.Equal(900.0, relSample.Time.Seconds, 9);

            Track tru = Assert.Single(r.Tracks, t => t.Kind == TrackKind.TargetBearing && t.BearingReference == BearingReference.True);
            TimelineSample trueSample = Assert.Single(tru.Samples);
            Assert.Equal(910.0, trueSample.Time.Seconds, 9);
            Assert.Equal(75.0, trueSample.Value, 9);

            VdrDiagnostic d = Assert.Single(r.Diagnostics, x => x.Code == "vdr_relative_bearing_no_heading");
            Assert.Equal(1, d.LineNumber);
            Assert.Equal(DiagnosticSeverity.Warning, d.Severity);
        }

        [Fact]
        public void D09_RelativeTrack_NotComparedWithOtherSourceTrueBearing_EmitsNotAvailable()
        {
            List<Track> tracks = new List<Track>();
            tracks.AddRange(VdrNmeaImporter.Import(
                Enumerable.Range(0, 11).Select(s => Ttm(1, 30.0, "R", s.ToString("00", CultureInfo.InvariantCulture))),
                W2AccFixture.Options(W2AccFixture.Mary)).Value.Tracks);
            tracks.AddRange(VdrNmeaImporter.Import(
                Enumerable.Range(0, 11).Select(s => Ttm(4, 75.0, "T", s.ToString("00", CultureInfo.InvariantCulture))),
                W2AccFixture.Options(W2AccFixture.Lily)).Value.Tracks);

            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(tracks));
            Assert.DoesNotContain(r.Conflicts, c => c.Kind == TrackKind.TargetBearing);
            Assert.Contains(r.Diagnostics, d => d.Code == ConflictDiagnostic.NotAvailableCode &&
                                                d.Kind == TrackKind.TargetBearing &&
                                                d.Reason == "bearing_relative_no_heading");
            // 距离仍按目标名比对（两路均 1.20 nm，不冲突）。
            Assert.DoesNotContain(r.Conflicts, c => c.Kind == TrackKind.TargetRange);
        }

        [Fact]
        public void D09_TrueBearingTtm_Unaffected()
        {
            VdrImportResult r = VdrNmeaImporter.Import(new[] { Ttm(1, 30.0, "T", "00") }, W2AccFixture.Options(W2AccFixture.Mary)).Value;
            Track t = Assert.Single(r.Tracks, x => x.Kind == TrackKind.TargetBearing);
            Assert.Equal(BearingReference.True, t.BearingReference);
            Assert.Equal(30.0, t.Samples[0].Value, 9);
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == "vdr_relative_bearing_no_heading");
        }
    }

    public class W21InvalidNumberTests
    {
        private static Track Seq(string src, TrackKind kind, params double[] values)
        {
            return W2AccFixture.ScalarTrack(src + "/" + kind, src, kind,
                values.Select((v, i) => W2AccFixture.S(i, v)).ToArray());
        }

        // D10 裁定：NaN/±∞ 时刻输出 NotAvailable 并发诊断（inv_invalid_number），不静默跳过；有效区段照常比对。
        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        [InlineData(double.NegativeInfinity)]
        public void D10_InvalidValueInMiddle_NotAvailableWithReasonAndRange_ValidPartsStillCompared(double bad)
        {
            Track a = Seq("A", TrackKind.SpeedOverGround, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12);
            Track b = Seq("B", TrackKind.SpeedOverGround, 13, 13, 13, 13, 13, bad, 13, 13, 13, 13, 13);
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[] { a, b }));

            ConflictDiagnostic d = Assert.Single(r.Diagnostics, x => x.Reason == ConflictDiagnostic.InvalidNumberReason);
            Assert.Equal(ConflictDiagnostic.NotAvailableCode, d.Code);
            Assert.True(d.Range.HasValue);
            Assert.True(d.Range.Value.Start.Seconds <= 5.0 && d.Range.Value.End.Seconds >= 5.0,
                "无效区间应覆盖 5 s，实际 " + d.Range.Value.Start.Seconds + ".." + d.Range.Value.End.Seconds);
            Assert.True(d.Range.Value.Start.Seconds >= 4.0 && d.Range.Value.End.Seconds <= 6.0);
            Assert.NotEmpty(r.Conflicts);
            Assert.All(r.Conflicts, c => Assert.True(!(c.Range.Start.Seconds < 5.0 && c.Range.End.Seconds > 5.0),
                "冲突区间不应跨越无效时刻：" + c));
        }

        [Fact]
        public void D10_InvalidInBothSources_AngularKind_AlsoReported()
        {
            Track a = Seq("A", TrackKind.Heading, 10, double.NaN, 10);
            Track b = Seq("B", TrackKind.Heading, 10, 10, double.PositiveInfinity);
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[] { a, b }));
            Assert.Empty(r.Conflicts);
            Assert.Contains(r.Diagnostics, x => x.Reason == ConflictDiagnostic.InvalidNumberReason && x.Kind == TrackKind.Heading);
        }

        [Fact]
        public void D10_AllFinite_NoInvalidNumberDiagnostic()
        {
            Track a = Seq("A", TrackKind.SpeedOverGround, 12, 12, 12);
            Track b = Seq("B", TrackKind.SpeedOverGround, 12, 12, 12);
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[] { a, b }));
            Assert.Empty(r.Diagnostics);
        }
    }

    /// <summary>
    /// 合同校验：测试内实现 JSON Schema draft 2020-12 中 conflict/common 实际用到的子集
    /// （type 含数组、enum、pattern、minLength、required、properties、additionalProperties:false、$ref（本地与跨文件）、format: date-time）。
    /// 未引入第三方 NuGet（离线缓存无 JSON Schema 库）。
    /// </summary>
    internal static class MiniSchema
    {
        private static readonly Regex DateTime3339 = new Regex(
            @"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$", RegexOptions.CultureInvariant);

        public static string SchemaDir()
        {
            DirectoryInfo dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, "contracts", "schemas", "conflict.schema.json")))
            {
                dir = dir.Parent;
            }

            Assert.NotNull(dir);
            return Path.Combine(dir.FullName, "contracts", "schemas");
        }

        public static JsonElement Load(string file)
        {
            return JsonDocument.Parse(File.ReadAllText(Path.Combine(SchemaDir(), file))).RootElement.Clone();
        }

        public static List<string> Validate(string json)
        {
            List<string> errors = new List<string>();
            JsonElement instance = JsonDocument.Parse(json).RootElement.Clone();
            JsonElement root = Load("conflict.schema.json");
            Check(instance, root, root, "$", errors);
            return errors;
        }

        private static JsonElement Resolve(string reference, JsonElement currentRoot, out JsonElement newRoot)
        {
            string file = null;
            string pointer = reference;
            int hash = reference.IndexOf('#');
            if (hash > 0)
            {
                file = reference.Substring(0, hash);
                pointer = reference.Substring(hash);
            }

            newRoot = file == null ? currentRoot : Load(file);
            JsonElement node = newRoot;
            foreach (string part in pointer.TrimStart('#').Split('/', StringSplitOptions.RemoveEmptyEntries))
            {
                node = node.GetProperty(part.Replace("~1", "/").Replace("~0", "~"));
            }

            return node;
        }

        private static string TypeOf(JsonElement e)
        {
            switch (e.ValueKind)
            {
                case JsonValueKind.Object: return "object";
                case JsonValueKind.Array: return "array";
                case JsonValueKind.String: return "string";
                case JsonValueKind.Number: return "number";
                case JsonValueKind.True:
                case JsonValueKind.False: return "boolean";
                case JsonValueKind.Null: return "null";
                default: return "undefined";
            }
        }

        private static void Check(JsonElement inst, JsonElement schema, JsonElement root, string path, List<string> errors)
        {
            JsonElement v;
            if (schema.TryGetProperty("$ref", out v))
            {
                JsonElement newRoot;
                JsonElement target = Resolve(v.GetString(), root, out newRoot);
                Check(inst, target, newRoot, path, errors);
            }

            if (schema.TryGetProperty("type", out v))
            {
                string[] allowed = v.ValueKind == JsonValueKind.Array
                    ? v.EnumerateArray().Select(x => x.GetString()).ToArray()
                    : new[] { v.GetString() };
                string actual = TypeOf(inst);
                bool ok = allowed.Contains(actual) ||
                          (actual == "number" && allowed.Contains("integer") && inst.GetDouble() == Math.Floor(inst.GetDouble()));
                if (!ok)
                {
                    errors.Add(path + ": 类型 " + actual + " 不在 [" + string.Join(",", allowed) + "]");
                    return;
                }
            }

            if (schema.TryGetProperty("enum", out v) && !v.EnumerateArray().Any(x => JsonElementEquals(x, inst)))
            {
                errors.Add(path + ": 值 " + inst.GetRawText() + " 不在 enum");
            }

            if (inst.ValueKind == JsonValueKind.String)
            {
                string s = inst.GetString();
                // JSON Schema 采用 ECMA-262 语义：末尾 $ 不匹配「行尾换行之前」；.NET 的 $ 会放过 "ABC\n"，故改写为 \z（W2.3 预写补强）。
                if (schema.TryGetProperty("pattern", out v) && !Regex.IsMatch(s, EcmaAnchors(v.GetString()), RegexOptions.CultureInvariant))
                {
                    errors.Add(path + ": 「" + s + "」不匹配 pattern " + v.GetString());
                }

                if (schema.TryGetProperty("minLength", out v) && s.Length < v.GetInt32())
                {
                    errors.Add(path + ": 长度小于 minLength");
                }

                DateTimeOffset parsed;
                if (schema.TryGetProperty("format", out v) && v.GetString() == "date-time" &&
                    (!DateTime3339.IsMatch(s) ||
                     !DateTimeOffset.TryParse(s, CultureInfo.InvariantCulture, DateTimeStyles.None, out parsed)))
                {
                    errors.Add(path + ": 「" + s + "」不是 RFC 3339 date-time");
                }
            }

            if (inst.ValueKind == JsonValueKind.Object)
            {
                if (schema.TryGetProperty("required", out v))
                {
                    foreach (JsonElement r in v.EnumerateArray())
                    {
                        if (!inst.TryGetProperty(r.GetString(), out _))
                        {
                            errors.Add(path + ": 缺必填 " + r.GetString());
                        }
                    }
                }

                JsonElement props;
                bool hasProps = schema.TryGetProperty("properties", out props);
                bool closed = schema.TryGetProperty("additionalProperties", out v) && v.ValueKind == JsonValueKind.False;
                HashSet<string> seen = new HashSet<string>(StringComparer.Ordinal);
                foreach (JsonProperty p in inst.EnumerateObject())
                {
                    if (!seen.Add(p.Name))
                    {
                        errors.Add(path + ": 重复键 " + p.Name);
                    }

                    JsonElement sub;
                    if (hasProps && props.TryGetProperty(p.Name, out sub))
                    {
                        Check(p.Value, sub, root, path + "." + p.Name, errors);
                    }
                    else if (closed)
                    {
                        errors.Add(path + ": additionalProperties:false 不允许 " + p.Name);
                    }
                }
            }
        }

        private static string EcmaAnchors(string pattern)
        {
            if (pattern.EndsWith("$", StringComparison.Ordinal) && !pattern.EndsWith("\\$", StringComparison.Ordinal))
            {
                pattern = pattern.Substring(0, pattern.Length - 1) + "\\z";
            }

            return pattern;
        }

        private static bool JsonElementEquals(JsonElement a, JsonElement b)
        {
            if (a.ValueKind != b.ValueKind)
            {
                return false;
            }

            if (a.ValueKind == JsonValueKind.String)
            {
                return a.GetString() == b.GetString();
            }

            if (a.ValueKind == JsonValueKind.Number)
            {
                return a.GetDouble() == b.GetDouble();
            }

            return a.GetRawText() == b.GetRawText();
        }
    }

    public class W21ConflictJsonContractTests
    {
        private static readonly DateTimeOffset At = new DateTimeOffset(2026, 11, 11, 20, 30, 15, 123, TimeSpan.FromHours(8));

        private static TimelineConflict Speed()
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/SOG", "MARY-VDR", TrackKind.SpeedOverGround, 0, 10, 12.0),
                W2AccFixture.Constant("B/SOG", "VTS-AIS", TrackKind.SpeedOverGround, 0, 10, 13.0)
            });
            return Assert.Single(ConflictDetector.DetectWithDiagnostics(tl, null, W2AccFixture.CaseId).Conflicts);
        }

        private static void AssertValid(string json)
        {
            List<string> errors = MiniSchema.Validate(json);
            Assert.True(errors.Count == 0, string.Join("\n", errors) + "\nJSON=" + json);
        }

        [Theory]
        [InlineData(ConflictStatus.Open)]
        [InlineData(ConflictStatus.PendingInterview)]
        [InlineData(ConflictStatus.ClockCorrected)]
        [InlineData(ConflictStatus.Annotated)]
        [InlineData(ConflictStatus.Resolved)]
        [InlineData(ConflictStatus.AcceptedAsIs)]
        public void EachStatus_WithResolver_PassesContract_AndRoundTrips(ConflictStatus status)
        {
            TimelineConflict c = Speed().WithResolution(status, "标注·采信 \"AIS\"\\备注\n第二行", "INV-甲", At);
            string json = ConflictJsonWriter.ToJson(c);
            AssertValid(json);

            JsonElement e = JsonDocument.Parse(json).RootElement;
            Assert.Equal(status.ToString(), e.GetProperty("status").GetString());
            Assert.Equal("C-01", e.GetProperty("conflictId").GetString());
            Assert.Equal(W2AccFixture.CaseId, e.GetProperty("caseId").GetString());
            Assert.Equal("INV-甲", e.GetProperty("resolvedBy").GetString());
            Assert.Equal("标注·采信 \"AIS\"\\备注\n第二行", e.GetProperty("resolution").GetString());
            DateTimeOffset back = DateTimeOffset.Parse(e.GetProperty("resolvedAt").GetString(), CultureInfo.InvariantCulture);
            Assert.Equal(At, back);
            Assert.Equal(At.Offset, back.Offset);
            Assert.Equal(1.0, e.GetProperty("delta").GetDouble(), 9);
            Assert.Equal("MARY-VDR", e.GetProperty("a").GetProperty("sourceLabel").GetString());
        }

        [Theory]
        [InlineData(ConflictStatus.Open)]
        [InlineData(ConflictStatus.PendingInterview)]
        [InlineData(ConflictStatus.ClockCorrected)]
        [InlineData(ConflictStatus.Annotated)]
        public void NonTerminalStatus_WithoutResolver_KeepsNullResolvedFields_AndPasses(ConflictStatus status)
        {
            TimelineConflict c = status == ConflictStatus.Open ? Speed() : Speed().WithResolution(status, null, null, null);
            string json = ConflictJsonWriter.ToJson(c);
            AssertValid(json);
            JsonElement e = JsonDocument.Parse(json).RootElement;
            Assert.Equal(JsonValueKind.Null, e.GetProperty("resolvedBy").ValueKind);
            Assert.Equal(JsonValueKind.Null, e.GetProperty("resolvedAt").ValueKind);
        }

        [Fact]
        public void AllConflictKinds_FromRealDetection_PassContract_AsArray()
        {
            Track evA = new Track("A/EVT", "MARY-VDR", TrackKind.Other, null, new TimelineSample[0],
                new[] { new EventMarker("e1", new SimTime(100), "event", "STOP ENGINE", "MARY-VDR", "A/EVT") });
            Track evB = new Track("B/EVT", "ER-LOG", TrackKind.Other, null, new TimelineSample[0],
                new[] { new EventMarker("e2", new SimTime(165), "event", "STOP ENGINE", "ER-LOG", "B/EVT") });
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                W2AccFixture.ScalarTrack("A/POS", "MARY-VDR", TrackKind.Position, W2AccFixture.P(0, 122.06, 30.1), W2AccFixture.P(10, 122.06, 30.1)),
                W2AccFixture.ScalarTrack("B/POS", "VTS-AIS", TrackKind.Position, W2AccFixture.P(0, 122.07, 30.1), W2AccFixture.P(10, 122.07, 30.1)),
                W2AccFixture.Constant("A/HDG", "MARY-VDR", TrackKind.Heading, 0, 10, 359.0),
                W2AccFixture.Constant("B/HDG", "VTS-AIS", TrackKind.Heading, 0, 10, 5.0),
                evA, evB
            });
            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.DetectWithDiagnostics(tl, null, W2AccFixture.CaseId).Conflicts;
            Assert.Equal(3, conflicts.Count);
            string array = ConflictJsonWriter.ToJsonArray(conflicts);
            JsonElement arr = JsonDocument.Parse(array).RootElement;
            Assert.Equal(3, arr.GetArrayLength());
            foreach (JsonElement item in arr.EnumerateArray())
            {
                AssertValid(item.GetRawText());
            }

            Assert.Contains(arr.EnumerateArray(), x => x.GetProperty("trackKind").GetString() == "EventTime");
            Assert.Contains(arr.EnumerateArray(), x => x.GetProperty("trackKind").GetString() == "Position");
        }

        [Fact]
        public void ToJsonArray_EmptyAndNull_AreValidJsonArrays()
        {
            Assert.Equal(0, JsonDocument.Parse(ConflictJsonWriter.ToJsonArray(new TimelineConflict[0])).RootElement.GetArrayLength());
            Assert.Equal(0, JsonDocument.Parse(ConflictJsonWriter.ToJsonArray(null)).RootElement.GetArrayLength());
        }

        [Fact]
        public void OutputKeys_AreSubsetOfContract_AndIncludeResolvedFields()
        {
            JsonElement props = MiniSchema.Load("conflict.schema.json").GetProperty("properties");
            JsonElement e = JsonDocument.Parse(ConflictJsonWriter.ToJson(Speed())).RootElement;
            foreach (JsonProperty p in e.EnumerateObject())
            {
                Assert.True(props.TryGetProperty(p.Name, out _), "合同未定义的键：" + p.Name);
            }

            Assert.True(e.TryGetProperty("resolvedBy", out _));
            Assert.True(e.TryGetProperty("resolvedAt", out _));
            Assert.Equal("RuleEngine", e.GetProperty("detectedBy").GetString());
        }

        // 校验器自检：确保 MiniSchema 真能拒收违规实例（否则上面的「通过」没有意义）。
        [Theory]
        [InlineData("extra", "additionalProperties")]
        [InlineData("badStatus", "enum")]
        [InlineData("badDate", "date-time")]
        [InlineData("dateNoZone", "date-time")]
        [InlineData("missingStatus", "缺必填")]
        [InlineData("obsExtra", "additionalProperties")]
        [InlineData("badId", "pattern")]
        [InlineData("badCase", "pattern")]
        [InlineData("resolvedByNumber", "类型")]
        public void MiniSchema_RejectsViolations(string mutation, string expectedFragment)
        {
            Dictionary<string, object> obj = JsonSerializer.Deserialize<Dictionary<string, object>>(
                ConflictJsonWriter.ToJson(Speed().WithResolution(ConflictStatus.Resolved, "x", "INV-1", At)));
            switch (mutation)
            {
                case "extra": obj["foo"] = 1; break;
                case "badStatus": obj["status"] = "Closed"; break;
                case "badDate": obj["resolvedAt"] = "昨天"; break;
                case "dateNoZone": obj["resolvedAt"] = "2026-11-11T20:30:15"; break;
                case "missingStatus": obj.Remove("status"); break;
                case "obsExtra": obj["a"] = new Dictionary<string, object> { { "sourceLabel", "A" }, { "valueText", "1" }, { "x", 1 } }; break;
                case "badId": obj["conflictId"] = "C-1"; break;
                case "badCase": obj["caseId"] = "案件 01"; break;
                case "resolvedByNumber": obj["resolvedBy"] = 5; break;
            }

            List<string> errors = MiniSchema.Validate(JsonSerializer.Serialize(obj));
            Assert.Contains(errors, e => e.Contains(expectedFragment));
        }
    }
}
