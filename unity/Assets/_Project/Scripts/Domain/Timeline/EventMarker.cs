using Mcis.Core;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 时间轴事件标记（车钟变化、媒体开始、人工注释等）。
    /// </summary>
    public sealed class EventMarker
    {
        /// <summary>事件唯一标识。</summary>
        public string Id { get; }

        /// <summary>事件发生时刻。</summary>
        public SimTime Time { get; }

        /// <summary>事件种类（如 change、media、event）。</summary>
        public string Kind { get; }

        /// <summary>事件描述文本。</summary>
        public string Label { get; }

        /// <summary>事件所属数据源标识。</summary>
        public string SourceId { get; }

        /// <summary>事件所属轨道标识。</summary>
        public string TrackId { get; }

        /// <summary>
        /// 构造事件标记。
        /// </summary>
        /// <param name="id">事件唯一标识。</param>
        /// <param name="time">事件发生时刻。</param>
        /// <param name="kind">事件种类。</param>
        /// <param name="label">事件描述文本。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="trackId">所属轨道标识。</param>
        public EventMarker(string id, SimTime time, string kind, string label, string sourceId, string trackId)
        {
            Id = id;
            Time = time;
            Kind = kind;
            Label = label;
            SourceId = sourceId;
            TrackId = trackId;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "{0}@{1:F3}s [{2}] {3}",
                Id,
                Time.Seconds,
                Kind,
                Label);
        }
    }
}
