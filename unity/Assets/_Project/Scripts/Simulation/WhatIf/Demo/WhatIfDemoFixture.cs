using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;

namespace Mcis.Simulation.WhatIf.Demo
{
    /// <summary>
    /// W14 What-if 演示数据（虚构）：星屿港 2026-05-18 14:15–14:27（+08:00），
    /// Mary 与 Lily 的原始航迹及 S0–S3 情景。所有数据均为示例数据（虚构）。
    /// </summary>
    public static class WhatIfDemoFixture
    {
        /// <summary>示例数据标识。</summary>
        public const string DataNotice = "示例数据（虚构）";

        /// <summary>Mary 标识。</summary>
        public const string MaryId = "Mary";

        /// <summary>Lily 标识。</summary>
        public const string LilyId = "Lily";

        /// <summary>Mary 基线转向时刻（秒，即原航迹碰撞附近）。</summary>
        public const double BaselineMaryTurnTimeSeconds = 540.0;

        /// <summary>评价起始时间（秒）。</summary>
        public const double StartSeconds = 0.0;

        /// <summary>评价结束时间（秒）。</summary>
        public const double EndSeconds = 720.0;

        private static readonly DateTimeOffset Epoch =
            new DateTimeOffset(2026, 5, 18, 14, 15, 0, TimeSpan.FromHours(8.0));

        private static readonly GeoCoord DemoEnuOrigin = new GeoCoord(121.5000, 31.2000, 0.0);

        private const string DemoReference = "WhatIfDemoFixture（虚构示例，非真实事故）";

        /// <summary>案件当地时间基准（2026-05-18 14:15:00 +08:00）。</summary>
        public static DateTimeOffset CaseEpochLocal
        {
            get { return Epoch; }
        }

        /// <summary>创建 Mary 原始航迹（虚构：船首向 355°、8 kn）。</summary>
        public static WhatIfVessel CreateMary()
        {
            ManeuverParams parameters = new ManeuverParams(
                0.10, 60.0, 12.0,
                35.0, 2.5, 90.0, 60.0, 30.0, 0.0,
                120.0, 20.0, 9000.0);
            return WhatIfVessel.FromStates(
                MaryId, parameters,
                BuildStraightStates(193.7, -2292.7, 355.0, 8.0, StartSeconds, EndSeconds, 1.0));
        }

        /// <summary>创建 Lily 原始航迹（虚构：船首向 175°、10 kn）。</summary>
        public static WhatIfVessel CreateLily()
        {
            ManeuverParams parameters = new ManeuverParams(
                0.08, 70.0, 12.0,
                35.0, 2.5, 90.0, 60.0, 30.0, 0.0,
                98.0, 16.0, 5000.0);
            return WhatIfVessel.FromStates(
                LilyId, parameters,
                BuildStraightStates(-267.2, 2795.6, 175.0, 10.0, StartSeconds, EndSeconds, 1.0));
        }

        /// <summary>创建演示评价设定。</summary>
        public static WhatIfSetup CreateSetup()
        {
            return new WhatIfSetup(
                new[] { CreateMary(), CreateLily() },
                MaryId,
                LilyId,
                StartSeconds,
                EndSeconds,
                1.0,
                0.05,
                0.5,
                0.1,
                null,
                Epoch,
                DemoEnuOrigin,
                DemoInputs());
        }

        /// <summary>虚构示例输入参数及来源（全部标为虚构示例）。</summary>
        public static IReadOnlyList<SourcedValue> DemoInputs()
        {
            return new ReadOnlyCollection<SourcedValue>(new List<SourcedValue>
            {
                new SourcedValue("Mary 船长", 120.0, "m", ValueSource.Fictional, DemoReference, "虚构示例船型"),
                new SourcedValue("Mary 型宽", 20.0, "m", ValueSource.Fictional, DemoReference, "虚构示例船型"),
                new SourcedValue("Mary 排水量", 9000.0, "t", ValueSource.Fictional, DemoReference, "虚构示例船型"),
                new SourcedValue("Lily 船长", 98.0, "m", ValueSource.Fictional, DemoReference, "虚构示例船型"),
                new SourcedValue("Lily 型宽", 16.0, "m", ValueSource.Fictional, DemoReference, "虚构示例船型"),
                new SourcedValue("Lily 排水量", 5000.0, "t", ValueSource.Fictional, DemoReference, "虚构示例船型")
            });
        }

        /// <summary>创建 S0–S3 四个情景。</summary>
        public static IReadOnlyList<WhatIfScenario> Scenarios()
        {
            VesselScenario s1Mary = VesselScenario.Create(
                MaryId,
                Intervention.TurnStarboard(420.0, 15.0, 15.0, 0.0, "提前 120 s 右舵 15°"));
            WhatIfScenario s1 = new WhatIfScenario(
                "S1", "Mary 提前右转",
                "Mary 提前 120 s，右舵 15°（目标航向改变 +15°）",
                new[] { s1Mary });

            VesselScenario s2Mary = VesselScenario.Create(
                MaryId,
                Intervention.ChangeSpeed(300.0, 6.0, 0.0, "减速至 6 kn"));
            WhatIfScenario s2 = new WhatIfScenario(
                "S2", "Mary 减速",
                "Mary 于 300 s 减速至 6 kn",
                new[] { s2Mary });

            VesselScenario s3Lily = VesselScenario.Create(
                LilyId,
                Intervention.TurnStarboard(480.0, 35.0, 30.0, 0.0, "右满舵"));
            WhatIfScenario s3 = new WhatIfScenario(
                "S3", "Lily 提前右转",
                "Lily 提前 1 min 右满舵 35°（目标航向改变 +30°）",
                new[] { s3Lily });

            return new ReadOnlyCollection<WhatIfScenario>(new List<WhatIfScenario>
            {
                WhatIfScenario.Original("S0", "原始"),
                s1,
                s2,
                s3
            });
        }

        /// <summary>创建“Mary 转向提前量”参数化情景，用于敏感性扫描。</summary>
        public static WhatIfScenario TurnAdvanceScenario(double advanceSeconds)
        {
            Intervention intervention = Intervention.TurnStarboard(
                BaselineMaryTurnTimeSeconds - advanceSeconds,
                15.0, 15.0, 0.0, "提前转向");
            VesselScenario scenario = VesselScenario.Create(MaryId, intervention);
            return new WhatIfScenario(
                "SENS",
                "Mary 转向提前量",
                "Mary 提前 " + advanceSeconds.ToString("0.##", CultureInfo.InvariantCulture) + " s 右舵 15°",
                new[] { scenario });
        }

        private static IReadOnlyList<KinematicState> BuildStraightStates(
            double eastM,
            double northM,
            double headingDeg,
            double speedKn,
            double startSeconds,
            double endSeconds,
            double stepSeconds)
        {
            List<KinematicState> states = new List<KinematicState>();
            double rad = headingDeg * Math.PI / 180.0;
            double speedMps = speedKn * VesselMotionState.MpsPerKnot;
            for (double t = startSeconds; t <= endSeconds + 1e-9; t += stepSeconds)
            {
                double distance = speedMps * t;
                states.Add(new KinematicState(
                    t,
                    eastM + distance * Math.Sin(rad),
                    northM + distance * Math.Cos(rad),
                    headingDeg,
                    speedKn,
                    0.0,
                    0.0));
            }
            return states;
        }
    }
}
