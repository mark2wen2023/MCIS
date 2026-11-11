using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Models;

namespace Mcis.Simulation
{
    public sealed partial class SimClock
    {
        private readonly List<ITimeDriven> _timeDrivenSystems = new List<ITimeDriven>();
        private readonly List<ITimelineMarkerProvider> _markerProviders = new List<ITimelineMarkerProvider>();
        private readonly List<TimelineMarker> _manualMarkers = new List<TimelineMarker>();

        /// <inheritdoc />
        public void Play()
        {
            TransitionState(SimClockState.Playing);
        }

        /// <inheritdoc />
        public void Pause()
        {
            TransitionState(SimClockState.Paused);
        }

        /// <summary>在播放与暂停之间切换。</summary>
        public void TogglePlayPause()
        {
            if (_state == SimClockState.Playing)
            {
                Pause();
            }
            else
            {
                Play();
            }
        }

        /// <inheritdoc />
        public void Stop()
        {
            TransitionState(SimClockState.Stopped);
            ApplyTimeJump(_startTicks, notifyIfUnchanged: false);
        }

        /// <inheritdoc />
        public void SetRate(float rate)
        {
            if (!IsSupportedRate(rate))
            {
                throw new ArgumentOutOfRangeException(
                    nameof(rate),
                    rate,
                    "Playback rate must be one of {0.25, 0.5, 1, 2, 4, 8, 16, 32}.");
            }

            if (Math.Abs(_playbackRate - rate) > 1e-6f)
            {
                _playbackRate = rate;
                RateChanged?.Invoke(_playbackRate);
            }
        }

        /// <summary>设置播放倍速（双精度重载）。</summary>
        public void SetRate(double rate)
        {
            SetRate((float)rate);
        }

        /// <inheritdoc />
        public void Seek(SimTime targetTime)
        {
            if (double.IsNaN(targetTime.Seconds) || double.IsInfinity(targetTime.Seconds))
            {
                throw new ArgumentOutOfRangeException(nameof(targetTime));
            }

            long targetTicks = ClampTicks(SecondsToTicks(targetTime.Seconds));
            ApplyTimeJump(targetTicks, notifyIfUnchanged: false);
        }

        /// <summary>跳转到指定仿真秒数（双精度重载）。</summary>
        public void Seek(double targetSeconds)
        {
            Seek(new SimTime(targetSeconds));
        }

        /// <inheritdoc />
        public void BeginScrub()
        {
            TransitionState(SimClockState.Scrubbing);
        }

        /// <inheritdoc />
        public void EndScrub()
        {
            if (_state == SimClockState.Scrubbing)
            {
                TransitionState(SimClockState.Paused);
            }
        }

        /// <inheritdoc />
        public void StepForward(double stepSeconds = DefaultStepSeconds)
        {
            if (double.IsNaN(stepSeconds) || double.IsInfinity(stepSeconds) || stepSeconds < 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(stepSeconds));
            }
            if (_state == SimClockState.Playing)
            {
                Pause();
            }

            long deltaTicks = SecondsToTicks(stepSeconds);
            long targetTicks = ClampTicks(_currentTicks + deltaTicks);
            ApplyTimeJump(targetTicks, notifyIfUnchanged: false);
        }

        /// <inheritdoc />
        public void StepBackward(double stepSeconds = DefaultStepSeconds)
        {
            if (double.IsNaN(stepSeconds) || double.IsInfinity(stepSeconds) || stepSeconds < 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(stepSeconds));
            }
            if (_state == SimClockState.Playing)
            {
                Pause();
            }

            long deltaTicks = SecondsToTicks(stepSeconds);
            long targetTicks = ClampTicks(_currentTicks - deltaTicks);
            ApplyTimeJump(targetTicks, notifyIfUnchanged: false);
        }

        /// <inheritdoc />
        public void StepFrames(int frameDelta, int referenceFps = 30)
        {
            if (referenceFps <= 0)
            {
                throw new ArgumentOutOfRangeException(nameof(referenceFps));
            }
            if (_state == SimClockState.Playing)
            {
                Pause();
            }

            long deltaTicks = (long)Math.Round(
                (double)frameDelta * TicksPerSecond / referenceFps,
                MidpointRounding.AwayFromZero);
            long targetTicks = ClampTicks(_currentTicks + deltaTicks);
            ApplyTimeJump(targetTicks, notifyIfUnchanged: false);
        }

        /// <inheritdoc />
        public void Tick(double unscaledDeltaSeconds)
        {
            if (_state != SimClockState.Playing && _state != SimClockState.OfflineRecording)
            {
                return;
            }
            if (double.IsNaN(unscaledDeltaSeconds) || double.IsInfinity(unscaledDeltaSeconds) || unscaledDeltaSeconds <= 0.0)
            {
                return;
            }

            long deltaTicks = SecondsToTicks(unscaledDeltaSeconds * _playbackRate);
            if (deltaTicks <= 0L)
            {
                return;
            }

            long prevTicks = _currentTicks;
            long nextTicks;
            if (IsLooping && _endTicks > _startTicks)
            {
                long candidate = prevTicks + deltaTicks;
                if (candidate > _endTicks)
                {
                    long span = _endTicks - _startTicks;
                    nextTicks = _startTicks + ((candidate - _startTicks) % span);
                }
                else
                {
                    nextTicks = candidate;
                }
            }
            else
            {
                nextTicks = ClampTicks(prevTicks + deltaTicks);
            }

            if (nextTicks == prevTicks)
            {
                return;
            }

            _currentTicks = nextTicks;
            SimTime prevTime = TicksToSimTime(prevTicks);
            SimTime currTime = TicksToSimTime(_currentTicks);
            EvaluateDrivenSystems(currTime, prevTime, isSeek: false);
            TimeChanged?.Invoke(currTime);
        }
    }
}
