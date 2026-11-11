using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Acceptance.W1.RealRef
{
    /// <summary>真实案例参考运行（不计入验收通过率）。推算航迹，公开报告数据。</summary>
    public static class Program
    {
        private const double Kn = 1852.0 / 3600.0;

        public static int Main(string[] args)
        {
            string root = "/workspace/maritime-sim-design";
            string log = Path.Combine(root, "logs", "w1.1-retest-realcases.txt");
            var sw = new StringWriter();
            RunHaili5(root, sw);
            sw.WriteLine();
            RunYangze22(root, sw);
            File.WriteAllText(log, sw.ToString());
            Console.Write(sw.ToString());
            Console.Error.WriteLine("wrote " + log);
            return 0;
        }

        private static TrackSample[] Load(string path, string vessel, int every = 10)
        {
            var list = new List<TrackSample>();
            foreach (var line in File.ReadAllLines(path).Skip(1))
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                var p = line.Split(',');
                if (p[0] != vessel) continue;
                double t = double.Parse(p[1], CultureInfo.InvariantCulture);
                if (((int)Math.Round(t)) % every != 0 && t != 0) continue;
                double e = double.Parse(p[2], CultureInfo.InvariantCulture);
                double n = double.Parse(p[3], CultureInfo.InvariantCulture);
                double cog = double.Parse(p[4], CultureInfo.InvariantCulture);
                double sog = double.Parse(p[5], CultureInfo.InvariantCulture);
                double hdg = double.Parse(p[6], CultureInfo.InvariantCulture);
                bool fromCog = p.Length > 7 && p[7] == "1";
                double hdgUsed = fromCog ? cog : hdg;
                double spd = sog;
                list.Add(new TrackSample(new SimTime(t), new GeoCoord(0, 0), new EnuPosition(e, n),
                    new Double2(spd * Math.Sin(hdgUsed * Math.PI / 180), spd * Math.Cos(hdgUsed * Math.PI / 180)),
                    (float)spd, (float)cog, (float)hdgUsed, 0,
                    SampleProvenance.Presumed, TimeQuality.Estimated, fromCog));
            }
            return list.ToArray();
        }

        private static void Dump(TextWriter w, ColregAnalysisReport r, string own, string tgt, Func<double, string> clock)
        {
            foreach (var b in r.TimeBands)
                w.WriteLine("[{0}-{1}] {2} {3}={4} {5}={6} gw={7} so={8} doubt={9} reason={10} stage={11} | {12}",
                    clock(b.StartTime.Seconds), clock(b.EndTime.Seconds), b.Situation,
                    own, b.OwnRole, tgt, b.TargetRole, b.GiveWayVesselId ?? "null", b.StandOnVesselId ?? "null",
                    b.Doubt, b.DoubtReason ?? "", b.DangerStage, b.Basis);
            foreach (var s in r.DangerStages)
                w.WriteLine("  stage {0}-{1} {2}", clock(s.StartTime.Seconds), clock(s.EndTime.Seconds), s.Stage);
            foreach (var c in r.RuleChecks.Where(c => c.Status != RuleCheckStatus.NotApplicable
                && (c.RuleId == ColregRuleId.R8 || c.RuleId == ColregRuleId.R13 || c.RuleId == ColregRuleId.R14
                    || c.RuleId == ColregRuleId.R15 || c.RuleId == ColregRuleId.R16 || c.RuleId == ColregRuleId.R17
                    || c.RuleId == ColregRuleId.R18 || c.RuleId == ColregRuleId.R5 || c.RuleId == ColregRuleId.R7)))
                w.WriteLine("   {0}-{1} {2} {3} {4} brg={5:F1} DCPA={6:F0}m TCPA={7:F0}s | {8}",
                    clock(c.StartTime.Seconds), clock(c.EndTime.Seconds), c.Clause, c.VesselId, c.Status,
                    c.Evidence.RelativeBearingDeg, c.Evidence.DcpaM, c.Evidence.TcpaSeconds,
                    c.Explanation.Length > 160 ? c.Explanation.Substring(0, 160) : c.Explanation);
        }

        private static void RunHaili5(string root, TextWriter w)
        {
            w.WriteLine("=== 海力5 / WAN HAI A17 参考运行（推算航迹，自 19:51:15 起海力5=NUC）===");
            string csv = Path.Combine(root, "logs", "w1.1-retest-haili5-tracks.csv");
            var h5 = Load(csv, "haili5", 10);
            var a17 = Load(csv, "wanhai_a17", 10);
            // include last sample 752
            if (h5[h5.Length - 1].Time.Seconds < 752)
            {
                var allH = Load(csv, "haili5", 1);
                var allA = Load(csv, "wanhai_a17", 1);
                h5 = allH.Where((s, i) => i % 10 == 0 || s.Time.Seconds == allH[allH.Length - 1].Time.Seconds).ToArray();
                a17 = allA.Where((s, i) => i % 10 == 0 || s.Time.Seconds == allA[allA.Length - 1].Time.Seconds).ToArray();
            }
            const double nuc = 19 * 3600 + 51 * 60 + 15 - (19 * 3600 + 42 * 60); // 555
            var status = new[]
            {
                new ColregVesselStatusSample("HAILI5", new SimTime(0), ColregVesselStatus.PowerDriven),
                new ColregVesselStatusSample("HAILI5", new SimTime(nuc), ColregVesselStatus.NotUnderCommand),
                new ColregVesselStatusSample("WANHAI_A17", new SimTime(0), ColregVesselStatus.PowerDriven)
            };
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(
                "HAILI5", "WANHAI_A17", h5, a17, null, null, 8, true, true, null, null, null,
                "HAILI5-1025-REF", null, status));
            if (!result.IsSuccess)
            {
                w.WriteLine("FAIL " + result.ErrorCode + " " + result.ErrorMessage);
                return;
            }
            var r = result.Value;
            Func<double, string> clk = s => TimeSpan.FromSeconds(19 * 3600 + 42 * 60 + s).ToString(@"hh\:mm\:ss");
            Dump(w, r, "H5", "A17", clk);

            bool h5R14Bad = r.RuleChecks.Any(c => c.VesselId == "HAILI5" && c.RuleId == ColregRuleId.R14
                && c.StartTime.Seconds >= nuc - 1e-6 && c.Status == RuleCheckStatus.NotSatisfied);
            bool a17GivesWayAfter = r.TimeBands.Any(b => b.StartTime.Seconds >= nuc - 1e-6
                && b.Situation != EncounterSituation.NoCollisionRisk && b.GiveWayVesselId == "WANHAI_A17");
            w.WriteLine("CHECK R14(HAILI5 after 19:51:15) has NotSatisfied? {0}  (expect False)", h5R14Bad);
            w.WriteLine("CHECK A17 is give-way after 19:51:15? {0}  (expect True)", a17GivesWayAfter);
            w.WriteLine("VERDICT haili5-NUC: {0}", !h5R14Bad && a17GivesWayAfter ? "MATCHES benchmark" : "DEVIATES from benchmark (reference only)");
        }

        private static void RunYangze22(string root, TextWriter w)
        {
            w.WriteLine("=== YANGZE 22 / VEGA DREAM 参考运行（推算航迹，HDG 优先否则 COG）===");
            string csv = Path.Combine(root, "logs", "w1.1-retest-yangze22-tracks.csv");
            var y = Load(csv, "yangze22", 5);
            var v = Load(csv, "vega_dream", 5);
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(
                "YANGZE22", "VEGA_DREAM", y, v, null, null, 8, true, true, null, null, null, "YANGZE22-1230-REF"));
            if (!result.IsSuccess)
            {
                w.WriteLine("FAIL " + result.ErrorCode + " " + result.ErrorMessage);
                return;
            }
            var r = result.Value;
            // t=0 is 21:58:30
            Func<double, string> clk = s => TimeSpan.FromSeconds(21 * 3600 + 58 * 60 + 30 + s).ToString(@"hh\:mm\:ss");
            Dump(w, r, "Y22", "VEGA", clk);
            bool vegaGw = r.TimeBands.Any(b => b.Situation != EncounterSituation.NoCollisionRisk
                && b.GiveWayVesselId == "VEGA_DREAM");
            var risk = r.TimeBands.Where(b => b.Situation != EncounterSituation.NoCollisionRisk).ToList();
            w.WriteLine("situations: {0}", string.Join(",", r.TimeBands.Select(b => b.Situation.ToString()).Distinct()));
            w.WriteLine("CHECK VEGA DREAM is give-way on any risk band? {0}  (expect False)", vegaGw);
            w.WriteLine("VERDICT yangze22: {0}", !vegaGw ? "ACCEPTABLE (VEGA not give-way)" : "DEVIATES: VEGA DREAM judged give-way (reference only)");
        }
    }
}
