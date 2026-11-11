using System;
using System.Collections.Generic;
using Mcis.Core;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 锚点来源：自动提取或人工确认。
    /// </summary>
    public enum AnchorOrigin
    {
        /// <summary>由导入器从数据中自动提取。</summary>
        Automatic = 0,
        /// <summary>由调查员人工确认。</summary>
        Manual = 1
    }

    /// <summary>
    /// 人工锚点：调查员确认两个数据源中的两个时间戳对应同一真实事件。
    /// </summary>
    public sealed class ManualAnchor
    {
        /// <summary>人工事件键（不含自动前缀）。</summary>
        public string EventKey { get; }

        /// <summary>数据源 A 标识。</summary>
        public string SourceA { get; }

        /// <summary>数据源 A 设备时钟下的时间。</summary>
        public SimTime TimeA { get; }

        /// <summary>数据源 B 标识。</summary>
        public string SourceB { get; }

        /// <summary>数据源 B 设备时钟下的时间。</summary>
        public SimTime TimeB { get; }

        /// <summary>调查说明，可为 null。</summary>
        public string Note { get; }

        /// <summary>调查员，可为 null。</summary>
        public string Investigator { get; }

        /// <summary>
        /// 构造人工锚点。
        /// </summary>
        /// <param name="eventKey">人工事件键。</param>
        /// <param name="sourceA">数据源 A 标识。</param>
        /// <param name="timeA">数据源 A 时间。</param>
        /// <param name="sourceB">数据源 B 标识。</param>
        /// <param name="timeB">数据源 B 时间。</param>
        /// <param name="note">调查说明，可为 null。</param>
        /// <param name="investigator">调查员，可为 null。</param>
        /// <exception cref="ArgumentException">事件键或数据源为空，或两个数据源相同时抛出。</exception>
        public ManualAnchor(
            string eventKey,
            string sourceA,
            SimTime timeA,
            string sourceB,
            SimTime timeB,
            string note = null,
            string investigator = null)
        {
            if (string.IsNullOrWhiteSpace(eventKey))
            {
                throw new ArgumentException("人工锚点事件键不能为空。", nameof(eventKey));
            }

            if (string.IsNullOrWhiteSpace(sourceA))
            {
                throw new ArgumentException("人工锚点数据源 A 不能为空。", nameof(sourceA));
            }

            if (string.IsNullOrWhiteSpace(sourceB))
            {
                throw new ArgumentException("人工锚点数据源 B 不能为空。", nameof(sourceB));
            }

            if (string.Equals(sourceA, sourceB, StringComparison.Ordinal))
            {
                throw new ArgumentException("人工锚点的两个数据源不能相同。", nameof(sourceB));
            }

            EventKey = eventKey;
            SourceA = sourceA;
            TimeA = timeA;
            SourceB = sourceB;
            TimeB = timeB;
            Note = note;
            Investigator = investigator;
        }

        /// <summary>
        /// 由 UTC 绝对时间创建人工锚点。
        /// </summary>
        /// <param name="eventKey">人工事件键。</param>
        /// <param name="sourceA">数据源 A 标识。</param>
        /// <param name="utcA">数据源 A 对应的 UTC 时间。</param>
        /// <param name="sourceB">数据源 B 标识。</param>
        /// <param name="utcB">数据源 B 对应的 UTC 时间。</param>
        /// <param name="caseEpochUtc">案件纪元（UTC）。</param>
        /// <param name="note">调查说明，可为 null。</param>
        /// <param name="investigator">调查员，可为 null。</param>
        /// <returns>人工锚点。</returns>
        public static ManualAnchor FromUtc(
            string eventKey,
            string sourceA,
            DateTimeOffset utcA,
            string sourceB,
            DateTimeOffset utcB,
            DateTimeOffset caseEpochUtc,
            string note = null,
            string investigator = null)
        {
            return new ManualAnchor(
                eventKey,
                sourceA,
                SimTime.FromUtc(utcA, caseEpochUtc),
                sourceB,
                SimTime.FromUtc(utcB, caseEpochUtc),
                note,
                investigator);
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "MANUAL:{0} {1}@{2:F3}s ↔ {3}@{4:F3}s",
                EventKey,
                SourceA,
                TimeA.Seconds,
                SourceB,
                TimeB.Seconds);
        }
    }

    /// <summary>
    /// 人工锚点与自动锚点的转换、合并辅助。
    /// </summary>
    public static class ManualAnchors
    {
        /// <summary>
        /// 把每个人工锚点转换为两条 Origin=Manual 的锚点观测。
        /// 事件键统一加 "MANUAL:" 前缀，避免与自动锚点键冲突。
        /// </summary>
        /// <param name="anchors">人工锚点集合，可为 null。</param>
        /// <returns>锚点观测列表（每个人工锚点两项，保持输入顺序）。</returns>
        public static IReadOnlyList<AnchorObservation> ToObservations(IEnumerable<ManualAnchor> anchors)
        {
            List<AnchorObservation> observations = new List<AnchorObservation>();
            if (anchors == null)
            {
                return observations;
            }

            foreach (ManualAnchor anchor in anchors)
            {
                if (anchor == null)
                {
                    continue;
                }

                string eventKey = "MANUAL:" + anchor.EventKey;
                observations.Add(new AnchorObservation(
                    eventKey,
                    anchor.SourceA,
                    anchor.TimeA,
                    AnchorOrigin.Manual,
                    anchor.Note));
                observations.Add(new AnchorObservation(
                    eventKey,
                    anchor.SourceB,
                    anchor.TimeB,
                    AnchorOrigin.Manual,
                    anchor.Note));
            }

            return observations;
        }

        /// <summary>
        /// 合并自动锚点与人工锚点转换出的观测，自动锚点在前。
        /// </summary>
        /// <param name="automatic">自动锚点观测，可为 null。</param>
        /// <param name="manual">人工锚点集合，可为 null。</param>
        /// <returns>合并后的锚点观测列表。</returns>
        public static IReadOnlyList<AnchorObservation> Merge(
            IEnumerable<AnchorObservation> automatic,
            IEnumerable<ManualAnchor> manual)
        {
            List<AnchorObservation> merged = new List<AnchorObservation>();
            if (automatic != null)
            {
                foreach (AnchorObservation observation in automatic)
                {
                    if (observation != null)
                    {
                        merged.Add(observation);
                    }
                }
            }

            merged.AddRange(ToObservations(manual));
            return merged;
        }
    }
}
