using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;

namespace Mcis.Cli
{
    /// <summary>
    /// align 子命令：调用已验收的 W2（VDR 导入 + 钟差估计/校准 + 冲突检测），
    /// 输出符合 conflict.schema.json 的 conflicts[]，以及各源时钟偏差。
    ///
    /// 请求：
    ///   {
    ///     "caseId": "...",                 // 必填；适配层在序列化前写入每条冲突（兼容 W2.2 caseId 拒写）
    ///     "caseEpochUtc": "2026-05-18T06:15:00Z",  // 必填
    ///     "referenceSourceId": "GNSS",     // 可选，默认 GNSS
    ///     "offsetMethod": "Median",        // 可选：Median | LeastSquares
    ///     "calibrate": true,               // 可选，默认 true；无锚点或估计失败时仍检测冲突
    ///     "defaultDateUtc": "2026-05-18",  // 可选，传到各源（无日期 NMEA）
    ///     "sources": [ {
    ///         "sourceId": "MARY-VDR",
    ///         "format": "nmea",            // nmea | csv | mediaManifest
    ///         "text": "...",               // 与 path 二选一，text 优先
    ///         "path": "/abs/or/relative",
    ///         "timeBasis": "LogPrefix",
    ///         "defaultDateUtc": "...",
    ///         "keepBadChecksum": false,
    ///         "emitGnssAnchors": true,
    ///         "csvMapping": { "timeColumn": "...", "timeFormat": null,
    ///             "timeZoneOffsetHours": 0, "delimiter": ",", "eventColumn": null,
    ///             "columns": [ { "column":"sog_kn", "kind":"SpeedOverGround",
    ///                 "trackName": null, "scale": 1, "offset": 0, "markChanges": false,
    ///                 "textValues": { "STOP": 0 } } ] }
    ///     } ],
    ///     "manualAnchors": { "text"|"path": "..." },
    ///     "thresholds": { "courseDeg": 2.0, "speedKn": 0.3, ... }
    ///   }
    ///
    /// 结果：{ caseId, conflicts, clockOffsets, calibration, importDiagnostics, conflictDiagnostics, stats }
    /// </summary>
    public static class AlignCommand
    {
        public static JsonNode Run(JsonNode req)
        {
            if (req == null)
            {
                throw new RequestException("BAD_REQUEST", "请求不能为空");
            }

            string caseId = Str(req, "caseId");
            if (string.IsNullOrWhiteSpace(caseId))
            {
                throw new RequestException("BAD_REQUEST", "缺少 caseId（合同必填；W2.2 将拒绝无 caseId 的写盘）");
            }

            // 入口统一校验（架构师裁定 2026-11-11 21:06）：不论是否有冲突，不合格的 caseId 一律拒绝。
            if (!Mcis.Domain.Evidence.EvidenceItem.IsValidCaseId(caseId))
            {
                throw new RequestException("conflict_case_id_invalid", "caseId 格式不符合合同：" + caseId);
            }

            DateTimeOffset epoch = ReadDateTimeOffset(req, "caseEpochUtc", required: true).Value;
            string referenceSourceId = Str(req, "referenceSourceId") ?? "GNSS";
            bool calibrate = req["calibrate"] == null || req["calibrate"].GetValue<bool>();
            OffsetMethod method = ReadOffsetMethod(req["offsetMethod"]);
            DateTime? defaultDate = ReadDate(req, "defaultDateUtc");

            JsonArray sourcesNode = req["sources"] as JsonArray;
            if (sourcesNode == null || sourcesNode.Count == 0)
            {
                throw new RequestException("BAD_REQUEST", "缺少 sources 数组（至少一个数据源）");
            }

            var tracks = new List<Track>();
            var anchors = new List<AnchorObservation>();
            var importDiagnostics = new JsonArray();
            int linesRead = 0;
            int sentencesUsed = 0;
            int sourcesImported = 0;

            for (int i = 0; i < sourcesNode.Count; i++)
            {
                JsonNode src = sourcesNode[i];
                if (src == null)
                {
                    throw new RequestException("BAD_REQUEST", "sources[" + i + "] 为空");
                }

                string sourceId = Str(src, "sourceId");
                if (string.IsNullOrWhiteSpace(sourceId))
                {
                    throw new RequestException("BAD_REQUEST", "sources[" + i + "].sourceId 缺失");
                }

                IEnumerable<string> lines = ReadLines(src, "sources[" + i + "]");
                var options = new VdrImportOptions
                {
                    SourceId = sourceId,
                    CaseEpochUtc = epoch,
                    DefaultDateUtc = ReadDate(src, "defaultDateUtc") ?? defaultDate,
                    TimeBasis = ReadTimeBasis(src["timeBasis"]),
                    KeepBadChecksum = src["keepBadChecksum"] != null && src["keepBadChecksum"].GetValue<bool>(),
                    EmitGnssAnchors = src["emitGnssAnchors"] == null || src["emitGnssAnchors"].GetValue<bool>()
                };

                string format = (Str(src, "format") ?? GuessFormat(src)).Trim();
                Result<VdrImportResult> imported = ImportSource(format, lines, options, src, "sources[" + i + "]");
                if (!imported.IsSuccess)
                {
                    throw new RequestException(
                        "BAD_REQUEST",
                        "sources[" + i + "]（" + sourceId + "）导入失败：" + imported.ErrorCode + " " + imported.ErrorMessage);
                }

                VdrImportResult part = imported.Value;
                tracks.AddRange(part.Tracks);
                anchors.AddRange(part.Anchors);
                linesRead += part.LinesRead;
                sentencesUsed += part.SentencesUsed;
                sourcesImported++;
                foreach (VdrDiagnostic d in part.Diagnostics)
                {
                    importDiagnostics.Add(DiagnosticJson(sourceId, d));
                }
            }

            IReadOnlyList<ManualAnchor> manual = ReadManualAnchors(req["manualAnchors"], epoch);
            IReadOnlyList<AnchorObservation> allAnchors = ManualAnchors.Merge(anchors, manual);

            var clockOffsets = new JsonArray();
            IReadOnlyList<ClockOffsetEstimate> estimates = Array.Empty<ClockOffsetEstimate>();
            string calibrationError = null;
            if (calibrate)
            {
                Result<IReadOnlyList<ClockOffsetEstimate>> estimated =
                    ClockOffsetEstimator.Estimate(allAnchors, referenceSourceId, method);
                if (estimated.IsSuccess)
                {
                    estimates = estimated.Value;
                    foreach (ClockOffsetEstimate e in estimates)
                    {
                        clockOffsets.Add(OffsetJson(e));
                    }
                }
                else
                {
                    calibrationError = estimated.ErrorCode + ": " + estimated.ErrorMessage;
                }
            }

            CalibrationResult calibration = TimelineCalibrator.Calibrate(tracks, estimates);
            ConflictThresholds thresholds = ReadThresholds(req["thresholds"]);
            ConflictDetectionResult detected = ConflictDetector.DetectWithDiagnostics(
                calibration.Timeline, thresholds, caseId);

            JsonArray conflicts = NormalizeConflicts(detected.Conflicts, caseId);
            var conflictDiagnostics = new JsonArray();
            foreach (ConflictDiagnostic d in detected.Diagnostics)
            {
                conflictDiagnostics.Add(ConflictDiagnosticJson(d));
            }

            var calibrationNode = new JsonObject
            {
                ["allCalibrated"] = calibration.AllCalibrated,
                ["uncalibratedSources"] = StringArray(calibration.UncalibratedSources),
                ["sources"] = CalibrationSourcesJson(calibration.Sources)
            };
            if (calibrationError != null)
            {
                calibrationNode["error"] = calibrationError;
            }

            JsonObject result = new JsonObject
            {
                ["caseId"] = caseId,
                ["caseEpochUtc"] = epoch.ToString("yyyy-MM-ddTHH:mm:ss.fffK", CultureInfo.InvariantCulture),
                ["referenceSourceId"] = referenceSourceId,
                ["conflicts"] = conflicts,
                ["clockOffsets"] = clockOffsets,
                ["calibration"] = calibrationNode,
                ["importDiagnostics"] = importDiagnostics,
                ["conflictDiagnostics"] = conflictDiagnostics,
                ["stats"] = new JsonObject
                {
                    ["sourcesImported"] = sourcesImported,
                    ["tracks"] = calibration.Timeline.Tracks.Count,
                    ["linesRead"] = linesRead,
                    ["sentencesUsed"] = sentencesUsed,
                    ["anchorCount"] = allAnchors.Count,
                    ["manualAnchorCount"] = manual.Count
                }
            };
            return result;
        }

