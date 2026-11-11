using System;
using Mcis.Domain.Common;

namespace Mcis.Simulation.Damage
{
    /// <summary>等效碰撞动能、损伤分级与破口面积估算（示意级，对应 ARCHITECTURE 4.8 节）。</summary>
    public readonly struct DamageAssessment
    {
        public double EnergyJ { get; }
        public double EnergyMJ { get { return EnergyJ / 1e6; } }
        public double RelativeNormalSpeedMps { get; }
        public DamageSeverity Severity { get; }
        public double BreachAreaM2 { get; }
        public double BreachDepthBelowWlM { get; }
        public double EquivalentMassKg { get; }

        public DamageAssessment(
            double energyJ,
            double relativeNormalSpeedMps,
            DamageSeverity severity,
            double breachAreaM2,
            double breachDepthBelowWlM,
            double equivalentMassKg)
        {
            EnergyJ = energyJ;
            RelativeNormalSpeedMps = relativeNormalSpeedMps;
            Severity = severity;
            BreachAreaM2 = breachAreaM2;
            BreachDepthBelowWlM = breachDepthBelowWlM;
            EquivalentMassKg = equivalentMassKg;
        }
    }

    public static class DamageModel
    {
        public const double DefaultLateralAddedMassCoeff = 0.45;
        public const double DefaultLongitudinalAddedMassCoeff = 0.05;
        public const double TonsToKg = 1000.0;

        /// <summary>
        /// E = ½ · m_eq · v_n²，m_eq = (m_a' · m_b') / (m_a' + m_b')，m' = m(1 + C_added)。
        /// 固定结构视作无限质量（m_eq = m_a'）。
        /// </summary>
        public static DamageAssessment Assess(
            CollisionBodyState a,
            CollisionBodyState b,
            double lateralAddedMassCoeff = DefaultLateralAddedMassCoeff,
            double longitudinalAddedMassCoeff = DefaultLongitudinalAddedMassCoeff)
        {
            EnuPosition contact = OrientedBoundingBox.ApproximateContact(a.Obb, b.Obb);
            Double2 n = ContactNormal(a, b, contact);
            Double2 vRel = a.VelocityEnuMps - b.VelocityEnuMps;
            double vn = Double2.Dot(vRel, n);
            // 取趋近法向速度（若在分离则取绝对值用于定级说明）
            double vnClosing = vn < 0.0 ? -vn : vn;

            double ma = AddedMassKg(a, n, lateralAddedMassCoeff, longitudinalAddedMassCoeff);
            double mb = b.IsFixed ? double.PositiveInfinity : AddedMassKg(b, n, lateralAddedMassCoeff, longitudinalAddedMassCoeff);
            double meq;
            if (double.IsInfinity(mb) || mb <= 0.0)
            {
                meq = ma;
            }
            else if (ma <= 0.0)
            {
                meq = mb;
            }
            else
            {
                meq = (ma * mb) / (ma + mb);
            }

            double energyJ = 0.5 * meq * vnClosing * vnClosing;
            DamageSeverity severity = Classify(energyJ, vnClosing);
            double area = EstimateBreachArea(energyJ, severity);
            double depth = EstimateBreachDepth(severity);
            return new DamageAssessment(energyJ, vnClosing, severity, area, depth, meq);
        }

        public static DamageSeverity Classify(double energyJ, double vnMps)
        {
            double mj = energyJ / 1e6;
            if (vnMps < 0.3 && mj < 5.0)
            {
                return DamageSeverity.None;
            }

            if (vnMps < 1.0 || mj < 20.0)
            {
                return DamageSeverity.Glancing;
            }

            if (vnMps < 2.5 || mj < 80.0)
            {
                return DamageSeverity.Minor;
            }

            if (vnMps < 4.5 || mj < 200.0)
            {
                return DamageSeverity.HullBreach;
            }

            return DamageSeverity.SevereFlooding;
        }

        public static double EstimateBreachArea(double energyJ, DamageSeverity severity)
        {
            switch (severity)
            {
                case DamageSeverity.None:
                    return 0.0;
                case DamageSeverity.Glancing:
                    return 0.0;
                case DamageSeverity.Minor:
                    return 0.4;
                case DamageSeverity.HullBreach:
                    return Math.Max(1.5, Math.Min(8.0, (energyJ / 1e6) * 0.02));
                case DamageSeverity.SevereFlooding:
                    return Math.Max(4.0, Math.Min(25.0, (energyJ / 1e6) * 0.02));
                default:
                    return 0.0;
            }
        }

        public static double EstimateBreachDepth(DamageSeverity severity)
        {
            switch (severity)
            {
                case DamageSeverity.HullBreach:
                    return 1.2;
                case DamageSeverity.SevereFlooding:
                    return 2.5;
                default:
                    return 0.0;
            }
        }

        internal static double AddedMassKg(
            CollisionBodyState body,
            Double2 contactNormalEnu,
            double cLat,
            double cLon)
        {
            double mass = Math.Max(body.DisplacementTons, 0.0) * TonsToKg;
            double rad = body.HeadingDeg * Math.PI / 180.0;
            Double2 forward = new Double2(Math.Sin(rad), Math.Cos(rad));
            double along = Math.Abs(Double2.Dot(Normalize(contactNormalEnu), forward));
            // along≈1 表示法向接近首尾向（纵向附加质量），along≈0 表示横向碰撞
            double c = cLon * along + cLat * (1.0 - along);
            return mass * (1.0 + c);
        }

        private static Double2 ContactNormal(CollisionBodyState a, CollisionBodyState b, EnuPosition contact)
        {
            Double2 ca = new Double2(a.Center.EastM, a.Center.NorthM);
            Double2 cb = new Double2(b.Center.EastM, b.Center.NorthM);
            Double2 n = cb - ca;
            if (n.LengthSquared < 1e-8)
            {
                n = new Double2(1.0, 0.0);
            }

            return Normalize(n);
        }

        private static Double2 Normalize(Double2 v)
        {
            double len = v.Length;
            return len < 1e-12 ? new Double2(1.0, 0.0) : v / len;
        }
    }
}
