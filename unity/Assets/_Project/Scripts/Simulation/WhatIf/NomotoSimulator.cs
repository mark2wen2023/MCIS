using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Damage;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>
    /// 可连续按时间求值的单船原航迹/反事实航迹。偏离时刻之前严格取原航迹，
    /// 偏离之后对固定步长积分结果做线性插值（航向按最短弧插值）。
    /// </summary>
    public sealed class WhatIfVessel
    {
        /// <summary>船舶标识。</summary>
        public string Id { get; }

        /// <summary>展示用船名（默认与 Id 相同）。</summary>
        public string DisplayName { get; }

        /// <summary>操纵模型参数。</summary>
        public ManeuverParams Params { get; }

        /// <summary>航迹起始仿真时间（秒）。</summary>
        public double StartSeconds { get; }

        /// <summary>航迹结束仿真时间（秒）。</summary>
        public double EndSeconds { get; }

        /// <summary>原始航迹采样函数（按仿真秒返回运动学状态）。</summary>
        public Func<double, KinematicState> Original { get; }

        /// <summary>构造单船原航迹。</summary>
        public WhatIfVessel(
            string id,
            ManeuverParams parameters,
            double startSeconds,
            double endSeconds,
            Func<double, KinematicState> original,
            string displayName = null)
        {
            if (string.IsNullOrWhiteSpace(id))
            {
                throw new ArgumentException("船舶标识不能为空。", nameof(id));
            }
            if (parameters == null)
            {
                throw new ArgumentNullException(nameof(parameters));
            }
            if (original == null)
            {
                throw new ArgumentNullException(nameof(original));
            }
            if (endSeconds < startSeconds)
            {
                throw new ArgumentException("结束时间不能早于起始时间。", nameof(endSeconds));
            }
            Id = id;
            DisplayName = string.IsNullOrWhiteSpace(displayName) ? id : displayName;
            Params = parameters;
            StartSeconds = startSeconds;
            EndSeconds = endSeconds;
            Original = original;
        }

        /// <summary>按仿真时间采样原航迹。</summary>
        public KinematicState SampleAt(double timeSeconds)
        {
            return Original(timeSeconds);
        }

        /// <summary>
        /// 由离散状态序列构造原航迹：按时间排序、线性插值、航向最短弧插值、范围外钳制。
        /// </summary>
        public static WhatIfVessel FromStates(
            string id,
            ManeuverParams parameters,
            IEnumerable<KinematicState> states,
            string displayName = null)
        {
            if (states == null)
            {
                throw new ArgumentNullException(nameof(states));
            }

            List<KinematicState> sorted = states.OrderBy(s => s.TimeSeconds).ToList();
            if (sorted.Count == 0)
            {
                throw new ArgumentException("状态序列不能为空。", nameof(states));
            }
            for (int i = 1; i < sorted.Count; i++)
            {
                if (Math.Abs(sorted[i].TimeSeconds - sorted[i - 1].TimeSeconds) <= 1e-9)
                {
                    throw new ArgumentException("状态序列存在重复时间戳。", nameof(states));
                }
            }

            KinematicState[] table = sorted.ToArray();
            double start = table[0].TimeSeconds;
            double end = table[table.Length - 1].TimeSeconds;

            Func<double, KinematicState> sampler = t =>
            {
                if (table.Length == 1 || t <= table[0].TimeSeconds)
                {
                    return WithTime(table[0], t);
                }
                if (t >= table[table.Length - 1].TimeSeconds)
                {
                    return WithTime(table[table.Length - 1], t);
                }

                int lo = FindBracket(table, t);
                KinematicState a = table[lo];
                KinematicState b = table[lo + 1];
                double span = b.TimeSeconds - a.TimeSeconds;
                double f = span > 1e-12 ? (t - a.TimeSeconds) / span : 0.0;
                KinematicState lerped = KinematicState.Lerp(a, b, f);
                return new KinematicState(
                    t, lerped.EastM, lerped.NorthM, lerped.HeadingDeg,
                    lerped.SpeedKn, lerped.RotDegPerSec, lerped.RudderDeg);
            };

            return new WhatIfVessel(id, parameters, start, end, sampler, displayName);
        }

        /// <summary>
        /// 由 IShipTrack 构造原航迹：使用 SampleAt 的船中心 ENU、船首向与 SOG（m/s 转 kn）。
        /// </summary>
        public static WhatIfVessel FromShipTrack(
            string id,
            ManeuverParams parameters,
            IShipTrack track,
            string displayName = null)
        {
            if (track == null)
            {
                throw new ArgumentNullException(nameof(track));
            }
            double start = track.StartTime.Seconds;
            double end = track.EndTime.Seconds;
            if (end < start)
            {
                throw new ArgumentException("航迹结束时间早于起始时间。", nameof(track));
            }

            Func<double, KinematicState> sampler = t =>
            {
                double clamped = t;
                if (clamped < start) clamped = start;
                if (clamped > end) clamped = end;
                TrackSample sample = track.SampleAt(new SimTime(clamped));
                return new KinematicState(
                    t,
                    sample.EnuCenter.EastM,
                    sample.EnuCenter.NorthM,
                    sample.HdgDeg,
                    sample.SogMps / VesselMotionState.MpsPerKnot,
                    sample.RotDegPerSec,
                    0.0);
            };

            return new WhatIfVessel(
                string.IsNullOrEmpty(id) ? track.VesselId : id,
                parameters, start, end, sampler, displayName);
        }

        private static int FindBracket(KinematicState[] table, double t)
        {
            int lo = 0;
            int hi = table.Length - 2;
            while (lo <= hi)
            {
                int mid = lo + ((hi - lo) >> 1);
                if (t < table[mid].TimeSeconds)
                {
                    hi = mid - 1;
                }
                else if (t > table[mid + 1].TimeSeconds)
                {
                    lo = mid + 1;
                }
                else
                {
                    return mid;
                }
            }
            return Math.Max(0, Math.Min(table.Length - 2, lo));
        }

        private static KinematicState WithTime(KinematicState state, double timeSeconds)
        {
            return new KinematicState(
                timeSeconds, state.EastM, state.NorthM, state.HeadingDeg,
                state.SpeedKn, state.RotDegPerSec, state.RudderDeg);
        }
    }

    /// <summary>
    /// 固定步长一阶 Nomoto 操纵模拟器。
    /// 模型：T·dr/dt + r = K·(u/u_ref)·δ，dψ/dt = r，du/dt = (u_target − u)/τ，
    /// δ 以舵机速率限制趋近指令舵角；采用四阶 Runge–Kutta 积分。
    /// </summary>
    public static class NomotoSimulator
    {
        /// <summary>航向保持 PD 比例增益（度舵角/度误差）。</summary>
        public const double HeadingHoldProportionalGain = 1.2;

        /// <summary>航向保持 PD 微分增益（度舵角/(度/秒)）。</summary>
        public const double HeadingHoldDerivativeGain = 10.0;

        /// <summary>
        /// 从初始状态开始按固定步长模拟到 endSeconds。
        /// 返回的状态序列包含初始时刻，并在 endSeconds 处结束。
        /// </summary>
        public static IReadOnlyList<KinematicState> Simulate(
            KinematicState initial,
            ManeuverParams parameters,
            IReadOnlyList<Intervention> interventions,
            double endSeconds,
            double dtSeconds = 0.1)
        {
            if (parameters == null)
            {
                throw new ArgumentNullException(nameof(parameters));
            }
            if (double.IsNaN(dtSeconds) || double.IsInfinity(dtSeconds) || dtSeconds <= 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(dtSeconds), "积分步长必须为有限正数。");
            }

            IReadOnlyList<string> errors = parameters.Validate();
            if (errors.Count > 0)
            {
                throw new ArgumentException("操纵参数非法：" + string.Join("；", errors), nameof(parameters));
            }

            List<Intervention> ordered = new List<Intervention>();
            if (interventions != null)
            {
                for (int i = 0; i < interventions.Count; i++)
                {
                    if (interventions[i] != null)
                    {
                        ordered.Add(interventions[i]);
                    }
                }
            }
            ordered.Sort((a, b) =>
            {
                int cmp = a.ExecutionTimeSeconds.CompareTo(b.ExecutionTimeSeconds);
                if (cmp != 0) return cmp;
                return a.TimeSeconds.CompareTo(b.TimeSeconds);
            });

            double t = initial.TimeSeconds;
            double east = initial.EastM;
            double north = initial.NorthM;
            double psi = initial.HeadingDeg;
            double r = initial.RotDegPerSec;
            double u = Math.Max(initial.SpeedKn, parameters.MinSpeedKn);
            double rudder = Clamp(initial.RudderDeg, -parameters.MaxRudderDeg, parameters.MaxRudderDeg);

            double speedTarget = u;
            double speedTau = parameters.SpeedTimeConstantSec;
            double rudderCommand = rudder;

            bool turning = false;
            double turnStartPsi = 0.0;
            double turnChangeDeg = 0.0;
            bool holding = false;
            double holdTargetPsi = psi;

            bool anchorDropped = false;
            double anchorEffectiveTime = double.PositiveInfinity;
            AnchorSide anchorSide = AnchorSide.Both;

            List<KinematicState> result = new List<KinematicState>();
            result.Add(new KinematicState(t, east, north, psi, u, r, rudder));
            if (endSeconds <= t)
            {
                return new ReadOnlyCollection<KinematicState>(result);
            }

            int nextIntervention = 0;
            while (t < endSeconds - 1e-12)
            {
                while (nextIntervention < ordered.Count &&
                       ordered[nextIntervention].ExecutionTimeSeconds <= t + 1e-9)
                {
                    ApplyIntervention(
                        ordered[nextIntervention], psi, u,
                        parameters, ref speedTarget, ref speedTau,
                        ref rudderCommand, ref turning, ref turnStartPsi,
                        ref turnChangeDeg, ref holding, ref holdTargetPsi,
                        ref anchorDropped, ref anchorEffectiveTime, ref anchorSide);
                    nextIntervention++;
                }

                if (turning)
                {
                    double delta = psi - turnStartPsi;
                    bool reached = turnChangeDeg >= 0.0
                        ? delta >= turnChangeDeg - 1e-6
                        : delta <= turnChangeDeg + 1e-6;
                    if (reached)
                    {
                        holdTargetPsi = turnStartPsi + turnChangeDeg;
                        turning = false;
                        holding = true;
                    }
                }

                if (holding)
                {
                    double err = KinematicState.NormalizeDeg180(holdTargetPsi - psi);
                    rudderCommand = Clamp(
                        HeadingHoldProportionalGain * err - HeadingHoldDerivativeGain * r,
                        -parameters.MaxRudderDeg,
                        parameters.MaxRudderDeg);
                }

                double dt = Math.Min(dtSeconds, endSeconds - t);
                double maxRudderDelta = parameters.RudderRateDegPerSec * dt;
                rudder += Clamp(rudderCommand - rudder, -maxRudderDelta, maxRudderDelta);
                rudder = Clamp(rudder, -parameters.MaxRudderDeg, parameters.MaxRudderDeg);

                double anchorDecelKnPerSec = 0.0;
                double anchorYawDegPerSec = 0.0;
                if (anchorDropped && t >= anchorEffectiveTime - 1e-9)
                {
                    double effectiveSpeed = parameters.Anchor.MaxEffectiveSpeedKn;
                    double reduction = u > effectiveSpeed ? effectiveSpeed / u : 1.0;
                    anchorDecelKnPerSec = parameters.Anchor.DecelerationKnPerSec * reduction;
                    double yawRate = parameters.Anchor.YawRateDegPerSec *
                        AnchorYawSpeedFactor(u, parameters.MinSpeedKn, parameters.Anchor.FullYawSpeedKn);
                    if (anchorSide == AnchorSide.Port)
                    {
                        anchorYawDegPerSec = -yawRate;
                    }
                    else if (anchorSide == AnchorSide.Starboard)
                    {
                        anchorYawDegPerSec = yawRate;
                    }
                }

                double dPsi1, dR1, dU1, dE1, dN1;
                Derivatives(psi, r, u, rudder, parameters, speedTarget, speedTau,
                    anchorDecelKnPerSec, anchorYawDegPerSec,
                    out dPsi1, out dR1, out dU1, out dE1, out dN1);

                double psi2 = psi + dPsi1 * dt * 0.5;
                double r2 = r + dR1 * dt * 0.5;
                double u2 = u + dU1 * dt * 0.5;
                double e2 = east + dE1 * dt * 0.5;
                double n2 = north + dN1 * dt * 0.5;
                double dPsi2, dR2, dU2, dE2, dN2;
                Derivatives(psi2, r2, u2, rudder, parameters, speedTarget, speedTau,
                    anchorDecelKnPerSec, anchorYawDegPerSec,
                    out dPsi2, out dR2, out dU2, out dE2, out dN2);

                double psi3 = psi + dPsi2 * dt * 0.5;
                double r3 = r + dR2 * dt * 0.5;
                double u3 = u + dU2 * dt * 0.5;
                double e3 = east + dE2 * dt * 0.5;
                double n3 = north + dN2 * dt * 0.5;
                double dPsi3, dR3, dU3, dE3, dN3;
                Derivatives(psi3, r3, u3, rudder, parameters, speedTarget, speedTau,
                    anchorDecelKnPerSec, anchorYawDegPerSec,
                    out dPsi3, out dR3, out dU3, out dE3, out dN3);

                double psi4 = psi + dPsi3 * dt;
                double r4 = r + dR3 * dt;
                double u4 = u + dU3 * dt;
                double e4 = east + dE3 * dt;
                double n4 = north + dN3 * dt;
                double dPsi4, dR4, dU4, dE4, dN4;
                Derivatives(psi4, r4, u4, rudder, parameters, speedTarget, speedTau,
                    anchorDecelKnPerSec, anchorYawDegPerSec,
                    out dPsi4, out dR4, out dU4, out dE4, out dN4);

                psi += dt / 6.0 * (dPsi1 + 2.0 * dPsi2 + 2.0 * dPsi3 + dPsi4);
                r += dt / 6.0 * (dR1 + 2.0 * dR2 + 2.0 * dR3 + dR4);
                u += dt / 6.0 * (dU1 + 2.0 * dU2 + 2.0 * dU3 + dU4);
                east += dt / 6.0 * (dE1 + 2.0 * dE2 + 2.0 * dE3 + dE4);
                north += dt / 6.0 * (dN1 + 2.0 * dN2 + 2.0 * dN3 + dN4);
                if (u < parameters.MinSpeedKn)
                {
                    u = parameters.MinSpeedKn;
                }
                t += dt;

                result.Add(new KinematicState(t, east, north, psi, u, r, rudder));
            }

            return new ReadOnlyCollection<KinematicState>(result);
        }

        private static void ApplyIntervention(
            Intervention intervention,
            double psi,
            double u,
            ManeuverParams parameters,
            ref double speedTarget,
            ref double speedTau,
            ref double rudderCommand,
            ref bool turning,
            ref double turnStartPsi,
            ref double turnChangeDeg,
            ref bool holding,
            ref double holdTargetPsi,
            ref bool anchorDropped,
            ref double anchorEffectiveTime,
            ref AnchorSide anchorSide)
        {
            switch (intervention.Kind)
            {
                case InterventionKind.Turn:
                    rudderCommand = Clamp(
                        intervention.RudderDeg,
                        -parameters.MaxRudderDeg,
                        parameters.MaxRudderDeg);
                    if (Math.Abs(intervention.HeadingChangeDeg) > 1e-9)
                    {
                        turning = true;
                        turnStartPsi = psi;
                        turnChangeDeg = intervention.HeadingChangeDeg;
                        holding = false;
                    }
                    else
                    {
                        turning = false;
                        holding = false;
                    }
                    break;

                case InterventionKind.SpeedChange:
                    speedTarget = Math.Max(intervention.TargetSpeedKn, parameters.MinSpeedKn);
                    speedTau = parameters.SpeedTimeConstantSec;
                    break;

                case InterventionKind.Stop:
                    speedTarget = parameters.MinSpeedKn;
                    speedTau = parameters.StopTimeConstantSec;
                    break;

                case InterventionKind.FullAstern:
                    speedTarget = parameters.MinSpeedKn;
                    speedTau = parameters.AsternTimeConstantSec;
                    break;

                case InterventionKind.HoldCourse:
                    turning = false;
                    holding = true;
                    holdTargetPsi = psi;
                    speedTarget = u;
                    speedTau = parameters.SpeedTimeConstantSec;
                    break;

                case InterventionKind.EmergencyAnchor:
                    anchorDropped = true;
                    anchorEffectiveTime = intervention.ExecutionTimeSeconds + parameters.Anchor.LetGoToBiteSec;
                    anchorSide = intervention.AnchorSide;
                    break;
            }
        }

        private static void Derivatives(
            double psiDeg,
            double rDegPerSec,
            double uKn,
            double rudderDeg,
            ManeuverParams parameters,
            double speedTargetKn,
            double speedTau,
            double anchorDecelKnPerSec,
            double anchorYawDegPerSec,
            out double dPsi,
            out double dR,
            out double dU,
            out double dEast,
            out double dNorth)
        {
            double uSafe = Math.Max(uKn, parameters.MinSpeedKn);
            dPsi = rDegPerSec + anchorYawDegPerSec;
            dR = (parameters.K * (uSafe / parameters.ReferenceSpeedKn) * rudderDeg - rDegPerSec) / parameters.T;
            dU = (speedTargetKn - uKn) / speedTau - anchorDecelKnPerSec;
            double speedMps = uSafe * VesselMotionState.MpsPerKnot;
            double rad = psiDeg * Math.PI / 180.0;
            dEast = speedMps * Math.Sin(rad);
            dNorth = speedMps * Math.Cos(rad);
        }

        /// <summary>
        /// 单锚转首率的航速折减系数：u ≥ FullYawSpeedKn 为 1；MinSpeed &lt; u &lt; FullYawSpeedKn 线性；
        /// u ≤ MinSpeed（停船）为 0。
        /// </summary>
        public static double AnchorYawSpeedFactor(double speedKn, double minSpeedKn, double fullYawSpeedKn)
        {
            double span = fullYawSpeedKn - minSpeedKn;
            if (span <= 1e-9)
            {
                return speedKn > minSpeedKn + 1e-9 ? 1.0 : 0.0;
            }
            return Clamp((speedKn - minSpeedKn) / span, 0.0, 1.0);
        }

        private static double Clamp(double value, double min, double max)
        {
            if (value < min) return min;
            if (value > max) return max;
            return value;
        }
    }

    /// <summary>
    /// 单船反事实航迹：固定步长状态序列，支持任意时刻采样与运动学/碰撞体转换。
    /// </summary>
    public sealed class CounterfactualTrack
    {
        private readonly KinematicState[] _states;
        private readonly ReadOnlyCollection<KinematicState> _readonlyStates;
        private readonly Func<double, KinematicState> _original;

        /// <summary>船舶标识。</summary>
        public string VesselId { get; }

        /// <summary>展示用船名（默认与 VesselId 相同）。</summary>
        public string DisplayName { get; }

        /// <summary>反事实积分步长（秒）。</summary>
        public double StepSeconds { get; }

        /// <summary>反事实状态序列（按时间升序）。</summary>
        public IReadOnlyList<KinematicState> States
        {
            get { return _readonlyStates; }
        }

        /// <summary>是否发生偏离（原始情景为 false）。</summary>
        public bool Diverged { get; }

        /// <summary>偏离原航迹时刻（秒）；未偏离为 NaN。</summary>
        public double DivergeTimeSeconds { get; }

        /// <summary>船舶总长（米）。</summary>
        public double LoaM { get; }

        /// <summary>船舶型宽（米）。</summary>
        public double BeamM { get; }

        /// <summary>排水量（吨）。</summary>
        public double DisplacementTons { get; }

        /// <summary>构造反事实航迹。</summary>
        public CounterfactualTrack(
            string vesselId,
            double stepSeconds,
            IReadOnlyList<KinematicState> states,
            bool diverged,
            double divergeTimeSeconds,
            ManeuverParams parameters,
            Func<double, KinematicState> original,
            string displayName = null)
        {
            if (string.IsNullOrWhiteSpace(vesselId))
            {
                throw new ArgumentException("船舶标识不能为空。", nameof(vesselId));
            }
            if (parameters == null)
            {
                throw new ArgumentNullException(nameof(parameters));
            }
            if (states == null || states.Count == 0)
            {
                throw new ArgumentException("状态序列不能为空。", nameof(states));
            }

            VesselId = vesselId;
            DisplayName = string.IsNullOrWhiteSpace(displayName) ? vesselId : displayName;
            StepSeconds = stepSeconds > 0.0 ? stepSeconds : 0.1;
            _states = states.ToArray();
            _readonlyStates = new ReadOnlyCollection<KinematicState>(_states);
            Diverged = diverged;
            DivergeTimeSeconds = diverged ? divergeTimeSeconds : double.NaN;
            LoaM = parameters.LoaM;
            BeamM = parameters.BeamM;
            DisplacementTons = parameters.DisplacementTons;
            _original = original;
        }

        /// <summary>
        /// 任意时刻采样：偏离前严格返回原航迹；偏离后对状态序列做线性插值，范围外钳制。
        /// </summary>
        public KinematicState SampleAt(double timeSeconds)
        {
            if (_original != null && (!Diverged || timeSeconds <= DivergeTimeSeconds + 1e-9))
            {
                return _original(timeSeconds);
            }

            KinematicState first = _states[0];
            KinematicState last = _states[_states.Length - 1];
            if (timeSeconds <= first.TimeSeconds)
            {
                return WithTime(first, timeSeconds);
            }
            if (timeSeconds >= last.TimeSeconds)
            {
                return WithTime(last, timeSeconds);
            }

            int lo = 0;
            int hi = _states.Length - 2;
            while (lo <= hi)
            {
                int mid = lo + ((hi - lo) >> 1);
                if (timeSeconds < _states[mid].TimeSeconds)
                {
                    hi = mid - 1;
                }
                else if (timeSeconds > _states[mid + 1].TimeSeconds)
                {
                    lo = mid + 1;
                }
                else
                {
                    lo = mid;
                    break;
                }
            }
            lo = Math.Max(0, Math.Min(_states.Length - 2, lo));
            KinematicState a = _states[lo];
            KinematicState b = _states[lo + 1];
            double span = b.TimeSeconds - a.TimeSeconds;
            double f = span > 1e-12 ? (timeSeconds - a.TimeSeconds) / span : 0.0;
            KinematicState lerped = KinematicState.Lerp(a, b, f);
            return new KinematicState(
                timeSeconds, lerped.EastM, lerped.NorthM, lerped.HeadingDeg,
                lerped.SpeedKn, lerped.RotDegPerSec, lerped.RudderDeg);
        }

        /// <summary>转换为 CPA 使用的船舶运动状态（无流时 COG=船首向）。</summary>
        public VesselMotionState ToMotionState(double timeSeconds)
        {
            KinematicState state = SampleAt(timeSeconds);
            return new VesselMotionState(
                state.EastM / VesselMotionState.MetersPerNm,
                state.NorthM / VesselMotionState.MetersPerNm,
                state.SpeedKn,
                state.HeadingDeg,
                timeSeconds);
        }

        /// <summary>转换为碰撞检测使用的 OBB 船体状态。</summary>
        public CollisionBodyState ToBodyState(double timeSeconds)
        {
            KinematicState state = SampleAt(timeSeconds);
            double rad = state.HeadingDeg * Math.PI / 180.0;
            double speedMps = state.SpeedKn * VesselMotionState.MpsPerKnot;
            return new CollisionBodyState(
                VesselId,
                new EnuPosition(state.EastM, state.NorthM, 0.0),
                state.HeadingDeg,
                new Double2(speedMps * Math.Sin(rad), speedMps * Math.Cos(rad)),
                (float)LoaM,
                (float)BeamM,
                (float)DisplacementTons,
                false);
        }

        private static KinematicState WithTime(KinematicState state, double timeSeconds)
        {
            return new KinematicState(
                timeSeconds, state.EastM, state.NorthM, state.HeadingDeg,
                state.SpeedKn, state.RotDegPerSec, state.RudderDeg);
        }
    }

    /// <summary>由原航迹与情景设定构建反事实航迹。</summary>
    public static class CounterfactualBuilder
    {
        /// <summary>
        /// 构建反事实航迹。scenario 为 null 或没有干预时等同于原航迹；
        /// 偏离时刻之前逐点取原航迹，偏离后由 Nomoto 模型积分。
        /// </summary>
        public static CounterfactualTrack Build(
            WhatIfVessel vessel,
            VesselScenario scenario,
            double stepSeconds = 0.1)
        {
            if (vessel == null)
            {
                throw new ArgumentNullException(nameof(vessel));
            }
            if (double.IsNaN(stepSeconds) || double.IsInfinity(stepSeconds) || stepSeconds <= 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(stepSeconds), "步长必须为有限正数。");
            }

            List<Intervention> ordered = new List<Intervention>();
            if (scenario != null)
            {
                for (int i = 0; i < scenario.Interventions.Count; i++)
                {
                    if (scenario.Interventions[i] != null)
                    {
                        ordered.Add(scenario.Interventions[i]);
                    }
                }
            }

            bool hasInterventions = ordered.Count > 0;
            bool hasExplicitDiverge = scenario != null && scenario.DivergeTimeSeconds.HasValue;
            if (!hasInterventions && !hasExplicitDiverge)
            {
                return BuildOriginal(vessel, stepSeconds);
            }

            ordered.Sort((a, b) =>
            {
                int cmp = a.ExecutionTimeSeconds.CompareTo(b.ExecutionTimeSeconds);
                if (cmp != 0) return cmp;
                return a.TimeSeconds.CompareTo(b.TimeSeconds);
            });

            double diverge = scenario.DivergeTimeSeconds.HasValue
                ? scenario.DivergeTimeSeconds.Value
                : ordered[0].ExecutionTimeSeconds;
            if (diverge < vessel.StartSeconds) diverge = vessel.StartSeconds;
            if (diverge > vessel.EndSeconds) diverge = vessel.EndSeconds;

            KinematicState initial = vessel.SampleAt(diverge);
            initial = new KinematicState(
                diverge, initial.EastM, initial.NorthM, initial.HeadingDeg,
                initial.SpeedKn, 0.0, 0.0);

            List<Intervention> applicable = new List<Intervention>();
            for (int i = 0; i < ordered.Count; i++)
            {
                if (ordered[i].ExecutionTimeSeconds >= diverge - 1e-9)
                {
                    applicable.Add(ordered[i]);
                }
            }

            IReadOnlyList<KinematicState> simulated = NomotoSimulator.Simulate(
                initial, vessel.Params, applicable, vessel.EndSeconds, stepSeconds);

            List<KinematicState> states = new List<KinematicState>();
            double t = vessel.StartSeconds;
            while (t < diverge - 1e-9)
            {
                states.Add(vessel.SampleAt(t));
                t += stepSeconds;
            }
            for (int i = 0; i < simulated.Count; i++)
            {
                if (states.Count > 0 && simulated[i].TimeSeconds <= states[states.Count - 1].TimeSeconds + 1e-9)
                {
                    continue;
                }
                states.Add(simulated[i]);
            }
            if (states.Count == 0)
            {
                states.Add(initial);
            }

            return new CounterfactualTrack(
                vessel.Id, stepSeconds, states, true, diverge,
                vessel.Params, vessel.SampleAt, vessel.DisplayName);
        }

        private static CounterfactualTrack BuildOriginal(WhatIfVessel vessel, double stepSeconds)
        {
            List<KinematicState> states = new List<KinematicState>();
            double t = vessel.StartSeconds;
            while (t < vessel.EndSeconds - 1e-9)
            {
                states.Add(vessel.SampleAt(t));
                t += stepSeconds;
            }
            states.Add(vessel.SampleAt(vessel.EndSeconds));
            return new CounterfactualTrack(
                vessel.Id, stepSeconds, states, false, double.NaN,
                vessel.Params, vessel.SampleAt, vessel.DisplayName);
        }
    }
}
