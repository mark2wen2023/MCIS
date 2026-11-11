using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// 将 VDR 记录的 NMEA 0183 文本导入为时间轴轨道与钟差锚点。
    /// 支持 RMC、GGA、VTG、HDT、ROT、RSA、TTM、TLL、ZDA。
    /// </summary>
    public static class VdrNmeaImporter
    {
        /// <summary>
        /// IEC 61162-1 规定的语句最大长度 82 字符，含行尾 CR/LF。保留此常量以兼容旧接口；
        /// W2.1 架构裁定：实际判定口径为不含 CRLF 的 '$'/'!' 至 "*hh" 长度，上限 80。
        /// </summary>
        public const int MaxSentenceLength = 82;

        /// <summary>
        /// 不含行尾 CR/LF 的最大语句长度（'$'/'!' 至 "*hh"）。W2.1 架构裁定：&gt;80 即告警，仍宽松解析。
        /// </summary>
        public const int MaxSentenceLengthExcludingCrLf = 80;

        /// <summary>
        /// 前缀时间与标签块时间都有效且相差超过该阈值加容差（秒）时，发出 Info 级 vdr_timesource_mismatch。
        /// 判定为 &gt; 阈值 + <see cref="TimeSourceMismatchToleranceSeconds"/>，与冲突检测一致（W2.3）。
        /// 与冲突检测 C-02 / EventTimeSeconds 默认 2 s 一致；相差正好等于阈值，或在阈值 + 容差以内时不报。
        /// </summary>
        public const double TimeSourceMismatchThresholdSeconds = 2.0;

        /// <summary>时间源差判定容差（秒），与冲突检测默认 Tolerance 相同，为 1e-6。</summary>
        public const double TimeSourceMismatchToleranceSeconds = 1e-6;

        /// <summary>
        /// 导入 NMEA 行集合。
        /// </summary>
        /// <param name="lines">NMEA 文本行（支持 '#' 注释行与空行）。</param>
        /// <param name="options">导入选项。</param>
        /// <returns>导入结果；选项非法时失败。</returns>
        public static Result<VdrImportResult> Import(IEnumerable<string> lines, VdrImportOptions options)
        {
            Result<VdrImportResult> validation = Validate(options);
            if (!validation.IsSuccess)
            {
                return validation;
            }

            ImportState state = new ImportState(options);
            if (lines != null)
            {
                int lineNumber = 0;
                foreach (string line in lines)
                {
                    lineNumber++;
                    state.LinesRead++;
                    if (line == null)
                    {
                        continue;
                    }

                    string trimmed = line.Trim();
                    if (trimmed.Length > 0 && trimmed[0] == '\uFEFF')
                    {
                        trimmed = trimmed.Substring(1).TrimStart();
                    }

                    if (trimmed.Length == 0 || trimmed[0] == '#')
                    {
                        continue;
                    }

                    NmeaSentence sentence;
                    string error;
                    if (!NmeaParser.TryParse(line, out sentence, out error))
                    {
                        state.AddDiagnostic(lineNumber, "vdr_parse_error", error);
                        continue;
                    }

                    if (sentence.SentenceLength > MaxSentenceLengthExcludingCrLf)
                    {
                        state.AddDiagnostic(
                            lineNumber,
                            "vdr_line_too_long",
                            string.Format(
                                CultureInfo.InvariantCulture,
                                "NMEA 语句不含 CRLF 计 {0} 字符，上限 {1}（含 CRLF {2}），超过 IEC 61162-1 上限（仍按宽松规则解析）。",
                                sentence.SentenceLength,
                                MaxSentenceLengthExcludingCrLf,
                                MaxSentenceLength));
                    }

                    if (!sentence.ChecksumValid && !options.KeepBadChecksum)
                    {
                        state.EnsureUnusedTimeSourceDiagnostics(sentence, lineNumber);
                        state.AddDiagnostic(
                            lineNumber,
                            "vdr_bad_checksum",
                            "NMEA 校验和错误，已丢弃：" + sentence.Raw);
                        continue;
                    }

                    state.SentencesUsed++;
                    try
                    {
                        state.Process(sentence, lineNumber);
                    }
                    catch (Exception ex)
                    {
                        // 单行处理异常只记诊断并跳过，绝不中止整批导入（W2-D01）。
                        state.SentencesUsed--;
                        state.AddDiagnostic(
                            lineNumber,
                            "vdr_parse_error",
                            "处理语句时出错（" + ex.GetType().Name + "），已跳过该行。");
                    }

                    // 兜底：该行未走到时间选择（未支持句型、处理异常等）时，仍报告无效的标签块/日志前缀。
                    state.EnsureUnusedTimeSourceDiagnostics(sentence, lineNumber);
                }
            }

            return Result<VdrImportResult>.Ok(state.BuildResult());
        }

        /// <summary>
        /// 导入 NMEA 文本（按 CRLF/LF/CR 拆分为行）。
        /// </summary>
        /// <param name="text">NMEA 全文。</param>
        /// <param name="options">导入选项。</param>
        /// <returns>导入结果；选项非法时失败。</returns>
        public static Result<VdrImportResult> ImportText(string text, VdrImportOptions options)
        {
            if (text == null)
            {
                return Import(new string[0], options);
            }

            string[] lines = text.Split(
                new[] { "\r\n", "\n", "\r" },
                StringSplitOptions.None);
            return Import(lines, options);
        }

        private static Result<VdrImportResult> Validate(VdrImportOptions options)
        {
            if (options == null)
            {
                return Result<VdrImportResult>.Fail("vdr_options", "导入选项不能为空。");
            }

            if (string.IsNullOrWhiteSpace(options.SourceId))
            {
                return Result<VdrImportResult>.Fail("vdr_missing_source", "必须指定数据源标识 SourceId。");
            }

            return Result<VdrImportResult>.Ok(null);
        }

        private sealed class ImportState
        {
            private readonly VdrImportOptions _options;
            private readonly Dictionary<string, TrackBuilder> _tracks =
                new Dictionary<string, TrackBuilder>(StringComparer.Ordinal);
            private readonly List<AnchorObservation> _anchors = new List<AnchorObservation>();
            private readonly HashSet<string> _anchorKeys = new HashSet<string>(StringComparer.Ordinal);
            private readonly List<VdrDiagnostic> _diagnostics = new List<VdrDiagnostic>();
            private readonly HashSet<string> _unsupportedTypes = new HashSet<string>(StringComparer.Ordinal);
            private readonly HashSet<string> _fallbackDiagnostics = new HashSet<string>(StringComparer.Ordinal);
            private DateTime? _currentDate;
            private DateTimeOffset? _lastGnssUtc;

            public int LinesRead;
            public int SentencesUsed;

            public ImportState(VdrImportOptions options)
            {
                _options = options;
                if (options.DefaultDateUtc.HasValue)
                {
                    _currentDate = DateTime.SpecifyKind(options.DefaultDateUtc.Value.Date, DateTimeKind.Utc);
                }
            }

            public void AddDiagnostic(int lineNumber, string code, string message)
            {
                _diagnostics.Add(new VdrDiagnostic(lineNumber, code, message, VdrDiagnostic.DefaultSeverityFor(code)));
            }

            /// <summary>
            /// 兜底诊断：标签块校验和无效或日志前缀无法解析、但该行没有进入时间选择时，
            /// 同样报告被弃用的时间源（同一行同一代码只发一次）。
            /// </summary>
            public void EnsureUnusedTimeSourceDiagnostics(NmeaSentence sentence, int lineNumber)
            {
                if (sentence.HasTagBlock && !sentence.TagBlockChecksumValid)
                {
                    AddFallbackDiagnostic(
                        lineNumber,
                        "vdr_tagblock_invalid",
                        "标签块校验和缺失或错误，不采信其时间（该行未使用时间）：" + sentence.Raw);
                }

                bool validTagBlock = sentence.HasTagBlock && sentence.TagBlockChecksumValid && sentence.TagBlockTimeUtc.HasValue;
                if (!validTagBlock && sentence.HasLogPrefix && !sentence.LogPrefixValid)
                {
                    AddFallbackDiagnostic(
                        lineNumber,
                        "vdr_logprefix_invalid",
                        "日志前缀「" + (sentence.LogPrefixText ?? string.Empty) + "」无法解析为时间（该行未使用时间）：" + sentence.Raw);
                }

                EmitTimeSourceMismatchIfNeeded(sentence, lineNumber);
            }

            private void AddFallbackDiagnostic(int lineNumber, string code, string message)
            {
                // 同一行同一代码只发一次（W2.1）；TryResolveTime 与 EmitGnssAnchors 可能都会触达。
                string key = lineNumber.ToString(CultureInfo.InvariantCulture) + "|" + code;
                if (_fallbackDiagnostics.Add(key))
                {
                    AddDiagnostic(lineNumber, code, message);
                }
            }

            /// <summary>
            /// 前缀时间与标签块时间都有效且相差 &gt; 2 s + 1e-6 时，发一条 Info 级 vdr_timesource_mismatch。
            /// 相差正好 2 s、在容差以内、或只有一侧有效时不报。同一行只发一次。诊断文字中的时间差保留 3 位小数。
            /// </summary>
            private void EmitTimeSourceMismatchIfNeeded(NmeaSentence sentence, int lineNumber)
            {
                bool validTagBlock = sentence.HasTagBlock &&
                                     sentence.TagBlockChecksumValid &&
                                     sentence.TagBlockTimeUtc.HasValue;
                bool validLogPrefix = sentence.LogPrefixValid && sentence.LogTimestampUtc.HasValue;
                if (!validTagBlock || !validLogPrefix)
                {
                    return;
                }

                double deltaSeconds = Math.Abs(
                    (sentence.TagBlockTimeUtc.Value - sentence.LogTimestampUtc.Value).TotalSeconds);
                if (deltaSeconds <= TimeSourceMismatchThresholdSeconds + TimeSourceMismatchToleranceSeconds)
                {
                    return;
                }

                AddFallbackDiagnostic(
                    lineNumber,
                    "vdr_timesource_mismatch",
                    string.Format(
                        CultureInfo.InvariantCulture,
                        "日志前缀时间 {0} 与标签块时间 {1} 相差 {2} s，超过 {3} s。",
                        sentence.LogTimestampUtc.Value.ToString("yyyy-MM-ddTHH:mm:ss.fffK", CultureInfo.InvariantCulture),
                        sentence.TagBlockTimeUtc.Value.ToString("yyyy-MM-ddTHH:mm:ss.fffK", CultureInfo.InvariantCulture),
                        deltaSeconds.ToString("0.000", CultureInfo.InvariantCulture),
                        TimeSourceMismatchThresholdSeconds.ToString("0.###", CultureInfo.InvariantCulture)));
            }

            public VdrImportResult BuildResult()
            {
                List<Track> tracks = new List<Track>(_tracks.Count);
                foreach (TrackBuilder builder in _tracks.Values)
                {
                    tracks.Add(builder.Build(_options.SourceId));
                }

                tracks.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));
                return new VdrImportResult(
                    _options.SourceId,
                    tracks,
                    _anchors.ToArray(),
                    _diagnostics.ToArray(),
                    LinesRead,
                    SentencesUsed);
            }

            public void Process(NmeaSentence sentence, int lineNumber)
            {
                string type = (sentence.Type ?? string.Empty).ToUpperInvariant();
                switch (type)
                {
                    case "RMC":
                        ProcessRmc(sentence, lineNumber);
                        break;
                    case "GGA":
                        ProcessGga(sentence, lineNumber);
                        break;
                    case "VTG":
                        ProcessVtg(sentence, lineNumber);
                        break;
                    case "HDT":
                        ProcessHdt(sentence, lineNumber);
                        break;
                    case "ROT":
                        ProcessRot(sentence, lineNumber);
                        break;
                    case "RSA":
                        ProcessRsa(sentence, lineNumber);
                        break;
                    case "TTM":
                        ProcessTtm(sentence, lineNumber);
                        break;
                    case "TLL":
                        ProcessTll(sentence, lineNumber);
                        break;
                    case "ZDA":
                        ProcessZda(sentence, lineNumber);
                        break;
                    default:
                        if (_unsupportedTypes.Add(type))
                        {
                            AddDiagnostic(
                                lineNumber,
                                "vdr_unsupported",
                                "不支持的 NMEA 语句类型：" + type);
                        }
                        break;
                }
            }

            private void ProcessRmc(NmeaSentence sentence, int lineNumber)
            {
                string status = Trim(sentence.Field(1));
                if (!string.Equals(status, "A", StringComparison.OrdinalIgnoreCase))
                {
                    return;
                }

                DateTime parsedDate;
                DateTime date;
                bool dated = TryParseNmeaDate(sentence.Field(8), out parsedDate);
                if (dated)
                {
                    date = parsedDate;
                    _currentDate = date;
                }
                else if (_currentDate.HasValue)
                {
                    date = _currentDate.Value;
                }
                else
                {
                    AddDiagnostic(lineNumber, "vdr_no_time", "RMC 缺少有效日期且无默认日期。");
                    return;
                }

                TimeSpan timeOfDay;
                if (!NmeaParser.TryParseUtcTime(sentence.Field(0), out timeOfDay))
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "RMC 时间字段无效。");
                    return;
                }

                DateTimeOffset sentenceUtc = dated
                    ? CombineUtc(date, timeOfDay)
                    : CombineUndated(timeOfDay, lineNumber);
                _lastGnssUtc = sentenceUtc;

                SimTime time;
                if (!TryResolveTime(sentence, sentenceUtc, lineNumber, out time))
                {
                    return;
                }

                double lat;
                double lon;
                if (NmeaParser.TryParseLatLon(sentence.Field(2), sentence.Field(3), true, out lat) &&
                    NmeaParser.TryParseLatLon(sentence.Field(4), sentence.Field(5), false, out lon))
                {
                    AddSample(
                        TrackId(TrackKind.Position),
                        TrackKind.Position,
                        TimelineSample.AtPosition(time, new GeoCoord(lon, lat, 0.0)));
                }

                double sog;
                if (TryParseDouble(sentence.Field(6), out sog))
                {
                    AddSample(
                        TrackId(TrackKind.SpeedOverGround),
                        TrackKind.SpeedOverGround,
                        TimelineSample.Scalar(time, sog));
                }

                double cog;
                if (TryParseDouble(sentence.Field(7), out cog))
                {
                    AddSample(
                        TrackId(TrackKind.CourseOverGround),
                        TrackKind.CourseOverGround,
                        TimelineSample.Scalar(time, AngleMath.Normalize360(cog)));
                }

                EmitGnssAnchors(sentenceUtc, sentence, lineNumber);
            }

            private void ProcessGga(NmeaSentence sentence, int lineNumber)
            {
                int quality;
                if (!int.TryParse(
                    Trim(sentence.Field(5)),
                    NumberStyles.Integer,
                    CultureInfo.InvariantCulture,
                    out quality) || quality <= 0)
                {
                    return;
                }

                if (!_currentDate.HasValue)
                {
                    AddDiagnostic(lineNumber, "vdr_no_time", "GGA 缺少日期且未配置 DefaultDateUtc。");
                    return;
                }

                TimeSpan timeOfDay;
                if (!NmeaParser.TryParseUtcTime(sentence.Field(0), out timeOfDay))
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "GGA 时间字段无效。");
                    return;
                }

                DateTimeOffset sentenceUtc = CombineUndated(timeOfDay, lineNumber);
                _lastGnssUtc = sentenceUtc;

                SimTime time;
                if (!TryResolveTime(sentence, sentenceUtc, lineNumber, out time))
                {
                    return;
                }

                double lat;
                double lon;
                if (NmeaParser.TryParseLatLon(sentence.Field(1), sentence.Field(2), true, out lat) &&
                    NmeaParser.TryParseLatLon(sentence.Field(3), sentence.Field(4), false, out lon))
                {
                    double height = 0.0;
                    double altitude;
                    if (TryParseDouble(sentence.Field(8), out altitude))
                    {
                        height = altitude;
                    }

                    AddSample(
                        TrackId(TrackKind.Position),
                        TrackKind.Position,
                        TimelineSample.AtPosition(time, new GeoCoord(lon, lat, height)));
                }

                EmitGnssAnchors(sentenceUtc, sentence, lineNumber);
            }

            private void ProcessVtg(NmeaSentence sentence, int lineNumber)
            {
                SimTime time;
                if (!TryResolveTime(sentence, null, lineNumber, out time))
                {
                    return;
                }

                double cog;
                if (TryParseDouble(sentence.Field(0), out cog))
                {
                    AddSample(
                        TrackId(TrackKind.CourseOverGround),
                        TrackKind.CourseOverGround,
                        TimelineSample.Scalar(time, AngleMath.Normalize360(cog)));
                }

                double sog;
                if (TryParseDouble(sentence.Field(4), out sog))
                {
                    AddSample(
                        TrackId(TrackKind.SpeedOverGround),
                        TrackKind.SpeedOverGround,
                        TimelineSample.Scalar(time, sog));
                }
            }

            private void ProcessHdt(NmeaSentence sentence, int lineNumber)
            {
                SimTime time;
                if (!TryResolveTime(sentence, null, lineNumber, out time))
                {
                    return;
                }

                double heading;
                if (TryParseDouble(sentence.Field(0), out heading))
                {
                    AddSample(
                        TrackId(TrackKind.Heading),
                        TrackKind.Heading,
                        TimelineSample.Scalar(time, AngleMath.Normalize360(heading)));
                }
            }

            private void ProcessRot(NmeaSentence sentence, int lineNumber)
            {
                string status = Trim(sentence.Field(1));
                if (!string.IsNullOrEmpty(status) &&
                    !string.Equals(status, "A", StringComparison.OrdinalIgnoreCase))
                {
                    return;
                }

                SimTime time;
                if (!TryResolveTime(sentence, null, lineNumber, out time))
                {
                    return;
                }

                double rate;
                if (TryParseDouble(sentence.Field(0), out rate))
                {
                    AddSample(
                        TrackId(TrackKind.RateOfTurn),
                        TrackKind.RateOfTurn,
                        TimelineSample.Scalar(time, rate));
                }
            }

            private void ProcessRsa(NmeaSentence sentence, int lineNumber)
            {
                SimTime time;
                if (!TryResolveTime(sentence, null, lineNumber, out time))
                {
                    return;
                }

                double starboard;
                double port;
                string starboardStatus = Trim(sentence.Field(1));
                string portStatus = Trim(sentence.Field(3));
                if (string.Equals(starboardStatus, "A", StringComparison.OrdinalIgnoreCase) &&
                    TryParseDouble(sentence.Field(0), out starboard))
                {
                    AddSample(
                        TrackId(TrackKind.RudderAngle),
                        TrackKind.RudderAngle,
                        TimelineSample.Scalar(time, starboard));
                }
                else if (string.Equals(portStatus, "A", StringComparison.OrdinalIgnoreCase) &&
                         TryParseDouble(sentence.Field(2), out port))
                {
                    AddSample(
                        TrackId(TrackKind.RudderAngle),
                        TrackKind.RudderAngle,
                        TimelineSample.Scalar(time, -port));
                }
            }

            private void ProcessTtm(NmeaSentence sentence, int lineNumber)
            {
                int targetNumber;
                if (!TryParseInt(sentence.Field(0), out targetNumber))
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "TTM 目标号无效。");
                    return;
                }

                SimTime time;
                if (!TryResolveTime(sentence, null, lineNumber, out time))
                {
                    return;
                }

                string name = Trim(sentence.Field(10));
                if (name.Length == 0)
                {
                    name = null;
                }

                double distance;
                if (TryParseDouble(sentence.Field(1), out distance))
                {
                    AddSample(
                        TargetTrackId(targetNumber, TrackKind.TargetRange),
                        TrackKind.TargetRange,
                        TimelineSample.Scalar(time, distance, name));
                }

                double bearing;
                if (TryParseDouble(sentence.Field(2), out bearing))
                {
                    string bearingUnit = Trim(sentence.Field(3));
                    bool relative = string.Equals(bearingUnit, "R", StringComparison.OrdinalIgnoreCase);
                    if (relative)
                    {
                        double heading;
                        if (TryGetLatestScalar(TrackKind.Heading, time, out heading))
                        {
                            bearing = heading + bearing;
                            AddSample(
                                TargetTrackId(targetNumber, TrackKind.TargetBearing),
                                TrackKind.TargetBearing,
                                TimelineSample.Scalar(time, AngleMath.Normalize360(bearing), name));
                        }
                        else
                        {
                            // W2-D09：相对方位缺船首向时不得当作真方位入库，也不能换算。
                            double relativeBearing = AngleMath.Normalize360(bearing);
                            string relativeTrackId =
                                TargetTrackId(targetNumber, TrackKind.TargetBearing) + "/REL";
                            AddSample(
                                relativeTrackId,
                                TrackKind.TargetBearing,
                                TimelineSample.Scalar(time, relativeBearing, name),
                                BearingReference.Relative);
                            AddDiagnostic(
                                lineNumber,
                                "vdr_relative_bearing_no_heading",
                                string.Format(
                                    CultureInfo.InvariantCulture,
                                    "第 {0} 行：目标 {1} 的方位为相对方位 {2:0.0###}°（R），此前没有船首向样本，真方位 NotAvailable；已保留相对方位原值于轨道 {3}。",
                                    lineNumber,
                                    targetNumber,
                                    relativeBearing,
                                    relativeTrackId));
                        }
                    }
                    else
                    {
                        AddSample(
                            TargetTrackId(targetNumber, TrackKind.TargetBearing),
                            TrackKind.TargetBearing,
                            TimelineSample.Scalar(time, AngleMath.Normalize360(bearing), name));
                    }
                }
            }

            private void ProcessTll(NmeaSentence sentence, int lineNumber)
            {
                int targetNumber;
                if (!TryParseInt(sentence.Field(0), out targetNumber))
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "TLL 目标号无效。");
                    return;
                }

                SimTime time;
                if (!TryResolveTime(sentence, null, lineNumber, out time))
                {
                    return;
                }

                double lat;
                double lon;
                if (!NmeaParser.TryParseLatLon(sentence.Field(1), sentence.Field(2), true, out lat) ||
                    !NmeaParser.TryParseLatLon(sentence.Field(3), sentence.Field(4), false, out lon))
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "TLL 经纬度无效。");
                    return;
                }

                string name = Trim(sentence.Field(5));
                AddSample(
                    TargetTrackId(targetNumber, TrackKind.TargetPosition),
                    TrackKind.TargetPosition,
                    TimelineSample.AtPosition(time, new GeoCoord(lon, lat, 0.0), name.Length == 0 ? null : name));
            }

            private void ProcessZda(NmeaSentence sentence, int lineNumber)
            {
                TimeSpan timeOfDay;
                int day;
                int month;
                int year;
                if (!NmeaParser.TryParseUtcTime(sentence.Field(0), out timeOfDay) ||
                    !TryParseInt(sentence.Field(1), out day) ||
                    !TryParseInt(sentence.Field(2), out month) ||
                    !TryParseInt(sentence.Field(3), out year))
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "ZDA 日期或时间字段无效。");
                    return;
                }

                DateTime date;
                try
                {
                    date = new DateTime(year, month, day, 0, 0, 0, DateTimeKind.Utc);
                }
                catch (ArgumentOutOfRangeException)
                {
                    AddDiagnostic(lineNumber, "vdr_parse_error", "ZDA 日期越界。");
                    return;
                }

                _currentDate = date;
                DateTimeOffset sentenceUtc = CombineUtc(date, timeOfDay);
                _lastGnssUtc = sentenceUtc;
                EmitGnssAnchors(sentenceUtc, sentence, lineNumber);
            }

            /// <summary>
            /// 无日期字段的 GNSS 时刻：沿用当前日期；若比上一 GNSS 时刻早 12 h 以上（如 23:59:50 → 00:00:10），
            /// 视为跨午夜，日期加 1 天（W2-D02）。
            /// </summary>
            private DateTimeOffset CombineUndated(TimeSpan timeOfDay, int lineNumber)
            {
                DateTimeOffset candidate = CombineUtc(_currentDate.Value, timeOfDay);
                if (_lastGnssUtc.HasValue && (candidate - _lastGnssUtc.Value) < TimeSpan.FromHours(-12))
                {
                    _currentDate = _currentDate.Value.AddDays(1);
                    candidate = candidate.AddDays(1);
                    AddDiagnostic(
                        lineNumber,
                        "vdr_date_rollover",
                        "检测到跨午夜，日期滚动到 " +
                        _currentDate.Value.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) + "。");
                }

                return candidate;
            }

            private static DateTimeOffset? DeviceTime(NmeaSentence sentence)
            {
                // 设备时钟优先级（W2.1 / 裁定 3）：有效标签块 > 有效日志前缀。
                if (sentence.HasTagBlock && sentence.TagBlockChecksumValid && sentence.TagBlockTimeUtc.HasValue)
                {
                    return sentence.TagBlockTimeUtc;
                }

                if (sentence.LogPrefixValid && sentence.LogTimestampUtc.HasValue)
                {
                    return sentence.LogTimestampUtc;
                }

                return null;
            }

            private DateTimeOffset? SelectUtc(NmeaSentence sentence, DateTimeOffset? sentenceUtc)
            {
                DateTimeOffset? tagBlock = sentence.HasTagBlock &&
                                          sentence.TagBlockChecksumValid &&
                                          sentence.TagBlockTimeUtc.HasValue
                    ? sentence.TagBlockTimeUtc
                    : null;
                DateTimeOffset? logPrefix = sentence.LogPrefixValid && sentence.LogTimestampUtc.HasValue
                    ? sentence.LogTimestampUtc
                    : null;

                if (_options.TimeBasis == VdrTimeBasis.GnssSentenceTime)
                {
                    // 基准行为保持不变：句内 GNSS 时间优先，其后才是设备时钟。
                    return sentenceUtc ?? tagBlock ?? logPrefix ?? _lastGnssUtc;
                }

                // 裁定 3：有效标签块 > 有效日志前缀 > 句内时间 > 最近 GNSS 时间。
                return tagBlock ?? logPrefix ?? sentenceUtc ?? _lastGnssUtc;
            }

            private bool TryResolveTime(
                NmeaSentence sentence,
                DateTimeOffset? sentenceUtc,
                int lineNumber,
                out SimTime time)
            {
                time = SimTime.Zero;
                EmitFallbackDiagnostics(sentence, sentenceUtc, lineNumber);

                DateTimeOffset? utc = SelectUtc(sentence, sentenceUtc);
                if (!utc.HasValue)
                {
                    AddDiagnostic(
                        lineNumber,
                        "vdr_no_time",
                        "语句没有可用的时间（无前缀、无 GNSS 时间）。");
                    return false;
                }

                time = SimTime.FromUtc(utc.Value, _options.CaseEpochUtc);
                return true;
            }

            private void EmitFallbackDiagnostics(
                NmeaSentence sentence,
                DateTimeOffset? sentenceUtc,
                int lineNumber)
            {
                bool validTagBlock = sentence.HasTagBlock &&
                                     sentence.TagBlockChecksumValid &&
                                     sentence.TagBlockTimeUtc.HasValue;
                bool validLogPrefix = sentence.LogPrefixValid && sentence.LogTimestampUtc.HasValue;

                if (sentence.HasTagBlock && !sentence.TagBlockChecksumValid)
                {
                    AddFallbackDiagnostic(
                        lineNumber,
                        "vdr_tagblock_invalid",
                        "标签块校验和缺失或错误，不采信其时间，" +
                        FallbackTarget(sentence, sentenceUtc, validLogPrefix) +
                        "：" + sentence.Raw);
                }

                if (!validTagBlock && sentence.HasLogPrefix && !validLogPrefix)
                {
                    string prefixText = string.IsNullOrEmpty(sentence.LogPrefixText)
                        ? "(空)"
                        : sentence.LogPrefixText;
                    AddFallbackDiagnostic(
                        lineNumber,
                        "vdr_logprefix_invalid",
                        "日志前缀「" + prefixText + "」无法解析为时间，" +
                        LogPrefixFallbackTarget(sentenceUtc) +
                        "：" + sentence.Raw);
                }

                EmitTimeSourceMismatchIfNeeded(sentence, lineNumber);
            }

            private string FallbackTarget(
                NmeaSentence sentence,
                DateTimeOffset? sentenceUtc,
                bool validLogPrefix)
            {
                if (_options.TimeBasis == VdrTimeBasis.GnssSentenceTime)
                {
                    if (sentenceUtc.HasValue)
                    {
                        return "回落到句内时间";
                    }
                    if (validLogPrefix)
                    {
                        return "回落到日志前缀";
                    }
                }
                else
                {
                    if (validLogPrefix)
                    {
                        return "回落到日志前缀";
                    }
                    if (sentenceUtc.HasValue)
                    {
                        return "回落到句内时间";
                    }
                }

                return _lastGnssUtc.HasValue ? "回落到最近 GNSS 时间" : "无可用的回落时间";
            }

            private string LogPrefixFallbackTarget(DateTimeOffset? sentenceUtc)
            {
                if (sentenceUtc.HasValue)
                {
                    return "回落到句内时间";
                }

                return _lastGnssUtc.HasValue ? "回落到最近 GNSS 时间" : "无可用的回落时间";
            }

            private void EmitGnssAnchors(DateTimeOffset sentenceUtc, NmeaSentence sentence, int lineNumber)
            {
                if (!_options.EmitGnssAnchors)
                {
                    return;
                }

                EmitFallbackDiagnostics(sentence, sentenceUtc, lineNumber);
                DateTimeOffset? deviceTime = DeviceTime(sentence);
                if (!deviceTime.HasValue)
                {
                    return;
                }

                string eventKey = "GNSS@" + sentenceUtc.UtcDateTime.ToString(
                    "yyyyMMddTHHmmss.fff",
                    CultureInfo.InvariantCulture);

                if (!_anchorKeys.Add(eventKey))
                {
                    return;
                }

                _anchors.Add(new AnchorObservation(
                    eventKey,
                    _options.SourceId,
                    SimTime.FromUtc(deviceTime.Value, _options.CaseEpochUtc)));
                _anchors.Add(new AnchorObservation(
                    eventKey,
                    "GNSS",
                    SimTime.FromUtc(sentenceUtc, _options.CaseEpochUtc)));
            }

            private bool TryGetLatestScalar(TrackKind kind, SimTime time, out double value)
            {
                value = 0.0;
                TrackBuilder builder;
                if (!_tracks.TryGetValue(TrackId(kind), out builder))
                {
                    return false;
                }

                bool found = false;
                for (int i = 0; i < builder.Samples.Count; i++)
                {
                    TimelineSample sample = builder.Samples[i];
                    if (sample.Time <= time && !sample.HasPosition)
                    {
                        value = sample.Value;
                        found = true;
                    }
                    else if (sample.Time > time)
                    {
                        break;
                    }
                }

                return found;
            }

            private void AddSample(string trackId, TrackKind kind, TimelineSample sample)
            {
                AddSample(trackId, kind, sample, BearingReference.True);
            }

            private void AddSample(
                string trackId,
                TrackKind kind,
                TimelineSample sample,
                BearingReference bearingReference)
            {
                TrackBuilder builder;
                if (!_tracks.TryGetValue(trackId, out builder))
                {
                    builder = new TrackBuilder(trackId, kind, TrackKindInfo.DefaultUnit(kind), bearingReference);
                    _tracks.Add(trackId, builder);
                }

                builder.AddSample(sample, bearingReference);
            }

            private string TrackId(TrackKind kind)
            {
                return _options.SourceId + "/" + kind.ToString();
            }

            private string TargetTrackId(int targetNumber, TrackKind kind)
            {
                string prefix = kind == TrackKind.TargetPosition ? "TLL" : "TTM";
                return _options.SourceId + "/" + prefix +
                       targetNumber.ToString("00", CultureInfo.InvariantCulture) +
                       "/" + kind.ToString();
            }
        }

        private sealed class TrackBuilder
        {
            private readonly HashSet<SimTime> _times = new HashSet<SimTime>();

            public string Id { get; }
            public TrackKind Kind { get; }
            public string Unit { get; }
            public BearingReference BearingReference { get; private set; }
            public List<TimelineSample> Samples { get; }

            public TrackBuilder(string id, TrackKind kind, string unit)
                : this(id, kind, unit, BearingReference.True)
            {
            }

            public TrackBuilder(
                string id,
                TrackKind kind,
                string unit,
                BearingReference bearingReference)
            {
                Id = id;
                Kind = kind;
                Unit = unit;
                BearingReference = bearingReference;
                Samples = new List<TimelineSample>();
            }

            public void AddSample(TimelineSample sample)
            {
                AddSample(sample, BearingReference);
            }

            public void AddSample(TimelineSample sample, BearingReference bearingReference)
            {
                BearingReference = bearingReference;
                // 同一时刻已存在样本时保留先到的。
                if (_times.Add(sample.Time))
                {
                    Samples.Add(sample);
                }
            }

            public Track Build(string sourceId)
            {
                return new Track(
                    Id,
                    sourceId,
                    Kind,
                    Unit,
                    Samples,
                    null,
                    null,
                    BearingReference);
            }
        }

        private static bool TryParseDouble(string value, out double result)
        {
            result = 0.0;
            if (string.IsNullOrEmpty(value))
            {
                return false;
            }

            if (!double.TryParse(
                value.Trim(),
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out result))
            {
                return false;
            }

            return !double.IsNaN(result) && !double.IsInfinity(result);
        }

        private static bool TryParseInt(string value, out int result)
        {
            result = 0;
            if (string.IsNullOrEmpty(value))
            {
                return false;
            }

            return int.TryParse(
                value.Trim(),
                NumberStyles.Integer,
                CultureInfo.InvariantCulture,
                out result);
        }

        private static bool TryParseNmeaDate(string value, out DateTime date)
        {
            date = default(DateTime);
            string text = Trim(value);
            if (text.Length != 6)
            {
                return false;
            }

            int day;
            int month;
            int year;
            if (!int.TryParse(text.Substring(0, 2), NumberStyles.Integer, CultureInfo.InvariantCulture, out day) ||
                !int.TryParse(text.Substring(2, 2), NumberStyles.Integer, CultureInfo.InvariantCulture, out month) ||
                !int.TryParse(text.Substring(4, 2), NumberStyles.Integer, CultureInfo.InvariantCulture, out year))
            {
                return false;
            }

            year += year >= 80 ? 1900 : 2000;
            try
            {
                date = new DateTime(year, month, day, 0, 0, 0, DateTimeKind.Utc);
                return true;
            }
            catch (ArgumentOutOfRangeException)
            {
                return false;
            }
        }

        private static DateTimeOffset CombineUtc(DateTime date, TimeSpan timeOfDay)
        {
            DateTime combined = DateTime.SpecifyKind(date.Date + timeOfDay, DateTimeKind.Unspecified);
            return new DateTimeOffset(combined, TimeSpan.Zero);
        }

        private static string Trim(string value)
        {
            return value == null ? string.Empty : value.Trim();
        }
    }
}