        private static Result<VdrImportResult> ImportSource(
            string format,
            IEnumerable<string> lines,
            VdrImportOptions options,
            JsonNode src,
            string path)
        {
            string kind = format.ToLowerInvariant();
            if (kind == "nmea" || kind == "vdr" || kind == "nmea0183")
            {
                return VdrNmeaImporter.Import(lines, options);
            }

            if (kind == "csv")
            {
                return VdrCsvImporter.Import(lines, ReadCsvMapping(src["csvMapping"], path), options);
            }

            if (kind == "mediamanifest" || kind == "media" || kind == "manifest")
            {
                return VdrMediaManifestImporter.Import(lines, options);
            }

            throw new RequestException("BAD_REQUEST", path + ".format 无效：" + format + "（应为 nmea / csv / mediaManifest）");
        }

        private static string GuessFormat(JsonNode src)
        {
            string path = Str(src, "path") ?? "";
            string ext = Path.GetExtension(path).ToLowerInvariant();
            if (ext == ".nmea" || ext == ".txt")
            {
                return "nmea";
            }

            if (ext == ".csv")
            {
                // 媒体清单也是 csv，调用方应显式给 format。
                return "csv";
            }

            throw new RequestException("BAD_REQUEST", "无法从路径推断 format，请显式给出 nmea / csv / mediaManifest");
        }

