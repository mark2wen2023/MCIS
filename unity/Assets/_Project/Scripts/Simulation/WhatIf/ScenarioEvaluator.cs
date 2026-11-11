using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Simulation.Cpa;
using Mcis.Simulation.Damage;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>
    /// What-if 情景评价器：构建反事实航迹，复用 CpaService 计算 DCPA/TCPA 与最小距离，
    /// 复用 CollisionDetector 计算首次接触时刻，并做净距与结论判定。
    /// </summary>
    public static class ScenarioEvaluator
    {
        /// <summary>评价单个情景；scenario 为 null 时按原始航迹评价。</summary>
        public static ScenarioResult Evaluate(WhatIfSetup setup, WhatIfScenario scenario)
        {
            if (setup == null)
            {
                throw new ArgumentNullException(nameof(setup));
            }

            ValidateScenario(setup, scenario);

            Dictionary<string, CounterfactualTrack> tracks =
                new Dictionary<string, CounterfactualTrack>(StringComparer.Ordinal);
            for (int i = 0; i < setup.Vessels.Count; i++)
            {
                WhatIfVessel vessel = setup.Vessels[i];
                VesselScenario vesselScenario = scenario != null ? scenario.FindVessel(vessel.Id) : null;
                tracks[vessel.Id] = CounterfactualBuilder.Build(vessel, vesselScenario, 0.1);
            }

            CounterfactualTrack own = tracks[setup.OwnVesselId];
            CounterfactualTrack target = tracks[setup.TargetVesselId];

            CpaService cpaService = new CpaService(
                t => own.ToMotionState(t),
                t => target.ToMotionState(t),
                setup.StartSeconds,
                setup.EndSeconds,
                setup.CpaStepSeconds,
                setup.Thresholds,
                setup.OwnVesselId,
                setup.TargetVesselId);

            CpaTimeSeries series = cpaService.PrimarySeries;
            if (series == null || series.Samples.Count == 0)
            {
                throw new InvalidOperationException("CPA 预计算未返回有效序列。");
            }

            SimTime? contact = CollisionDetector.FindFirstContactTime(
                t => own.ToBodyState(t),
                t => target.ToBodyState(t),
                new SimTime(setup.StartSeconds),
                new SimTime(setup.EndSeconds),
                setup.CollisionPrecisionSec,
                setup.CollisionCoarseStepSec);

            bool collision = contact.HasValue;
            double minClearanceTime = collision ? contact.Value.Seconds : double.NaN;
            double minClearanceM = collision
                ? 0.0
                : ComputeMinClearance(setup, own, target, out minClearanceTime);
            double? minDcpaAfterDeviationNm = ComputeMinDcpaAfterDeviation(series, tracks);

            ScenarioVerdict verdict;
            if (collision)
            {
                verdict = ScenarioVerdict.Collision;
            }
            else if (minClearanceM < setup.SafeDistanceM)
            {
                verdict = ScenarioVerdict.NearMiss;
            }
            else
            {
                verdict = ScenarioVerdict.Avoided;
            }

            double? tcSeconds = collision ? (double?)contact.Value.Seconds : null;
            string tcLocal = collision
                ? setup.FormatLocalTime(contact.Value.Seconds)
                : "—";
            CollisionGeometry geometry = collision
                ? CollisionGeometry.Create(setup, own, target, contact.Value.Seconds)
                : null;
            IReadOnlyList<SourcedValue> inputs = MergeInputs(setup, scenario);
            List<string> assumptions = WhatIfAssumptions.CreateDefaultList();
            bool hasFictionalInput = false;
            for (int i = 0; i < inputs.Count; i++)
            {
                if (inputs[i] != null && inputs[i].Source == ValueSource.Fictional)
                {
                    hasFictionalInput = true;
                    break;
                }
            }
            if (hasFictionalInput)
            {
                assumptions.Add("本情景输入为虚构示例数据，仅用于方法演示，不代表任何真实事故。");
            }
            for (int i = 0; i < setup.CaseAssumptions.Count; i++)
            {
                if (!string.IsNullOrWhiteSpace(setup.CaseAssumptions[i]))
                {
                    assumptions.Add(setup.CaseAssumptions[i]);
                }
            }

            string id = scenario != null ? scenario.Id : "S0";
            string name = scenario != null ? scenario.Name : "原始";
            string summary = scenario != null ? scenario.ChangeSummary : "原始航迹，无改动";

            return new ScenarioResult(
                id,
                name,
                summary,
                tracks,
                series,
                series.MinDistanceNm,
                series.MinDistanceTime.Seconds,
                series.MinDcpaSample.DcpaNm,
                minClearanceM,
                collision,
                tcSeconds,
                tcLocal,
                verdict,
                ScenarioResult.VerdictToText(verdict),
                new ReadOnlyCollection<string>(assumptions),
                WhatIfAssumptions.DisclaimerText,
                geometry,
                inputs,
                minDcpaAfterDeviationNm,
                minClearanceTime,
                setup.SafeDistanceM);
        }

        /// <summary>按输入顺序评价多个情景。</summary>
        public static IReadOnlyList<ScenarioResult> EvaluateAll(
            WhatIfSetup setup,
            IReadOnlyList<WhatIfScenario> scenarios)
        {
            if (scenarios == null)
            {
                throw new ArgumentNullException(nameof(scenarios));
            }

            List<ScenarioResult> results = new List<ScenarioResult>(scenarios.Count);
            for (int i = 0; i < scenarios.Count; i++)
            {
                results.Add(Evaluate(setup, scenarios[i]));
            }
            return new ReadOnlyCollection<ScenarioResult>(results);
        }

        private static IReadOnlyList<SourcedValue> MergeInputs(WhatIfSetup setup, WhatIfScenario scenario)
        {
            List<SourcedValue> inputs = new List<SourcedValue>();
            for (int i = 0; i < setup.Inputs.Count; i++)
            {
                inputs.Add(setup.Inputs[i]);
            }
            if (scenario != null)
            {
                for (int i = 0; i < scenario.Inputs.Count; i++)
                {
                    inputs.Add(scenario.Inputs[i]);
                }
            }
            return new ReadOnlyCollection<SourcedValue>(inputs);
        }

        private static void ValidateScenario(WhatIfSetup setup, WhatIfScenario scenario)
        {
            if (scenario == null)
            {
                return;
            }

            HashSet<string> seen = new HashSet<string>(StringComparer.Ordinal);
            for (int i = 0; i < scenario.Vessels.Count; i++)
            {
                VesselScenario vesselScenario = scenario.Vessels[i];
                if (vesselScenario == null)
                {
                    throw new ArgumentException("情景中存在空的单船设定。", nameof(scenario));
                }
                if (setup.FindVessel(vesselScenario.VesselId) == null)
                {
                    throw new ArgumentException("情景引用了设定中不存在的船舶：" + vesselScenario.VesselId, nameof(scenario));
                }
                if (!seen.Add(vesselScenario.VesselId))
                {
                    throw new ArgumentException("情景中同一船舶出现多次：" + vesselScenario.VesselId, nameof(scenario));
                }
            }
        }

        /// <summary>全程净距粗扫步长（秒）。</summary>
        public const double ClearanceCoarseStepSec = 0.5;

        /// <summary>局部极小处细化扫描步长（秒）；之后再做黄金分割到 1e-3 s。</summary>
        public const double ClearanceFineStepSec = 0.02;

        private static double ComputeMinClearance(
            WhatIfSetup setup,
            CounterfactualTrack own,
            CounterfactualTrack target,
            out double timeSeconds)
        {
            // W14.2 裁定 7b：全程全局最小 OBB 真实净距——先在 [Start, End] 粗扫，
            // 再在每个局部极小处细化（±1 个粗步长细扫 + 黄金分割），取所有局部极小中的最小值。
            double best = GlobalMinimum(
                setup.StartSeconds,
                setup.EndSeconds,
                t => OrientedBoundingBox.Clearance(ToBox(own.SampleAt(t), own), ToBox(target.SampleAt(t), target)),
                ClearanceCoarseStepSec,
                ClearanceFineStepSec,
                out timeSeconds);
            return best > 0.0 ? best : 0.0;
        }

        /// <summary>
        /// 一维函数在 [from, to] 上的全局最小：粗扫找全部局部极小（含端点），每个极小在 ±coarse 内按 fine 步长细扫，
        /// 再在最优细扫点 ±fine 内黄金分割收敛到 1e-3 s。返回最小值，并输出对应时刻。
        /// </summary>
        internal static double GlobalMinimum(
            double from,
            double to,
            Func<double, double> f,
            double coarse,
            double fine,
            out double argMin)
        {
            if (f == null)
            {
                throw new ArgumentNullException(nameof(f));
            }
            if (!(coarse > 0.0) || !(fine > 0.0))
            {
                throw new ArgumentOutOfRangeException(nameof(coarse), "步长必须为正。");
            }
            if (to < from)
            {
                double tmp = to;
                to = from;
                from = tmp;
            }

            List<double> times = new List<double>();
            List<double> values = new List<double>();
            int n = (int)Math.Floor((to - from) / coarse + 1e-9);
            for (int i = 0; i <= n; i++)
            {
                double t = Math.Min(to, from + i * coarse);
                times.Add(t);
                values.Add(f(t));
            }
            if (times[times.Count - 1] < to - 1e-9)
            {
                times.Add(to);
                values.Add(f(to));
            }

            double bestValue = double.PositiveInfinity;
            double bestTime = from;
            for (int i = 0; i < values.Count; i++)
            {
                double v = values[i];
                // 局部极小（含端点）：不大于左邻、严格小于右邻；平台段只取最后一点，最后一点只比左邻。
                bool leftOk = i == 0 || v <= values[i - 1];
                bool rightOk = i == values.Count - 1 || v < values[i + 1];
                if (!(leftOk && rightOk))
                {
                    continue;
                }

                double lo = Math.Max(from, times[i] - coarse);
                double hi = Math.Min(to, times[i] + coarse);
                double localTime = times[i];
                double localValue = v;
                int steps = (int)Math.Ceiling((hi - lo) / fine - 1e-9);
                for (int k = 0; k <= steps; k++)
                {
                    double t = Math.Min(hi, lo + k * fine);
                    double ft = f(t);
                    if (ft < localValue)
                    {
                        localValue = ft;
                        localTime = t;
                    }
                }

                double ga = Math.Max(from, localTime - fine);
                double gb = Math.Min(to, localTime + fine);
                double gt;
                double gv = GoldenSection(f, ga, gb, 1e-3, out gt);
                if (gv < localValue)
                {
                    localValue = gv;
                    localTime = gt;
                }

                if (localValue < bestValue)
                {
                    bestValue = localValue;
                    bestTime = localTime;
                }
            }

            argMin = bestTime;
            return bestValue;
        }

        private static double GoldenSection(Func<double, double> f, double a, double b, double tol, out double argMin)
        {
            const double InvPhi = 0.6180339887498949;
            double c = b - InvPhi * (b - a);
            double d = a + InvPhi * (b - a);
            double fc = f(c);
            double fd = f(d);
            int guard = 0;
            while (b - a > tol && guard++ < 200)
            {
                if (fc <= fd)
                {
                    b = d;
                    d = c;
                    fd = fc;
                    c = b - InvPhi * (b - a);
                    fc = f(c);
                }
                else
                {
                    a = c;
                    c = d;
                    fc = fd;
                    d = a + InvPhi * (b - a);
                    fd = f(d);
                }
            }
            if (fc <= fd)
            {
                argMin = c;
                return fc;
            }
            argMin = d;
            return fd;
        }

        /// <summary>
        /// 偏离后最小 DCPA：只统计最早偏离时刻（任一船）及之后的 CPA 样本；原始情景（无偏离）返回 null。
        /// </summary>
        internal static double? ComputeMinDcpaAfterDeviation(
            CpaTimeSeries series,
            IReadOnlyDictionary<string, CounterfactualTrack> tracks)
        {
            double divergeTime = double.PositiveInfinity;
            foreach (KeyValuePair<string, CounterfactualTrack> pair in tracks)
            {
                CounterfactualTrack track = pair.Value;
                if (track != null && track.Diverged && !double.IsNaN(track.DivergeTimeSeconds) &&
                    track.DivergeTimeSeconds < divergeTime)
                {
                    divergeTime = track.DivergeTimeSeconds;
                }
            }
            if (double.IsInfinity(divergeTime))
            {
                return null;
            }

            double best = double.PositiveInfinity;
            for (int i = 0; i < series.Samples.Count; i++)
            {
                if (series.Samples[i].Time.Seconds >= divergeTime - 1e-9 &&
                    series.Samples[i].DcpaNm < best)
                {
                    best = series.Samples[i].DcpaNm;
                }
            }
            return double.IsInfinity(best) ? (double?)null : best;
        }

        private static OrientedBoundingBox ToBox(KinematicState state, CounterfactualTrack track)
        {
            return OrientedBoundingBox.FromVessel(
                new EnuPosition(state.EastM, state.NorthM, 0.0),
                state.HeadingDeg,
                (float)track.LoaM,
                (float)track.BeamM);
        }
    }
}
