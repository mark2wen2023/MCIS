using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>敏感性扫描的单个参数点结果。</summary>
    public sealed class SensitivityPoint
    {
        /// <summary>扫描参数值。</summary>
        public double ParameterValue { get; }

        /// <summary>该参数值下的最小船中心距离（海里）。</summary>
        public double MinDistanceNm { get; }

        /// <summary>该参数值下的 OBB 最小净距（米）。</summary>
        public double MinClearanceM { get; }

        /// <summary>该参数值下是否碰撞。</summary>
        public bool Collision { get; }

        /// <summary>该参数值下的首次接触时刻（仿真秒）；未碰撞为 null。</summary>
        public double? TcSeconds { get; }

        /// <summary>构造敏感性扫描点。</summary>
        public SensitivityPoint(
            double parameterValue,
            double minDistanceNm,
            double minClearanceM,
            bool collision,
            double? tcSeconds)
        {
            ParameterValue = parameterValue;
            MinDistanceNm = minDistanceNm;
            MinClearanceM = minClearanceM;
            Collision = collision;
            TcSeconds = tcSeconds;
        }
    }

    /// <summary>敏感性扫描结果，含碰撞临界值与安全净距临界值。</summary>
    public sealed class SensitivityResult
    {
        private readonly ReadOnlyCollection<SensitivityPoint> _points;
        private readonly ReadOnlyCollection<string> _assumptions;

        /// <summary>扫描参数名称（中文）。</summary>
        public string ParameterName { get; }

        /// <summary>参数单位。</summary>
        public string Unit { get; }

        /// <summary>扫描点列表（按参数升序）。</summary>
        public IReadOnlyList<SensitivityPoint> Points
        {
            get { return _points; }
        }

        /// <summary>碰撞→不碰撞的临界参数值；无转换为 null。</summary>
        public double? CriticalValueCollision { get; }

        /// <summary>最小净距首次达到安全线的临界参数值；无转换为 null。</summary>
        public double? CriticalValueSafe { get; }

        /// <summary>中文结论描述。</summary>
        public string Description { get; }

        /// <summary>中文模型假设列表。</summary>
        public IReadOnlyList<string> Assumptions
        {
            get { return _assumptions; }
        }

        /// <summary>固定免责声明。</summary>
        public string Disclaimer { get; }

        /// <summary>构造敏感性扫描结果。</summary>
        public SensitivityResult(
            string parameterName,
            string unit,
            IReadOnlyList<SensitivityPoint> points,
            double? criticalValueCollision,
            double? criticalValueSafe,
            string description,
            IReadOnlyList<string> assumptions,
            string disclaimer)
        {
            ParameterName = parameterName ?? string.Empty;
            Unit = unit ?? string.Empty;
            _points = new ReadOnlyCollection<SensitivityPoint>(
                points != null ? new List<SensitivityPoint>(points) : new List<SensitivityPoint>());
            CriticalValueCollision = criticalValueCollision;
            CriticalValueSafe = criticalValueSafe;
            Description = description ?? string.Empty;
            _assumptions = new ReadOnlyCollection<string>(
                assumptions != null ? new List<string>(assumptions) : WhatIfAssumptions.CreateDefaultList());
            Disclaimer = string.IsNullOrEmpty(disclaimer) ? WhatIfAssumptions.DisclaimerText : disclaimer;
        }
    }

    /// <summary>参数敏感性扫描：固定步长扫描并用二分细化临界参数值。</summary>
    public static class SensitivitySweep
    {
        /// <summary>
        /// 运行敏感性扫描。factory 把参数值映射为 What-if 情景；
        /// 临界值由扫描点括住区间后二分细化到 tolerance 以内。
        /// </summary>
        public static SensitivityResult Run(
            WhatIfSetup setup,
            string parameterName,
            string unit,
            Func<double, WhatIfScenario> factory,
            double from,
            double to,
            double step,
            double tolerance = 0.5)
        {
            if (setup == null)
            {
                throw new ArgumentNullException(nameof(setup));
            }
            if (factory == null)
            {
                throw new ArgumentNullException(nameof(factory));
            }
            if (double.IsNaN(from) || double.IsInfinity(from) ||
                double.IsNaN(to) || double.IsInfinity(to) || to < from)
            {
                throw new ArgumentException("扫描范围必须为有限值且 to 不小于 from。", nameof(to));
            }
            if (double.IsNaN(step) || double.IsInfinity(step) || step <= 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(step), "扫描步长必须为有限正数。");
            }
            if (double.IsNaN(tolerance) || double.IsInfinity(tolerance) || tolerance <= 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(tolerance), "二分容差必须为有限正数。");
            }

            List<double> values = BuildValues(from, to, step);
            List<SensitivityPoint> points = new List<SensitivityPoint>(values.Count);
            for (int i = 0; i < values.Count; i++)
            {
                WhatIfScenario scenario = factory(values[i]);
                ScenarioResult result = ScenarioEvaluator.Evaluate(setup, scenario);
                points.Add(new SensitivityPoint(
                    values[i],
                    result.MinDistanceNm,
                    result.MinClearanceM,
                    result.Collision,
                    result.TcSeconds));
            }

            double safeDistanceM = setup.SafeDistanceM;
            double? criticalCollision = FindCollisionCritical(
                setup, factory, values, points, tolerance);
            double? criticalSafe = FindSafeCritical(
                setup, factory, values, points, safeDistanceM, tolerance);

            string description = BuildDescription(
                parameterName, unit, points, criticalCollision, criticalSafe, setup.SafeDistanceNm);

            return new SensitivityResult(
                parameterName,
                unit,
                points,
                criticalCollision,
                criticalSafe,
                description,
                new ReadOnlyCollection<string>(WhatIfAssumptions.CreateDefaultList()),
                WhatIfAssumptions.DisclaimerText);
        }

        /// <summary>
        /// 扫描“转向提前量”（秒）：基线转向时刻前移该秒数，其余参数不变。
        /// </summary>
        public static SensitivityResult SweepTurnAdvance(
            WhatIfSetup setup,
            string vesselId,
            double baselineTurnTimeSeconds,
            double rudderDeg,
            double headingChangeDeg,
            double fromSec,
            double toSec,
            double stepSec)
        {
            if (setup == null)
            {
                throw new ArgumentNullException(nameof(setup));
            }
            if (setup.FindVessel(vesselId) == null)
            {
                throw new ArgumentException("未找到用于转向扫描的船舶：" + vesselId, nameof(vesselId));
            }

            Func<double, WhatIfScenario> factory = advance =>
            {
                double turnTime = baselineTurnTimeSeconds - advance;
                Intervention intervention = Intervention.TurnStarboard(
                    turnTime, rudderDeg, headingChangeDeg, 0.0, "提前转向");
                VesselScenario vesselScenario = VesselScenario.Create(vesselId, intervention);
                string id = "SENS-" + advance.ToString("0.###", CultureInfo.InvariantCulture);
                return new WhatIfScenario(
                    id,
                    "转向提前量扫描",
                    "提前 " + advance.ToString("0.##", CultureInfo.InvariantCulture) + " s 转向",
                    new[] { vesselScenario });
            };

            return Run(setup, "转向提前量", "s", factory, fromSec, toSec, stepSec);
        }

        private static List<double> BuildValues(double from, double to, double step)
        {
            List<double> values = new List<double>();
            double span = to - from;
            int count = (int)Math.Floor(span / step + 1e-9);
            for (int i = 0; i <= count; i++)
            {
                double value = from + i * step;
                values.Add(value);
            }
            if (values.Count == 0 || values[values.Count - 1] < to - 1e-9)
            {
                values.Add(to);
            }
            else if (Math.Abs(values[values.Count - 1] - to) <= 1e-9)
            {
                values[values.Count - 1] = to;
            }
            return values;
        }

        private static double? FindCollisionCritical(
            WhatIfSetup setup,
            Func<double, WhatIfScenario> factory,
            IReadOnlyList<double> values,
            IReadOnlyList<SensitivityPoint> points,
            double tolerance)
        {
            for (int i = 1; i < points.Count; i++)
            {
                if (points[i - 1].Collision && !points[i].Collision)
                {
                    return Bisect(
                        setup, factory,
                        values[i - 1], values[i],
                        r => !r.Collision,
                        tolerance);
                }
            }
            return null;
        }

        private static double? FindSafeCritical(
            WhatIfSetup setup,
            Func<double, WhatIfScenario> factory,
            IReadOnlyList<double> values,
            IReadOnlyList<SensitivityPoint> points,
            double safeDistanceM,
            double tolerance)
        {
            Func<SensitivityPoint, bool> isSafe = p =>
                !p.Collision && p.MinClearanceM >= safeDistanceM;

            for (int i = 1; i < points.Count; i++)
            {
                if (!isSafe(points[i - 1]) && isSafe(points[i]))
                {
                    return Bisect(
                        setup, factory,
                        values[i - 1], values[i],
                        r => !r.Collision && r.MinClearanceM >= safeDistanceM,
                        tolerance);
                }
            }
            return null;
        }

        private static double Bisect(
            WhatIfSetup setup,
            Func<double, WhatIfScenario> factory,
            double lo,
            double hi,
            Func<ScenarioResult, bool> predicate,
            double tolerance)
        {
            double width = tolerance > 1e-9 ? tolerance : 1e-9;
            // 不变式：predicate(lo)=false，predicate(hi)=true
            for (int i = 0; i < 128 && hi - lo > width; i++)
            {
                double mid = 0.5 * (lo + hi);
                ScenarioResult result = ScenarioEvaluator.Evaluate(setup, factory(mid));
                if (predicate(result))
                {
                    hi = mid;
                }
                else
                {
                    lo = mid;
                }
            }
            return hi;
        }

        private static string BuildDescription(
            string parameterName,
            string unit,
            IReadOnlyList<SensitivityPoint> points,
            double? criticalCollision,
            double? criticalSafe,
            double safeDistanceNm)
        {
            string name = string.IsNullOrEmpty(parameterName) ? "参数" : parameterName;
            string suffix = string.IsNullOrEmpty(unit) ? string.Empty : " " + unit;
            List<string> parts = new List<string>();

            if (criticalCollision.HasValue)
            {
                parts.Add(name + " ≥ " + FormatValue(criticalCollision.Value) + suffix + " 可避免碰撞");
            }
            else
            {
                bool allCollision = true;
                bool anyCollision = false;
                for (int i = 0; i < points.Count; i++)
                {
                    if (points[i].Collision) anyCollision = true;
                    else allCollision = false;
                }
                if (points.Count > 0 && allCollision)
                {
                    parts.Add("扫描范围内均为碰撞，未出现碰撞→不碰撞的临界值");
                }
                else if (!anyCollision)
                {
                    parts.Add("扫描范围内均未发生碰撞，未出现碰撞→不碰撞的临界值");
                }
                else
                {
                    parts.Add("扫描范围内未找到单调的碰撞→不碰撞转换");
                }
            }

            if (criticalSafe.HasValue)
            {
                parts.Add(name + " ≥ " + FormatValue(criticalSafe.Value) + suffix +
                          " 时最小净距达到 " + safeDistanceNm.ToString("0.##", CultureInfo.InvariantCulture) + " nm 安全线");
            }
            else
            {
                bool allSafe = points.Count > 0;
                for (int i = 0; i < points.Count; i++)
                {
                    if (points[i].Collision || points[i].MinClearanceM < safeDistanceNm * 1852.0)
                    {
                        allSafe = false;
                        break;
                    }
                }
                if (allSafe)
                {
                    parts.Add("扫描范围内均满足 " + safeDistanceNm.ToString("0.##", CultureInfo.InvariantCulture) + " nm 安全线");
                }
                else
                {
                    parts.Add("扫描范围内未出现最小净距达到 " + safeDistanceNm.ToString("0.##", CultureInfo.InvariantCulture) + " nm 安全线的转换");
                }
            }

            return string.Join("；", parts) + "。";
        }

        private static string FormatValue(double value)
        {
            return value.ToString("0.##", CultureInfo.InvariantCulture);
        }
    }
}
