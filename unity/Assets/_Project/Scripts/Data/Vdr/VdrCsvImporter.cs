using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Timeline;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// 通用 CSV 导入器：根据列映射把车钟、舵角、事件等表格数据导入为时间轴轨道。
    /// 跳过空行与 '#' 开头的注释行，支持双引号字段。
    /// </summary>
    public static class VdrCsvImporter
    {
        /// <summary>
        /// 导入 CSV 行集合。
        /// </summary>
        /// <param name="lines">CSV 文本行。</param>
        /// <param name="mapping">列映射。</param>
        /// <param name="options">导入选项。</param>
        /// <returns>导入结果；缺少列或选项非法时失败。</returns>
        public static Result<VdrImportResult> Import(
            IEnumerable<string> lines,
            VdrCsvMapping mapping,
            VdrImportOptions options)
        {
            if (options == null || string.IsNullOrWhiteSpace(options.SourceId))
            {
                return Result<VdrImportResult>.Fail("vdr_missing_source", "必须指定数据源标识 SourceId。");
            }

            if (mapping == null)
            {
                return Result<VdrImportResult>.Fail("vdr_csv_mapping", "CSV 列映射不能为空。");
            }

            List<string> rawLines = new List<string>();
            if (lines != null)
            {
                rawLines.AddRange(lines);
            }

            List<VdrDiagnostic> diagnostics = new List<VdrDiagnostic>();
            int headerIndex = FindNextDataLine(rawLines, 0);
            if (headerIndex < 0)
            {
                return Result<VdrImportResult>.Fail("vdr_csv_missing_header", "CSV 文件没有表头行。");
            }

            List<string> header = SplitCsvLine(rawLines[headerIndex], mapping.Delimiter);
            if (header.Count > 0)
            {
                header[0] = header[0].TrimStart('\uFEFF');
            }

            Dictionary<string, int> columnIndex = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < header.Count; i++)
            {
                string name = header[i].Trim();
                if (name.Length > 0 && !columnIndex.ContainsKey(name))
                {
                    columnIndex.Add(name, i);
                }
            }

            int timeIndex;
            if (string.IsNullOrWhiteSpace(mapping.TimeColumn) ||
                !columnIndex.TryGetValue(mapping.TimeColumn.Trim(), out timeIndex))
            {
                return Result<VdrImportResult>.Fail(
                    "vdr_csv_missing_column",
                    "CSV 缺少时间列：" + mapping.TimeColumn);
            }

            int eventIndex = -1;
            if (!string.IsNullOrWhiteSpace(mapping.EventColumn) &&
                !columnIndex.TryGetValue(mapping.EventColumn.Trim(), out eventIndex))
            {
                return Result<VdrImportResult>.Fail(
                    "vdr_csv_missing_column",
                    "CSV 缺少事件列：" + mapping.EventColumn);
            }

            List<ColumnRuntime> columns = new List<ColumnRuntime>();
            Dictionary<string, CsvTrackBuilder> trackBuilders =
                new Dictionary<string, CsvTrackBuilder>(StringComparer.Ordinal);

            if (mapping.Columns != null)
            {
                for (int i = 0; i < mapping.Columns.Count; i++)
                {
                    VdrCsvColumnMapping column = mapping.Columns[i];
                    if (column == null || string.IsNullOrWhiteSpace(column.Column))
                    {
                        continue;
                    }

                    int index;
                    if (!columnIndex.TryGetValue(column.Column.Trim(), out index))
                    {
                        return Result<VdrImportResult>.Fail(
                            "vdr_csv_missing_column",
                            "CSV 缺少列：" + column.Column);
                    }

                    string trackName = string.IsNullOrWhiteSpace(column.TrackName)
                        ? column.Kind.ToString()
                        : column.TrackName.Trim();
                    string trackId = options.SourceId + "/" + trackName;

                    CsvTrackBuilder builder;
                    if (!trackBuilders.TryGetValue(trackId, out builder))
                    {
                        builder = new CsvTrackBuilder(
                            trackId,
                            options.SourceId,
                            column.Kind,
                            TrackKindInfo.DefaultUnit(column.Kind));
                        trackBuilders.Add(trackId, builder);
                    }

                    columns.Add(new ColumnRuntime(column, index, trackId, trackName, builder));
                }
            }

            CsvTrackBuilder eventBuilder = null;
            if (!string.IsNullOrWhiteSpace(mapping.EventColumn))
            {
                if (columns.Count > 0)
                {
                    eventBuilder = columns[0].Builder;
                }
                else
                {
                    string eventsTrackId = options.SourceId + "/Events";
                    eventBuilder = new CsvTrackBuilder(
                        eventsTrackId,
                        options.SourceId,
                        TrackKind.Other,
                        string.Empty);
                    trackBuilders.Add(eventsTrackId, eventBuilder);
                }
            }

            int linesRead = rawLines.Count;
            int sentencesUsed = 0;
            int eventSequence = 0;
            for (int lineIndex = headerIndex + 1; lineIndex < rawLines.Count; lineIndex++)
            {
                string line = rawLines[lineIndex];
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

                List<string> fields = SplitCsvLine(line, mapping.Delimiter);
                string timeText = Cell(fields, timeIndex);
                DateTimeOffset utc;
                if (!TryParseTime(timeText, mapping, out utc))
                {
                    diagnostics.Add(new VdrDiagnostic(
                        lineIndex + 1,
                        "vdr_csv_bad_time",
                        "无法解析时间单元格：" + timeText));
                    continue;
                }

                SimTime time = SimTime.FromUtc(utc, options.CaseEpochUtc);

                for (int c = 0; c < columns.Count; c++)
                {
                    ColumnRuntime runtime = columns[c];
                    string rawCell = Cell(fields, runtime.Index).Trim();
                    if (rawCell.Length == 0)
                    {
                        continue;
                    }

                    double numeric;
                    if (!TryResolveNumeric(runtime.Mapping, rawCell, out numeric))
                    {
                        diagnostics.Add(new VdrDiagnostic(
                            lineIndex + 1,
                            "vdr_csv_bad_value",
                            "列 " + runtime.Mapping.Column + " 的值无法解析：" + rawCell));
                        continue;
                    }

                    double value = numeric * runtime.Mapping.Scale + runtime.Mapping.Offset;
                    runtime.Builder.AddSample(TimelineSample.Scalar(time, value, rawCell));

                    if (runtime.Mapping.MarkChanges && runtime.HasPrevious)
                    {
                        if (Math.Abs(value - runtime.PreviousValue) > 1e-12)
                        {
                            runtime.Builder.AddMarker(new EventMarker(
                                runtime.Builder.Id + "/change/" +
                                runtime.MarkerSequence.ToString("000", CultureInfo.InvariantCulture),
                                time,
                                "change",
                                runtime.TrackName + ": " + runtime.PreviousText + " → " + rawCell,
                                options.SourceId,
                                runtime.TrackId));
                            runtime.MarkerSequence++;
                        }
                    }

                    runtime.PreviousValue = value;
                    runtime.PreviousText = rawCell;
                    runtime.HasPrevious = true;
                }

                if (!string.IsNullOrWhiteSpace(mapping.EventColumn) && eventBuilder != null)
                {
                    string eventText = Cell(fields, eventIndex).Trim();
                    if (eventText.Length > 0)
                    {
                        eventBuilder.AddMarker(new EventMarker(
                            options.SourceId + "/event/" +
                            eventSequence.ToString("000", CultureInfo.InvariantCulture),
                            time,
                            "event",
                            eventText,
                            options.SourceId,
                            eventBuilder.Id));
                        eventSequence++;
                    }
                }

                sentencesUsed++;
            }

            List<Track> tracks = new List<Track>(trackBuilders.Count);
            foreach (CsvTrackBuilder builder in trackBuilders.Values)
            {
                tracks.Add(builder.Build());
            }

            tracks.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));

            VdrImportResult result = new VdrImportResult(
                options.SourceId,
                tracks,
                new AnchorObservation[0],
                diagnostics,
                linesRead,
                sentencesUsed);
            return Result<VdrImportResult>.Ok(result);
        }

        private static int FindNextDataLine(List<string> lines, int start)
        {
            for (int i = start; i < lines.Count; i++)
            {
                string line = lines[i];
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

                return i;
            }

            return -1;
        }

        private static bool TryResolveNumeric(
            VdrCsvColumnMapping mapping,
            string raw,
            out double value)
        {
            value = 0.0;
            if (mapping.TextValues != null)
            {
                foreach (KeyValuePair<string, double> pair in mapping.TextValues)
                {
                    if (string.Equals(pair.Key == null ? null : pair.Key.Trim(), raw, StringComparison.OrdinalIgnoreCase))
                    {
                        value = pair.Value;
                        return true;
                    }
                }
            }

            return TryParseDouble(raw, out value);
        }

        private static bool TryParseDouble(string text, out double value)
        {
            value = 0.0;
            if (string.IsNullOrEmpty(text))
            {
                return false;
            }

            if (!double.TryParse(
                text.Trim(),
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out value))
            {
                return false;
            }

            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private static bool TryParseTime(string text, VdrCsvMapping mapping, out DateTimeOffset utc)
        {
            utc = default(DateTimeOffset);
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            string value = text.Trim();
            if (string.IsNullOrEmpty(mapping.TimeFormat))
            {
                return DateTimeOffset.TryParse(
                    value,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                    out utc);
            }

            string format = mapping.TimeFormat;
            bool formatHasOffset =
                format.IndexOf('z') >= 0 ||
                format.IndexOf('K') >= 0 ||
                format.IndexOf("zzz", StringComparison.OrdinalIgnoreCase) >= 0;

            if (formatHasOffset)
            {
                DateTimeOffset parsed;
                if (!DateTimeOffset.TryParseExact(
                    value,
                    format,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.RoundtripKind,
                    out parsed))
                {
                    return false;
                }

                utc = parsed.ToUniversalTime();
                return true;
            }

            DateTime local;
            if (!DateTime.TryParseExact(
                value,
                format,
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out local))
            {
                return false;
            }

            DateTime unspecified = DateTime.SpecifyKind(local, DateTimeKind.Unspecified);
            utc = new DateTimeOffset(unspecified, mapping.TimeZoneOffset).ToUniversalTime();
            return true;
        }

        private static string Cell(List<string> fields, int index)
        {
            if (index < 0 || index >= fields.Count)
            {
                return string.Empty;
            }

            return fields[index] ?? string.Empty;
        }

        /// <summary>
        /// 拆分一行 CSV，支持双引号包裹与 "" 转义；保留空字段。
        /// </summary>
        internal static List<string> SplitCsvLine(string line, char delimiter)
        {
            List<string> fields = new List<string>();
            if (line == null)
            {
                fields.Add(string.Empty);
                return fields;
            }

            int index = 0;
            while (true)
            {
                if (index < line.Length && line[index] == '"')
                {
                    index++;
                    System.Text.StringBuilder builder = new System.Text.StringBuilder();
                    while (index < line.Length)
                    {
                        char c = line[index];
                        if (c == '"')
                        {
                            if (index + 1 < line.Length && line[index + 1] == '"')
                            {
                                builder.Append('"');
                                index += 2;
                                continue;
                            }

                            index++;
                            break;
                        }

                        builder.Append(c);
                        index++;
                    }

                    fields.Add(builder.ToString());
                    if (index < line.Length && line[index] == delimiter)
                    {
                        index++;
                        if (index >= line.Length)
                        {
                            fields.Add(string.Empty);
                        }
                        continue;
                    }

                    break;
                }

                int end = line.IndexOf(delimiter, index);
                if (end < 0)
                {
                    fields.Add(line.Substring(index));
                    break;
                }

                fields.Add(line.Substring(index, end - index));
                index = end + 1;
                if (index >= line.Length)
                {
                    fields.Add(string.Empty);
                    break;
                }
            }

            return fields;
        }

        private sealed class ColumnRuntime
        {
            public VdrCsvColumnMapping Mapping { get; }
            public int Index { get; }
            public string TrackId { get; }
            public string TrackName { get; }
            public CsvTrackBuilder Builder { get; }
            public bool HasPrevious { get; set; }
            public double PreviousValue { get; set; }
            public string PreviousText { get; set; }
            public int MarkerSequence { get; set; }

            public ColumnRuntime(
                VdrCsvColumnMapping mapping,
                int index,
                string trackId,
                string trackName,
                CsvTrackBuilder builder)
            {
                Mapping = mapping;
                Index = index;
                TrackId = trackId;
                TrackName = trackName;
                Builder = builder;
                PreviousText = string.Empty;
            }
        }

        private sealed class CsvTrackBuilder
        {
            private readonly HashSet<SimTime> _times = new HashSet<SimTime>();
            private readonly List<TimelineSample> _samples = new List<TimelineSample>();
            private readonly List<EventMarker> _markers = new List<EventMarker>();

            public string Id { get; }
            public string SourceId { get; }
            public TrackKind Kind { get; }
            public string Unit { get; }

            public CsvTrackBuilder(string id, string sourceId, TrackKind kind, string unit)
            {
                Id = id;
                SourceId = sourceId;
                Kind = kind;
                Unit = unit;
            }

            public void AddSample(TimelineSample sample)
            {
                if (_times.Add(sample.Time))
                {
                    _samples.Add(sample);
                }
            }

            public void AddMarker(EventMarker marker)
            {
                _markers.Add(marker);
            }

            public Track Build()
            {
                return new Track(Id, SourceId, Kind, Unit, _samples, _markers);
            }
        }
    }
}
