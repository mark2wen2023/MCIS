using System;
using System.Globalization;

namespace Mcis.Core
{
    /// <summary>
    /// 仿真相对时间（距案件纪元 CaseEpochUtc 的双精度秒数）。
    /// 系统内所有时间轴采样、插值、烘焙均以 SimTime 为唯一自变量。
    /// </summary>
    public readonly struct SimTime : IComparable<SimTime>, IEquatable<SimTime>
    {
        /// <summary>仿真零时刻。</summary>
        public static readonly SimTime Zero = new SimTime(0.0);

        /// <summary>距案件纪元的秒数（双精度）。</summary>
        public double Seconds { get; }

        /// <summary>构造仿真相对时间。</summary>
        public SimTime(double seconds)
        {
            Seconds = seconds;
        }

        /// <summary>转换为对应的 UTC 绝对时间。</summary>
        public DateTimeOffset ToUtc(DateTimeOffset caseEpochUtc)
        {
            return caseEpochUtc.AddSeconds(Seconds);
        }

        /// <summary>从 UTC 绝对时间与案件纪元换算仿真相对时间。</summary>
        public static SimTime FromUtc(DateTimeOffset timestampUtc, DateTimeOffset caseEpochUtc)
        {
            return new SimTime((timestampUtc - caseEpochUtc).TotalSeconds);
        }

        /// <summary>比较两个仿真时间。</summary>
        public int CompareTo(SimTime other)
        {
            return Seconds.CompareTo(other.Seconds);
        }

        /// <summary>判断两个仿真时间是否相等。</summary>
        public bool Equals(SimTime other)
        {
            return Seconds.Equals(other.Seconds);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is SimTime other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            return Seconds.GetHashCode();
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(CultureInfo.InvariantCulture, "{0:F3}s", Seconds);
        }

        public static SimTime operator +(SimTime a, double deltaSeconds)
        {
            return new SimTime(a.Seconds + deltaSeconds);
        }

        public static SimTime operator -(SimTime a, double deltaSeconds)
        {
            return new SimTime(a.Seconds - deltaSeconds);
        }

        public static double operator -(SimTime a, SimTime b)
        {
            return a.Seconds - b.Seconds;
        }

        public static bool operator <(SimTime a, SimTime b)
        {
            return a.Seconds < b.Seconds;
        }

        public static bool operator >(SimTime a, SimTime b)
        {
            return a.Seconds > b.Seconds;
        }

        public static bool operator <=(SimTime a, SimTime b)
        {
            return a.Seconds <= b.Seconds;
        }

        public static bool operator >=(SimTime a, SimTime b)
        {
            return a.Seconds >= b.Seconds;
        }

        public static bool operator ==(SimTime a, SimTime b)
        {
            return a.Seconds == b.Seconds;
        }

        public static bool operator !=(SimTime a, SimTime b)
        {
            return a.Seconds != b.Seconds;
        }
    }
}
