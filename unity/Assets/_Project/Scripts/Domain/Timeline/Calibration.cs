using System;
using System.Collections.Generic;
using System.Linq;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 数据源时间校准状态。
    /// </summary>
    public enum CalibrationStatus
    {
        /// <summary>没有任何可用钟差估计，按原始时间使用。</summary>
        Uncalibrated = 0,
        /// <summary>作为基准源，偏移恒为 0。</summary>
        Reference = 1,
        /// <summary>已按钟差估计完成校准。</summary>
        Calibrated = 2
    }

    /// <summary>
    /// 校准状态的中文文本。
    /// </summary>
    public static class CalibrationStatusText
    {
        /// <summary>
        /// 返回状态的中文名称。
        /// </summary>
        /// <param name="status">校准状态。</param>
        /// <returns>"未校准"、"基准" 或 "已校准"。</returns>
        public static string ToChinese(CalibrationStatus status)
        {
            switch (status)
            {
                case CalibrationStatus.Reference:
                    return "基准";
                case CalibrationStatus.Calibrated:
                    return "已校准";
                default:
                    return "未校准";
            }
        }
    }

    /// <summary>
    /// 单个数据源的校准摘要。
    /// </summary>
    public sealed class SourceCalibration
    {
        /// <summary>数据源标识。</summary>
        public string SourceId { get; }

        /// <summary>校准状态。</summary>
        public CalibrationStatus Status { get; }

        /// <summary>相对基准源的钟差（秒）；无估计时为 NaN。</summary>
        public double OffsetSeconds { get; }

        /// <summary>不确定度（秒）；无估计或样本不足时为 NaN。</summary>
        public double UncertaintySeconds { get; }

        /// <summary>参与估计的锚点数量。</summary>
        public int AnchorCount { get; }

        /// <summary>其中的人工锚点数量。</summary>
        public int ManualAnchorCount { get; }

        /// <summary>间接校准时的中间源标识；直接校准为 null。</summary>
        public string ViaSourceId { get; }

        /// <summary>中文摘要，例如 “MARY-VDR：已校准，偏移 +3.200 s ±0.010 s（锚点 60，人工 0）”。</summary>
        public string Description { get; }

        /// <summary>
        /// 构造数据源校准摘要。
        /// </summary>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="status">校准状态。</param>
        /// <param name="offsetSeconds">钟差（秒）。</param>
        /// <param name="uncertaintySeconds">不确定度（秒）。</param>
        /// <param name="anchorCount">锚点数量。</param>
        /// <param name="manualAnchorCount">人工锚点数量。</param>
        /// <param name="viaSourceId">间接中间源，可为 null。</param>
        /// <param name="description">中文摘要。</param>
        public SourceCalibration(
            string sourceId,
            CalibrationStatus status,
            double offsetSeconds,
            double uncertaintySeconds,
            int anchorCount,
            int manualAnchorCount,
            string viaSourceId,
            string description)
        {
            SourceId = sourceId;
            Status = status;
            OffsetSeconds = offsetSeconds;
            UncertaintySeconds = uncertaintySeconds;
            AnchorCount = anchorCount;
            ManualAnchorCount = manualAnchorCount;
            ViaSourceId = viaSourceId;
            Description = description;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return Description;
        }
    }

    /// <summary>
    /// 多轨时间轴校准结果：校准后的时间轴与逐数据源摘要。
    /// </summary>
    public sealed class CalibrationResult
    {
        private static readonly IReadOnlyList<SourceCalibration> EmptySources =
            new SourceCalibration[0];

        /// <summary>校准后的多轨时间轴。</summary>
        public MultiTrackTimeline Timeline { get; }

        /// <summary>逐数据源校准摘要，按 SourceId 序数排序。</summary>
        public IReadOnlyList<SourceCalibration> Sources { get; }

        /// <summary>仍处于未校准状态的数据源，按 SourceId 序数排序。</summary>
        public IReadOnlyList<string> UncalibratedSources { get; }

        /// <summary>是否所有出现的数据源均已校准或是基准源。</summary>
        public bool AllCalibrated { get; }

        /// <summary>
        /// 构造校准结果。
        /// </summary>
        /// <param name="timeline">校准后的时间轴，可为 null。</param>
        /// <param name="sources">逐数据源摘要，可为 null。</param>
        public CalibrationResult(
            MultiTrackTimeline timeline,
            IEnumerable<SourceCalibration> sources)
        {
            Timeline = timeline ?? new MultiTrackTimeline(null);

            SourceCalibration[] ordered = (sources ?? EmptySources)
                .Where(s => s != null)
                .OrderBy(s => s.SourceId, StringComparer.Ordinal)
                .ToArray();
            Sources = ordered;

            UncalibratedSources = ordered
                .Where(s => s.Status == CalibrationStatus.Uncalibrated)
                .Select(s => s.SourceId)
                .ToArray();

            AllCalibrated = UncalibratedSources.Count == 0;
        }
    }
}
