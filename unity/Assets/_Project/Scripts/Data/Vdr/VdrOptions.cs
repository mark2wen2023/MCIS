using System;
using System.Collections.Generic;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// VDR 时间基准。
    /// </summary>
    public enum VdrTimeBasis
    {
        /// <summary>
        /// 设备时钟优先（默认，裁定 3）：校验和有效的标签块时间 &gt; 日志行前缀时间 &gt; 句内 GNSS 时间 &gt; 最近一次 GNSS 时间。
        /// </summary>
        LogPrefix = 0,
        /// <summary>优先使用 GNSS 语句内部的 UTC 时间。</summary>
        GnssSentenceTime = 1
    }

    /// <summary>
    /// VDR 导入选项。
    /// </summary>
    public sealed class VdrImportOptions
    {
        /// <summary>数据源标识（必填，如 "MARY-VDR"）。</summary>
        public string SourceId { get; set; }

        /// <summary>案件纪元 UTC，用于把绝对 UTC 换算为 SimTime。</summary>
        public DateTimeOffset CaseEpochUtc { get; set; }

        /// <summary>GGA 等无日期语句使用的默认日期（UTC）；RMC/ZDA 出现日期后会更新。</summary>
        public DateTime? DefaultDateUtc { get; set; }

        /// <summary>时间基准，默认使用日志行前缀设备时钟。</summary>
        public VdrTimeBasis TimeBasis { get; set; } = VdrTimeBasis.LogPrefix;

        /// <summary>是否保留校验和错误的语句，默认 false（丢弃并记诊断）。</summary>
        public bool KeepBadChecksum { get; set; }

        /// <summary>是否根据 GNSS 语句与日志前缀生成钟差锚点，默认 true。</summary>
        public bool EmitGnssAnchors { get; set; } = true;
    }

    /// <summary>VDR 导入诊断严重程度。</summary>
    public enum DiagnosticSeverity
    {
        /// <summary>错误：该行或该语句被丢弃。</summary>
        Error = 0,
        /// <summary>警告：仍然导入，但需要调查员留意（如超长行、标签块无效回落）。</summary>
        Warning = 1,
        /// <summary>提示信息（如跨午夜日期滚动）。</summary>
        Info = 2
    }

    /// <summary>导入诊断记录。</summary>
    public sealed class VdrDiagnostic
    {
        /// <summary>严重程度。旧构造按诊断代码推导：vdr_line_too_long / vdr_unsupported / vdr_tagblock_invalid / vdr_logprefix_invalid / vdr_relative_bearing_no_heading 为警告，vdr_date_rollover / vdr_timesource_mismatch 为提示，其余为错误。</summary>
        public DiagnosticSeverity Severity { get; }

        /// <summary>输入文件行号（从 1 开始）。</summary>
        public int LineNumber { get; }

        /// <summary>诊断代码（vdr_bad_checksum、vdr_parse_error、vdr_no_time、vdr_unsupported 等）。</summary>
        public string Code { get; }

        /// <summary>诊断描述。</summary>
        public string Message { get; }

        /// <summary>
        /// 构造诊断记录。
        /// </summary>
        /// <param name="lineNumber">输入行号。</param>
        /// <param name="code">诊断代码。</param>
        /// <param name="message">诊断描述。</param>
        public VdrDiagnostic(int lineNumber, string code, string message)
        {
            LineNumber = lineNumber;
            Code = code;
            Message = message;
            Severity = DefaultSeverityFor(code);
        }

        /// <summary>
        /// 构造带严重程度的诊断记录。
        /// </summary>
        /// <param name="lineNumber">输入行号。</param>
        /// <param name="code">诊断代码。</param>
        /// <param name="message">诊断描述。</param>
        /// <param name="severity">严重程度。</param>
        public VdrDiagnostic(int lineNumber, string code, string message, DiagnosticSeverity severity)
        {
            LineNumber = lineNumber;
            Code = code;
            Message = message;
            Severity = severity;
        }

        /// <summary>按诊断代码推导默认严重程度。</summary>
        /// <param name="code">诊断代码。</param>
        /// <returns>默认严重程度。</returns>
        public static DiagnosticSeverity DefaultSeverityFor(string code)
        {
            switch (code)
            {
                case "vdr_line_too_long":
                case "vdr_unsupported":
                case "vdr_tagblock_invalid":
                case "vdr_logprefix_invalid":
                case "vdr_relative_bearing_no_heading":
                    return DiagnosticSeverity.Warning;
                case "vdr_date_rollover":
                case "vdr_timesource_mismatch":
                    return DiagnosticSeverity.Info;
                default:
                    return DiagnosticSeverity.Error;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "L{0} {1}: {2}",
                LineNumber,
                Code,
                Message);
        }
    }

    /// <summary>
    /// VDR 导入结果，统一承载 NMEA、CSV 与媒体清单的导入产出。
    /// </summary>
    public sealed class VdrImportResult
    {
        /// <summary>数据源标识。</summary>
        public string SourceId { get; }

        /// <summary>导入得到的时间轴轨道。</summary>
        public IReadOnlyList<Domain.Timeline.Track> Tracks { get; }

        /// <summary>导入得到的钟差锚点。</summary>
        public IReadOnlyList<Domain.Timeline.AnchorObservation> Anchors { get; }

        /// <summary>导入诊断。</summary>
        public IReadOnlyList<VdrDiagnostic> Diagnostics { get; }

        /// <summary>读取的输入行数。</summary>
        public int LinesRead { get; }

        /// <summary>成功使用（通过校验和并参与处理）的语句数。</summary>
        public int SentencesUsed { get; }

        /// <summary>
        /// 构造 VDR 导入结果。
        /// </summary>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="tracks">轨道列表，可为 null。</param>
        /// <param name="anchors">锚点列表，可为 null。</param>
        /// <param name="diagnostics">诊断列表，可为 null。</param>
        /// <param name="linesRead">读取行数。</param>
        /// <param name="sentencesUsed">使用语句数。</param>
        public VdrImportResult(
            string sourceId,
            IReadOnlyList<Domain.Timeline.Track> tracks,
            IReadOnlyList<Domain.Timeline.AnchorObservation> anchors,
            IReadOnlyList<VdrDiagnostic> diagnostics,
            int linesRead,
            int sentencesUsed)
        {
            SourceId = sourceId;
            Tracks = tracks ?? new Domain.Timeline.Track[0];
            Anchors = anchors ?? new Domain.Timeline.AnchorObservation[0];
            Diagnostics = diagnostics ?? new VdrDiagnostic[0];
            LinesRead = linesRead;
            SentencesUsed = sentencesUsed;
        }
    }
}
