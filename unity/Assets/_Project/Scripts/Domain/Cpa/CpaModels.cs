using System;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Models
{
    /// <summary>
    /// CPA 风险分级阈值与滞回配置（对应 ARCHITECTURE.md 4.6.3 与 5.2 节）。
    /// 默认单位：DCPA 为海里 (nm)，TCPA 为分钟 (min)，滞回保持时长为秒 (s)。
    /// </summary>
    public readonly struct RiskThresholds : IEquatable<RiskThresholds>
    {
        /// <summary>默认配置（Danger: DCPA&lt;0.3nm 且 0&lt;TCPA&lt;6min；Warning: DCPA&lt;1.0nm 且 0&lt;TCPA&lt;12min；滞回 1s，裕度 10%）。</summary>
        public static readonly RiskThresholds Default = new RiskThresholds(
            "Default", 0.3, 6.0, 1.0, 12.0, 1.0, 0.1);

        /// <summary>预设方案名称。</summary>
        public string PresetName { get; }

        /// <summary>危险级（Danger）DCPA 阈值（海里，默认 0.3 nm）。</summary>
        public double DangerDcpaNm { get; }

        /// <summary>危险级（Danger）TCPA 阈值（分钟，默认 6.0 min）。</summary>
        public double DangerTcpaMin { get; }

        /// <summary>警告级（Warning）DCPA 阈值（海里，默认 1.0 nm）。</summary>
        public double WarningDcpaNm { get; }

        /// <summary>警告级（Warning）TCPA 阈值（分钟，默认 12.0 min）。</summary>
        public double WarningTcpaMin { get; }

        /// <summary>风险降级保持确认时长 N（秒，默认 1.0 s）。</summary>
        public double HysteresisSeconds { get; }

        /// <summary>风险降级相对裕度比例（降级需越过 阈值×(1+裕度)，默认 0.1 即 10%）。</summary>
        public double DowngradeMarginRatio { get; }

        /// <summary>构造 CPA 风险阈值配置。</summary>
        public RiskThresholds(
            string presetName,
            double dangerDcpaNm = 0.3,
            double dangerTcpaMin = 6.0,
            double warningDcpaNm = 1.0,
            double warningTcpaMin = 12.0,
            double hysteresisSeconds = 1.0,
            double downgradeMarginRatio = 0.1)
        {
            PresetName = presetName ?? "Default";
            DangerDcpaNm = dangerDcpaNm > 0.0 ? dangerDcpaNm : 0.3;
            DangerTcpaMin = dangerTcpaMin > 0.0 ? dangerTcpaMin : 6.0;
            WarningDcpaNm = warningDcpaNm > 0.0 ? warningDcpaNm : 1.0;
            WarningTcpaMin = warningTcpaMin > 0.0 ? warningTcpaMin : 12.0;
            HysteresisSeconds = hysteresisSeconds >= 0.0 ? hysteresisSeconds : 0.0;
            DowngradeMarginRatio = downgradeMarginRatio >= 0.0 ? downgradeMarginRatio : 0.0;
        }

        /// <inheritdoc />
        public bool Equals(RiskThresholds other)
        {
            return string.Equals(PresetName, other.PresetName, StringComparison.Ordinal) &&
                   DangerDcpaNm.Equals(other.DangerDcpaNm) &&
                   DangerTcpaMin.Equals(other.DangerTcpaMin) &&
                   WarningDcpaNm.Equals(other.WarningDcpaNm) &&
                   WarningTcpaMin.Equals(other.WarningTcpaMin) &&
                   HysteresisSeconds.Equals(other.HysteresisSeconds) &&
                   DowngradeMarginRatio.Equals(other.DowngradeMarginRatio);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is RiskThresholds other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = PresetName != null ? PresetName.GetHashCode() : 0;
                hash = (hash * 397) ^ DangerDcpaNm.GetHashCode();
                hash = (hash * 397) ^ DangerTcpaMin.GetHashCode();
                hash = (hash * 397) ^ WarningDcpaNm.GetHashCode();
                hash = (hash * 397) ^ WarningTcpaMin.GetHashCode();
                hash = (hash * 397) ^ HysteresisSeconds.GetHashCode();
                hash = (hash * 397) ^ DowngradeMarginRatio.GetHashCode();
                return hash;
            }
        }
    }
}

