using System;
using System.Collections.Generic;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 媒体条目（音频、雷达截图、ECDIS 截屏）。只保留元数据与时间范围，不读取或解码文件内容。
    /// </summary>
    public sealed class MediaItem
    {
        private static readonly IReadOnlyDictionary<string, string> EmptyMetadata =
            new Dictionary<string, string>(StringComparer.Ordinal);

        /// <summary>媒体唯一标识（通常来自清单 id 列）。</summary>
        public string Id { get; }

        /// <summary>媒体所属轨道种类。</summary>
        public TrackKind Kind { get; }

        /// <summary>通道名称（如 CH1、CH16、X-BAND、ECDIS）。</summary>
        public string Channel { get; }

        /// <summary>媒体文件名（不要求文件真实存在）。</summary>
        public string FileName { get; }

        /// <summary>媒体覆盖的时间范围。</summary>
        public TimeRange Range { get; }

        /// <summary>附加元数据（sha256、note、file 等）。</summary>
        public IReadOnlyDictionary<string, string> Metadata { get; }

        /// <summary>
        /// 构造媒体条目。
        /// </summary>
        /// <param name="id">媒体唯一标识。</param>
        /// <param name="kind">媒体轨道种类。</param>
        /// <param name="channel">通道名称。</param>
        /// <param name="fileName">媒体文件名。</param>
        /// <param name="range">媒体时间范围。</param>
        /// <param name="metadata">附加元数据，可为 null。</param>
        public MediaItem(
            string id,
            TrackKind kind,
            string channel,
            string fileName,
            TimeRange range,
            IReadOnlyDictionary<string, string> metadata = null)
        {
            Id = id;
            Kind = kind;
            Channel = channel;
            FileName = fileName;
            Range = range;
            Metadata = metadata ?? EmptyMetadata;
        }

        /// <summary>
        /// 返回时间平移后的新媒体条目（共享元数据字典）。
        /// </summary>
        /// <param name="seconds">平移秒数。</param>
        /// <returns>新的媒体条目。</returns>
        public MediaItem Shift(double seconds)
        {
            return new MediaItem(Id, Kind, Channel, FileName, Range.Shift(seconds), Metadata);
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "{0} [{1}/{2}] {3}",
                Id,
                Kind,
                Channel,
                FileName);
        }
    }
}
