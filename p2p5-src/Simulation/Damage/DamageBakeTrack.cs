using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Damage
{
    /// <summary>调查员指定的沉没关键帧剖面（来源标记视为推定）。</summary>
    public sealed class ScriptedSinkProfile
    {
        public string VesselId { get; }
        public SimTime StartTime { get; }
        public double DurationSeconds { get; }
        public float TargetListAngleDeg { get; }
        public float TargetTrimAngleDeg { get; }
        public float TargetSinkDepthM { get; }

        public ScriptedSinkProfile(
            string vesselId,
            SimTime startTime,
            double durationSeconds,
            float targetListAngleDeg,
            float targetTrimAngleDeg,
            float targetSinkDepthM)
        {
            VesselId = vesselId ?? string.Empty;
            StartTime = startTime;
            DurationSeconds = durationSeconds > 0.0 ? durationSeconds : 1.0;
            TargetListAngleDeg = targetListAngleDeg;
            TargetTrimAngleDeg = targetTrimAngleDeg;
            TargetSinkDepthM = targetSinkDepthM;
        }
    }

    /// <summary>碰撞后 10 Hz 烘焙轨迹，支持确定性线性采样。</summary>
    public interface IDamageBakeTrack
    {
        string VesselId { get; }
        SimTime StartTime { get; }
        SimTime EndTime { get; }
        IReadOnlyList<DamageKeyframe> Keyframes { get; }
        DamageKeyframe SampleAt(SimTime time);
    }

    public sealed class DamageBakeTrack : IDamageBakeTrack
    {
        public const double DefaultSampleHz = 10.0;

        public string VesselId { get; }
        public SimTime StartTime { get; }
        public SimTime EndTime { get; }
        public IReadOnlyList<DamageKeyframe> Keyframes { get; }

        public DamageBakeTrack(string vesselId, IReadOnlyList<DamageKeyframe> keyframes)
        {
            VesselId = vesselId ?? string.Empty;
            Keyframes = keyframes ?? Array.Empty<DamageKeyframe>();
            if (Keyframes.Count == 0)
            {
                StartTime = SimTime.Zero;
                EndTime = SimTime.Zero;
            }
            else
            {
                StartTime = Keyframes[0].Time;
                EndTime = Keyframes[Keyframes.Count - 1].Time;
            }
        }

        public DamageKeyframe SampleAt(SimTime time)
        {
            if (Keyframes.Count == 0)
            {
                return new DamageKeyframe(time, EnuPosition.Zero, 0f, 0f, 0f, 0f, 0f);
            }

            if (time <= StartTime)
            {
                return Keyframes[0];
            }

            if (time >= EndTime)
            {
                return Keyframes[Keyframes.Count - 1];
            }

            int lo = 0;
            int hi = Keyframes.Count - 1;
            while (hi - lo > 1)
            {
                int mid = (lo + hi) / 2;
                if (Keyframes[mid].Time <= time)
                {
                    lo = mid;
                }
                else
                {
                    hi = mid;
                }
            }

            DamageKeyframe a = Keyframes[lo];
            DamageKeyframe b = Keyframes[hi];
            double span = b.Time.Seconds - a.Time.Seconds;
            double s = span > 1e-12 ? (time.Seconds - a.Time.Seconds) / span : 0.0;
            s = Math.Max(0.0, Math.Min(1.0, s));
            return new DamageKeyframe(
                time,
                new EnuPosition(
                    Lerp(a.EnuCenter.EastM, b.EnuCenter.EastM, s),
                    Lerp(a.EnuCenter.NorthM, b.EnuCenter.NorthM, s),
                    Lerp(a.EnuCenter.UpM, b.EnuCenter.UpM, s)),
                (float)LerpAngle(a.HdgDeg, b.HdgDeg, s),
                (float)Lerp(a.RollDeg, b.RollDeg, s),
                (float)Lerp(a.PitchDeg, b.PitchDeg, s),
                (float)Lerp(a.SinkHeaveM, b.SinkHeaveM, s),
                (float)Lerp(a.FloodedWaterMassTons, b.FloodedWaterMassTons, s));
        }

        public static DamageBakeTrack BakeFlooding(
            string vesselId,
            CollisionEvent collision,
            VesselParticulars vessel,
            CollisionBodyState stateAtTc,
            SimTime endTime,
            double sampleHz = DefaultSampleHz,
            double cd = FloodingModel.DefaultDischargeCoeff,
            Func<double, CollisionBodyState> residualMotion = null)
        {
            double hz = sampleHz > 0.0 ? sampleHz : DefaultSampleHz;
            double dt = 1.0 / hz;
            var frames = new List<DamageKeyframe>();
            double floodedKg = 0.0;
            double sink = 0.0;
            double roll = 0.0;
            double t = collision.CollisionTime.Seconds;
            double tEnd = endTime.Seconds;
            if (tEnd < t)
            {
                tEnd = t;
            }

            int guard = 0;
            while (t <= tEnd + 1e-9 && guard < 100000)
            {
                CollisionBodyState st = residualMotion != null ? residualMotion(t) : stateAtTc;
                EnuPosition pos = new EnuPosition(st.Center.EastM, st.Center.NorthM, st.Center.UpM - sink);
                frames.Add(new DamageKeyframe(
                    new SimTime(t),
                    pos,
                    (float)st.HeadingDeg,
                    (float)roll,
                    0f,
                    (float)sink,
                    (float)(floodedKg / 1000.0)));

                if (t >= tEnd)
                {
                    break;
                }

                double next = Math.Min(t + dt, tEnd);
                FloodingModel.IntegrateStep(vessel, collision, next - t, ref floodedKg, ref sink, ref roll, cd);
                t = next;
                guard++;
            }

            return new DamageBakeTrack(vesselId, frames);
        }

        public static DamageBakeTrack BakeScripted(
            ScriptedSinkProfile profile,
            CollisionBodyState stateAtStart,
            double sampleHz = DefaultSampleHz)
        {
            if (profile == null)
            {
                throw new ArgumentNullException(nameof(profile));
            }

            double hz = sampleHz > 0.0 ? sampleHz : DefaultSampleHz;
            double dt = 1.0 / hz;
            var frames = new List<DamageKeyframe>();
            double t0 = profile.StartTime.Seconds;
            double t1 = t0 + profile.DurationSeconds;
            double t = t0;
            int guard = 0;
            while (t <= t1 + 1e-9 && guard < 100000)
            {
                double s = profile.DurationSeconds > 1e-9 ? (t - t0) / profile.DurationSeconds : 1.0;
                s = SmoothStep(Math.Max(0.0, Math.Min(1.0, s)));
                float roll = (float)(profile.TargetListAngleDeg * s);
                float pitch = (float)(profile.TargetTrimAngleDeg * s);
                float sink = (float)(profile.TargetSinkDepthM * s);
                var pos = new EnuPosition(stateAtStart.Center.EastM, stateAtStart.Center.NorthM, stateAtStart.Center.UpM - sink);
                frames.Add(new DamageKeyframe(new SimTime(t), pos, (float)stateAtStart.HeadingDeg, roll, pitch, sink, 0f));
                if (t >= t1)
                {
                    break;
                }

                t = Math.Min(t + dt, t1);
                guard++;
            }

            return new DamageBakeTrack(profile.VesselId, frames);
        }

        private static double Lerp(double a, double b, double s)
        {
            return a + (b - a) * s;
        }

        private static double LerpAngle(double a, double b, double s)
        {
            double d = (b - a) % 360.0;
            if (d > 180.0) d -= 360.0;
            if (d <= -180.0) d += 360.0;
            double v = a + d * s;
            v %= 360.0;
            if (v < 0.0) v += 360.0;
            return v;
        }

        private static double SmoothStep(double s)
        {
            return s * s * (3.0 - 2.0 * s);
        }
    }
}
