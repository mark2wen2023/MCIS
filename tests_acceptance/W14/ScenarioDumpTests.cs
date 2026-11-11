using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    /// <summary>把关键情景结果与采样航迹写入 logs/，供独立 Python 核算使用。</summary>
    public class ScenarioDumpTests
    {
        [Fact]
        public void DumpScenariosForIndependentCheck()
        {
            StringBuilder json = new StringBuilder();
            json.AppendLine("{");
            json.AppendLine("  \"demo\": {");
            WhatIfSetup demoSetup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<WhatIfScenario> demoScenarios = WhatIfDemoFixture.Scenarios();
            IReadOnlyList<ScenarioResult> demoResults = ScenarioEvaluator.EvaluateAll(demoSetup, demoScenarios);
            AppendResults(json, demoResults, 1, "    ");
            json.AppendLine(",");
            json.Append("    \"maryParams\": ");
            AppendParams(json, demoSetup.FindVessel(WhatIfDemoFixture.MaryId).Params);
            json.AppendLine(",");
            json.Append("    \"lilyParams\": ");
            AppendParams(json, demoSetup.FindVessel(WhatIfDemoFixture.LilyId).Params);
            json.AppendLine();
            json.AppendLine("  },");

            Yangze22Result yangze = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            json.AppendLine("  \"yangze22\": {");
            AppendResults(json, yangze.Results, 1, "    ");
            json.AppendLine(",");
            json.AppendLine("    \"originalDeviation\": " + Q(yangze.OriginalDeviation) + ",");
            json.AppendLine("    \"combinedNote\": " + Q(yangze.CombinedScenarioNote));
            json.AppendLine("  }");
            json.AppendLine("}");

            string path = Path.Combine(W14AccFixture.LogsDirectory, "w14-scenario-dump.json");
            File.WriteAllText(path, json.ToString(), Encoding.UTF8);
            Assert.True(File.Exists(path));
            Assert.True(new FileInfo(path).Length > 1000);
        }

        private static void AppendResults(
            StringBuilder json, IReadOnlyList<ScenarioResult> results, int trackStep, string indent)
        {
            json.AppendLine(indent + "\"results\": [");
            for (int i = 0; i < results.Count; i++)
            {
                ScenarioResult r = results[i];
                json.Append(indent + "  {");
                json.Append("\"id\":" + Q(r.ScenarioId));
                json.Append(",\"verdict\":" + Q(r.Verdict.ToString()));
                json.Append(",\"verdictText\":" + Q(r.VerdictText));
                json.Append(",\"collision\":" + (r.Collision ? "true" : "false"));
                json.Append(",\"tcSeconds\":" + (r.TcSeconds.HasValue ? F(r.TcSeconds.Value) : "null"));
                json.Append(",\"tcLocal\":" + Q(r.TcLocalText));
                json.Append(",\"minDistanceNm\":" + F(r.MinDistanceNm));
                json.Append(",\"minClearanceM\":" + F(r.MinClearanceM));
                json.Append(",\"minDcpaNm\":" + F(r.MinDcpaNm));
                json.Append(",\"disclaimer\":" + Q(r.Disclaimer));
                if (r.Geometry != null)
                {
                    json.Append(",\"geometry\":{");
                    json.Append("\"striking\":" + Q(r.Geometry.StrikingVesselId));
                    json.Append(",\"struck\":" + Q(r.Geometry.StruckVesselId));
                    json.Append(",\"angleDeg\":" + F(r.Geometry.CollisionAngleDeg));
                    json.Append(",\"side\":" + Q(r.Geometry.StruckSide));
                    json.Append(",\"fromBowM\":" + F(r.Geometry.ContactFromStruckBowM));
                    json.Append(",\"contactE\":" + F(r.Geometry.ContactPointEnu.EastM));
                    json.Append(",\"contactN\":" + F(r.Geometry.ContactPointEnu.NorthM));
                    json.Append("}");
                }
                else
                {
                    json.Append(",\"geometry\":null");
                }
                json.Append(",\"tracks\":{");
                bool firstTrack = true;
                foreach (KeyValuePair<string, CounterfactualTrack> kv in r.Tracks)
                {
                    if (!firstTrack) json.Append(",");
                    firstTrack = false;
                    json.Append(Q(kv.Key) + ":{");
                    json.Append("\"loaM\":" + F(kv.Value.LoaM));
                    json.Append(",\"beamM\":" + F(kv.Value.BeamM));
                    json.Append(",\"samples\":[");
                    bool first = true;
                    double start = kv.Value.States[0].TimeSeconds;
                    double end = kv.Value.States[kv.Value.States.Count - 1].TimeSeconds;
                    for (double t = start; t <= end + 1e-9; t += trackStep)
                    {
                        KinematicState s = kv.Value.SampleAt(t);
                        if (!first) json.Append(",");
                        first = false;
                        json.Append("[");
                        json.Append(F(s.TimeSeconds)); json.Append(",");
                        json.Append(F(s.EastM)); json.Append(",");
                        json.Append(F(s.NorthM)); json.Append(",");
                        json.Append(F(s.HeadingDeg)); json.Append(",");
                        json.Append(F(s.SpeedKn)); json.Append(",");
                        json.Append(F(s.RotDegPerSec)); json.Append(",");
                        json.Append(F(s.RudderDeg));
                        json.Append("]");
                    }
                    json.Append("]}");
                }
                json.Append("}");
                json.Append("}");
                if (i < results.Count - 1) json.Append(",");
                json.AppendLine();
            }
            json.Append(indent + "]");
        }

        private static void AppendParams(StringBuilder json, ManeuverParams p)
        {
            json.Append("{");
            json.Append("\"K\":" + F(p.K));
            json.Append(",\"T\":" + F(p.T));
            json.Append(",\"uRef\":" + F(p.ReferenceSpeedKn));
            json.Append(",\"maxRudder\":" + F(p.MaxRudderDeg));
            json.Append(",\"rudderRate\":" + F(p.RudderRateDegPerSec));
            json.Append(",\"speedTau\":" + F(p.SpeedTimeConstantSec));
            json.Append(",\"kP\":" + F(NomotoSimulator.HeadingHoldProportionalGain));
            json.Append(",\"kD\":" + F(NomotoSimulator.HeadingHoldDerivativeGain));
            json.Append(",\"loaM\":" + F(p.LoaM));
            json.Append(",\"beamM\":" + F(p.BeamM));
            json.Append("}");
        }

        private static string F(double v)
        {
            return v.ToString("R", CultureInfo.InvariantCulture);
        }

        private static string Q(string s)
        {
            if (s == null) return "null";
            return "\"" + s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n") + "\"";
        }
    }
}
