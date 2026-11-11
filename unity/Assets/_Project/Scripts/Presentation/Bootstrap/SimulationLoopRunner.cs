#if UNITY_5_3_OR_NEWER
using System;
using UnityEngine;
using Mcis.Simulation;

namespace Mcis.Presentation.Bootstrap
{
    /// <summary>
    /// 仿真主循环驱动器（MonoBehaviour）。
    /// 在 Unity 引擎的生命周期 Update 中按真实帧间隔调用 <see cref="ISimClock.Tick(double)"/>，
    /// 驱动确定性仿真时钟连续平滑推进。
    /// </summary>
    [AddComponentMenu("MCIS/Simulation/Simulation Loop Runner")]
    public sealed class SimulationLoopRunner : MonoBehaviour
    {
        [Tooltip("是否允许自动推进时钟")]
        [SerializeField] private bool _autoTick = true;

        [Tooltip("单帧最大允许步长（秒），防止极端卡顿或切出窗口时发生时间膨胀")]
        [SerializeField] private float _maxDeltaTimeSeconds = 0.25f;

        private ISimClock _clock;

        /// <summary>当前被驱动的仿真时钟实例。</summary>
        public ISimClock Clock
        {
            get { return _clock; }
            set { _clock = value; }
        }

        /// <summary>是否允许每帧自动调用 Tick。</summary>
        public bool AutoTick
        {
            get { return _autoTick; }
            set { _autoTick = value; }
        }

        /// <summary>单帧最大时间步长门限（秒）。</summary>
        public float MaxDeltaTimeSeconds
        {
            get { return _maxDeltaTimeSeconds; }
            set { _maxDeltaTimeSeconds = Mathf.Max(0.01f, value); }
        }

        /// <summary>绑定要驱动的仿真时钟。</summary>
        public void BindClock(ISimClock clock)
        {
            _clock = clock;
        }

        /// <summary>解绑当前仿真时钟。</summary>
        public void UnbindClock()
        {
            _clock = null;
        }

        private void Update()
        {
            if (!_autoTick || _clock == null)
            {
                return;
            }

            float dt = Time.unscaledDeltaTime;
            if (dt <= 0f || float.IsNaN(dt) || float.IsInfinity(dt))
            {
                return;
            }

            if (_maxDeltaTimeSeconds > 0f && dt > _maxDeltaTimeSeconds)
            {
                dt = _maxDeltaTimeSeconds;
            }

            _clock.Tick(dt);
        }

        private void OnDestroy()
        {
            _clock = null;
        }
    }
}
#endif
