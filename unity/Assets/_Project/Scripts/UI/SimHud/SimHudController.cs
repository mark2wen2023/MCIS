using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation;
using Mcis.Simulation.Cpa;
using Mcis.UI.MiniMap;
using UnityEngine;
using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    /// <summary>
    /// 主仿真 HUD 控制器（MonoBehaviour，挂载于含 <see cref="UIDocument"/> 的对象上）。
    /// 负责将 <see cref="ISimClock"/>、<see cref="ICpaService"/> 及双船状态数据源绑定至 <see cref="NavHud"/>、<see cref="TimelineBar"/> 与 <see cref="MiniMapElement"/>。
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public partial class SimHudController : MonoBehaviour, ITimeDriven
    {
        [SerializeField]
        [Tooltip("可选：指定 UIDocument；为空时自动获取同物体上的 UIDocument")]
        private UIDocument _uiDocument;

        [SerializeField]
        [Tooltip("显示时区相对 UTC 的分钟偏移（默认 +480 即 UTC+8 北京时间）")]
        private int _displayTimeZoneOffsetMinutes = 480;

        private ISimClock _clock;
        private ICpaService _cpaService;
        private IShipStateSource _ownSource;
        private IShipStateSource _targetSource;
        private DateTimeOffset _caseEpochUtc = new DateTimeOffset(2026, 5, 18, 6, 15, 0, TimeSpan.Zero);

        private NavHud _navHud;
        private TimelineBar _timelineBar;
        private MiniMapElement _miniMap;
        private Label _miniMapScaleLabel;
        private Button _miniMapFitBtn;
        private bool _uiInitialized;

        /// <summary>ITimeDriven 执行优先级（60 = UI/表现层）。</summary>
        public int ExecutionPriority
        {
            get { return 60; }
        }

        /// <summary>航行遥测与 CPA 告警 HUD 元素。</summary>
        public NavHud NavHudElement
        {
            get
            {
                EnsureUiInitialized();
                return _navHud;
            }
        }

        /// <summary>底部时间轴与倍速控制栏元素。</summary>
        public TimelineBar TimelineBarElement
        {
            get
            {
                EnsureUiInitialized();
                return _timelineBar;
            }
        }

        /// <summary>2D 矢量海图小地图元素。</summary>
        public MiniMapElement MiniMapElement
        {
            get
            {
                EnsureUiInitialized();
                return _miniMap;
            }
        }

        private void Awake()
        {
            if (_uiDocument == null)
            {
                _uiDocument = GetComponent<UIDocument>();
            }
        }

        private void OnEnable()
        {
            EnsureUiInitialized();
            if (_clock != null)
            {
                RefreshAll(_clock.CurrentTime);
            }
        }

        private void OnDestroy()
        {
            Unbind();
        }

        /// <summary>
        /// 绑定仿真时钟、CPA 服务与双船状态数据源（<see cref="IShipStateSource"/>）。
        /// </summary>
        public void Bind(
            ISimClock clock,
            ICpaService cpaService,
            IShipStateSource ownVessel,
            IShipStateSource targetVessel,
            DateTimeOffset? caseEpochUtc = null,
            int displayTimeZoneOffsetMinutes = 480)
        {
            Unbind();
            EnsureUiInitialized();

            _clock = clock;
            _cpaService = cpaService;
            _ownSource = ownVessel;
            _targetSource = targetVessel;
            if (caseEpochUtc.HasValue)
            {
                _caseEpochUtc = caseEpochUtc.Value;
            }
            _displayTimeZoneOffsetMinutes = displayTimeZoneOffsetMinutes;

            ConfigureBoundElements();
        }

        /// <summary>
        /// 直接使用领域层 <see cref="IShipTrack"/> 绑定仿真时钟、CPA 服务与双船轨迹的便捷重载。
        /// </summary>
        public void Bind(
            ISimClock clock,
            ICpaService cpaService,
            IShipTrack ownTrack,
            IShipTrack targetTrack,
            VesselParticulars ownParticulars = null,
            VesselParticulars targetParticulars = null,
            DateTimeOffset? caseEpochUtc = null,
            int displayTimeZoneOffsetMinutes = 480)
        {
            IShipStateSource ownSrc = ownTrack != null
                ? new ShipTrackStateSource(ownTrack, null, "本船 / 出港船", "压载出港", ownParticulars)
                : null;
            IShipStateSource tgtSrc = targetTrack != null
                ? new ShipTrackStateSource(targetTrack, null, "他船 / 进港船", "满载进港", targetParticulars)
                : null;

            Bind(clock, cpaService, ownSrc, tgtSrc, caseEpochUtc, displayTimeZoneOffsetMinutes);
        }

        /// <summary>解除与仿真时钟、CPA 服务的所有事件绑定。</summary>
        public void Unbind()
        {
            if (_clock != null)
            {
                _clock.TimeChanged -= OnClockTimeChanged;
                _clock.UnregisterTimeDriven(this);
            }
            if (_cpaService != null)
            {
                _cpaService.MarkersChanged -= OnCpaMarkersChanged;
            }
            if (_timelineBar != null)
            {
                _timelineBar.UnbindClock();
            }

            _clock = null;
            _cpaService = null;
            _ownSource = null;
            _targetSource = null;
        }

        /// <inheritdoc />
        public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            RefreshAll(currentTime);
        }
    }
}
