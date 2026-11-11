using System;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 角度数学辅助方法：归一到 [0,360) 以及最短弧差值。
    /// </summary>
    public static class AngleMath
    {
        /// <summary>
        /// 将任意角度归一化到 [0,360) 区间。
        /// </summary>
        /// <param name="degrees">输入角度（度）。</param>
        /// <returns>[0,360) 区间内的等价角度；输入 NaN 时返回 NaN。</returns>
        public static double Normalize360(double degrees)
        {
            if (double.IsNaN(degrees) || double.IsInfinity(degrees))
            {
                return degrees;
            }

            double value = degrees % 360.0;
            if (value < 0.0)
            {
                value += 360.0;
            }

            if (value >= 360.0)
            {
                value = 0.0;
            }

            return value;
        }

        /// <summary>
        /// 计算从 from 到 to 的最短弧有符号差值，结果位于 (-180,180]。
        /// 正值表示顺时针（角度增大）方向。
        /// </summary>
        /// <param name="from">起始角度（度）。</param>
        /// <param name="to">目标角度（度）。</param>
        /// <returns>最短弧差值（度）。</returns>
        public static double ShortestDiff(double from, double to)
        {
            if (double.IsNaN(from) || double.IsNaN(to) ||
                double.IsInfinity(from) || double.IsInfinity(to))
            {
                return double.NaN;
            }

            double diff = Normalize360(to) - Normalize360(from);
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

        /// <summary>
        /// 计算两个角度的最短弧绝对差，结果位于 [0,180]。
        /// </summary>
        /// <param name="a">角度 A（度）。</param>
        /// <param name="b">角度 B（度）。</param>
        /// <returns>最短弧绝对差（度）。</returns>
        public static double AbsoluteDiff(double a, double b)
        {
            double diff = ShortestDiff(a, b);
            return double.IsNaN(diff) ? double.NaN : Math.Abs(diff);
        }
    }
}
