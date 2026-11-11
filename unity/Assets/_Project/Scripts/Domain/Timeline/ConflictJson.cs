using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Core;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 将时间轴冲突写为 contracts/schemas/conflict.schema.json 约定的 JSON。
    /// 只输出合同中的键，camelCase、additionalProperties=false；数字使用不变文化 "R"，
    /// NaN/±∞ 写 null（W2.1）。
    /// </summary>
    public static class ConflictJsonWriter
    {
        private const string TimeFormat = "yyyy-MM-ddTHH:mm:ss.fffK";
        private const string DetectedByRuleEngine = "RuleEngine";

        /// <summary>案件编号缺失时拒绝写盘的诊断代码（W2.2）。</summary>
        public const string MissingCaseIdCode = "conflict_case_id_missing";

        /// <summary>案件编号格式不合格时拒绝写盘的诊断代码（W2.3）。校验规则与 <see cref="EvidenceItem.IsValidCaseId"/> 相同。</summary>
        public const string InvalidCaseIdCode = "conflict_case_id_invalid";

        /// <summary>
        /// 输出单个冲突对象。仅用于内存和调试序列化，不得用于落盘，落盘请用 TryWrite/TryToJson。
        /// caseId 为空时本方法仍可输出 JSON null。
        /// </summary>
        /// <param name="conflict">冲突对象；null 时输出 JSON null。</param>
        /// <returns>合同格式的 JSON 文本。</returns>
        public static string ToJson(TimelineConflict conflict)
        {
            if (conflict == null)
            {
                return "null";
            }

            StringBuilder builder = new StringBuilder(512);
            builder.Append('{');

            bool first = true;
            AppendProperty(builder, ref first, "conflictId", conflict.ConflictId);
            AppendProperty(builder, ref first, "caseId", conflict.CaseId);
            AppendProperty(builder, ref first, "summary", conflict.Summary);
            AppendProperty(builder, ref first, "trackKind", conflict.Kind.ToString());
            AppendProperty(builder, ref first, "vesselId", null);
            AppendNumberProperty(builder, ref first, "timeSec", conflict.PeakTime.Seconds);
            AppendObservation(builder, ref first, "a", conflict.SourceA, conflict.ValueA, conflict.PeakTime.Seconds);
            AppendObservation(builder, ref first, "b", conflict.SourceB, conflict.ValueB, conflict.PeakTime.Seconds);
            AppendNumberProperty(builder, ref first, "delta", conflict.MaxDifference);
            AppendProperty(builder, ref first, "deltaUnit", ContractDeltaUnit(conflict.Unit, conflict.Kind));
            AppendProperty(builder, ref first, "status", conflict.Status.ToString());
            if (conflict.Resolution != null)
            {
                AppendProperty(builder, ref first, "resolution", conflict.Resolution);
            }
            AppendProperty(builder, ref first, "detectedBy", DetectedByRuleEngine);
            AppendProperty(builder, ref first, "resolvedBy", conflict.ResolvedBy);
            AppendDateProperty(builder, ref first, "resolvedAt", conflict.ResolvedAt);

            builder.Append('}');
            return builder.ToString();
        }

        /// <summary>
        /// 输出冲突对象数组。仅用于内存和调试序列化，不得用于落盘，落盘请用 TryWrite/TryToJson。
        /// </summary>
        /// <param name="conflicts">冲突集合，可为 null。</param>
        /// <returns>合同格式的 JSON 数组文本；null 集合输出 []。</returns>
        public static string ToJsonArray(IEnumerable<TimelineConflict> conflicts)
        {
            StringBuilder builder = new StringBuilder();
            builder.Append('[');
            if (conflicts != null)
            {
                bool first = true;
                foreach (TimelineConflict conflict in conflicts)
                {
                    if (!first)
                    {
                        builder.Append(',');
                    }

                    first = false;
                    builder.Append(ToJson(conflict));
                }
            }

            builder.Append(']');
            return builder.ToString();
        }

        /// <summary>
        /// 将单个冲突序列化为合同 JSON；caseId 为空或空白、或格式不合格时拒绝，不返回 JSON。
        /// </summary>
        /// <param name="conflict">冲突对象。</param>
        /// <returns>成功时值为 JSON 文本；失败时 ErrorCode 为 conflict_case_id_missing 或 conflict_case_id_invalid。</returns>
        public static Result<string> TryToJson(TimelineConflict conflict)
        {
            Result<bool> issue = CaseIdWriteIssue(conflict);
            if (!issue.IsSuccess)
            {
                return Result<string>.Fail(issue.ErrorCode, issue.ErrorMessage);
            }

            return Result<string>.Ok(ToJson(conflict));
        }

        /// <summary>
        /// 将冲突集合序列化为合同 JSON 数组；任一条 caseId 为空、空白或格式不合格时拒绝整个数组。
        /// 空集合或 null 输出 []。
        /// </summary>
        /// <param name="conflicts">冲突集合，可为 null。</param>
        /// <returns>成功时值为 JSON 数组文本；失败时 ErrorCode 为 conflict_case_id_missing 或 conflict_case_id_invalid。</returns>
        public static Result<string> TryToJsonArray(IEnumerable<TimelineConflict> conflicts)
        {
            Result<bool> issue = FirstCaseIdWriteIssue(conflicts);
            if (!issue.IsSuccess)
            {
                return Result<string>.Fail(issue.ErrorCode, issue.ErrorMessage);
            }

            return Result<string>.Ok(ToJsonArray(conflicts));
        }

        /// <summary>
        /// 将单个冲突写入文件；caseId 为空、空白或格式不合格时拒绝写盘，既不创建也不改写目标文件。
        /// 格式校验使用共享的 <see cref="EvidenceItem.IsValidCaseId"/>。
        /// </summary>
        /// <param name="path">目标路径。</param>
        /// <param name="conflict">冲突对象。</param>
        /// <returns>成功时值为 true；失败时 ErrorCode 为 conflict_case_id_missing、conflict_case_id_invalid 或路径/写入错误代码。</returns>
        public static Result<bool> TryWrite(string path, TimelineConflict conflict)
        {
            Result<string> json = TryToJson(conflict);
            if (!json.IsSuccess)
            {
                return Result<bool>.Fail(json.ErrorCode, json.ErrorMessage);
            }

            return WriteText(path, json.Value);
        }

        /// <summary>
        /// 将冲突集合写入文件；任一条 caseId 为空、空白或格式不合格时拒绝写盘，既不创建也不改写目标文件。
        /// 格式校验使用共享的 <see cref="EvidenceItem.IsValidCaseId"/>。
        /// </summary>
        /// <param name="path">目标路径。</param>
        /// <param name="conflicts">冲突集合，可为 null。</param>
        /// <returns>成功时值为 true；失败时 ErrorCode 为 conflict_case_id_missing、conflict_case_id_invalid 或路径/写入错误代码。</returns>
        public static Result<bool> TryWrite(string path, IEnumerable<TimelineConflict> conflicts)
        {
            Result<string> json = TryToJsonArray(conflicts);
            if (!json.IsSuccess)
            {
                return Result<bool>.Fail(json.ErrorCode, json.ErrorMessage);
            }

            return WriteText(path, json.Value);
        }

        /// <summary>
        /// 判断冲突的 caseId 是否为空或空白（检测阶段允许，写盘阶段不允许）。
        /// </summary>
        /// <param name="conflict">冲突对象，可为 null。</param>
        /// <returns>对象为 null，或 caseId 为空/空白时返回 true。</returns>
        public static bool HasMissingCaseId(TimelineConflict conflict)
        {
            return conflict == null || string.IsNullOrWhiteSpace(conflict.CaseId);
        }

        private static Result<bool> WriteText(string path, string text)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return Result<bool>.Fail("conflict_write_path_invalid", "写盘路径不能为空。");
            }

            try
            {
                string directory = Path.GetDirectoryName(path);
                if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                File.WriteAllText(path, text, new UTF8Encoding(false));
                return Result<bool>.Ok(true);
            }
            catch (Exception ex)
            {
                return Result<bool>.Fail(
                    "conflict_write_failed",
                    "写入冲突 JSON 失败：" + ex.GetType().Name + "。");
            }
        }

        private static Result<bool> FirstCaseIdWriteIssue(IEnumerable<TimelineConflict> conflicts)
        {
            if (conflicts == null)
            {
                return Result<bool>.Ok(true);
            }

            foreach (TimelineConflict conflict in conflicts)
            {
                Result<bool> issue = CaseIdWriteIssue(conflict);
                if (!issue.IsSuccess)
                {
                    return issue;
                }
            }

            return Result<bool>.Ok(true);
        }

        /// <summary>
        /// 写盘前检查 caseId：空或空白 → conflict_case_id_missing；格式不合格 → conflict_case_id_invalid。
        /// 格式规则与 <see cref="EvidenceItem.IsValidCaseId"/> 相同。
        /// </summary>
        private static Result<bool> CaseIdWriteIssue(TimelineConflict conflict)
        {
            if (HasMissingCaseId(conflict))
            {
                string missingId = conflict == null || string.IsNullOrEmpty(conflict.ConflictId)
                    ? "(无编号)"
                    : conflict.ConflictId;
                return Result<bool>.Fail(
                    MissingCaseIdCode,
                    "冲突 " + missingId + " 的 caseId 为空或空白，拒绝写盘（conflict_case_id_missing）。");
            }

            if (!EvidenceItem.IsValidCaseId(conflict.CaseId))
            {
                string id = string.IsNullOrEmpty(conflict.ConflictId) ? "(无编号)" : conflict.ConflictId;
                return Result<bool>.Fail(
                    InvalidCaseIdCode,
                    "冲突 " + id + " 的 caseId 格式不合格，拒绝写盘（conflict_case_id_invalid）。");
            }

            return Result<bool>.Ok(true);
        }

        /// <summary>
        /// 合同 deltaUnit：不得为空串。位置写 m，速度写 kn，时间写 s；
        /// 角度单位统一为 ASCII "deg"，写盘不得出现 "°"（"°/min" 写为 "deg/min"）。
        /// 内存单位保持原样（角度仍为 "°"，位置可为空）。
        /// </summary>
        private static string ContractDeltaUnit(string unit, TrackKind kind)
        {
            if (string.IsNullOrEmpty(unit))
            {
                switch (kind)
                {
                    case TrackKind.Position:
                    case TrackKind.TargetPosition:
                        return "m";
                    case TrackKind.SpeedOverGround:
                        return "kn";
                    case TrackKind.EventTime:
                        return "s";
                    case TrackKind.CourseOverGround:
                    case TrackKind.Heading:
                    case TrackKind.RudderAngle:
                    case TrackKind.TargetBearing:
                        return "deg";
                    case TrackKind.RateOfTurn:
                        return "deg/min";
                    case TrackKind.TargetRange:
                        return "nm";
                    default:
                        return string.Empty;
                }
            }

            return unit.Replace("°", "deg");
        }

        private static void AppendObservation(
            StringBuilder builder,
            ref bool first,
            string key,
            string sourceLabel,
            double value,
            double timeSec)
        {
            if (!first)
            {
                builder.Append(',');
            }

            first = false;
            AppendQuoted(builder, key);
            builder.Append(":{");
            bool firstField = true;
            AppendProperty(builder, ref firstField, "sourceLabel", sourceLabel ?? string.Empty);
            AppendProperty(builder, ref firstField, "valueText", FormatValueText(value));
            AppendNumberProperty(builder, ref firstField, "value", value);
            AppendNumberProperty(builder, ref firstField, "timeSec", timeSec);
            builder.Append('}');
        }

        private static string FormatValueText(double value)
        {
            return IsFinite(value)
                ? value.ToString("R", CultureInfo.InvariantCulture)
                : "NotAvailable";
        }

        private static void AppendProperty(
            StringBuilder builder,
            ref bool first,
            string key,
            string value)
        {
            if (!first)
            {
                builder.Append(',');
            }

            first = false;
            AppendQuoted(builder, key);
            builder.Append(':');
            if (value == null)
            {
                builder.Append("null");
            }
            else
            {
                AppendQuoted(builder, value);
            }
        }

        private static void AppendNumberProperty(
            StringBuilder builder,
            ref bool first,
            string key,
            double value)
        {
            if (!first)
            {
                builder.Append(',');
            }

            first = false;
            AppendQuoted(builder, key);
            builder.Append(':');
            if (IsFinite(value))
            {
                builder.Append(value.ToString("R", CultureInfo.InvariantCulture));
            }
            else
            {
                builder.Append("null");
            }
        }

        private static void AppendDateProperty(
            StringBuilder builder,
            ref bool first,
            string key,
            DateTimeOffset? value)
        {
            if (!first)
            {
                builder.Append(',');
            }

            first = false;
            AppendQuoted(builder, key);
            builder.Append(':');
            if (value.HasValue)
            {
                AppendQuoted(builder, value.Value.ToString(TimeFormat, CultureInfo.InvariantCulture));
            }
            else
            {
                builder.Append("null");
            }
        }

        private static void AppendQuoted(StringBuilder builder, string text)
        {
            builder.Append('"');
            if (text != null)
            {
                for (int i = 0; i < text.Length; i++)
                {
                    char c = text[i];
                    switch (c)
                    {
                        case '"':
                            builder.Append("\\\"");
                            break;
                        case '\\':
                            builder.Append("\\\\");
                            break;
                        default:
                            if (c < ' ')
                            {
                                builder.Append("\\u");
                                builder.Append(((int)c).ToString("X4", CultureInfo.InvariantCulture));
                            }
                            else
                            {
                                builder.Append(c);
                            }
                            break;
                    }
                }
            }

            builder.Append('"');
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }
    }
}