        /// <summary>
        /// 读取 path 或 text。text 优先。path 可为绝对路径或相对当前目录。
        /// </summary>
        private static IEnumerable<string> ReadLines(JsonNode src, string path)
        {
            string text = Str(src, "text");
            if (text != null)
            {
                return SplitLines(text);
            }

            string file = Str(src, "path");
            if (string.IsNullOrWhiteSpace(file))
            {
                throw new RequestException("BAD_REQUEST", path + " 需要 text 或 path");
            }

            if (!File.Exists(file))
            {
                throw new RequestException("BAD_REQUEST", path + ".path 文件不存在：" + file);
            }

            return File.ReadAllLines(file);
        }

        private static string[] SplitLines(string text)
        {
            return text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
        }

        private static IReadOnlyList<ManualAnchor> ReadManualAnchors(JsonNode node, DateTimeOffset epoch)
        {
            if (node == null)
            {
                return Array.Empty<ManualAnchor>();
            }

            IEnumerable<string> lines = ReadLines(node, "manualAnchors");
            Result<IReadOnlyList<ManualAnchor>> result = ManualAnchorCsvImporter.Import(lines, epoch);
            if (!result.IsSuccess)
            {
                throw new RequestException("BAD_REQUEST", "人工锚点导入失败：" + result.ErrorCode + " " + result.ErrorMessage);
            }

            return result.Value;
        }

        private static VdrCsvMapping ReadCsvMapping(JsonNode node, string path)
        {
            if (node == null)
            {
                throw new RequestException("BAD_REQUEST", path + " 为 csv 时必须提供 csvMapping");
            }

            var mapping = new VdrCsvMapping
            {
                TimeColumn = Str(node, "timeColumn") ?? throw new RequestException("BAD_REQUEST", path + ".csvMapping.timeColumn 缺失"),
                TimeFormat = Str(node, "timeFormat"),
                EventColumn = Str(node, "eventColumn"),
                TimeZoneOffset = ReadTimeZoneOffset(node),
                Delimiter = ReadDelimiter(node)
            };

            JsonArray cols = node["columns"] as JsonArray;
            if (cols != null)
            {
                for (int i = 0; i < cols.Count; i++)
                {
                    JsonNode c = cols[i];
                    string column = Str(c, "column");
                    string kindName = Str(c, "kind");
                    if (string.IsNullOrWhiteSpace(column) || string.IsNullOrWhiteSpace(kindName))
                    {
                        throw new RequestException("BAD_REQUEST", path + ".csvMapping.columns[" + i + "] 需要 column 与 kind");
                    }

                    TrackKind kind;
                    if (!Enum.TryParse(kindName, true, out kind))
                    {
                        throw new RequestException("BAD_REQUEST", path + ".csvMapping.columns[" + i + "].kind 无效：" + kindName);
                    }

                    var col = new VdrCsvColumnMapping
                    {
                        Column = column,
                        Kind = kind,
                        TrackName = Str(c, "trackName"),
                        Scale = Num(c, "scale") ?? 1.0,
                        Offset = Num(c, "offset") ?? 0.0,
                        MarkChanges = c["markChanges"] != null && c["markChanges"].GetValue<bool>()
                    };

                    JsonObject tv = c["textValues"] as JsonObject;
                    if (tv != null)
                    {
                        var dict = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
                        foreach (var kv in tv)
                        {
                            dict[kv.Key] = kv.Value.GetValue<double>();
                        }

                        col.TextValues = dict;
                    }

                    mapping.Columns.Add(col);
                }
            }

            return mapping;
        }

