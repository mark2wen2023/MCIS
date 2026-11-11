using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Ecfc;

namespace Mcis.Fixtures
{
    /// <summary>
    /// 附录 C / 论文 5.4 节情节的虚构案例 Lily / Mary 演示数据工厂。
    /// 所有船名、MMSI、IMO、坐标与时间戳均为虚构示例数据（IsFictionalDemo = true），仅供演示。
    /// 会遇过程设计：t=0 处于安全（DCPA ≥ 1 nm），约 3–4 分钟后转入警告，再转入危险，约 10 分钟时碰撞。
    /// 本工厂供报告、测试与 M8 示例场景共用；M8 请直接采用此处航迹与关键时刻，勿另写一套冲突数据。
    /// </summary>
    public static class LilyMaryDemo
    {
        public const string CaseId = "CASE-2026-DEMO-LILY-MARY";
        public const string Disclaimer = "示例数据 / 虚构案例（仅供演示）";
        public const string LilyId = "vessel_lily";
        public const string MaryId = "vessel_mary";

        public static readonly GeoCoord Origin = new GeoCoord(113.705000, 22.260000, 0.0);
        public static readonly DateTimeOffset CaseEpochUtc = new DateTimeOffset(2026, 5, 18, 10, 0, 0, TimeSpan.Zero);

        /// <summary>设计接触时刻（约 10 分钟）。精确 tc 请用两船 OBB 二分搜索，可能与此相差数秒。</summary>
        public static readonly SimTime CollisionTime = new SimTime(600.0);
        public static readonly SimTime SimulationEnd = new SimTime(900.0);

        public static CaseMetadata CreateMetadata()
        {
            return new CaseMetadata(
                CaseId,
                CaseMetadata.CurrentSchemaVersion,
                "虚构青屿水道 Lily 轮与 Mary 轮碰撞事故（演示）",
                "DEMO-LILY-MARY",
                "碰撞",
                "一般",
                CaseEpochUtc.AddSeconds(CollisionTime.Seconds),
                CaseEpochUtc,
                480,
                Origin,
                0.0,
                "演示调查员",
                "演示海事机构",
                true,
                "依据论文 5.4 节情节构建的虚构演示数据，不代表任何真实海事事故。" + Disclaimer);
        }

        public static LocalEnuGeoConverter CreateGeo()
        {
            return new LocalEnuGeoConverter(Origin, 0.0);
        }

        public static VesselParticulars CreateLily()
        {
            var compartments = new List<CompartmentSpec>
            {
                new CompartmentSpec("lily-no3-port", "No.3 左舷货舱", new Double3(-8.0, 0.0, 10.0), new Double3(25.0, 12.0, 10.0), 0.85f),
                new CompartmentSpec("lily-no4-port", "No.4 左舷货舱", new Double3(-8.0, 0.0, -10.0), new Double3(25.0, 12.0, 10.0), 0.85f)
            };
            return new VesselParticulars(
                LilyId, "Lily", "莉莉轮", "413990101", "IMO 9900101", "BXXX1", "中国（虚拟演示旗）",
                "BulkCarrier", "bulk_handy", 189.9f, 32.26f, 5.2f, 6.8f, 18.0f, 24500f, "Ballast",
                new AntennaOffset(152f, 37.9f, 12.1f, 20.16f),
                new Double3(0.0, 24.5, -52.0), 0.095f, 38.0f, compartments, 70, "DEMO");
        }

        public static VesselParticulars CreateMary()
        {
            var compartments = new List<CompartmentSpec>
            {
                new CompartmentSpec("mary-forepeak", "球鼻首前尖舱", new Double3(0.0, 0.0, 100.0), new Double3(8.0, 8.0, 10.0), 0.80f)
            };
            return new VesselParticulars(
                MaryId, "Mary", "玛丽轮", "351990202", "IMO 9900202", "3FXX2", "巴拿马（虚拟演示旗）",
                "ContainerShip", "container_panamax", 225.0f, 32.20f, 12.4f, 12.8f, 19.2f, 58200f, "FullLoad",
                new AntennaOffset(165f, 60.0f, 16.1f, 16.1f),
                new Double3(0.0, 28.0, -35.0), 0.068f, 62.0f, compartments, 70, "DEMO");
        }

        /// <summary>
        /// Lily 轮南下出港航迹（ENU 米）。t=0 位于参考原点以北约 3 km，左舷向东与 Mary 计划左对左通过（DCPA ≈ 1.1 nm）；
        /// 约 7 分钟后向右转向并减速，但已来不及避开。
        /// </summary>
        public static IShipTrack BuildLilyTrack(IGeoConverter geo)
        {
            var wps = new List<ManualDrawnWaypoint>
            {
                Enu(77.2, 2985.6, 0, 10.5f, 180f),
                Enu(77.2, 2337.4, 120, 10.5f, 180f),
                Enu(77.2, 2013.3, 180, 10.5f, 180f),
                Enu(77.2, 1689.2, 240, 10.5f, 180f),
                Enu(77.2, 1365.1, 300, 10.5f, 180f),
                Enu(77.2, 1041.0, 360, 10.5f, 180f),
                Enu(71.7, 724.7, 420, 10.0f, 182f),
                Enu(47.3, 440.3, 480, 8.5f, 188f),
                Enu(17.6, 199.8, 540, 7.2f, 186f),
                Enu(0.0, 0.0, 600, 5.8f, 184f),
                Enu(-23.0, -208.5, 720, 1.0f, 190f),
                Enu(-31.8, -258.7, 900, 0.1f, 190f)
            };
            return new ManualDrawnTrackBuilder().Build(LilyId, wps, geo, InterpolationMode.CubicHermite, 10.5, 1.0, SimTime.Zero);
        }

