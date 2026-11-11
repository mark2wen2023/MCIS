using System;
using System.Globalization;
using Mcis.Core;

namespace Mcis.Domain.Colreg
{
    /// <summary>由请求身份和区间内容派生的稳定标识；不依赖时钟、随机数或当前文化。</summary>
    internal static class ColregIds
    {
        internal static string Band(ColregAnalysisRequest request, SimTime start, SimTime end,
            EncounterSituation situation, TrafficRole ownRole, TrafficRole targetRole)
        {
            return Prefix(request) + ":band:" + situation + ":" + ownRole + ":" + targetRole + ":" + Range(start, end);
        }

        internal static string Check(ColregAnalysisRequest request, ColregRuleCheck check)
        {
            return Prefix(request) + ":check:" + check.RuleId + ":" + Part(check.Clause) + ":" +
                Part(check.VesselId) + ":" + Range(check.StartTime, check.EndTime);
        }

        internal static string Stage(ColregAnalysisRequest request, SimTime start, SimTime end,
            ColregDangerStage stage)
        {
            return Prefix(request) + ":stage:" + stage + ":" + Range(start, end);
        }

        private static string Prefix(ColregAnalysisRequest request)
        {
            return Part(request.CaseId ?? "case") + ":" + Part(request.OwnVesselId) + ":" + Part(request.TargetVesselId);
        }

        // 转义分隔符，保留任意船号及案件号的区分；不作大小写或空格归一化。
        private static string Part(string value) { return Uri.EscapeDataString(value ?? ""); }

        private static string Range(SimTime start, SimTime end)
        {
            // round-trip 格式保留亚毫秒边界，避免毫秒舍入让相邻短区间产生重复 ID。
            return start.Seconds.ToString("R", CultureInfo.InvariantCulture) + "-" +
                end.Seconds.ToString("R", CultureInfo.InvariantCulture);
        }
    }
}
