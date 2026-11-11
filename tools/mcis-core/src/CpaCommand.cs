using System;
using System.Text.Json.Nodes;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Cli
{
    /// <summary>
    /// cpa 子命令：调用现有 Domain/Cpa 的 CpaCalculator.CalculateByVector 与 EvaluateInstantRisk（不重写公式）。
    /// 请求（contracts/schemas/core-cpa-request.schema.json）：
    ///   { "pairs": [ { "pairId"?, "own": VesselState, "target": VesselState, "timeSec"? } ],
    ///     "origin"?: {"latDeg","lonDeg"}, "thresholds"?: {...} }
    /// VesselState = {"vesselId"?, "speedKn","courseDeg"} + 位置 {"eastNm","northNm"} 或 {"latDeg","lonDeg"}。
    /// 用经纬度时以 origin（缺省为第一对的 own 位置）为 ENU 原点，经 GeoMath.Wgs84ToEnu 转换。
    /// </summary>
    public static class CpaCommand
    {
        public static JsonNode Run(JsonNode req)
        {
            JsonArray pairs = req?["pairs"] as JsonArray;
            if (pairs == null)
            {
                // 兼容单对写法 {"own":..,"target":..}
                if (req?["own"] != null && req?["target"] != null)
                {
                    pairs = new JsonArray(JsonNode.Parse(req.ToJsonString()));
                }
                else
                {
                    throw new RequestException("BAD_REQUEST", "缺少 pairs 数组（或 own/target）");
                }
            }

            RiskThresholds th = ReadThresholds(req?["thresholds"]);
            GeoCoord? origin = ReadGeo(req?["origin"]);
            if (origin == null && pairs.Count > 0)
            {
                origin = ReadGeo(pairs[0]?["own"]);
            }

            var results = new JsonArray();
            for (int i = 0; i < pairs.Count; i++)
            {
                JsonNode p = pairs[i];
                JsonNode own = p?["own"] ?? throw new RequestException("BAD_REQUEST", "pairs[" + i + "].own 缺失");
                JsonNode tgt = p?["target"] ?? throw new RequestException("BAD_REQUEST", "pairs[" + i + "].target 缺失");
                Double2 ownPos = ReadPositionNm(own, origin, "pairs[" + i + "].own");
                Double2 tgtPos = ReadPositionNm(tgt, origin, "pairs[" + i + "].target");
                Double2 ownVel = VelocityKn(own, "pairs[" + i + "].own");
                Double2 tgtVel = VelocityKn(tgt, "pairs[" + i + "].target");
                string ownId = Str(own, "vesselId") ?? "own";
                string tgtId = Str(tgt, "vesselId") ?? "target";
                double timeSec = Num(p, "timeSec") ?? 0.0;

                CpaResult r = CpaCalculator.CalculateByVector(
                    ownPos, ownVel, tgtPos, tgtVel,
                    new CpaPairKey(ownId, tgtId), new Mcis.Core.SimTime(timeSec));
                RiskLevel level = CpaCalculator.EvaluateInstantRisk(r.DcpaNm, r.TcpaMin, r.IsDegenerate, th);

                results.Add(new JsonObject
                {
                    ["pairId"] = Str(p, "pairId") ?? (ownId + "|" + tgtId),
                    ["ownVesselId"] = ownId,
                    ["targetVesselId"] = tgtId,
                    ["timeSec"] = timeSec,
                    ["currentDistanceNm"] = Finite(r.CurrentDistanceNm),
                    ["trueBearingDeg"] = Finite(r.TrueBearingDeg),
                    ["relativeCourseDeg"] = Finite(r.RelativeCourseDeg),
                    ["relativeSpeedKn"] = Finite(r.RelativeSpeedMps / CpaCalculator.MetersPerSecondPerKnot),
                    ["dcpaNm"] = Finite(r.DcpaNm),
                    ["tcpaMin"] = Finite(r.TcpaMin),
                    ["isDiverging"] = r.IsDiverging,
                    ["isDegenerate"] = r.IsDegenerate,
                    ["riskLevel"] = level.ToString()
                });
            }

            return new JsonObject
            {
                ["thresholds"] = new JsonObject
                {
                    ["presetName"] = th.PresetName,
                    ["dangerDcpaNm"] = th.DangerDcpaNm,
                    ["dangerTcpaMin"] = th.DangerTcpaMin,
                    ["warningDcpaNm"] = th.WarningDcpaNm,
                    ["warningTcpaMin"] = th.WarningTcpaMin
                },
                ["results"] = results
            };
        }

        private static RiskThresholds ReadThresholds(JsonNode n)
        {
            RiskThresholds d = RiskThresholds.Default;
            if (n == null)
            {
                return d;
            }

            return new RiskThresholds(
                Str(n, "presetName") ?? "custom",
                Num(n, "dangerDcpaNm") ?? d.DangerDcpaNm,
                Num(n, "dangerTcpaMin") ?? d.DangerTcpaMin,
                Num(n, "warningDcpaNm") ?? d.WarningDcpaNm,
                Num(n, "warningTcpaMin") ?? d.WarningTcpaMin,
                d.HysteresisSeconds,
                d.DowngradeMarginRatio);
        }

        private static Double2 VelocityKn(JsonNode v, string path)
        {
            double sog = Num(v, "speedKn") ?? throw new RequestException("BAD_REQUEST", path + ".speedKn 缺失");
            double cog = Num(v, "courseDeg") ?? throw new RequestException("BAD_REQUEST", path + ".courseDeg 缺失");
            double rad = cog * Math.PI / 180.0;
            return new Double2(sog * Math.Sin(rad), sog * Math.Cos(rad));
        }

        private static Double2 ReadPositionNm(JsonNode v, GeoCoord? origin, string path)
        {
            double? e = Num(v, "eastNm");
            double? n = Num(v, "northNm");
            if (e.HasValue && n.HasValue)
            {
                return new Double2(e.Value, n.Value);
            }

            GeoCoord? g = ReadGeo(v);
            if (g.HasValue && origin.HasValue)
            {
                EnuPosition enu = GeoMath.Wgs84ToEnu(g.Value, origin.Value);
                return new Double2(enu.EastM / CpaCalculator.MetersPerNauticalMile, enu.NorthM / CpaCalculator.MetersPerNauticalMile);
            }

            throw new RequestException("BAD_REQUEST", path + " 需要 eastNm/northNm 或 latDeg/lonDeg");
        }

        private static GeoCoord? ReadGeo(JsonNode v)
        {
            double? lat = Num(v, "latDeg");
            double? lon = Num(v, "lonDeg");
            return lat.HasValue && lon.HasValue ? new GeoCoord(lon.Value, lat.Value, 0.0) : (GeoCoord?)null;
        }

        private static JsonNode Finite(double d)
        {
            return double.IsNaN(d) || double.IsInfinity(d) ? null : JsonValue.Create(Math.Round(d, 6));
        }

        private static double? Num(JsonNode n, string key)
        {
            JsonNode v = n?[key];
            if (v == null)
            {
                return null;
            }

            try { return v.GetValue<double>(); }
            catch (Exception) { throw new RequestException("BAD_REQUEST", key + " 应为数字"); }
        }

        private static string Str(JsonNode n, string key)
        {
            JsonNode v = n?[key];
            return v == null ? null : v.ToString();
        }
    }
}
