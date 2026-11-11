using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json.Nodes;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Cli
{
    /// <summary>
    /// colreg 子命令：调用已验收的 W1 Domain/Colreg，输出符合 colreg.schema.json 的 bands + checks。
    /// 请求（服务 evaluate 及 CLI 通用）：
    ///   { "caseId", "caseEpochUtc"?, "origin"?: {latDeg,lonDeg},
    ///     "ownVesselId"?, "targetVesselId"?,
    ///     "tracks": { "<id>": [ TrackPoint, ... ], ... }
    ///       或 "own": [...], "target": [...],
    ///     "visibilityNm"?, "vesselsInSight"?, "inNarrowChannel"?,
    ///     "inSightSamples"?: [{timeSec,inSight}],
    ///     "vesselStatus"?: [{vesselId,timeSec,status}],
    ///     "evidenceIds"?: ["EV-001"],
    ///     "thresholds"?: { ... ColregThresholds 字段 ... } }
    /// TrackPoint：timeSec + (latDeg/lonDeg | eastNm/northNm | eastM/northM) + sogKn + cogDeg + 可选 hdgDeg。
    /// </summary>
    public static class ColregCommand
    {
        private const double MetersPerNm = 1852.0;

        public static JsonNode Run(JsonNode req)
        {
            if (req == null) throw new RequestException("BAD_REQUEST", "缺少请求体");
            string caseId = Str(req, "caseId") ?? "case";
            if (caseId.Length < 3)
                throw new RequestException("BAD_REQUEST", "caseId 至少 3 个字符");

            DateTimeOffset? epoch = null;
            string epochText = Str(req, "caseEpochUtc");
            if (!string.IsNullOrEmpty(epochText))
            {
                if (!DateTimeOffset.TryParse(epochText, CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var parsed))
                    throw new RequestException("BAD_REQUEST", "caseEpochUtc 无法解析");
                epoch = parsed;
            }

            Dictionary<string, List<JsonNode>> tracks = ReadTracks(req);
            string ownId = Str(req, "ownVesselId");
            string tgtId = Str(req, "targetVesselId");
            if (string.IsNullOrEmpty(ownId) || string.IsNullOrEmpty(tgtId))
            {
                var ids = tracks.Keys.ToList();
                if (ids.Count < 2)
                    throw new RequestException("BAD_REQUEST", "需要至少两条船舶航迹（tracks 或 own/target）");
                if (string.IsNullOrEmpty(ownId)) ownId = ids[0];
                if (string.IsNullOrEmpty(tgtId)) tgtId = ids.First(x => x != ownId);
            }
            if (!tracks.ContainsKey(ownId) || !tracks.ContainsKey(tgtId))
                throw new RequestException("BAD_REQUEST", "找不到指定船舶的航迹：" + ownId + " / " + tgtId);
            if (ownId == tgtId)
                throw new RequestException("BAD_REQUEST", "本船与他船标识不能相同");

            GeoCoord? origin = ReadGeo(req["origin"]);
            if (origin == null)
                origin = FirstGeo(tracks[ownId]) ?? FirstGeo(tracks[tgtId]);
            if (origin == null)
                origin = new GeoCoord(0, 0, 0);

            var own = BuildSamples(tracks[ownId], origin.Value, "own");
            var tgt = BuildSamples(tracks[tgtId], origin.Value, "target");
            var thresholds = ReadThresholds(req["thresholds"]);
            var status = ReadStatus(req["vesselStatus"] ?? req["vesselStatusSamples"]);
            var sight = ReadSight(req["inSightSamples"]);
            var evidence = ReadStrings(req["evidenceIds"]);
            double? vis = Num(req, "visibilityNm");
            bool? inSight = req["vesselsInSight"] == null ? (bool?)null : req["vesselsInSight"].GetValue<bool>();
            bool narrow = req["inNarrowChannel"] != null && req["inNarrowChannel"].GetValue<bool>();

            var request = new ColregAnalysisRequest(ownId, tgtId, own, tgt, thresholds, null, vis, inSight,
                narrow, epoch, sight, null, caseId, evidence, status);
            var result = new ColregEngine().Analyze(request);
            if (!result.IsSuccess)
                throw new RequestException("BAD_REQUEST", result.ErrorCode + ": " + result.ErrorMessage);
            return ToContract(caseId, result.Value, Program.CoreVersion);
        }

        internal static JsonObject ToContract(string caseId, ColregAnalysisReport report, string engineVersion)
        {
            var bands = new JsonArray();
            foreach (var b in report.TimeBands) bands.Add(MapBand(b));
            var checks = new JsonArray();
            foreach (var c in report.RuleChecks) checks.Add(MapCheck(c));
            return new JsonObject
            {
                ["caseId"] = caseId,
                ["engineVersion"] = engineVersion,
                ["disclaimer"] = report.Disclaimer,
                ["bands"] = bands,
                ["checks"] = checks
            };
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
                foreach (var kv in b.VesselStatus) status[kv.Key] = kv.Value.ToString();
            o["vesselStatus"] = status;
            return o;
        }

        private static JsonObject MapCheck(ColregRuleCheck c)
        {
            string actual = string.Format(CultureInfo.InvariantCulture,
                "航向变化 {0:F1}°，航速变化 {1:F2} m/s，转向={2}，变速={3}",
                c.ActualAction.HeadingChangeDeg, c.ActualAction.SpeedChangeMps,
                c.ActualAction.Turn, c.ActualAction.Speed);
            return new JsonObject
            {
                ["checkId"] = c.CheckId,
                ["rule"] = RuleName(c.Clause, c.RuleId),
                ["title"] = c.ExpectedAction,
                ["vesselId"] = c.VesselId,
                ["verdict"] = ColregContractNames.Verdict(c.Status),
                ["atTimeSec"] = c.AtTimeSec,
                ["requiredAction"] = c.ExpectedAction,
                ["actualAction"] = actual,
                ["evidenceIds"] = new JsonArray((c.EvidenceIds ?? Array.Empty<string>()).Select(x => JsonValue.Create(x)).ToArray()),
                ["source"] = "RuleEngine",
                ["reviewStatus"] = c.ReviewStatus.ToString()
            };
        }

        private static Dictionary<string, List<JsonNode>> ReadTracks(JsonNode req)
        {
            var map = new Dictionary<string, List<JsonNode>>();
            if (req["tracks"] is JsonObject obj)
            {
                foreach (var kv in obj)
                {
                    var arr = kv.Value as JsonArray;
                    if (arr == null) throw new RequestException("BAD_REQUEST", "tracks." + kv.Key + " 应为数组");
                    map[kv.Key] = arr.Where(x => x != null).ToList();
                }
            }
            if (req["own"] is JsonArray own)
                map[Str(req, "ownVesselId") ?? "own"] = own.Where(x => x != null).ToList();
            if (req["target"] is JsonArray tgt)
                map[Str(req, "targetVesselId") ?? "target"] = tgt.Where(x => x != null).ToList();
            return map;
        }

        private static List<TrackSample> BuildSamples(List<JsonNode> points, GeoCoord origin, string path)
        {
            if (points == null || points.Count == 0)
                throw new RequestException("BAD_REQUEST", path + " 航迹为空");
            var list = new List<TrackSample>(points.Count);
            foreach (var p in points)
            {
                double? t = Num(p, "timeSec");
                if (!t.HasValue) throw new RequestException("BAD_REQUEST", path + " 缺少 timeSec");
                double? sogKn = Num(p, "sogKn") ?? Num(p, "speedKn");
                if (!sogKn.HasValue) throw new RequestException("BAD_REQUEST", path + " 缺少 sogKn");
                double? cog = Num(p, "cogDeg") ?? Num(p, "courseDeg");
                if (!cog.HasValue) throw new RequestException("BAD_REQUEST", path + " 缺少 cogDeg");
                double? hdg = Num(p, "hdgDeg");
                bool fromCog = !hdg.HasValue;
                double heading = fromCog ? cog.Value : hdg.Value;
                double sogMps = sogKn.Value * (MetersPerNm / 3600.0);
                double rad = heading * Math.PI / 180.0;
                var vel = new Double2(sogMps * Math.Sin(rad), sogMps * Math.Cos(rad));

                GeoCoord? geo = ReadGeo(p);
                EnuPosition enu;
                if (TryEnu(p, out double east, out double north))
                    enu = new EnuPosition(east, north);
                else if (geo.HasValue)
                    enu = GeoMath.Wgs84ToEnu(geo.Value, origin);
                else
                    throw new RequestException("BAD_REQUEST", path + " 需要 latDeg/lonDeg 或 eastNm/northNm 或 eastM/northM");
                if (geo == null) geo = origin;

                var prov = ParseProvenance(Str(p, "provenance"));
                list.Add(new TrackSample(new SimTime(t.Value), geo.Value, enu, vel, (float)sogMps,
                    (float)cog.Value, (float)heading, 0, prov, TimeQuality.Estimated, fromCog));
            }
            return list.OrderBy(s => s.Time.Seconds).ToList();
        }

        private static bool TryEnu(JsonNode p, out double eastM, out double northM)
        {
            double? eM = Num(p, "eastM"), nM = Num(p, "northM");
            if (eM.HasValue && nM.HasValue) { eastM = eM.Value; northM = nM.Value; return true; }
            double? eNm = Num(p, "eastNm"), nNm = Num(p, "northNm");
            if (eNm.HasValue && nNm.HasValue) { eastM = eNm.Value * MetersPerNm; northM = nNm.Value * MetersPerNm; return true; }
            eastM = northM = 0;
            return false;
        }

        private static SampleProvenance ParseProvenance(string s)
        {
            if (string.IsNullOrEmpty(s)) return SampleProvenance.Measured;
            if (s == "Simulated") return SampleProvenance.Presumed;
            if (Enum.TryParse(s, true, out SampleProvenance p)) return p;
            return SampleProvenance.Measured;
        }

        private static List<ColregVesselStatusSample> ReadStatus(JsonNode node)
        {
            var arr = node as JsonArray;
            if (arr == null || arr.Count == 0) return null;
            var list = new List<ColregVesselStatusSample>();
            foreach (var n in arr)
            {
                string id = Str(n, "vesselId");
                double? t = Num(n, "timeSec");
                string st = Str(n, "status");
                if (string.IsNullOrEmpty(id) || !t.HasValue || string.IsNullOrEmpty(st))
                    throw new RequestException("BAD_REQUEST", "vesselStatus 项需要 vesselId、timeSec、status");
                if (!Enum.TryParse(st, true, out ColregVesselStatus status))
                    throw new RequestException("BAD_REQUEST", "未知船舶状态：" + st);
                list.Add(new ColregVesselStatusSample(id, new SimTime(t.Value), status));
            }
            return list;
        }

        private static List<ColregInSightSample> ReadSight(JsonNode node)
        {
            var arr = node as JsonArray;
            if (arr == null || arr.Count == 0) return null;
            var list = new List<ColregInSightSample>();
            foreach (var n in arr)
            {
                double? t = Num(n, "timeSec");
                if (!t.HasValue || n["inSight"] == null)
                    throw new RequestException("BAD_REQUEST", "inSightSamples 项需要 timeSec、inSight");
                list.Add(new ColregInSightSample(new SimTime(t.Value), n["inSight"].GetValue<bool>()));
            }
            return list;
        }

        private static List<string> ReadStrings(JsonNode node)
        {
            var arr = node as JsonArray;
            if (arr == null) return null;
            return arr.Select(x => x == null ? null : x.ToString()).Where(s => !string.IsNullOrEmpty(s)).ToList();
        }

        private static ColregThresholds ReadThresholds(JsonNode n)
        {
            if (n == null) return ColregThresholds.Default;
            var d = ColregThresholds.Default;
            return new ColregThresholds(
                headOnHalfAngleDeg: Num(n, "headOnHalfAngleDeg") ?? d.HeadOnHalfAngleDeg,
                overtakingAbaftBeamAngleDeg: Num(n, "overtakingAbaftBeamAngleDeg") ?? d.OvertakingAbaftBeamAngleDeg,
                restrictedVisibilityNm: Num(n, "restrictedVisibilityNm") ?? d.RestrictedVisibilityNm,
                collisionRiskDcpaNm: Num(n, "collisionRiskDcpaNm") ?? d.CollisionRiskDcpaNm,
                safePassingDcpaNm: Num(n, "safePassingDcpaNm") ?? d.SafePassingDcpaNm,
                substantialTurnDeg: Num(n, "substantialTurnDeg") ?? d.SubstantialTurnDeg,
                sampleIntervalSeconds: Num(n, "sampleIntervalSeconds") ?? d.SampleIntervalSeconds,
                earlyActionTcpaSeconds: Num(n, "earlyActionTcpaSeconds") ?? d.EarlyActionTcpaSeconds,
                earlyActionDistanceNm: Num(n, "earlyActionDistanceNm") ?? d.EarlyActionDistanceNm,
                safeSpeedMps: Num(n, "safeSpeedMps") ?? d.SafeSpeedMps,
                headOnForwardHalfAngleDeg: Num(n, "headOnForwardHalfAngleDeg") ?? d.HeadOnForwardHalfAngleDeg,
                standOnEmergencyTcpaSeconds: Num(n, "standOnEmergencyTcpaSeconds") ?? d.StandOnEmergencyTcpaSeconds,
                standOnInterventionTcpaSeconds: Num(n, "standOnInterventionTcpaSeconds") ?? d.StandOnInterventionTcpaSeconds,
                clearDistanceNm: Num(n, "clearDistanceNm") ?? d.ClearDistanceNm,
                collisionRiskTcpaSeconds: Num(n, "collisionRiskTcpaSeconds") ?? d.CollisionRiskTcpaSeconds,
                closeQuartersDcpaNm: Num(n, "closeQuartersDcpaNm") ?? d.CloseQuartersDcpaNm,
                closeQuartersTcpaSeconds: Num(n, "closeQuartersTcpaSeconds") ?? d.CloseQuartersTcpaSeconds,
                substantialSpeedChangeFraction: Num(n, "substantialSpeedChangeFraction") ?? d.SubstantialSpeedChangeFraction,
                substantialTurnWindowSeconds: Num(n, "substantialTurnWindowSeconds") ?? d.SubstantialTurnWindowSeconds,
                headOnDoubtBearingDeg: Num(n, "headOnDoubtBearingDeg") ?? d.HeadOnDoubtBearingDeg,
                lockHeadingStableWindowSeconds: Num(n, "lockHeadingStableWindowSeconds") ?? d.LockHeadingStableWindowSeconds,
                lockHeadingStableMaxChangeDeg: Num(n, "lockHeadingStableMaxChangeDeg") ?? d.LockHeadingStableMaxChangeDeg,
                lockMaxDeferSeconds: Num(n, "lockMaxDeferSeconds") ?? d.LockMaxDeferSeconds);
        }

        private static GeoCoord? FirstGeo(List<JsonNode> points)
        {
            foreach (var p in points)
            {
                var g = ReadGeo(p);
                if (g.HasValue) return g;
            }
            return null;
        }

        private static GeoCoord? ReadGeo(JsonNode v)
        {
            if (v == null) return null;
            double? lat = Num(v, "latDeg");
            double? lon = Num(v, "lonDeg");
            return lat.HasValue && lon.HasValue ? new GeoCoord(lon.Value, lat.Value, 0.0) : (GeoCoord?)null;
        }

        private static double? Num(JsonNode n, string key)
        {
            JsonNode v = n?[key];
            if (v == null || v.GetValueKind() == System.Text.Json.JsonValueKind.Null) return null;
            try { return v.GetValue<double>(); }
            catch (Exception) { throw new RequestException("BAD_REQUEST", key + " 应为数字"); }
        }

        private static string Str(JsonNode n, string key)
        {
            JsonNode v = n?[key];
            if (v == null || v.GetValueKind() == System.Text.Json.JsonValueKind.Null) return null;
            return v.GetValueKind() == System.Text.Json.JsonValueKind.String ? v.GetValue<string>() : v.ToString();
        }
    }
}
