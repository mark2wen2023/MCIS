using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;

namespace Mcis.Tests.W14
{
    public class CollisionGeometryTests
    {
        [Fact]
        public void ObliqueS0GeometryIdentifiesMaryStrikingLilyPortSide()
        {
            // 专门的虚构 T 形碰撞：Mary 自北向南，Lily 自西向东横越；
            // Mary 船首撞 Lily 左舷舯部，碰撞角约 90°。
            WhatIfSetup setup = CreateObliqueSetup();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original("S0", "斜交碰撞"));

            Assert.True(s0.Collision);
            Assert.NotNull(s0.Geometry);
            CollisionGeometry geometry = s0.Geometry;

            Assert.Equal(WhatIfDemoFixture.MaryId, geometry.StrikingVesselId);
            Assert.Equal(WhatIfDemoFixture.LilyId, geometry.StruckVesselId);
            Assert.Equal("左舷", geometry.StruckSide);
            Assert.InRange(geometry.CollisionAngleDeg, 80.0, 100.0);
            Assert.Equal(s0.TcSeconds.Value, geometry.TcSeconds);
            Assert.InRange(geometry.ContactFromStruckBowM, 0.0, 98.0);
            Assert.InRange(geometry.ContactFromStruckBowRatio, 0.0, 1.0);
            Assert.True(geometry.RelativeSpeedKn > 0.0);
            Assert.True(geometry.ContactPointGeo.HasValue, "setup 提供 ENU 原点时应输出接触点经纬度");
            Assert.Contains("Mary", geometry.Description);
            Assert.Contains("Lily", geometry.Description);
            Assert.Contains("左舷", geometry.Description);
            Assert.Contains("碰撞角", geometry.Description);
        }

        [Fact]
        public void DemoHeadOnS0StillProducesGeometry()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[0]);

            Assert.True(s0.Collision);
            Assert.NotNull(s0.Geometry);
            // W14.2 裁定 7a：虚构 S0 两船船首距接触点约 8.8 m（Mary）/ 6.8 m（Lily），均小于 max(10 m, 0.05L)，
            // 判为“船首对船首”，不指定单一撞击船（W14.1 曾按“船首更近者”判 Lily，更早按排水量规约为 Mary）。
            Assert.True(s0.Geometry.IsBowToBow);
            Assert.Equal(ImpactKind.BowToBow, s0.Geometry.Kind);
            Assert.Equal(string.Empty, s0.Geometry.StrikingVesselId);
            Assert.Equal(string.Empty, s0.Geometry.StruckVesselId);
            Assert.Equal(CollisionGeometry.BowToBowText, s0.Geometry.StruckSide);
            Assert.Contains("船首对船首", s0.Geometry.Description);
            Assert.Contains("Mary", s0.Geometry.Description);
            Assert.Contains("Lily", s0.Geometry.Description);
            Assert.InRange(s0.Geometry.CollisionAngleDeg, 0.0, 1.0);
            Assert.True(s0.Geometry.ContactPointGeo.HasValue);
        }

        [Fact]
        public void NoCollisionHasNullGeometry()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s1 = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[1]);

            Assert.False(s1.Collision);
            Assert.Null(s1.Geometry);
        }

        [Fact]
        public void ComparisonMarkdownHasAngleAndContactColumns()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results =
                ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ComparisonTable table = ScenarioComparison.Build(results);
            string markdown = table.ToMarkdown();

            Assert.Contains("碰撞角", markdown);
            Assert.Contains("接触部位", markdown);
            Assert.Contains("| S0 |", markdown);
            Assert.NotNull(table.Rows[0].CollisionAngleDeg);
            Assert.Contains("°", table.Rows[0].CollisionAngleText);
            // W14.2：虚构 S0 为船首对船首，接触部位不再写被撞船舷别。
            Assert.Contains("船首对船首", table.Rows[0].ContactPartText);
            Assert.Contains("Mary", table.Rows[0].ContactPartText);
            Assert.Contains("Lily", table.Rows[0].ContactPartText);
            Assert.Equal("—", table.Rows[1].CollisionAngleText);
            Assert.Equal("—", table.Rows[1].ContactPartText);
        }

        [Fact]
        public void ContactPointGeoUsesEnuOrigin()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[0]);

            Assert.True(s0.Geometry.ContactPointGeo.HasValue);
            Assert.InRange(s0.Geometry.ContactPointGeo.Value.LatDeg, 31.0, 31.4);
            Assert.InRange(s0.Geometry.ContactPointGeo.Value.LonDeg, 121.3, 121.7);
        }

        [Fact]
        public void SetupWithoutEnuOriginHasNullContactGeo()
        {
            WhatIfSetup withOrigin = WhatIfDemoFixture.CreateSetup();
            WhatIfSetup noOrigin = new WhatIfSetup(
                withOrigin.Vessels, withOrigin.OwnVesselId, withOrigin.TargetVesselId,
                withOrigin.StartSeconds, withOrigin.EndSeconds,
                withOrigin.CpaStepSeconds, withOrigin.CollisionPrecisionSec,
                withOrigin.CollisionCoarseStepSec, withOrigin.SafeDistanceNm,
                withOrigin.Thresholds, withOrigin.CaseEpochLocal);

            ScenarioResult s0 = ScenarioEvaluator.Evaluate(noOrigin, WhatIfDemoFixture.Scenarios()[0]);
            Assert.True(s0.Collision);
            Assert.Null(s0.Geometry.ContactPointGeo);
        }

        private static WhatIfSetup CreateObliqueSetup()
        {
            ManeuverParams maryParams = TestUtil.Params(loaM: 120.0, beamM: 20.0, displacementTons: 9000.0);
            ManeuverParams lilyParams = TestUtil.Params(loaM: 98.0, beamM: 16.0, displacementTons: 5000.0);
            WhatIfVessel mary = WhatIfVessel.FromStates(
                WhatIfDemoFixture.MaryId, maryParams,
                BuildStraightStates(0.0, 2182.0, 180.0, 8.0));
            WhatIfVessel lily = WhatIfVessel.FromStates(
                WhatIfDemoFixture.LilyId, lilyParams,
                BuildStraightStates(-2778.0, -100.0, 90.0, 10.0));
            return new WhatIfSetup(
                new[] { mary, lily },
                WhatIfDemoFixture.MaryId,
                WhatIfDemoFixture.LilyId,
                0.0, 720.0, 1.0, 0.05, 0.5, 0.1,
                null,
                new DateTimeOffset(2026, 5, 18, 14, 15, 0, TimeSpan.FromHours(8.0)),
                new GeoCoord(121.5, 31.2, 0.0));
        }

        private static IReadOnlyList<KinematicState> BuildStraightStates(
            double eastM, double northM, double headingDeg, double speedKn)
        {
            List<KinematicState> states = new List<KinematicState>();
            double rad = headingDeg * Math.PI / 180.0;
            double speedMps = speedKn * VesselMotionState.MpsPerKnot;
            for (int t = 0; t <= 720; t++)
            {
                states.Add(new KinematicState(
                    t,
                    eastM + speedMps * t * Math.Sin(rad),
                    northM + speedMps * t * Math.Cos(rad),
                    headingDeg,
                    speedKn,
                    0.0,
                    0.0));
            }
            return states;
        }
    }
}
