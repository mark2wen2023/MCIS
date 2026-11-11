using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Xunit;
using Mcis.Domain.Common;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;

namespace Mcis.Tests.W14
{
    public class Yangze22CaseTests
    {
        [Fact]
        public void CaseJsonRudderOrderR220014MatchesReport()
        {
            Yangze22Study study = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), LoadInputs());

            Assert.Equal(13, study.RudderOrders.Count);
            Yangze22RudderOrder row = study.RudderOrders.First(r => r.Id == "r-220014");
            Assert.Equal(109.0, row.HeadingDeg);
            Assert.Equal("右满舵", row.PilotOrder);
            Assert.Equal(-29.0, row.RudderCommandDeg);
            Assert.Equal(-30.0, row.RudderFeedbackDeg);
            Assert.True(row.ReversedVsOrder);
            Assert.False(string.IsNullOrWhiteSpace(row.Reference));
            Assert.Equal(2024, row.TimeBeijing.Year);
        }

        [Fact]
        public void InputsAllCarryNonEmptyReferencesAndCorrectSources()
        {
            Yangze22Study study = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), LoadInputs());

            Assert.NotEmpty(study.Inputs);
            Assert.All(study.Inputs, value =>
            {
                Assert.False(string.IsNullOrWhiteSpace(value.Reference), "缺少 Reference：" + value.Name);
                Assert.True(Enum.IsDefined(typeof(ValueSource), value.Source));
            });

            SourcedValue yangzeLoa = study.Inputs.First(v => v.Name == "YANGZE 22 船长");
            Assert.Equal(225.29, yangzeLoa.Value, 6);
            Assert.Equal(ValueSource.ReportDirect, yangzeLoa.Source);

            SourcedValue vegaLoa = study.Inputs.First(v => v.Name == "VEGA DREAM 船长");
            Assert.Equal(283.3, vegaLoa.Value, 6);
            Assert.Equal(ValueSource.ReportDirect, vegaLoa.Source);

            SourcedValue collisionAngle = study.Inputs.First(v => v.Name == "报告碰撞角");
            Assert.Equal(70.0, collisionAngle.Value);
            Assert.Equal(ValueSource.ReportDirect, collisionAngle.Source);

            SourcedValue rudderRate = study.Inputs.First(v => v.Name == "YANGZE 22 舵速");
            Assert.Equal(4.0, rudderRate.Value);
            Assert.Equal(ValueSource.ReportDerived, rudderRate.Source);

            SourcedValue k = study.Inputs.First(v => v.Name == "YANGZE 22 K");
            Assert.Equal(ValueSource.Estimated, k.Source);
            Assert.Contains("估计", k.Note);

            SourcedValue displacement = study.Inputs.First(v => v.Name == "YANGZE 22 排水量");
            Assert.Equal(ValueSource.Estimated, displacement.Source);
            Assert.Contains("1.55", displacement.Note);

            SourcedValue anchorDecel = study.Inputs.First(v => v.Name == "VEGA DREAM 锚附加减速度");
            Assert.Equal(ValueSource.Estimated, anchorDecel.Source);

            SourcedValue csvRows = study.Inputs.First(v => v.Name == "CSV 数据行数");
            Assert.Equal(54.0, csvRows.Value);
            Assert.Equal(ValueSource.ReportDerived, csvRows.Source);
        }

        [Fact]
        public void StudyProvidesS0Y1Y5AndCombinedScenarios()
        {
            Yangze22Study study = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), LoadInputs());
            string[] ids = study.Scenarios.Select(s => s.Id).ToArray();

            Assert.Contains("S0", ids);
            Assert.Contains("Y1", ids);
            Assert.Contains("Y5", ids);
            Assert.Contains("Y1+Y5", ids);
            Assert.Contains("Y4", ids);
            Assert.True(ids.Length >= 4);
            Assert.All(study.Scenarios, scenario => Assert.False(string.IsNullOrWhiteSpace(scenario.ChangeSummary)));
        }

        [Fact]
        public void S0ReplayQuantifiesDeviationFromReport()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), LoadInputs());
            ScenarioResult s0 = result.Original;

            Assert.Equal("S0", s0.ScenarioId);
            Assert.True(s0.MinDistanceNm < 0.25,
                "S0 最小距离应接近报告接触点，实际 " + s0.MinDistanceNm + " nm");
            Assert.False(string.IsNullOrWhiteSpace(result.OriginalDeviation));
            Assert.Contains("S0", result.OriginalDeviation);
            Assert.Contains("偏差", result.OriginalDeviation);
            Assert.Contains("70", result.OriginalDeviation);

            if (s0.Collision)
            {
                Assert.NotNull(s0.Geometry);
                Assert.Contains("复现接触", result.OriginalDeviation);
                Assert.Equal(Yangze22Case.VegaDreamId, s0.Geometry.StrikingVesselId);
                Assert.Equal(Yangze22Case.Yangze22Id, s0.Geometry.StruckVesselId);
                Assert.Equal("右舷", s0.Geometry.StruckSide);
                Assert.InRange(s0.Geometry.ContactFromStruckBowRatio, 0.0, 1.0);
                Assert.Contains("VEGA DREAM", s0.Geometry.Description);
                Assert.Contains("YANGZE 22", s0.Geometry.Description);
                Assert.InRange(s0.Geometry.CollisionAngleDeg,
                    LoadInputs().ReportCollisionAngleDeg - 20.0,
                    LoadInputs().ReportCollisionAngleDeg + 20.0);
            }
            else
            {
                Assert.Null(s0.Geometry);
                Assert.Contains("未复现接触", result.OriginalDeviation);
                Assert.True(s0.MinClearanceM < 200.0,
                    "未接触时 OBB 净距也应接近报告接触，实际 " + s0.MinClearanceM + " m");
            }
        }

        [Fact]
        public void Y1IncreasesMinimumDistanceVersusS0()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), LoadInputs());
            ScenarioResult s0 = result.Find("S0");
            ScenarioResult y1 = result.Find("Y1");

            Assert.NotNull(y1);
            Assert.True(y1.MinDistanceNm > s0.MinDistanceNm,
                "Y1 最小距离应大于 S0，实际 Y1=" + y1.MinDistanceNm + " nm，S0=" + s0.MinDistanceNm + " nm");
            Assert.NotEqual("碰撞", y1.VerdictText);
        }

        [Fact]
        public void Y5VegaDreamIsSlowerAtClosestApproach()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), LoadInputs());
            ScenarioResult s0 = result.Find("S0");
            ScenarioResult y5 = result.Find("Y5");

            Assert.NotNull(y5);
            double time = s0.MinDistanceTimeSeconds;
            double s0Speed = s0.Tracks[Yangze22Case.VegaDreamId].SampleAt(time).SpeedKn;
            double y5Speed = y5.Tracks[Yangze22Case.VegaDreamId].SampleAt(time).SpeedKn;
            Assert.True(y5Speed < s0Speed - 0.5,
                "Y5 中 VEGA DREAM 在 S0 最近点速度应明显更低，实际 Y5=" + y5Speed + " kn，S0=" + s0Speed + " kn");
        }

        [Fact]
        public void CombinedScenarioIsNotWorseThanEitherSingleIntervention()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), LoadInputs());
            ScenarioResult y1 = result.Find("Y1");
            ScenarioResult y5 = result.Find("Y5");
            ScenarioResult combined = result.Find("Y1+Y5");

            Assert.NotNull(combined);
            Assert.False(string.IsNullOrWhiteSpace(result.CombinedScenarioNote));
            double expected = Math.Max(y1.MinDistanceNm, y5.MinDistanceNm);
            if (combined.MinDistanceNm < expected - 1e-6)
            {
                Assert.Contains("非单调", result.CombinedScenarioNote);
                Assert.Contains("几何", result.CombinedScenarioNote);
            }
            else
            {
                Assert.Contains("≥", result.CombinedScenarioNote);
            }
        }

        [Fact]
        public void EveryResultCarriesAnchorAssumptionsDisclaimerAndInputs()
        {
            Yangze22Result result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), LoadInputs());

            Assert.Equal(5, result.Results.Count);
            Assert.All(result.Results, scenario =>
            {
                Assert.NotEmpty(scenario.Assumptions);
                Assert.Contains(scenario.Assumptions, a => a.Contains("锚"));
                Assert.Contains(scenario.Assumptions, a => a.Contains("估计"));
                Assert.DoesNotContain(scenario.Assumptions, a => a.Contains("虚构示例数据"));
                Assert.Equal(WhatIfAssumptions.DisclaimerText, scenario.Disclaimer);
                Assert.Contains("仅供分析参考", scenario.Disclaimer);
                Assert.NotEmpty(scenario.Inputs);
                Assert.All(scenario.Inputs, value => Assert.False(string.IsNullOrWhiteSpace(value.Reference)));
            });

            ComparisonTable table = result.Comparison;
            Assert.Equal(5, table.Rows.Count);
            Assert.NotEmpty(table.Inputs);
            Assert.All(table.Inputs, value => Assert.False(string.IsNullOrWhiteSpace(value.Reference)));
            string markdown = table.ToMarkdown();
            Assert.Contains("碰撞角", markdown);
            Assert.Contains("接触部位", markdown);
            Assert.Contains(WhatIfAssumptions.DisclaimerText, markdown);
        }

        [Fact]
        public void YangzeEvaluationIsDeterministic()
        {
            Yangze22Inputs inputs = LoadInputs();
            string[] lines = Yangze22TestData.ReadTrackLines();
            Yangze22Result first = Yangze22Case.Run(lines, inputs);
            Yangze22Result second = Yangze22Case.Run(lines, inputs);

            ScenarioResult a = first.Find("Y1+Y5");
            ScenarioResult b = second.Find("Y1+Y5");
            Assert.Equal(a.MinDistanceNm, b.MinDistanceNm);
            Assert.Equal(a.MinClearanceM, b.MinClearanceM);
            Assert.Equal(a.MinDcpaNm, b.MinDcpaNm);
            Assert.Equal(a.Collision, b.Collision);
            Assert.Equal(a.TcSeconds, b.TcSeconds);
            Assert.Equal(first.OriginalDeviation, second.OriginalDeviation);

            double[] times = { 0.0, 60.0, 104.0, 132.0, 180.0, 204.0, 240.0 };
            for (int i = 0; i < times.Length; i++)
            {
                Assert.Equal(
                    a.Tracks[Yangze22Case.Yangze22Id].SampleAt(times[i]),
                    b.Tracks[Yangze22Case.Yangze22Id].SampleAt(times[i]));
                Assert.Equal(
                    a.Tracks[Yangze22Case.VegaDreamId].SampleAt(times[i]),
                    b.Tracks[Yangze22Case.VegaDreamId].SampleAt(times[i]));
            }
        }

        [Fact]
        public void ScenarioInputsAreReportedWithSourceForY1AndY5()
        {
            Yangze22Study study = Yangze22Case.Build(Yangze22TestData.ReadTrackLines(), LoadInputs());
            WhatIfScenario y1 = study.Scenarios.First(s => s.Id == "Y1");
            WhatIfScenario y5 = study.Scenarios.First(s => s.Id == "Y5");

            Assert.Contains(y1.Inputs, v => v.Name == "Y1 干预时刻" && v.Value == 104.0);
            Assert.Contains(y1.Inputs, v => v.Name == "Y1 舵角" && v.Value == 35.0);
            Assert.Contains(y5.Inputs, v => v.Name == "Y5 干预时刻" && v.Value == 132.0);
            Assert.Contains(y5.Inputs, v => v.Name == "Y5 抛锚舷别（1=右舷）" &&
                                            v.Source == ValueSource.Estimated);
            Assert.All(y1.Inputs, v => Assert.False(string.IsNullOrWhiteSpace(v.Reference)));
            Assert.All(y5.Inputs, v => Assert.False(string.IsNullOrWhiteSpace(v.Reference)));
        }

        internal static Yangze22Inputs LoadInputs(bool truncateAfterReportedCollision = true)
        {
            using JsonDocument document = JsonDocument.Parse(Yangze22TestData.ReadCaseJson());
            JsonElement root = document.RootElement;

            List<Yangze22VesselInput> vessels = new List<Yangze22VesselInput>();
            int index = 0;
            foreach (JsonElement vessel in root.GetProperty("vessels").EnumerateArray())
            {
                JsonElement fieldSources = vessel.GetProperty("fieldSources");
                string reference =
                    "case.json vessels[" + index + "].fieldSources.loaM/beamM/grossTonnage；" +
                    FormatSource(fieldSources.GetProperty("loaM"));
                vessels.Add(new Yangze22VesselInput(
                    vessel.GetProperty("vesselId").GetString(),
                    vessel.GetProperty("name").GetString(),
                    vessel.GetProperty("loaM").GetDouble(),
                    vessel.GetProperty("beamM").GetDouble(),
                    vessel.GetProperty("grossTonnage").GetDouble(),
                    reference));
                index++;
            }

            List<Yangze22RudderOrder> orders = new List<Yangze22RudderOrder>();
            foreach (JsonElement row in root.GetProperty("rudderOrders").GetProperty("rows").EnumerateArray())
            {
                JsonElement source = row.GetProperty("source");
                orders.Add(new Yangze22RudderOrder(
                    row.GetProperty("id").GetString(),
                    DateTimeOffset.Parse(row.GetProperty("time").GetProperty("beijing").GetString()),
                    GetNullableDouble(row, "headingDeg"),
                    GetNullableString(row, "pilotOrder"),
                    GetNullableDouble(row, "rudderCommandDeg"),
                    GetNullableDouble(row, "rudderFeedbackDeg"),
                    GetNullableBool(row, "reversedVsOrder"),
                    "case.json rudderOrders.rows[" + row.GetProperty("id").GetString() + "].source；" +
                    FormatSource(source)));
            }

            JsonElement collision = root.GetProperty("collision");
            JsonElement location = collision.GetProperty("location");
            DateTimeOffset collisionTime = DateTimeOffset.Parse(
                collision.GetProperty("time").GetProperty("beijing").GetString());
            DateTimeOffset epoch = new DateTimeOffset(2024, 12, 30, 21, 58, 30, TimeSpan.FromHours(8.0));

            string collisionReference =
                "case.json collision.timeSource；" +
                FormatSource(collision.GetProperty("timeSource")) + "；" +
                "case.json collision.angleSource；" +
                FormatSource(collision.GetProperty("angleSource"));

            return new Yangze22Inputs(
                vessels,
                orders,
                new GeoCoord(
                    location.GetProperty("lonDeg").GetDouble(),
                    location.GetProperty("latDeg").GetDouble(),
                    0.0),
                collisionTime,
                epoch,
                collision.GetProperty("collisionAngleDeg").GetDouble(),
                collision.GetProperty("contact").GetString(),
                collisionReference,
                GetNullableDouble(collision, "yangze22HeadingDeg"),
                GetNullableDouble(collision, "vegaDreamHeadingDeg"),
                GetNullableDouble(collision, "yangze22SpeedKn"),
                GetNullableDouble(collision, "vegaDreamSpeedKn"),
                300.0,
                truncateAfterReportedCollision);
        }

        private static string FormatSource(JsonElement source)
        {
            string page = source.TryGetProperty("page", out JsonElement pageElement)
                ? pageElement.ToString() : "—";
            string pdfPage = source.TryGetProperty("pdfPage", out JsonElement pdfElement)
                ? pdfElement.ToString() : "—";
            string line = source.TryGetProperty("line", out JsonElement lineElement)
                ? lineElement.ToString() : "—";
            return "报告第" + page + "页（PDF 第" + pdfPage + "页，line " + line + "）";
        }

        private static double? GetNullableDouble(JsonElement element, string name)
        {
            if (!element.TryGetProperty(name, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
            {
                return null;
            }
            return value.GetDouble();
        }

        private static string GetNullableString(JsonElement element, string name)
        {
            if (!element.TryGetProperty(name, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
            {
                return null;
            }
            return value.GetString();
        }

        private static bool? GetNullableBool(JsonElement element, string name)
        {
            if (!element.TryGetProperty(name, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
            {
                return null;
            }
            return value.GetBoolean();
        }
    }
}
