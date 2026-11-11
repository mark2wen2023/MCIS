using System;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 时间轴样本。标量轨道使用 Value；位置轨道使用 Position（此时 Value 为 NaN）；
    /// Text 保存车钟档位、目标名称等附加文本。
    /// </summary>
    public readonly struct TimelineSample
    {
        /// <summary>样本时刻。</summary>
        public SimTime Time { get; }

        /// <summary>标量数值；位置轨道为 NaN。</summary>
        public double Value { get; }

        /// <summary>是否携带经纬度位置。</summary>
        public bool HasPosition { get; }

        /// <summary>经纬度位置；无位置时为默认零坐标。</summary>
        public GeoCoord Position { get; }

        /// <summary>附加文本（车钟档位、目标名称等），可为 null。</summary>
        public string Text { get; }

        private TimelineSample(SimTime time, double value, bool hasPosition, GeoCoord position, string text)
        {
            Time = time;
            Value = value;
            HasPosition = hasPosition;
            Position = position;
            Text = text;
        }

        /// <summary>
        /// 创建标量样本。
        /// </summary>
        /// <param name="time">样本时刻。</param>
        /// <param name="value">标量数值。</param>
        /// <param name="text">附加文本，可为 null。</param>
        /// <returns>标量样本。</returns>
        public static TimelineSample Scalar(SimTime time, double value, string text = null)
        {
            return new TimelineSample(time, value, false, default(GeoCoord), text);
        }

        /// <summary>
        /// 创建位置样本（Value 强制为 NaN）。
        /// </summary>
        /// <param name="time">样本时刻。</param>
        /// <param name="position">经纬度位置。</param>
        /// <returns>位置样本。</returns>
        public static TimelineSample AtPosition(SimTime time, GeoCoord position)
        {
            return new TimelineSample(time, double.NaN, true, position, null);
        }

        /// <summary>
        /// 创建带附加文本的位置样本（例如目标位置附带目标名称）。
        /// </summary>
        /// <param name="time">样本时刻。</param>
        /// <param name="position">经纬度位置。</param>
        /// <param name="text">附加文本，可为 null。</param>
        /// <returns>位置样本。</returns>
        public static TimelineSample AtPosition(SimTime time, GeoCoord position, string text)
        {
            return new TimelineSample(time, double.NaN, true, position, text);
        }

        /// <inheritdoc />
        public override string ToString()
        {
            if (HasPosition)
            {
                return string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "{0:F3}s @ {1}",
                    Time.Seconds,
                    Position);
            }

            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "{0:F3}s = {1}{2}",
                Time.Seconds,
                Value,
                string.IsNullOrEmpty(Text) ? string.Empty : " (" + Text + ")");
        }
    }
}
