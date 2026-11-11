using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Mcis.Domain.Evidence
{
    /// <summary>
    /// 调查域审计记录。字段、键顺序与时间格式与 Data 层 <c>Mcis.Data.Audit.AuditRecord</c>
    /// （.mcase/audit/audit.jsonl）逐字对齐，Data 层可直接用 AuditRecord.FromJsonLine 读入。
    /// Domain 程序集不能引用 Data，所以在此复刻格式而非引用类型。
    /// </summary>
    public sealed class InvestigationAuditEntry
    {
        public DateTimeOffset Utc { get; }
        public string OperatorName { get; }
        public string Action { get; }
        public string Category { get; }
        public string CommandName { get; }
        public string BeforeValueSummary { get; }
        public string AfterValueSummary { get; }

        /// <summary>
        /// W5.1（DEFECTS/W3.md 21:32）：批量两阶段提交的批次号，合同扩展键 x-batchId（可选）。只有批量行带；空串视为 null。
        /// 非 null 时 <see cref="ToJsonLine"/> 在 7 个标准键后追加 "x-batchId"。
        /// </summary>
        public string BatchId { get; }

        public InvestigationAuditEntry(
            DateTimeOffset utc,
            string operatorName,
            string action,
            string category,
            string commandName,
            string beforeValueSummary,
            string afterValueSummary,
            string batchId)
            : this(utc, operatorName, action, category, commandName, beforeValueSummary, afterValueSummary)
        {
            BatchId = string.IsNullOrEmpty(batchId) ? null : batchId;
        }

        public InvestigationAuditEntry(
            DateTimeOffset utc,
            string operatorName,
            string action,
            string category,
            string commandName,
            string beforeValueSummary,
            string afterValueSummary)
        {
            Utc = AuditJson.TruncateToSecond(utc);
            OperatorName = operatorName ?? string.Empty;
            Action = action ?? string.Empty;
            Category = category ?? string.Empty;
            CommandName = commandName ?? string.Empty;
            BeforeValueSummary = beforeValueSummary ?? string.Empty;
            AfterValueSummary = afterValueSummary ?? string.Empty;
        }

        /// <summary>与 AuditRecord.ToJsonLine 相同的 7 键单行 JSON；带 <see cref="BatchId"/> 时追加扩展键 "x-batchId"（读取方按合同忽略未知扩展键）。</summary>
        public string ToJsonLine()
        {
            var sb = new StringBuilder();
            AuditJson.AppendStandardFields(sb, Utc, OperatorName, Action, Category, CommandName, BeforeValueSummary, AfterValueSummary);
            if (BatchId != null)
            {
                sb.Append(",\"x-batchId\":").Append(AuditJson.Quote(BatchId));
            }

            sb.Append('}');
            return sb.ToString();
        }
    }

    /// <summary>审计写入口。Data 层实现时转写到 audit/audit.jsonl（只追加）。</summary>
    public interface IInvestigationAuditSink
    {
        void Append(InvestigationAuditEntry entry);
    }

    /// <summary>内存审计汇（测试与预览用），只追加。</summary>
    public sealed class InMemoryInvestigationAuditSink : IInvestigationAuditSink
    {
        private readonly List<InvestigationAuditEntry> _entries = new List<InvestigationAuditEntry>();

        public IReadOnlyList<InvestigationAuditEntry> Entries { get { return _entries; } }

        public void Append(InvestigationAuditEntry entry)
        {
            if (entry == null)
            {
                throw new ArgumentNullException(nameof(entry));
            }

            _entries.Add(entry);
        }
    }

    /// <summary>审计类别常量（写入 category 字段）。</summary>
    public static class InvestigationAuditCategories
    {
        public const string Custody = "Custody";
        public const string Interview = "Interview";
        public const string SafetyRec = "SafetyRec";
        public const string Consultation = "Consultation";
    }

    /// <summary>与 Data 层 SimpleJson 一致的转义、时间格式，以及一个仅支持扁平对象的极简读取器。</summary>
    public static class AuditJson
    {
        public const string IsoFormat = "yyyy-MM-ddTHH:mm:ssZ";

        public static DateTimeOffset TruncateToSecond(DateTimeOffset utc)
        {
            DateTimeOffset u = utc.ToUniversalTime();
            return new DateTimeOffset(u.Ticks - (u.Ticks % TimeSpan.TicksPerSecond), TimeSpan.Zero);
        }

        public static string FormatIso(DateTimeOffset dto)
        {
            return dto.ToUniversalTime().ToString(IsoFormat, CultureInfo.InvariantCulture);
        }

        public static DateTimeOffset ParseIso(string s)
        {
            return DateTimeOffset.Parse(s, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
        }

        public static string Escape(string s)
        {
            if (s == null)
            {
                return string.Empty;
            }

            var sb = new StringBuilder(s.Length + 8);
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                switch (c)
                {
                    case '\\': sb.Append("\\\\"); break;
                    case '"': sb.Append("\\\""); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 32)
                        {
                            sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        }
                        else
                        {
                            sb.Append(c);
                        }

                        break;
                }
            }

            return sb.ToString();
        }

        public static string Quote(string s)
        {
            return "\"" + Escape(s ?? string.Empty) + "\"";
        }

        /// <summary>写入 "{" 与 7 个标准键（不含结尾 "}"），以便调用方追加扩展键。</summary>
        public static void AppendStandardFields(StringBuilder sb, DateTimeOffset utc, string op, string action, string category, string command, string before, string after)
        {
            sb.Append('{');
            sb.Append("\"utc\":").Append(Quote(FormatIso(utc))).Append(',');
            sb.Append("\"operator\":").Append(Quote(op)).Append(',');
            sb.Append("\"action\":").Append(Quote(action)).Append(',');
            sb.Append("\"category\":").Append(Quote(category)).Append(',');
            sb.Append("\"command\":").Append(Quote(command)).Append(',');
            sb.Append("\"before\":").Append(Quote(before)).Append(',');
            sb.Append("\"after\":").Append(Quote(after));
        }

        /// <summary>
        /// 读取扁平 JSON 对象（值为字符串、数字、true/false/null）。不支持嵌套；遇到嵌套或语法错误返回 false。
        /// </summary>
        public static bool TryParseFlatObject(string json, out Dictionary<string, string> fields)
        {
            fields = new Dictionary<string, string>(StringComparer.Ordinal);
            if (json == null)
            {
                return false;
            }

            int i = 0;
            SkipWs(json, ref i);
            if (i >= json.Length || json[i] != '{')
            {
                return false;
            }

            i++;
            SkipWs(json, ref i);
            if (i < json.Length && json[i] == '}')
            {
                i++;
                SkipWs(json, ref i);
                return i == json.Length;
            }

            while (true)
            {
                SkipWs(json, ref i);
                if (!TryReadString(json, ref i, out string key))
                {
                    return false;
                }

                SkipWs(json, ref i);
                if (i >= json.Length || json[i] != ':')
                {
                    return false;
                }

                i++;
                SkipWs(json, ref i);
                string value;
                if (i < json.Length && json[i] == '"')
                {
                    if (!TryReadString(json, ref i, out value))
                    {
                        return false;
                    }
                }
                else
                {
                    int start = i;
                    while (i < json.Length && json[i] != ',' && json[i] != '}' && !char.IsWhiteSpace(json[i]))
                    {
                        if (json[i] == '{' || json[i] == '[' || json[i] == '"')
                        {
                            return false;
                        }

                        i++;
                    }

                    value = json.Substring(start, i - start);
                    if (value.Length == 0)
                    {
                        return false;
                    }

                    if (value == "null")
                    {
                        value = null;
                    }
                }

                fields[key] = value;
                SkipWs(json, ref i);
                if (i >= json.Length)
                {
                    return false;
                }

                if (json[i] == ',')
                {
                    i++;
                    continue;
                }

                if (json[i] == '}')
                {
                    i++;
                    SkipWs(json, ref i);
                    return i == json.Length;
                }

                return false;
            }
        }

        private static void SkipWs(string s, ref int i)
        {
            while (i < s.Length && char.IsWhiteSpace(s[i]))
            {
                i++;
            }
        }

        private static bool TryReadString(string s, ref int i, out string value)
        {
            value = null;
            if (i >= s.Length || s[i] != '"')
            {
                return false;
            }

            i++;
            var sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"')
                {
                    value = sb.ToString();
                    return true;
                }

                if (c != '\\')
                {
                    sb.Append(c);
                    continue;
                }

                if (i >= s.Length)
                {
                    return false;
                }

                char e = s[i++];
                switch (e)
                {
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case 'u':
                        if (i + 4 > s.Length ||
                            !int.TryParse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out int code))
                        {
                            return false;
                        }

                        sb.Append((char)code);
                        i += 4;
                        break;
                    default:
                        return false;
                }
            }

            return false;
        }
    }
}
