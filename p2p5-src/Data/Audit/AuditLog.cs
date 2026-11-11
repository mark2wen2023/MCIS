using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Core.Commands;
using Mcis.Data.CasePackage;

namespace Mcis.Data.Audit
{
    /// <summary>单条追加写入的审计记录。</summary>
    public sealed class AuditRecord
    {
        public DateTimeOffset Utc { get; }
        public string OperatorName { get; }
        public string Action { get; }
        public string Category { get; }
        public string CommandName { get; }
        public string BeforeValueSummary { get; }
        public string AfterValueSummary { get; }

        public AuditRecord(
            DateTimeOffset utc,
            string operatorName,
            string action,
            string category,
            string commandName,
            string beforeValueSummary,
            string afterValueSummary)
        {
            Utc = utc;
            OperatorName = operatorName ?? string.Empty;
            Action = action ?? string.Empty;
            Category = category ?? string.Empty;
            CommandName = commandName ?? string.Empty;
            BeforeValueSummary = beforeValueSummary ?? string.Empty;
            AfterValueSummary = afterValueSummary ?? string.Empty;
        }

        public string ToJsonLine()
        {
            var sb = new StringBuilder();
            sb.Append('{');
            sb.Append("\"utc\":").Append(SimpleJson.Quote(SimpleJson.FormatIso(Utc))).Append(',');
            sb.Append("\"operator\":").Append(SimpleJson.Quote(OperatorName)).Append(',');
            sb.Append("\"action\":").Append(SimpleJson.Quote(Action)).Append(',');
            sb.Append("\"category\":").Append(SimpleJson.Quote(Category)).Append(',');
            sb.Append("\"command\":").Append(SimpleJson.Quote(CommandName)).Append(',');
            sb.Append("\"before\":").Append(SimpleJson.Quote(BeforeValueSummary)).Append(',');
            sb.Append("\"after\":").Append(SimpleJson.Quote(AfterValueSummary));
            sb.Append('}');
            return sb.ToString();
        }

        public static AuditRecord FromJsonLine(string line)
        {
            SimpleJson.JsonValue v = SimpleJson.Parse(line);
            string utc = v.GetString("utc");
            return new AuditRecord(
                string.IsNullOrEmpty(utc) ? DateTimeOffset.UtcNow : SimpleJson.ParseIso(utc),
                v.GetString("operator"),
                v.GetString("action"),
                v.GetString("category"),
                v.GetString("command"),
                v.GetString("before"),
                v.GetString("after"));
        }
    }

    /// <summary>向 .mcase/audit/audit.jsonl 追加写入的只增审计日志。</summary>
    public sealed class AuditLog
    {
        private readonly string _filePath;
        private readonly object _sync = new object();

        public string FilePath { get { return _filePath; } }

        public AuditLog(string filePath)
        {
            _filePath = filePath ?? throw new ArgumentNullException(nameof(filePath));
            string dir = Path.GetDirectoryName(_filePath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            if (!File.Exists(_filePath))
            {
                File.WriteAllText(_filePath, string.Empty, new UTF8Encoding(false));
            }
        }

        public static AuditLog OpenInWorkspace(string workspaceRoot)
        {
            string path = CasePackageLayout.Combine(workspaceRoot, CasePackageLayout.AuditDirectory + "/" + CasePackageLayout.AuditFileName);
            return new AuditLog(path);
        }

        /// <summary>追加一条记录。本方法只追加，从不重写已有行。</summary>
        public void Append(AuditRecord record)
        {
            if (record == null)
            {
                throw new ArgumentNullException(nameof(record));
            }

            string line = record.ToJsonLine() + "\n";
            lock (_sync)
            {
                File.AppendAllText(_filePath, line, new UTF8Encoding(false));
            }
        }

        public void AppendCommand(IReversibleCommand command, string action, string operatorName)
        {
            Append(new AuditRecord(
                DateTimeOffset.UtcNow,
                operatorName,
                action,
                command.AuditCategory,
                command.CommandName,
                command.BeforeValueSummary,
                command.AfterValueSummary));
        }

        public IReadOnlyList<AuditRecord> ReadAll()
        {
            var list = new List<AuditRecord>();
            if (!File.Exists(_filePath))
            {
                return list;
            }

            string[] lines;
            lock (_sync)
            {
                lines = File.ReadAllLines(_filePath, Encoding.UTF8);
            }

            for (int i = 0; i < lines.Length; i++)
            {
                string line = lines[i].Trim();
                if (line.Length == 0)
                {
                    continue;
                }

                list.Add(AuditRecord.FromJsonLine(line));
            }

            return list;
        }
    }
}
