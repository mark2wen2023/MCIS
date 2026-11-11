using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Timeline;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// 媒体清单导入器：读取音频/雷达截图/ECDIS 截屏的元数据与时间范围，
    /// 每个通道生成一条无样本、仅含 MediaItem 与起始事件标记的轨道。
    /// 不读取或解码任何媒体文件。
    /// </summary>
    public static class VdrMediaManifestImporter
    {
        /// <summary>
        /// 导入媒体清单 CSV 行集合。
        /// 表头：id,kind,channel,file,start_utc,duration_s[,sha256][,note]。
        /// </summary>
        /// <param name="lines">清单文本行（跳过 '#' 注释与空行）。</param>
        /// <param name="options">导入选项。</param>
        /// <returns>导入结果；缺少必需列或选项非法时失败。</returns>
        public static Result<VdrImportResult> Import(
            IEnumerable<string> lines,
            VdrImportOptions options)
        {
            if (options == null || string.IsNullOrWhiteSpace(options.SourceId))
            {
                return Result<VdrImportResult>.Fail("vdr_missing_source", "必须指定数据源标识 SourceId。");
            }

            List<string> rawLines = new List<string>();
            if (lines != null)
            {
                rawLines.AddRange(lines);
            }

            int headerIndex = FindNextDataLine(rawLines, 0);
            if (headerIndex < 0)
            {
                return Result<VdrImportResult>.Fail("vdr_media_missing_header", "媒体清单没有表头行。");
            }

            List<string> header = VdrCsvImporter.SplitCsvLine(rawLines[headerIndex], ',');
            if (header.Count > 0)
            {
                header[0] = header[0].TrimStart('\uFEFF');
            }

            Dictionary<string, int> index = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < header.Count; i++)
            {
                string name = header[i].Trim();
                if (name.Length > 0 && !index.ContainsKey(name))
                {
                    index.Add(name, i);
                }
            }

            string[] required = { "id", "kind", "channel", "file", "start_utc", "duration_s" };
            for (int i = 0; i < required.Length; i++)
            {
                if (!index.ContainsKey(required[i]))
                {
                    return Result<VdrImportResult>.Fail(
                        "vdr_media_missing_column",
                        "媒体清单缺少列：" + required[i]);
                }
            }

            int idIndex = index["id"];
            int kindIndex = index["kind"];
            int channelIndex = index["channel"];
            int fileIndex = index["file"];
            int startIndex = index["start_utc"];
            int durationIndex = index["duration_s"];
            int shaIndex;
            int noteIndex;
            index.TryGetValue("sha256", out shaIndex);
            index.TryGetValue("note", out noteIndex);
            if (!index.ContainsKey("sha256"))
            {
                shaIndex = -1;
            }
            if (!index.ContainsKey("note"))
            {
                noteIndex = -1;
            }

            List<VdrDiagnostic> diagnostics = new List<VdrDiagnostic>();
            Dictionary<string, MediaTrackBuilder> builders =
                new Dictionary<string, MediaTrackBuilder>(StringComparer.Ordinal);
            HashSet<string> unsupportedKinds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            int sentencesUsed = 0;
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

                List<string> fields = VdrCsvImporter.SplitCsvLine(line, ',');
                string id = Cell(fields, idIndex).Trim();
                string kindText = Cell(fields, kindIndex).Trim();
                string channel = Cell(fields, channelIndex).Trim();
                string file = Cell(fields, fileIndex).Trim();
                string startText = Cell(fields, startIndex).Trim();
                string durationText = Cell(fields, durationIndex).Trim();

                TrackKind kind;
                if (!TryMapKind(kindText, out kind))
                {
                    if (unsupportedKinds.Add(kindText))
                    {
                        diagnostics.Add(new VdrDiagnostic(
                            lineIndex + 1,
                            "vdr_unsupported",
                            "不支持的媒体种类：" + kindText));
                    }
                    continue;
                }

                DateTimeOffset startUtc;
                if (!DateTimeOffset.TryParse(
                    startText,
                    CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                    out startUtc))
                {
                    diagnostics.Add(new VdrDiagnostic(
                        lineIndex + 1,
                        "vdr_parse_error",
                        "媒体起始时间无效：" + startText));
                    continue;
                }

                double durationSeconds;
                if (!double.TryParse(
                    durationText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out durationSeconds) ||
                    double.IsNaN(durationSeconds) ||
                    double.IsInfinity(durationSeconds) ||
                    durationSeconds < 0.0)
                {
                    diagnostics.Add(new VdrDiagnostic(
                        lineIndex + 1,
                        "vdr_parse_error",
                        "媒体时长无效：" + durationText));
                    continue;
                }

                if (id.Length == 0)
                {
                    id = options.SourceId + "/media/" +
                         (sentencesUsed + 1).ToString("000", CultureInfo.InvariantCulture);
                }

                if (channel.Length == 0)
                {
                    channel = "default";
                }

                SimTime start = SimTime.FromUtc(startUtc, options.CaseEpochUtc);
                TimeRange range = new TimeRange(start, start + durationSeconds);

                Dictionary<string, string> metadata = new Dictionary<string, string>(StringComparer.Ordinal);
                metadata["file"] = file;
                string sha = Cell(fields, shaIndex).Trim();
                string note = Cell(fields, noteIndex).Trim();
                if (sha.Length > 0)
                {
                    metadata["sha256"] = sha;
                }
                if (note.Length > 0)
                {
                    metadata["note"] = note;
                }

                string trackId = options.SourceId + "/" + kind + "/" + channel;
                MediaTrackBuilder builder;
                if (!builders.TryGetValue(trackId, out builder))
                {
                    builder = new MediaTrackBuilder(trackId, options.SourceId, kind);
                    builders.Add(trackId, builder);
                }

                MediaItem item = new MediaItem(id, kind, channel, file, range, metadata);
                builder.AddMedia(item);
                builder.AddMarker(new EventMarker(
                    id + "/marker",
                    start,
                    "media",
                    file,
                    options.SourceId,
                    trackId));

                sentencesUsed++;
            }

            List<Track> tracks = new List<Track>(builders.Count);
            foreach (MediaTrackBuilder builder in builders.Values)
            {
                tracks.Add(builder.Build());
            }

            tracks.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));

            VdrImportResult result = new VdrImportResult(
                options.SourceId,
                tracks,
                new AnchorObservation[0],
                diagnostics,
                rawLines.Count,
                sentencesUsed);
            return Result<VdrImportResult>.Ok(result);
        }

        private static bool TryMapKind(string text, out TrackKind kind)
        {
            switch ((text ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "audio":
                    kind = TrackKind.Audio;
                    return true;
                case "radar":
                    kind = TrackKind.RadarImage;
                    return true;
                case "ecdis":
                    kind = TrackKind.EcdisImage;
                    return true;
                default:
                    kind = TrackKind.Other;
                    return false;
            }
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

        private static string Cell(List<string> fields, int index)
        {
            if (index < 0 || index >= fields.Count)
            {
                return string.Empty;
            }

            return fields[index] ?? string.Empty;
        }

        private sealed class MediaTrackBuilder
        {
            private readonly List<MediaItem> _media = new List<MediaItem>();
            private readonly List<EventMarker> _markers = new List<EventMarker>();

            public string Id { get; }
            public string SourceId { get; }
            public TrackKind Kind { get; }

            public MediaTrackBuilder(string id, string sourceId, TrackKind kind)
            {
                Id = id;
                SourceId = sourceId;
                Kind = kind;
            }

            public void AddMedia(MediaItem item)
            {
                _media.Add(item);
            }

            public void AddMarker(EventMarker marker)
            {
                _markers.Add(marker);
            }

            public Track Build()
            {
                return new Track(
                    Id,
                    SourceId,
                    Kind,
                    TrackKindInfo.DefaultUnit(Kind),
                    new TimelineSample[0],
                    _markers,
                    _media);
            }
        }
    }
}
