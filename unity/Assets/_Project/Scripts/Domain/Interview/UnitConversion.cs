using System;
using System.Collections.Generic;

namespace Mcis.Domain.Interview
{
    /// <summary>
    /// 比对用单位换算（确定性）。支持的量纲与单位（别名不区分大小写）：
    /// 长度 m / nm（海里，1 nm = 1852 m；注意本系统中 nm 指海里而非纳米）/ km；
    /// 速度 m/s / kn（节，1 kn = 1852/3600 m/s）/ km/h；
    /// 角度 rad / deg（°）；时间 s / min / h。
    /// 不在表中的单位视为未知，比对判“无法核实”。
    /// </summary>
    public static class UnitConversion
    {
        private sealed class UnitDef
        {
            public string Canonical;
            public string Dimension;
            public double ToBase;
        }

        private static readonly Dictionary<string, UnitDef> Units = Build();

        private static Dictionary<string, UnitDef> Build()
        {
            var d = new Dictionary<string, UnitDef>(StringComparer.OrdinalIgnoreCase);
            void Add(string canonical, string dim, double toBase, params string[] aliases)
            {
                var u = new UnitDef { Canonical = canonical, Dimension = dim, ToBase = toBase };
                d[canonical] = u;
                foreach (string a in aliases)
                {
                    d[a] = u;
                }
            }

            Add("m", "length", 1.0, "meter", "meters", "metre", "metres", "米");
            Add("nm", "length", 1852.0, "nmi", "nautical mile", "nautical miles", "海里", "浬");
            Add("km", "length", 1000.0, "千米", "公里");
            Add("m/s", "speed", 1.0, "mps", "米/秒", "m·s⁻¹", "m⋅s⁻¹", "m s⁻¹", "m.s-1", "m s-1", "m·s-1", "ms-1"); // W3-D10：SI 记法
            Add("kn", "speed", 1852.0 / 3600.0, "kt", "kts", "knot", "knots", "节");
            Add("km/h", "speed", 1.0 / 3.6, "kph", "kmh", "公里/小时");
            Add("rad", "angle", 1.0, "radian", "radians", "弧度");
            Add("deg", "angle", Math.PI / 180.0, "°", "degree", "degrees", "度");
            Add("s", "time", 1.0, "sec", "second", "seconds", "秒");
            Add("min", "time", 60.0, "minute", "minutes", "分钟", "分");
            Add("h", "time", 3600.0, "hr", "hour", "hours", "小时");
            return d;
        }

        public static bool IsKnown(string unit)
        {
            return unit != null && Units.ContainsKey(unit.Trim());
        }

        /// <summary>规范单位名（如 "kt" → "kn"）；未知返回 null。</summary>
        public static string Canonical(string unit)
        {
            return unit != null && Units.TryGetValue(unit.Trim(), out UnitDef u) ? u.Canonical : null;
        }

        /// <summary>两单位是否同一量纲且都已知。</summary>
        public static bool AreCompatible(string a, string b)
        {
            return a != null && b != null &&
                   Units.TryGetValue(a.Trim(), out UnitDef ua) && Units.TryGetValue(b.Trim(), out UnitDef ub) &&
                   ua.Dimension == ub.Dimension;
        }

        /// <summary>把 value 从 fromUnit 换算到 toUnit；任一未知或量纲不同返回 false。</summary>
        public static bool TryConvert(double value, string fromUnit, string toUnit, out double result)
        {
            result = double.NaN;
            if (double.IsNaN(value) || double.IsInfinity(value))
            {
                return false; // W3-D08：NaN/±∞ 不参与换算
            }

            if (fromUnit == null || toUnit == null ||
                !Units.TryGetValue(fromUnit.Trim(), out UnitDef f) || !Units.TryGetValue(toUnit.Trim(), out UnitDef t) ||
                f.Dimension != t.Dimension)
            {
                return false;
            }

            result = ReferenceEquals(f, t) ? value : value * f.ToBase / t.ToBase;
            return true;
        }
    }
}
