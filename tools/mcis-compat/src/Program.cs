using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Mcis.Domain.Evidence;

// 用法：mcis-compat custody <path-to-custody.jsonl>
// 输出一行 JSON：{"ok":true,"events":N,"items":M,"status":{"EV-001":"Verified",...}} 或 {"ok":false,"code":"...","message":"..."}
internal static class Program
{
    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        if (args.Length != 2 || args[0] != "custody")
        {
            Console.Error.WriteLine("usage: mcis-compat custody <custody.jsonl>");
            return 2;
        }

        var lines = new List<string>();
        foreach (string l in File.ReadAllLines(args[1], new UTF8Encoding(false)))
        {
            if (l.Length > 0) lines.Add(l);
        }

        var r = CustodyLedger.Load(lines);
        if (!r.IsSuccess)
        {
            Console.WriteLine("{\"ok\":false,\"code\":" + AuditJson.Quote(r.ErrorCode) + ",\"message\":" + AuditJson.Quote(r.ErrorMessage) + "}");
            return 1;
        }

        var ledger = r.Value;
        var sb = new StringBuilder();
        sb.Append("{\"ok\":true,\"events\":").Append(ledger.Events.Count).Append(",\"items\":").Append(ledger.Items.Count).Append(",\"status\":{");
        for (int i = 0; i < ledger.Items.Count; i++)
        {
            string id = ledger.Items[i].EvidenceId;
            if (i > 0) sb.Append(',');
            sb.Append(AuditJson.Quote(id)).Append(':').Append(AuditJson.Quote(ledger.StatusOf(id).ToString()));
        }

        sb.Append("},\"restricted\":[");
        bool first = true;
        foreach (var it in ledger.Items)
        {
            if (!it.IsRestricted) continue;
            if (!first) sb.Append(',');
            sb.Append(AuditJson.Quote(it.EvidenceId));
            first = false;
        }

        sb.Append("]}");
        Console.WriteLine(sb.ToString());
        return 0;
    }
}
