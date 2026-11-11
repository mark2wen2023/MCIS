using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using UnityEngine;
using UnityEngine.UIElements;

namespace Mcis.UI.MiniMap
{
    /// <summary>
    /// 基于 UI Toolkit <see cref="Painter2D"/> 的 ECDIS 风格 2D 海图小地图自定义元素（对应 ARCHITECTURE.md 4.10 与 5.3.11 节，目标 Unity 6.0 LTS）。
    /// 在 <see cref="VisualElement.generateVisualContent"/> 中绘制网格、双船完整航迹、当前位置船首向三角、CPA 连线，并支持自适应范围。
    /// </summary>
    [UxmlElement]
    public partial class MiniMapElement : VisualElement, IMiniMap
    {
        private readonly List<TrackSample> _ownTrackSamples = new List<TrackSample>();
        private readonly List<TrackSample> _targetTrackSamples = new List<TrackSample>();
        private readonly List<TimeGapSpan> _ownTimeGaps = new List<TimeGapSpan>();
        private readonly List<TimeGapSpan> _targetTimeGaps = new List<TimeGapSpan>();

        private TrackSample _ownCurrent;
        private TrackSample _targetCurrent;
        private bool _hasOwnCurrent;
        private bool _hasTargetCurrent;
        private CpaResult? _currentCpa;
        private SimTime _currentTime = SimTime.Zero;

        private EnuPosition _centerEnu = EnuPosition.Zero;
        private float _metersPerPixel = 20.0f;
        private bool _isFollowingOwnVessel;
        private bool _autoFitPending = true;
        private float _autoFitPaddingRatio = 0.15f;
        private MiniMapLayers _visibleLayers = MiniMapLayers.All;

        private bool _isDragging;
        private Vector2 _dragStartPos;
        private EnuPosition _dragStartCenterEnu;

        /// <summary>用户点击小地图上航迹附近点时触发的时间跳转请求事件。</summary>
        public event Action<SimTime> TrackTimeClicked;

        /// <inheritdoc />
        public EnuPosition CenterEnu
        {
            get { return _centerEnu; }
        }

        /// <inheritdoc />
        public float MetersPerPixel
        {
            get { return _metersPerPixel; }
        }

        /// <inheritdoc />
        [UxmlAttribute("follow-own-vessel")]
        public bool IsFollowingOwnVessel
        {
            get { return _isFollowingOwnVessel; }
            set { SetFollowOwnVessel(value); }
        }

        /// <summary>自适应全航迹缩放时的边距比例（UXML 属性 auto-fit-padding）。</summary>
        [UxmlAttribute("auto-fit-padding")]
        public float AutoFitPaddingRatio
        {
            get { return _autoFitPaddingRatio; }
            set { _autoFitPaddingRatio = Mathf.Clamp(value, 0.02f, 0.45f); }
        }

        /// <inheritdoc />
        public MiniMapLayers VisibleLayers
        {
            get { return _visibleLayers; }
            set
            {
                if (_visibleLayers != value)
                {
                    _visibleLayers = value;
                    MarkDirtyRepaint();
                }
            }
        }

        /// <summary>构造 2D 小地图自定义视觉元素。</summary>
        public MiniMapElement()
        {
            AddToClassList("minimap-canvas");
            pickingMode = PickingMode.Position;
            generateVisualContent += OnGenerateVisualContent;

            RegisterCallback<GeometryChangedEvent>(OnGeometryChanged);
            RegisterCallback<WheelEvent>(OnWheelZoom);
            RegisterCallback<PointerDownEvent>(OnPointerDown);
            RegisterCallback<PointerMoveEvent>(OnPointerMove);
            RegisterCallback<PointerUpEvent>(OnPointerUp);
        }

        /// <summary>设置双船完整航迹（<see cref="IShipTrack"/>）并自动计算适配范围。</summary>
        public void SetTracks(IShipTrack ownTrack, IShipTrack targetTrack, bool autoFit = true)
        {
            _ownTrackSamples.Clear();
            _ownTimeGaps.Clear();
            if (ownTrack != null)
            {
                if (ownTrack.CleanedSamples != null)
                    _ownTrackSamples.AddRange(ownTrack.CleanedSamples);
                if (ownTrack.TimeGaps != null)
                    _ownTimeGaps.AddRange(ownTrack.TimeGaps);
            }

            _targetTrackSamples.Clear();
            _targetTimeGaps.Clear();
            if (targetTrack != null)
            {
                if (targetTrack.CleanedSamples != null)
                    _targetTrackSamples.AddRange(targetTrack.CleanedSamples);
                if (targetTrack.TimeGaps != null)
                    _targetTimeGaps.AddRange(targetTrack.TimeGaps);
            }

            if (autoFit)
            {
                ZoomToFitAllTracks(_autoFitPaddingRatio);
            }
            else
            {
                MarkDirtyRepaint();
            }
        }

        /// <summary>直接设置双船离散航迹点列表（无 IShipTrack 实例时的轻量重载）。</summary>
        public void SetTrackSamples(
            IReadOnlyList<TrackSample> ownSamples,
            IReadOnlyList<TrackSample> targetSamples,
            bool autoFit = true)
        {
            _ownTrackSamples.Clear();
            _ownTimeGaps.Clear();
            if (ownSamples != null)
            {
                for (int i = 0; i < ownSamples.Count; i++) _ownTrackSamples.Add(ownSamples[i]);
            }

            _targetTrackSamples.Clear();
            _targetTimeGaps.Clear();
            if (targetSamples != null)
            {
                for (int i = 0; i < targetSamples.Count; i++) _targetTrackSamples.Add(targetSamples[i]);
            }

            if (autoFit)
            {
                ZoomToFitAllTracks(_autoFitPaddingRatio);
            }
            else
            {
                MarkDirtyRepaint();
            }
        }

        /// <summary>更新当前仿真时刻、两船实时位置/航向及 CPA 计算结果，触发重绘。</summary>
        public void UpdateState(
            SimTime currentTime,
            TrackSample ownSample,
            TrackSample targetSample,
            CpaResult? cpaResult)
        {
            _currentTime = currentTime;
            _ownCurrent = ownSample;
            _targetCurrent = targetSample;
            _hasOwnCurrent = true;
            _hasTargetCurrent = true;
            _currentCpa = cpaResult;

            if (_isFollowingOwnVessel)
            {
                _centerEnu = ownSample.EnuCenter;
            }
            else if (_autoFitPending)
            {
                RecomputeAutoFitBounds(_autoFitPaddingRatio);
            }

            MarkDirtyRepaint();
        }
    }
}
