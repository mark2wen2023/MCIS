using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Text;

namespace Mcis.Simulation.WhatIf.Cases
{
    /// <summary>
    /// tracks_from_report.csv 的一行（全列保留）。位置为空表示报告未给经纬度；
    /// provenance 为 ReportNarrative / ReportFigure-VDR / ReportFigure-AIS。
    /// </summary>
    public sealed class ReportTrackRow
    {
        /// <summary>船舶标识（vega_dream / yangze22）。</summary>
        public string VesselId { get; }

        /// <summary>北京时间原文。</summary>
        public string TimeBeijingText { get; }

        /// <summary>解析后的北京时间。</summary>
        public DateTimeOffset TimeBeijing { get; }

        /// <summary>解析后的 UTC 时间；空值为 null。</summary>
        public DateTimeOffset? TimeUtc { get; }

        /// <summary>报告时刻是否为约数。</summary>
        public bool Approximate { get; }

        /// <summary>纬度（十进制度）；报告未给为 null。</summary>
        public double? LatDeg { get; }

        /// <summary>经度（十进制度）；报告未给为 null。</summary>
        public double? LonDeg { get; }

        /// <summary>报告“航向”（ReportNarrative 行常为船首向）。</summary>
        public double? CogDeg { get; }

        /// <summary>对地航速（节）。</summary>
        public double? SogKn { get; }

        /// <summary>VDR/AIS 船首向（度）。</summary>
        public double? HdgDeg { get; }

        /// <summary>转首率（度/分，右转为正）。</summary>
        public double? RotDegPerMin { get; }

        /// <summary>VDR 主机转速对应的 STW（节）。</summary>
        public double? StwKn { get; }

        /// <summary>舵角（度，右舵为正）。</summary>
        public double? RudderDeg { get; }

        /// <summary>螺旋桨转速（rpm）。</summary>
        public double? PropellerRpm { get; }

        /// <summary>报告文字位置描述。</summary>
        public string PositionText { get; }

        /// <summary>来源类型（ReportNarrative / ReportFigure-VDR / ReportFigure-AIS）。</summary>
        public string Provenance { get; }

        /// <summary>正文页码；空值为 null。</summary>
        public int? Page { get; }

        /// <summary>PDF 页码；空值为 null。</summary>
        public int? PdfPage { get; }

        /// <summary>report.txt 行号或行号范围。</summary>
        public string Line { get; }

        /// <summary>图号。</summary>
        public string Figure { get; }

        /// <summary>图读内容。</summary>
        public string FigureReading { get; }

        /// <summary>报告原文引文。</summary>
        public string Quote { get; }

        /// <summary>备注（含矛盾与取舍说明）。</summary>
        public string Note { get; }

        /// <summary>构造航迹行。</summary>
        public ReportTrackRow(
            string vesselId,
            string timeBeijingText,
            DateTimeOffset timeBeijing,
            DateTimeOffset? timeUtc,
            bool approximate,
            double? latDeg,
            double? lonDeg,
            double? cogDeg,
            double? sogKn,
            double? hdgDeg,
            double? rotDegPerMin,
            double? stwKn,
            double? rudderDeg,
            double? propellerRpm,
            string positionText,
            string provenance,
            int? page,
            int? pdfPage,
            string line,
            string figure,
            string figureReading,
            string quote,
            string note)
        {
            VesselId = vesselId ?? string.Empty;
            TimeBeijingText = timeBeijingText ?? string.Empty;
            TimeBeijing = timeBeijing;
            TimeUtc = timeUtc;
            Approximate = approximate;
            LatDeg = latDeg;
            LonDeg = lonDeg;
            CogDeg = cogDeg;
            SogKn = sogKn;
            HdgDeg = hdgDeg;
            RotDegPerMin = rotDegPerMin;
            StwKn = stwKn;
            RudderDeg = rudderDeg;
            PropellerRpm = propellerRpm;
            PositionText = positionText ?? string.Empty;
            Provenance = provenance ?? string.Empty;
            Page = page;
            PdfPage = pdfPage;
            Line = line ?? string.Empty;
            Figure = figure ?? string.Empty;
            FigureReading = figureReading ?? string.Empty;
            Quote = quote ?? string.Empty;
            Note = note ?? string.Empty;
        }