        private static TimeSpan ReadTimeZoneOffset(JsonNode node)
        {
            double? hours = Num(node, "timeZoneOffsetHours");
            if (hours.HasValue)
            {
                return TimeSpan.FromHours(hours.Value);
            }

            string text = Str(node, "timeZoneOffset");
            if (string.IsNullOrWhiteSpace(text))
            {
                return TimeSpan.Zero;
            }

            TimeSpan ts;
            if (TimeSpan.TryParse(text.Trim().TrimStart('+'), CultureInfo.InvariantCulture, out ts))
            {
                if (text.Trim().StartsWith("-", StringComparison.Ordinal))
                {
                    return ts <= TimeSpan.Zero ? ts : -ts;
                }

                return ts;
            }

            throw new RequestException("BAD_REQUEST", "timeZoneOffset 无法解析：" + text);
        }

        private static char ReadDelimiter(JsonNode node)
        {
            string d = Str(node, "delimiter");
            if (string.IsNullOrEmpty(d))
            {
                return ',';
            }

            if (d == "\\t" || string.Equals(d, "tab", StringComparison.OrdinalIgnoreCase))
            {
                return '\t';
            }

            return d[0];
        }

        private static ConflictThresholds ReadThresholds(JsonNode n)
        {
            ConflictThresholds d = ConflictThresholds.Default;
            if (n == null)
            {
                return d;
            }

            d.HeadingDeg = Num(n, "headingDeg") ?? d.HeadingDeg;
            d.CourseDeg = Num(n, "courseDeg") ?? d.CourseDeg;
            d.SpeedKn = Num(n, "speedKn") ?? d.SpeedKn;
            d.RudderDeg = Num(n, "rudderDeg") ?? d.RudderDeg;
            d.RateOfTurnDegPerMin = Num(n, "rateOfTurnDegPerMin") ?? d.RateOfTurnDegPerMin;
            d.PositionM = Num(n, "positionM") ?? d.PositionM;
            d.TargetRangeNm = Num(n, "targetRangeNm") ?? d.TargetRangeNm;
            d.TargetBearingDeg = Num(n, "targetBearingDeg") ?? d.TargetBearingDeg;
            d.SampleStepSeconds = Num(n, "sampleStepSeconds") ?? d.SampleStepSeconds;
            d.MinDurationSeconds = Num(n, "minDurationSeconds") ?? d.MinDurationSeconds;
            d.TargetPositionM = Num(n, "targetPositionM") ?? d.TargetPositionM;
            d.EventTimeSeconds = Num(n, "eventTimeSeconds") ?? d.EventTimeSeconds;
            d.Tolerance = Num(n, "tolerance") ?? d.Tolerance;

            JsonObject aliases = n["eventAliases"] as JsonObject;
            if (aliases != null)
            {
                foreach (var kv in aliases)
                {
                    d.EventAliases[kv.Key] = kv.Value == null ? null : kv.Value.ToString();
                }
            }

            return d;
        }

