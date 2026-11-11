using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Simulation;
using UnityEngine;
using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    /// <summary>
    /// 底部仿真时间轴控制栏组件（对应 ARCHITECTURE.md 5.3.5 与 9.2 节，目标 Unity 6.0 LTS）。
    /// 提供播放/暂停、0.5x–16x 倍速按钮组、可拖动进度条 Seek、关键事件标记跳转及等宽时间显示。
    /// </summary>
    [UxmlElement]
    public partial class TimelineBar : VisualElement
    {
        private static readonly float[] SupportedSpeeds = new float[] { 0.5f, 1.0f, 2.0f, 4.0f, 8.0f, 16.0f };
        private static readonly string[] SpeedButtonNames = new string[]
        {
            "btn-speed-0_5", "btn-speed-1", "btn-speed-2", "btn-speed-4", "btn-speed-8", "btn-speed-16"
        };

        private ISimClock _clock;
        private DateTimeOffset _caseEpochUtc = new DateTimeOffset(2026, 5, 18, 6, 15, 0, TimeSpan.Zero);
        private int _displayTzMinutes = 480;
        private SimTime? _keyCpaOrCollisionTime;

        private VisualElement _markersLayer;
        private Slider _scrubber;
        private Button _playBtn;
        private Button _stepBackBtn;
        private Button _stepFwdBtn;
        private Button _jumpCpaBtn;
        private Button _resetBtn;
        private Label _elapsedLabel;
        private Label _durationLabel;
        private Label _utcLabel;
        private readonly List<Button> _speedButtons = new List<Button>(6);
        private readonly List<TimelineMarker> _markers = new List<TimelineMarker>();

        private bool _isBound;
        private bool _isUpdatingFromClock;
        private bool _isPointerScrubbing;

        /// <summary>用户点击关键事件或最小会遇点按钮时触发的回调（可选）。</summary>
        public event Action<SimTime> MarkerSeekRequested;

        /// <summary>构造时间轴控制栏。</summary>
        public TimelineBar()
        {
            AddToClassList("timeline-dock");
            RegisterCallback<AttachToPanelEvent>(OnAttachToPanel);
        }

        private void OnAttachToPanel(AttachToPanelEvent evt)
        {
            EnsureBound();
        }

        /// <summary>绑定 <see cref="ISimClock"/> 时钟与案件纪元显示参数。</summary>
        public void BindClock(
            ISimClock clock,
            DateTimeOffset caseEpochUtc,
            int displayTimeZoneOffsetMinutes = 480,
            SimTime? keyJumpTime = null)
        {
            EnsureBound();
            UnbindClock();

            _clock = clock;
            _caseEpochUtc = caseEpochUtc;
            _displayTzMinutes = displayTimeZoneOffsetMinutes;
            _keyCpaOrCollisionTime = keyJumpTime;

            if (_clock != null)
            {
                _clock.TimeChanged += OnClockTimeChanged;
                _clock.StateChanged += OnClockStateChanged;
                SyncRangeAndStateFromClock();
            }
        }

        /// <summary>解除与仿真时钟的事件订阅。</summary>
        public void UnbindClock()
        {
            if (_clock != null)
            {
                _clock.TimeChanged -= OnClockTimeChanged;
                _clock.StateChanged -= OnClockStateChanged;
                _clock = null;
            }
        }

        /// <summary>设置一键跳转的关键时间点（如最小 DCPA 或碰撞时刻）。</summary>
        public void SetKeyJumpTime(SimTime time, string buttonLabel = null)
        {
            EnsureBound();
            _keyCpaOrCollisionTime = time;
            if (_jumpCpaBtn != null && !string.IsNullOrEmpty(buttonLabel))
            {
                _jumpCpaBtn.text = buttonLabel;
            }
        }

        /// <summary>设置并渲染时间轴上的关键事件标记列表（如最小会遇点、危险区间、碰撞、ECFC 事件）。</summary>
        public void SetMarkers(IReadOnlyList<TimelineMarker> markers)
        {
            EnsureBound();
            _markers.Clear();
            if (markers != null)
            {
                for (int i = 0; i < markers.Count; i++)
                {
                    _markers.Add(markers[i]);
                }
            }
            RebuildMarkerElements();
        }

        /// <summary>根据当前仿真时间刷新进度条与等宽时间标签。</summary>
        public void RefreshTimeDisplay(SimTime currentTime)
        {
            EnsureBound();
            double startSec = _clock != null ? _clock.StartTime.Seconds : 0.0;
            double endSec = _clock != null ? _clock.EndTime.Seconds : 900.0;
            double durationSec = Math.Max(0.001, endSec - startSec);
            double elapsedSec = Math.Max(0.0, currentTime.Seconds - startSec);

            if (_scrubber != null && !_isPointerScrubbing)
            {
                _isUpdatingFromClock = true;
                _scrubber.lowValue = (float)startSec;
                _scrubber.highValue = (float)endSec;
                _scrubber.SetValueWithoutNotify((float)currentTime.Seconds);
                _isUpdatingFromClock = false;
            }

            if (_elapsedLabel != null)
                _elapsedLabel.text = HudFormatters.FormatElapsedMinSec(elapsedSec);
            if (_durationLabel != null)
                _durationLabel.text = HudFormatters.FormatElapsedMinSec(durationSec);
            if (_utcLabel != null)
            {
                DateTimeOffset localDt = currentTime.ToUtc(_caseEpochUtc).ToOffset(TimeSpan.FromMinutes(_displayTzMinutes));
                _utcLabel.text = localDt.ToString("HH:mm:ss", CultureInfo.InvariantCulture);
            }
        }

        /// <summary>刷新播放/暂停按钮状态与倍速高亮。</summary>
        public void RefreshPlaybackState()
        {
            EnsureBound();
            if (_clock == null) return;

            if (_playBtn != null)
            {
                _playBtn.text = _clock.IsPlaying ? "⏸ 暂停" : "▶ 播放";
            }

            float activeRate = _clock.PlaybackRate;
            for (int i = 0; i < _speedButtons.Count && i < SupportedSpeeds.Length; i++)
            {
                Button btn = _speedButtons[i];
                if (btn == null) continue;
                bool isMatch = Mathf.Abs(activeRate - SupportedSpeeds[i]) < 0.05f;
                btn.EnableInClassList("active", isMatch);
            }
        }
    }
}