        /// <summary>是否带经纬度。</summary>
        public bool HasPosition
        {
            get { return LatDeg.HasValue && LonDeg.HasValue; }
        }

        /// <summary>来源优先级：ReportFigure-VDR=0、ReportFigure-AIS=1、正文=2、其他=3。</summary>
        public int ProvenancePriority
        {
            get
            {
                if (string.Equals(Provenance, "ReportFigure-VDR", StringComparison.OrdinalIgnoreCase)) return 0;
                if (string.Equals(Provenance, "ReportFigure-AIS", StringComparison.OrdinalIgnoreCase)) return 1;
                if (string.Equals(Provenance, "ReportNarrative", StringComparison.OrdinalIgnoreCase)) return 2;
                return 3;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return VesselId + " " + TimeBeijingText + " " + Provenance;
        }
    }

    /// <summary>
    /// tracks_from_report.csv 解析器。跳过 # 注释行，按表头映射列，支持双引号包裹的
    /// 含逗号字段与空值；不写死文件路径，由调用方按行传入。
    /// </summary>
    public static class ReportTrackCsv
    {
        /// <summary>解析 CSV 行（可含注释行与表头）；返回全部数据行。</summary>
        public static IReadOnlyList<ReportTrackRow> Parse(IEnumerable<string> lines)
        {
            if (lines == null)
            {
                throw new ArgumentNullException(nameof(lines));
            }

            string[] header = null;
            List<string[]> records = new List<string[]>();
            int physicalLine = 0;
            foreach (string raw in lines)
            {
                physicalLine++;
                if (raw == null)
                {
                    continue;
                }

                string line = raw.TrimStart('\uFEFF');
                if (line.Length == 0)
                {
                    continue;
                }
                if (line[0] == '#')
                {
                    continue;
                }

                string[] fields = SplitLine(line, physicalLine);
                if (header == null)
                {
                    header = fields;
                    continue;
                }
                if (fields.Length == 1 && fields[0].Trim().Length == 0)
                {
                    continue;
                }
                records.Add(fields);
            }

            if (header == null)
            {
                throw new FormatException("CSV 缺少表头行。");
            }

            Dictionary<string, int> map = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            for (int i = 0; i < header.Length; i++)
            {
                string key = header[i].Trim();
                if (key.Length > 0 && !map.ContainsKey(key))
                {
                    map.Add(key, i);
                }
            }

            RequireColumn(map, "vesselId");
            RequireColumn(map, "timeBeijing");

            List<ReportTrackRow> rows = new List<ReportTrackRow>(records.Count);
            for (int i = 0; i < records.Count; i++)
            {
                string[] fields = records[i];
                if (fields.Length != header.Length)
                {
                    throw new FormatException(
                        "CSV 第 " + (i + 1) + " 个数据行列数为 " + fields.Length +
                        "，与表头 " + header.Length + " 列不一致（含逗号的字段需用双引号包裹）。");
                }

                string vesselId = Get(fields, map, "vesselId");
                string timeText = Get(fields, map, "timeBeijing");
                DateTimeOffset timeBeijing;
                if (!DateTimeOffset.TryParse(
                        timeText, CultureInfo.InvariantCulture,
                        DateTimeStyles.RoundtripKind | DateTimeStyles.AllowWhiteSpaces, out timeBeijing))
                {
                    throw new FormatException("CSV 第 " + (i + 1) + " 个数据行的 timeBeijing 无法解析：" + timeText);
                }

                string utcText = Get(fields, map, "timeUtc");
                DateTimeOffset? timeUtc = null;
                if (utcText.Length > 0)
                {
                    DateTimeOffset parsedUtc;
                    if (DateTimeOffset.TryParse(
                            utcText, CultureInfo.InvariantCulture,
                            DateTimeStyles.RoundtripKind | DateTimeStyles.AllowWhiteSpaces, out parsedUtc))
                    {
                        timeUtc = parsedUtc;
                    }
                }

                rows.Add(new ReportTrackRow(
                    vesselId,
                    timeText,
                    timeBeijing,
                    timeUtc,
                    ParseBool(Get(fields, map, "approximate")),
                    ParseDouble(Get(fields, map, "latDeg")),
                    ParseDouble(Get(fields, map, "lonDeg")),
                    ParseDouble(Get(fields, map, "cogDeg")),
                    ParseDouble(Get(fields, map, "sogKn")),
                    ParseDouble(Get(fields, map, "hdgDeg")),
                    ParseDouble(Get(fields, map, "rotDegPerMin")),
                    ParseDouble(Get(fields, map, "stwKn")),
                    ParseDouble(Get(fields, map, "rudderDeg")),
                    ParseDouble(Get(fields, map, "propellerRpm")),
                    Get(fields, map, "positionText"),
                    Get(fields, map, "provenance"),
                    ParseInt(Get(fields, map, "page")),
                    ParseInt(Get(fields, map, "pdfPage")),
                    Get(fields, map, "line"),
                    Get(fields, map, "figure"),
                    Get(fields, map, "figureReading"),
                    Get(fields, map, "quote"),
                    Get(fields, map, "note")));
            }

            return new ReadOnlyCollection<ReportTrackRow>(rows);
        }

