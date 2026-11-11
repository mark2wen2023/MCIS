using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Ships
{
    /// <summary>
    /// 船舶运动学仿真控制器（纯 C# 实现，不依赖 UnityEngine）。
    /// 订阅 <see cref="ISimClock"/> 时间推进，从 <see cref="IShipTrack"/> 连续插值求取当前运动状态，
    /// 并通过 <see cref="IGeoConverter"/> 计算对应的 Unity 局部世界坐标（双精度）。
    /// 说明：为避免 Mcis.Simulation 反向依赖 Mcis.UI，UI 层的 IShipStateSource 接口由
    /// Mcis.Presentation.Ships.ShipStateSourceAdapter 适配包装本控制器。
    /// </summary>
    public sealed class ShipController : IShipController, ITimeDriven, IDisposable
    {
        private IShipTrack _track;
        private IGeoConverter _geoConverter;
        private ISimClock _clock;
        private TrackSample _currentSample;
        private Double3 _currentUnityPosition;
        private TimeGapSpan _currentTimeGap;
        private SimTime _lastEvaluatedTime;
        private bool _hasEvaluated;
        private bool _isVisible;
        private bool _isInTimeGap;
        private bool _lastUpdateWasSeek;

        /// <summary>ITimeDriven 执行优先级（20 = ShipController，早于 CPA=30 与 Presentation/UI=60）。</summary>
        public int ExecutionPriority
        {
            get { return 20; }
        }

        /// <summary>船舶唯一标识。</summary>
        public string VesselId { get; }

        /// <summary>HUD 或视图显示船名。</summary>
        public string DisplayName { get; set; }

        /// <summary>角色或船型副标题（如 "本船 / 散货船"）。</summary>
        public string SubtitleRole { get; set; }

        /// <summary>状态徽章文本（如 "压载出港"、"满载进港"）。</summary>
        public string StatusBadgeText { get; set; }

        /// <summary>船舶静态尺度与识别参数（可选）。</summary>
        public VesselParticulars Particulars { get; set; }

        /// <summary>底层连续插值航迹。</summary>
        public IShipTrack Track
        {
            get { return _track; }
        }

        /// <summary>大地坐标与 Unity 世界坐标转换器。</summary>
        public IGeoConverter GeoConverter
        {
            get { return _geoConverter; }
            set
            {
                _geoConverter = value ?? new LocalEnuGeoConverter();
                if (_hasEvaluated)
                {
                    _currentUnityPosition = _geoConverter.EnuToUnityWorld(_currentSample.EnuCenter);
                }
            }
        }

        /// <summary>当前绑定的仿真时钟。</summary>
        public ISimClock Clock
        {
            get { return _clock; }
        }

        /// <summary>当前船舶运动控制模式（默认 AisReplay）。</summary>
        public ControlMode ControlMode { get; set; }

        /// <summary>运动控制模式别名（实现 IShipController）。</summary>
        public ControlMode Mode
        {
            get { return ControlMode; }
            set { ControlMode = value; }
        }

        /// <summary>当前时刻的船舶运动学样本。</summary>
        public TrackSample CurrentSample
        {
            get { return _currentSample; }
        }

        /// <summary>当前时刻的船舶运动学状态（实现 IShipController）。</summary>
        public TrackSample CurrentState
        {
            get { return _currentSample; }
        }

        /// <summary>是否启用视觉水波横摇/纵摇姿态合成。</summary>
        public bool VisualWaveMotionEnabled { get; set; } = true;

        /// <summary>设置是否启用视觉水波姿态合成。</summary>
        public void SetVisualWaveMotionEnabled(bool enabled)
        {
            VisualWaveMotionEnabled = enabled;
        }

        /// <summary>当前时刻经 <see cref="GeoConverter"/> 转换后的双精度 Unity 世界坐标 (x=East, y=Up+Offset, z=North)。</summary>
        public Double3 CurrentUnityPosition
        {
            get { return _currentUnityPosition; }
        }

        /// <summary>当前时刻船舶是否可见（若处于 HideVessel 策略的时间缺口或超出有效区间外推被拒则为 false）。</summary>
        public bool IsVisible
        {
            get { return _isVisible; }
        }

        /// <summary>当前时刻是否处于时间缺口内。</summary>
        public bool IsInTimeGap
        {
            get { return _isInTimeGap; }
        }

        /// <summary>当前所处的时间缺口详情（仅当 <see cref="IsInTimeGap"/> 为 true 时有效）。</summary>
        public TimeGapSpan CurrentTimeGap
        {
            get { return _currentTimeGap; }
        }

        /// <summary>最近一次状态更新是否由跳转/拖动（Seek）触发。</summary>
        public bool LastUpdateWasSeek
        {
            get { return _lastUpdateWasSeek; }
        }

        /// <summary>船舶总长 LOA（米），优先取 Particulars.LoaM，次取 AntennaOffset.LoaM。</summary>
        public float LoaM
        {
            get
            {
                if (Particulars == null) return 0f;
                if (Particulars.LoaM > 0f) return Particulars.LoaM;
                return Particulars.AntennaOffset.LoaM > 0f ? Particulars.AntennaOffset.LoaM : 0f;
            }
        }

        /// <summary>船舶型宽 Beam（米），优先取 Particulars.BeamM，次取 AntennaOffset.BeamM。</summary>
        public float BeamM
        {
            get
            {
                if (Particulars == null) return 0f;
                if (Particulars.BeamM > 0f) return Particulars.BeamM;
                return Particulars.AntennaOffset.BeamM > 0f ? Particulars.AntennaOffset.BeamM : 0f;
            }
        }

        /// <summary>当船舶运动学状态随时间更新时触发（参数：控制器、当前样本、是否为 Seek）。</summary>
        public event Action<ShipController, TrackSample, bool> StateUpdated;

        /// <summary>构造船舶控制器并可选立即绑定仿真时钟。</summary>
        public ShipController(
            IShipTrack track,
            VesselParticulars particulars = null,
            IGeoConverter geoConverter = null,
            ISimClock clock = null,
            string displayName = null,
            string subtitleRole = null,
            string statusBadgeText = null)
        {
            if (track == null) throw new ArgumentNullException(nameof(track));
            _track = track;
            Particulars = particulars;
            _geoConverter = geoConverter ?? new LocalEnuGeoConverter();
            ControlMode = ControlMode.AisReplay;

            VesselId = !string.IsNullOrEmpty(track.VesselId)
                ? track.VesselId
                : (particulars != null && !string.IsNullOrEmpty(particulars.VesselId) ? particulars.VesselId : "Vessel");
            DisplayName = !string.IsNullOrEmpty(displayName)
                ? displayName
                : (particulars != null && !string.IsNullOrEmpty(particulars.Name) ? particulars.Name : VesselId);
            SubtitleRole = subtitleRole ?? (particulars != null ? particulars.VesselTypeCode : string.Empty);
            StatusBadgeText = statusBadgeText ?? (particulars != null ? particulars.LoadingCondition : "在航");

            EvaluateInternal(_track.StartTime, isSeek: true);

            if (clock != null)
            {
                BindClock(clock);
            }
        }

        /// <summary>绑定仿真时钟并立即按时钟当前时刻求值。</summary>
        public void BindClock(ISimClock clock)
        {
            if (ReferenceEquals(_clock, clock)) return;
            UnbindClock();
            _clock = clock;
            if (_clock != null)
            {
                _clock.RegisterTimeDriven(this);
                _clock.TimeChanged += OnClockTimeChanged;
                EvaluateInternal(_clock.CurrentTime, isSeek: true);
            }
        }

        /// <summary>解除与当前仿真时钟的订阅绑定。</summary>
        public void UnbindClock()
        {
            if (_clock != null)
            {
                _clock.TimeChanged -= OnClockTimeChanged;
                _clock.UnregisterTimeDriven(this);
                _clock = null;
            }
        }

        /// <summary>替换底层航迹并刷新当前状态。</summary>
        public void SetTrack(IShipTrack track)
        {
            if (track == null) throw new ArgumentNullException(nameof(track));
            _track = track;
            SimTime evalTime = _clock != null ? _clock.CurrentTime : (_hasEvaluated ? _lastEvaluatedTime : _track.StartTime);
            EvaluateInternal(evalTime, isSeek: true);
        }

        /// <summary>绑定航迹并指定运动控制模式（实现 IShipController）。</summary>
        public void BindTrack(IShipTrack track, ControlMode mode = ControlMode.AisReplay)
        {
            ControlMode = mode;
            SetTrack(track);
        }

        /// <summary>纯函数查询任意时刻该船的运动学状态（实现 IShipController）。</summary>
        public TrackSample SampleStatePure(SimTime time)
        {
            return SampleStateAt(time);
        }

        /// <summary>查询任意仿真时刻的船舶运动学样本（若与当前已求值时刻相同则直接返回缓存）。</summary>
        public TrackSample SampleStateAt(SimTime time)
        {
            if (_hasEvaluated && Math.Abs(time.Seconds - _lastEvaluatedTime.Seconds) <= 1e-7)
            {
                return _currentSample;
            }
            return _track.SampleAt(time);
        }

        /// <summary>计算指定仿真时刻船舶在 Unity 世界坐标系中的双精度位置。</summary>
        public Double3 GetUnityPositionAt(SimTime time)
        {
            TrackSample sample = SampleStateAt(time);
            return _geoConverter.EnuToUnityWorld(sample.EnuCenter);
        }

        /// <inheritdoc />
        public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            EvaluateInternal(currentTime, isSeek);
        }

        private void OnClockTimeChanged(SimTime time)
        {
            if (!_hasEvaluated || Math.Abs(time.Seconds - _lastEvaluatedTime.Seconds) > 1e-7)
            {
                EvaluateInternal(time, isSeek: false);
            }
        }

        private void EvaluateInternal(SimTime time, bool isSeek)
        {
            _lastEvaluatedTime = time;
            _hasEvaluated = true;
            _lastUpdateWasSeek = isSeek;

            TimeGapSpan gap;
            _isInTimeGap = _track.IsInTimeGap(time, out gap);
            _currentTimeGap = gap;

            TrackSample sample;
            _isVisible = _track.TrySampleAt(time, out sample);
            _currentSample = sample;
            _currentUnityPosition = _geoConverter.EnuToUnityWorld(_currentSample.EnuCenter);

            StateUpdated?.Invoke(this, _currentSample, isSeek);
        }

        /// <inheritdoc />
        public void Dispose()
        {
            UnbindClock();
        }
    }
}