        private static JsonArray NormalizeConflicts(IReadOnlyList<TimelineConflict> conflicts, string caseId)
        {
            var prepared = new List<TimelineConflict>();
            if (conflicts != null)
            {
                foreach (TimelineConflict conflict in conflicts)
                {
                    TimelineConflict item = conflict;
                    if (item == null)
                    {
                        continue;
                    }

                    // 适配层先补 caseId，再走 TryToJsonArray；ToJson 在 caseId 为空时仍会写 null，故不使用。
                    if (string.IsNullOrWhiteSpace(item.CaseId))
                    {
                        item = item.WithCaseId(caseId);
                    }

                    prepared.Add(item);
                }
            }

            Result<string> json = ConflictJsonWriter.TryToJsonArray(prepared);
            if (!json.IsSuccess)
            {
                throw new RequestException(
                    json.ErrorCode ?? "BAD_REQUEST",
                    json.ErrorMessage ?? "冲突序列化失败");
            }

            // 用 JsonDocument 重建节点，避免 JsonNode.Parse 的树在 Program.Write 里
            // 因 JsonSerializerOptions 缺 TypeInfoResolver 而抛 InvalidOperationException。
            JsonArray arr = FreshArray(json.Value);

            return arr;
        }

        private static JsonArray FreshArray(string json)
        {
            using (JsonDocument doc = JsonDocument.Parse(json))
            {
                return (JsonArray)FromElement(doc.RootElement);
            }
        }

        private static JsonNode FromElement(JsonElement element)
        {
            switch (element.ValueKind)
            {
                case JsonValueKind.Object:
                    var obj = new JsonObject();
                    foreach (JsonProperty property in element.EnumerateObject())
                    {
                        obj[property.Name] = FromElement(property.Value);
                    }
                    return obj;
                case JsonValueKind.Array:
                    var arr = new JsonArray();
                    foreach (JsonElement child in element.EnumerateArray())
                    {
                        arr.Add(FromElement(child));
                    }
                    return arr;
                case JsonValueKind.String:
                    return JsonValue.Create(element.GetString());
                case JsonValueKind.Number:
                    if (element.TryGetInt64(out long l))
                    {
                        // 合同里 timeSec/delta 等可能是整数或小数；有小数时走 double。
                        if (element.GetRawText().IndexOf('.') >= 0 || element.GetRawText().IndexOf('e') >= 0 ||
                            element.GetRawText().IndexOf('E') >= 0)
                        {
                            return JsonValue.Create(element.GetDouble());
                        }
                        return JsonValue.Create(l);
                    }
                    return JsonValue.Create(element.GetDouble());
                case JsonValueKind.True:
                    return JsonValue.Create(true);
                case JsonValueKind.False:
                    return JsonValue.Create(false);
                default:
                    return null;
            }
        }

        private static JsonObject OffsetJson(ClockOffsetEstimate e)
        {
            var rejected = new JsonArray();
            if (e.RejectedAnchors != null)
            {
                foreach (RejectedAnchor r in e.RejectedAnchors)
                {
                    rejected.Add(new JsonObject
                    {
                        ["eventKey"] = r.EventKey,
                        ["differenceSeconds"] = Finite(r.DifferenceSeconds),
                        ["residualSeconds"] = Finite(r.ResidualSeconds),
                        ["excludedFromFit"] = r.ExcludedFromFit,
                        ["reason"] = r.Reason
                    });
                }
            }

            return new JsonObject
            {
                ["sourceId"] = e.SourceId,
                ["referenceSourceId"] = e.ReferenceSourceId,
                ["offsetSeconds"] = Finite(e.OffsetSeconds),
                ["uncertaintySeconds"] = Finite(e.UncertaintySeconds),
                ["anchorCount"] = e.AnchorCount,
                ["usedAnchorCount"] = e.UsedAnchorCount,
                ["manualAnchorCount"] = e.ManualAnchorCount,
                ["method"] = e.Method.ToString(),
                ["isReference"] = e.IsReference,
                ["status"] = e.Status.ToString(),
                ["viaSourceId"] = e.ViaSourceId,
                ["rejectedAnchors"] = rejected
            };
        }

