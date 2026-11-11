using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mcis.Domain.Colreg;

namespace Mcis.Acceptance.W1
{
    /// <summary>
    /// 验收用合同适配：用 Domain 的 ColregContractNames 把报告映射为 colreg.schema.json 形状。
    /// 不修改被测代码；mcis-core 接入时使用同一套名称映射。
    /// </summary>
    internal static class ColregContractMapper
    {
        public static JsonObject ToContract(string caseId, ColregAnalysisReport report, string engineVersion = "W1.1-retest-adapter")
        {
            var bands = new JsonArray();
            foreach (var b in report.TimeBands)
                bands.Add(MapBand(b));
            var checks = new JsonArray();
            foreach (var c in report.RuleChecks)
                checks.Add(MapCheck(c));
            return new JsonObject
            {
                ["caseId"] = caseId,
                ["engineVersion"] = engineVersion,
                ["disclaimer"] = report.Disclaimer,
                ["bands"] = bands,
                ["checks"] = checks
            };
        }

        public static void Write(string path, JsonObject doc)
        {
            var opts = new JsonSerializerOptions { WriteIndented = true, Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
            File.WriteAllText(path, doc.ToJsonString(opts) + "\n");
        }

        internal static string RuleName(string clause, ColregRuleId id)
        {
            string s = string.IsNullOrEmpty(clause) ? id.ToString() : clause;
            if (id == ColregRuleId.R34_35 && (s == "R34_35" || s == "R34/35")) return "R34-35";
            return s
                .Replace("R17(b)", "R17-2b", StringComparison.Ordinal)
                .Replace("R17(a)(ii)", "R17-2aii", StringComparison.Ordinal)
                .Replace("R17(a)(i)", "R17-2ai", StringComparison.Ordinal)
                .Replace("R19(d)(ii)", "R19-4ii", StringComparison.Ordinal)
                .Replace("R19(d)(i)", "R19-4i", StringComparison.Ordinal)
                .Replace("R19(b)", "R19-2b", StringComparison.Ordinal)
                .Replace("R18(a)", "R18-1a", StringComparison.Ordinal)
                .Replace("R9(a)", "R9-1a", StringComparison.Ordinal)
                .Replace("R34/35", "R34-35", StringComparison.Ordinal)
                .Replace("R34_35", "R34-35", StringComparison.Ordinal);
        }

        private static JsonObject MapBand(ColregTimeBand b)
        {
            var o = new JsonObject
            {
                ["bandId"] = b.BandId,
                ["startTimeSec"] = b.StartTime.Seconds,
                ["endTimeSec"] = b.EndTime.Seconds,
                ["situation"] = ColregContractNames.Situation(b.Situation),
                ["inSight"] = b.InSight.HasValue ? JsonValue.Create(b.InSight.Value) : null,
                ["giveWayVesselId"] = b.GiveWayVesselId,
                ["standOnVesselId"] = b.StandOnVesselId,
                ["applicableRules"] = new JsonArray(b.ApplicableRules.Select(r =>
                    JsonValue.Create(r == ColregRuleId.R34_35 ? "R34-35" : r.ToString())).ToArray()),
                ["basis"] = b.Basis,
                ["dangerStage"] = ColregContractNames.DangerStage(b.DangerStage),
                ["doubt"] = b.Doubt,
                ["doubtReason"] = string.IsNullOrEmpty(b.DoubtReason) ? null : b.DoubtReason
            };
            var status = new JsonObject();
            if (b.VesselStatus != null)
                foreach (var kv in b.VesselStatus)
                    status[kv.Key] = kv.Value.ToString();
            o["vesselStatus"] = status;
            return o;
        }

        private static JsonObject MapCheck(ColregRuleCheck c)
        {
            var o = new JsonObject
            {
                ["checkId"] = c.CheckId,
                ["rule"] = RuleName(c.Clause, c.RuleId),
                ["title"] = c.ExpectedAction,
                ["vesselId"] = c.VesselId,
                ["verdict"] = ColregContractNames.Verdict(c.Status),
                ["atTimeSec"] = c.AtTimeSec,
                ["requiredAction"] = c.ExpectedAction,
                ["actualAction"] = c.ActualAction.ToString(),
                ["evidenceIds"] = new JsonArray((c.EvidenceIds ?? Array.Empty<string>()).Select(x => JsonValue.Create(x)).ToArray()),
                ["source"] = "RuleEngine",
                ["reviewStatus"] = c.ReviewStatus.ToString()
            };
            return o;
        }
    }
}
