using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Cpa
{
    /// <summary>
    /// DCPA / TCPA 核心解算器（对应 ARCHITECTURE.md 4.6 节与论文 thesis.txt 3.4 节）。
    /// 提供平面向量法与雷达标绘矢量三角形公式法两种严格等价的实现。
    /// </summary>
    public static partial class CpaCalculator
    {
        /// <summary>标准海里米数（1 nm = 1852 m）。</summary>
        public const double MetersPerNauticalMile = 1852.0;

        /// <summary>每分钟秒数（60 s）。</summary>
        public const double SecondsPerMinute = 60.0;

        /// <summary>每小时秒数（3600 s）。</summary>
        public const double SecondsPerHour = 3600.0;

        /// <summary>节转米每秒系数（1 kn = 1852 / 3600 m/s）。</summary>
        public const double MetersPerSecondPerKnot = MetersPerNauticalMile / SecondsPerHour;

        /// <summary>相对静止退化判定默认阈值（0.01 m/s，对应 ARCHITECTURE.md 4.6.1 节）。</summary>
        public const double DefaultDegenerateSpeedMps = 0.01;

        /// <summary>相对静止退化判定默认阈值（节，约 0.01943844 kn）。</summary>
        public const double DefaultDegenerateSpeedKn = DefaultDegenerateSpeedMps / MetersPerSecondPerKnot;

        /// <summary>
        /// 向量法计算 DCPA / TCPA（SI 单位输入：位置为 ENU 米，速度为东/北 m/s）。
        /// 公式：
        /// r = P_t - P_o
        /// v = V_t - V_o
        /// TCPA = -(r · v) / |v|²
        /// DCPA = |r + v · TCPA|
        /// 当 |v| &lt; ε 时判为退化（相对静止），DCPA = |r|，TCPA = +∞，IsDegenerate = true。
        /// </summary>
        public static CpaResult CalculateByVector(
            EnuPosition ownPosition,
            Double2 ownVelocityMps,
            EnuPosition targetPosition,
            Double2 targetVelocityMps,
            CpaPairKey pair = default,
            SimTime time = default,
            RiskLevel riskLevel = RiskLevel.Safe,
            double hullClearanceM = double.NaN,
            double degenerateSpeedEpsilonMps = DefaultDegenerateSpeedMps)
        {
            double rx = targetPosition.EastM - ownPosition.EastM;
            double ry = targetPosition.NorthM - ownPosition.NorthM;
            double currentDistanceM = Math.Sqrt(rx * rx + ry * ry);

            double vx = targetVelocityMps.X - ownVelocityMps.X;
            double vy = targetVelocityMps.Y - ownVelocityMps.Y;
            double vSq = vx * vx + vy * vy;
            double relSpeedMps = Math.Sqrt(vSq);

            double trueBearingDeg = currentDistanceM > 1e-12
                ? NormalizeAngleDeg(Math.Atan2(rx, ry) * (180.0 / Math.PI))
                : 0.0;

            double eps = degenerateSpeedEpsilonMps > 0.0 ? degenerateSpeedEpsilonMps : DefaultDegenerateSpeedMps;
            bool isDegenerate = relSpeedMps < eps;

            double relCourseDeg;
            double tcpaSec;
            double dcpaM;
            EnuPosition ownCpaEnu;
            EnuPosition targetCpaEnu;
            bool isDiverging;

            if (isDegenerate)
            {
                relCourseDeg = 0.0;
                tcpaSec = double.PositiveInfinity;
                dcpaM = currentDistanceM;
                ownCpaEnu = ownPosition;
                targetCpaEnu = targetPosition;
                isDiverging = false;
            }
            else
            {
                relCourseDeg = NormalizeAngleDeg(Math.Atan2(vx, vy) * (180.0 / Math.PI));
                double rDotV = rx * vx + ry * vy;
                tcpaSec = -rDotV / vSq;

                double cpaRx = rx + vx * tcpaSec;
                double cpaRy = ry + vy * tcpaSec;
                dcpaM = Math.Sqrt(cpaRx * cpaRx + cpaRy * cpaRy);

                ownCpaEnu = new EnuPosition(
                    ownPosition.EastM + ownVelocityMps.X * tcpaSec,
                    ownPosition.NorthM + ownVelocityMps.Y * tcpaSec,
                    ownPosition.UpM);
                targetCpaEnu = new EnuPosition(
                    targetPosition.EastM + targetVelocityMps.X * tcpaSec,
                    targetPosition.NorthM + targetVelocityMps.Y * tcpaSec,
                    targetPosition.UpM);
                isDiverging = tcpaSec < 0.0;
            }

            double clearance = double.IsNaN(hullClearanceM) ? currentDistanceM : hullClearanceM;

            return new CpaResult(
                pair,
                time,
                currentDistanceM,
                clearance,
                trueBearingDeg,
                relCourseDeg,
                relSpeedMps,
                dcpaM,
                tcpaSec,
                ownCpaEnu,
                targetCpaEnu,
                isDiverging,
                isDegenerate,
                riskLevel);
        }

        /// <summary>
        /// 向量法计算 DCPA / TCPA（航海单位输入：位置为海里 nm，速度为节 kn）。
        /// 返回的 CpaResult 可直接读取 DcpaNm（海里）、TcpaMin（分钟）、CurrentDistanceNm（海里）以及对应 SI 属性。
        /// </summary>
        public static CpaResult CalculateByVector(
            Double2 ownPositionNm,
            Double2 ownVelocityKn,
            Double2 targetPositionNm,
            Double2 targetVelocityKn,
            CpaPairKey pair = default,
            SimTime time = default,
            RiskLevel riskLevel = RiskLevel.Safe,
            double degenerateSpeedEpsilonKn = DefaultDegenerateSpeedKn)
        {
            EnuPosition ownEnu = new EnuPosition(
                ownPositionNm.X * MetersPerNauticalMile,
                ownPositionNm.Y * MetersPerNauticalMile,
                0.0);
            EnuPosition targetEnu = new EnuPosition(
                targetPositionNm.X * MetersPerNauticalMile,
                targetPositionNm.Y * MetersPerNauticalMile,
                0.0);
            Double2 ownVelMps = new Double2(
                ownVelocityKn.X * MetersPerSecondPerKnot,
                ownVelocityKn.Y * MetersPerSecondPerKnot);
            Double2 targetVelMps = new Double2(
                targetVelocityKn.X * MetersPerSecondPerKnot,
                targetVelocityKn.Y * MetersPerSecondPerKnot);

            double epsMps = (degenerateSpeedEpsilonKn > 0.0 ? degenerateSpeedEpsilonKn : DefaultDegenerateSpeedKn)
                            * MetersPerSecondPerKnot;

            return CalculateByVector(
                ownEnu, ownVelMps, targetEnu, targetVelMps,
                pair, time, riskLevel, double.NaN, epsMps);
        }

        /// <summary>
        /// 从两船状态（VesselMotionState）按向量法计算 DCPA / TCPA。
        /// </summary>
        public static CpaResult CalculateFromStates(
            VesselMotionState ownState,
            VesselMotionState targetState,
            CpaPairKey pair = default,
            SimTime? timeOverride = null,
            RiskLevel riskLevel = RiskLevel.Safe,
            double degenerateSpeedEpsilonMps = DefaultDegenerateSpeedMps)
        {
            SimTime t = timeOverride ?? new SimTime(ownState.TimeSeconds);
            return CalculateByVector(
                ownState.EnuPositionM,
                ownState.VelocityEnuMps,
                targetState.EnuPositionM,
                targetState.VelocityEnuMps,
                pair,
                t,
                riskLevel,
                double.NaN,
                degenerateSpeedEpsilonMps);
        }

        /// <summary>
        /// 从两船航迹样本（TrackSample）按向量法计算 DCPA / TCPA。
        /// </summary>
        public static CpaResult CalculateFromSamples(
            TrackSample ownSample,
            TrackSample targetSample,
            CpaPairKey pair = default,
            bool useRawSogCog = false,
            RiskLevel riskLevel = RiskLevel.Safe,
            double degenerateSpeedEpsilonMps = DefaultDegenerateSpeedMps)
        {
            VesselMotionState ownState = VesselMotionState.FromTrackSample(ownSample, useRawSogCog);
            VesselMotionState targetState = VesselMotionState.FromTrackSample(targetSample, useRawSogCog);
            return CalculateFromStates(ownState, targetState, pair, ownSample.Time, riskLevel, degenerateSpeedEpsilonMps);
        }
    }
}