        /// <summary>解析一行 CSV（支持双引号字段内的逗号与转义双引号）。</summary>
        public static string[] SplitLine(string line, int lineNumber = 0)
        {
            if (line == null)
            {
                throw new ArgumentNullException(nameof(line));
            }

            List<string> fields = new List<string>();
            StringBuilder builder = new StringBuilder();
            bool inQuotes = false;
            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (inQuotes)
                {
                    if (c == '"')
                    {
                        if (i + 1 < line.Length && line[i + 1] == '"')
                        {
                            builder.Append('"');
                            i++;
                        }
                        else
                        {
                            inQuotes = false;
                        }
                    }
                    else
                    {
                        builder.Append(c);
                    }
                }
                else if (c == '"')
                {
                    inQuotes = true;
                }
                else if (c == ',')
                {
                    fields.Add(builder.ToString());
                    builder.Length = 0;
                }
                else
                {
                    builder.Append(c);
                }
            }

            if (inQuotes)
            {
                throw new FormatException(
                    "CSV" + (lineNumber > 0 ? " 第 " + lineNumber + " 行" : string.Empty) + "存在未闭合的双引号。");
            }

            fields.Add(builder.ToString());
            return fields.ToArray();
        }

        private static void RequireColumn(Dictionary<string, int> map, string name)
        {
            if (!map.ContainsKey(name))
            {
                throw new FormatException("CSV 缺少必需列：" + name);
            }
        }

        private static string Get(string[] fields, Dictionary<string, int> map, string name)
        {
            int index;
            if (!map.TryGetValue(name, out index) || index < 0 || index >= fields.Length)
            {
                return string.Empty;
            }
            return fields[index].Trim();
        }

        private static double? ParseDouble(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return null;
            }
            double value;
            if (!double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out value))
            {
                return null;
            }
            return value;
        }

        private static int? ParseInt(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return null;
            }
            int value;
            if (!int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            {
                return null;
            }
            return value;
        }

        private static bool ParseBool(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return false;
            }
            return string.Equals(text, "true", StringComparison.OrdinalIgnoreCase) ||
                   string.Equals(text, "1", StringComparison.Ordinal);
        }
    }
}
