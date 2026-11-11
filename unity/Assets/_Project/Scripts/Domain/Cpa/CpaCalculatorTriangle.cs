using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Cpa
{
    public static partial class CpaCalculator
    {
        /// <summary>
        /// 按论文 thesis.txt 3.4 节雷达标绘矢量三角形公式计算 DCPA / TCPA（航海单位：航速为节 kn，航向/方位为度 °，距离为海里 nm）。
        ///
        /// 【严格数学推导（对应 thesis.txt 3.4 节 Figure 6 船舶会遇矢量三角形 ABC 与 ARCHITECTURE.md 4.6.2 节）】
        /// 1. 设真北为 +N 轴（0°），正东为 +E 轴（90°），角度均按真北顺时针度量：
        ///    - 本船航速 Vo（节），真航向 Co（度） ⇒ 本船速度向量 Vo_vec = (Vo·sin(Co), Vo·cos(Co))
        ///    - 目标船航速 Vt（节），真航向 Ct（度） ⇒ 目标船速度向量 Vt_vec = (Vt·sin(Ct), Vt·cos(Ct))
        ///    - 目标船相对本船真方位为 Q（度），距离为 D（海里） ⇒ 初始相对位置 r0 = (D·sin(Q), D·cos(Q))
        ///
        /// 2. 在速度矢量三角形 ABC 中（V_r = V_t - V_o），Vo_vec 与 Vt_vec 夹角为 (Ct - Co)，由余弦定理得相对速度大小 Vr：
        ///    Vr = sqrt(Vo² + Vt² - 2·Vo·Vt·cos(Ct - Co))
        ///
        /// 3. 目标船相对本船的相对速度分量：
        ///    Vr_E = Vt·sin(Ct) - Vo·sin(Co)
        ///    Vr_N = Vt·cos(Ct) - Vo·cos(Co)
        ///    相对航向 Cr ∈ [0°, 360°) 由四象限反正切给出（消除论文反余弦公式在 0°~180° 之外的象限歧义）：
        ///    Cr = atan2(Vr_E, Vr_N) mod 360°
        ///
        /// 4. 从目标船指向本船的反方位（视线方向）为 (Q + 180°)，因此目标船相对运动方向 Cr 与视线方向 (Q + 180°) 的夹角为：
        ///    θ = Cr - Q - 180°
        ///    在以初始距离 D 为斜边的直角三角形中：
        ///    - 本船到相对运动线的垂距即最近会遇距离 DCPA：
        ///      DCPA = D · |sin(Cr - Q - 180°)|  （单位：海里 nm）
        ///    - 沿相对运动线到达最近会遇点的有向行程为 D · cos(Cr - Q - 180°)，除以相对速度 Vr 得最近会遇时间 TCPA：
        ///      TCPA_hours = D · cos(Cr - Q - 180°) / Vr  （单位：小时 h）
        ///      TCPA_min   = 60 · D · cos(Cr - Q - 180°) / Vr  （单位：分钟 min）
        ///
        /// 5. 与向量法等价性证明：
        ///    r0 · v = (D·sin Q)(Vr·sin Cr) + (D·cos Q)(Vr·cos Cr) = D·Vr·cos(Cr - Q) = -D·Vr·cos(Cr - Q - 180°)
        ///    故 TCPA = -(r0 · v) / |v|² = D·cos(Cr - Q - 180°) / Vr；
        ///    |r0 × v| / |v| = D·|sin(Cr - Q)| = D·|sin(Cr - Q - 180°)| = DCPA。两者恒等。
        /// </summary>
        public static CpaResult CalculateByTriangle(
            double voKn,
            double coDeg,
            double vtKn,
            double ctDeg,
            double azimuthQDeg,
            double distanceNm,
            CpaPairKey pair = default,
            SimTime time = default,
            RiskLevel riskLevel = RiskLevel.Safe,
            double degenerateSpeedEpsilonKn = DefaultDegenerateSpeedKn)
        {
            double dNm = Math.Max(0.0, distanceNm);
            double qDeg = NormalizeAngleDeg(azimuthQDeg);
            double coRad = coDeg * (Math.PI / 180.0);
            double ctRad = ctDeg * (Math.PI / 180.0);
            double qRad = qDeg * (Math.PI / 180.0);

            // 余弦定理求相对速度大小 Vr（节）
            double deltaCourseRad = ctRad - coRad;
            double vrSquared = voKn * voKn + vtKn * vtKn - 2.0 * voKn * vtKn * Math.Cos(deltaCourseRad);
            if (vrSquared < 0.0)
            {
                vrSquared = 0.0;
            }
            double vrKn = Math.Sqrt(vrSquared);

            double epsKn = degenerateSpeedEpsilonKn > 0.0 ? degenerateSpeedEpsilonKn : DefaultDegenerateSpeedKn;
            bool isDegenerate = vrKn < epsKn;

            double currentDistanceM = dNm * MetersPerNauticalMile;
            double relSpeedMps = vrKn * MetersPerSecondPerKnot;
            EnuPosition ownPos = EnuPosition.Zero;
            EnuPosition targetPos = new EnuPosition(
                currentDistanceM * Math.Sin(qRad),
                currentDistanceM * Math.Cos(qRad),
                0.0);

            double crDeg;
            double dcpaNm;
            double tcpaMin;
            EnuPosition ownCpaEnu;
            EnuPosition targetCpaEnu;
            bool isDiverging;

            if (isDegenerate)
            {
                crDeg = 0.0;
                dcpaNm = dNm;
                tcpaMin = double.PositiveInfinity;
                ownCpaEnu = ownPos;
                targetCpaEnu = targetPos;
                isDiverging = false;
            }
            else
            {
                double vrEastKn = vtKn * Math.Sin(ctRad) - voKn * Math.Sin(coRad);
                double vrNorthKn = vtKn * Math.Cos(ctRad) - voKn * Math.Cos(coRad);
                crDeg = NormalizeAngleDeg(Math.Atan2(vrEastKn, vrNorthKn) * (180.0 / Math.PI));

                // θ = Cr - Q - 180°
                double thetaRad = (crDeg - qDeg - 180.0) * (Math.PI / 180.0);
                dcpaNm = dNm * Math.Abs(Math.Sin(thetaRad));
                double tcpaHours = (dNm * Math.Cos(thetaRad)) / vrKn;
                tcpaMin = tcpaHours * 60.0;

                double tcpaSecVal = tcpaMin * SecondsPerMinute;
                double voMps = voKn * MetersPerSecondPerKnot;
                double vtMps = vtKn * MetersPerSecondPerKnot;
                ownCpaEnu = new EnuPosition(
                    voMps * Math.Sin(coRad) * tcpaSecVal,
                    voMps * Math.Cos(coRad) * tcpaSecVal,
                    0.0);
                targetCpaEnu = new EnuPosition(
                    targetPos.EastM + vtMps * Math.Sin(ctRad) * tcpaSecVal,
                    targetPos.NorthM + vtMps * Math.Cos(ctRad) * tcpaSecVal,
                    0.0);
                isDiverging = tcpaMin < 0.0;
            }

            double dcpaM = dcpaNm * MetersPerNauticalMile;
            double tcpaSec = double.IsPositiveInfinity(tcpaMin)
                ? double.PositiveInfinity
                : tcpaMin * SecondsPerMinute;

            return new CpaResult(
                pair,
                time,
                currentDistanceM,
                currentDistanceM,
                qDeg,
                crDeg,
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
        /// 根据瞬时 DCPA（海里）与 TCPA（分钟）评估未加滞回的瞬时三级风险等级。
        /// 默认规则：Danger: DCPA &lt; 0.3nm 且 0 &lt; TCPA &lt; 6min；Warning: DCPA &lt; 1.0nm 且 0 &lt; TCPA &lt; 12min；其余 Safe。
        /// </summary>
        public static RiskLevel EvaluateInstantRisk(
            double dcpaNm,
            double tcpaMin,
            bool isDegenerate,
            RiskThresholds thresholds)
        {
            if (isDegenerate || double.IsNaN(dcpaNm) || double.IsNaN(tcpaMin) || tcpaMin <= 0.0)
            {
                return RiskLevel.Safe;
            }

            if (dcpaNm < thresholds.DangerDcpaNm && tcpaMin < thresholds.DangerTcpaMin)
            {
                return RiskLevel.Danger;
            }

            if (dcpaNm < thresholds.WarningDcpaNm && tcpaMin < thresholds.WarningTcpaMin)
            {
                return RiskLevel.Warning;
            }

            return RiskLevel.Safe;
        }

        internal static double NormalizeAngleDeg(double deg)
        {
            double m = deg % 360.0;
            return m < 0.0 ? m + 360.0 : m;
        }
    }
}
