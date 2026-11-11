using System;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Damage
{
    /// <summary>
    /// 简化破口进水与横倾下沉模型。孔口流量 Q = Cd · A · √(2 g h)，
    /// 进水增加质量并按分舱横向偏移产生横倾，按排水量/水线面近似下沉。
    /// </summary>
    public static class FloodingModel
    {
        public const double GravityMps2 = 9.81;
        public const double DefaultDischargeCoeff = 0.60;
        public const double SeawaterDensityKgPerM3 = 1025.0;
        public const double DefaultWaterplaneCoeff = 0.80;

        /// <summary>单步孔口体积流量（m³/s）。h 为破口中心水头（水线以下深度 + 已下沉，米）。</summary>
        public static double OrificeFlowM3PerSec(double cd, double areaM2, double headM)
        {
            if (areaM2 <= 0.0 || headM <= 0.0)
            {
                return 0.0;
            }

            if (cd <= 0.0)
            {
                cd = DefaultDischargeCoeff;
            }

            return cd * areaM2 * Math.Sqrt(2.0 * GravityMps2 * headM);
        }

        /// <summary>
        /// 以固定时间步积分进水质量、横倾与下沉。
        /// 水线面面积近似为 Cwp · L · B；横倾 φ ≈ atan( (m_flood · y_comp) / (Δ · GM) )，GM 取型宽的 0.12 倍作为示意初稳心。
        /// </summary>
        public static void IntegrateStep(
            VesselParticulars vessel,
            CollisionEvent collision,
            double dtSec,
            ref double floodedMassKg,
            ref double sinkHeaveM,
            ref double rollDeg,
            double cd = DefaultDischargeCoeff)
        {
            if (vessel == null || collision == null || dtSec <= 0.0)
            {
                return;
            }

            double area = Math.Max(collision.EstimatedBreachAreaM2, 0.0);
            double head = Math.Max(collision.BreachDepthBelowWlM + sinkHeaveM, 0.0);
            double q = OrificeFlowM3PerSec(cd, area, head);
            floodedMassKg += q * SeawaterDensityKgPerM3 * dtSec;

            double loa = Math.Max(vessel.LoaM, 1.0);
            double beam = Math.Max(vessel.BeamM, 1.0);
            double awp = DefaultWaterplaneCoeff * loa * beam;
            sinkHeaveM = floodedMassKg / (SeawaterDensityKgPerM3 * Math.Max(awp, 1.0));

            double yLever = EstimateLateralLever(vessel);
            double displacementKg = Math.Max(vessel.DisplacementTons, 1.0) * 1000.0;
            double gm = 0.12 * beam;
            double righting = displacementKg * gm;
            if (righting > 1.0)
            {
                double phiRad = Math.Atan((floodedMassKg * yLever) / righting);
                const double maxPhi = 50.0 * Math.PI / 180.0;
                if (phiRad > maxPhi) phiRad = maxPhi;
                if (phiRad < -maxPhi) phiRad = -maxPhi;
                rollDeg = (float)(phiRad * 180.0 / Math.PI);
            }
        }

        private static double EstimateLateralLever(VesselParticulars vessel)
        {
            if (vessel.Compartments != null && vessel.Compartments.Count > 0)
            {
                // CenterLocalM.X 约定为右舷为正（与天线偏移一致）
                double sum = 0.0;
                int n = 0;
                for (int i = 0; i < vessel.Compartments.Count; i++)
                {
                    sum += vessel.Compartments[i].CenterLocalM.X;
                    n++;
                }

                if (n > 0 && Math.Abs(sum / n) > 0.1)
                {
                    return sum / n;
                }
            }

            return 0.25 * vessel.BeamM;
        }
    }
}
