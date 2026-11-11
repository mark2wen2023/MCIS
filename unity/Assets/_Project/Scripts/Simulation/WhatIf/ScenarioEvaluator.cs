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

        /// <summary>兼容旧调用者保留的 W14.2 粗扫常量（秒）；W14.3 实际净距扫描改用航迹积分步长与全部积分点，不再使用本常量。</summary>
        public const double ClearanceCoarseStepSec = 0.5;

        /// <summary>细化步长的兼容上限（秒）；实际使用 min(本值, dt/10)，再做黄金分割到 1e-3 s。</summary>
        public const double ClearanceFineStepSec = 0.02;

        /// <summary>数值加密触发阈值（度/秒），不是危险判定或航海规则阈值。</summary>
        public const double ClearanceTurnRefinementDegPerSec = 0.5;

        private static double ComputeMinClearance(
            WhatIfSetup setup,
            CounterfactualTrack own,
            CounterfactualTrack target,
            out double timeSeconds)
        {
            double dt = Math.Min(own.StepSeconds, target.StepSeconds);
            List<double> times = ClearanceSamplingTimes(setup.StartSeconds, setup.EndSeconds, own, target);
            double best = MinimumOnGrid(times,
                t => OrientedBoundingBox.Clearance(ToBox(own.SampleAt(t), own), ToBox(target.SampleAt(t), target)),
                Math.Min(ClearanceFineStepSec, dt / 10.0),
                (a, b) => HighTurnInterval(own.SampleAt(a), own.SampleAt(b)) ||
                          HighTurnInterval(target.SampleAt(a), target.SampleAt(b)),
                out timeSeconds);
            return best > 0.0 ? best : 0.0;
        }

        /// <summary>两船所有真实积分节点、dt 网格与首尾的有序并集；容差内重复时间只保留一次。</summary>
        internal static List<double> ClearanceSamplingTimes(double from, double to,
            CounterfactualTrack own, CounterfactualTrack target)
        {
            double dt = Math.Min(own.StepSeconds, target.StepSeconds);
            var points = new SortedSet<double>(UniformTimes(from, to, dt));
            foreach (KinematicState state in own.States)
                if (state.TimeSeconds >= from && state.TimeSeconds <= to) points.Add(state.TimeSeconds);
            foreach (KinematicState state in target.States)
                if (state.TimeSeconds >= from && state.TimeSeconds <= to) points.Add(state.TimeSeconds);
            var times = new List<double>();
            foreach (double t in points)
                if (times.Count == 0 || t - times[times.Count - 1] > 1e-9 || t == to) times.Add(t);
            return times;
        }

        /// <summary>原始轨迹的 ROT 可缺省为零，因此同时检查相邻实际航向的最短角差。</summary>
        internal static bool HighTurnInterval(KinematicState a, KinematicState b)
        {
            double span = b.TimeSeconds - a.TimeSeconds;
            if (!(span > 0.0)) return false;
            double headingRate = Math.Abs(KinematicState.NormalizeDeg180(b.HeadingDeg - a.HeadingDeg)) / span;
            return Math.Abs(a.RotDegPerSec) > ClearanceTurnRefinementDegPerSec ||
                   Math.Abs(b.RotDegPerSec) > ClearanceTurnRefinementDegPerSec ||
                   headingRate > ClearanceTurnRefinementDegPerSec;
        }

        private static List<double> UniformTimes(double from, double to, double step)
        {
            if (double.IsNaN(step) || double.IsInfinity(step) || !(step > 0.0))
                throw new ArgumentOutOfRangeException(nameof(step));
            var times = new List<double>();
            int n = checked((int)Math.Floor((to - from) / step + 1e-9));
            for (int i = 0; i <= n; i++) times.Add(Math.Min(to, from + i * step));
            if (times[times.Count - 1] < to) times.Add(to);
            return times;
        }

        /// <summary>保留原内部入口；使用规则网格搜索全部局部极小。</summary>
        internal static double GlobalMinimum(double from, double to, Func<double, double> f,
            double coarse, double fine, out double argMin)
        {
            if (to < from) { double swap = from; from = to; to = swap; }
            return MinimumOnGrid(UniformTimes(from, to, coarse), f, fine, null, out argMin);
        }

        /// <summary>全网格逐点比较；局部极小及触发区间细扫，再在每个细网格极小附近细化。</summary>
        internal static double MinimumOnGrid(IReadOnlyList<double> times, Func<double, double> f,
            double fine, Func<double, double, bool> refineInterval, out double argMin)
        {
            if (f == null) throw new ArgumentNullException(nameof(f));
            if (times == null || times.Count == 0) throw new ArgumentException("采样时间不能为空。", nameof(times));
            if (double.IsNaN(fine) || double.IsInfinity(fine) || !(fine > 0.0))
                throw new ArgumentOutOfRangeException(nameof(fine));
            var values = new List<double>(times.Count);
            double best = double.PositiveInfinity, bestTime = times[0];
            for (int i = 0; i < times.Count; i++)
            {
                double v = f(times[i]);
                values.Add(v);
                if (v < best) { best = v; bestTime = times[i]; }
            }
            var windows = new List<Tuple<double, double>>();
            for (int i = 0; i < times.Count; i++)
            {
                bool left = i == 0 || values[i] <= values[i - 1];
                bool right = i == times.Count - 1 || values[i] < values[i + 1];
                if (left && right)
                    windows.Add(Tuple.Create(times[Math.Max(0, i - 1)], times[Math.Min(times.Count - 1, i + 1)]));
                if (i > 0 && refineInterval != null && refineInterval(times[i - 1], times[i]))
                    windows.Add(Tuple.Create(times[i - 1], times[i]));
            }
            windows.Sort((a, b) => a.Item1.CompareTo(b.Item1));
            var merged = new List<Tuple<double, double>>();
            foreach (var window in windows)
            {
                if (merged.Count > 0 && window.Item1 <= merged[merged.Count - 1].Item2 + 1e-9)
                {
                    var last = merged[merged.Count - 1];
                    merged[merged.Count - 1] = Tuple.Create(last.Item1, Math.Max(last.Item2, window.Item2));
                }
                else merged.Add(window);
            }
            foreach (var window in merged)
            {
                var fineTimes = UniformTimes(window.Item1, window.Item2, fine);
                var fineValues = new List<double>(fineTimes.Count);
                foreach (double t in fineTimes)
                {
                    double v = f(t);
                    fineValues.Add(v);
                    if (v < best) { best = v; bestTime = t; }
                }
                for (int i = 0; i < fineTimes.Count; i++)
                {
                    bool left = i == 0 || fineValues[i] <= fineValues[i - 1];
                    bool right = i == fineTimes.Count - 1 || fineValues[i] < fineValues[i + 1];
                    if (!(left && right)) continue;
                    double a = fineTimes[Math.Max(0, i - 1)], b = fineTimes[Math.Min(fineTimes.Count - 1, i + 1)];
                    if (b - a <= 1e-9) continue;
                    double t;
                    double v = GoldenSection(f, a, b, 1e-3, out t);
                    if (v < best) { best = v; bestTime = t; }
                }
            }
            argMin = bestTime;
            return best;
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
