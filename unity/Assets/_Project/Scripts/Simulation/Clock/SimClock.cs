using System;
using System.Collections.Generic;
using Mcis.Core;

namespace Mcis.Simulation
{
    /// <summary>
    /// 确定性仿真时钟实现（对应 P1_TASK_A 第 7 条与 ARCHITECTURE 4.4 / 5.3.5 节）。
    /// 内部以 64 位整数微秒 Tick（1 tick = 1 μs）累计时间，确保任意连续 Tick 与直接 Seek 到同一时刻状态严格一致。
    /// </summary>
    public sealed partial class SimClock : ISimClock
    {
        /// <summary>每秒对应的整数 Tick 数（1 tick = 1 微秒 = 1e-6 秒）。</summary>
        public const long TicksPerSecond = 1_000_000L;

        /// <summary>每毫秒对应的整数 Tick 数。</summary>
        public const long TicksPerMillisecond = 1_000L;

        /// <summary>未显式配置区间时的默认最大仿真时长（秒，约 100 天）。</summary>
        public const double DefaultMaxEndSeconds = 8_640_000.0;

        /// <summary>默认单步步进时长（秒）。</summary>
        public const double DefaultStepSeconds = 1.0;

        /// <summary>标准支持的播放倍速列表（0.5x, 1x, 2x, 4x, 8x, 16x）。</summary>
        public static readonly IReadOnlyList<float> SupportedRates = new float[]
        {
            0.5f, 1.0f, 2.0f, 4.0f, 8.0f, 16.0f
        };

        private long _startTicks;
        private long _endTicks;
        private long _currentTicks;
        private SimClockState _state;
        private float _playbackRate;

        /// <summary>当前整数微秒 Tick 值。</summary>
        public long CurrentTicks
        {
            get { return _currentTicks; }
        }

        /// <summary>区间起始整数微秒 Tick 值。</summary>
        public long StartTicks
        {
            get { return _startTicks; }
        }

        /// <summary>区间结束整数微秒 Tick 值。</summary>
        public long EndTicks
        {
            get { return _endTicks; }
        }

        /// <inheritdoc />
        public SimTime CurrentTime
        {
            get { return TicksToSimTime(_currentTicks); }
        }

        /// <inheritdoc />
        public SimTime StartTime
        {
            get { return TicksToSimTime(_startTicks); }
        }

        /// <inheritdoc />
        public SimTime EndTime
        {
            get { return TicksToSimTime(_endTicks); }
        }

        /// <inheritdoc />
        public SimClockState State
        {
            get { return _state; }
        }

        /// <inheritdoc />
        public float PlaybackRate
        {
            get { return _playbackRate; }
        }

        /// <summary>当前播放倍速（PlaybackRate 的简写别名）。</summary>
        public float Rate
        {
            get { return _playbackRate; }
        }

        /// <inheritdoc />
        public bool IsPlaying
        {
            get { return _state == SimClockState.Playing; }
        }

        /// <summary>是否处于暂停状态。</summary>
        public bool IsPaused
        {
            get { return _state == SimClockState.Paused; }
        }

        /// <inheritdoc />
        public bool IsLooping { get; set; }

        /// <inheritdoc />
        public event Action<SimTime> TimeChanged;

        /// <inheritdoc />
        public event Action<SimClockState> StateChanged;

        /// <summary>播放倍速发生变化时触发。</summary>
        public event Action<float> RateChanged;

        /// <summary>构造默认区间的仿真时钟（[0, DefaultMaxEndSeconds]，初始状态为 Paused，倍速 1x）。</summary>
        public SimClock()
            : this(SimTime.Zero, new SimTime(DefaultMaxEndSeconds))
        {
        }

        /// <summary>按指定起止秒数构造仿真时钟。</summary>
        public SimClock(double startSeconds, double endSeconds)
            : this(new SimTime(startSeconds), new SimTime(endSeconds))
        {
        }

        /// <summary>按指定起止仿真时间构造仿真时钟。</summary>
        public SimClock(SimTime startTime, SimTime endTime)
        {
            if (double.IsNaN(startTime.Seconds) || double.IsInfinity(startTime.Seconds))
            {
                throw new ArgumentOutOfRangeException(nameof(startTime));
            }
            if (double.IsNaN(endTime.Seconds) || double.IsInfinity(endTime.Seconds) || endTime < startTime)
            {
                throw new ArgumentOutOfRangeException(nameof(endTime), "EndTime must be >= StartTime.");
            }

            _startTicks = SecondsToTicks(startTime.Seconds);
            _endTicks = SecondsToTicks(endTime.Seconds);
            _currentTicks = _startTicks;
            _state = SimClockState.Paused;
            _playbackRate = 1.0f;
        }

        /// <summary>将双精度秒数转换为整数微秒 Tick（四舍五入远离零）。</summary>
        public static long SecondsToTicks(double seconds)
        {
            return (long)Math.Round(seconds * TicksPerSecond, MidpointRounding.AwayFromZero);
        }

        /// <summary>将整数微秒 Tick 转换为双精度秒数。</summary>
        public static double TicksToSeconds(long ticks)
        {
            return (double)ticks / TicksPerSecond;
        }

        /// <summary>将整数微秒 Tick 转换为 SimTime。</summary>
        public static SimTime TicksToSimTime(long ticks)
        {
            return new SimTime(TicksToSeconds(ticks));
        }

        /// <summary>检查给定倍速是否为合法受支持倍速（0.5, 1, 2, 4, 8, 16 及扩展 0.25, 32）。</summary>
        public static bool IsSupportedRate(float rate)
        {
            if (float.IsNaN(rate) || float.IsInfinity(rate) || rate <= 0f)
            {
                return false;
            }
            for (int i = 0; i < SupportedRates.Count; i++)
            {
                if (Math.Abs(rate - SupportedRates[i]) < 1e-5f)
                {
                    return true;
                }
            }
            return Math.Abs(rate - 0.25f) < 1e-5f || Math.Abs(rate - 32.0f) < 1e-5f;
        }

        /// <inheritdoc />
        public void ConfigureRange(SimTime start, SimTime end)
        {
            if (double.IsNaN(start.Seconds) || double.IsInfinity(start.Seconds))
            {
                throw new ArgumentOutOfRangeException(nameof(start));
            }
            if (double.IsNaN(end.Seconds) || double.IsInfinity(end.Seconds) || end < start)
            {
                throw new ArgumentOutOfRangeException(nameof(end), "EndTime must be >= StartTime.");
            }

            _startTicks = SecondsToTicks(start.Seconds);
            _endTicks = SecondsToTicks(end.Seconds);

            long clamped = ClampTicks(_currentTicks);
            if (clamped != _currentTicks)
            {
                ApplyTimeJump(clamped, notifyIfUnchanged: false);
            }
        }

        /// <summary>配置仿真起止时间区间（双精度秒重载）。</summary>
        public void ConfigureRange(double startSeconds, double endSeconds)
        {
            ConfigureRange(new SimTime(startSeconds), new SimTime(endSeconds));
        }
    }
}
