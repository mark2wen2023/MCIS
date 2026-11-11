using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    /// <summary>手绘航迹关键点（位置必填，时间或航速可选；缺时间则按航速沿样条分配）。</summary>
    public sealed class ManualDrawnWaypoint
    {
        public GeoCoord? Geo { get; }
        public EnuPosition? Enu { get; }
        public SimTime? Time { get; }
        public float? SogKn { get; }
        public float? HdgDeg { get; }

        public ManualDrawnWaypoint(GeoCoord geo, SimTime? time = null, float? sogKn = null, float? hdgDeg = null)
        {
            Geo = geo;
            Enu = null;
            Time = time;
            SogKn = sogKn;
            HdgDeg = hdgDeg;
        }

        public ManualDrawnWaypoint(EnuPosition enu, SimTime? time = null, float? sogKn = null, float? hdgDeg = null)
        {
            Geo = null;
            Enu = enu;
            Time = time;
            SogKn = sogKn;
            HdgDeg = hdgDeg;
        }
    }

    /// <summary>
    /// 将海图手绘关键点经 Catmull-Rom / Hermite 样条转换为带时间的 TrackSample（Provenance = ManualDrawn），按航速分配时间。
    /// </summary>
    public sealed class ManualDrawnTrackBuilder
    {
        public const double DefaultSpeedKn = 8.0;
        public const double DefaultSampleStepSec = 1.0;

        /// <summary>从手绘关键点构建可连续求值航迹。</summary>
        public IShipTrack Build(
            string vesselId,
            IReadOnlyList<ManualDrawnWaypoint> waypoints,
            IGeoConverter geoConverter,
            InterpolationMode mode = InterpolationMode.CatmullRom,
            double defaultSpeedKn = DefaultSpeedKn,
            double sampleStepSec = DefaultSampleStepSec,
            SimTime? startTime = null)
        {
            if (string.IsNullOrWhiteSpace(vesselId))
            {
                throw new ArgumentException("vesselId 不能为空", nameof(vesselId));
            }

            if (geoConverter == null)
            {
                throw new ArgumentNullException(nameof(geoConverter));
            }

            if (waypoints == null || waypoints.Count < 2)
            {
                throw new ArgumentException("手绘航迹至少需要两个关键点", nameof(waypoints));
            }

            EnuPosition[] positions = ResolvePositions(waypoints, geoConverter);
            double[] times = AllocateTimes(waypoints, positions, defaultSpeedKn, startTime ?? SimTime.Zero);
            double[] speedsMps = ResolveSpeedsMps(waypoints, defaultSpeedKn);

            List<TrackSample> dense = Resample(
                positions,
                times,
                speedsMps,
                waypoints,
                geoConverter,
                mode,
                sampleStepSec > 0.0 ? sampleStepSec : DefaultSampleStepSec);

            var interpolator = new TrackInterpolator();
            return interpolator.BuildFromDrawnWaypoints(
                vesselId,
                dense,
                mode,
                1e9,
                GapPolicy.ConnectDashed,
                geoConverter);
        }

        internal static EnuPosition[] ResolvePositions(IReadOnlyList<ManualDrawnWaypoint> waypoints, IGeoConverter geo)
        {
            var result = new EnuPosition[waypoints.Count];
            for (int i = 0; i < waypoints.Count; i++)
            {
                ManualDrawnWaypoint wp = waypoints[i];
                if (wp.Enu.HasValue)
                {
                    result[i] = wp.Enu.Value;
                }
                else if (wp.Geo.HasValue)
                {
                    result[i] = geo.Wgs84ToEnu(wp.Geo.Value);
                }
                else
                {
                    throw new InvalidOperationException("手绘关键点缺少位置（Geo 或 Enu）");
                }
            }

            return result;
        }

        internal static double[] AllocateTimes(
            IReadOnlyList<ManualDrawnWaypoint> waypoints,
            EnuPosition[] positions,
            double defaultSpeedKn,
            SimTime startTime)
        {
            int n = waypoints.Count;
            var times = new double[n];
            bool[] known = new bool[n];
            for (int i = 0; i < n; i++)
            {
                if (waypoints[i].Time.HasValue)
                {
                    times[i] = waypoints[i].Time.Value.Seconds;
                    known[i] = true;
                }
            }

            if (!known[0])
            {
                times[0] = startTime.Seconds;
                known[0] = true;
            }

            for (int i = 1; i < n; i++)
            {
                if (known[i])
                {
                    if (times[i] <= times[i - 1])
                    {
                        times[i] = times[i - 1] + 1e-3;
                    }

                    continue;
                }

                double dist = positions[i - 1].HorizontalDistanceTo(positions[i]);
                double speedKn = waypoints[i - 1].SogKn ?? waypoints[i].SogKn ?? (float)defaultSpeedKn;
                if (speedKn <= 1e-6)
                {
                    speedKn = defaultSpeedKn;
                }

                double speedMps = speedKn * HermiteMath.MetersPerSecondPerKnot;
                double dt = dist / Math.Max(speedMps, 1e-6);
                times[i] = times[i - 1] + Math.Max(dt, 1e-3);
                known[i] = true;
            }

            return times;
        }

        private static double[] ResolveSpeedsMps(IReadOnlyList<ManualDrawnWaypoint> waypoints, double defaultSpeedKn)
        {
            var speeds = new double[waypoints.Count];
            for (int i = 0; i < waypoints.Count; i++)
            {
                double kn = waypoints[i].SogKn ?? (float)defaultSpeedKn;
                if (kn <= 0.0)
                {
                    kn = defaultSpeedKn;
                }

                speeds[i] = kn * HermiteMath.MetersPerSecondPerKnot;
            }

            return speeds;
        }

        private static List<TrackSample> Resample(
            EnuPosition[] positions,
            double[] times,
            double[] speedsMps,
            IReadOnlyList<ManualDrawnWaypoint> waypoints,
            IGeoConverter geo,
            InterpolationMode mode,
            double stepSec)
        {
            var samples = new List<TrackSample>();
            int n = positions.Length;
            double t0 = times[0];
            double t1 = times[n - 1];
            if (t1 <= t0)
            {
                t1 = t0 + stepSec;
            }

            var timeList = new List<double>();
            int count = Math.Max(2, (int)Math.Ceiling((t1 - t0) / stepSec) + 1);
            for (int i = 0; i < count; i++)
            {
                double tt = (i == count - 1) ? t1 : t0 + i * stepSec;
                if (tt > t1) tt = t1;
                timeList.Add(tt);
            }
            for (int k = 0; k < n; k++)
            {
                timeList.Add(times[k]);
            }
            timeList.Sort();
            for (int i = timeList.Count - 1; i > 0; i--)
            {
                if (Math.Abs(timeList[i] - timeList[i - 1]) < 1e-9)
                {
                    timeList.RemoveAt(i);
                }
            }

            for (int i = 0; i < timeList.Count; i++)
            {
                double t = timeList[i];

                int seg = FindSegment(times, t);
                int i0 = seg;
                int i1 = Math.Min(seg + 1, n - 1);
                double span = times[i1] - times[i0];
                double s = span > 1e-9 ? (t - times[i0]) / span : 0.0;
                s = Math.Max(0.0, Math.Min(1.0, s));

                Double2 p0 = new Double2(positions[i0].EastM, positions[i0].NorthM);
                Double2 p1 = new Double2(positions[i1].EastM, positions[i1].NorthM);
                Double2 m0 = Tangent(positions, times, speedsMps, waypoints, i0);
                Double2 m1 = Tangent(positions, times, speedsMps, waypoints, i1);
                Double2 pos;
                Double2 vel;
                if (mode == InterpolationMode.Linear || i0 == i1)
                {
                    pos = p0 + (p1 - p0) * s;
                    vel = span > 1e-9 ? (p1 - p0) / span : Double2.Zero;
                }
                else
                {
                    pos = HermiteMath.EvaluateHermitePosition(p0, m0, p1, m1, span, s);
                    vel = HermiteMath.EvaluateHermiteVelocity(p0, m0, p1, m1, span, s);
                }

                double speed = vel.Length;
                if (speed < 1e-6)
                {
                    speed = Lerp(speedsMps[i0], speedsMps[i1], s);
                    float fallbackHdg = waypoints[i0].HdgDeg ?? waypoints[i1].HdgDeg ?? 0f;
                    vel = HermiteMath.VelocityFromSogCog(speed, fallbackHdg);
                }

                double cog = HermiteMath.VelocityToCogDeg(vel, waypoints[i0].HdgDeg ?? 0f);
                float hdg;
                bool headingFromCog;
                if (waypoints[i0].HdgDeg.HasValue || waypoints[i1].HdgDeg.HasValue)
                {
                    double h0 = waypoints[i0].HdgDeg ?? cog;
                    double h1 = waypoints[i1].HdgDeg ?? cog;
                    hdg = (float)HermiteMath.InterpolateAngleDeg(h0, h1, s);
                    headingFromCog = false;
                }
                else
                {
                    hdg = (float)cog;
                    headingFromCog = true;
                }

                var enu = new EnuPosition(pos.X, pos.Y, 0.0);
                GeoCoord geoCoord = geo.EnuToWgs84(enu);
                float rot = 0f;
                if (i0 != i1 && (waypoints[i0].HdgDeg.HasValue || waypoints[i1].HdgDeg.HasValue))
                {
                    double h0 = waypoints[i0].HdgDeg ?? cog;
                    double h1 = waypoints[i1].HdgDeg ?? cog;
                    rot = (float)(HermiteMath.DeltaAngleDeg(h0, h1) / Math.Max(span, 1e-6));
                }

                samples.Add(new TrackSample(
                    new SimTime(t),
                    geoCoord,
                    enu,
                    vel,
                    (float)speed,
                    (float)HermiteMath.NormalizeAngleDeg(cog),
                    (float)HermiteMath.NormalizeAngleDeg(hdg),
                    rot,
                    SampleProvenance.ManualDrawn,
                    TimeQuality.Estimated,
                    headingFromCog,
                    null));
            }

            samples.Sort((a, b) => a.Time.CompareTo(b.Time));
            return DeduplicateTimes(samples);
        }

        private static List<TrackSample> DeduplicateTimes(List<TrackSample> samples)
        {
            var result = new List<TrackSample>(samples.Count);
            for (int i = 0; i < samples.Count; i++)
            {
                if (result.Count > 0 && Math.Abs(result[result.Count - 1].Time.Seconds - samples[i].Time.Seconds) < 1e-9)
                {
                    result[result.Count - 1] = samples[i];
                }
                else
                {
                    result.Add(samples[i]);
                }
            }

            return result;
        }

        private static int FindSegment(double[] times, double t)
        {
            for (int i = 0; i < times.Length - 1; i++)
            {
                if (t <= times[i + 1])
                {
                    return i;
                }
            }

            return times.Length - 2;
        }

        private static Double2 Tangent(
            EnuPosition[] positions,
            double[] times,
            double[] speedsMps,
            IReadOnlyList<ManualDrawnWaypoint> waypoints,
            int index)
        {
            if (waypoints[index].HdgDeg.HasValue)
            {
                return HermiteMath.VelocityFromSogCog(speedsMps[index], waypoints[index].HdgDeg.Value);
            }

            int n = positions.Length;
            if (index == 0)
            {
                double dt = Math.Max(times[1] - times[0], 1e-6);
                return new Double2((positions[1].EastM - positions[0].EastM) / dt, (positions[1].NorthM - positions[0].NorthM) / dt);
            }

            if (index == n - 1)
            {
                double dt = Math.Max(times[n - 1] - times[n - 2], 1e-6);
                return new Double2((positions[n - 1].EastM - positions[n - 2].EastM) / dt, (positions[n - 1].NorthM - positions[n - 2].NorthM) / dt);
            }

            double dt2 = Math.Max(times[index + 1] - times[index - 1], 1e-6);
            return new Double2(
                (positions[index + 1].EastM - positions[index - 1].EastM) / dt2,
                (positions[index + 1].NorthM - positions[index - 1].NorthM) / dt2);
        }

        private static double Lerp(double a, double b, double s)
        {
            return a + (b - a) * s;
        }
    }
}
