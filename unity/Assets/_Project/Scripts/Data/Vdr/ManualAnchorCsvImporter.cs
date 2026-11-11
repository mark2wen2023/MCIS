using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Timeline;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// 人工锚点 CSV 导入器。表头：
    /// event_key,source_a,time_a_utc,source_b,time_b_utc,note,investigator。
    /// 跳过 '#' 注释行与空行，支持双引号字段。
    /// </summary>
    public static class ManualAnchorCsvImporter
    {
        /// <summary>
        /// 导入人工锚点行集合。
        /// </summary>
        /// <param name="lines">CSV 文本行。</param>
        /// <param name="caseEpochUtc">案件纪元（UTC）。</param>
        /// <returns>成功时返回按文件顺序排列的人工锚点；表头/列/时间非法时失败。</returns>
        public static Result<IReadOnlyList<ManualAnchor>> Import(
            IEnumerable<string> lines,
            DateTimeOffset caseEpochUtc)
        {
            List<string> rawLines = new List<string>();
            if (lines != null)
            {
                rawLines.AddRange(lines);
            }

            int headerIndex = FindNextDataLine(rawLines, 0);
            if (headerIndex < 0)
            {
                return Result<IReadOnlyList<ManualAnchor>>.Fail(
                    "vdr_manual_anchor_missing_header",
                    "人工锚点 CSV 没有表头行。");
            }

            List<string> header = VdrCsvImporter.SplitCsvLine(rawLines[headerIndex], ',');
            if (header.Count > 0)
            {
                header[0] = header[0].TrimStart('\uFEFF');
            }

            Dictionary<string, int> index =
                new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < header.Count; i++)
            {
                string name = header[i].Trim();
                if (name.Length > 0 && !index.ContainsKey(name))
                {
                    index.Add(name, i);
                }
            }

            string[] required =
            {
                "event_key", "source_a", "time_a_utc", "source_b", "time_b_utc"
            };
            for (int i = 0; i < required.Length; i++)
            {
                if (!index.ContainsKey(required[i]))
                {
                    return Result<IReadOnlyList<ManualAnchor>>.Fail(
                        "vdr_manual_anchor_missing_column",
                        "人工锚点 CSV 缺少列：" + required[i]);
                }
            }

            int eventKeyIndex = index["event_key"];
            int sourceAIndex = index["source_a"];
            int timeAIndex = index["time_a_utc"];
            int sourceBIndex = index["source_b"];
            int timeBIndex = index["time_b_utc"];
            int noteIndex = index.ContainsKey("note") ? index["note"] : -1;
            int investigatorIndex = index.ContainsKey("investigator")
                ? index["investigator"]
                : -1;

            List<ManualAnchor> anchors = new List<ManualAnchor>();
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
                string eventKey = Cell(fields, eventKeyIndex).Trim();
                string sourceA = Cell(fields, sourceAIndex).Trim();
                string sourceB = Cell(fields, sourceBIndex).Trim();
                string timeAText = Cell(fields, timeAIndex).Trim();
                string timeBText = Cell(fields, timeBIndex).Trim();
                string note = NullIfEmpty(Cell(fields, noteIndex).Trim());
                string investigator = NullIfEmpty(Cell(fields, investigatorIndex).Trim());

                DateTimeOffset timeA;
                if (!TryParseUtc(timeAText, out timeA))
                {
                    return Result<IReadOnlyList<ManualAnchor>>.Fail(
                        "vdr_manual_anchor_bad_time",
                        "人工锚点第 " + (lineIndex + 1) + " 行 time_a_utc 无效：" + timeAText);
                }

                DateTimeOffset timeB;
                if (!TryParseUtc(timeBText, out timeB))
                {
                    return Result<IReadOnlyList<ManualAnchor>>.Fail(
                        "vdr_manual_anchor_bad_time",
                        "人工锚点第 " + (lineIndex + 1) + " 行 time_b_utc 无效：" + timeBText);
                }

                try
                {
                    anchors.Add(ManualAnchor.FromUtc(
                        eventKey,
                        sourceA,
                        timeA,
                        sourceB,
                        timeB,
                        caseEpochUtc,
                        note,
                        investigator));
                }
                catch (ArgumentException ex)
                {
                    return Result<IReadOnlyList<ManualAnchor>>.Fail(
                        "vdr_manual_anchor_invalid",
                        "人工锚点第 " + (lineIndex + 1) + " 行无效：" + ex.Message);
                }
            }

            return Result<IReadOnlyList<ManualAnchor>>.Ok(anchors);
        }

        private static bool TryParseUtc(string text, out DateTimeOffset utc)
        {
            return DateTimeOffset.TryParse(
                text,
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                out utc);
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

        private static string NullIfEmpty(string value)
        {
            return string.IsNullOrEmpty(value) ? null : value;
        }
    }
}
