using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 锚点观测：同一事件（EventKey）在不同数据源设备时钟下的时间戳。
    /// </summary>
    public sealed class AnchorObservation
    {
        /// <summary>事件共用键（同一事件在各源之间相同）。</summary>
        public string EventKey { get; }

        /// <summary>数据源标识。</summary>
        public string SourceId { get; }

        /// <summary>该源设备时钟下的时间（仿真相对时间）。</summary>
        public SimTime Timestamp { get; }

        /// <summary>锚点来源，默认为自动提取。</summary>
        public AnchorOrigin Origin { get; }

        /// <summary>人工说明，可为 null。</summary>
        public string Note { get; }

        /// <summary>
        /// 构造自动锚点观测。
        /// </summary>
        /// <param name="eventKey">事件共用键。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="timestamp">该源设备时钟下的时间。</param>
        public AnchorObservation(string eventKey, string sourceId, SimTime timestamp)
            : this(eventKey, sourceId, timestamp, AnchorOrigin.Automatic, null)
        {
        }

        /// <summary>
        /// 构造带说明的自动锚点观测。
        /// </summary>
        /// <param name="eventKey">事件共用键。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="timestamp">该源设备时钟下的时间。</param>
        /// <param name="note">人工说明，可为 null。</param>
        public AnchorObservation(string eventKey, string sourceId, SimTime timestamp, string note)
            : this(eventKey, sourceId, timestamp, AnchorOrigin.Automatic, note)
        {
        }

        /// <summary>
        /// 构造锚点观测。
        /// </summary>
        /// <param name="eventKey">事件共用键。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="timestamp">该源设备时钟下的时间。</param>
        /// <param name="origin">锚点来源。</param>
        /// <param name="note">人工说明，可为 null。</param>
        public AnchorObservation(
            string eventKey,
            string sourceId,
            SimTime timestamp,
            AnchorOrigin origin,
            string note = null)
        {
            EventKey = eventKey;
            SourceId = sourceId;
            Timestamp = timestamp;
            Origin = origin;
            Note = note;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0}@{1:F3}s [{2}]",
                EventKey,
                Timestamp.Seconds,
                SourceId);
        }
    }

    /// <summary>
    /// 钟差估计方法。
    /// </summary>
    public enum OffsetMethod
    {
        /// <summary>最小二乘（均值），不确定度为样本标准差除以 sqrt(n)。</summary>
        LeastSquares = 0,
        /// <summary>中位数，抗离群；不确定度为 1.4826*MAD/sqrt(n)。</summary>
        Median = 1
    }

    /// <summary>钟差估计的离群判定与不确定度选项（裁定 2）。</summary>
    public sealed class ClockOffsetOptions
    {
        /// <summary>离群门限的 MAD 倍数：|r| &gt; 倍数 × 1.4826 × MAD 记为离群，默认 3。</summary>
        public double OutlierMadMultiplier { get; set; } = 3.0;

        /// <summary>离群门限的绝对下限（秒），避免 MAD=0 时把微小抖动判为离群，默认 1.0 s。</summary>
        public double OutlierAbsoluteFloorSeconds { get; set; } = 1.0;

        /// <summary>不确定度下限（秒，时间戳分辨率），默认 0.001 s；仅 1 个锚点时仍为 NaN。</summary>
        public double MinUncertaintySeconds { get; set; } = 0.001;

        /// <summary>默认选项：每次返回新实例，避免共享可变状态。</summary>
        public static ClockOffsetOptions Default
        {
            get { return new ClockOffsetOptions(); }
        }
    }

    /// <summary>
    /// 被标记为离群的锚点（裁定 2：不物理删除输入；最小二乘拟合时剔除，中位数方法只标记）。
    /// </summary>
    public sealed class RejectedAnchor
    {
        /// <summary>锚点事件键。</summary>
        public string EventKey { get; }

        /// <summary>该锚点的时间差 d = t_源 − t_对方（秒）。</summary>
        public double DifferenceSeconds { get; }

        /// <summary>相对中位数的残差（秒）。</summary>
        public double ResidualSeconds { get; }

        /// <summary>是否已从拟合中剔除（最小二乘为 true，中位数为 false）。</summary>
        public bool ExcludedFromFit { get; }

        /// <summary>中文原因说明。</summary>
        public string Reason { get; }

        /// <summary>构造离群锚点记录。</summary>
        /// <param name="eventKey">事件键。</param>
        /// <param name="differenceSeconds">时间差。</param>
        /// <param name="residualSeconds">残差。</param>
        /// <param name="excludedFromFit">是否剔除出拟合。</param>
        /// <param name="reason">原因说明。</param>
        public RejectedAnchor(string eventKey, double differenceSeconds, double residualSeconds, bool excludedFromFit, string reason)
        {
            EventKey = eventKey;
            DifferenceSeconds = differenceSeconds;
            ResidualSeconds = residualSeconds;
            ExcludedFromFit = excludedFromFit;
            Reason = reason;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return EventKey + ": " + Reason;
        }
    }

    /// <summary>
    /// 单个数据源相对于基准源的钟差估计。
    /// 偏移定义：源时间 − 基准时间；校准后时间 = 源时间 − Offset。
    /// </summary>
    public sealed class ClockOffsetEstimate
    {
        /// <summary>参与拟合的锚点数（最小二乘为剔除离群后的数量；中位数为全部）。</summary>
        public int UsedAnchorCount { get; }

        /// <summary>被标记为离群的锚点及原因。</summary>
        public IReadOnlyList<RejectedAnchor> RejectedAnchors { get; }

        /// <summary>被估计的数据源标识。</summary>
        public string SourceId { get; }

        /// <summary>基准数据源标识。</summary>
        public string ReferenceSourceId { get; }

        /// <summary>钟差（秒）：源时间 − 基准时间。</summary>
        public double OffsetSeconds { get; }

        /// <summary>不确定度（秒）；样本不足时为 NaN。</summary>
        public double UncertaintySeconds { get; }

        /// <summary>参与估计的共有锚点数量。</summary>
        public int AnchorCount { get; }

        /// <summary>其中的人工锚点数量。</summary>
        public int ManualAnchorCount { get; }

        /// <summary>估计方法。</summary>
        public OffsetMethod Method { get; }

        /// <summary>是否为基准源（基准源偏移恒为 0）。</summary>
        public bool IsReference { get; }

        /// <summary>各锚点残差（观测差 − 估计偏移），顺序与参与估计的锚点一致。</summary>
        public IReadOnlyList<double> Residuals { get; }

        /// <summary>间接校准时的中间源标识；直接校准或基准源为 null。</summary>
        public string ViaSourceId { get; }

        /// <summary>校准状态。</summary>
        public CalibrationStatus Status { get; }

        /// <summary>
        /// 构造钟差估计（兼容旧接口，状态由 IsReference 与有限偏移推导）。
        /// </summary>
        /// <param name="sourceId">被估计的数据源标识。</param>
        /// <param name="referenceSourceId">基准数据源标识。</param>
        /// <param name="offsetSeconds">钟差（秒）。</param>
        /// <param name="uncertaintySeconds">不确定度（秒）。</param>
        /// <param name="anchorCount">锚点数量。</param>
        /// <param name="method">估计方法。</param>
        /// <param name="isReference">是否为基准源。</param>
        /// <param name="residuals">残差列表，可为 null。</param>
        public ClockOffsetEstimate(
            string sourceId,
            string referenceSourceId,
            double offsetSeconds,
            double uncertaintySeconds,
            int anchorCount,
            OffsetMethod method,
            bool isReference,
            IReadOnlyList<double> residuals = null)
            : this(
                sourceId,
                referenceSourceId,
                offsetSeconds,
                uncertaintySeconds,
                anchorCount,
                0,
                method,
                isReference,
                residuals,
                null,
                DeriveStatus(isReference, offsetSeconds))
        {
        }

        /// <summary>
        /// 构造钟差估计（含人工锚点、间接来源与显式状态）。
        /// </summary>
        /// <param name="sourceId">被估计的数据源标识。</param>
        /// <param name="referenceSourceId">基准数据源标识。</param>
        /// <param name="offsetSeconds">钟差（秒）。</param>
        /// <param name="uncertaintySeconds">不确定度（秒）。</param>
        /// <param name="anchorCount">锚点数量。</param>
        /// <param name="manualAnchorCount">人工锚点数量。</param>
        /// <param name="method">估计方法。</param>
        /// <param name="isReference">是否为基准源。</param>
        /// <param name="residuals">残差列表，可为 null。</param>
        /// <param name="viaSourceId">间接中间源，可为 null。</param>
        /// <param name="status">校准状态。</param>
        public ClockOffsetEstimate(
            string sourceId,
            string referenceSourceId,
            double offsetSeconds,
            double uncertaintySeconds,
            int anchorCount,
            int manualAnchorCount,
            OffsetMethod method,
            bool isReference,
            IReadOnlyList<double> residuals,
            string viaSourceId,
            CalibrationStatus status)
            : this(
                sourceId,
                referenceSourceId,
                offsetSeconds,
                uncertaintySeconds,
                anchorCount,
                manualAnchorCount,
                method,
                isReference,
                residuals,
                viaSourceId,
                status,
                anchorCount,
                null)
        {
        }

        /// <summary>
        /// 构造钟差估计（含离群锚点信息，裁定 2）。
        /// </summary>
        /// <param name="sourceId">被估计的数据源标识。</param>
        /// <param name="referenceSourceId">基准数据源标识。</param>
        /// <param name="offsetSeconds">钟差（秒）。</param>
        /// <param name="uncertaintySeconds">不确定度（秒）。</param>
        /// <param name="anchorCount">全部共同锚点数量。</param>
        /// <param name="manualAnchorCount">人工锚点数量。</param>
        /// <param name="method">估计方法。</param>
        /// <param name="isReference">是否为基准源。</param>
        /// <param name="residuals">残差列表，可为 null。</param>
        /// <param name="viaSourceId">间接中间源，可为 null。</param>
        /// <param name="status">校准状态。</param>
        /// <param name="usedAnchorCount">参与拟合的锚点数量。</param>
        /// <param name="rejectedAnchors">离群锚点，可为 null。</param>
        public ClockOffsetEstimate(
            string sourceId,
            string referenceSourceId,
            double offsetSeconds,
            double uncertaintySeconds,
            int anchorCount,
            int manualAnchorCount,
            OffsetMethod method,
            bool isReference,
            IReadOnlyList<double> residuals,
            string viaSourceId,
            CalibrationStatus status,
            int usedAnchorCount,
            IReadOnlyList<RejectedAnchor> rejectedAnchors)
        {
            UsedAnchorCount = usedAnchorCount;
            RejectedAnchors = rejectedAnchors ?? new RejectedAnchor[0];
            SourceId = sourceId;
            ReferenceSourceId = referenceSourceId;
            OffsetSeconds = offsetSeconds;
            UncertaintySeconds = uncertaintySeconds;
            AnchorCount = anchorCount;
            ManualAnchorCount = manualAnchorCount;
            Method = method;
            IsReference = isReference;
            Residuals = residuals ?? new double[0];
            ViaSourceId = viaSourceId;
            Status = status;
        }

        private static CalibrationStatus DeriveStatus(bool isReference, double offsetSeconds)
        {
            if (isReference)
            {
                return CalibrationStatus.Reference;
            }

            return IsFinite(offsetSeconds)
                ? CalibrationStatus.Calibrated
                : CalibrationStatus.Uncalibrated;
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0}->{1} offset={2:F3}s uncertainty={3:F3}s n={4} {5}{6}{7}",
                SourceId,
                ReferenceSourceId,
                OffsetSeconds,
                UncertaintySeconds,
                AnchorCount,
                Method,
                IsReference ? " (reference)" : string.Empty,
                ViaSourceId == null ? string.Empty : " via " + ViaSourceId);
        }
    }

    /// <summary>
    /// 基于共键锚点观测的钟差估计器。所有计算均为确定性代码。
    /// </summary>
    public static class ClockOffsetEstimator
    {
        /// <summary>
        /// 估计各数据源相对于基准源的钟差。直接共键锚点优先；
        /// 无直接锚点时沿共键关系按广度优先搜索间接链。
        /// </summary>
        /// <param name="anchors">锚点观测集合。</param>
        /// <param name="referenceSourceId">基准源标识（通常为 "GNSS"）。</param>
        /// <param name="method">估计方法，默认中位数。</param>
        /// <returns>成功时返回按 SourceId 序数排序的估计列表（基准源在首位）；基准源不存在时失败。</returns>
        public static Result<IReadOnlyList<ClockOffsetEstimate>> Estimate(
            IEnumerable<AnchorObservation> anchors,
            string referenceSourceId,
            OffsetMethod method = OffsetMethod.Median)
        {
            return Estimate(anchors, referenceSourceId, method, null);
        }

        /// <summary>
        /// 估计各源相对基准源的钟差（带离群锚点选项，裁定 2）。
        /// 先以中位数 + MAD 标记离群（|r| &gt; max(倍数×1.4826×MAD, 绝对下限)）；
        /// 中位数方法只标记不剔除，最小二乘在剔除离群后求均值。
        /// </summary>
        /// <param name="anchors">锚点观测集合。</param>
        /// <param name="referenceSourceId">基准源标识（GNSS/AIS）。</param>
        /// <param name="method">估计方法。</param>
        /// <param name="options">离群与不确定度选项；null 使用默认。</param>
        /// <returns>估计结果；基准源不存在时失败。</returns>
        public static Result<IReadOnlyList<ClockOffsetEstimate>> Estimate(
            IEnumerable<AnchorObservation> anchors,
            string referenceSourceId,
            OffsetMethod method,
            ClockOffsetOptions options)
        {
            ClockOffsetOptions opts = options ?? ClockOffsetOptions.Default;
            if (string.IsNullOrEmpty(referenceSourceId))
            {
                return Result<IReadOnlyList<ClockOffsetEstimate>>.Fail(
                    "timeline_no_reference",
                    "未指定基准数据源。");
            }

            Dictionary<string, Dictionary<string, AnchorObservation>> bySource =
                new Dictionary<string, Dictionary<string, AnchorObservation>>(StringComparer.Ordinal);

            if (anchors != null)
            {
                foreach (AnchorObservation anchor in anchors)
                {
                    if (anchor == null || anchor.SourceId == null || anchor.EventKey == null)
                    {
                        continue;
                    }

                    Dictionary<string, AnchorObservation> perSource;
                    if (!bySource.TryGetValue(anchor.SourceId, out perSource))
                    {
                        perSource = new Dictionary<string, AnchorObservation>(StringComparer.Ordinal);
                        bySource.Add(anchor.SourceId, perSource);
                    }

                    // 同一源同键多次出现时只取首次。
                    if (!perSource.ContainsKey(anchor.EventKey))
                    {
                        perSource.Add(anchor.EventKey, anchor);
                    }
                }
            }

            Dictionary<string, AnchorObservation> referenceAnchors;
            if (!bySource.TryGetValue(referenceSourceId, out referenceAnchors))
            {
                return Result<IReadOnlyList<ClockOffsetEstimate>>.Fail(
                    "timeline_no_reference",
                    "基准数据源不存在于锚点观测中：" + referenceSourceId);
            }

            int referenceManualCount = 0;
            foreach (AnchorObservation anchor in referenceAnchors.Values)
            {
                if (anchor.Origin == AnchorOrigin.Manual)
                {
                    referenceManualCount++;
                }
            }

            Dictionary<string, ClockOffsetEstimate> resolved =
                new Dictionary<string, ClockOffsetEstimate>(StringComparer.Ordinal);
            resolved.Add(referenceSourceId, new ClockOffsetEstimate(
                referenceSourceId,
                referenceSourceId,
                0.0,
                0.0,
                referenceAnchors.Count,
                referenceManualCount,
                method,
                true,
                new double[0],
                null,
                CalibrationStatus.Reference));

            List<string> otherSources = bySource.Keys
                .Where(s => !string.Equals(s, referenceSourceId, StringComparison.Ordinal))
                .OrderBy(s => s, StringComparer.Ordinal)
                .ToList();

            // 广度优先：跳数少者优先；同一跳数按中间源 SourceId 序数解析。
            List<string> frontier = new List<string> { referenceSourceId };
            while (frontier.Count > 0)
            {
                frontier.Sort(StringComparer.Ordinal);
                List<string> next = new List<string>();

                for (int f = 0; f < frontier.Count; f++)
                {
                    string intermediateSourceId = frontier[f];
                    Dictionary<string, AnchorObservation> intermediateAnchors =
                        bySource[intermediateSourceId];
                    ClockOffsetEstimate intermediateEstimate = resolved[intermediateSourceId];

                    for (int s = 0; s < otherSources.Count; s++)
                    {
                        string sourceId = otherSources[s];
                        if (resolved.ContainsKey(sourceId))
                        {
                            continue;
                        }

                        Dictionary<string, AnchorObservation> sourceAnchors = bySource[sourceId];
                        List<string> commonKeys = CommonKeys(sourceAnchors, intermediateAnchors);
                        if (commonKeys.Count == 0)
                        {
                            continue;
                        }

                        PairEstimate pair = EstimatePair(
                            sourceAnchors,
                            intermediateAnchors,
                            commonKeys,
                            method,
                            opts);
                        bool direct = string.Equals(
                            intermediateSourceId,
                            referenceSourceId,
                            StringComparison.Ordinal);

                        double offset = direct
                            ? pair.OffsetSeconds
                            : intermediateEstimate.OffsetSeconds + pair.OffsetSeconds;
                        double uncertainty = direct
                            ? pair.UncertaintySeconds
                            : CombineUncertainty(
                                intermediateEstimate.UncertaintySeconds,
                                pair.UncertaintySeconds);

                        resolved.Add(sourceId, new ClockOffsetEstimate(
                            sourceId,
                            referenceSourceId,
                            offset,
                            uncertainty,
                            commonKeys.Count,
                            CountManual(sourceAnchors, intermediateAnchors, commonKeys),
                            method,
                            false,
                            pair.Residuals,
                            direct ? null : intermediateSourceId,
                            IsFinite(offset)
                                ? CalibrationStatus.Calibrated
                                : CalibrationStatus.Uncalibrated,
                            pair.UsedCount,
                            pair.Rejected));
                        next.Add(sourceId);
                    }
                }

                frontier = next;
            }

            // 无法连通的源保留 NaN 估计。
            for (int s = 0; s < otherSources.Count; s++)
            {
                string sourceId = otherSources[s];
                if (!resolved.ContainsKey(sourceId))
                {
                    resolved.Add(sourceId, new ClockOffsetEstimate(
                        sourceId,
                        referenceSourceId,
                        double.NaN,
                        double.NaN,
                        0,
                        0,
                        method,
                        false,
                        new double[0],
                        null,
                        CalibrationStatus.Uncalibrated));
                }
            }

            List<ClockOffsetEstimate> estimates = new List<ClockOffsetEstimate>(resolved.Count);
            estimates.Add(resolved[referenceSourceId]);
            for (int s = 0; s < otherSources.Count; s++)
            {
                estimates.Add(resolved[otherSources[s]]);
            }

            return Result<IReadOnlyList<ClockOffsetEstimate>>.Ok(estimates);
        }

        private static List<string> CommonKeys(
            Dictionary<string, AnchorObservation> source,
            Dictionary<string, AnchorObservation> other)
        {
            return source.Keys
                .Where(other.ContainsKey)
                .OrderBy(k => k, StringComparer.Ordinal)
                .ToList();
        }

        private static PairEstimate EstimatePair(
            Dictionary<string, AnchorObservation> source,
            Dictionary<string, AnchorObservation> other,
            List<string> commonKeys,
            OffsetMethod method,
            ClockOffsetOptions options)
        {
            int n = commonKeys.Count;
            double[] differences = new double[n];
            for (int i = 0; i < n; i++)
            {
                string key = commonKeys[i];
                differences[i] = source[key].Timestamp.Seconds - other[key].Timestamp.Seconds;
            }

            // 先用中位数 + MAD 标记离群（不物理删除输入）。
            double median = Median(differences);
            double mad = MedianAbsoluteDeviation(differences, median);
            double gate = Math.Max(
                options.OutlierMadMultiplier * 1.4826 * mad,
                options.OutlierAbsoluteFloorSeconds);
            bool[] outlier = new bool[n];
            int outlierCount = 0;
            if (n >= 3)
            {
                for (int i = 0; i < n; i++)
                {
                    if (Math.Abs(differences[i] - median) > gate)
                    {
                        outlier[i] = true;
                        outlierCount++;
                    }
                }
            }

            bool excludeFromFit = method == OffsetMethod.LeastSquares;
            double offset;
            double uncertainty;
            int usedCount;
            if (excludeFromFit)
            {
                List<double> inliers = new List<double>(n);
                for (int i = 0; i < n; i++)
                {
                    if (!outlier[i])
                    {
                        inliers.Add(differences[i]);
                    }
                }

                double[] used = inliers.ToArray();
                usedCount = used.Length;
                offset = Mean(used);
                uncertainty = SampleMeanStandardError(used, offset);
            }
            else
            {
                usedCount = n;
                offset = median;
                uncertainty = n <= 1 ? double.NaN : 1.4826 * mad / Math.Sqrt(n);
                if (n > 1 && !(uncertainty > 0.0))
                {
                    // MAD 为 0（如 10/10/10/100）时用全部点残差标准差，避免把离散掩盖成 0（W2-D05）。
                    uncertainty = SampleMeanStandardError(differences, offset);
                }
            }

            if (!double.IsNaN(uncertainty))
            {
                uncertainty = Math.Max(uncertainty, options.MinUncertaintySeconds);
            }

            double[] residuals = new double[n];
            List<RejectedAnchor> rejected = new List<RejectedAnchor>(outlierCount);
            for (int i = 0; i < n; i++)
            {
                residuals[i] = differences[i] - offset;
                if (outlier[i])
                {
                    double r = differences[i] - median;
                    rejected.Add(new RejectedAnchor(
                        commonKeys[i],
                        differences[i],
                        r,
                        excludeFromFit,
                        string.Format(
                            CultureInfo.InvariantCulture,
                            "离群：残差 {0:F3} s > 门限 {1:F3} s（{2}）",
                            Math.Abs(r),
                            gate,
                            excludeFromFit ? "已剔除出最小二乘拟合" : "中位数法仅标记，未剔除")));
                }
            }

            return new PairEstimate(offset, uncertainty, residuals, usedCount, rejected);
        }

        private static int CountManual(
            Dictionary<string, AnchorObservation> source,
            Dictionary<string, AnchorObservation> other,
            List<string> commonKeys)
        {
            int count = 0;
            for (int i = 0; i < commonKeys.Count; i++)
            {
                string key = commonKeys[i];
                if (source[key].Origin == AnchorOrigin.Manual ||
                    other[key].Origin == AnchorOrigin.Manual)
                {
                    count++;
                }
            }

            return count;
        }

        private static double CombineUncertainty(double first, double second)
        {
            if (double.IsNaN(first) || double.IsNaN(second))
            {
                return double.NaN;
            }

            return Math.Sqrt(first * first + second * second);
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private static double Mean(double[] values)
        {
            double sum = 0.0;
            for (int i = 0; i < values.Length; i++)
            {
                sum += values[i];
            }

            return sum / values.Length;
        }

        private static double SampleMeanStandardError(double[] values, double mean)
        {
            if (values.Length <= 1)
            {
                return double.NaN;
            }

            double sum = 0.0;
            for (int i = 0; i < values.Length; i++)
            {
                double d = values[i] - mean;
                sum += d * d;
            }

            double sampleStdDev = Math.Sqrt(sum / (values.Length - 1));
            return sampleStdDev / Math.Sqrt(values.Length);
        }

        private static double Median(double[] values)
        {
            if (values.Length == 0)
            {
                return double.NaN;
            }

            double[] sorted = (double[])values.Clone();
            Array.Sort(sorted);
            int middle = sorted.Length / 2;
            if ((sorted.Length & 1) == 1)
            {
                return sorted[middle];
            }

            return (sorted[middle - 1] + sorted[middle]) * 0.5;
        }

        private static double MedianAbsoluteDeviation(double[] values, double median)
        {
            if (values.Length == 0)
            {
                return double.NaN;
            }

            double[] deviations = new double[values.Length];
            for (int i = 0; i < values.Length; i++)
            {
                deviations[i] = Math.Abs(values[i] - median);
            }

            return Median(deviations);
        }

        private readonly struct PairEstimate
        {
            public double OffsetSeconds { get; }
            public double UncertaintySeconds { get; }
            public IReadOnlyList<double> Residuals { get; }
            public int UsedCount { get; }
            public IReadOnlyList<RejectedAnchor> Rejected { get; }

            public PairEstimate(
                double offsetSeconds,
                double uncertaintySeconds,
                IReadOnlyList<double> residuals,
                int usedCount,
                IReadOnlyList<RejectedAnchor> rejected)
            {
                OffsetSeconds = offsetSeconds;
                UncertaintySeconds = uncertaintySeconds;
                Residuals = residuals;
                UsedCount = usedCount;
                Rejected = rejected;
            }
        }
    }

    /// <summary>
    /// 时间轴钟差校准器：按数据源匹配估计，平移轨道时间并记录校准状态。
    /// </summary>
    public static class TimelineCalibrator
    {
        /// <summary>
        /// 对轨道应用钟差校准。偏移有限时对整条轨道平移 −Offset；无估计或 NaN 的源保持原样。
        /// </summary>
        /// <param name="tracks">输入轨道集合。</param>
        /// <param name="offsets">钟差估计集合。</param>
        /// <returns>校准后的轨道列表，顺序与输入一致。</returns>
        public static MultiTrackTimeline Apply(
            IEnumerable<Track> tracks,
            IEnumerable<ClockOffsetEstimate> offsets)
        {
            return Calibrate(tracks, offsets).Timeline;
        }

        /// <summary>
        /// 对轨道应用钟差校准，并返回逐数据源状态。
        /// 已校准源平移并标 Calibrated；基准源标 Reference 且不平移；
        /// 无估计或偏移为 NaN/无穷的源标 Uncalibrated 并原样保留。
        /// </summary>
        /// <param name="tracks">输入轨道集合。</param>
        /// <param name="offsets">钟差估计集合。</param>
        /// <returns>校准结果，Sources 覆盖轨道中出现的所有 SourceId。</returns>
        public static CalibrationResult Calibrate(
            IEnumerable<Track> tracks,
            IEnumerable<ClockOffsetEstimate> offsets)
        {
            Dictionary<string, ClockOffsetEstimate> bySource = BuildOffsetMap(offsets);
            List<Track> calibrated = new List<Track>();
            List<SourceCalibration> sources = new List<SourceCalibration>();
            HashSet<string> seenSources = new HashSet<string>(StringComparer.Ordinal);

            if (tracks != null)
            {
                foreach (Track track in tracks)
                {
                    if (track == null)
                    {
                        continue;
                    }

                    string sourceId = track.SourceId ?? string.Empty;
                    ClockOffsetEstimate estimate;
                    bool hasEstimate = bySource.TryGetValue(sourceId, out estimate) &&
                                       IsFinite(estimate.OffsetSeconds);

                    CalibrationStatus status;
                    Track output;
                    if (hasEstimate && estimate.IsReference)
                    {
                        status = CalibrationStatus.Reference;
                        output = track.WithCalibration(CalibrationStatus.Reference, 0.0);
                    }
                    else if (hasEstimate)
                    {
                        status = CalibrationStatus.Calibrated;
                        double shiftSeconds = -estimate.OffsetSeconds;
                        output = track
                            .WithTimeShift(shiftSeconds)
                            .WithCalibration(CalibrationStatus.Calibrated, shiftSeconds);
                    }
                    else
                    {
                        status = CalibrationStatus.Uncalibrated;
                        output = track;
                    }

                    calibrated.Add(output);

                    if (seenSources.Add(sourceId))
                    {
                        sources.Add(BuildSourceCalibration(sourceId, status, estimate, hasEstimate));
                    }
                }
            }

            return new CalibrationResult(new MultiTrackTimeline(calibrated), sources);
        }

        /// <summary>
        /// 返回没有有限钟差估计（无估计或 Offset 为 NaN/无穷）的轨道数据源，按序数排序。
        /// </summary>
        /// <param name="tracks">输入轨道集合。</param>
        /// <param name="offsets">钟差估计集合。</param>
        /// <returns>未校准的数据源标识列表。</returns>
        public static IReadOnlyList<string> UncalibratedSources(
            IEnumerable<Track> tracks,
            IEnumerable<ClockOffsetEstimate> offsets)
        {
            Dictionary<string, ClockOffsetEstimate> bySource = BuildOffsetMap(offsets);
            HashSet<string> uncalibrated = new HashSet<string>(StringComparer.Ordinal);

            if (tracks != null)
            {
                foreach (Track track in tracks)
                {
                    if (track == null || track.SourceId == null)
                    {
                        continue;
                    }

                    ClockOffsetEstimate estimate;
                    if (!bySource.TryGetValue(track.SourceId, out estimate) ||
                        !IsFinite(estimate.OffsetSeconds))
                    {
                        uncalibrated.Add(track.SourceId);
                    }
                }
            }

            return uncalibrated.OrderBy(s => s, StringComparer.Ordinal).ToArray();
        }

        private static SourceCalibration BuildSourceCalibration(
            string sourceId,
            CalibrationStatus status,
            ClockOffsetEstimate estimate,
            bool hasEstimate)
        {
            double offset = hasEstimate ? estimate.OffsetSeconds : double.NaN;
            double uncertainty = hasEstimate ? estimate.UncertaintySeconds : double.NaN;
            int anchorCount = hasEstimate ? estimate.AnchorCount : 0;
            int manualAnchorCount = hasEstimate ? estimate.ManualAnchorCount : 0;
            string viaSourceId = hasEstimate ? estimate.ViaSourceId : null;

            return new SourceCalibration(
                sourceId,
                status,
                offset,
                uncertainty,
                anchorCount,
                manualAnchorCount,
                viaSourceId,
                BuildDescription(
                    sourceId,
                    status,
                    offset,
                    uncertainty,
                    anchorCount,
                    manualAnchorCount,
                    viaSourceId));
        }

        private static string BuildDescription(
            string sourceId,
            CalibrationStatus status,
            double offset,
            double uncertainty,
            int anchorCount,
            int manualAnchorCount,
            string viaSourceId)
        {
            if (status == CalibrationStatus.Reference)
            {
                return sourceId + "：基准";
            }

            if (status == CalibrationStatus.Calibrated)
            {
                string via = string.IsNullOrEmpty(viaSourceId)
                    ? string.Empty
                    : "（经 " + viaSourceId + " 间接）";
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "{0}：已校准{1}，偏移 {2} s ±{3} s（锚点 {4}，人工 {5}）",
                    sourceId,
                    via,
                    FormatSignedSeconds(offset),
                    FormatSeconds(uncertainty),
                    anchorCount,
                    manualAnchorCount);
            }

            return sourceId + "：未校准（无共同锚点，按原始时间使用）";
        }

        private static string FormatSignedSeconds(double value)
        {
            if (double.IsNaN(value))
            {
                return "NaN";
            }

            string text = value.ToString("F3", CultureInfo.InvariantCulture);
            return value >= 0.0 ? "+" + text : text;
        }

        private static string FormatSeconds(double value)
        {
            return double.IsNaN(value)
                ? "NaN"
                : value.ToString("F3", CultureInfo.InvariantCulture);
        }

        private static Dictionary<string, ClockOffsetEstimate> BuildOffsetMap(
            IEnumerable<ClockOffsetEstimate> offsets)
        {
            Dictionary<string, ClockOffsetEstimate> map =
                new Dictionary<string, ClockOffsetEstimate>(StringComparer.Ordinal);
            if (offsets == null)
            {
                return map;
            }

            foreach (ClockOffsetEstimate estimate in offsets)
            {
                if (estimate == null || estimate.SourceId == null || map.ContainsKey(estimate.SourceId))
                {
                    continue;
                }

                map.Add(estimate.SourceId, estimate);
            }

            return map;
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }
    }
}
