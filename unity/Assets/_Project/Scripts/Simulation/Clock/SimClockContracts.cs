using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Models
{
    /// <summary>
    /// 时间轴标记点（供时间轴 UI 渲染刻度旗标与一键跳转，对应 ARCHITECTURE 5.2 节）。
    /// </summary>
    public readonly struct TimelineMarker : IEquatable<TimelineMarker>, IComparable<TimelineMarker>
    {
        /// <summary>标记唯一标识。</summary>
        public string MarkerId { get; }

        /// <summary>标记所在的仿真时间。</summary>
        public SimTime Time { get; }

        /// <summary>标记类别（如 "ECFC" / "CPA_Danger" / "MinDCPA" / "Collision" / "TimeGap" / "Bookmark"）。</summary>
        public string Category { get; }

        /// <summary>显示标签文本。</summary>
        public string Label { get; }

        /// <summary>关联的风险等级。</summary>
        public RiskLevel AssociatedRisk { get; }

        /// <summary>关联目标实体 ID（可选）。</summary>
        public string TargetEntityId { get; }

        /// <summary>构造时间轴标记点。</summary>
        public TimelineMarker(
            string markerId,
            SimTime time,
            string category,
            string label,
            RiskLevel associatedRisk = RiskLevel.Safe,
            string targetEntityId = null)
        {
            MarkerId = markerId ?? string.Empty;
            Time = time;
            Category = category ?? string.Empty;
            Label = label ?? string.Empty;
            AssociatedRisk = associatedRisk;
            TargetEntityId = targetEntityId;
        }

        /// <inheritdoc />
        public int CompareTo(TimelineMarker other)
        {
            return Time.CompareTo(other.Time);
        }

        /// <inheritdoc />
        public bool Equals(TimelineMarker other)
        {
            return string.Equals(MarkerId, other.MarkerId, StringComparison.Ordinal) &&
                   Time.Equals(other.Time) &&
                   string.Equals(Category, other.Category, StringComparison.Ordinal) &&
                   string.Equals(Label, other.Label, StringComparison.Ordinal) &&
                   AssociatedRisk == other.AssociatedRisk &&
                   string.Equals(TargetEntityId, other.TargetEntityId, StringComparison.Ordinal);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is TimelineMarker other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = MarkerId != null ? MarkerId.GetHashCode() : 0;
                hash = (hash * 397) ^ Time.GetHashCode();
                hash = (hash * 397) ^ (Category != null ? Category.GetHashCode() : 0);
                return hash;
            }
        }
    }
}

namespace Mcis.Simulation
{
    /// <summary>
    /// 仿真时钟运行状态枚举（对应 ARCHITECTURE 5.3.5 节）。
    /// </summary>
    public enum SimClockState : byte
    {
        /// <summary>已停止（位于起始时间）。</summary>
        Stopped = 0,
        /// <summary>正常或倍速播放中。</summary>
        Playing = 1,
        /// <summary>已暂停。</summary>
        Paused = 2,
        /// <summary>正在拖动时间轴滑块（Scrubbing）。</summary>
        Scrubbing = 3,
        /// <summary>离线固定步长视频录制中。</summary>
        OfflineRecording = 4
    }

    /// <summary>
    /// 所有受仿真时间驱动的子系统接口，按 ExecutionPriority 升序确定性执行。
    /// </summary>
    public interface ITimeDriven
    {
        /// <summary>执行优先级（越小越先执行：10=Environment, 20=ShipController, 30=CPA, 40=Collision, 50=ECFC, 60=Presentation）。</summary>
        int ExecutionPriority { get; }

        /// <summary>在给定仿真时间步求值子系统状态。</summary>
        void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek);
    }

    /// <summary>
    /// 时间轴标记提供者接口。
    /// </summary>
    public interface ITimelineMarkerProvider
    {
        /// <summary>获取当前提供者的全部时间轴标记。</summary>
        IReadOnlyList<TimelineMarker> GetMarkers();

        /// <summary>标记集合发生变化时触发。</summary>
        event Action MarkersChanged;
    }

    /// <summary>
    /// 全局确定性仿真时钟接口，掌控播放、暂停、倍速（0.5x–16x）、Seek、逐帧/步进与区间钳制。
    /// </summary>
    public interface ISimClock
    {
        /// <summary>当前仿真时间。</summary>
        SimTime CurrentTime { get; }

        /// <summary>当前整数微秒 Tick 值（1 tick = 1 μs）。</summary>
        long CurrentTicks { get; }

        /// <summary>仿真区间起始时间。</summary>
        SimTime StartTime { get; }

        /// <summary>仿真区间结束时间。</summary>
        SimTime EndTime { get; }

        /// <summary>当前时钟运行状态。</summary>
        SimClockState State { get; }

        /// <summary>当前播放倍速（支持 0.5, 1, 2, 4, 8, 16 等）。</summary>
        float PlaybackRate { get; }

        /// <summary>是否处于播放状态。</summary>
        bool IsPlaying { get; }

        /// <summary>到达终点时是否循环播放。</summary>
        bool IsLooping { get; set; }

        /// <summary>仿真时间发生变化时触发。</summary>
        event Action<SimTime> TimeChanged;

        /// <summary>时钟状态发生变化时触发。</summary>
        event Action<SimClockState> StateChanged;

        /// <summary>配置仿真起止时间区间。</summary>
        void ConfigureRange(SimTime start, SimTime end);

        /// <summary>开始或继续播放。</summary>
        void Play();

        /// <summary>暂停播放。</summary>
        void Pause();

        /// <summary>停止并重置回起始时间。</summary>
        void Stop();

        /// <summary>设置播放倍速。</summary>
        void SetRate(float rate);

        /// <summary>跳转到指定仿真时间（isSeek=true，钳制到有效区间）。</summary>
        void Seek(SimTime targetTime);

        /// <summary>开始时间轴拖动。</summary>
        void BeginScrub();

        /// <summary>结束时间轴拖动并恢复为暂停状态。</summary>
        void EndScrub();

        /// <summary>向前步进指定秒数（默认 1.0 秒）。</summary>
        void StepForward(double stepSeconds = 1.0);

        /// <summary>向后步进指定秒数（默认 1.0 秒）。</summary>
        void StepBackward(double stepSeconds = 1.0);

        /// <summary>按固定帧率（默认 30 fps）前进或后退指定帧数。</summary>
        void StepFrames(int frameDelta, int referenceFps = 30);

        /// <summary>跳转到下一个时间轴标记。</summary>
        void JumpToNextMarker(string categoryFilter = null);

        /// <summary>跳转到上一个时间轴标记。</summary>
        void JumpToPreviousMarker(string categoryFilter = null);

        /// <summary>推进仿真时钟（由主循环按真实帧时间调用）。</summary>
        void Tick(double unscaledDeltaSeconds);

        /// <summary>注册受时间驱动的子系统。</summary>
        void RegisterTimeDriven(ITimeDriven driven);

        /// <summary>注销受时间驱动的子系统。</summary>
        void UnregisterTimeDriven(ITimeDriven driven);
    }
}