        private static JsonArray CalibrationSourcesJson(IReadOnlyList<SourceCalibration> sources)
        {
            var arr = new JsonArray();
            if (sources == null)
            {
                return arr;
            }

            foreach (SourceCalibration s in sources)
            {
                arr.Add(new JsonObject
                {
                    ["sourceId"] = s.SourceId,
                    ["status"] = s.Status.ToString(),
                    ["offsetSeconds"] = Finite(s.OffsetSeconds),
                    ["uncertaintySeconds"] = Finite(s.UncertaintySeconds),
                    ["anchorCount"] = s.AnchorCount,
                    ["manualAnchorCount"] = s.ManualAnchorCount,
                    ["viaSourceId"] = s.ViaSourceId,
                    ["description"] = s.Description
                });
            }

            return arr;
        }

        private static JsonObject DiagnosticJson(string sourceId, VdrDiagnostic d)
        {
            return new JsonObject
            {
                ["sourceId"] = sourceId,
                ["severity"] = d.Severity.ToString(),
                ["lineNumber"] = d.LineNumber,
                ["code"] = d.Code,
                ["message"] = d.Message
            };
        }

        private static JsonObject ConflictDiagnosticJson(ConflictDiagnostic d)
        {
            var obj = new JsonObject
            {
                ["code"] = d.Code,
                ["trackKind"] = d.Kind.ToString(),
                ["sourceId"] = d.SourceId,
                ["trackId"] = d.TrackId,
                ["message"] = d.Message,
                ["reason"] = d.Reason
            };
            if (d.Range.HasValue)
            {
                obj["range"] = new JsonObject
                {
                    ["startSec"] = d.Range.Value.Start.Seconds,
                    ["endSec"] = d.Range.Value.End.Seconds
                };
            }

            return obj;
        }

        private static JsonArray StringArray(IReadOnlyList<string> items)
        {
            var arr = new JsonArray();
            if (items == null)
            {
                return arr;
            }

            foreach (string s in items)
            {
                arr.Add(s);
            }

            return arr;
        }

        private static OffsetMethod ReadOffsetMethod(JsonNode n)
        {
            if (n == null)
            {
                return OffsetMethod.Median;
            }

            OffsetMethod method;
            if (!Enum.TryParse(n.ToString(), true, out method))
            {
                throw new RequestException("BAD_REQUEST", "offsetMethod 无效：" + n + "（应为 Median 或 LeastSquares）");
            }

            return method;
        }

        private static VdrTimeBasis ReadTimeBasis(JsonNode n)
        {
            if (n == null)
            {
                return VdrTimeBasis.LogPrefix;
            }

            VdrTimeBasis basis;
            if (!Enum.TryParse(n.ToString(), true, out basis))
            {
                throw new RequestException("BAD_REQUEST", "timeBasis 无效：" + n + "（应为 LogPrefix 或 GnssSentenceTime）");
            }

            return basis;
        }

        private static DateTimeOffset? ReadDateTimeOffset(JsonNode n, string key, bool required)
        {
            string text = Str(n, key);
            if (string.IsNullOrWhiteSpace(text))
            {
                if (required)
                {
                    throw new RequestException("BAD_REQUEST", "缺少 " + key);
                }

                return null;
            }

            DateTimeOffset value;
            if (!DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out value))
            {
                throw new RequestException("BAD_REQUEST", key + " 无法解析：" + text);
            }

            return value;
        }

        private static DateTime? ReadDate(JsonNode n, string key)
        {
            string text = Str(n, key);
            if (string.IsNullOrWhiteSpace(text))
            {
                return null;
            }

            DateTime value;
            if (DateTime.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out value))
            {
                return DateTime.SpecifyKind(value, DateTimeKind.Utc);
            }

            throw new RequestException("BAD_REQUEST", key + " 无法解析：" + text);
        }

        private static JsonNode Finite(double d)
        {
            return double.IsNaN(d) || double.IsInfinity(d) ? null : JsonValue.Create(d);
        }

        private static double? Num(JsonNode n, string key)
        {
            JsonNode v = n?[key];
            if (v == null)
            {
                return null;
            }

            try
            {
                return v.GetValue<double>();
            }
            catch (Exception)
            {
                throw new RequestException("BAD_REQUEST", key + " 应为数字");
            }
        }

        private static string Str(JsonNode n, string key)
        {
            JsonNode v = n?[key];
            if (v == null || v.GetValueKind() == JsonValueKind.Null)
            {
                return null;
            }

            return v.GetValueKind() == JsonValueKind.String ? v.GetValue<string>() : v.ToString();
        }
    }
}
