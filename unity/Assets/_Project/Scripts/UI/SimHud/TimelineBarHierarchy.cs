using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Simulation;
using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    public partial class TimelineBar
    {
        /// <summary>确保内部 UI 节点已查询并绑定事件；若为空则自动构建子元素。</summary>
        public void EnsureBound()
        {
            if (_isBound && _scrubber != null)
            {
                return;
            }

            QueryElements();
            if (_scrubber == null)
            {
                BuildFallbackHierarchy();
                QueryElements();
            }

            WireCallbacks();
            _isBound = true;
        }

        private void QueryElements()
        {
            _markersLayer = this.Q<VisualElement>("tl-markers-layer");
            _scrubber = this.Q<Slider>("tl-scrubber");
            _playBtn = this.Q<Button>("btn-tl-play");
            _stepBackBtn = this.Q<Button>("btn-tl-step-back");
            _stepFwdBtn = this.Q<Button>("btn-tl-step-fwd");
            _jumpCpaBtn = this.Q<Button>("btn-tl-jump-cpa");
            _resetBtn = this.Q<Button>("btn-tl-reset");
            _elapsedLabel = this.Q<Label>("tl-elapsed-label");
            _durationLabel = this.Q<Label>("tl-duration-label");
            _utcLabel = this.Q<Label>("tl-utc-label");

            _speedButtons.Clear();
            for (int i = 0; i < SpeedButtonNames.Length; i++)
            {
                _speedButtons.Add(this.Q<Button>(SpeedButtonNames[i]));
            }
        }

        private void WireCallbacks()
        {
            if (_playBtn != null)
                _playBtn.clicked += OnPlayPauseClicked;
            if (_stepBackBtn != null)
                _stepBackBtn.clicked += () => { if (_clock != null) _clock.StepBackward(10.0); };
            if (_stepFwdBtn != null)
                _stepFwdBtn.clicked += () => { if (_clock != null) _clock.StepForward(10.0); };
            if (_jumpCpaBtn != null)
                _jumpCpaBtn.clicked += OnJumpKeyEventClicked;
            if (_resetBtn != null)
                _resetBtn.clicked += () => { if (_clock != null) _clock.Stop(); };

            for (int i = 0; i < _speedButtons.Count && i < SupportedSpeeds.Length; i++)
            {
                Button btn = _speedButtons[i];
                float speed = SupportedSpeeds[i];
                if (btn != null)
                {
                    btn.clicked += () => OnSpeedButtonClicked(speed);
                }
            }

            if (_scrubber != null)
            {
                _scrubber.RegisterValueChangedCallback(OnScrubberValueChanged);
                _scrubber.RegisterCallback<PointerDownEvent>(OnScrubberPointerDown, TrickleDown.TrickleDown);
                _scrubber.RegisterCallback<PointerUpEvent>(OnScrubberPointerUp, TrickleDown.TrickleDown);
                _scrubber.RegisterCallback<PointerCaptureOutEvent>(OnScrubberCaptureOut);
            }
        }

        private void OnPlayPauseClicked()
        {
            if (_clock == null) return;
            if (_clock.IsPlaying)
                _clock.Pause();
            else
                _clock.Play();
            RefreshPlaybackState();
        }

        private void OnJumpKeyEventClicked()
        {
            if (_clock == null) return;
            if (_keyCpaOrCollisionTime.HasValue)
            {
                _clock.Seek(_keyCpaOrCollisionTime.Value);
                MarkerSeekRequested?.Invoke(_keyCpaOrCollisionTime.Value);
            }
            else
            {
                _clock.JumpToNextMarker();
            }
        }

        private void OnSpeedButtonClicked(float rate)
        {
            if (_clock != null)
            {
                _clock.SetRate(rate);
            }
            RefreshPlaybackState();
        }

        private void OnScrubberPointerDown(PointerDownEvent evt)
        {
            if (_clock != null && !_isPointerScrubbing)
            {
                _isPointerScrubbing = true;
                _clock.BeginScrub();
            }
        }

        private void OnScrubberPointerUp(PointerUpEvent evt)
        {
            FinishPointerScrub();
        }

        private void OnScrubberCaptureOut(PointerCaptureOutEvent evt)
        {
            FinishPointerScrub();
        }

        private void FinishPointerScrub()
        {
            if (_isPointerScrubbing)
            {
                _isPointerScrubbing = false;
                if (_clock != null && _clock.State == SimClockState.Scrubbing)
                {
                    _clock.EndScrub();
                }
            }
        }

        private void OnScrubberValueChanged(ChangeEvent<float> evt)
        {
            if (_isUpdatingFromClock || _clock == null)
            {
                return;
            }

            SimTime target = new SimTime(evt.newValue);
            _clock.Seek(target);
            RefreshTimeDisplay(_clock.CurrentTime);
        }

        private void OnClockTimeChanged(SimTime time)
        {
            RefreshTimeDisplay(time);
        }

        private void OnClockStateChanged(SimClockState state)
        {
            RefreshPlaybackState();
        }

        private void SyncRangeAndStateFromClock()
        {
            if (_clock == null) return;
            RefreshTimeDisplay(_clock.CurrentTime);
            RefreshPlaybackState();
            RebuildMarkerElements();
        }

        private void RebuildMarkerElements()
        {
            if (_markersLayer == null) return;
            _markersLayer.Clear();

            double startSec = _clock != null ? _clock.StartTime.Seconds : 0.0;
            double endSec = _clock != null ? _clock.EndTime.Seconds : 900.0;
            double span = endSec - startSec;
            if (span <= 1e-6) return;

            for (int i = 0; i < _markers.Count; i++)
            {
                TimelineMarker m = _markers[i];
                double ratio = (m.Time.Seconds - startSec) / span;
                if (ratio < 0.0 || ratio > 1.0) continue;

                Button flag = new Button();
                flag.text = !string.IsNullOrEmpty(m.Label) ? m.Label : m.Category;
                flag.AddToClassList("tl-marker");
                flag.AddToClassList("mcis-mono");
                flag.AddToClassList(GetMarkerRiskClass(m.AssociatedRisk));
                flag.style.left = Length.Percent((float)(ratio * 100.0));

                SimTime markerTime = m.Time;
                flag.clicked += () =>
                {
                    if (_clock != null) _clock.Seek(markerTime);
                    MarkerSeekRequested?.Invoke(markerTime);
                };

                _markersLayer.Add(flag);
            }
        }

        private static string GetMarkerRiskClass(RiskLevel risk)
        {
            switch (risk)
            {
                case RiskLevel.Danger:
                    return "tl-marker-danger";
                case RiskLevel.Warning:
                    return "tl-marker-warning";
                default:
                    return "tl-marker-safe";
            }
        }
    }
}