namespace Mcis.Domain.Cpa
{
    /// <summary>
    /// 轻量级船舶水平运动学状态（供 CPA 委托采样与解算使用，支持海里/节与米/米每秒双单位互转）。
    /// </summary>
    public readonly struct VesselMotionState
    {
        /// <summary>一海里对应的米数（1852.0 m）。</summary>
        public const double MetersPerNm = 1852.0;

        /// <summary>一节对应的米每秒（1852.0 / 3600.0 m/s）。</summary>
        public const double MpsPerKnot = 1852.0 / 3600.0;

        /// <summary>仿真相对时间（秒）。</summary>
        public double TimeSeconds { get; }

        /// <summary>东向坐标（海里）。</summary>
        public double EastNm { get; }

        /// <summary>北向坐标（海里）。</summary>
        public double NorthNm { get; }

        /// <summary>东向速度分量（节）。</summary>
        public double VelocityEastKn { get; }

        /// <summary>北向速度分量（节）。</summary>
        public double VelocityNorthKn { get; }

        /// <summary>对地航速 SOG（节）。</summary>
        public double SpeedKn { get; }

        /// <summary>对地航向 COG（真北顺时针度，0..360°）。</summary>
        public double CourseDeg { get; }

        /// <summary>局部 ENU 位置（米）。</summary>
        public EnuPosition EnuPositionM
        {
            get { return new EnuPosition(EastNm * MetersPerNm, NorthNm * MetersPerNm, 0.0); }
        }

        /// <summary>局部 ENU 速度分量（米/秒）。</summary>
        public Double2 VelocityEnuMps
        {
            get { return new Double2(VelocityEastKn * MpsPerKnot, VelocityNorthKn * MpsPerKnot); }
        }

        /// <summary>按海里位置（EastNm, NorthNm）、航速（节）与真北航向（度）构造运动状态。</summary>
        public VesselMotionState(double eastNm, double northNm, double speedKn, double courseDeg, double timeSeconds = 0.0)
        {
            TimeSeconds = timeSeconds;
            EastNm = eastNm;
            NorthNm = northNm;
            SpeedKn = speedKn;
            CourseDeg = NormalizeAngleDeg(courseDeg);
            double rad = CourseDeg * (Math.PI / 180.0);
            VelocityEastKn = speedKn * Math.Sin(rad);
            VelocityNorthKn = speedKn * Math.Cos(rad);
        }

        private VesselMotionState(
            double timeSeconds, double eastNm, double northNm,
            double veKn, double vnKn, double speedKn, double courseDeg)
        {
            TimeSeconds = timeSeconds;
            EastNm = eastNm;
            NorthNm = northNm;
            VelocityEastKn = veKn;
            VelocityNorthKn = vnKn;
            SpeedKn = speedKn;
            CourseDeg = NormalizeAngleDeg(courseDeg);
        }

        /// <summary>按海里位置与东/北速度分量（节）构造运动状态。</summary>
        public static VesselMotionState FromVelocityKn(double eastNm, double northNm, double veKn, double vnKn, double timeSeconds = 0.0)
        {
            double speed = Math.Sqrt(veKn * veKn + vnKn * vnKn);
            double cog = speed > 1e-12 ? NormalizeAngleDeg(Math.Atan2(veKn, vnKn) * (180.0 / Math.PI)) : 0.0;
            return new VesselMotionState(timeSeconds, eastNm, northNm, veKn, vnKn, speed, cog);
        }

        /// <summary>按 SI 单位（米、米/秒）构造运动状态。</summary>
        public static VesselMotionState FromEnuMeters(EnuPosition enuM, Double2 velocityMps, double timeSeconds = 0.0)
        {
            return FromVelocityKn(
                enuM.EastM / MetersPerNm,
                enuM.NorthM / MetersPerNm,
                velocityMps.X / MpsPerKnot,
                velocityMps.Y / MpsPerKnot,
                timeSeconds);
        }

        /// <summary>从 TrackSample 转换为船舶运动状态。</summary>
        public static VesselMotionState FromTrackSample(TrackSample sample, bool useRawSogCog = false)
        {
            if (useRawSogCog && sample.SogMps >= 0f && !float.IsNaN(sample.CogDeg))
            {
                return new VesselMotionState(
                    sample.EnuCenter.EastM / MetersPerNm,
                    sample.EnuCenter.NorthM / MetersPerNm,
                    sample.SogMps / MpsPerKnot,
                    sample.CogDeg,
                    sample.Time.Seconds);
            }
            return FromEnuMeters(sample.EnuCenter, sample.VelocityEnuMps, sample.Time.Seconds);
        }

        /// <summary>隐式从 TrackSample 转换。</summary>
        public static implicit operator VesselMotionState(TrackSample sample)
        {
            return FromTrackSample(sample, false);
        }

        private static double NormalizeAngleDeg(double deg)
        {
            double m = deg % 360.0;
            return m < 0.0 ? m + 360.0 : m;
        }
    }
}