        /// <summary>
        /// Mary 轮北上进港航迹。起初沿航道保持左对左会遇；约 3 分钟后违规向左转向切入 Lily 轮航线，约 10 分钟时以左舷撞击。
        /// </summary>
        public static IShipTrack BuildMaryTrack(IGeoConverter geo)
        {
            var wps = new List<ManualDrawnWaypoint>
            {
                Enu(2100.0, -3000.0, 0, 13.8f, 0f),
                Enu(2100.0, -2148.1, 120, 13.8f, 0f),
                Enu(2100.0, -1722.1, 180, 13.8f, 0f),
                Enu(2062.9, -1298.3, 240, 13.8f, 350f),
                Enu(1856.1, -939.3, 300, 13.6f, 310f),
                Enu(1526.8, -686.6, 360, 13.3f, 305f),
                Enu(1184.7, -468.5, 420, 13.0f, 300f),
                Enu(835.6, -290.5, 480, 12.4f, 294f),
                Enu(400.0, -120.0, 540, 11.5f, 289f),
                Enu(128.0, -24.0, 600, 9.5f, 287f),
                Enu(120.0, -30.0, 720, 0.5f, 287f),
                Enu(118.0, -32.0, 900, 0.1f, 287f)
            };
            return new ManualDrawnTrackBuilder().Build(MaryId, wps, geo, InterpolationMode.CubicHermite, 13.8, 1.0, SimTime.Zero);
        }

        public static void PopulateEcfc(EcfcService service)
        {
            service.Clear();
            AddEvent(service, "E1", "Lily 轮沿窄航道南下出港", 0.0, 0, false, LilyId, "航速", "10.5 kn");
            AddEvent(service, "E2", "Mary 轮沿航道北上进港", 0.0, 0, false, MaryId, "航速", "13.8 kn");
            AddEvent(service, "E5", "Mary 轮违规向左转向", 240.0, 0, false, MaryId, "航向", "000°→310°");
            AddEvent(service, "E4", "双方 VHF 沟通未达成一致避让协议", 300.0, 1, false, null, "时段", "18:05:00");
            AddEvent(service, "E3", "Lily 轮向右转向避让", 420.0, 0, false, LilyId, "航向", "180°→188°");
            AddEvent(service, "E6", "Lily 轮鸣放五短声并下令全速倒车", 480.0, 0, false, LilyId, "航速", "8.5 kn");
            AddEvent(service, "E7", "Mary 轮撞击 Lily 轮左舷货舱", CollisionTime.Seconds, 0, true, LilyId, "交角", "约70°");
            AddEvent(service, "E8", "Lily 轮左舷破口进水并横倾", 720.0, 0, false, LilyId, "进水", "持续增加");
            AddEvent(service, "E9", "Lily 轮开始下沉船长下令弃船", 840.0, 0, false, LilyId, "横倾", "22.0°");

            var c1q = new Dictionary<string, string> { { "流速", "1.8 kn" }, { "能见度", "2.2 nm" } };
            service.UpsertNode(new EcfcNode("C1", EcfcNodeKind.Condition, "窄航道弯曲段且正值涨潮急流", new SimTime(120), null, 1, false, false, null, null, c1q, new[] { "E-DEMO-ENV" }));
            var c2q = new Dictionary<string, string> { { "说明", "推定" } };
            service.UpsertNode(new EcfcNode("C2", EcfcNodeKind.Condition, "Mary 轮未按安全航速航行且瞭望疏忽", new SimTime(180), null, -1, false, true, MaryId, null, c2q, Array.Empty<string>()));
            var c3q = new Dictionary<string, string> { { "间距", "已低于 1 nm" } };
            service.UpsertNode(new EcfcNode("C3", EcfcNodeKind.Condition, "距离过近且 Mary 轮满载冲程大", new SimTime(420), null, 1, false, false, MaryId, null, c3q, new[] { "E-DEMO-CPA" }));

            service.ConnectNodes("E1", "E2");
            service.ConnectNodes("E2", "E5");
            service.ConnectNodes("E5", "E3");
            service.ConnectNodes("E3", "E6");
            service.ConnectNodes("E6", "E7");
            service.ConnectNodes("E7", "E8");
            service.ConnectNodes("E8", "E9");
            service.ConnectNodes("E4", "E5");
            service.ConnectNodes("C1", "E5");
            service.ConnectNodes("C2", "E5");
            service.ConnectNodes("C3", "E6");
        }

        public static EnvironmentState CreateEnvironment(SimTime time)
        {
            return new EnvironmentState(time, "HeavyFog", 2.2f, 0f, 0.55f, 7.5f, 65f, 0.8f, 4.5f, 65f, 1.8f, 325f, 0.6f);
        }

        private static void AddEvent(
            EcfcService service,
            string id,
            string text,
            double t,
            int lane,
            bool primary,
            string vessel,
            string qk,
            string qv)
        {
            var q = new Dictionary<string, string> { { qk, qv } };
            service.UpsertNode(new EcfcNode(id, EcfcNodeKind.Event, text, new SimTime(t), null, lane, primary, false, vessel, null, q, new[] { "E-DEMO-" + id }));
        }

        private static ManualDrawnWaypoint Enu(double eastM, double northM, double t, float sogKn, float hdg)
        {
            return new ManualDrawnWaypoint(new EnuPosition(eastM, northM, 0.0), new SimTime(t), sogKn, hdg);
        }
    }
}
