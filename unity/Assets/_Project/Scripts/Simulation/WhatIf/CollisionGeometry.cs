using System;
using System.Globalization;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Simulation.Damage;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>撞击形态（裁定 7a）。</summary>
    public enum ImpactKind
    {
        /// <summary>一船船首撞另一船（指定单一撞击船与被撞船）。</summary>
        BowStrike = 0,

        /// <summary>船首对船首：两船船首到接触点的距离都小于各自 max(10 m, 0.05L)，不指定单一撞击船。</summary>
        BowToBow = 1
    }

    /// <summary>
    /// 首次接触的碰撞几何：接触点、撞击船/被撞船、碰撞角、被撞船舷别与沿首尾线位置、
    /// 相对速度与中文描述。
    /// 撞击船判定（裁定 7a，W14.2）：两船船首到接触点的距离都小于各自 max(10 m, 0.05L) 时为“船首对船首”，
    /// 不指定单一撞击船（StrikingVesselId/StruckVesselId 为空串）；其余情况取船首离接触点更近的一方为撞击船。
    /// 不再按排水量兜底。
    /// </summary>
    public sealed class CollisionGeometry
    {
        /// <summary>“船首对船首”中文标签。</summary>
        public const string BowToBowText = "船首对船首";

        /// <summary>船首对船首判定的绝对阈值下限（米）。</summary>
        public const double BowToBowMinThresholdM = 10.0;

        /// <summary>船首对船首判定的船长比例阈值（L 的倍数）。</summary>
        public const double BowToBowLoaRatio = 0.05;

        /// <summary>撞击形态。</summary>
        public ImpactKind Kind { get; }

        /// <summary>是否判为“船首对船首”（不指定单一撞击船）。</summary>
        public bool IsBowToBow
        {
            get { return Kind == ImpactKind.BowToBow; }
        }

        /// <summary>本船（setup.OwnVesselId）标识。</summary>
        public string OwnVesselId { get; }

        /// <summary>目标船（setup.TargetVesselId）标识。</summary>
        public string TargetVesselId { get; }

        /// <summary>接触时刻本船船首点到接触点的距离（米）。</summary>
        public double OwnBowToContactM { get; }

        /// <summary>接触时刻目标船船首点到接触点的距离（米）。</summary>
        public double TargetBowToContactM { get; }

        /// <summary>本船船首对船首阈值 max(10 m, 0.05L)（米）。</summary>
        public double OwnBowToBowThresholdM { get; }

        /// <summary>目标船船首对船首阈值 max(10 m, 0.05L)（米）。</summary>
        public double TargetBowToBowThresholdM { get; }

        /// <summary>首次接触时刻（仿真秒）。</summary>
        public double TcSeconds { get; }

        /// <summary>撞击船标识（船首点距接触点更近者）；船首对船首时为空串。</summary>
        public string StrikingVesselId { get; }

        /// <summary>被撞船标识；船首对船首时为空串。</summary>
        public string StruckVesselId { get; }

        /// <summary>两船船首尾线的锐夹角（度，0–180；按调查惯例取锐角）。</summary>
        public double CollisionAngleDeg { get; }

        /// <summary>接触点 ENU 坐标（两船 OBB 近似接触点）。</summary>
        public EnuPosition ContactPointEnu { get; }

        /// <summary>接触点经纬度；setup 未提供 ENU 原点时为 null。</summary>
        public GeoCoord? ContactPointGeo { get; }

        /// <summary>接触点位于被撞船哪一舷（“左舷”/“右舷”）；船首对船首时为“船首对船首”。</summary>
        public string StruckSide { get; }

        /// <summary>接触点沿被撞船首尾线距船首的距离（米，0=船首，LOA=船尾）；船首对船首时无被撞船，取 0（两船船首距离见 OwnBowToContactM / TargetBowToContactM）。</summary>
        public double ContactFromStruckBowM { get; }

        /// <summary>接触点沿被撞船首尾线距船首的比例（0=船首，1=船尾）。</summary>
        public double ContactFromStruckBowRatio { get; }

        /// <summary>接触时刻两船相对速度（节）。</summary>
        public double RelativeSpeedKn { get; }

        /// <summary>中文描述，例如“VEGA DREAM 船首撞 YANGZE 22 右舷，距船首约 120 m（0.53 L），碰撞角约 70°”。</summary>
        public string Description { get; }

        /// <summary>构造碰撞几何（单一撞击船形态，兼容旧签名）。</summary>
        public CollisionGeometry(
            double tcSeconds,
            string strikingVesselId,
            string struckVesselId,
            double collisionAngleDeg,
            EnuPosition contactPointEnu,
            GeoCoord? contactPointGeo,
            string struckSide,
            double contactFromStruckBowM,
            double contactFromStruckBowRatio,
            double relativeSpeedKn,
            string description)
            : this(
                tcSeconds, ImpactKind.BowStrike, strikingVesselId, struckVesselId, collisionAngleDeg,
                contactPointEnu, contactPointGeo, struckSide, contactFromStruckBowM, contactFromStruckBowRatio,
                relativeSpeedKn, description, strikingVesselId, struckVesselId,
                double.NaN, double.NaN, double.NaN, double.NaN)
        {
        }

        /// <summary>构造碰撞几何（含撞击形态与两船船首距接触点距离）。</summary>
        public CollisionGeometry(
            double tcSeconds,
            ImpactKind kind,
            string strikingVesselId,
            string struckVesselId,
            double collisionAngleDeg,
            EnuPosition contactPointEnu,
            GeoCoord? contactPointGeo,
            string struckSide,
            double contactFromStruckBowM,
            double contactFromStruckBowRatio,
            double relativeSpeedKn,
            string description,
            string ownVesselId,
            string targetVesselId,
            double ownBowToContactM,
            double targetBowToContactM,
            double ownBowToBowThresholdM,
            double targetBowToBowThresholdM)
        {
            Kind = kind;
            OwnVesselId = ownVesselId ?? string.Empty;
            TargetVesselId = targetVesselId ?? string.Empty;
            OwnBowToContactM = ownBowToContactM;
            TargetBowToContactM = targetBowToContactM;
            OwnBowToBowThresholdM = ownBowToBowThresholdM;
            TargetBowToBowThresholdM = targetBowToBowThresholdM;
            TcSeconds = tcSeconds;
            StrikingVesselId = strikingVesselId ?? string.Empty;
            StruckVesselId = struckVesselId ?? string.Empty;
            CollisionAngleDeg = collisionAngleDeg;
            ContactPointEnu = contactPointEnu;
            ContactPointGeo = contactPointGeo;
            StruckSide = struckSide ?? string.Empty;
            ContactFromStruckBowM = contactFromStruckBowM;
            ContactFromStruckBowRatio = contactFromStruckBowRatio;
            RelativeSpeedKn = relativeSpeedKn;
            Description = description ?? string.Empty;
        }

        /// <summary>
        /// 由两船反事实航迹与首次接触时刻计算碰撞几何。调用方应确保 tc 处两船 OBB 已接触。
        /// </summary>
        public static CollisionGeometry Create(
            WhatIfSetup setup,
            CounterfactualTrack own,
            CounterfactualTrack target,
            double tcSeconds)
        {
            if (setup == null)
            {
                throw new ArgumentNullException(nameof(setup));
            }
            if (own == null)
            {
                throw new ArgumentNullException(nameof(own));
            }
            if (target == null)
            {
                throw new ArgumentNullException(nameof(target));
            }

            KinematicState ownState = own.SampleAt(tcSeconds);
            KinematicState targetState = target.SampleAt(tcSeconds);
            OrientedBoundingBox ownBox = ToBox(ownState, own);
            OrientedBoundingBox targetBox = ToBox(targetState, target);
            EnuPosition contact = OrientedBoundingBox.ApproximateContact(ownBox, targetBox);

            EnuPosition ownBow = BowPoint(ownState, own.LoaM);
            EnuPosition targetBow = BowPoint(targetState, target.LoaM);
            double ownBowDistance = ownBow.HorizontalDistanceTo(contact);
            double targetBowDistance = targetBow.HorizontalDistanceTo(contact);
            double ownThreshold = BowToBowThresholdM(own.LoaM);
            double targetThreshold = BowToBowThresholdM(target.LoaM);
            double relativeSpeedKn = ComputeRelativeSpeedKn(ownState, targetState);
            GeoCoord? contactGeo = setup.EnuOrigin.HasValue
                ? (GeoCoord?)GeoMath.EnuToWgs84(contact, setup.EnuOrigin.Value)
                : null;
            double angle = AcuteAngleBetweenLines(ownState.HeadingDeg, targetState.HeadingDeg);

            if (ownBowDistance < ownThreshold && targetBowDistance < targetThreshold)
            {
                // 裁定 7a：两船船首都贴近接触点，判为船首对船首，不指定单一撞击船。
                string bowDescription = string.Format(
                    CultureInfo.InvariantCulture,
                    "{0} 与 {1} {2}（{0} 船首距接触点约 {3:F1} m，{1} 约 {4:F1} m，均小于各自 max(10 m, 0.05L)），碰撞角约 {5:F0}°，不指定单一撞击船",
                    own.DisplayName, target.DisplayName, BowToBowText, ownBowDistance, targetBowDistance, angle);
                return new CollisionGeometry(
                    tcSeconds,
                    ImpactKind.BowToBow,
                    string.Empty,
                    string.Empty,
                    angle,
                    contact,
                    contactGeo,
                    BowToBowText,
                    0.0,
                    0.0,
                    relativeSpeedKn,
                    bowDescription,
                    own.VesselId,
                    target.VesselId,
                    ownBowDistance,
                    targetBowDistance,
                    ownThreshold,
                    targetThreshold);
            }

            // 其余情况：船首离接触点更近的一方为撞击船（不再按排水量兜底；距离严格相等时取本船，仅为确定性）。
            bool ownStrikes = ownBowDistance <= targetBowDistance;

            string strikingId = ownStrikes ? own.VesselId : target.VesselId;
            string struckId = ownStrikes ? target.VesselId : own.VesselId;
            string strikingName = ownStrikes ? own.DisplayName : target.DisplayName;
            string struckName = ownStrikes ? target.DisplayName : own.DisplayName;
            KinematicState struckState = ownStrikes ? targetState : ownState;
            CounterfactualTrack struckTrack = ownStrikes ? target : own;

            double struckRad = struckState.HeadingDeg * Math.PI / 180.0;
            double starboardEast = Math.Cos(struckRad);
            double starboardNorth = -Math.Sin(struckRad);
            double toEast = contact.EastM - struckState.EastM;
            double toNorth = contact.NorthM - struckState.NorthM;
            double sideDot = toEast * starboardEast + toNorth * starboardNorth;
            string side = sideDot >= 0.0 ? "右舷" : "左舷";

            double forwardEast = Math.Sin(struckRad);
            double forwardNorth = Math.Cos(struckRad);
            double projection = toEast * forwardEast + toNorth * forwardNorth;
            double fromBow = struckTrack.LoaM * 0.5 - projection;
            if (fromBow < 0.0) fromBow = 0.0;
            if (fromBow > struckTrack.LoaM) fromBow = struckTrack.LoaM;
            double ratio = struckTrack.LoaM > 1e-9 ? fromBow / struckTrack.LoaM : 0.0;

            string description = string.Format(
                CultureInfo.InvariantCulture,
                "{0} 船首撞 {1} {2}，距船首约 {3:F0} m（{4:F2} L），碰撞角约 {5:F0}°",
                strikingName, struckName, side, fromBow, ratio, angle);

            return new CollisionGeometry(
                tcSeconds,
                ImpactKind.BowStrike,
                strikingId,
                struckId,
                angle,
                contact,
                contactGeo,
                side,
                fromBow,
                ratio,
                relativeSpeedKn,
                description,
                own.VesselId,
                target.VesselId,
                ownBowDistance,
                targetBowDistance,
                ownThreshold,
                targetThreshold);
        }

        /// <summary>船首对船首阈值：max(10 m, 0.05L)。</summary>
        public static double BowToBowThresholdM(double loaM)
        {
            return Math.Max(BowToBowMinThresholdM, BowToBowLoaRatio * loaM);
        }

        private static OrientedBoundingBox ToBox(KinematicState state, CounterfactualTrack track)
        {
            return OrientedBoundingBox.FromVessel(
                new EnuPosition(state.EastM, state.NorthM, 0.0),
                state.HeadingDeg,
                (float)track.LoaM,
                (float)track.BeamM);
        }

        private static EnuPosition BowPoint(KinematicState state, double loaM)
        {
            double rad = state.HeadingDeg * Math.PI / 180.0;
            return new EnuPosition(
                state.EastM + Math.Sin(rad) * loaM * 0.5,
                state.NorthM + Math.Cos(rad) * loaM * 0.5,
                0.0);
        }

        private static double AcuteAngleBetweenLines(double headingA, double headingB)
        {
            double delta = Math.Abs(KinematicState.NormalizeDeg180(headingA - headingB));
            if (delta > 90.0)
            {
                delta = 180.0 - delta;
            }
            return delta;
        }

        private static double ComputeRelativeSpeedKn(KinematicState a, KinematicState b)
        {
            double aRad = a.HeadingDeg * Math.PI / 180.0;
            double bRad = b.HeadingDeg * Math.PI / 180.0;
            double aEast = a.SpeedKn * VesselMotionState.MpsPerKnot * Math.Sin(aRad);
            double aNorth = a.SpeedKn * VesselMotionState.MpsPerKnot * Math.Cos(aRad);
            double bEast = b.SpeedKn * VesselMotionState.MpsPerKnot * Math.Sin(bRad);
            double bNorth = b.SpeedKn * VesselMotionState.MpsPerKnot * Math.Cos(bRad);
            double de = aEast - bEast;
            double dn = aNorth - bNorth;
            return Math.Sqrt(de * de + dn * dn) / VesselMotionState.MpsPerKnot;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return Description;
        }
    }
}
