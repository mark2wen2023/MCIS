using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.UI.MiniMap;
using UnityEngine;
using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    public partial class SimHudController
    {
        private void ConfigureBoundElements()
        {
            if (_navHud != null && _ownSource != null && _targetSource != null)
            {
                string ownTitle = FormatCardHeader(_ownSource.DisplayName, _ownSource.SubtitleRole, "LILY 轮 (本船)");
                string tgtTitle = FormatCardHeader(_targetSource.DisplayName, _targetSource.SubtitleRole, "MARY 轮 (他船)");
                _navHud.SetVesselHeaders(
                    ownTitle,
                    _ownSource.StatusBadgeText ?? "在航",
                    tgtTitle,
                    _targetSource.StatusBadgeText ?? "在航");
            }

            if (_miniMap != null)
            {
                _miniMap.SetTracks(
                    _ownSource != null ? _ownSource.Track : null,
                    _targetSource != null ? _targetSource.Track : null,
                    true);
            }

            SimTime? minDistTime = null;
            if (_cpaService != null)
            {
                minDistTime = _cpaService.GetMinDistanceTime();
                _cpaService.MarkersChanged += OnCpaMarkersChanged;
            }

            if (_timelineBar != null)
            {
                _timelineBar.BindClock(_clock, _caseEpochUtc, _displayTimeZoneOffsetMinutes, minDistTime);
                if (_cpaService != null)
                {
                    IReadOnlyList<TimelineMarker> markers = _cpaService.GetMarkers();
                    _timelineBar.SetMarkers(markers);
                }
            }

            if (_clock != null)
            {
                _clock.TimeChanged += OnClockTimeChanged;
                _clock.RegisterTimeDriven(this);
                RefreshAll(_clock.CurrentTime);
            }
        }

        private void OnClockTimeChanged(SimTime time)
        {
            RefreshAll(time);
        }

        private void OnCpaMarkersChanged()
        {
            if (_timelineBar != null && _cpaService != null)
            {
                _timelineBar.SetMarkers(_cpaService.GetMarkers());
            }
        }

        private void OnMiniMapTimeClicked(SimTime targetTime)
        {
            if (_clock != null)
            {
                _clock.Seek(targetTime);
            }
        }

        /// <summary>在给定仿真时刻刷新 NavHud、TimelineBar 与 MiniMap。</summary>
        public void RefreshAll(SimTime time)
        {
            if (!_uiInitialized)
            {
                EnsureUiInitialized();
            }

            TrackSample ownSample = _ownSource != null ? _ownSource.SampleStateAt(time) : default;
            TrackSample targetSample = _targetSource != null ? _targetSource.SampleStateAt(time) : default;

            if (_navHud != null)
            {
                if (_ownSource != null) _navHud.UpdateOwnVessel(ownSample);
                if (_targetSource != null) _navHud.UpdateTargetVessel(targetSample);
            }

            CpaResult? cpaOpt = null;
            if (_cpaService != null)
            {
                CpaResult cpa = _cpaService.GetAt(time);
                cpaOpt = cpa;
                if (_navHud != null)
                {
                    _navHud.UpdateCpa(cpa, time, _caseEpochUtc, _displayTimeZoneOffsetMinutes);
                }
            }

            if (_miniMap != null)
            {
                _miniMap.UpdateState(time, ownSample, targetSample, cpaOpt);
                if (_miniMapScaleLabel != null)
                {
                    _miniMapScaleLabel.text = string.Format(
                        CultureInfo.InvariantCulture,
                        "比例: {0:0.0} m/px",
                        _miniMap.MetersPerPixel);
                }
            }

            if (_timelineBar != null)
            {
                _timelineBar.RefreshTimeDisplay(time);
            }
        }

        private void EnsureUiInitialized()
        {
            if (_uiInitialized && _navHud != null && _timelineBar != null && _miniMap != null)
            {
                return;
            }

            if (_uiDocument == null)
            {
                _uiDocument = GetComponent<UIDocument>();
            }
            if (_uiDocument == null || _uiDocument.rootVisualElement == null)
            {
                return;
            }

            VisualElement root = _uiDocument.rootVisualElement;
            _navHud = root.Q<NavHud>("nav-hud") ?? root.Q<NavHud>();
            _timelineBar = root.Q<TimelineBar>("timeline-bar") ?? root.Q<TimelineBar>();
            _miniMap = root.Q<MiniMapElement>("minimap-canvas") ?? root.Q<MiniMapElement>();
            _miniMapScaleLabel = root.Q<Label>("minimap-scale-label");
            _miniMapFitBtn = root.Q<Button>("btn-minimap-fit");

            if (_navHud == null || _timelineBar == null || _miniMap == null)
            {
                BuildFallbackRootLayout(root);
            }

            if (_navHud != null) _navHud.EnsureBound();
            if (_timelineBar != null) _timelineBar.EnsureBound();

            if (_miniMap != null)
            {
                _miniMap.TrackTimeClicked -= OnMiniMapTimeClicked;
                _miniMap.TrackTimeClicked += OnMiniMapTimeClicked;
            }

            if (_miniMapFitBtn != null && _miniMap != null)
            {
                _miniMapFitBtn.clicked += () => _miniMap.ZoomToFitAllTracks();
            }

            _uiInitialized = true;
        }

        private void BuildFallbackRootLayout(VisualElement root)
        {
            VisualElement screen = new VisualElement { name = "sim-hud-screen", pickingMode = PickingMode.Ignore };
            screen.AddToClassList("sim-hud-screen");

            VisualElement topBar = new VisualElement { name = "sim-hud-top-bar", pickingMode = PickingMode.Ignore };
            topBar.AddToClassList("sim-hud-top-bar");

            _navHud = new NavHud { name = "nav-hud" };
            _navHud.AddToClassList("sim-hud-nav-region");

            VisualElement rightRegion = new VisualElement { name = "sim-hud-right-region" };
            rightRegion.AddToClassList("sim-hud-right-region");

            VisualElement mapBox = new VisualElement { name = "minimap-box" };
            mapBox.AddToClassList("minimap-box");

            VisualElement mapHeader = new VisualElement();
            mapHeader.AddToClassList("minimap-header");
            Label mapTitle = new Label("2D 全局航迹小地图 (MiniMap)");
            mapTitle.AddToClassList("minimap-title");
            Label mapHint = new Label("点击定位 · 滚轮缩放");
            mapHint.AddToClassList("minimap-hint");
            mapHint.AddToClassList("mcis-mono");
            mapHeader.Add(mapTitle);
            mapHeader.Add(mapHint);

            _miniMap = new MiniMapElement { name = "minimap-canvas" };

            VisualElement mapFooter = new VisualElement();
            mapFooter.AddToClassList("minimap-footer");
            _miniMapScaleLabel = new Label("比例尺: 自动适配") { name = "minimap-scale-label" };
            _miniMapScaleLabel.AddToClassList("minimap-scale-label");
            _miniMapScaleLabel.AddToClassList("mcis-mono");
            _miniMapFitBtn = new Button { name = "btn-minimap-fit", text = "⌖ 全景" };
            _miniMapFitBtn.AddToClassList("mcis-btn");
            _miniMapFitBtn.AddToClassList("minimap-fit-btn");
            mapFooter.Add(_miniMapScaleLabel);
            mapFooter.Add(_miniMapFitBtn);

            mapBox.Add(mapHeader);
            mapBox.Add(_miniMap);
            mapBox.Add(mapFooter);
            rightRegion.Add(mapBox);

            topBar.Add(_navHud);
            topBar.Add(rightRegion);

            VisualElement bottomBar = new VisualElement { name = "sim-hud-bottom-bar" };
            bottomBar.AddToClassList("sim-hud-bottom-bar");
            _timelineBar = new TimelineBar { name = "timeline-bar" };
            bottomBar.Add(_timelineBar);

            screen.Add(topBar);
            screen.Add(bottomBar);
            root.Add(screen);
        }

        private static string FormatCardHeader(string name, string role, string fallback)
        {
            if (string.IsNullOrEmpty(name)) return fallback;
            if (string.IsNullOrEmpty(role)) return name;
            return string.Concat(name, " (", role, ")");
        }
    }
}
