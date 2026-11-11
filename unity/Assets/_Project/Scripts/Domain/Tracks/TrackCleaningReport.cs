using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>
    /// 航迹异常点剔除与缺口检测报告（包含保留样本、被剔除样本及按原因码分类统计）。
    /// </summary>
    public sealed class TrackCleaningReport
    {
        /// <summary>船舶标识。</summary>
        public string VesselId { get; }

        /// <summary>输入的原始记录总数。</summary>
        public int TotalInputCount { get; }

        /// <summary>通过清洗保留下来的原始 AIS 记录列表。</summary>
        public IReadOnlyList<AisDecodedRecord> KeptRecords { get; }

        /// <summary>转换至局部 ENU 坐标系后的保留航迹样本列表（按时间升序）。</summary>
        public IReadOnlyList<TrackSample> CleanedSamples { get; }

        /// <summary>被剔除的异常样本列表（含原因码与诊断详情）。</summary>
        public IReadOnlyList<RejectedSample> RejectedSamples { get; }

        /// <summary>检测到的时间缺口区间列表。</summary>
        public IReadOnlyList<TimeGapSpan> TimeGaps { get; }

        /// <summary>按剔除原因码统计的被剔除点数量。</summary>
        public IReadOnlyDictionary<RejectReason, int> RejectionCountsByReason { get; }

        /// <summary>构造航迹清洗报告。</summary>
        public TrackCleaningReport(
            string vesselId,
            int totalInputCount,
            IReadOnlyList<AisDecodedRecord> keptRecords,
            IReadOnlyList<TrackSample> cleanedSamples,
            IReadOnlyList<RejectedSample> rejectedSamples,
            IReadOnlyList<TimeGapSpan> timeGaps)
        {
            VesselId = vesselId ?? string.Empty;
            TotalInputCount = totalInputCount;
            KeptRecords = keptRecords ?? Array.Empty<AisDecodedRecord>();
            CleanedSamples = cleanedSamples ?? Array.Empty<TrackSample>();
            RejectedSamples = rejectedSamples ?? Array.Empty<RejectedSample>();
            TimeGaps = timeGaps ?? Array.Empty<TimeGapSpan>();

            Dictionary<RejectReason, int> counts = new Dictionary<RejectReason, int>();
            for (int i = 0; i < RejectedSamples.Count; i++)
            {
                RejectReason reason = RejectedSamples[i].Reason;
                int existing;
                if (counts.TryGetValue(reason, out existing))
                {
                    counts[reason] = existing + 1;
                }
                else
                {
                    counts[reason] = 1;
                }
            }
            RejectionCountsByReason = counts;
        }

        /// <summary>获取指定原因码的被剔除样本数量。</summary>
        public int GetRejectedCount(RejectReason reason)
        {
            int count;
            return RejectionCountsByReason.TryGetValue(reason, out count) ? count : 0;
        }
    }
}
