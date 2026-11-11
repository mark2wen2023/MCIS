using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 航迹插值与运动学几何纯数学工具（三次 Hermite 样条、Catmull-Rom 有限差分切线、最短角插值与速度矢量换算）。
    /// </summary>
    public static class HermiteMath
    {
        /// <summary>1 节对应的米/秒（1852 / 3600）。</summary>
        public const double MetersPerSecondPerKnot = 1852.0 / 3600.0;

        /// <summary>1 米/秒对应的节（3600 / 1852）。</summary>
        public const double KnotsPerMeterPerSecond = 3600.0 / 1852.0;

        /// <summary>将角度归一化到 [0, 360) 区间。</summary>
        public static double NormalizeAngleDeg(double angleDeg)
        {
            if (double.IsNaN(angleDeg) || double.IsInfinity(angleDeg))
            {
                return 0.0;
            }
            double mod = angleDeg % 360.0;
            if (mod < 0.0)
            {
                mod += 360.0;
            }
            if (mod >= 360.0)
            {
                mod -= 360.0;
            }
            return mod;
        }

        /// <summary>计算从 fromDeg 到 toDeg 的有符号最短角度差，范围 (-180, 180]。</summary>
        public static double DeltaAngleDeg(double fromDeg, double toDeg)
        {
            double diff = (toDeg - fromDeg) % 360.0;
            if (diff > 180.0)
            {
                diff -= 360.0;
            }
            else if (diff <= -180.0)
            {
                diff += 360.0;
            }
            return diff;
        }

        /// <summary>按最短圆弧在两个角度（度）之间线性插值，结果归一化至 [0, 360)。</summary>
        public static double InterpolateAngleDeg(double a0Deg, double a1Deg, double s)
        {
            double delta = DeltaAngleDeg(a0Deg, a1Deg);
            return NormalizeAngleDeg(a0Deg + delta * s);
        }

        /// <summary>由对地航速（m/s）与真北顺时针航向（度）计算局部 ENU 水平速度向量 (Ve, Vn)。</summary>
        public static Double2 VelocityFromSogCog(double sogMps, double cogDeg)
        {
            if (double.IsNaN(sogMps) || sogMps <= 0.0 || double.IsNaN(cogDeg))
            {
                return Double2.Zero;
            }
            double rad = cogDeg * GeoMath.DegToRad;
            return new Double2(sogMps * Math.Sin(rad), sogMps * Math.Cos(rad));
        }

        /// <summary>从局部 ENU 水平速度向量 (Ve, Vn) 提取真北顺时针航向角（度）；低速退化时返回备用航向。</summary>
        public static double VelocityToCogDeg(Double2 velocityEnuMps, double fallbackCogDeg = 0.0)
        {
            double speedSq = velocityEnuMps.LengthSquared;
            if (speedSq < 1e-6)
            {
                return NormalizeAngleDeg(fallbackCogDeg);
            }
            double rad = Math.Atan2(velocityEnuMps.X, velocityEnuMps.Y);
            return NormalizeAngleDeg(rad * GeoMath.RadToDeg);
        }

        /// <summary>
        /// 计算三次 Hermite 插值在归一化参数 s ∈ [0, 1] 处的二维位置。
        /// p(s) = h00(s)*p0 + h10(s)*dt*v0 + h01(s)*p1 + h11(s)*dt*v1。
        /// </summary>
        public static Double2 EvaluateHermitePosition(
            Double2 p0,
            Double2 v0,
            Double2 p1,
            Double2 v1,
            double dt,
            double s)
        {
            double s2 = s * s;
            double s3 = s2 * s;

            double h00 = 2.0 * s3 - 3.0 * s2 + 1.0;
            double h10 = s3 - 2.0 * s2 + s;
            double h01 = -2.0 * s3 + 3.0 * s2;
            double h11 = s3 - s2;

            double east = h00 * p0.X + h10 * dt * v0.X + h01 * p1.X + h11 * dt * v1.X;
            double north = h00 * p0.Y + h10 * dt * v0.Y + h01 * p1.Y + h11 * dt * v1.Y;
            return new Double2(east, north);
        }

        /// <summary>
        /// 计算三次 Hermite 插值在归一化参数 s ∈ [0, 1] 处的对地速度向量 dp/dt (m/s)。
        /// </summary>
        public static Double2 EvaluateHermiteVelocity(
            Double2 p0,
            Double2 v0,
            Double2 p1,
            Double2 v1,
            double dt,
            double s)
        {
            if (dt <= 1e-9)
            {
                return v0;
            }
            double s2 = s * s;

            double dh00 = (6.0 * s2 - 6.0 * s) / dt;
            double dh10 = 3.0 * s2 - 4.0 * s + 1.0;
            double dh01 = (-6.0 * s2 + 6.0 * s) / dt;
            double dh11 = 3.0 * s2 - 2.0 * s;

            double ve = dh00 * p0.X + dh10 * v0.X + dh01 * p1.X + dh11 * v1.X;
            double vn = dh00 * p0.Y + dh10 * v0.Y + dh01 * p1.Y + dh11 * v1.Y;
            return new Double2(ve, vn);
        }

        /// <summary>
        /// 当节点缺失有效 SOG/COG 时，使用 Catmull-Rom 中心有限差分（端点处使用单侧差分）估算节点速度向量。
        /// </summary>
        public static Double2 ComputeFiniteDifferenceTangent(IReadOnlyList<TrackSample> samples, int index)
        {
            if (samples == null || samples.Count < 2)
            {
                return Double2.Zero;
            }

            if (index <= 0)
            {
                double dt0 = samples[1].Time - samples[0].Time;
                if (dt0 <= 1e-9)
                {
                    return Double2.Zero;
                }
                return (samples[1].EnuCenter.Horizontal - samples[0].EnuCenter.Horizontal) / dt0;
            }

            if (index >= samples.Count - 1)
            {
                int last = samples.Count - 1;
                double dtLast = samples[last].Time - samples[last - 1].Time;
                if (dtLast <= 1e-9)
                {
                    return Double2.Zero;
                }
                return (samples[last].EnuCenter.Horizontal - samples[last - 1].EnuCenter.Horizontal) / dtLast;
            }

            double dtPrev = samples[index].Time - samples[index - 1].Time;
            double dtNext = samples[index + 1].Time - samples[index].Time;
            double dtTotal = dtPrev + dtNext;
            if (dtTotal <= 1e-9)
            {
                return Double2.Zero;
            }

            return (samples[index + 1].EnuCenter.Horizontal - samples[index - 1].EnuCenter.Horizontal) / dtTotal;
        }
    }
}
