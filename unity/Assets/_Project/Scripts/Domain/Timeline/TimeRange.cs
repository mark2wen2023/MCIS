using System;
using Mcis.Core;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 闭区间时间范围 [Start, End]，端点均包含在范围内。
    /// </summary>
    public readonly struct TimeRange : IEquatable<TimeRange>
    {
        /// <summary>范围起点（含）。</summary>
        public SimTime Start { get; }

        /// <summary>范围终点（含）。</summary>
        public SimTime End { get; }

        /// <summary>范围时长（秒）。</summary>
        public double DurationSeconds
        {
            get { return End.Seconds - Start.Seconds; }
        }

        /// <summary>
        /// 构造闭区间时间范围。
        /// </summary>
        /// <param name="start">范围起点（含）。</param>
        /// <param name="end">范围终点（含），不得早于起点。</param>
        /// <exception cref="ArgumentException">当 end 早于 start 时抛出。</exception>
        public TimeRange(SimTime start, SimTime end)
        {
            if (end < start)
            {
                throw new ArgumentException("时间范围终点不能早于起点。", nameof(end));
            }

            Start = start;
            End = end;
        }

        /// <summary>
        /// 判断给定时刻是否落在闭区间内。
        /// </summary>
        /// <param name="time">待判断时刻。</param>
        /// <returns>位于 [Start, End] 内返回 true。</returns>
        public bool Contains(SimTime time)
        {
            return time >= Start && time <= End;
        }

        /// <summary>
        /// 判断两个闭区间是否重叠（端点接触也算重叠）。
        /// </summary>
        /// <param name="other">另一时间范围。</param>
        /// <returns>存在公共部分返回 true。</returns>
        public bool Overlaps(TimeRange other)
        {
            return Start <= other.End && other.Start <= End;
        }

        /// <summary>
        /// 求当前范围与另一范围的交集。
        /// </summary>
        /// <param name="other">另一时间范围。</param>
        /// <param name="intersection">重叠时输出交集，不重叠时输出默认零区间。</param>
        /// <returns>存在交集返回 true。</returns>
        public bool Intersect(TimeRange other, out TimeRange intersection)
        {
            if (!Overlaps(other))
            {
                intersection = default(TimeRange);
                return false;
            }

            SimTime start = Start >= other.Start ? Start : other.Start;
            SimTime end = End <= other.End ? End : other.End;
            intersection = new TimeRange(start, end);
            return true;
        }

        /// <summary>
        /// 求两个范围的交集（静态便捷重载）。
        /// </summary>
        /// <param name="first">第一个时间范围。</param>
        /// <param name="second">第二个时间范围。</param>
        /// <param name="intersection">重叠时输出交集，不重叠时输出默认零区间。</param>
        /// <returns>存在交集返回 true。</returns>
        public static bool Intersect(TimeRange first, TimeRange second, out TimeRange intersection)
        {
            return first.Intersect(second, out intersection);
        }

        /// <summary>
        /// 求两个区间的并集（包含两者之间的空隙，结果为最小覆盖区间）。
        /// </summary>
        /// <param name="other">另一时间范围。</param>
        /// <returns>覆盖两个区间的最小闭区间。</returns>
        public TimeRange Union(TimeRange other)
        {
            SimTime start = Start <= other.Start ? Start : other.Start;
            SimTime end = End >= other.End ? End : other.End;
            return new TimeRange(start, end);
        }

        /// <summary>
        /// 将范围整体平移指定秒数，返回新的时间范围。
        /// </summary>
        /// <param name="seconds">平移秒数，可为负。</param>
        /// <returns>平移后的时间范围。</returns>
        public TimeRange Shift(double seconds)
        {
            return new TimeRange(Start + seconds, End + seconds);
        }

        /// <inheritdoc />
        public bool Equals(TimeRange other)
        {
            return Start == other.Start && End == other.End;
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is TimeRange other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                return (Start.GetHashCode() * 397) ^ End.GetHashCode();
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "[{0:F3}s, {1:F3}s]",
                Start.Seconds,
                End.Seconds);
        }
    }
}
