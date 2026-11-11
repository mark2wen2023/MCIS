using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Ships
{
    /// <summary>
    /// 单船运动学与多模式控制器接口（对应 ARCHITECTURE.md 5.3.6 节）。
    /// 支持 AIS 回放、手绘航迹、操纵推演等多模式驱动，受 ISimClock 仿真时间推进调度。
    /// </summary>
    public interface IShipController : ITimeDriven
    {
        /// <summary>船舶唯一标识。</summary>
        string VesselId { get; }

        /// <summary>船舶静态尺度与识别参数（可选）。</summary>
        VesselParticulars Particulars { get; }

        /// <summary>当前运动控制模式（如 AisReplay、ManualDrawn、Simulation）。</summary>
        ControlMode Mode { get; }

        /// <summary>当前时刻的船舶运动学状态。</summary>
        TrackSample CurrentState { get; }

        /// <summary>绑定连续插值航迹并设定运动控制模式。</summary>
        void BindTrack(IShipTrack track, ControlMode mode = ControlMode.AisReplay);

        /// <summary>设置是否启用视觉水波横摇/纵摇姿态合成。</summary>
        void SetVisualWaveMotionEnabled(bool enabled);

        /// <summary>纯函数查询任意时刻该船的运动学状态（供 CPA 预计算与碰撞二分搜索调用）。</summary>
        TrackSample SampleStatePure(SimTime time);
    }
}
