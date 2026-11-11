using System;
using System.Collections.Generic;
using Mcis.Domain.Timeline;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// 单个 CSV 列到时间轴轨道的映射。
    /// </summary>
    public sealed class VdrCsvColumnMapping
    {
        private static readonly IReadOnlyDictionary<string, double> EmptyTextValues =
            new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);

        /// <summary>CSV 列名（表头文本）。</summary>
        public string Column { get; set; }

        /// <summary>该列对应的轨道种类。</summary>
        public TrackKind Kind { get; set; }

        /// <summary>轨道名称；为空时使用 Kind 的名称。</summary>
        public string TrackName { get; set; }

        /// <summary>数值缩放系数，默认 1。</summary>
        public double Scale { get; set; } = 1.0;

        /// <summary>数值偏移量，默认 0。</summary>
        public double Offset { get; set; } = 0.0;

        /// <summary>文本到数值的映射（如 "HALF AHEAD"→3），匹配忽略大小写与首尾空白。</summary>
        public IReadOnlyDictionary<string, double> TextValues { get; set; } = EmptyTextValues;

        /// <summary>值变化时是否生成 Kind="change" 的事件标记。</summary>
        public bool MarkChanges { get; set; }
    }

    /// <summary>
    /// 通用 CSV 导入映射。
    /// </summary>
    public sealed class VdrCsvMapping
    {
        /// <summary>时间列名。</summary>
        public string TimeColumn { get; set; }

        /// <summary>
        /// 时间格式；null 表示按 ISO-8601 解析，否则使用 DateTime.ParseExact 格式，
        /// 并按 UTC 或 TimeZoneOffset 解释。
        /// </summary>
        public string TimeFormat { get; set; }

        /// <summary>本地时间相对 UTC 的偏移（默认 0；+08:00 本地时间用 TimeSpan.FromHours(8)）。</summary>
        public TimeSpan TimeZoneOffset { get; set; } = TimeSpan.Zero;

        /// <summary>字段分隔符，默认逗号。</summary>
        public char Delimiter { get; set; } = ',';

        /// <summary>列映射集合。</summary>
        public IList<VdrCsvColumnMapping> Columns { get; set; } = new List<VdrCsvColumnMapping>();

        /// <summary>事件列（可空）；该列非空时生成 Kind="event" 的事件标记，Label 为单元格值。</summary>
        public string EventColumn { get; set; }
    }
}
