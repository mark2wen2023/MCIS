using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using Mcis.Simulation.Cpa;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>
    /// 单个 What-if 情景的评价结果。
    /// </summary>
    public sealed class ScenarioResult
    {
        private readonly ReadOnlyDictionary<string, CounterfactualTrack> _tracks;
        private readonly ReadOnlyCollection<string> _assumptions;
        private readonly ReadOnlyCollection<SourcedValue> _inputs;

        /// <summary>情景标识（如 S0）。</summary>
        public string ScenarioId { get; }

        /// <summary>情景名称。</summary>
        public string Name { get; }

        /// <summary>改动摘要（中文）。</summary>
        public string ChangeSummary { get; }

        /// <summary>各船反事实航迹字典（键为船舶标识）。</summary>
        public IReadOnlyDictionary<string, CounterfactualTrack> Tracks
        {
            get { return _tracks; }
        }

        /// <summary>本船/目标船的 CPA 预计算时间序列。</summary>
        public CpaTimeSeries Cpa { get; }

        /// <summary>全时段最小船中心距离（海里）。</summary>
        public double MinDistanceNm { get; }

        /// <summary>最小船中心距离对应时刻（仿真秒）。</summary>
        public double MinDistanceTimeSeconds { get; }

        /// <summary>全时段最小预测 DCPA（海里）。</summary>
        public double MinDcpaNm { get; }

        /// <summary>
        /// 偏离后最小预测 DCPA（海里）：只统计最早偏离时刻及之后的样本；原始情景（无偏离）为 null。
        /// 全时段 <see cref="MinDcpaNm"/> 在干预前各情景相同，比较干预效果应看本项。
        /// </summary>
        public double? MinDcpaAfterDeviationNm { get; }

        /// <summary>全程全局最小 OBB 真实净距（米，两矩形欧氏最小距离；粗扫 + 局部极小细化）；碰撞为 0。</summary>
        public double MinClearanceM { get; }

        /// <summary>最小净距对应时刻（仿真秒）；碰撞时为首次接触时刻；未提供时为 NaN。</summary>
        public double MinClearanceTimeSeconds { get; }

        /// <summary>评价时使用的安全线（米，= setup.SafeDistanceNm × 1852）；未提供时为 NaN。</summary>
        public double SafeDistanceM { get; }

        /// <summary>是否发生碰撞。</summary>
        public bool Collision { get; }

        /// <summary>首次接触时刻（仿真秒）；未碰撞为 null。</summary>
        public double? TcSeconds { get; }

        /// <summary>首次接触的当地时刻文字（HH:mm:ss.ff）；未碰撞为“—”。</summary>
        public string TcLocalText { get; }

        /// <summary>结论枚举。</summary>
        public ScenarioVerdict Verdict { get; }

        /// <summary>结论文字（碰撞/险情/无碰撞）。</summary>
        public string VerdictText { get; }

        /// <summary>首次接触碰撞几何；未碰撞为 null。</summary>
        public CollisionGeometry Geometry { get; }

        /// <summary>情景输入参数及来源。</summary>
        public IReadOnlyList<SourcedValue> Inputs
        {
            get { return _inputs; }
        }

        /// <summary>中文模型假设列表。</summary>
        public IReadOnlyList<string> Assumptions
        {
            get { return _assumptions; }
        }

        /// <summary>固定免责声明。</summary>
        public string Disclaimer { get; }

        /// <summary>构造情景评价结果。</summary>
        public ScenarioResult(
            string scenarioId,
            string name,
            string changeSummary,
            IReadOnlyDictionary<string, CounterfactualTrack> tracks,
            CpaTimeSeries cpa,
            double minDistanceNm,
            double minDistanceTimeSeconds,
            double minDcpaNm,
            double minClearanceM,
            bool collision,
            double? tcSeconds,
            string tcLocalText,
            ScenarioVerdict verdict,
            string verdictText,
            IReadOnlyList<string> assumptions,
            string disclaimer,
            CollisionGeometry geometry = null,
            IReadOnlyList<SourcedValue> inputs = null,
            double? minDcpaAfterDeviationNm = null,
            double minClearanceTimeSeconds = double.NaN,
            double safeDistanceM = double.NaN)
        {
            MinDcpaAfterDeviationNm = minDcpaAfterDeviationNm;
            MinClearanceTimeSeconds = minClearanceTimeSeconds;
            SafeDistanceM = safeDistanceM;
            ScenarioId = scenarioId ?? string.Empty;
            Name = name ?? string.Empty;
            ChangeSummary = changeSummary ?? string.Empty;
            _tracks = new ReadOnlyDictionary<string, CounterfactualTrack>(
                tracks != null
                    ? new Dictionary<string, CounterfactualTrack>(tracks, StringComparer.Ordinal)
                    : new Dictionary<string, CounterfactualTrack>(StringComparer.Ordinal));
            Cpa = cpa;
            MinDistanceNm = minDistanceNm;
            MinDistanceTimeSeconds = minDistanceTimeSeconds;
            MinDcpaNm = minDcpaNm;
            MinClearanceM = minClearanceM;
            Collision = collision;
            TcSeconds = tcSeconds;
            TcLocalText = tcLocalText ?? "—";
            Verdict = verdict;
            VerdictText = verdictText ?? VerdictToText(verdict);
            _assumptions = new ReadOnlyCollection<string>(
                assumptions != null ? new List<string>(assumptions) : WhatIfAssumptions.CreateDefaultList());
            Disclaimer = string.IsNullOrEmpty(disclaimer) ? WhatIfAssumptions.DisclaimerText : disclaimer;
            Geometry = geometry;
            _inputs = new ReadOnlyCollection<SourcedValue>(
                inputs != null ? new List<SourcedValue>(inputs) : new List<SourcedValue>());
        }

        /// <summary>把结论枚举转换为中文文字。</summary>
        public static string VerdictToText(ScenarioVerdict verdict)
        {
            switch (verdict)
            {
                case ScenarioVerdict.Collision:
                    return "碰撞";
                case ScenarioVerdict.NearMiss:
                    return "险情";
                default:
                    return "无碰撞";
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0} {1}：MinDist={2:F3}nm MinClear={3:F1}m MinDCPA={4:F3}nm {5}",
                ScenarioId, Name, MinDistanceNm, MinClearanceM, MinDcpaNm, VerdictText);
        }
    }
}
