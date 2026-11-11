using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Models;

namespace Mcis.Simulation
{
    public sealed partial class SimClock
    {
        /// <inheritdoc />
        public void RegisterTimeDriven(ITimeDriven driven)
        {
            if (driven == null || _timeDrivenSystems.Contains(driven))
            {
                return;
            }

            int insertIndex = _timeDrivenSystems.Count;
            for (int i = 0; i < _timeDrivenSystems.Count; i++)
            {
                if (driven.ExecutionPriority < _timeDrivenSystems[i].ExecutionPriority)
                {
                    insertIndex = i;
                    break;
                }
            }
            _timeDrivenSystems.Insert(insertIndex, driven);
        }

        /// <inheritdoc />
        public void UnregisterTimeDriven(ITimeDriven driven)
        {
            if (driven == null)
            {
                return;
            }
            _timeDrivenSystems.Remove(driven);
        }

        /// <summary>注册时间轴标记提供者。</summary>
        public void RegisterMarkerProvider(ITimelineMarkerProvider provider)
        {
            if (provider == null || _markerProviders.Contains(provider))
            {
                return;
            }
            _markerProviders.Add(provider);
        }

        /// <summary>注销时间轴标记提供者。</summary>
        public void UnregisterMarkerProvider(ITimelineMarkerProvider provider)
        {
            if (provider == null)
            {
                return;
            }
            _markerProviders.Remove(provider);
        }

        /// <summary>直接设置静态时间轴标记列表。</summary>
        public void SetMarkers(IEnumerable<TimelineMarker> markers)
        {
            _manualMarkers.Clear();
            if (markers != null)
            {
                _manualMarkers.AddRange(markers);
            }
        }

        /// <inheritdoc />
        public void JumpToNextMarker(string categoryFilter = null)
        {
            List<TimelineMarker> allMarkers = CollectAllMarkers(categoryFilter);
            long bestTicks = long.MaxValue;
            bool found = false;

            for (int i = 0; i < allMarkers.Count; i++)
            {
                long markerTicks = ClampTicks(SecondsToTicks(allMarkers[i].Time.Seconds));
                if (markerTicks > _currentTicks && markerTicks < bestTicks)
                {
                    bestTicks = markerTicks;
                    found = true;
                }
            }

            if (found)
            {
                ApplyTimeJump(bestTicks, notifyIfUnchanged: false);
            }
        }

        /// <inheritdoc />
        public void JumpToPreviousMarker(string categoryFilter = null)
        {
            List<TimelineMarker> allMarkers = CollectAllMarkers(categoryFilter);
            long bestTicks = long.MinValue;
            bool found = false;

            for (int i = 0; i < allMarkers.Count; i++)
            {
                long markerTicks = ClampTicks(SecondsToTicks(allMarkers[i].Time.Seconds));
                if (markerTicks < _currentTicks && markerTicks > bestTicks)
                {
                    bestTicks = markerTicks;
                    found = true;
                }
            }

            if (found)
            {
                ApplyTimeJump(bestTicks, notifyIfUnchanged: false);
            }
        }

        private List<TimelineMarker> CollectAllMarkers(string categoryFilter)
        {
            var result = new List<TimelineMarker>();
            bool hasFilter = !string.IsNullOrEmpty(categoryFilter);

            for (int i = 0; i < _manualMarkers.Count; i++)
            {
                TimelineMarker m = _manualMarkers[i];
                if (!hasFilter || string.Equals(m.Category, categoryFilter, StringComparison.OrdinalIgnoreCase))
                {
                    result.Add(m);
                }
            }

            for (int p = 0; p < _markerProviders.Count; p++)
            {
                IReadOnlyList<TimelineMarker> list = _markerProviders[p].GetMarkers();
                if (list == null)
                {
                    continue;
                }
                for (int i = 0; i < list.Count; i++)
                {
                    TimelineMarker m = list[i];
                    if (!hasFilter || string.Equals(m.Category, categoryFilter, StringComparison.OrdinalIgnoreCase))
                    {
                        result.Add(m);
                    }
                }
            }

            return result;
        }

        private long ClampTicks(long ticks)
        {
            if (ticks < _startTicks)
            {
                return _startTicks;
            }
            if (ticks > _endTicks)
            {
                return _endTicks;
            }
            return ticks;
        }

        private void TransitionState(SimClockState newState)
        {
            if (_state == newState)
            {
                return;
            }
            _state = newState;
            StateChanged?.Invoke(_state);
        }

        private void ApplyTimeJump(long targetTicks, bool notifyIfUnchanged)
        {
            long prevTicks = _currentTicks;
            _currentTicks = targetTicks;
            SimTime currTime = TicksToSimTime(_currentTicks);

            EvaluateDrivenSystems(currTime, currTime, isSeek: true);

            if (_currentTicks != prevTicks || notifyIfUnchanged)
            {
                TimeChanged?.Invoke(currTime);
            }
        }

        private void EvaluateDrivenSystems(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            for (int i = 0; i < _timeDrivenSystems.Count; i++)
            {
                _timeDrivenSystems[i].EvaluateTime(currentTime, previousTime, isSeek);
            }
        }
    }
}

namespace Mcis.Simulation.Clock
{
    /// <summary>
    /// 仿真时钟辅助常量与工厂入口（提供 Mcis.Simulation.Clock 子命名空间兼容支持）。
    /// </summary>
    public static class SimClockConstants
    {
        /// <summary>每秒整数 Tick 数（1 tick = 1 微秒）。</summary>
        public const long TicksPerSecond = SimClock.TicksPerSecond;

        /// <summary>默认单帧参考帧率（30 FPS）。</summary>
        public const int DefaultReferenceFps = 30;
    }
}
